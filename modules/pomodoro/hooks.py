# -*- coding: utf-8 -*-
"""
Anki gui_hooks integration for Floating Native Pomodoro FAB, Focus Fullscreen Mode & Reviewer HUD.
Uses Native PyQt6 Overlay for 100% reliable click response, zero IPC latency, and seamless operation.
"""

from typing import Optional, Tuple, Any
import os
import datetime

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QAction, QKeySequence, QShortcut
    from PyQt6.QtWidgets import QDialog
    import aqt
    from aqt import mw, gui_hooks
except ImportError:
    aqt = None
    mw = None
    gui_hooks = None
    QTimer = None
    QDialog = object
    QAction = object
    QShortcut = object
    QKeySequence = object

from .timer_engine import PomodoroEngine, PomodoroState
from .hud_manager import RestOverlayDialog
from .config_dialog import PomodoroConfigDialog
from .focus_guard import FocusGuard
from .auto_advance import get_auto_advance_manager
try:
    from .native_fab import NativePomodoroFab
except ImportError:
    NativePomodoroFab = None

try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config

_global_engine: Optional[PomodoroEngine] = None
_global_rest_dialog: Optional[RestOverlayDialog] = None
_global_native_fab: Optional[Any] = None
_global_focus_guard: Optional[FocusGuard] = None
_was_maximized: bool = True


def log_runtime_event(event_str: str):
    """Appends timestamped event into runtime_debug.log for forensic tracking."""
    try:
        addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(addon_dir, "runtime_debug.log")
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {event_str}\n")
    except Exception:
        pass


def get_pomodoro_engine() -> PomodoroEngine:
    global _global_engine
    if _global_engine is None:
        _global_engine = PomodoroEngine()
        _global_engine.on_tick_callback = _on_engine_tick
        _global_engine.on_state_change_callback = _on_engine_state_change
    return _global_engine


def get_native_pomodoro_fab() -> Optional[Any]:
    global _global_native_fab
    if _global_native_fab is None and mw and NativePomodoroFab:
        try:
            _global_native_fab = NativePomodoroFab(get_pomodoro_engine(), mw)
            log_runtime_event("NATIVE_FAB_INITIALIZED_SUCCESS")
        except Exception as e:
            log_runtime_event(f"NATIVE_FAB_INIT_ERROR: {e}")
            print(f"Error creating NativePomodoroFab: {e}")
    return _global_native_fab


def get_rest_dialog() -> Optional[RestOverlayDialog]:
    global _global_rest_dialog
    if _global_rest_dialog is None and mw:
        try:
            _global_rest_dialog = RestOverlayDialog(get_pomodoro_engine(), mw)
        except Exception as e:
            print(f"Error creating RestOverlayDialog: {e}")
    return _global_rest_dialog


def get_focus_guard() -> Optional[FocusGuard]:
    global _global_focus_guard
    if _global_focus_guard is None:
        try:
            _global_focus_guard = FocusGuard(get_pomodoro_engine())
            log_runtime_event("FOCUS_GUARD_INITIALIZED_SUCCESS")
        except Exception as e:
            log_runtime_event(f"FOCUS_GUARD_INIT_ERROR: {e}")
            print(f"Error creating FocusGuard: {e}")

    if _global_focus_guard is not None:
        target_mw = getattr(aqt, "mw", None) or mw
        if target_mw and not getattr(_global_focus_guard, "_installed_mw", False):
            try:
                target_mw.installEventFilter(_global_focus_guard)
                _global_focus_guard._installed_mw = True
                log_runtime_event("FOCUS_GUARD_MW_FILTER_INSTALLED")
            except Exception as e:
                log_runtime_event(f"FOCUS_GUARD_MW_FILTER_ERROR: {e}")

        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QGuiApplication
            app = QApplication.instance() or QGuiApplication.instance()
            if app and not getattr(_global_focus_guard, "_installed_app", False):
                app.installEventFilter(_global_focus_guard)
                _global_focus_guard._installed_app = True
        except Exception:
            pass

    return _global_focus_guard


def _on_engine_tick(engine: PomodoroEngine):
    get_focus_guard()
    if engine.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
        dialog = get_rest_dialog()
        if dialog:
            if not dialog.isVisible():
                dialog.show_centered()
            dialog.update_countdown()
    else:
        dialog = get_rest_dialog()
        if dialog and dialog.isVisible():
            dialog.hide()

    fab = get_native_pomodoro_fab()
    if fab and fab.isVisible():
        fab.update_display()


