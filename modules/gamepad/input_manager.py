# -*- coding: utf-8 -*-
"""
Gamepad Input Manager.
Provides non-blocking 60Hz polling via QTimer, radial deadzone calculation,
discrete trigger thresholding, hot-plug detection, and Qt signal emission.
"""

import math
import time
from typing import Set, Tuple, Optional

try:
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal
except ImportError:
    class _DummySignal:
        def __init__(self, *args):
            self._callbacks = []

        def connect(self, cb):
            self._callbacks.append(cb)

        def emit(self, *args, **kwargs):
            for cb in list(self._callbacks):
                cb(*args, **kwargs)

    class QObject:
        def __init__(self, parent=None):
            self._parent = parent

    QTimer = None
    pyqtSignal = _DummySignal

from .drivers import get_gamepad_driver, BaseGamepadDriver, GamepadState
from .drivers.base import (
    BUTTON_LT,
    BUTTON_RT,
    BUTTON_DPAD_UP,
    BUTTON_DPAD_DOWN,
    BUTTON_DPAD_LEFT,
    BUTTON_DPAD_RIGHT,
    STICK_LS_UP,
    STICK_LS_DOWN,
    STICK_LS_LEFT,
    STICK_LS_RIGHT,
    STICK_RS_UP,
    STICK_RS_DOWN,
    STICK_RS_LEFT,
    STICK_RS_RIGHT,
)

try:
    from .actions import keep_system_and_pomodoro_active
except (ImportError, ValueError):
    try:
        from modules.gamepad.actions import keep_system_and_pomodoro_active
    except (ImportError, ValueError):
        keep_system_and_pomodoro_active = None


def apply_radial_deadzone(x: float, y: float, deadzone: float) -> Tuple[float, float]:
    """
    Computes radial deadzone filtering for a 2D analog stick.
    If magnitude is below deadzone, returns (0.0, 0.0).
    Otherwise, rescales smoothly between 0.0 and 1.0 to eliminate stick drift.
    """
    mag = math.hypot(x, y)
    if mag <= deadzone or mag == 0:
        return 0.0, 0.0

    # Rescale magnitude to remove discontinuity at deadzone boundary
    clamped_mag = min(1.0, mag)
    rescaled_mag = (clamped_mag - deadzone) / (1.0 - deadzone)

    norm_x = (x / mag) * rescaled_mag
    norm_y = (y / mag) * rescaled_mag
    return norm_x, norm_y


