# -*- coding: utf-8 -*-
"""
Reviewer Auto-Advance Module for Obsidian Addon Suite (Pomodoro Focus Integration).

Business Logic:
1. Question Timeout: Automatically flips to answer if user doesn't flip within `auto_show_answer_seconds`.
   Marks `_auto_question_timeout = True`.
2. Conditional Answer Timeout:
   - If question timed out (`_auto_question_timeout == True`): Assumes user didn't know answer.
     Waits `auto_answer_again_seconds` and automatically grades as 'Again' (ease = 1).
   - If user revealed answer manually: `_auto_question_timeout == False`. The answer is NOT timed out,
     allowing the user to evaluate and grade at their own pace.
3. Inactivity & Pause Synchronization:
   - If Pomodoro pauses (due to inactivity, loss of focus, card editing, or manual pause),
     all auto-advance timers are immediately stopped to prevent runaway auto-advancing while away.
   - Resumes automatically when user returns and focus mode resumes.
"""

from typing import Optional, Any
import time

try:
    from PyQt6.QtCore import QTimer
    from aqt import mw
except ImportError:
    QTimer = None
    mw = None

try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config
    except ImportError:
        def get_module_config(mod_name: str):
            return {}

from .timer_engine import PomodoroEngine, PomodoroState


class ReviewerAutoAdvanceManager:
    """
    Coordinates smart automatic card advance in the Anki Reviewer,
    synchronized with Pomodoro focus and inactivity detection.
    """

    def __init__(self, engine: Optional[PomodoroEngine] = None):
        self.engine = engine
        self._auto_question_timeout: bool = False
        self._question_timer: Optional[Any] = None
        self._answer_timer: Optional[Any] = None
        self._current_card_side: Optional[str] = None  # 'question' or 'answer'
        self._card_side_start_time: float = 0.0

        if QTimer:
            self._question_timer = QTimer()
            self._question_timer.setSingleShot(True)
            self._question_timer.timeout.connect(self._on_question_timeout)

            self._answer_timer = QTimer()
            self._answer_timer.setSingleShot(True)
            self._answer_timer.timeout.connect(self._on_answer_timeout)

    def set_engine(self, engine: PomodoroEngine):
        self.engine = engine

    # --- Configuration Helpers ---

    def _is_enabled(self) -> bool:
        cfg = get_module_config("pomodoro")
        return bool(cfg.get("auto_advance_enabled", False))

    def _get_show_answer_seconds(self) -> int:
        cfg = get_module_config("pomodoro")
        return max(3, int(cfg.get("auto_show_answer_seconds", 20)))

    def _get_answer_again_seconds(self) -> int:
        cfg = get_module_config("pomodoro")
        return max(2, int(cfg.get("auto_answer_again_seconds", 8)))

    def _is_focus_active(self) -> bool:
        """Returns True only if Pomodoro is in active running WORK state and Anki is in Reviewer."""
        if not self.engine:
            return False

        # Must be in WORK phase
        is_work = (self.engine.state == PomodoroState.WORK) or (getattr(self.engine.state, "value", "") == "work")
        if not is_work or not self.engine.is_running:
            return False

        # Must not be paused by inactivity, focus loss, or editing
        if (
            getattr(self.engine, "is_paused_by_inactivity", False)
            or getattr(self.engine, "is_paused_by_loss_of_focus", False)
            or getattr(self.engine, "is_paused_by_editing", False)
        ):
            return False

        # Reviewer must be active
        if mw and hasattr(mw, "state") and mw.state != "review":
            return False

        return True

    def get_countdown_info(self) -> dict:
        """
        Returns real-time countdown state for visual HUD/FAB integration:
        {
            "enabled": bool,
            "active": bool,
            "side": Optional[str],         # "question", "answer", or None
            "remaining_seconds": int,
            "total_seconds": int,
            "auto_question_timeout": bool
        }
        """
        if not self._is_enabled() or not self._is_focus_active():
            return {
                "enabled": self._is_enabled(),
                "active": False,
                "side": self._current_card_side,
                "remaining_seconds": 0,
                "total_seconds": 0,
                "auto_question_timeout": self._auto_question_timeout,
            }

        if self._current_card_side == "question":
            total = self._get_show_answer_seconds()
            elapsed = max(0.0, time.time() - self._card_side_start_time)
            rem = max(0, int(round(total - elapsed)))
            return {
                "enabled": True,
                "active": True,
                "side": "question",
                "remaining_seconds": rem,
                "total_seconds": total,
                "auto_question_timeout": False,
            }
        elif self._current_card_side == "answer" and self._auto_question_timeout:
            total = self._get_answer_again_seconds()
            elapsed = max(0.0, time.time() - self._card_side_start_time)
            rem = max(0, int(round(total - elapsed)))
            return {
                "enabled": True,
                "active": True,
                "side": "answer",
                "remaining_seconds": rem,
                "total_seconds": total,
                "auto_question_timeout": True,
            }

        return {
            "enabled": self._is_enabled(),
            "active": False,
            "side": self._current_card_side,
            "remaining_seconds": 0,
            "total_seconds": 0,
            "auto_question_timeout": self._auto_question_timeout,
        }

    # --- Timer Control ---

    def stop_timers(self):
        """Immediately stops both question and answer auto-advance timers."""
        if self._question_timer and hasattr(self._question_timer, "stop"):
            self._question_timer.stop()
        if self._answer_timer and hasattr(self._answer_timer, "stop"):
            self._answer_timer.stop()

    def _notify_fab_update(self):
        """Notifies the Pomodoro FAB overlay to refresh its display immediately."""
        try:
            from .hooks import get_native_pomodoro_fab
            fab = get_native_pomodoro_fab()
            if fab:
                if hasattr(fab, "_update_auto_advance_display"):
                    fab._update_auto_advance_display()
                if hasattr(fab, "update_display"):
                    fab.update_display()
        except Exception:
            pass

    # --- Reviewer Event Handlers ---

    def on_reviewer_question_shown(self, card: Any):
        """Called when a card question is displayed in the Reviewer."""
        self.stop_timers()
        self._current_card_side = "question"
        self._card_side_start_time = time.time()
        self._auto_question_timeout = False

        if not self._is_enabled():
            self._notify_fab_update()
            return

        # If user is in Reviewer with auto-advance enabled and pomodoro has not started yet,
        # automatically start the focus cycle so the timer and auto-advance run seamlessly.
        if (
            self.engine
            and not self.engine.is_started
            and self.engine.state not in (PomodoroState.BREAK, PomodoroState.LONG_BREAK)
        ):
            self.engine.start_work_cycle()

        if not self._is_focus_active():
            self._notify_fab_update()
            return

        timeout_sec = self._get_show_answer_seconds()
        if self._question_timer and hasattr(self._question_timer, "start"):
            self._question_timer.start(int(timeout_sec * 1000))
        self._notify_fab_update()

    def on_reviewer_answer_shown(self, card: Any):
        """
        Called when the card answer is revealed.
        Starts answer timer ONLY IF question timed out automatically.
        """
        if self._question_timer and hasattr(self._question_timer, "stop"):
            self._question_timer.stop()

        self._current_card_side = "answer"
        self._card_side_start_time = time.time()

        if not self._is_enabled():
            self._notify_fab_update()
            return

        # Core Rule: Auto-grade Again ONLY if question timed out automatically!
        if not self._auto_question_timeout:
            # User manually pressed show answer: leave decision to user.
            self._notify_fab_update()
            return

        if not self._is_focus_active():
            self._notify_fab_update()
            return

        timeout_sec = self._get_answer_again_seconds()
        if self._answer_timer and hasattr(self._answer_timer, "start"):
            self._answer_timer.start(int(timeout_sec * 1000))
        self._notify_fab_update()

    def on_reviewer_card_answered(self, card: Any, ease: int):
        """Called when user or system answers a card."""
        self.stop_timers()
        self._current_card_side = None
        self._auto_question_timeout = False
        self._notify_fab_update()

    # --- Pomodoro & Inactivity Synchronization ---

    def on_pomodoro_state_changed(self, engine: PomodoroEngine):
        """
        Synchronizes timers with Pomodoro state changes:
        - If Pomodoro pauses (inactivity, focus loss, manual), freezes timers.
        - If Pomodoro resumes WORK, restarts countdown for current side.
        """
        self.engine = engine

        if not self._is_enabled():
            self.stop_timers()
            self._notify_fab_update()
            return

        if not self._is_focus_active():
            # Inactivity or pause: freeze everything immediately!
            self.stop_timers()
            self._notify_fab_update()
            return

        # Pomodoro is active and running in WORK mode.
        # Check if we should resume a timer for the current card side:
        if self._current_card_side == "question":
            timeout_sec = self._get_show_answer_seconds()
            if self._question_timer and hasattr(self._question_timer, "start"):
                self._question_timer.start(int(timeout_sec * 1000))
        elif self._current_card_side == "answer" and self._auto_question_timeout:
            timeout_sec = self._get_answer_again_seconds()
            if self._answer_timer and hasattr(self._answer_timer, "start"):
                self._answer_timer.start(int(timeout_sec * 1000))
        self._notify_fab_update()

    # --- Timeout Triggers ---

    def _on_question_timeout(self):
        """Triggered when question countdown expires."""
        if not self._is_enabled() or not self._is_focus_active():
            return

        # Ensure reviewer is still on question side
        if mw and hasattr(mw, "reviewer") and mw.reviewer:
            rev_state = getattr(mw.reviewer, "state", None)
            if rev_state != "question":
                return

        self._auto_question_timeout = True
        self._trigger_show_answer()

    def _on_answer_timeout(self):
        """Triggered when answer countdown expires (after auto question timeout)."""
        if not self._is_enabled() or not self._is_focus_active():
            return

        # Ensure reviewer is still on answer side
        if mw and hasattr(mw, "reviewer") and mw.reviewer:
            rev_state = getattr(mw.reviewer, "state", None)
            if rev_state != "answer":
                return

        self._trigger_answer_again()

    def _trigger_show_answer(self):
        """Safely invokes show answer in Reviewer across all Anki versions."""
        try:
            if mw and hasattr(mw, "reviewer") and mw.reviewer:
                rev = mw.reviewer
                if hasattr(rev, "_showAnswer"):
                    rev._showAnswer()
                elif hasattr(rev, "_show_answer"):
                    rev._show_answer()
                elif hasattr(rev, "show_answer"):
                    rev.show_answer()
                elif hasattr(rev, "show"):
                    rev.show()
        except Exception as e:
            print(f"[AutoAdvance] Error showing answer: {e}")

    def _trigger_answer_again(self):
        """Safely grades card with ease 1 (Again / Errei) across all Anki versions."""
        try:
            if mw and hasattr(mw, "reviewer") and mw.reviewer:
                rev = mw.reviewer
                if hasattr(rev, "_answerCard"):
                    rev._answerCard(1)
                elif hasattr(rev, "_answer_card"):
                    rev._answer_card(1)
                elif hasattr(rev, "answerCard"):
                    rev.answerCard(1)
                elif hasattr(rev, "answer_card"):
                    rev.answer_card(1)
        except Exception as e:
            print(f"[AutoAdvance] Error grading Again: {e}")


_global_auto_advance_manager: Optional[ReviewerAutoAdvanceManager] = None


def get_auto_advance_manager(engine: Optional[PomodoroEngine] = None) -> ReviewerAutoAdvanceManager:
    global _global_auto_advance_manager
    if _global_auto_advance_manager is None:
        _global_auto_advance_manager = ReviewerAutoAdvanceManager(engine)
    elif engine is not None and _global_auto_advance_manager.engine is None:
        _global_auto_advance_manager.set_engine(engine)
    return _global_auto_advance_manager
