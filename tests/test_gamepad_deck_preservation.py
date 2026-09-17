# -*- coding: utf-8 -*-
"""
Unit tests for Gamepad Deck Selection Preservation and System Keep-Alive.
Validates:
1. keep_system_and_pomodoro_active keeps Windows display and Pomodoro idle timer awake.
2. GamepadInputManager ping activity throttling and immediate button activation.
3. GamepadActionDispatcher last_focused_deck_id retention and return_screen stability.
4. FocusGuard process discovery and active window verification.
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from modules.gamepad.actions import (
    GamepadActionDispatcher,
    keep_system_and_pomodoro_active,
)
from modules.gamepad.input_manager import GamepadInputManager
from modules.gamepad.drivers.base import GamepadState, BUTTON_A, BUTTON_B
from modules.pomodoro.timer_engine import PomodoroEngine, PomodoroState
from modules.pomodoro.focus_guard import get_anki_process_pids, is_anki_active_window


class TestGamepadDeckPreservationAndKeepAlive(unittest.TestCase):

    def test_keep_system_and_pomodoro_active(self):
        """Validates that keep_system_and_pomodoro_active invokes Pomodoro activity registration."""
        mock_engine = MagicMock()
        with patch("modules.pomodoro.hooks.get_pomodoro_engine", return_value=mock_engine):
            keep_system_and_pomodoro_active()
            mock_engine.register_user_activity.assert_called_once()

    def test_dispatcher_last_focused_deck_id_retention(self):
        """Validates that GamepadActionDispatcher tracks last_focused_deck_id and preserves state."""
        dispatcher = GamepadActionDispatcher()
        self.assertIsNone(dispatcher.last_focused_deck_id)

        dispatcher.last_focused_deck_id = "1725839201"
        dispatcher.focused_deck_index = 7

        # Return screen from overview shouldn't blindly wipe focused_deck_index or last_focused_deck_id
        with patch("modules.gamepad.actions.mw") as mock_mw:
            mock_mw.state = "overview"
            handled = dispatcher.execute_action("return_screen")
            self.assertTrue(handled)
            mock_mw.moveToState.assert_called_with("deckBrowser")
            self.assertEqual(dispatcher.last_focused_deck_id, "1725839201")
            self.assertEqual(dispatcher.focused_deck_index, 7)

    def test_input_manager_activity_throttling_and_dispatch(self):
        """Validates input manager immediate ping on button press and 1s throttle on scroll."""
        pings = []
        with patch("modules.gamepad.input_manager.keep_system_and_pomodoro_active", side_effect=lambda: pings.append(time.time())):
            manager = GamepadInputManager()
            
            class MockDriver:
                def __init__(self):
                    self.s = GamepadState(True, "Mock", set(), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                def poll(self):
                    return self.s

            manager.driver = MockDriver()

            # 1. Button down fires immediately
            manager.driver.s.buttons = {BUTTON_A}
            manager.poll_cycle()
            self.assertEqual(len(pings), 1)

            # 2. Holding same button does not fire duplicate
            manager.poll_cycle()
            self.assertEqual(len(pings), 1)

            # 3. Continuous scroll below 1s is throttled
            manager.driver.s.buttons = set()
            manager.driver.s.thumb_ry = 0.35  # above deadzone 0.15, below discrete 0.55
            manager.poll_cycle()
            self.assertEqual(len(pings), 1)

            # 4. After 1.1s, continuous scroll fires ping
            manager._last_activity_ping_time -= 1.1
            manager.poll_cycle()
            self.assertEqual(len(pings), 2)

            # 5. Rapid button press interrupts and fires immediately
            manager.driver.s.buttons = {BUTTON_B}
            manager.poll_cycle()
            self.assertEqual(len(pings), 3)

    def test_focus_guard_pid_discovery(self):
        """Validates that get_anki_process_pids captures the current process and does not error."""
        pids = get_anki_process_pids()
        self.assertIsInstance(pids, set)
        self.assertIn(os.getpid(), pids)

    def test_focus_guard_active_window_qt_fast_path(self):
        """Validates that is_anki_active_window returns True when Qt activeWindow or focusWidget is set."""
        with patch("modules.pomodoro.focus_guard.QApplication") as mock_qapp:
            mock_qapp.activeWindow.return_value = MagicMock()
            mock_qapp.focusWidget.return_value = None
            active = is_anki_active_window()
            self.assertTrue(active)

    def test_navigate_deck_selection_does_not_falsely_ascend_to_topbar_on_up(self):
        """Validates that moving UP when focused_deck_index is 0 does NOT prematurely jump to topbar in Python."""
        dispatcher = GamepadActionDispatcher()
        dispatcher.focus_zone = "decks"
        dispatcher.focused_deck_index = 0

        with patch("modules.gamepad.actions.mw") as mock_mw:
            mock_mw.state = "deckBrowser"
            mock_web = MagicMock()
            mock_mw.deckBrowser.web = mock_web

            dispatcher.navigate_deck_selection(-1)

            # focus_zone must remain 'decks'; JavaScript in webview handles the true DOM index check
            self.assertEqual(dispatcher.focus_zone, "decks")
            mock_web.eval.assert_called_once()
            called_js = mock_web.eval.call_args[0][0]
            self.assertIn("gamepad_ascend_topbar", called_js)
            self.assertIn("curIdx === 0 && -1 < 0", called_js)

    def test_ascend_and_descend_topbar(self):
        """Validates explicit ascend_to_topbar and descend_from_topbar transitions."""
        dispatcher = GamepadActionDispatcher()
        self.assertEqual(dispatcher.focus_zone, "decks")

        with patch("modules.gamepad.actions.mw") as mock_mw:
            mock_mw.state = "deckBrowser"
            mock_mw.deckBrowser.web = MagicMock()
            mock_mw.toolbar.web = MagicMock()

            dispatcher.ascend_to_topbar()
            self.assertEqual(dispatcher.focus_zone, "topbar")
            self.assertEqual(dispatcher.topbar_index, 0)

            dispatcher.descend_from_topbar()
            self.assertEqual(dispatcher.focus_zone, "decks")
            self.assertEqual(dispatcher.focused_deck_index, 0)

    def test_sync_deck_focus(self):
        """Validates that sync_deck_focus updates both focused_deck_index and last_focused_deck_id."""
        dispatcher = GamepadActionDispatcher()
        dispatcher.sync_deck_focus(8, "deck_456")
        self.assertEqual(dispatcher.focus_zone, "decks")
        self.assertEqual(dispatcher.focused_deck_index, 8)
        self.assertEqual(dispatcher.last_focused_deck_id, "deck_456")

    def test_webview_js_message_dispatching(self):
        """Validates on_webview_js_message handling for gamepad_ascend_topbar and gamepad_deck_focused."""
        from modules.gamepad.hooks import on_webview_js_message

        mock_dispatcher = MagicMock()
        with patch("modules.gamepad.hooks.get_gamepad_dispatcher", return_value=mock_dispatcher):
            # 1. Ascend to topbar
            handled, res = on_webview_js_message((False, None), "gamepad_ascend_topbar", None)
            self.assertTrue(handled)
            mock_dispatcher.ascend_to_topbar.assert_called_once()

            # 2. Sync focused deck
            handled, res = on_webview_js_message((False, None), "gamepad_deck_focused:5:16892011", None)
            self.assertTrue(handled)
            mock_dispatcher.sync_deck_focus.assert_called_once_with(5, "16892011")


if __name__ == "__main__":
    unittest.main()
