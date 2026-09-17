# -*- coding: utf-8 -*-
"""
Pomodoro Timer Engine with Clinical/Card-Adapted Flow:
- Manual Start (Requires user to click Start or press Alt+P)
- Soft Break Mode (waits for current card completion before break)
- Intelligent Inactivity Detection (auto-pause on inactivity)
- Predictive Deck ETA & Cognitive Fatigue Tracking
"""

from enum import Enum
import time
from typing import Optional, Callable, Dict, Any, Tuple

try:
    from PyQt6.QtCore import QTimer
    from aqt import mw
except ImportError:
    QTimer = None
    mw = None

from .fatigue_analytics import FatigueTracker
from .sounds import play_chime_sound, play_pomodoro_sound
try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config


class PomodoroState(Enum):
    WORK = "work"
    SOFT_BREAK = "soft_break"
    BREAK = "break"
    LONG_BREAK = "long_break"
    PAUSED = "paused"


class PomodoroEngine:
    """
    Core state machine for Pomodoro timer with Manual Start requirement.
    """

    def __init__(self):
        self.state: PomodoroState = PomodoroState.PAUSED
        self.previous_state: PomodoroState = PomodoroState.WORK
        self.is_running: bool = False
        self.is_started: bool = False

        self.remaining_seconds: int = 25 * 60
        self.total_phase_seconds: int = 25 * 60
        self.completed_cycles: int = 0

        # Inactivity tracking & Focus loss tracking
        self.last_activity_time: float = time.time()
        self.is_paused_by_inactivity: bool = False
        self.is_paused_by_loss_of_focus: bool = False
        self.is_paused_by_editing: bool = False

        # Analytics
        self.fatigue_tracker = FatigueTracker()
        self.current_cycle_cards_count: int = 0
        self.current_cycle_cards_correct: int = 0
        self.current_cycle_time_spent: float = 0.0
        self.current_deck_name: Optional[str] = None

        # Callbacks
        self.on_tick_callback: Optional[Callable[["PomodoroEngine"], None]] = None
        self.on_state_change_callback: Optional[Callable[["PomodoroEngine"], None]] = None

        # Initialize durations from config
        self._init_durations()

        # Qt Timer setup (1 second tick)
        self._qt_timer = None
        if QTimer:
            self._qt_timer = QTimer()
            self._qt_timer.setInterval(1000)
            self._qt_timer.timeout.connect(self.tick)
            self._qt_timer.start()

    def _init_durations(self):
        durations = self.get_deck_durations(self.current_deck_name)
        work_sec = durations[0] * 60
        self.total_phase_seconds = work_sec
        self.remaining_seconds = work_sec

    def get_deck_durations(self, deck_name: Optional[str] = None) -> Tuple[int, int, int, int]:
        config = get_module_config("pomodoro")
        work_min = int(config.get("work_duration_minutes", 25))
        short_min = int(config.get("short_break_minutes", 5))
        long_min = int(config.get("long_break_minutes", 15))
        long_interval = int(config.get("long_break_interval", 4))

        if deck_name and "deck_profiles" in config:
            deck_profile = config["deck_profiles"].get(deck_name)
            if deck_profile:
                work_min = int(deck_profile.get("work_duration_minutes", work_min))
                short_min = int(deck_profile.get("short_break_minutes", short_min))
                long_min = int(deck_profile.get("long_break_minutes", long_min))

        return work_min, short_min, long_min, long_interval

    def start_work_cycle(self, deck_name: Optional[str] = None):
        """Starts a focus block."""
        if deck_name:
            self.current_deck_name = deck_name
        durations = self.get_deck_durations(self.current_deck_name)
        self.total_phase_seconds = durations[0] * 60
        self.remaining_seconds = self.total_phase_seconds
        self.state = PomodoroState.WORK
        self.is_running = True
        self.is_started = True
        self.is_paused_by_inactivity = False
        self.is_paused_by_loss_of_focus = False
        self.is_paused_by_editing = False
        self.last_activity_time = time.time()
        self.current_cycle_cards_count = 0
        self.current_cycle_cards_correct = 0
        self.current_cycle_time_spent = 0.0

        self._notify_state_change()

    def _notify_state_change(self):
        """Notifies registered callback about state change."""
        if self.on_state_change_callback:
            self.on_state_change_callback(self)

    def pause_for_editing(self, source: str = "card_edit") -> bool:
        """Pauses the timer when entering card editing or note add modal."""
        if self.state == PomodoroState.WORK and self.is_running:
            self.previous_state = self.state
            self.state = PomodoroState.PAUSED
            self.is_running = False
            self.is_paused_by_editing = True
            try:
                from .hooks import log_runtime_event
                log_runtime_event(f"PAUSE_FOR_EDITING: Paused WORK timer (source={source})")
            except Exception:
                pass
            self._notify_state_change()
            return True
        return False

    def resume_from_editing(self, source: str = "card_edit") -> bool:
        """Resumes timer if it was paused by editing."""
        if self.is_paused_by_editing:
            self.is_paused_by_editing = False
            self.state = getattr(self, "previous_state", PomodoroState.WORK) or PomodoroState.WORK
            if self.state == PomodoroState.PAUSED:
                self.state = PomodoroState.WORK
            self.is_running = True
            self.last_activity_time = time.time()
            try:
                from .hooks import log_runtime_event
                log_runtime_event(f"RESUME_FROM_EDITING: Resumed timer to {self.state} (source={source})")
            except Exception:
                pass
            self._notify_state_change()
            return True
        return False

    def start_break(self, is_long: bool = False):
        """Initiates a cognitive rest break."""
        durations = self.get_deck_durations(self.current_deck_name)
        break_min = durations[2] if is_long else durations[1]
        self.total_phase_seconds = break_min * 60
        self.remaining_seconds = self.total_phase_seconds
        self.state = PomodoroState.LONG_BREAK if is_long else PomodoroState.BREAK
        self.is_running = True

        config = get_module_config("pomodoro")
        if config.get("sound_notifications", True):
            play_chime_sound("break")

        self._notify_state_change()

    def trigger_soft_break(self):
        """Signals that focus time has ended, waiting for current card answer."""
        self.state = PomodoroState.SOFT_BREAK
        config = get_module_config("pomodoro")
        if config.get("sound_notifications", True):
            play_chime_sound("soft_break")

        self._notify_state_change()

    def pause_for_focus_loss(self):
        """Pauses the timer when Anki loses window focus during WORK mode."""
        if self.state == PomodoroState.WORK and self.is_running:
            self.previous_state = self.state
            self.state = PomodoroState.PAUSED
            self.is_running = False
            self.is_paused_by_loss_of_focus = True
            self._notify_state_change()

    def resume_from_focus_loss(self):
        """Resumes timer if it was paused by focus loss."""
        if self.is_paused_by_loss_of_focus:
            self.state = self.previous_state if self.previous_state != PomodoroState.PAUSED else PomodoroState.WORK
            self.is_running = True
            self.is_paused_by_loss_of_focus = False
            self.last_activity_time = time.time()
            self._notify_state_change()

    def toggle_pause(self):
        """Toggles play/pause."""
        if not self.is_started:
            self.start_work_cycle()
            return

        if self.is_running:
            self.previous_state = self.state
            self.state = PomodoroState.PAUSED
            self.is_running = False
            self.is_paused_by_inactivity = False
            self.is_paused_by_loss_of_focus = False
            self.is_paused_by_editing = False
        else:
            self.state = self.previous_state if self.previous_state != PomodoroState.PAUSED else PomodoroState.WORK
            self.is_running = True
            self.is_paused_by_inactivity = False
            self.is_paused_by_loss_of_focus = False
            self.is_paused_by_editing = False
            self.last_activity_time = time.time()

        self._notify_state_change()

    def skip_to_break(self):
        """Skips immediately to break."""
        self.completed_cycles += 1
        durations = self.get_deck_durations(self.current_deck_name)
        long_interval = max(1, durations[3])
        is_long = (self.completed_cycles % long_interval == 0)
        self.start_break(is_long)

    def reset_current_phase(self):
        """Resets the timer for the current phase."""
        self.remaining_seconds = self.total_phase_seconds
        if self.on_tick_callback:
            self.on_tick_callback(self)

    def on_card_shown(self):
        """Updates activity timestamp when a card is shown."""
        self.last_activity_time = time.time()
        # If paused by inactivity and timer was running before, auto-resume
        if self.is_paused_by_inactivity and self.is_started:
            self.state = self.previous_state
            self.is_running = True
            self.is_paused_by_inactivity = False
            if self.on_state_change_callback:
                self.on_state_change_callback(self)

    def on_card_answered(self, ease: int, deck_name: Optional[str] = None):
        """Handles card answer event."""
        self.last_activity_time = time.time()
        if deck_name:
            self.current_deck_name = deck_name

        self.current_cycle_cards_count += 1
        if ease > 1:
            self.current_cycle_cards_correct += 1

        # If in SOFT_BREAK, now that card is answered, begin actual break!
        if self.state == PomodoroState.SOFT_BREAK:
            self.completed_cycles += 1
            durations = self.get_deck_durations(self.current_deck_name)
            long_interval = max(1, durations[3])
            is_long = (self.completed_cycles % long_interval == 0)

            # Record cycle analytics
            self.fatigue_tracker.record_cycle(
                cycle_index=self.completed_cycles,
                phase_type="work",
                duration_seconds=self.total_phase_seconds,
                cards_reviewed=self.current_cycle_cards_count,
                correct_count=self.current_cycle_cards_correct,
            )
            self.start_break(is_long)

    def on_reviewer_state_changed(self, in_reviewer: bool, deck_name: Optional[str] = None):
        """Auto-pause when leaving reviewer screen."""
        if deck_name:
            self.current_deck_name = deck_name
        config = get_module_config("pomodoro")
        if not config.get("auto_pause_outside_reviewer", True):
            return

        if not in_reviewer and self.is_running:
            # Cognitive breaks should continue running freely even if user leaves reviewer
            if self.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
                return
            self.previous_state = self.state
            self.state = PomodoroState.PAUSED
            self.is_running = False
            self.is_paused_by_inactivity = False
            if self.on_state_change_callback:
                self.on_state_change_callback(self)

    def add_time_seconds(self, seconds: int):
        """Adds seconds to the current phase timer (e.g. +5 min to break)."""
        self.remaining_seconds += seconds
        if self.remaining_seconds > self.total_phase_seconds:
            self.total_phase_seconds = self.remaining_seconds
        if self.on_tick_callback:
            self.on_tick_callback(self)

    def register_user_activity(self):
        """Registers user activity (keypress/mouse/card interaction) to reset idle timer."""
        self.last_activity_time = time.time()

    def tick(self):
        """Timer tick every 1000ms."""
        if getattr(self, "is_paused_by_editing", False):
            return

        if not self.is_running or self.state == PomodoroState.PAUSED:
            return

        config = get_module_config("pomodoro")

        # 0. Focus loss check - ONLY applies during active WORK (focus) block!
        if self.state == PomodoroState.WORK and config.get("pause_on_focus_loss", True):
            try:
                from .focus_guard import is_anki_active_window
                if not is_anki_active_window():
                    try:
                        from .hooks import log_runtime_event
                        log_runtime_event("FOCUS_LOSS_DETECTED: Tick outside Anki during WORK. Pausing timer and sounding alarm.")
                    except Exception:
                        pass
                    self.pause_for_focus_loss()
                    if config.get("sound_notifications", True):
                        play_pomodoro_sound(event_type="focus_loss")
                    from .hooks import get_focus_guard
                    guard = get_focus_guard()
                    if guard and getattr(guard, "_reminder_dialog", None):
                        guard._reminder_dialog.show_centered()
                    return
            except Exception:
                pass

        # Inactivity check - ONLY applies during active WORK (focus) block!
        # Rest breaks (BREAK / LONG_BREAK) must run continuously without being paused by inactivity.
        if self.state == PomodoroState.WORK and config.get("inactivity_detection", True):
            inactivity_limit = int(config.get("inactivity_timeout_seconds", 60))
            if time.time() - self.last_activity_time > inactivity_limit:
                try:
                    from .hooks import log_runtime_event
                    log_runtime_event(f"INACTIVITY_TIMEOUT: Pausing timer after {inactivity_limit}s idle during WORK.")
                except Exception:
                    pass
                self.previous_state = self.state
                self.state = PomodoroState.PAUSED
                self.is_running = False
                self.is_paused_by_inactivity = True

                # Play alarm sound warning
                if config.get("sound_notifications", True):
                    play_pomodoro_sound(event_type="inactivity")

                if self.on_state_change_callback:
                    self.on_state_change_callback(self)
                return

        # 1. Focus Phase (WORK)
        if self.state == PomodoroState.WORK:
            if self.remaining_seconds > 0:
                self.remaining_seconds -= 1
                self.current_cycle_time_spent += 1
                if self.on_tick_callback:
                    self.on_tick_callback(self)

            if self.remaining_seconds == 0:
                if config.get("sound_notifications", True):
                    play_chime_sound("work_end")
                if config.get("soft_break_mode", True):
                    self.trigger_soft_break()
                else:
                    self.skip_to_break()

        # 2. Break Phase (BREAK or LONG_BREAK)
        elif self.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
            self.remaining_seconds -= 1
            if self.remaining_seconds == 0:
                # Play Break End Sound alert
                if config.get("sound_notifications", True):
                    play_chime_sound("break_end")
            if self.on_tick_callback:
                self.on_tick_callback(self)

    def get_formatted_time(self) -> str:
        if self.remaining_seconds < 0:
            abs_sec = abs(self.remaining_seconds)
            minutes = abs_sec // 60
            seconds = abs_sec % 60
            return f"-{minutes:02d}:{seconds:02d}"
        else:
            minutes = self.remaining_seconds // 60
            seconds = self.remaining_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
