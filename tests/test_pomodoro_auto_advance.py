# -*- coding: utf-8 -*-
"""
Unit tests for Pomodoro Smart Auto-Advance in the Reviewer.

Verifies:
1. Auto-advance is disabled by default.
2. Question timeout triggers show answer and sets `_auto_question_timeout = True`.
3. Manual flip leaves `_auto_question_timeout = False` and does not start answer timer.
4. Auto-flip starts answer timer and grades 'Again' (ease = 1) on expiration.
5. Answering a card manually stops timers and resets auto-flip flag.
6. Inactivity, focus loss, and editing pause immediately freeze/stop auto-advance timers.
7. Returning from pause restarts countdown for current side in review mode.
8. Break phases (BREAK, LONG_BREAK) completely bypass auto-advance.
"""

import unittest
from unittest.mock import MagicMock, patch

from modules.pomodoro.timer_engine import PomodoroEngine, PomodoroState
from modules.pomodoro.auto_advance import ReviewerAutoAdvanceManager


class TestPomodoroAutoAdvance(unittest.TestCase):
    """Test suite for ReviewerAutoAdvanceManager."""

    def setUp(self):
        self.engine = PomodoroEngine()
        self.manager = ReviewerAutoAdvanceManager(self.engine)
        self.manager._question_timer = MagicMock()
        self.manager._answer_timer = MagicMock()

    def test_disabled_by_default(self):
        """When auto_advance_enabled is False, showing a question does not start timer."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg:
            mock_cfg.return_value = {
                "auto_advance_enabled": False,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            self.engine.start_work_cycle()
            self.manager.on_reviewer_question_shown(card=MagicMock())
            self.manager._question_timer.start.assert_not_called()

    def test_question_timeout_triggers_show_answer(self):
        """When enabled and in WORK mode, question timer starts and triggers show answer on timeout."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 15,
                "auto_answer_again_seconds": 6,
            }
            mock_mw.state = "review"
            mock_mw.reviewer = MagicMock()
            mock_mw.reviewer.state = "question"

            self.engine.start_work_cycle()
            self.manager.on_reviewer_question_shown(card=MagicMock())

            # Verify question timer started with 15000ms
            self.manager._question_timer.start.assert_called_once_with(15000)

            # Trigger timeout
            self.manager._on_question_timeout()
            self.assertTrue(self.manager._auto_question_timeout)
            mock_mw.reviewer._showAnswer.assert_called_once()

    def test_manual_flip_skips_answer_timer(self):
        """If user flips card manually, auto_question_timeout is False and answer timer is not started."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            mock_mw.reviewer = MagicMock()
            self.engine.start_work_cycle()

            # User is shown question
            self.manager.on_reviewer_question_shown(card=MagicMock())
            self.assertFalse(self.manager._auto_question_timeout)

            # User manually flips card to answer before timeout
            self.manager.on_reviewer_answer_shown(card=MagicMock())

            # Answer timer MUST NOT start
            self.manager._answer_timer.start.assert_not_called()
            self.assertFalse(self.manager._auto_question_timeout)

    def test_auto_flip_starts_answer_timer_and_grades_again(self):
        """If question timed out automatically, showing answer starts answer timer, and timeout grades Again."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            mock_mw.reviewer = MagicMock()
            mock_mw.reviewer.state = "answer"
            self.engine.start_work_cycle()

            # Simulate question timeout
            self.manager._auto_question_timeout = True

            # Answer shown
            self.manager.on_reviewer_answer_shown(card=MagicMock())

            # Answer timer must start with 8000ms
            self.manager._answer_timer.start.assert_called_once_with(8000)

            # Timeout expires
            self.manager._on_answer_timeout()
            mock_mw.reviewer._answerCard.assert_called_once_with(1)

    def test_answering_card_stops_timers_and_cleans_state(self):
        """When card is answered, timers are stopped and state is reset."""
        self.manager._auto_question_timeout = True
        self.manager._current_card_side = "answer"

        self.manager.on_reviewer_card_answered(card=MagicMock(), ease=3)

        self.assertFalse(self.manager._auto_question_timeout)
        self.assertIsNone(self.manager._current_card_side)
        self.manager._question_timer.stop.assert_called_once()
        self.manager._answer_timer.stop.assert_called_once()

    def test_inactivity_pause_freezes_timers(self):
        """When Pomodoro pauses due to inactivity, active timers are immediately stopped."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.start_work_cycle()
            self.manager.on_reviewer_question_shown(card=MagicMock())

            # Simulate inactivity pause
            self.engine.is_running = False
            self.engine.is_paused_by_inactivity = True
            self.manager.on_pomodoro_state_changed(self.engine)

            self.manager._question_timer.stop.assert_called()
            self.manager._answer_timer.stop.assert_called()

    def test_focus_loss_pause_freezes_timers(self):
        """When Pomodoro pauses due to focus loss, active timers are immediately stopped."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.start_work_cycle()

            self.engine.pause_for_focus_loss()
            self.manager.on_pomodoro_state_changed(self.engine)

            self.manager._question_timer.stop.assert_called()
            self.manager._answer_timer.stop.assert_called()

    def test_resume_from_pause_restarts_timer(self):
        """When Pomodoro resumes WORK, timer restarts for the current card side."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.start_work_cycle()
            self.manager._current_card_side = "question"

            # Inactivity pauses
            self.engine.is_running = False
            self.engine.is_paused_by_inactivity = True
            self.manager.on_pomodoro_state_changed(self.engine)

            # User returns, pomodoro resumes
            self.engine.is_running = True
            self.engine.is_paused_by_inactivity = False
            self.manager.on_pomodoro_state_changed(self.engine)

            # Question timer restarted
            self.manager._question_timer.start.assert_called_with(20000)

    def test_break_mode_ignores_auto_advance(self):
        """Auto advance does not operate during BREAK or LONG_BREAK mode."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.state = PomodoroState.BREAK
            self.engine.is_running = True

            self.manager.on_reviewer_question_shown(card=MagicMock())
            self.manager._question_timer.start.assert_not_called()

    def test_get_countdown_info_question(self):
        """get_countdown_info reports active question countdown when question is showing."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.start_work_cycle()
            self.manager.on_reviewer_question_shown(card=MagicMock())

            info = self.manager.get_countdown_info()
            self.assertTrue(info["enabled"])
            self.assertTrue(info["active"])
            self.assertEqual(info["side"], "question")
            self.assertGreaterEqual(info["remaining_seconds"], 19)
            self.assertEqual(info["total_seconds"], 20)

    def test_get_countdown_info_answer_auto_vs_manual(self):
        """get_countdown_info is active only if question timed out automatically."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.start_work_cycle()

            # Case A: Manual flip -> Not active on answer
            self.manager.on_reviewer_question_shown(card=MagicMock())
            self.manager.on_reviewer_answer_shown(card=MagicMock())
            info_manual = self.manager.get_countdown_info()
            self.assertFalse(info_manual["active"])

            # Case B: Auto timeout flip -> Active on answer
            mock_mw.reviewer.state = "question"
            self.manager.on_reviewer_question_shown(card=MagicMock())
            self.manager._on_question_timeout()
            self.manager.on_reviewer_answer_shown(card=MagicMock())
            info_auto = self.manager.get_countdown_info()
            self.assertTrue(info_auto["active"])
            self.assertEqual(info_auto["side"], "answer")
            self.assertGreaterEqual(info_auto["remaining_seconds"], 7)
            self.assertEqual(info_auto["total_seconds"], 8)

    def test_get_countdown_info_inactive_when_paused(self):
        """get_countdown_info returns active=False if Pomodoro is paused or inactive."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.engine.start_work_cycle()
            self.manager.on_reviewer_question_shown(card=MagicMock())

            # Pause engine
            self.engine.is_running = False
            self.engine.is_paused_by_inactivity = True
            info = self.manager.get_countdown_info()
            self.assertFalse(info["active"])

    def test_auto_start_focus_on_review(self):
        """When auto_advance is enabled and pomodoro has not started, reviewing a card auto-starts focus."""
        with patch("modules.pomodoro.auto_advance.get_module_config") as mock_cfg, \
             patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_cfg.return_value = {
                "auto_advance_enabled": True,
                "auto_show_answer_seconds": 20,
                "auto_answer_again_seconds": 8,
            }
            mock_mw.state = "review"
            self.assertFalse(self.engine.is_started)
            self.assertFalse(self.engine.is_running)

            self.manager.on_reviewer_question_shown(card=MagicMock())

            self.assertTrue(self.engine.is_started)
            self.assertTrue(self.engine.is_running)
            self.assertEqual(self.engine.state, PomodoroState.WORK)
            self.manager._question_timer.start.assert_called_once_with(20000)

    def test_trigger_show_answer_and_again_snake_case_fallback(self):
        """Reviewer methods fall back to snake_case (_show_answer, _answer_card) if camelCase is not present."""
        with patch("modules.pomodoro.auto_advance.mw") as mock_mw:
            mock_rev = MagicMock(spec=["_show_answer", "_answer_card"])
            mock_mw.reviewer = mock_rev

            self.manager._trigger_show_answer()
            mock_rev._show_answer.assert_called_once()

            self.manager._trigger_answer_again()
            mock_rev._answer_card.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
