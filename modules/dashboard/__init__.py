# -*- coding: utf-8 -*-
from .stats_engine import compute_dashboard_stats, DeckDashboardStats
from .renderer import render_dashboard_html
from .config_dialog import DashboardConfigDialog
from .hooks import setup_dashboard_hooks, show_dashboard_config_dialog

__all__ = [
    "compute_dashboard_stats",
    "DeckDashboardStats",
    "render_dashboard_html",
    "DashboardConfigDialog",
    "setup_dashboard_hooks",
    "show_dashboard_config_dialog",
]
