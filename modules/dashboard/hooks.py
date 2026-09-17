# -*- coding: utf-8 -*-
"""
Anki gui_hooks integration for Modern Stats Dashboard & Modern UI.
Places the dashboard directly below the deck tree in DeckBrowser and below the table in Overview.
"""

from typing import Optional

try:
    from PyQt6.QtGui import QAction
    from aqt import mw, gui_hooks
except ImportError:
    mw = None
    gui_hooks = None
    QAction = object

from .stats_engine import compute_dashboard_stats
from .renderer import render_dashboard_html, get_modern_ui_stylesheet
from .config_dialog import DashboardConfigDialog
try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config


def show_dashboard_config_dialog():
    """Opens the unified settings dialog focused on Dashboard tab."""
    if not mw:
        return
    try:
        from ..unified_config.settings_dialog import ObsidianSuiteHubDialog
        dialog = ObsidianSuiteHubDialog(mw)
        dialog.tabs.setCurrentIndex(1)  # Dashboard tab
        dialog.exec()
    except Exception:
        dialog = DashboardConfigDialog(mw)
        dialog.exec()


def on_overview_will_render_content(overview, content):
    """
    Hook called when rendering the Deck Overview screen.
    Applies modern UI enhancements and injects per-deck statistics below the table.
    """
    if not mw or not mw.col:
        return

    config = get_module_config("dashboard")
    modern_ui_css = get_modern_ui_stylesheet(config)

    hide_css = ""
    if config.get("hide_native_msg_box", False):
        hide_css = "<style>#deck-desc, .overview-msg, #overview-message { display: none !important; }</style>"
        if hasattr(content, "desc"):
            content.desc = ""

    dash_html = ""
    if config.get("enabled", True) and config.get("show_on_overview", True):
        try:
            current_did = mw.col.decks.get_current_id()
            include_new = config.get("include_new_in_remaining_total", True)
            stats = compute_dashboard_stats(
                col=mw.col,
                deck_id=current_did,
                include_new_in_remaining=include_new,
            )
            dash_html = render_dashboard_html(stats, config)
        except Exception as e:
            print(f"Modern Stats Dashboard Overview calculation error: {e}")

    # Inject modern UI styles and place dashboard below the overview table
    if hasattr(content, "table"):
        content.table = modern_ui_css + hide_css + content.table + dash_html
    elif hasattr(content, "desc"):
        content.desc = modern_ui_css + hide_css + (content.desc or "") + dash_html
    elif hasattr(content, "html"):
        content.html = modern_ui_css + hide_css + content.html + dash_html


def on_deck_browser_will_render_content(deck_browser, content):
    """
    Hook called when rendering the main Deck Browser (deck list).
    Places the Modern Stats Dashboard below the deck list in content.stats.
    """
    if not mw or not mw.col:
        return

    config = get_module_config("dashboard")
    modern_ui_css = get_modern_ui_stylesheet(config)

    dash_html = ""
    if config.get("enabled", True) and config.get("show_on_deck_browser", True):
        try:
            include_new = config.get("include_new_in_remaining_total", True)
            stats = compute_dashboard_stats(
                col=mw.col,
                deck_id=None,
                include_new_in_remaining=include_new,
            )
            dash_html = render_dashboard_html(stats, config)
        except Exception as e:
            print(f"Modern Stats Dashboard DeckBrowser calculation error: {e}")

    # Apply modern UI styling to deck tree
    if hasattr(content, "tree"):
        content.tree = modern_ui_css + content.tree
    elif hasattr(content, "html"):
        content.html = modern_ui_css + content.html

    # Place dashboard below the deck list in content.stats
    if hasattr(content, "stats"):
        content.stats = (content.stats or "") + dash_html
    elif hasattr(content, "html"):
        content.html = content.html + dash_html


def setup_dashboard_hooks():
    """Registers render hooks."""
    if not mw or not gui_hooks:
        return

    # Register render hooks
    gui_hooks.overview_will_render_content.append(on_overview_will_render_content)
    gui_hooks.deck_browser_will_render_content.append(on_deck_browser_will_render_content)
