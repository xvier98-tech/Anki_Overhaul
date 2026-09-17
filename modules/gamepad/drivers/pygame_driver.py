# -*- coding: utf-8 -*-
"""
Pygame Joystick Driver (Fallback / Alternative).
Uses pygame.joystick if installed in the environment.
"""

from typing import Set, Optional
from .base import (
    BaseGamepadDriver,
    GamepadState,
    BUTTON_A,
    BUTTON_B,
    BUTTON_X,
    BUTTON_Y,
    BUTTON_LB,
    BUTTON_RB,
    BUTTON_BACK,
    BUTTON_START,
    BUTTON_L3,
    BUTTON_R3,
    BUTTON_DPAD_UP,
    BUTTON_DPAD_DOWN,
    BUTTON_DPAD_LEFT,
    BUTTON_DPAD_RIGHT,
)


class PygameDriver(BaseGamepadDriver):
    """Driver using pygame.joystick module."""

    def __init__(self):
        self._pygame = None
        self._joystick = None
        self._init_pygame()

    def _init_pygame(self):
        try:
            import pygame
            pygame.init()
            pygame.joystick.init()
            self._pygame = pygame
        except Exception:
            self._pygame = None

    def is_available(self) -> bool:
        return self._pygame is not None

    def get_driver_name(self) -> str:
        return "Pygame Joystick Driver"

    def poll(self) -> GamepadState:
        if not self.is_available():
            return GamepadState(connected=False, device_name="Pygame não instalado")

        # Process internal pygame events to update joystick state
        self._pygame.event.pump()

        count = self._pygame.joystick.get_count()
        if count == 0:
            self._joystick = None
            return GamepadState(connected=False, device_name="Nenhum joystick conectado")

        if self._joystick is None or not self._joystick.get_init():
            try:
                self._joystick = self._pygame.joystick.Joystick(0)
                self._joystick.init()
            except Exception:
                return GamepadState(connected=False, device_name="Erro ao inicializar joystick")

        device_name = self._joystick.get_name()

        active_buttons: Set[str] = set()

        # Standard button index mapping (Xbox / generic SDL mapping)
        btn_map = {
            0: BUTTON_A,
            1: BUTTON_B,
            2: BUTTON_X,
            3: BUTTON_Y,
            4: BUTTON_LB,
            5: BUTTON_RB,
            6: BUTTON_BACK,
            7: BUTTON_START,
            8: BUTTON_L3,
            9: BUTTON_R3,
        }

        num_buttons = self._joystick.get_numbuttons()
        for idx, btn_name in btn_map.items():
            if idx < num_buttons and self._joystick.get_button(idx):
                active_buttons.add(btn_name)

        # D-pad via Hats
        num_hats = self._joystick.get_numhats()
        if num_hats > 0:
            hat_x, hat_y = self._joystick.get_hat(0)
            if hat_y == 1:
                active_buttons.add(BUTTON_DPAD_UP)
            elif hat_y == -1:
                active_buttons.add(BUTTON_DPAD_DOWN)
            if hat_x == -1:
                active_buttons.add(BUTTON_DPAD_LEFT)
            elif hat_x == 1:
                active_buttons.add(BUTTON_DPAD_RIGHT)

        # Axes
        num_axes = self._joystick.get_numaxes()
        lx = self._joystick.get_axis(0) if num_axes > 0 else 0.0
        # Invert pygame Y axis to match standard Cartesian (+Y is UP)
        ly = -self._joystick.get_axis(1) if num_axes > 1 else 0.0

        # Triggers (on SDL/Pygame often axes 2 and 5 or 4 and 5, mapped -1.0 to 1.0)
        lt_raw = self._joystick.get_axis(2) if num_axes > 2 else -1.0
        rt_raw = self._joystick.get_axis(5) if num_axes > 5 else -1.0
        lt = max(0.0, (lt_raw + 1.0) / 2.0)
        rt = max(0.0, (rt_raw + 1.0) / 2.0)

        rx = self._joystick.get_axis(3) if num_axes > 3 else 0.0
        ry = -self._joystick.get_axis(4) if num_axes > 4 else 0.0

        return GamepadState(
            connected=True,
            device_name=f"🎮 {device_name}",
            buttons=active_buttons,
            left_trigger=lt,
            right_trigger=rt,
            thumb_lx=max(-1.0, min(1.0, lx)),
            thumb_ly=max(-1.0, min(1.0, ly)),
            thumb_rx=max(-1.0, min(1.0, rx)),
            thumb_ry=max(-1.0, min(1.0, ry)),
        )
