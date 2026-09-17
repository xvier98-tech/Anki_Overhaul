# -*- coding: utf-8 -*-
"""
Theme Injection Engine for Anki Desktop.
Applies customized palettes across all webviews (Toolbar, DeckBrowser, Overview, Reviewer, BottomWeb, Editor, Browser),
Qt application menus, status bar, dialog windows (AddCards, EditCurrent, Card Browser), and Windows 11 native title bar.
"""

import sys
from typing import Dict, Any, Optional

try:
    from PyQt6.QtGui import QColor, QPalette
    from aqt import mw, gui_hooks
except ImportError:
    mw = None
    gui_hooks = None
    QColor = object
    QPalette = object

from .presets import get_active_theme_colors
try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config


def set_windows_titlebar_color(bg_hex: str, hwnd: Optional[int] = None):
    """Sets the Windows 11 native title bar color to match the theme."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        if hwnd is None:
            if not mw:
                return
            hwnd = int(mw.winId())
        bg_clean = bg_hex.lstrip("#")
        if len(bg_clean) == 6:
            r = int(bg_clean[0:2], 16)
            g = int(bg_clean[2:4], 16)
            b = int(bg_clean[4:6], 16)
            colorref = r | (g << 8) | (b << 16)

            is_dark = (r * 0.299 + g * 0.587 + b * 0.114) < 128
            dark_flag = ctypes.c_int(1 if is_dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(dark_flag), 4
            )
            color_val = ctypes.c_int(colorref)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(color_val), 4
            )
    except Exception:
        pass


def get_perceptual_luminance(hex_color: str) -> float:
    """Calculates relative luminance (0.0 to 1.0) according to WCAG 2.1 specs."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        def srgb_to_lin(c):
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)
    except Exception:
        return 0.5


def get_contrast_ratio(val1, val2) -> float:
    """Calculates contrast ratio between two hex colors or relative luminance values."""
    lum1 = get_perceptual_luminance(val1) if isinstance(val1, str) else float(val1)
    lum2 = get_perceptual_luminance(val2) if isinstance(val2, str) else float(val2)
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return (l_max + 0.05) / (l_min + 0.05)


def is_light_color(hex_color: str) -> bool:
    """Returns True if hex color is perceptually light (relative luminance > 0.40)."""
    return get_perceptual_luminance(hex_color) > 0.40


def get_accessible_text_color(bg_hex: str, dark_color: str = "#0f172a", light_color: str = "#ffffff") -> str:
    """Returns high-contrast text color (dark or light) that maximizes WCAG contrast ratio on bg_hex."""
    bg_lum = get_perceptual_luminance(bg_hex)
    c_light = get_contrast_ratio(bg_lum, get_perceptual_luminance(light_color))
    c_dark = get_contrast_ratio(bg_lum, get_perceptual_luminance(dark_color))
    return light_color if c_light >= c_dark else dark_color


def get_hover_text_color(bg_hover_hex: str, accent_hex: str, text_pri_hex: str) -> str:
    """Ensures hover text on buttons retains at least 4.0:1 contrast against bg_hover."""
    hover_lum = get_perceptual_luminance(bg_hover_hex)
    accent_lum = get_perceptual_luminance(accent_hex)
    ratio = get_contrast_ratio(hover_lum, accent_lum)
    if ratio >= 4.0:
        return accent_hex
    return get_accessible_text_color(bg_hover_hex, dark_color="#0f172a", light_color="#ffffff")