def _on_engine_state_change(engine: PomodoroEngine):
    try:
        get_auto_advance_manager(engine).on_pomodoro_state_changed(engine)
    except Exception as e:
        print(f"Error notifying auto advance on state change: {e}")

    if engine.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
        def _show_dialog():
            dialog = get_rest_dialog()
            if dialog:
                dialog.show_centered()
                dialog.update_countdown()
        if QTimer:
            QTimer.singleShot(120, _show_dialog)
        else:
            _show_dialog()
    else:
        dialog = get_rest_dialog()
        if dialog and dialog.isVisible():
            dialog.hide()

    update_active_fab()


def show_pomodoro_config_dialog():
    """Opens the unified settings dialog focused on Pomodoro tab safely on main GUI thread."""
    if not mw:
        return
    try:
        from ..unified_config.settings_dialog import ObsidianSuiteHubDialog
        dialog = ObsidianSuiteHubDialog(mw)
        dialog.tabs.setCurrentIndex(2)  # Pomodoro tab
        dialog.exec()
    except Exception as e:
        print(f"Error opening ObsidianSuiteHubDialog: {e}")
        try:
            dialog = PomodoroConfigDialog(get_pomodoro_engine(), mw)
            dialog.exec()
        except Exception as e2:
            print(f"Error opening PomodoroConfigDialog: {e2}")


def toggle_focus_fullscreen():
    """Toggles full screen focus mode for Anki main window."""
    global _was_maximized
    if not mw:
        return
    try:
        if mw.isFullScreen():
            if _was_maximized:
                mw.showMaximized()
            else:
                mw.showNormal()
        else:
            _was_maximized = mw.isMaximized()
            mw.showFullScreen()
        mw.activateWindow()
    except Exception as e:
        print(f"Error toggling fullscreen: {e}")
    _safe_delayed_update()


def on_escape_pressed():
    """Exits fullscreen if active when Escape key is pressed."""
    global _was_maximized
    if mw and mw.isFullScreen():
        try:
            if _was_maximized:
                mw.showMaximized()
            else:
                mw.showNormal()
            mw.activateWindow()
        except Exception as e:
            print(f"Error on escape exit fullscreen: {e}")
        _safe_delayed_update()


def update_active_fab():
    """Updates and ensures the Native Qt Floating FAB is shown and positioned correctly."""
    get_focus_guard()
    if not mw:
        return

    is_min = mw.isMinimized() if hasattr(mw, "isMinimized") and callable(mw.isMinimized) else False
    is_vis = mw.isVisible() if hasattr(mw, "isVisible") and callable(mw.isVisible) else True
    if is_min or not is_vis:
        fab = get_native_pomodoro_fab()
        if fab and fab.isVisible():
            fab.hide()
        return

    cfg = get_module_config("pomodoro")
    if not cfg.get("enabled", True):
        fab = get_native_pomodoro_fab()
        if fab and fab.isVisible():
            fab.hide()
        return

    fab = get_native_pomodoro_fab()
    if fab:
        fab.update_display()
        if not fab.isVisible():
            fab.show()
        is_active = mw.isActiveWindow() if hasattr(mw, "isActiveWindow") and callable(mw.isActiveWindow) else True
        fab_active = fab.isActiveWindow() if hasattr(fab, "isActiveWindow") and callable(fab.isActiveWindow) else False
        if is_active or fab_active:
            fab.raise_()


def _safe_delayed_update():
    """Performs immediate and delayed updates to catch window resize / state completion."""
    update_active_fab()
    if QTimer:
        QTimer.singleShot(60, update_active_fab)
        QTimer.singleShot(200, update_active_fab)


def on_card_will_show(text: str, card, kind: str) -> str:
    """Card hook keeping text clean while updating native overlay."""
    try:
        engine = get_pomodoro_engine()
        engine.on_card_shown()
        _safe_delayed_update()
    except Exception:
        pass
    return text


def on_deck_browser_rendered(deck_browser):
    _safe_delayed_update()


def on_overview_rendered(overview):
    _safe_delayed_update()


