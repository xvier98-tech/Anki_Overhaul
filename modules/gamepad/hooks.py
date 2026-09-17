# -*- coding: utf-8 -*-
"""
Anki gui_hooks integration for Native Gamepad & Controller Support.
Initializes polling on profile load and cleanly shuts down on profile close.
"""

from typing import Optional, Any
try:
    from aqt import mw, gui_hooks
    from PyQt6.QtCore import QObject, QEvent
    from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit
except ImportError:
    mw = None
    gui_hooks = None
    QObject = object
    QEvent = object
    QApplication = None
    QLineEdit = None
    QTextEdit = None
    QPlainTextEdit = None

from .input_manager import GamepadInputManager
from .actions import GamepadActionDispatcher, get_default_bindings, qt_key_event_to_string
from .sounds import ensure_gamepad_sound_assets
try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config

_global_input_manager: Optional[GamepadInputManager] = None
_global_action_dispatcher: Optional[GamepadActionDispatcher] = None
_keyboard_filter: Optional[Any] = None


class GamepadGlobalKeyboardFilter(QObject):
    """Global event filter to execute actions mapped to keyboard keys (KEY:...) when in Reviewer or DeckBrowser."""

    def eventFilter(self, obj, event):
        try:
            if hasattr(event, "type") and hasattr(QEvent, "Type"):
                if event.type() == QEvent.Type.KeyPress:
                    # Do not intercept if user is typing in a text field
                    app = QApplication.instance() if QApplication else None
                    if app and hasattr(app, "focusWidget"):
                        focused = app.focusWidget()
                        if focused and QLineEdit and isinstance(focused, (QLineEdit, QTextEdit, QPlainTextEdit)):
                            return False

                    key_name = qt_key_event_to_string(event)
                    if key_name:
                        trigger = f"KEY:{key_name}"
                        dispatcher = get_gamepad_dispatcher()
                        if dispatcher and dispatcher.has_binding(trigger):
                            if dispatcher.get_active_dialog() or (mw and getattr(mw, "state", "") in ("review", "deckBrowser", "overview")):
                                if dispatcher.handle_button_press(trigger):
                                    return True
        except Exception:
            pass
        return False


def get_gamepad_manager() -> GamepadInputManager:
    global _global_input_manager
    if _global_input_manager is None:
        _global_input_manager = GamepadInputManager(mw if mw else None)
        _init_gamepad_subsystem()
    return _global_input_manager


def get_gamepad_dispatcher() -> GamepadActionDispatcher:
    global _global_action_dispatcher
    if _global_action_dispatcher is None:
        cfg = get_module_config("gamepad")
        bindings = cfg.get("bindings", get_default_bindings())
        _global_action_dispatcher = GamepadActionDispatcher(bindings)
    return _global_action_dispatcher


def set_active_dialog(dialog: Optional[Any]):
    """Registers the active modal dialog on the global GamepadActionDispatcher."""
    dispatcher = get_gamepad_dispatcher()
    if dispatcher:
        dispatcher.set_active_dialog(dialog)


def get_active_dialog() -> Optional[Any]:
    """Retrieves the active modal dialog from the global GamepadActionDispatcher."""
    dispatcher = get_gamepad_dispatcher()
    return dispatcher.get_active_dialog() if dispatcher else None


def _init_gamepad_subsystem():
    global _global_input_manager, _global_action_dispatcher
    if not _global_input_manager:
        return

    try:
        ensure_gamepad_sound_assets()
    except Exception:
        pass

    cfg = get_module_config("gamepad")
    _global_input_manager.deadzone = float(cfg.get("deadzone", 0.15))
    _global_input_manager.scroll_sensitivity = float(cfg.get("scroll_sensitivity", 50.0))
    _global_input_manager.trigger_threshold = float(cfg.get("trigger_threshold", 0.5))
    _global_input_manager.continuous_scroll_stick = cfg.get("continuous_scroll_stick", "right")

    dispatcher = get_gamepad_dispatcher()
    dispatcher.trigger_on_release = cfg.get("trigger_on_release", True)
    dispatcher.visual_intensity = cfg.get("visual_feedback_intensity", "moderate")

    # Wire button press, release and continuous scroll to dispatcher
    _global_input_manager.button_down.connect(dispatcher.handle_button_down)
    _global_input_manager.button_up.connect(dispatcher.handle_button_up)
    _global_input_manager.continuous_scroll.connect(dispatcher.continuous_scroll_webview)

    # Install global keyboard filter for actions mapped to keyboard keys
    global _keyboard_filter
    if QApplication and _keyboard_filter is None:
        try:
            app = QApplication.instance()
            if app and hasattr(app, "installEventFilter"):
                _keyboard_filter = GamepadGlobalKeyboardFilter()
                app.installEventFilter(_keyboard_filter)
        except Exception:
            pass


def on_profile_did_open():
    """Starts non-blocking gamepad polling when user opens Anki profile."""
    cfg = get_module_config("gamepad")
    if cfg.get("enabled", True):
        manager = get_gamepad_manager()
        manager.start_polling()


def on_profile_will_close():
    """Stops polling cleanly on profile close and cleans up global event filter."""
    global _keyboard_filter
    if _global_input_manager:
        _global_input_manager.stop_polling()
    if QApplication and _keyboard_filter:
        try:
            app = QApplication.instance()
            if app and hasattr(app, "removeEventFilter"):
                app.removeEventFilter(_keyboard_filter)
        except Exception:
            pass
        _keyboard_filter = None


def on_webview_js_message(handled: tuple, cmd: str, context: Any) -> tuple:
    """Captures gamepad bridge messages from DeckBrowser webview."""
    if not isinstance(cmd, str):
        return handled

    if cmd == "gamepad_ascend_topbar":
        dispatcher = get_gamepad_dispatcher()
        if dispatcher:
            dispatcher.ascend_to_topbar()
        return (True, None)

    elif cmd.startswith("gamepad_deck_focused:"):
        parts = cmd.split(":", 2)
        if len(parts) >= 3:
            try:
                idx = int(parts[1])
                deck_id = parts[2]
                dispatcher = get_gamepad_dispatcher()
                if dispatcher:
                    dispatcher.sync_deck_focus(idx, deck_id)
            except Exception:
                pass
        return (True, None)

    return handled


def setup_gamepad_hooks():
    """Registers profile lifecycle hooks with Anki."""
    if not mw or not gui_hooks:
        return

    gui_hooks.profile_did_open.append(on_profile_did_open)
    gui_hooks.profile_will_close.append(on_profile_will_close)
    if hasattr(gui_hooks, "webview_did_receive_js_message"):
        gui_hooks.webview_did_receive_js_message.append(on_webview_js_message)
