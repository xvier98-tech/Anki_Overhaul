# -*- coding: utf-8 -*-
"""
Integration hooks for Anki Desktop (PyQt6 / gui_hooks).
Registers menus, context menus, and automated profile/sync events safely.
"""

try:
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QMenu
    from aqt import mw, gui_hooks
    from aqt.utils import showInfo
except ImportError:
    # Standalone mock for testing environment without PyQt6
    mw = None
    gui_hooks = None
    QAction = object
    QMenu = object

from .priority_dialog import PriorityManagerDialog
from .set_priority_modal import SetPriorityModal
from ..core.reorder import run_reorder_with_ui
from ..utils.config_manager import get_config


def show_priority_manager_dialog() -> None:
    """Opens the main priority manager dialog."""
    if not mw:
        return
    dialog = PriorityManagerDialog(mw)
    dialog.exec()


def on_deck_browser_context_menu(menu: QMenu, deck_id: int) -> None:
    """
    Hook called when right-clicking a deck or opening the gear menu in the deck browser.
    Appends the 'Definir Prioridade...' action.
    """
    action = QAction("🎯 Definir Prioridade de Novos...", menu)
    action.triggered.connect(lambda: open_set_priority_modal(deck_id))
    menu.addAction(action)


def open_set_priority_modal(deck_id: int) -> None:
    """Opens the quick priority editor for a specific deck."""
    if not mw:
        return
    modal = SetPriorityModal(mw, deck_id)
    modal.exec()


def on_profile_did_open() -> None:
    """Auto reorder on profile load if configured."""
    config = get_config()
    if config.get("auto_reorder_on_profile_open", False):
        run_reorder_with_ui(interactive=False)


def on_sync_did_finish() -> None:
    """Auto reorder after sync if configured."""
    config = get_config()
    if config.get("auto_reorder_on_sync", False):
        run_reorder_with_ui(interactive=False)


def setup_hooks_and_menus() -> None:
    """Registers all UI actions, tools menu items, and background hooks."""
    if not mw or not gui_hooks:
        return

    # 1. Add item to Tools Menu
    action_manager = QAction("🎯 Prioridades e Blocos de Novos Cartões...", mw)
    action_manager.triggered.connect(show_priority_manager_dialog)
    mw.form.menuTools.addAction(action_manager)

    action_reorder_now = QAction("⚡ Reordenar Novos Cartões por Prioridade", mw)
    action_reorder_now.triggered.connect(lambda: run_reorder_with_ui(ask_confirmation=True, interactive=True))
    mw.form.menuTools.addAction(action_reorder_now)

    # 2. Hook into Deck Browser Context / Gear Menu
    gui_hooks.deck_browser_will_show_options_menu.append(on_deck_browser_context_menu)

    # 3. Hook into profile opened & sync finished events
    gui_hooks.profile_did_open.append(on_profile_did_open)
    gui_hooks.sync_did_finish.append(on_sync_did_finish)
