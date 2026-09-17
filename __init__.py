# -*- coding: utf-8 -*-
"""
Obsidian Addon Unified Suite for Anki Desktop.
Integrates:
- 🎨 Theme & Global Color Manager (Custom themes & palettes)
- 📊 Modern Stats Dashboard (Daily Goals, Limits, Deck Composition & Insights)
- 🍅 Adaptive Pomodoro Timer (Manual start, real-time seconds, Soft Break & Reviewer FAB)
- 🎯 Deck Priority & Closed Block New Card Sequencer
- 📝 Multiple Choice for Anki (AllInOne note types & templates)
- 🌐 AnkiConnect Local JSON-RPC Server
"""

try:
    from PyQt6.QtGui import QAction
    from aqt import mw, gui_hooks
except ImportError:
    mw = None
    gui_hooks = None
    QAction = object

from .modules.theme_manager import setup_theme_hooks, apply_theme_to_anki
from .modules.dashboard.hooks import setup_dashboard_hooks
from .modules.pomodoro.hooks import setup_pomodoro_hooks
from .modules.priority_sequencer.reorder import run_reorder_with_ui
from .modules.priority_sequencer.ui.set_priority_modal import SetPriorityModal
from .modules.multiple_choice import setup_multiple_choice
from .modules.ankiconnect import setup_ankiconnect
from .modules.gamepad import setup_gamepad_hooks
from .modules.unified_config.settings_dialog import ObsidianSuiteHubDialog


def show_unified_settings():
    """Opens the master settings hub dialog."""
    if not mw:
        return
    dialog = ObsidianSuiteHubDialog(mw)
    dialog.exec()


def open_set_priority_modal(deck_id: int):
    """Opens the quick priority modal for a deck."""
    if not mw:
        return
    modal = SetPriorityModal(mw, deck_id)
    modal.exec()


def on_deck_browser_context_menu(menu, deck_id: int):
    """Adds priority option to right-click deck menu."""
    action = QAction("🎯 Definir Prioridade de Novos...", menu)
    action.triggered.connect(lambda: open_set_priority_modal(deck_id))
    menu.addAction(action)


def initialize_addon_suite():
    """Initializes all submodules and registers unified menu actions."""
    if not mw or not gui_hooks:
        return

    # 1. Global Themes & Colors
    try:
        setup_theme_hooks()
        gui_hooks.profile_did_open.append(apply_theme_to_anki)
    except Exception as e:
        print(f"[Obsidian Addon] Theme Manager error: {e}")

    # 2. Modern Stats Dashboard
    try:
        setup_dashboard_hooks()
    except Exception as e:
        print(f"[Obsidian Addon] Dashboard error: {e}")

    # 3. Pomodoro Timer & Reviewer FAB
    try:
        setup_pomodoro_hooks()
    except Exception as e:
        print(f"[Obsidian Addon] Pomodoro error: {e}")

    # 4. Multiple Choice
    try:
        gui_hooks.profile_did_open.append(setup_multiple_choice)
    except Exception as e:
        print(f"[Obsidian Addon] Multiple Choice error: {e}")

    # 5. AnkiConnect
    try:
        setup_ankiconnect()
    except Exception as e:
        print(f"[Obsidian Addon] AnkiConnect error: {e}")

    # 6. Native Gamepad & Controller Support
    try:
        setup_gamepad_hooks()
    except Exception as e:
        print(f"[Obsidian Addon] Gamepad error: {e}")

    # 7. Card Editor Web Image Search & Inserter
    try:
        from .modules.image_search import setup_image_search_hooks
        setup_image_search_hooks()
    except Exception as e:
        print(f"[Obsidian Addon] Image Search error: {e}")

    # 8. Unified Menus in Ferramentas (Tools)
    try:
        action_hub = QAction("⚙️ Obsidian Addon Suite - Central de Configurações...", mw)
        action_hub.triggered.connect(show_unified_settings)
        mw.form.menuTools.addAction(action_hub)

        action_reorder = QAction("⚡ Reordenar Novos Cartões por Prioridade", mw)
        action_reorder.triggered.connect(lambda: run_reorder_with_ui(ask_confirmation=True))
        mw.form.menuTools.addAction(action_reorder)

        # Context menu in deck browser
        gui_hooks.deck_browser_will_show_options_menu.append(on_deck_browser_context_menu)
    except Exception as e:
        print(f"[Obsidian Addon] Menu registration error: {e}")


# Run initialization
initialize_addon_suite()