def on_reviewer_question_shown(card):
    engine = get_pomodoro_engine()
    engine.on_card_shown()
    guard = get_focus_guard()
    if guard:
        guard.on_card_shown_cursor_check()
    try:
        get_auto_advance_manager(engine).on_reviewer_question_shown(card)
    except Exception as e:
        print(f"Error in auto advance question shown: {e}")
    _safe_delayed_update()


def on_reviewer_answer_shown(card):
    engine = get_pomodoro_engine()
    engine.on_card_shown()
    try:
        get_auto_advance_manager(engine).on_reviewer_answer_shown(card)
    except Exception as e:
        print(f"Error in auto advance answer shown: {e}")
    _safe_delayed_update()


# Alias for backwards compatibility
on_reviewer_card_shown = on_reviewer_question_shown


def on_reviewer_card_answered(reviewer, card, ease: int):
    engine = get_pomodoro_engine()
    try:
        get_auto_advance_manager(engine).on_reviewer_card_answered(card, ease)
    except Exception as e:
        print(f"Error in auto advance card answered: {e}")
    deck_name = None
    if mw and mw.col:
        deck_obj = mw.col.decks.get(card.did)
        if deck_obj:
            deck_name = deck_obj.get("name")
    engine.on_card_answered(ease, deck_name=deck_name)


def on_anki_state_change(next_state: str, prev_state: str):
    engine = get_pomodoro_engine()
    in_reviewer = (next_state == "review")
    deck_name = None
    if in_reviewer and mw and mw.col:
        try:
            cur_did = mw.col.decks.get_current_id()
            deck_obj = mw.col.decks.get(cur_did)
            if deck_obj:
                deck_name = deck_obj.get("name")
        except Exception:
            pass
    engine.on_reviewer_state_changed(in_reviewer, deck_name=deck_name)
    _safe_delayed_update()


_registered_shortcuts = []


def on_profile_did_open():
    """Initializes and displays the Native Pomodoro FAB and installs Focus Guard when profile opens."""
    log_runtime_event("ANKI_PROFILE_OPENED: Initializing Native FAB & Focus Guard")
    get_focus_guard()
    _safe_delayed_update()


def on_editor_closed(editor=None):
    """Resumes pomodoro if paused by card editor."""
    engine = get_pomodoro_engine()
    if getattr(engine, "is_paused_by_editing", False):
        if hasattr(engine, "resume_from_editing"):
            engine.resume_from_editing(source="editor_closed")
        _safe_delayed_update()


def on_add_cards_closed(add_cards=None):
    """Resumes pomodoro if paused by Add Cards window."""
    engine = get_pomodoro_engine()
    if getattr(engine, "is_paused_by_editing", False):
        if hasattr(engine, "resume_from_editing"):
            engine.resume_from_editing(source="editor_closed")
        _safe_delayed_update()


def on_editor_did_init(editor):
    """Handles card editor initialization, connects close signal, and pauses Pomodoro if in WORK."""
    try:
        parent_win = getattr(editor, "parentWindow", None)
        if parent_win:
            if (QDialog is not object and isinstance(parent_win, QDialog)) or (
                hasattr(parent_win, "finished") and hasattr(parent_win.finished, "connect")
            ):
                if not getattr(parent_win, "_obsidian_pomodoro_connected", False):
                    parent_win.finished.connect(lambda *args: on_editor_closed(editor))
                    parent_win._obsidian_pomodoro_connected = True

        cfg = get_module_config("pomodoro")
        if not cfg.get("auto_pause_on_card_edit", True):
            return

        engine = get_pomodoro_engine()
        is_work = (engine.state == PomodoroState.WORK) or (getattr(engine.state, "value", "") == "work")
        if is_work and engine.is_running:
            if hasattr(engine, "pause_for_editing"):
                engine.pause_for_editing(source="card_editor")
            _safe_delayed_update()
    except Exception as e:
        print(f"Error in on_editor_did_init: {e}")