def get_light_tone(hex_color: str, factor: float = 0.75) -> str:
    """Returns a lighter / pastel version of the hex color for readable text contrast."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        try:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = int(r + (255 - r) * factor)
            g = int(g + (255 - g) * factor)
            b = int(b + (255 - b) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            pass
    return "#ffffff"


def generate_global_theme_css(colors: Dict[str, str], config: Optional[Dict[str, Any]] = None) -> str:
    """Generates global CSS variable stylesheet to inject into all webviews."""
    bg_pri = colors.get("bg_primary", "#000000")
    bg_card = colors.get("bg_card", "#121316")
    bg_hover = colors.get("bg_card_hover", "#1c1e24")
    accent = colors.get("accent", "#38bdf8")
    accent_grad = colors.get("accent_gradient", "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)")
    text_pri = colors.get("text_primary", "#f8fafc")
    text_sec = colors.get("text_secondary", "#94a3b8")
    border = colors.get("border_color", "#27272a")
    new_c = colors.get("new_color", "#38bdf8")
    learn_c = colors.get("learn_color", "#fb923c")
    rev_c = colors.get("review_color", "#4ade80")

    if config is None:
        try:
            from ...utils.config_manager import get_module_config
            config = get_module_config("theme")
        except Exception:
            config = {}

    ans_cfg = config.get("answer_buttons", {})
    c_again = ans_cfg.get("again_color", "#ef4444")
    c_hard = ans_cfg.get("hard_color", "#b45309")
    c_good = ans_cfg.get("good_color", "#16a34a")
    c_easy = ans_cfg.get("easy_color", "#2563eb")

    btn_scale = float(ans_cfg.get("button_scale", 1.15))
    btn_pad_y = int(8 * btn_scale)
    btn_pad_x = int(22 * btn_scale)
    btn_min_w = int(88 * btn_scale)
    btn_font_sz = round(13.5 * btn_scale, 1)
    btn_rad = int(14 * btn_scale)
    ansbut_pad_y = int(10 * btn_scale)
    ansbut_pad_x = int(36 * btn_scale)
    ansbut_min_w = int(140 * btn_scale)
    ansbut_font_sz = round(15.0 * btn_scale, 1)
    ansbut_rad = int(16 * btn_scale)

    btn_study_text = get_accessible_text_color(accent)
    btn_ans_text = get_accessible_text_color(accent)

    # High-contrast label colors for answer buttons (white for dark/saturated tones, dark for pastel tones)
    t_again = "#0f172a" if is_light_color(c_again) else "#ffffff"
    t_hard = "#0f172a" if is_light_color(c_hard) else "#ffffff"
    t_good = "#0f172a" if is_light_color(c_good) else "#ffffff"
    t_easy = "#0f172a" if is_light_color(c_easy) else "#ffffff"

    # Review interval time labels (.nobold, .stattxt) are positioned ABOVE the buttons (top: -3px; translate(-50%, -100%)).
    # They hover directly over the reviewer bottom bar / canvas (bg_pri).
    # Their text color MUST be computed against bg_pri to guarantee 100% contrast in both dark and light themes.
    is_theme_light = is_light_color(bg_pri)
    ease_sub_text = "rgba(15, 23, 42, 0.88)" if is_theme_light else "rgba(255, 255, 255, 0.95)"
    ease_sub_shadow = "0 1px 2px rgba(255, 255, 255, 0.5)" if is_theme_light else "0 1px 2px rgba(0, 0, 0, 0.8)"

    sub_again = ease_sub_text
    sub_hard = ease_sub_text
    sub_good = ease_sub_text
    sub_easy = ease_sub_text

    hitem_hover_color = get_hover_text_color(bg_hover, accent, text_pri)
    c_label_card = get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_card))
    c_label_pri = get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_pri))
    field_label_color = accent if (c_label_card >= 4.5 and c_label_pri >= 4.5) else (text_pri if is_theme_light else get_accessible_text_color(bg_pri))

    try:
        ac_clean = accent.lstrip("#")
        if len(ac_clean) == 3:
            ac_clean = "".join(c * 2 for c in ac_clean)
        ar, ag, ab = int(ac_clean[0:2], 16), int(ac_clean[2:4], 16), int(ac_clean[4:6], 16)
    except Exception:
        ar, ag, ab = 56, 189, 248

    is_card_light = is_light_color(bg_card)
    tag_bg = f"rgba({ar}, {ag}, {ab}, 0.14)" if is_card_light else f"rgba({ar}, {ag}, {ab}, 0.20)"
    tag_border = f"rgba({ar}, {ag}, {ab}, 0.45)"
    c_tag_card = get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_card))
    tag_text = accent if c_tag_card >= 4.5 else get_accessible_text_color(bg_card)

    highlight_bg = f"rgba({ar}, {ag}, {ab}, 0.35)" if is_theme_light else f"rgba({ar}, {ag}, {ab}, 0.45)"
    highlight_fg = text_pri
    cm_selected_bg = f"rgba({ar}, {ag}, {ab}, 0.28)" if is_theme_light else f"rgba({ar}, {ag}, {ab}, 0.40)"
    selected_bg = cm_selected_bg
    selected_fg = text_pri
    cm_selection_color = accent
    cm_selection_text = btn_ans_text

    if is_theme_light:
        cm_syntax_rules = f"""
        /* High-contrast CodeMirror tokens for Light Themes (WCAG AAA >= 7:1) */
        .CodeMirror .cm-tag, .CodeMirror .cm-bracket,
        .cm-s-monokai .cm-tag, .cm-s-monokai .cm-bracket,
        .cm-s-default .cm-tag, .cm-s-default .cm-bracket {{
            color: #991b1b !important;
            font-weight: 700 !important;
        }}
        .CodeMirror .cm-attribute,
        .cm-s-monokai .cm-attribute,
        .cm-s-default .cm-attribute {{
            color: #14532d !important;
            font-weight: 600 !important;
        }}
        .CodeMirror .cm-string, .CodeMirror .cm-string-2,
        .cm-s-monokai .cm-string, .cm-s-monokai .cm-string-2,
        .cm-s-default .cm-string, .cm-s-default .cm-string-2 {{
            color: #78350f !important;
            font-weight: 500 !important;
        }}
        .CodeMirror .cm-keyword,
        .cm-s-monokai .cm-keyword,
        .cm-s-default .cm-keyword {{
            color: #581c87 !important;
            font-weight: 700 !important;
        }}
        .CodeMirror .cm-atom, .CodeMirror .cm-number,
        .cm-s-monokai .cm-atom, .cm-s-monokai .cm-number {{
            color: #1e3a8a !important;
        }}
        .CodeMirror .cm-comment,
        .cm-s-monokai .cm-comment {{
            color: #475569 !important;
            font-style: italic !important;
        }}
        """
    else:
        cm_syntax_rules = f"""
        /* Preserved high-contrast CodeMirror tokens for Dark Themes */
        .CodeMirror .cm-tag, .CodeMirror .cm-bracket {{
            color: #f87171 !important;
        }}
        .CodeMirror .cm-attribute {{
            color: #4ade80 !important;
        }}
        .CodeMirror .cm-string, .CodeMirror .cm-string-2 {{
            color: #fbbf24 !important;
        }}
        .CodeMirror .cm-keyword {{
            color: #c084fc !important;
        }}
        .CodeMirror .cm-atom, .CodeMirror .cm-number {{
            color: #60a5fa !important;
        }}
        .CodeMirror .cm-comment {{
            color: #94a3b8 !important;
        }}
        """

    return f"""
    <style id="anki-obsidian-suite-global-theme">
        :root, :root.night-mode, [data-bs-theme=dark], [data-bs-theme=light], body, html {{
            --suite-bg-primary: {bg_pri};
            --suite-bg-card: {bg_card};
            --suite-bg-hover: {bg_hover};
            --suite-accent: {accent};
            --suite-accent-gradient: {accent_grad};
            --suite-text-primary: {text_pri};
            --suite-text-secondary: {text_sec};
            --suite-border: {border};
            --suite-new: {new_c};
            --suite-learn: {learn_c};
            --suite-review: {rev_c};

            /* Overrides for Anki 24/25 native CSS tokens */
            --state-new: {new_c} !important;
            --state-learn: {learn_c} !important;
            --state-review: {rev_c} !important;
            --canvas: {bg_pri} !important;
            --canvas-elevated: {bg_card} !important;
            --canvas-overlay: {bg_card} !important;
            --canvas-inset: {bg_card} !important;
            --canvas-code: {bg_card} !important;
            --canvas-glass: {bg_card} !important;
            --fg: {text_pri} !important;
            --fg-subtle: {text_sec} !important;
            --fg-disabled: {text_sec} !important;
            --border: {border} !important;
            --border-subtle: {border} !important;
            --border-strong: {border} !important;
            --border-focus: {accent} !important;
            --button-bg: {bg_card} !important;
            --button-gradient-start: {bg_card} !important;
            --button-gradient-end: {bg_card} !important;
            --link: {accent} !important;
            --link-hover: {accent} !important;
            --fg-link: {accent} !important;

            /* Bootstrap 5 tokens for Editor & Components */
            --bs-body-bg: {bg_pri} !important;
            --bs-body-color: {text_pri} !important;
            --bs-tertiary-bg: {bg_card} !important;
            --bs-secondary-bg: {bg_card} !important;
            --bs-border-color: {border} !important;
            --bs-emphasis-color: {text_pri} !important;
            --bs-primary: {accent} !important;
            --text-fg: {text_pri} !important;
            --text-secondary: {text_sec} !important;
            --highlight-bg: {highlight_bg} !important;
            --highlight-fg: {highlight_fg} !important;
            --selected-bg: {selected_bg} !important;
            --selected-fg: {selected_fg} !important;
        }}

        html, body {{
            background-color: {bg_pri} !important;
            color: {text_pri} !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        }}

        /* Top Toolbar Background & Elements */
        #header, header, .header, nav, #top-bar, .top-bar,
        body.fancy .toolbar, body.fancy:not(.flat) .toolbar, .toolbar {{
            background-color: {bg_pri} !important;
            background: {bg_pri} !important;
            border-bottom: 1px solid {border} !important;
            box-shadow: none !important;
        }}

        .hitem, body.fancy:not(.flat) .hitem, body.fancy .hitem {{
            background: {bg_card} !important;
            background-color: {bg_card} !important;
            color: {text_pri} !important;
            border: 1px solid {border} !important;
            border-radius: 8px !important;
            padding: 5px 14px !important;
            margin: 2px 4px !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
            text-decoration: none !important;
        }}

        .hitem:hover, body.fancy .hitem:hover, body.fancy:not(.flat) .hitem:hover {{
            background: {bg_hover} !important;
            background-color: {bg_hover} !important;
            border-color: {accent} !important;
            color: {hitem_hover_color} !important;
            text-decoration: none !important;
        }}

        /* Action Buttons */
        button#study, #study, .study-btn {{
            background: {accent_grad} !important;
            color: {btn_study_text} !important;
            border: none !important;
            border-radius: 22px !important;
            padding: 9px 32px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            cursor: pointer !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.18s ease !important;
            margin: 10px auto !important;
        }}
        button#study:hover, #study:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45) !important;
            filter: brightness(1.1) !important;
        }}

        /* =======================================================
           CARD EDITOR & EDIT CURRENT & ADD CARDS WEB COMPONENTS
           ======================================================= */
        #top-area, .editor-toolbar, .editor-toolbar-container, .toolbar-container, .rich-text-toolbar {{
            background-color: {bg_pri} !important;
            border-bottom: 1px solid {border} !important;
        }}

        #top-area button, .editor-toolbar button, .rich-text-toolbar button, .linkb, button.linkb, button.topbut, .topbut {{
            background: {bg_card} !important;
            color: {text_pri} !important;
            border: 1px solid {border} !important;
            border-radius: 6px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            vertical-align: middle !important;
            box-sizing: border-box !important;
            padding: 3px 8px !important;
            min-height: 28px !important;
            line-height: 1 !important;
            margin: 1px 2px !important;
        }}

        #top-area button:hover, .editor-toolbar button:hover, .rich-text-toolbar button:hover, .linkb:hover, button.linkb:hover, button.topbut:hover {{
            background: {bg_hover} !important;
            color: {hitem_hover_color} !important;
            border-color: {accent} !important;
        }}

        #top-area button img, #top-area button svg,
        .editor-toolbar button img, .editor-toolbar button svg,
        .topbut img, .linkb img {{
            vertical-align: middle !important;
            margin: auto !important;
            display: inline-block !important;
        }}

        #fields, .fields-container {{
            background-color: {bg_pri} !important;
            color: {text_pri} !important;
        }}

        .field-container, .field-wrapper, .editor-field, .rich-text-input, .plain-text-input {{
            background-color: {bg_card} !important;
            color: {text_pri} !important;
            border: 1px solid {border} !important;
            border-radius: 8px !important;
            padding: 4px !important;
            margin-bottom: 8px !important;
        }}

        .field-container.focus, .field-container:focus-within, .editor-field.focus, .editor-field:focus-within {{
            border-color: {accent} !important;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important;
        }}

        .label-container {{
            background-color: {bg_pri} !important;
            border-bottom: 1px solid {border} !important;
        }}

        .label-name, .field-label, .field-name, .collapse-label, label, .field-state {{
            color: {field_label_color} !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            padding: 4px 6px !important;
        }}

        anki-editable, .rich-text-editable, .plain-text, .plain-text-input, .editing-area, .editor-field [contenteditable] {{
            background-color: {bg_card} !important;
            color: {text_pri} !important;
            -webkit-text-fill-color: {text_pri} !important;
            caret-color: {accent} !important;
            border-radius: 6px !important;
            padding: 6px 10px !important;
            min-height: 48px !important;
        }}

        /* Force high contrast text on all children of rich-text-input, rich-text-editable and anki-editable in Light DOM */
        .rich-text-input, .rich-text-input *,
        .rich-text-editable, .rich-text-editable *,
        anki-editable, anki-editable *,
        .plain-text-input, .plain-text-input *,
        .editing-area, .editing-area * {{
            color: {text_pri} !important;
            -webkit-text-fill-color: {text_pri} !important;
        }}

        anki-editable::selection, anki-editable *::selection,
        .rich-text-editable::selection, .rich-text-editable *::selection,
        .editor-field [contenteditable]::selection, .editor-field [contenteditable] *::selection {{
            background-color: {highlight_bg} !important;
            color: {highlight_fg} !important;
            -webkit-text-fill-color: {highlight_fg} !important;
        }}

        .rich-text-editable.empty::before, anki-editable.empty::before, .editor-field [contenteditable].empty::before {{
            color: {text_sec} !important;
            -webkit-text-fill-color: {text_sec} !important;
            opacity: 0.75 !important;
        }}

        /* CodeMirror / Plain-Text / HTML Editor Mode */
        .CodeMirror, .CodeMirror-scroll, .CodeMirror-sizer, .CodeMirror-lines, .CodeMirror-gutters {{
            background-color: {bg_card} !important;
            color: {text_pri} !important;
        }}
        .CodeMirror pre.CodeMirror-line, .CodeMirror pre.CodeMirror-line-like, .CodeMirror-lines * {{
            color: {text_pri};
        }}
        .CodeMirror-cursor {{
            border-left: 2px solid {accent} !important;
        }}
        .CodeMirror-gutters {{
            background-color: {bg_pri} !important;
            border-right: 1px solid {border} !important;
        }}
        .CodeMirror-linenumber {{
            color: {text_sec} !important;
        }}
        .CodeMirror-selected, .CodeMirror-focused .CodeMirror-selected, div.CodeMirror-selected {{
            background: {cm_selected_bg} !important;
        }}
        .CodeMirror-line::selection, .CodeMirror-line > span::selection, .CodeMirror-line > span > span::selection,
        .CodeMirror ::selection {{
            background-color: {cm_selection_color} !important;
            color: {cm_selection_text} !important;
        }}
        {cm_syntax_rules}

        /* Tags editor area */
        #tags-container, .tag-editor, .tags-container, .tag-editor-container {{
            background-color: {bg_card} !important;
            border: 1px solid {border} !important;
            border-radius: 8px !important;
            padding: 4px 8px !important;
            color: {text_pri} !important;
        }}

        .tag, .badge-tag {{
            background: {tag_bg} !important;
            color: {tag_text} !important;
            border: 1px solid {tag_border} !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            font-weight: 600 !important;
        }}

        input.tag-input, .tag-input {{
            background: transparent !important;
            color: {text_pri} !important;
            border: none !important;
            outline: none !important;
        }}

        /* =======================================================
           REVIEWER BOTTOM BAR & ANSWER BUTTONS THEMING
           ======================================================= */
        #outer, table#innertable {{
            background-color: {bg_pri} !important;
            border-top: 1px solid {border} !important;
        }}

        #middle {{
            padding: 6px 0 !important;
        }}

        /* Show Answer Button (#ansbut) */
        button#ansbut, #ansbut button, #ansbut {{
            background: {accent_grad} !important;
            color: {btn_ans_text} !important;
            border: none !important;
            border-radius: {ansbut_rad}px !important;
            padding: {ansbut_pad_y}px {ansbut_pad_x}px !important;
            min-width: {ansbut_min_w}px !important;
            font-size: {ansbut_font_sz}px !important;
            font-weight: 700 !important;
            cursor: pointer !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
            transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
            margin: 6px auto !important;
            display: inline-block !important;
        }}
        button#ansbut:hover, #ansbut button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(56, 189, 248, 0.45) !important;
            filter: brightness(1.1) !important;
        }}

        /* Answer Buttons (Again, Hard, Good, Easy) */
        button[data-ease="1"], button.ease1 {{
            background: {c_again} !important;
            color: {t_again} !important;
            border: 1.5px solid {c_again} !important;
            border-radius: {btn_rad}px !important;
            padding: {btn_pad_y}px {btn_pad_x}px !important;
            min-width: {btn_min_w}px !important;
            font-size: {btn_font_sz}px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.15s ease !important;
        }}
        button[data-ease="1"]:hover, button.ease1:hover {{
            filter: brightness(1.2) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4) !important;
        }}
        /* Review interval time labels positioned above buttons (Anki .nobold / .stattxt) */
        .nobold, .stattxt {{
            color: {ease_sub_text} !important;
            font-weight: 600 !important;
            text-shadow: {ease_sub_shadow} !important;
        }}
        button#ansbut .stattxt, #ansbut .stattxt {{
            color: {ease_sub_text} !important;
            font-weight: 600 !important;
            text-shadow: {ease_sub_shadow} !important;
        }}

        button[data-ease="1"] .nobold, button[data-ease="1"] .stattxt,
        button.ease1 .nobold, button.ease1 .stattxt {{
            color: {sub_again} !important;
            font-weight: 600 !important;
            text-shadow: {ease_sub_shadow} !important;
        }}

        button[data-ease="2"], button.ease2 {{
            background: {c_hard} !important;
            color: {t_hard} !important;
            border: 1.5px solid {c_hard} !important;
            border-radius: {btn_rad}px !important;
            padding: {btn_pad_y}px {btn_pad_x}px !important;
            min-width: {btn_min_w}px !important;
            font-size: {btn_font_sz}px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.15s ease !important;
        }}
        button[data-ease="2"]:hover, button.ease2:hover {{
            filter: brightness(1.2) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(180, 83, 9, 0.4) !important;
        }}
        button[data-ease="2"] .nobold, button[data-ease="2"] .stattxt,
        button.ease2 .nobold, button.ease2 .stattxt {{
            color: {sub_hard} !important;
            font-weight: 600 !important;
            text-shadow: {ease_sub_shadow} !important;
        }}

        button[data-ease="3"], button.ease3, button#defease {{
            background: {c_good} !important;
            color: {t_good} !important;
            border: 1.5px solid {c_good} !important;
            border-radius: {btn_rad}px !important;
            padding: {btn_pad_y}px {btn_pad_x}px !important;
            min-width: {btn_min_w}px !important;
            font-size: {btn_font_sz}px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.15s ease !important;
        }}
        button[data-ease="3"]:hover, button.ease3:hover, button#defease:hover {{
            filter: brightness(1.2) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(22, 163, 74, 0.4) !important;
        }}
        button[data-ease="3"] .nobold, button[data-ease="3"] .stattxt,
        button.ease3 .nobold, button.ease3 .stattxt,
        button#defease .nobold, button#defease .stattxt {{
            color: {sub_good} !important;
            font-weight: 600 !important;
            text-shadow: {ease_sub_shadow} !important;
        }}

        button[data-ease="4"], button.ease4 {{
            background: {c_easy} !important;
            color: {t_easy} !important;
            border: 1.5px solid {c_easy} !important;
            border-radius: {btn_rad}px !important;
            padding: {btn_pad_y}px {btn_pad_x}px !important;
            min-width: {btn_min_w}px !important;
            font-size: {btn_font_sz}px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.15s ease !important;
        }}
        button[data-ease="4"]:hover, button.ease4:hover {{
            filter: brightness(1.2) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4) !important;
        }}
        button[data-ease="4"] .nobold, button[data-ease="4"] .stattxt,
        button.ease4 .nobold, button.ease4 .stattxt {{
            color: {sub_easy} !important;
            font-weight: 600 !important;
            text-shadow: {ease_sub_shadow} !important;
        }}

        /* General Button Rule (Excluding special toolbars and answer buttons) */
        button:not(#study):not(.card-action-btn):not(.pomo-btn-icon):not(.pomo-action-btn):not([data-ease]):not(.ease1):not(.ease2):not(.ease3):not(.ease4):not(#defease):not(#ansbut):not(#top-area button):not(.editor-toolbar button):not(.rich-text-toolbar button):not(.linkb):not(.topbut) {{
            background: {bg_card} !important;
            color: {text_pri} !important;
            border: 1px solid {border} !important;
            border-radius: 12px !important;
            padding: 6px 16px !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
        }}
        button:not(#study):not(.card-action-btn):not(.pomo-btn-icon):not(.pomo-action-btn):not([data-ease]):not(.ease1):not(.ease2):not(.ease3):not(.ease4):not(#defease):not(#ansbut):not(#top-area button):not(.editor-toolbar button):not(.rich-text-toolbar button):not(.linkb):not(.topbut):hover {{
            background: {bg_hover} !important;
            border-color: {accent} !important;
        }}

        /* Deck Table */
        table#deckbrowser-table, table.deck-table, table#overview-table {{
            border-collapse: separate !important;
            border-spacing: 0 4px !important;
        }}
        tr.deck, tr.deck-row {{
            transition: background 0.15s ease !important;
            border-radius: 8px !important;
        }}
        tr.deck:hover, tr.deck-row:hover {{
            background: {bg_hover} !important;
        }}

        /* Count badges */
        .count.new-count, .new-count, td.new, span.new-count {{
            color: {new_c} !important;
            font-weight: 700 !important;
        }}
        .count.learn-count, .learn-count, td.learn, span.learn-count {{
            color: {learn_c} !important;
            font-weight: 700 !important;
        }}
        .count.review-count, .review-count, td.review, span.review-count {{
            color: {rev_c} !important;
            font-weight: 700 !important;
        }}

        /* =======================================================
           CONGRATULATIONS / DECK FINISHED SCREEN THEMING
           ======================================================= */
        .congrats, #congrats, .congrats-container, .congrats-message, main.congrats {{
            background: {bg_card} !important;
            border: 1px solid {border} !important;
            border-radius: 20px !important;
            padding: 36px 40px !important;
            margin: 36px auto 24px auto !important;
            max-width: 580px !important;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35) !important;
            text-align: center !important;
            box-sizing: border-box !important;
        }}

        .congrats h1, .congrats h2, .congrats h3,
        #congrats h1, #congrats h2, #congrats h3 {{
            color: {accent} !important;
            font-size: 22px !important;
            font-weight: 800 !important;
            letter-spacing: -0.01em !important;
            margin-top: 0 !important;
            margin-bottom: 16px !important;
            line-height: 1.35 !important;
        }}

        .congrats p, #congrats p {{
            color: {text_sec} !important;
            font-size: 14.5px !important;
            line-height: 1.6 !important;
            margin: 10px 0 !important;
        }}

        .congrats a,
        .congrats a[href*="customStudy"],
        .congrats a[href*="unbury"],
        .congrats button,
        button[onclick*="customStudy"],
        button[onclick*="unbury"],
        button[onclick*="opts"],
        button[onclick*="studymore"] {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: {bg_card} !important;
            color: {text_pri} !important;
            border: 1px solid {border} !important;
            border-radius: 12px !important;
            padding: 6px 16px !important;
            margin: 4px 6px !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
            text-decoration: none !important;
            cursor: pointer !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.15s ease !important;
        }}

        .congrats a:hover,
        .congrats button:hover,
        button[onclick*="customStudy"]:hover,
        button[onclick*="unbury"]:hover,
        button[onclick*="opts"]:hover,
        button[onclick*="studymore"]:hover {{
            background: {bg_hover} !important;
            color: {hitem_hover_color} !important;
            border-color: {accent} !important;
            transform: translateY(-1px) !important;
            text-decoration: none !important;
        }}

        /* Highlight primary action on finished screen: Custom Study */
        .congrats a[href*="customStudy"],
        button[onclick*="customStudy"],
        button[onclick*="studymore"],
        .custom-study-btn {{
            background: {accent_grad} !important;
            color: {btn_study_text} !important;
            border: none !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
        }}
        .congrats a[href*="customStudy"]:hover,
        button[onclick*="customStudy"]:hover,
        button[onclick*="studymore"]:hover,
        .custom-study-btn:hover {{
            filter: brightness(1.1) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45) !important;
            color: {btn_study_text} !important;
        }}

        .congrats .description, .congrats-description {{
            background: {bg_pri} !important;
            color: {text_sec} !important;
            border: 1px solid {border} !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            margin-top: 20px !important;
            text-align: left !important;
            font-size: 13.5px !important;
            line-height: 1.5 !important;
        }}
    </style>

    <script id="anki-obsidian-suite-bridge-injector">
        (function() {{
            if (typeof pycmd === "function") {{
                window.pycmd = pycmd;
            }}
            if (typeof bridgeCommand === "function") {{
                window.bridgeCommand = bridgeCommand;
            }}
            window.sendPomoCommand = function(cmd) {{
                try {{
                    if (typeof pycmd === "function") {{
                        pycmd(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof window.pycmd === "function") {{
                        window.pycmd(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof bridgeCommand === "function") {{
                        bridgeCommand(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof window.bridgeCommand === "function") {{
                        window.bridgeCommand(cmd);
                        return;
                    }}
                }} catch(e) {{}}
            }};

            // Dynamic Editor Theme & Shadow DOM Contrast Fix (Strictly scoped to Editor webviews)
            var _isSyncingTheme = false;
            function syncEditorTheme() {{
                if (_isSyncingTheme) return;

                // Fast bailout: only execute on webviews that contain card editor components
                var editorHost = document.querySelector("anki-editable, .rich-text-editable, .plain-text-input, #fields, .fields-container, .field-container");
                if (!editorHost) return;

                _isSyncingTheme = true;
                try {{
                    var isLight = {str(is_theme_light).lower()};
                    var textPri = "{text_pri}";
                    var textSec = "{text_sec}";
                    var accent = "{accent}";
                    var highlightBg = "{highlight_bg}";
                    var highlightFg = "{highlight_fg}";

                    try {{
                        var docEl = document.documentElement;
                        if (isLight) {{
                            if (docEl.classList.contains("night-mode")) {{
                                docEl.classList.remove("night-mode");
                            }}
                            if (!docEl.classList.contains("light-mode")) {{
                                docEl.classList.add("light-mode");
                            }}
                            if (docEl.getAttribute("data-bs-theme") !== "light") {{
                                docEl.setAttribute("data-bs-theme", "light");
                            }}
                        }} else {{
                            if (docEl.classList.contains("light-mode")) {{
                                docEl.classList.remove("light-mode");
                            }}
                            if (!docEl.classList.contains("night-mode")) {{
                                docEl.classList.add("night-mode");
                            }}
                            if (docEl.getAttribute("data-bs-theme") !== "dark") {{
                                docEl.setAttribute("data-bs-theme", "dark");
                            }}
                        }}
                    }} catch(e) {{}}

                    function applyStylesToShadow(sr) {{
                        if (!sr) return;
                        try {{
                            // 1. Force overwrite of Svelte's userBase stylesheet if present
                            var userBase = sr.querySelector("style#userBase");
                            var userBaseCss = "anki-editable {{ color: " + textPri + " !important; -webkit-text-fill-color: " + textPri + " !important; }}";
                            if (userBase && userBase.textContent !== userBaseCss) {{
                                userBase.textContent = userBaseCss;
                            }}

                            // 2. Inject or update our dedicated high-priority shadow stylesheet
                            var styleId = "anki-suite-shadow-style";
                            var styleEl = sr.querySelector("#" + styleId);
                            if (!styleEl) {{
                                styleEl = document.createElement("style");
                                styleEl.id = styleId;
                                sr.appendChild(styleEl);
                            }}
                            if (sr.lastElementChild !== styleEl) {{
                                sr.appendChild(styleEl);
                            }}
                            var shadowCss = ":host, :host *, :host-context(*), " +
                                "anki-editable, anki-editable *, " +
                                ".rich-text-editable, .rich-text-editable *, " +
                                "div, p, span, strong, em, b, i, a, u, s, [contenteditable], [contenteditable] * {{ " +
                                "color: " + textPri + " !important; " +
                                "-webkit-text-fill-color: " + textPri + " !important; " +
                                "caret-color: " + accent + " !important; }} " +
                                "::selection, *::selection {{ background-color: " + highlightBg + " !important; color: " + highlightFg + " !important; -webkit-text-fill-color: " + highlightFg + " !important; }} " +
                                ".empty::before {{ color: " + textSec + " !important; -webkit-text-fill-color: " + textSec + " !important; }}";
                            if (styleEl.textContent !== shadowCss) {{
                                styleEl.textContent = shadowCss;
                            }}

                            // 3. Directly force style properties on anki-editable and all text nodes
                            var editables = sr.querySelectorAll("anki-editable, p, span, em, strong, div, a, b, i, u, s");
                            editables.forEach(function(node) {{
                                if (node.style.getPropertyValue("color") !== textPri) {{
                                    node.style.setProperty("color", textPri, "important");
                                }}
                                if (node.style.getPropertyValue("-webkit-text-fill-color") !== textPri) {{
                                    node.style.setProperty("-webkit-text-fill-color", textPri, "important");
                                }}
                            }});

                            // 4. Attach dedicated MutationObserver directly to this shadowRoot
                            if (!sr._obsidian_obs) {{
                                sr._obsidian_obs = new MutationObserver(function() {{
                                    applyStylesToShadow(sr);
                                }});
                                sr._obsidian_obs.observe(sr, {{ childList: true, subtree: true }});
                            }}

                            // 5. Recursively inspect nested shadow roots
                            applyShadowStyles(sr);
                        }} catch(e) {{}}
                    }}

                    function applyShadowStyles(root) {{
                        if (!root) return;
                        try {{
                            var hosts = root.querySelectorAll("anki-editable, .rich-text-editable, .rich-text-input, .plain-text-input, .field-container, .editing-area");
                            hosts.forEach(function(el) {{
                                if (el.shadowRoot) {{
                                    applyStylesToShadow(el.shadowRoot);
                                }}
                            }});
                        }} catch(e) {{}}
                    }}

                    applyShadowStyles(document);

                    // Enforce in Light DOM on all fields and inputs
                    try {{
                        var lightNodes = document.querySelectorAll(".rich-text-editable, .rich-text-editable *, .rich-text-input, .rich-text-input *, anki-editable, anki-editable *, .plain-text-input, .plain-text-input *");
                        lightNodes.forEach(function(ln) {{
                            if (ln.style.getPropertyValue("color") !== textPri) {{
                                ln.style.setProperty("color", textPri, "important");
                            }}
                            if (ln.style.getPropertyValue("-webkit-text-fill-color") !== textPri) {{
                                ln.style.setProperty("-webkit-text-fill-color", textPri, "important");
                            }}
                        }});
                    }} catch(e) {{}}
                }} finally {{
                    _isSyncingTheme = false;
                }}
            }}

            // Expose globally so Python hooks and timers can invoke it
            window.syncEditorTheme = syncEditorTheme;

            // Only attach listeners if this webview contains card editor components
            if (document.querySelector("anki-editable, .rich-text-editable, .plain-text-input, #fields, .fields-container, .field-container")) {{
                syncEditorTheme();
                document.addEventListener("focusin", syncEditorTheme, true);
                document.addEventListener("focusout", syncEditorTheme, true);
                document.addEventListener("input", syncEditorTheme, true);
                document.addEventListener("keyup", syncEditorTheme, true);

                if (!window._obsidianEditorSyncInterval) {{
                    window._obsidianEditorSyncInterval = setInterval(syncEditorTheme, 300);
                }}

                try {{
                    var obs = new MutationObserver(function() {{
                        syncEditorTheme();
                    }});
                    obs.observe(document.body || document.documentElement, {{
                        childList: true,
                        subtree: true
                    }});
                }} catch(e) {{}}
            }}
        }})();
    </script>
    """


def get_qt_dialog_stylesheet(colors: Dict[str, str]) -> str:
    """Generates complete Qt stylesheet for dialogs (AddCards, EditCurrent, Browser, etc.)."""
    bg_pri = colors.get("bg_primary", "#000000")
    bg_card = colors.get("bg_card", "#121316")
    bg_hover = colors.get("bg_card_hover", "#1c1e24")
    accent = colors.get("accent", "#38bdf8")
    text_pri = colors.get("text_primary", "#f8fafc")
    text_sec = colors.get("text_secondary", "#94a3b8")
    border = colors.get("border_color", "#27272a")

    btn_hover_color = get_hover_text_color(bg_hover, accent, text_pri)
    is_pri_light = is_light_color(bg_pri)
    disabled_text = text_sec if get_contrast_ratio(get_perceptual_luminance(text_sec), get_perceptual_luminance(bg_pri)) >= 3.0 else ("#64748b" if is_pri_light else "#94a3b8")
    tab_unselected_color = text_sec if get_contrast_ratio(get_perceptual_luminance(text_sec), get_perceptual_luminance(bg_card)) >= 4.0 else text_pri
    tab_selected_color = accent if get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_pri)) >= 4.0 else get_accessible_text_color(bg_pri)
    group_title_color = accent if get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_pri)) >= 4.0 else text_pri
    header_sec_color = accent if get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_pri)) >= 4.0 else text_pri
    selection_text_color = get_accessible_text_color(accent)

    return f"""
        QDialog, QMainWindow, QWidget#centralwidget, QWidget#scrollAreaWidgetContents,
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget,
        QScrollArea QWidget#qt_scrollarea_viewport, .QScrollArea,
        QTabWidget, QTabWidget > QWidget, QTabWidget QWidget#tab {{
            background-color: {bg_pri};
            color: {text_pri};
        }}
        QLabel, QCheckBox, QRadioButton {{
            color: {text_pri};
            background-color: transparent;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {border};
            border-radius: 4px;
            background-color: {bg_card};
        }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {accent};
        }}
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {accent};
            border-color: {accent};
        }}
        QCheckBox:disabled, QRadioButton:disabled, QLabel:disabled {{
            color: {disabled_text};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {bg_card};
            color: {text_pri};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 5px 8px;
            selection-background-color: {accent};
            selection-color: {selection_text_color};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
            border: 1px solid {accent};
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            background-color: {bg_hover};
            border: none;
            border-radius: 3px;
            width: 16px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {accent};
        }}
        QPushButton, QToolButton {{
            background-color: {bg_card};
            color: {text_pri};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 6px 14px;
            font-weight: 600;
        }}
        QPushButton:hover, QToolButton:hover {{
            background-color: {bg_hover};
            border-color: {accent};
            color: {btn_hover_color};
        }}
        QPushButton:pressed, QToolButton:pressed {{
            background-color: {bg_pri};
        }}
        QPushButton:disabled, QToolButton:disabled {{
            background-color: {bg_pri};
            color: {disabled_text};
            border-color: {border};
        }}
        QComboBox {{
            background-color: {bg_card};
            color: {text_pri};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px 10px;
        }}
        QComboBox:hover {{
            border-color: {accent};
        }}
        QComboBox QAbstractItemView {{
            background-color: {bg_card};
            color: {text_pri};
            border: 1px solid {border};
            selection-background-color: {bg_hover};
            selection-color: {accent};
        }}
        QTabWidget::pane {{
            border: 1px solid {border};
            background-color: {bg_pri};
            border-radius: 6px;
        }}
        QTabBar::tab {{
            background-color: {bg_card};
            color: {tab_unselected_color};
            border: 1px solid {border};
            padding: 7px 16px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {bg_pri};
            color: {tab_selected_color};
            border-bottom-color: {bg_pri};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {bg_hover};
            color: {text_pri};
        }}
        QGroupBox {{
            border: 1px solid {border};
            border-radius: 8px;
            margin-top: 14px;
            padding-top: 12px;
            font-weight: bold;
            color: {text_pri};
            background-color: {bg_pri};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 6px;
            background-color: {bg_pri};
            color: {group_title_color};
        }}
        QSlider::groove:horizontal {{
            border: 1px solid {border};
            height: 6px;
            background: {bg_card};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {accent};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {accent};
            border: 1px solid {border};
            width: 16px;
            margin-top: -6px;
            margin-bottom: -6px;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            filter: brightness(1.2);
        }}
        QScrollBar:vertical {{
            background-color: {bg_pri};
            width: 10px;
            margin: 0px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {border};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
            border: none;
        }}
        QScrollBar:horizontal {{
            background-color: {bg_pri};
            height: 10px;
            margin: 0px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {border};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {accent};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
            border: none;
        }}
        /* Tables & Lists (Browser Card Table, Review History & Dialogs) */
        QTableView, QTableWidget {{
            background-color: {bg_card};
            alternate-background-color: {bg_pri};
            color: {text_pri};
            border: 1px solid {border};
            gridline-color: {border};
            selection-background-color: {accent};
            selection-color: {selection_text_color};
            outline: none;
        }}
        QTableView::item {{
            color: {text_pri};
            padding: 3px 6px;
            border: none;
        }}
        QTableView::item:alternate {{
            background-color: {bg_pri};
            color: {text_pri};
        }}
        QTableView::item:selected {{
            background-color: {accent};
            color: {selection_text_color};
        }}
        QTableView::item:hover:!selected {{
            background-color: {bg_hover};
        }}

        /* Tree Views & Sidebar (Browser Sidebar & Tag Trees) */
        QTreeView, QTreeWidget, QTreeView#sidebar, QTreeView#sidebarTree, .SidebarTreeView {{
            background-color: {bg_card};
            color: {text_pri};
            border: 1px solid {border};
            outline: none;
            show-decoration-selected: 1;
        }}
        QTreeView::item {{
            color: {text_pri};
            padding: 4px 6px;
            border-radius: 4px;
        }}
        QTreeView::item:hover:!selected {{
            background-color: {bg_hover};
            color: {accent};
        }}
        QTreeView::item:selected {{
            background-color: {accent};
            color: {selection_text_color};
        }}
        QTreeView::branch {{
            background-color: {bg_card};
        }}
        QTreeView::branch:selected {{
            background-color: {accent};
        }}

        /* Table Headers */
        QHeaderView {{
            background-color: {bg_pri};
            border: none;
        }}
        QHeaderView::section {{
            background-color: {bg_pri};
            color: {header_sec_color};
            border: 1px solid {border};
            padding: 5px 8px;
            font-weight: bold;
        }}
        QHeaderView::section:checked {{
            background-color: {bg_hover};
            color: {accent};
        }}

        /* Splitters in Browser and Dialogs */
        QSplitter {{
            background-color: transparent;
        }}
        QSplitter::handle {{
            background-color: {border};
        }}
        QSplitter::handle:hover {{
            background-color: {accent};
        }}
        QSplitter::handle:horizontal {{
            width: 4px;
        }}
        QSplitter::handle:vertical {{
            height: 4px;
        }}

        /* Search Bar in Browser */
        QLineEdit#searchEdit {{
            background-color: {bg_card};
            color: {text_pri};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 5px 10px;
        }}
        QLineEdit#searchEdit:focus {{
            border-color: {accent};
        }}
    """


def apply_theme_to_anki():
    """Applies theme to main window, titlebar, Qt menus, toolbar, and webviews."""
    if not mw or not mw.col:
        return
    theme_cfg = get_module_config("theme")
    if not theme_cfg.get("enabled", True):
        return

    colors = get_active_theme_colors(theme_cfg)
    bg_pri = colors.get("bg_primary", "#000000")
    bg_card = colors.get("bg_card", "#121316")
    bg_hover = colors.get("bg_card_hover", "#1c1e24")
    accent = colors.get("accent", "#38bdf8")
    text_pri = colors.get("text_primary", "#f8fafc")
    text_sec = colors.get("text_secondary", "#94a3b8")
    border = colors.get("border_color", "#27272a")

    # 1. Native Title Bar for Main Window
    set_windows_titlebar_color(bg_pri)

    # 2. Qt Application Menubar & Main Window
    try:
        mw.setStyleSheet(f"""
            QMainWindow, QWidget#centralwidget {{
                background-color: {bg_pri};
                color: {text_pri};
            }}
            QMenuBar {{
                background-color: {bg_pri};
                color: {text_pri};
                border-bottom: 1px solid {border};
            }}
            QMenuBar::item {{
                background-color: {bg_pri};
                color: {text_pri};
                padding: 4px 10px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {bg_hover};
                color: {accent};
            }}
            QMenu {{
                background-color: {bg_card};
                color: {text_pri};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 24px 5px 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {bg_hover};
                color: {accent};
            }}
            QStatusBar {{
                background-color: {bg_pri};
                color: {text_sec};
                border-top: 1px solid {border};
            }}
        """)
    except Exception as e:
        print(f"Error applying Qt stylesheet: {e}")

    # 3. Redraw Top Toolbar with full HTML & CSS re-injection
    try:
        if hasattr(mw, "toolbar") and mw.toolbar:
            mw.toolbar.draw()
    except Exception:
        pass

    # 4. Refresh Active Content Webview
    try:
        if mw.state == "deckBrowser" and hasattr(mw, "deckBrowser") and mw.deckBrowser:
            mw.deckBrowser.refresh()
        elif mw.state == "overview" and hasattr(mw, "overview") and mw.overview:
            mw.overview.refresh()
            if hasattr(mw.overview, "web") and mw.overview.web:
                inject_theme_into_dynamic_webview(mw.overview.web)
    except Exception:
        pass


def inject_theme_into_dynamic_webview(web_view):
    """Injects theme CSS and variables into a dynamic / SvelteKit webview (e.g. congrats screen)."""
    if not web_view:
        return
    try:
        theme_cfg = get_module_config("theme")
        if not theme_cfg.get("enabled", True):
            return
        colors = get_active_theme_colors(theme_cfg)
        css_block = generate_global_theme_css(colors, theme_cfg)
        import json
        css_json = json.dumps(css_block)
        js = f"""
        (function() {{
            let target = document.body || document.documentElement;
            if (!target) return;
            let container = document.getElementById("anki-obsidian-suite-theme-container");
            if (!container) {{
                container = document.createElement("div");
                container.id = "anki-obsidian-suite-theme-container";
                target.appendChild(container);
            }}
            container.innerHTML = {css_json};
            let scripts = container.querySelectorAll("script");
            scripts.forEach(function(s) {{
                let fresh = document.createElement("script");
                if (s.id) fresh.id = s.id + "-exec";
                fresh.textContent = s.textContent;
                target.appendChild(fresh);
            }});
        }})();
        """
        web_view.eval(js)
    except Exception as e:
        pass


def on_webview_will_set_content(web_content, context):
    """Injects theme CSS and global bridge helpers into every webview in Anki."""
    theme_cfg = get_module_config("theme")
    if not theme_cfg.get("enabled", True):
        return

    colors = get_active_theme_colors(theme_cfg)
    css_block = generate_global_theme_css(colors, theme_cfg)
    web_content.head += css_block


def _sync_editor_theme_deferred(web_view):
    """Injects theme CSS and reinforces syncEditorTheme at staggered intervals to guarantee contrast after Svelte async note mounting."""
    if not web_view:
        return
    try:
        inject_theme_into_dynamic_webview(web_view)
        eval_js = "if (window.syncEditorTheme) window.syncEditorTheme();"
        web_view.eval(eval_js)
        try:
            from aqt.qt import QTimer
            for delay in (50, 150, 300, 600):
                QTimer.singleShot(delay, lambda w=web_view, js=eval_js: w.eval(js))
        except Exception:
            pass
    except Exception:
        pass


def on_editor_did_init(editor):
    """Styles the Card Editor and its parent dialog."""
    try:
        theme_cfg = get_module_config("theme")
        if not theme_cfg.get("enabled", True):
            return
        colors = get_active_theme_colors(theme_cfg)
        bg_pri = colors.get("bg_primary", "#000000")
        if hasattr(editor, "parentWindow") and editor.parentWindow:
            set_windows_titlebar_color(bg_pri, hwnd=int(editor.parentWindow.winId()))
            editor.parentWindow.setStyleSheet(get_qt_dialog_stylesheet(colors))
        if hasattr(editor, "web") and editor.web:
            _sync_editor_theme_deferred(editor.web)
    except Exception as e:
        print(f"Error styling editor on init: {e}")


def on_editor_did_load_note(editor):
    """Refreshes Editor styling when note changes."""
    try:
        if hasattr(editor, "web") and editor.web:
            _sync_editor_theme_deferred(editor.web)
        else:
            on_editor_did_init(editor)
    except Exception as e:
        on_editor_did_init(editor)


def on_add_cards_did_init(add_cards):
    """Styles Add Cards dialog."""
    try:
        theme_cfg = get_module_config("theme")
        if not theme_cfg.get("enabled", True):
            return
        colors = get_active_theme_colors(theme_cfg)
        bg_pri = colors.get("bg_primary", "#000000")
        set_windows_titlebar_color(bg_pri, hwnd=int(add_cards.winId()))
        add_cards.setStyleSheet(get_qt_dialog_stylesheet(colors))
        if hasattr(add_cards, "editor") and hasattr(add_cards.editor, "web") and add_cards.editor.web:
            _sync_editor_theme_deferred(add_cards.editor.web)
    except Exception as e:
        print(f"Error styling AddCards: {e}")


def apply_theme_to_browser_sidebar(browser, colors):
    """
    Applies dedicated theme styling, readable contrast and sensible minimum width
    to the Card Browser sidebar (QDockWidget, SidebarTreeView, SearchBar, Toolbar).
    """
    try:
        from PyQt6.QtGui import QColor, QPalette
        from PyQt6.QtCore import Qt

        bg_pri = colors.get("bg_primary", "#ffffff")
        bg_card = colors.get("bg_card", "#ffffff")
        bg_sec = colors.get("bg_secondary", "#f4f4f5")
        text_pri = colors.get("text_primary", "#000000")
        text_sec = colors.get("text_secondary", "#71717a")
        accent = colors.get("accent", "#38bdf8")
        border = colors.get("border", "#e4e4e7")
        bg_hover = colors.get("bg_hover", "#e4e4e7")
        selection_text_color = get_accessible_text_color(accent)

        # 1. DockWidget geometry & container styling
        if hasattr(browser, "sidebarDockWidget") and browser.sidebarDockWidget:
            dw = browser.sidebarDockWidget
            dw.setMinimumWidth(220)
            try:
                browser.resizeDocks([dw], [260], Qt.Orientation.Horizontal)
            except Exception:
                pass

            dw_qss = f"""
                QDockWidget#Sidebar, QDockWidget {{
                    background-color: {bg_sec};
                    color: {text_pri};
                    border-right: 1px solid {border};
                }}
                QDockWidget#Sidebar > QWidget {{
                    background-color: {bg_sec};
                    color: {text_pri};
                }}
                QToolBar {{
                    background-color: {bg_sec};
                    border: none;
                    spacing: 4px;
                    padding: 2px 4px;
                }}
                QToolButton {{
                    background-color: transparent;
                    color: {text_pri};
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 3px;
                }}
                QToolButton:hover {{
                    background-color: {bg_hover};
                    border-color: {border};
                }}
                QToolButton:checked {{
                    background-color: {accent};
                    color: {selection_text_color};
                    border-color: {accent};
                }}
                QLineEdit {{
                    background-color: {bg_card};
                    color: {text_pri};
                    border: 1px solid {border};
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border-color: {accent};
                }}
            """
            dw.setStyleSheet(dw_qss)

        # 2. SidebarTreeView styling and palette override
        if hasattr(browser, "sidebar") and browser.sidebar:
            sb = browser.sidebar

            # Palette override (ensures Base, Window, Text and Highlight roles match theme)
            pal = sb.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor(bg_sec))
            pal.setColor(QPalette.ColorRole.Window, QColor(bg_sec))
            pal.setColor(QPalette.ColorRole.Text, QColor(text_pri))
            pal.setColor(QPalette.ColorRole.WindowText, QColor(text_pri))
            pal.setColor(QPalette.ColorRole.Highlight, QColor(accent))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor(selection_text_color))
            sb.setPalette(pal)
            if hasattr(sb, "viewport") and sb.viewport():
                sb.viewport().setPalette(pal)

            sidebar_tree_qss = f"""
                QTreeView, SidebarTreeView {{
                    background-color: {bg_sec} !important;
                    alternate-background-color: {bg_sec} !important;
                    color: {text_pri} !important;
                    border: none !important;
                    outline: none !important;
                    show-decoration-selected: 1;
                    font-size: 13px;
                    padding: 4px 2px;
                }}
                QTreeView::item {{
                    color: {text_pri} !important;
                    padding: 4px 6px;
                    border-radius: 4px;
                    min-height: 22px;
                }}
                QTreeView::item:hover:!selected {{
                    background-color: {bg_hover} !important;
                    color: {accent} !important;
                }}
                QTreeView::item:selected {{
                    background-color: {accent} !important;
                    color: {selection_text_color} !important;
                }}
                QTreeView::branch {{
                    background-color: {bg_sec} !important;
                }}
                QTreeView::branch:selected {{
                    background-color: {accent} !important;
                }}
                QTreeView::branch:has-children:!has-siblings:closed,
                QTreeView::branch:closed:has-children:has-siblings {{
                    border-image: none;
                    background-color: {bg_sec} !important;
                }}
                QTreeView::branch:open:has-children:!has-siblings,
                QTreeView::branch:open:has-children:has-siblings {{
                    border-image: none;
                    background-color: {bg_sec} !important;
                }}
                QScrollBar:vertical {{
                    width: 8px;
                    background-color: transparent;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {border};
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {accent};
                }}
            """
            sb.setStyleSheet(sidebar_tree_qss)
            if hasattr(sb, "viewport") and sb.viewport():
                sb.viewport().setStyleSheet(f"background-color: {bg_sec} !important; color: {text_pri} !important;")

            # Override _setup_style so Anki's native theme_did_change does not revert to black
            sb._setup_style = lambda: apply_theme_to_browser_sidebar(browser, colors)

    except Exception as e:
        print(f"[ThemeManager] Error applying sidebar theme: {e}")


def fix_browser_layout_and_splitters(browser):
    """
    Ensures that the Card Browser's editor and sidebar are never collapsed or squished.
    Automatically un-squishes splitters (such as when the editor was squeezed into 50px)
    and enforces sensible minimum dimensions on the editor pane.
    """
    try:
        from PyQt6.QtWidgets import QSplitter
        from PyQt6.QtCore import Qt

        # 1. Enforce minimum dimensions on the embedded card editor
        if hasattr(browser, "editor"):
            ed = browser.editor
            if hasattr(ed, "widget") and ed.widget:
                ed.widget.setMinimumWidth(350)
                ed.widget.setMinimumHeight(220)

        # 2. Enforce minimum width on the sidebar dock widget
        if hasattr(browser, "sidebarDockWidget") and browser.sidebarDockWidget:
            dw = browser.sidebarDockWidget
            if not dw.isHidden():
                dw.setMinimumWidth(220)
                if dw.width() < 200:
                    try:
                        browser.resizeDocks([dw], [260], Qt.Orientation.Horizontal)
                    except Exception:
                        pass

        # 3. Inspect and normalize all splitters in the Browser window
        splitters = browser.findChildren(QSplitter)
        for splitter in splitters:
            splitter.setChildrenCollapsible(False)
            sizes = splitter.sizes()
            if len(sizes) == 2:
                total = sum(sizes)
                if total > 300:
                    # Check if second pane (editor) is squished (< 240px)
                    if sizes[1] < 240:
                        is_horiz = (splitter.orientation() == Qt.Orientation.Horizontal)
                        ratio = 0.42 if is_horiz else 0.45
                        editor_size = max(350, int(total * ratio))
                        table_size = total - editor_size
                        splitter.setSizes([table_size, editor_size])
                    # Check if first pane (sidebar or table) is squished (< 120px)
                    elif sizes[0] < 120:
                        first_size = max(180, int(total * 0.22))
                        second_size = total - first_size
                        splitter.setSizes([first_size, second_size])
    except Exception as e:
        print(f"[ThemeManager] Note on browser splitters: {e}")


def on_browser_will_show(browser):
    """Styles Card Browser window and its embedded editor."""
    try:
        theme_cfg = get_module_config("theme")
        if not theme_cfg.get("enabled", True):
            return
        colors = get_active_theme_colors(theme_cfg)
        bg_pri = colors.get("bg_primary", "#000000")
        set_windows_titlebar_color(bg_pri, hwnd=int(browser.winId()))
        browser.setStyleSheet(get_qt_dialog_stylesheet(colors))

        # Apply dedicated theme styling to sidebar
        apply_theme_to_browser_sidebar(browser, colors)

        # Enforce healthy splitter dimensions immediately and deferred (post-restoreState)
        fix_browser_layout_and_splitters(browser)
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: fix_browser_layout_and_splitters(browser))
            QTimer.singleShot(200, lambda: fix_browser_layout_and_splitters(browser))
            QTimer.singleShot(500, lambda: fix_browser_layout_and_splitters(browser))
            QTimer.singleShot(50, lambda: apply_theme_to_browser_sidebar(browser, colors))
            QTimer.singleShot(200, lambda: apply_theme_to_browser_sidebar(browser, colors))
            QTimer.singleShot(600, lambda: apply_theme_to_browser_sidebar(browser, colors))
        except Exception:
            pass

        if hasattr(browser, "editor") and hasattr(browser.editor, "web") and browser.editor.web:
            _sync_editor_theme_deferred(browser.editor.web)
    except Exception as e:
        print(f"Error styling Browser: {e}")


def setup_theme_hooks():
    """Registers theme webview hooks and dialog listeners."""
    if not mw or not gui_hooks:
        return
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    gui_hooks.editor_did_init.append(on_editor_did_init)
    gui_hooks.editor_did_load_note.append(on_editor_did_load_note)
    gui_hooks.add_cards_did_init.append(on_add_cards_did_init)
    gui_hooks.browser_will_show.append(on_browser_will_show)

    # Defense-in-depth: hook Overview._show_finished_screen to ensure theme is applied on deck completion
    try:
        from aqt.overview import Overview
        from anki.hooks import wrap
        def _after_show_finished_screen(ov_self):
            if hasattr(ov_self, "web") and ov_self.web:
                inject_theme_into_dynamic_webview(ov_self.web)
                if hasattr(mw, "progress") and hasattr(mw.progress, "timer"):
                    mw.progress.timer(120, lambda: inject_theme_into_dynamic_webview(ov_self.web), False)
        Overview._show_finished_screen = wrap(
            Overview._show_finished_screen, _after_show_finished_screen, "after"
        )
    except Exception:
        pass
