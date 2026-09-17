# -*- coding: utf-8 -*-
"""
Unit tests for Pomodoro Editing Pause, Modal Parent Resolution, and Image Search Modality.
Validates:
1. Pausing timer when card editor or note add modal opens during WORK mode.
2. Ignoring pause_for_editing when timer is in BREAK or LONG_BREAK mode.
3. Resuming timer when leaving editor or note add modal.
4. FocusGuard skipping focus-loss alarms and dialogs when paused by editing.
5. FocusReminderDialog dynamically resolving active modal widget as parent.
6. ImageSearchDialog setting WindowModal modality upon initialization.
"""

import unittest
from unittest.mock import MagicMock, patch

from modules.pomodoro.timer_engine import PomodoroEngine, PomodoroState
from modules.pomodoro.focus_guard import FocusGuard, FocusReminderDialog
from modules.image_search.ui.search_dialog import ImageSearchDialog


class MockDialogBase:
    """Headless Qt dialog simulation supporting parent and modality tracking."""

    def __init__(self, parent=None, *args, **kwargs):
        self._parent = parent
        self._modality = None

    def parent(self):
        return self._parent

    def setWindowModality(self, modality):
        self._modality = modality

    def windowModality(self):
        return self._modality

    def setWindowTitle(self, *args, **kwargs): pass
    def setFixedSize(self, *args, **kwargs): pass
    def setWindowFlags(self, *args, **kwargs): pass
    def setAttribute(self, *args, **kwargs): pass


class SubFocusReminderDialog(FocusReminderDialog, MockDialogBase):
    """Subclass combining FocusReminderDialog and MockDialogBase in MRO."""
    pass


class SubImageSearchDialog(ImageSearchDialog, MockDialogBase):
    """Subclass combining ImageSearchDialog and MockDialogBase in MRO."""
    pass