class GamepadInputManager(QObject):
    """
    Polls active gamepad driver at 60Hz (~16ms), detects button edges,
    filters analog inputs, and emits Qt signals.
    """

    # Signals
    button_down = pyqtSignal(str)              # Emits button name on press
    button_up = pyqtSignal(str)                # Emits button name on release
    connection_changed = pyqtSignal(bool, str) # (connected, device_name)
    continuous_scroll = pyqtSignal(float)      # Scroll delta (pixels)
    listening_captured = pyqtSignal(str)       # Emits captured button in listening mode
    telemetry_updated = pyqtSignal(dict)       # Live telemetry dictionary for visualizer

    def __init__(self, parent=None):
        super().__init__(parent)
        self.driver: BaseGamepadDriver = get_gamepad_driver("auto")

        # Configuration parameters
        self.deadzone: float = 0.15
        self.trigger_threshold: float = 0.5
        self.scroll_sensitivity: float = 50.0
        self.continuous_scroll_stick: str = "right"  # "right" or "left"

        # State tracking
        self._is_connected: bool = False
        self._device_name: str = ""
        self._previous_buttons: Set[str] = set()

        # Interactive binding capture flag
        self.listening_mode: bool = False
        self._last_stick_nav_time: float = 0.0
        self._last_activity_ping_time: float = 0.0

        # 60 Hz Polling Timer (16 ms)
        self._timer: Optional[QTimer] = None
        if QTimer:
            self._timer = QTimer(self)
            self._timer.setInterval(16)
            self._timer.timeout.connect(self.poll_cycle)

    def set_driver(self, driver_type: str):
        """Switches driver backend ('auto', 'xinput', 'pygame')."""
        self.driver = get_gamepad_driver(driver_type)

    def start_polling(self):
        if self._timer and not self._timer.isActive():
            self._timer.start()

    def stop_polling(self):
        if self._timer and self._timer.isActive():
            self._timer.stop()

    def is_polling(self) -> bool:
        return self._timer.isActive() if self._timer else False

    def is_connected(self) -> bool:
        return self._is_connected

    def get_device_name(self) -> str:
        return self._device_name

    def _ping_activity(self, immediate: bool = False):
        """Notifies system keep-alive and pomodoro of user gamepad activity."""
        now = time.time()
        if immediate or (now - self._last_activity_ping_time >= 1.0):
            self._last_activity_ping_time = now
            global keep_system_and_pomodoro_active
            if keep_system_and_pomodoro_active is None:
                try:
                    from .actions import keep_system_and_pomodoro_active
                except (ImportError, ValueError):
                    try:
                        from modules.gamepad.actions import keep_system_and_pomodoro_active
                    except (ImportError, ValueError):
                        keep_system_and_pomodoro_active = None
            if keep_system_and_pomodoro_active:
                try:
                    keep_system_and_pomodoro_active()
                except Exception:
                    pass

    def poll_cycle(self):
        """Executed every 16ms to capture inputs and detect events."""
        raw_state: GamepadState = self.driver.poll()

        # 1. Hot-Plugging Detection
        if raw_state.connected != self._is_connected or raw_state.device_name != self._device_name:
            self._is_connected = raw_state.connected
            self._device_name = raw_state.device_name
            self.connection_changed.emit(self._is_connected, self._device_name)

        if not self._is_connected:
            self._previous_buttons.clear()
            self.telemetry_updated.emit({
                "connected": False,
                "device_name": self._device_name or "Nenhum controle detectado",
                "buttons": set(),
                "raw_buttons": set(),
                "left_trigger": 0.0,
                "right_trigger": 0.0,
                "thumb_lx": 0.0,
                "thumb_ly": 0.0,
                "thumb_rx": 0.0,
                "thumb_ry": 0.0,
                "scroll_delta": 0.0,
                "scroll_stick": self.continuous_scroll_stick,
                "deadzone": self.deadzone,
            })
            return

        # 2. Build current active button set
        current_buttons: Set[str] = set(raw_state.buttons)

        # Trigger Discrete Mode (acting as digital buttons when threshold exceeded)
        if raw_state.left_trigger >= self.trigger_threshold:
            current_buttons.add(BUTTON_LT)
        if raw_state.right_trigger >= self.trigger_threshold:
            current_buttons.add(BUTTON_RT)

        # Analog Stick discrete directional triggers (Left and Right Stick gestures)
        stick_thresh = 0.55
        if raw_state.thumb_ly > stick_thresh:
            current_buttons.add(STICK_LS_UP)
        elif raw_state.thumb_ly < -stick_thresh:
            current_buttons.add(STICK_LS_DOWN)

        if raw_state.thumb_lx > stick_thresh:
            current_buttons.add(STICK_LS_RIGHT)
        elif raw_state.thumb_lx < -stick_thresh:
            current_buttons.add(STICK_LS_LEFT)

        if raw_state.thumb_ry > stick_thresh:
            current_buttons.add(STICK_RS_UP)
        elif raw_state.thumb_ry < -stick_thresh:
            current_buttons.add(STICK_RS_DOWN)

        if raw_state.thumb_rx > stick_thresh:
            current_buttons.add(STICK_RS_RIGHT)
        elif raw_state.thumb_rx < -stick_thresh:
            current_buttons.add(STICK_RS_LEFT)

        activity_pinged = False

        # 3. Edge Detection (Press & Release)
        just_pressed = current_buttons - self._previous_buttons
        just_released = self._previous_buttons - current_buttons
        self._previous_buttons = current_buttons

        if just_pressed:
            self._ping_activity(immediate=True)
            activity_pinged = True

        # 4. Listening Mode for UI Binds
        if self.listening_mode and just_pressed:
            captured_btn = next(iter(just_pressed))
            self.listening_mode = False
            self.listening_captured.emit(captured_btn)
            return

        # 5. Normal Button Press Signals
        for btn in just_pressed:
            self.button_down.emit(btn)

        for btn in just_released:
            self.button_up.emit(btn)

        # 5.5. Left Stick Step Navigation (for lists, DeckBrowser, and Top Navigation Bar)
        now = time.time()
        if (now - self._last_stick_nav_time) > 0.28:
            if abs(raw_state.thumb_ly) > 0.60:
                self._last_stick_nav_time = now
                if not activity_pinged:
                    self._ping_activity(immediate=True)
                    activity_pinged = True
                if raw_state.thumb_ly > 0.60:
                    self.button_down.emit(BUTTON_DPAD_UP)
                else:
                    self.button_down.emit(BUTTON_DPAD_DOWN)
            elif abs(raw_state.thumb_lx) > 0.60:
                self._last_stick_nav_time = now
                if not activity_pinged:
                    self._ping_activity(immediate=True)
                    activity_pinged = True
                if raw_state.thumb_lx > 0.60:
                    self.button_down.emit(BUTTON_DPAD_RIGHT)
                else:
                    self.button_down.emit(BUTTON_DPAD_LEFT)

        # 6. Analog Stick Filtering and Continuous Scrolling
        # Apply radial deadzone to selected stick
        if self.continuous_scroll_stick == "right":
            stick_x, stick_y = raw_state.thumb_rx, raw_state.thumb_ry
        else:
            stick_x, stick_y = raw_state.thumb_lx, raw_state.thumb_ly

        norm_x, norm_y = apply_radial_deadzone(stick_x, stick_y, self.deadzone)

        # Invert stick_y so positive Y (stick pushed UP) scrolls UP (-top delta in DOM)
        scroll_delta = 0.0
        if abs(norm_y) > 0.001:
            scroll_delta = -norm_y * (self.scroll_sensitivity * 0.4)
            self.continuous_scroll.emit(scroll_delta)

        if scroll_delta != 0.0 and not activity_pinged:
            self._ping_activity(immediate=False)

        # 7. Live Telemetry Broadcast for UI Visualizer
        self.telemetry_updated.emit({
            "connected": True,
            "device_name": raw_state.device_name,
            "buttons": current_buttons,
            "raw_buttons": raw_state.buttons,
            "left_trigger": raw_state.left_trigger,
            "right_trigger": raw_state.right_trigger,
            "thumb_lx": raw_state.thumb_lx,
            "thumb_ly": raw_state.thumb_ly,
            "thumb_rx": raw_state.thumb_rx,
            "thumb_ry": raw_state.thumb_ry,
            "scroll_delta": scroll_delta,
            "scroll_stick": self.continuous_scroll_stick,
            "deadzone": self.deadzone,
        })