def on_add_cards_did_init(add_cards):
    """Handles Add Cards window opening, connects close signal, and pauses Pomodoro if in WORK."""
    try:
        if hasattr(add_cards, "finished") and hasattr(add_cards.finished, "connect"):
            if not getattr(add_cards, "_obsidian_pomodoro_connected", False):
                add_cards.finished.connect(lambda *args: on_add_cards_closed(add_cards))
                add_cards._obsidian_pomodoro_connected = True

        cfg = get_module_config("pomodoro")
        if not cfg.get("auto_pause_on_card_edit", True):
            return

        engine = get_pomodoro_engine()
        is_work = (engine.state == PomodoroState.WORK) or (getattr(engine.state, "value", "") == "work")
        if is_work and engine.is_running:
            if hasattr(engine, "pause_for_editing"):
                engine.pause_for_editing(source="add_cards")
            _safe_delayed_update()
    except Exception as e:
        print(f"Error in on_add_cards_did_init: {e}")


def on_editor_did_focus_field(note, current_field_idx: int) -> bool:
    """Registers user activity on editor field focus to prevent idle timeout."""
    try:
        engine = get_pomodoro_engine()
        if hasattr(engine, "register_user_activity"):
            engine.register_user_activity()
    except Exception as e:
        print(f"Error in on_editor_did_focus_field: {e}")
    return False


def setup_pomodoro_hooks():
    """Registers all Pomodoro hooks, native overlay lifecycle, focus guard and global shortcuts."""
    if not mw or not gui_hooks:
        return

    # Lifecycle & Render events
    gui_hooks.card_will_show.append(on_card_will_show)
    gui_hooks.deck_browser_did_render.append(on_deck_browser_rendered)
    gui_hooks.overview_did_render.append(on_overview_rendered)
    gui_hooks.reviewer_did_show_question.append(on_reviewer_question_shown)
    gui_hooks.reviewer_did_show_answer.append(on_reviewer_answer_shown)
    gui_hooks.reviewer_did_answer_card.append(on_reviewer_card_answered)
    gui_hooks.state_did_change.append(on_anki_state_change)
    gui_hooks.profile_did_open.append(on_profile_did_open)

    # Editor & Card Creation hooks
    if hasattr(gui_hooks, "editor_did_init"):
        gui_hooks.editor_did_init.append(on_editor_did_init)
    if hasattr(gui_hooks, "add_cards_did_init"):
        gui_hooks.add_cards_did_init.append(on_add_cards_did_init)
    if hasattr(gui_hooks, "editor_did_focus_field"):
        gui_hooks.editor_did_focus_field.append(on_editor_did_focus_field)

    # 1. Anti-Distraction & Focus Loss Guard
    try:
        get_focus_guard()
    except Exception as e:
        log_runtime_event(f"FOCUS_GUARD_DIRECT_INIT_ERROR: {e}")
        print(f"Error initializing FocusGuard in setup_pomodoro_hooks: {e}")

    # 2. Global Hotkeys & Esc Fullscreen Exit
    try:
        engine = get_pomodoro_engine()
        cfg = get_module_config("pomodoro")
        hotkeys = cfg.get("hotkeys", {})

        key_pause = hotkeys.get("toggle_pause", "Alt+P")
        shortcut_pause = QShortcut(QKeySequence(key_pause), mw)
        shortcut_pause.activated.connect(lambda: (engine.toggle_pause(), _safe_delayed_update()))
        _registered_shortcuts.append(shortcut_pause)

        key_skip = hotkeys.get("skip_to_break", "Alt+S")
        shortcut_skip = QShortcut(QKeySequence(key_skip), mw)
        shortcut_skip.activated.connect(lambda: (engine.skip_to_break(), _safe_delayed_update()))
        _registered_shortcuts.append(shortcut_skip)

        key_reset = hotkeys.get("reset_cycle", "Alt+R")
        shortcut_reset = QShortcut(QKeySequence(key_reset), mw)
        shortcut_reset.activated.connect(lambda: (engine.reset_current_phase(), _safe_delayed_update()))
        _registered_shortcuts.append(shortcut_reset)

        # Focus Mode Fullscreen shortcuts
        shortcut_esc = QShortcut(QKeySequence("Escape"), mw)
        shortcut_esc.activated.connect(on_escape_pressed)
        _registered_shortcuts.append(shortcut_esc)

        shortcut_f11 = QShortcut(QKeySequence("F11"), mw)
        shortcut_f11.activated.connect(toggle_focus_fullscreen)
        _registered_shortcuts.append(shortcut_f11)
    except Exception as e:
        print(f"Pomodoro hotkeys registration warning: {e}")