class TestPomodoroEditingPause(unittest.TestCase):
    """
    Test suite for card editing pause integration and modal hierarchy preservation.
    """

    def test_pause_for_editing_during_work(self):
        """
        When timer is running in WORK mode, entering card editing pauses the timer,
        sets state to PAUSED, is_running to False, and is_paused_by_editing to True.
        """
        engine = PomodoroEngine()
        engine.start_work_cycle()
        self.assertEqual(engine.state, PomodoroState.WORK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

        # User opens card editor or add cards dialog
        result = engine.pause_for_editing(source="card_edit")
        self.assertTrue(result)
        self.assertEqual(engine.state, PomodoroState.PAUSED)
        self.assertFalse(engine.is_running)
        self.assertTrue(engine.is_paused_by_editing)

    def test_pause_for_editing_ignored_during_break(self):
        """
        Cognitive rest breaks (BREAK and LONG_BREAK) must run continuously and
        MUST NOT be paused when user opens an editor or image search.
        """
        engine = PomodoroEngine()

        # 1. Short BREAK
        engine.start_break(is_long=False)
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

        result_break = engine.pause_for_editing(source="card_edit")
        self.assertFalse(result_break)
        self.assertEqual(engine.state, PomodoroState.BREAK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

        # 2. LONG_BREAK
        engine.start_break(is_long=True)
        self.assertEqual(engine.state, PomodoroState.LONG_BREAK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

        result_long_break = engine.pause_for_editing(source="card_edit")
        self.assertFalse(result_long_break)
        self.assertEqual(engine.state, PomodoroState.LONG_BREAK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

    def test_resume_from_editing(self):
        """
        Closing card editor or image search restores WORK mode, restarts the timer,
        and clears the is_paused_by_editing flag.
        """
        engine = PomodoroEngine()
        engine.start_work_cycle()
        self.assertEqual(engine.state, PomodoroState.WORK)
        self.assertTrue(engine.is_running)

        # Pause for editing
        engine.pause_for_editing(source="card_edit")
        self.assertEqual(engine.state, PomodoroState.PAUSED)
        self.assertFalse(engine.is_running)
        self.assertTrue(engine.is_paused_by_editing)

        # Resume from editing
        resumed = engine.resume_from_editing(source="card_edit")
        self.assertTrue(resumed)
        self.assertEqual(engine.state, PomodoroState.WORK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

        # Second resume call when not paused by editing returns False
        resumed_again = engine.resume_from_editing(source="card_edit")
        self.assertFalse(resumed_again)
        self.assertEqual(engine.state, PomodoroState.WORK)
        self.assertTrue(engine.is_running)
        self.assertFalse(engine.is_paused_by_editing)

    @patch("modules.pomodoro.focus_guard.play_pomodoro_sound")
    def test_focus_guard_skips_when_editing_paused(self, mock_play_sound):
        """
        FocusGuard must NOT trigger focus loss alarm or reminder dialog when
        the timer is paused due to card editing.
        """
        engine = PomodoroEngine()
        engine.start_work_cycle()
        engine.pause_for_editing(source="card_edit")
        self.assertTrue(engine.is_paused_by_editing)

        guard = FocusGuard(engine)
        self.assertIsNone(guard._reminder_dialog)

        # 1. _check_focus_loss() must return False and skip
        check_result = guard._check_focus_loss()
        self.assertFalse(check_result)
        mock_play_sound.assert_not_called()
        self.assertIsNone(guard._reminder_dialog)
        self.assertFalse(engine.is_paused_by_loss_of_focus)

        # 2. _trigger_focus_loss() must directly skip without playing alarm or dialog
        guard._trigger_focus_loss()
        mock_play_sound.assert_not_called()
        self.assertIsNone(guard._reminder_dialog)
        self.assertFalse(engine.is_paused_by_loss_of_focus)

        # 3. Heartbeat polling ticks must also skip triggering focus loss
        guard._consecutive_inactive_ticks = 5
        guard._on_focus_poll_tick()
        mock_play_sound.assert_not_called()
        self.assertIsNone(guard._reminder_dialog)

    def test_focus_reminder_dialog_active_modal_parent(self):
        """
        FocusReminderDialog must dynamically resolve QApplication.activeModalWidget()
        as its parent to prevent being hidden beneath active modal dialogs.
        """
        engine = PomodoroEngine()
        mock_active_modal = MagicMock(name="ActiveModalDialog")
        mock_mw = MagicMock(name="MainWindow")

        class MockQApplication:
            @staticmethod
            def activeModalWidget():
                return mock_active_modal

        orig_new = FocusReminderDialog.__new__
        try:
            FocusReminderDialog.__new__ = lambda cls, *args, **kwargs: object.__new__(SubFocusReminderDialog)
            with patch("modules.pomodoro.focus_guard.QApplication", MockQApplication), \
                 patch("modules.pomodoro.focus_guard.QDialog", MockDialogBase), \
                 patch("modules.pomodoro.focus_guard.Qt", MagicMock(), create=True), \
                 patch("modules.pomodoro.focus_guard.mw", mock_mw), \
                 patch.object(FocusReminderDialog, "_setup_ui", lambda self: None):

                # 1. When parent is None, resolves activeModalWidget()
                dialog = FocusReminderDialog(engine)
                self.assertEqual(dialog.parent(), mock_active_modal)
                self.assertNotEqual(dialog.parent(), mock_mw)

                # 2. When parent is explicitly provided, it takes priority
                explicit_parent = MagicMock(name="ExplicitParent")
                dialog_explicit = FocusReminderDialog(engine, parent=explicit_parent)
                self.assertEqual(dialog_explicit.parent(), explicit_parent)

                # 3. Fallback to mw if no modal widget is active
                MockQApplication.activeModalWidget = staticmethod(lambda: None)
                dialog_fallback = FocusReminderDialog(engine)
                self.assertEqual(dialog_fallback.parent(), mock_mw)
        finally:
            FocusReminderDialog.__new__ = orig_new

    def test_image_search_modality(self):
        """
        ImageSearchDialog must initialize with Qt.WindowModality.WindowModal
        so that it blocks its parent window and stays accessible.
        """
        class MockWindowModality:
            WindowModal = "WindowModal_Value"

        class MockQt:
            WindowModality = MockWindowModality

        mock_editor = MagicMock(name="MockEditor")

        orig_new = ImageSearchDialog.__new__
        try:
            ImageSearchDialog.__new__ = lambda cls, *args, **kwargs: object.__new__(SubImageSearchDialog)
            with patch("modules.image_search.ui.search_dialog.QDialog", MockDialogBase), \
                 patch("modules.image_search.ui.search_dialog.Qt", MockQt), \
                 patch.object(ImageSearchDialog, "init_ui", lambda self: None), \
                 patch.object(ImageSearchDialog, "do_search", lambda self: None):
                dialog = ImageSearchDialog(parent=None, editor=mock_editor)
                self.assertEqual(dialog.windowModality(), MockWindowModality.WindowModal)
                self.assertEqual(dialog.windowModality(), "WindowModal_Value")
        finally:
            ImageSearchDialog.__new__ = orig_new


if __name__ == "__main__":
    unittest.main()
