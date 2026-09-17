# -*- coding: utf-8 -*-
"""
Unit tests for Pomodoro Engine & Fatigue Analytics.
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from modules.pomodoro.timer_engine import PomodoroEngine, PomodoroState
from modules.pomodoro.fatigue_analytics import FatigueTracker


class TestPomodoro(unittest.TestCase):

    def test_initial_state_and_countdown(self):
        engine = PomodoroEngine()
        # Initial state is PAUSED until manual start
        self.assertFalse(engine.is_running)
        self.assertEqual(engine.get_formatted_time(), "25:00")

        # Start focus cycle
        engine.start_work_cycle()
        self.assertTrue(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.WORK)

        # Simulate 10 ticks
        for _ in range(10):
            engine.tick()

        self.assertEqual(engine.remaining_seconds, 25 * 60 - 10)
        self.assertEqual(engine.get_formatted_time(), "24:50")

    def test_soft_break_transition(self):
        """When timer reaches 00:00 in WORK, soft break is activated until card is answered."""
        engine = PomodoroEngine()
        engine.start_work_cycle()
        engine.remaining_seconds = 1

        engine.tick()  # Reaches 0
        self.assertEqual(engine.state, PomodoroState.SOFT_BREAK)

        # Answering card finishes the soft break and starts the break
        engine.on_card_answered(ease=3)
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertEqual(engine.completed_cycles, 1)

    def test_long_break_cycle(self):
        """Long break is activated after 4 completed cycles."""
        engine = PomodoroEngine()
        engine.start_work_cycle()
        engine.completed_cycles = 3  # 3 completed so far

        # Trigger soft break and answer card
        engine.state = PomodoroState.SOFT_BREAK
        engine.on_card_answered(ease=3)

        self.assertEqual(engine.completed_cycles, 4)
        self.assertEqual(engine.state, PomodoroState.LONG_BREAK)

    def test_inactivity_auto_pause(self):
        """Timer pauses automatically if user is inactive for longer than threshold."""
        engine = PomodoroEngine()
        engine.start_work_cycle()
        engine.remaining_seconds = 1000

        # Simulate last activity 70 seconds ago
        engine.last_activity_time = time.time() - 70
        engine.tick()

        self.assertEqual(engine.state, PomodoroState.PAUSED)
        self.assertTrue(engine.is_paused_by_inactivity)

        # Card shown resumes timer
        engine.on_card_shown()
        self.assertEqual(engine.state, PomodoroState.WORK)
        self.assertFalse(engine.is_paused_by_inactivity)

    def test_fatigue_tracker_analytics(self):
        tracker = FatigueTracker()

        # Cycle 1: 50 cards, high retention (90%)
        tracker.start_cycle(1)
        for _ in range(45):
            tracker.record_card_answer(ease=3, time_spent_sec=10.0)  # Good
        for _ in range(5):
            tracker.record_card_answer(ease=1, time_spent_sec=10.0)  # Again
        tracker.finish_cycle()

        # Cycle 2: 50 cards, degraded retention (70%)
        tracker.start_cycle(2)
        for _ in range(35):
            tracker.record_card_answer(ease=3, time_spent_sec=10.0)  # Good
        for _ in range(15):
            tracker.record_card_answer(ease=1, time_spent_sec=10.0)  # Again
        tracker.finish_cycle()

        analysis = tracker.analyze_fatigue()
        self.assertTrue(analysis["fatigue_detected"])
        self.assertEqual(analysis["drop_percentage"], 20.0)

    def test_break_overtime_and_add_time(self):
        """Break does not auto-close on reaching 0; it counts negative overtime and supports +5m."""
        engine = PomodoroEngine()
        engine.start_break()
        self.assertEqual(engine.state, PomodoroState.BREAK)
        engine.remaining_seconds = 1

        engine.tick()  # reaches 0
        self.assertEqual(engine.remaining_seconds, 0)
        self.assertEqual(engine.get_formatted_time(), "00:00")
        self.assertEqual(engine.state, PomodoroState.BREAK)  # Stays in break!

        engine.tick()  # enters negative overtime: -1
        self.assertEqual(engine.remaining_seconds, -1)
        self.assertEqual(engine.get_formatted_time(), "-00:01")
        self.assertEqual(engine.state, PomodoroState.BREAK)

        # User adds +5 minutes (+300s)
        engine.add_time_seconds(300)
        self.assertEqual(engine.remaining_seconds, 299)
        self.assertEqual(engine.get_formatted_time(), "04:59")

    def test_focus_loss_pause_and_resume(self):
        """Focus loss during WORK mode pauses timer and sets is_paused_by_loss_of_focus."""
        engine = PomodoroEngine()
        engine.start_work_cycle()
        self.assertTrue(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.WORK)

        # Trigger focus loss
        engine.pause_for_focus_loss()
        self.assertFalse(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.PAUSED)
        self.assertTrue(engine.is_paused_by_loss_of_focus)

        # Resume
        engine.resume_from_focus_loss()
        self.assertTrue(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.WORK)
        self.assertFalse(engine.is_paused_by_loss_of_focus)

    def test_custom_long_break_interval(self):
        """Custom long_break_interval triggers long break at the specified round count."""
        engine = PomodoroEngine()
        # Mock get_deck_durations to return long_break_interval = 2
        engine.get_deck_durations = lambda deck=None: (25, 5, 15, 2)

        # Round 1 -> Short Break
        engine.completed_cycles = 0
        engine.state = PomodoroState.SOFT_BREAK
        engine.on_card_answered(ease=3)
        self.assertEqual(engine.completed_cycles, 1)
        self.assertEqual(engine.state, PomodoroState.BREAK)

        # Round 2 -> Long Break! (2 % 2 == 0)
        engine.state = PomodoroState.SOFT_BREAK
        engine.on_card_answered(ease=3)
        self.assertEqual(engine.completed_cycles, 2)
        self.assertEqual(engine.state, PomodoroState.LONG_BREAK)

    def test_break_not_paused_outside_reviewer(self):
        """Leaving the reviewer during a BREAK or LONG_BREAK does NOT auto-pause the timer."""
        engine = PomodoroEngine()
        engine.start_break()
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertTrue(engine.is_running)

        # Leaving reviewer screen
        engine.on_reviewer_state_changed(in_reviewer=False)
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertTrue(engine.is_running)

    def test_fab_refresh_theme(self):
        """NativePomodoroFab refresh_theme correctly executes and applies active theme."""
        from modules.pomodoro.native_fab import NativePomodoroFab
        engine = PomodoroEngine()
        fab = NativePomodoroFab(engine)
        # Verify refresh_theme runs without error
        fab.refresh_theme()
        self.assertIsNotNone(fab.styleSheet())

    def test_fab_header_focus_toggle_and_auto_advance(self):
        """NativePomodoroFab contains direct header focus button and auto-advance badge."""
        from modules.pomodoro.native_fab import NativePomodoroFab
        engine = PomodoroEngine()
        fab = NativePomodoroFab(engine)

        # Verify widgets exist on the header
        self.assertTrue(hasattr(fab, "btn_focus_toggle"))
        self.assertTrue(hasattr(fab, "lbl_auto_advance"))

        # In windowed mode, button is target icon (to enter focus)
        fab.update_display()
        self.assertIn(fab.btn_focus_toggle.text(), ("🎯", "🗗"))

        # Test auto-advance badge update
        with patch("modules.pomodoro.auto_advance.get_auto_advance_manager") as mock_mgr:
            mock_inst = MagicMock()
            mock_inst.get_countdown_info.return_value = {
                "enabled": True,
                "active": True,
                "side": "question",
                "remaining_seconds": 18,
                "total_seconds": 20,
            }
            mock_mgr.return_value = mock_inst
            fab._update_auto_advance_display()
            self.assertTrue(fab.lbl_auto_advance.isVisible())
            self.assertIn("18s", fab.lbl_auto_advance.text())

            # When inactive, badge hides
            mock_inst.get_countdown_info.return_value = {"active": False}
            fab._update_auto_advance_display()
            self.assertFalse(fab.lbl_auto_advance.isVisible())

    def test_fab_window_flags_no_topmost(self):
        """NativePomodoroFab MUST NOT have WindowStaysOnTopHint so it does not float over other OS applications."""
        from modules.pomodoro.native_fab import NativePomodoroFab
        try:
            from PyQt6.QtCore import Qt
        except ImportError:
            from modules.pomodoro.native_fab import Qt

        engine = PomodoroEngine()
        fab = NativePomodoroFab(engine)
        flags = fab.windowFlags()

        # WindowStaysOnTopHint must NOT be present
        if hasattr(Qt, "WindowType") and hasattr(Qt.WindowType, "WindowStaysOnTopHint"):
            topmost_flag = Qt.WindowType.WindowStaysOnTopHint
        elif hasattr(Qt, "WindowStaysOnTopHint"):
            topmost_flag = Qt.WindowStaysOnTopHint
        else:
            topmost_flag = None

        if topmost_flag is not None and isinstance(flags, int):
            self.assertFalse(bool(flags & topmost_flag))

    def test_fab_event_filter_minimized_handling(self):
        """NativePomodoroFab hides when mw is minimized and shows when restored."""
        from modules.pomodoro.native_fab import NativePomodoroFab
        engine = PomodoroEngine()
        fab = NativePomodoroFab(engine)

        mock_mw = MagicMock()
        mock_mw.isMinimized.return_value = True
        mock_event = MagicMock()
        try:
            from PyQt6.QtCore import QEvent
            mock_event.type.return_value = QEvent.Type.WindowStateChange
        except ImportError:
            mock_event.type.return_value = 105

        with patch("modules.pomodoro.native_fab.mw", mock_mw):
            fab.eventFilter(mock_mw, mock_event)
            self.assertFalse(fab.isVisible())

    def test_break_countdown_never_paused_by_inactivity(self):
        """Break timer MUST run continuously and NEVER pause due to user inactivity."""
        engine = PomodoroEngine()
        engine.start_break()
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertTrue(engine.is_running)
        start_rem = engine.remaining_seconds

        # Simulate user stepping away for 120 seconds (well past the 60s inactivity limit)
        engine.last_activity_time = time.time() - 120
        engine.tick()

        # Engine must remain in BREAK and running, and decrement remaining time!
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_inactivity)
        self.assertEqual(engine.remaining_seconds, start_rem - 1)

    def test_long_break_countdown_never_paused_by_inactivity(self):
        """Long break timer MUST run continuously and NEVER pause due to user inactivity."""
        engine = PomodoroEngine()
        engine.start_break(is_long=True)
        self.assertEqual(engine.state, PomodoroState.LONG_BREAK)
        self.assertTrue(engine.is_running)
        start_rem = engine.remaining_seconds

        # Simulate user inactive for 300 seconds
        engine.last_activity_time = time.time() - 300
        engine.tick()

        self.assertEqual(engine.state, PomodoroState.LONG_BREAK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_inactivity)
        self.assertEqual(engine.remaining_seconds, start_rem - 1)

    def test_focus_loss_guard_triggers_only_in_work(self):
        """FocusGuard pauses timer ONLY during WORK mode, never during BREAK."""
        from modules.pomodoro.focus_guard import FocusGuard
        engine = PomodoroEngine()
        guard = FocusGuard(engine)

        # 1. During WORK mode: focus loss pauses timer
        engine.start_work_cycle()
        self.assertTrue(engine.is_running)
        guard._trigger_focus_loss()
        self.assertFalse(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.PAUSED)
        self.assertTrue(engine.is_paused_by_loss_of_focus)

        # 2. During BREAK mode: focus loss DOES NOT pause timer
        engine.start_break()
        self.assertTrue(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.BREAK)
        guard._trigger_focus_loss()
        self.assertTrue(engine.is_running)
        self.assertEqual(engine.state, PomodoroState.BREAK)

    def test_alarm_sound_presets_exist(self):
        """Verify built-in alarm sound files exist on disk."""
        from modules.pomodoro.sounds import get_sound_asset_path
        digital = get_sound_asset_path("digital_alarm")
        analog = get_sound_asset_path("analog_alarm")
        bell = get_sound_asset_path("bell")
        school = get_sound_asset_path("school_bell")
        self.assertIsNotNone(digital)
        self.assertIsNotNone(analog)
        self.assertIsNotNone(bell)
        self.assertIsNotNone(school)

    def test_is_anki_active_window_executes_safely(self):
        """is_anki_active_window runs without exception and returns boolean."""
        from modules.pomodoro.focus_guard import is_anki_active_window
        result = is_anki_active_window()
        self.assertIsInstance(result, bool)

    def test_focus_guard_heartbeat_polls_during_work(self):
        """FocusGuard heartbeat polls every 250ms and pauses after 2 inactive ticks during WORK."""
        from modules.pomodoro.focus_guard import FocusGuard
        import modules.pomodoro.focus_guard as fg_mod
        engine = PomodoroEngine()
        guard = FocusGuard(engine)

        # Mock is_anki_active_window to False
        orig_is_active = fg_mod.is_anki_active_window
        try:
            fg_mod.is_anki_active_window = lambda: False

            # 1. During WORK mode
            engine.start_work_cycle()
            self.assertTrue(engine.is_running)
            self.assertEqual(engine.state, PomodoroState.WORK)

            # Tick 1: should not pause yet (debounce)
            guard._on_focus_poll_tick()
            self.assertEqual(guard._consecutive_inactive_ticks, 1)
            self.assertTrue(engine.is_running)

            # Tick 2: reaches threshold 2 -> triggers focus loss
            guard._on_focus_poll_tick()
            self.assertFalse(engine.is_running)
            self.assertEqual(engine.state, PomodoroState.PAUSED)
            self.assertTrue(engine.is_paused_by_loss_of_focus)

            # 2. During BREAK mode: heartbeat never pauses break
            engine.start_break()
            self.assertTrue(engine.is_running)
            self.assertEqual(engine.state, PomodoroState.BREAK)

            guard._on_focus_poll_tick()
            guard._on_focus_poll_tick()
            self.assertTrue(engine.is_running)
            self.assertEqual(engine.state, PomodoroState.BREAK)
        finally:
            fg_mod.is_anki_active_window = orig_is_active

    def test_tick_focus_loss_dual_trigger(self):
        """PomodoroEngine.tick() detects focus loss during WORK and pauses immediately."""
        import modules.pomodoro.focus_guard as fg_mod
        orig_is_active = fg_mod.is_anki_active_window
        try:
            fg_mod.is_anki_active_window = lambda: False
            engine = PomodoroEngine()
            engine.start_work_cycle()
            self.assertTrue(engine.is_running)

            # In WORK: tick detects focus loss
            engine.tick()
            self.assertFalse(engine.is_running)
            self.assertEqual(engine.state, PomodoroState.PAUSED)
            self.assertTrue(engine.is_paused_by_loss_of_focus)
        finally:
            fg_mod.is_anki_active_window = orig_is_active

    def test_auto_hide_cursor_lifecycle(self):
        """Cursor hides when idle for 2s during WORK, and restores immediately upon movement."""
        from modules.pomodoro.focus_guard import FocusGuard
        from unittest.mock import MagicMock
        try:
            from PyQt6.QtCore import QPoint
            from PyQt6.QtGui import QCursor
        except ImportError:
            QPoint = None
            QCursor = None

        engine = PomodoroEngine()
        guard = FocusGuard(engine)
        engine.start_work_cycle()

        self.assertFalse(guard._is_cursor_hidden)

        # 1. Simulate mouse idle for 3 seconds
        guard._last_mouse_activity = time.time() - 3.0
        guard._on_focus_poll_tick()
        self.assertTrue(guard._is_cursor_hidden)

        # 2. Simulate physical mouse movement
        if QPoint and QCursor:
            guard._last_cursor_pos = QPoint(100, 100)
            orig_pos = QCursor.pos
            try:
                QCursor.pos = staticmethod(lambda: QPoint(150, 150))
                guard._on_focus_poll_tick()
                self.assertFalse(guard._is_cursor_hidden)
            finally:
                QCursor.pos = orig_pos
        else:
            guard._on_user_interaction()
            self.assertFalse(guard._is_cursor_hidden)

    def test_cursor_never_hidden_during_break(self):
        """Cursor remains visible and is never hidden during BREAK mode."""
        from modules.pomodoro.focus_guard import FocusGuard
        engine = PomodoroEngine()
        guard = FocusGuard(engine)
        engine.start_break()

        # Simulate mouse idle for 10 seconds during break
        guard._last_mouse_activity = time.time() - 10.0
        guard._on_focus_poll_tick()
        self.assertFalse(guard._is_cursor_hidden)

    def test_focus_loss_and_inactivity_outside_anki(self):
        """When user switches away from Anki, mouse movement does NOT reset inactivity and focus loss triggers."""
        from modules.pomodoro.focus_guard import FocusGuard
        try:
            from PyQt6.QtCore import QPoint
            from PyQt6.QtGui import QCursor
        except ImportError:
            QPoint = None
            QCursor = None

        engine = PomodoroEngine()
        guard = FocusGuard(engine)
        engine.start_work_cycle()

        with patch("modules.pomodoro.focus_guard.is_anki_active_window", return_value=False), \
             patch.object(guard, "_trigger_focus_loss") as mock_trigger, \
             patch.object(engine, "register_user_activity") as mock_reg_act:

            # 1. Moving mouse while outside Anki does NOT register user activity
            if QPoint and QCursor:
                guard._last_cursor_pos = QPoint(100, 100)
                orig_pos = QCursor.pos
                try:
                    QCursor.pos = staticmethod(lambda: QPoint(200, 200))
                    guard._on_focus_poll_tick()
                    mock_reg_act.assert_not_called()
                finally:
                    QCursor.pos = orig_pos

            # 2. Polling tick outside Anki increments consecutive ticks and triggers focus loss at threshold (2)
            guard._consecutive_inactive_ticks = 1
            guard._on_focus_poll_tick()
            mock_trigger.assert_called_once()


if __name__ == "__main__":
    unittest.main()

