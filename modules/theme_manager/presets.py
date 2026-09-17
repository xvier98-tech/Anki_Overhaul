# -*- coding: utf-8 -*-
"""
Theme presets and color palette definitions for Anki Desktop UI Overhaul.
Supports OLED Black, Nord Dark, Catppuccin Mocha, Dracula, Solarized Dark, Forest Night, Warm Paper, Clean Light.
"""

from typing import Dict, Any

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "oled_dark": {
        "name": "Midnight OLED (Preto Puro)",
        "bg_primary": "#000000",
        "bg_card": "#121316",
        "bg_card_hover": "#1c1e24",
        "accent": "#38bdf8",
        "accent_gradient": "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "border_color": "#27272a",
        "new_color": "#38bdf8",
        "learn_color": "#fb923c",
        "review_color": "#4ade80",
    },
    "nord_dark": {
        "name": "Nord Dark (Polar Ártico)",
        "bg_primary": "#242933",
        "bg_card": "#2e3440",
        "bg_card_hover": "#3b4252",
        "accent": "#88c0d0",
        "accent_gradient": "linear-gradient(135deg, #88c0d0 0%, #81a1c1 100%)",
        "text_primary": "#eceff4",
        "text_secondary": "#d8dee9",
        "border_color": "#434c5e",
        "new_color": "#81a1c1",
        "learn_color": "#ebcb8b",
        "review_color": "#a3be8c",
    },
    "catppuccin_mocha": {
        "name": "Catppuccin Mocha (Lavanda Suave)",
        "bg_primary": "#181825",
        "bg_card": "#1e1e2e",
        "bg_card_hover": "#313244",
        "accent": "#cba6f7",
        "accent_gradient": "linear-gradient(135deg, #cba6f7 0%, #b4befe 100%)",
        "text_primary": "#cdd6f4",
        "text_secondary": "#a6adc8",
        "border_color": "#45475a",
        "new_color": "#89b4fa",
        "learn_color": "#fab387",
        "review_color": "#a6e3a1",
    },
    "dracula": {
        "name": "Dracula (Alto Contraste)",
        "bg_primary": "#1e1f29",
        "bg_card": "#282a36",
        "bg_card_hover": "#44475a",
        "accent": "#bd93f9",
        "accent_gradient": "linear-gradient(135deg, #bd93f9 0%, #ff79c6 100%)",
        "text_primary": "#f8f8f2",
        "text_secondary": "#95a5d5",
        "border_color": "#44475a",
        "new_color": "#8be9fd",
        "learn_color": "#ffb86c",
        "review_color": "#50fa7b",
    },
    "solarized_dark": {
        "name": "Solarized Dark (Azul Petróleo)",
        "bg_primary": "#00212b",
        "bg_card": "#073642",
        "bg_card_hover": "#0a4756",
        "accent": "#2aa198",
        "accent_gradient": "linear-gradient(135deg, #2aa198 0%, #268bd2 100%)",
        "text_primary": "#93a1a1",
        "text_secondary": "#839496",
        "border_color": "#0d5565",
        "new_color": "#268bd2",
        "learn_color": "#cb4b16",
        "review_color": "#859900",
    },
    "forest_night": {
        "name": "Forest Night (Esmeralda Noturno)",
        "bg_primary": "#101d18",
        "bg_card": "#182a23",
        "bg_card_hover": "#223d32",
        "accent": "#34d399",
        "accent_gradient": "linear-gradient(135deg, #34d399 0%, #059669 100%)",
        "text_primary": "#f0fdf4",
        "text_secondary": "#86efac",
        "border_color": "#2d4f41",
        "new_color": "#38bdf8",
        "learn_color": "#fbbf24",
        "review_color": "#34d399",
    },
    "warm_paper": {
        "name": "Warm Paper / Sépia (Conforto Visual Claro)",
        "bg_primary": "#f8f1e5",
        "bg_card": "#fff9f0",
        "bg_card_hover": "#f3e8d5",
        "accent": "#b45309",
        "accent_gradient": "linear-gradient(135deg, #b45309 0%, #92400e 100%)",
        "text_primary": "#451a03",
        "text_secondary": "#572507",
        "border_color": "#e7d7c1",
        "new_color": "#0284c7",
        "learn_color": "#d97706",
        "review_color": "#15803d",
    },
    "clean_light": {
        "name": "Clean Modern Light",
        "bg_primary": "#f8fafc",
        "bg_card": "#ffffff",
        "bg_card_hover": "#f1f5f9",
        "accent": "#0078d4",
        "accent_gradient": "linear-gradient(135deg, #0078d4 0%, #005a9e 100%)",
        "text_primary": "#1e293b",
        "text_secondary": "#64748b",
        "border_color": "#e2e8f0",
        "new_color": "#0284c7",
        "learn_color": "#ea580c",
        "review_color": "#16a34a",
    },
}


def get_active_theme_colors(theme_config: Dict[str, Any]) -> Dict[str, str]:
    """Resolves active theme colors from selected preset or custom user palette."""
    preset_key = theme_config.get("preset", "oled_dark")
    if preset_key in THEME_PRESETS:
        colors = dict(THEME_PRESETS[preset_key])
    else:
        colors = dict(THEME_PRESETS["oled_dark"])

    # Apply custom color overrides if specified
    custom_overrides = theme_config.get("custom_overrides", {})
    if custom_overrides and isinstance(custom_overrides, dict):
        for k, v in custom_overrides.items():
            if v and isinstance(v, str):
                colors[k] = v

    return colors
