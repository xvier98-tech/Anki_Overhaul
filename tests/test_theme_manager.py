# -*- coding: utf-8 -*-
"""
Unit tests for Theme Manager, CSS generation, Editor Toolbar alignment, and Answer Buttons.
"""

import unittest
from modules.theme_manager.engine import (
    generate_global_theme_css,
    get_light_tone,
    get_active_theme_colors,
    get_perceptual_luminance,
    get_contrast_ratio,
    is_light_color,
    get_accessible_text_color,
    get_hover_text_color,
    get_qt_dialog_stylesheet,
)
from modules.theme_manager.presets import THEME_PRESETS


class TestThemeManager(unittest.TestCase):

    def test_get_light_tone(self):
        # Red
        light_red = get_light_tone("#ef4444", 0.75)
        self.assertTrue(light_red.startswith("#"))
        self.assertNotEqual(light_red, "#ef4444")

        # Blue
        light_blue = get_light_tone("#2563eb", 0.75)
        self.assertTrue(light_blue.startswith("#"))

    def test_generate_global_theme_css_answer_buttons(self):
        colors = THEME_PRESETS["oled_dark"]
        config = {
            "answer_buttons": {
                "enabled": True,
                "again_color": "#ef4444",
                "hard_color": "#b45309",
                "good_color": "#16a34a",
                "easy_color": "#2563eb",
            }
        }
        css = generate_global_theme_css(colors, config)

        # Check for answer button ease rules
        self.assertIn('button[data-ease="1"]', css)
        self.assertIn('button[data-ease="2"]', css)
        self.assertIn('button[data-ease="3"]', css)
        self.assertIn('button[data-ease="4"]', css)
        self.assertIn("#ef4444", css)
        self.assertIn("#b45309", css)
        self.assertIn("#16a34a", css)
        self.assertIn("#2563eb", css)

    def test_editor_toolbar_alignment_rules(self):
        colors = THEME_PRESETS["nord_dark"]
        css = generate_global_theme_css(colors)

        # Check that editor toolbar buttons have explicit inline-flex / center alignment
        self.assertIn(".editor-toolbar button", css)
        self.assertIn("#top-area button", css)
        self.assertIn("display: inline-flex !important;", css)
        self.assertIn("align-items: center !important;", css)
        self.assertIn("justify-content: center !important;", css)

    def test_theme_presets_structure_and_switch(self):
        """Verify that THEME_PRESETS have valid color mappings and no 'colors' sub-key."""
        for preset_name, preset_data in THEME_PRESETS.items():
            self.assertIn("name", preset_data)
            self.assertIn("bg_primary", preset_data)
            self.assertIn("accent", preset_data)
            self.assertIn("text_primary", preset_data)
            # Guarantee that presets can be accessed directly without KeyError('colors')
            colors = preset_data.get("colors", preset_data)
            self.assertTrue(colors["bg_primary"].startswith("#"))

    def test_settings_dialog_on_preset_changed_logic(self):
        """Verify settings dialog _on_preset_changed updates color swatches without raising KeyError."""
        from modules.unified_config.settings_dialog import ObsidianSuiteHubDialog, ColorPickerButton

        dialog = ObsidianSuiteHubDialog()
        for preset_key in ("nord_dark", "dracula", "catppuccin_mocha", "warm_paper"):
            idx = dialog.combo_presets.findData(preset_key)
            self.assertGreaterEqual(idx, 0)
            dialog.combo_presets.setCurrentIndex(idx)
            # Execute change handler
            dialog._on_preset_changed()
            expected_bg = THEME_PRESETS[preset_key]["bg_primary"]
            self.assertEqual(dialog.color_buttons["bg_primary"].color_hex, expected_bg)

    def test_settings_dialog_tabs_and_i18n(self):
        """Verify settings dialog initializes General tab, language combo, and long interval spinbox."""
        from modules.unified_config.settings_dialog import ObsidianSuiteHubDialog
        dialog = ObsidianSuiteHubDialog()
        self.assertTrue(hasattr(dialog, "combo_lang"))
        self.assertTrue(hasattr(dialog, "spin_long_interval"))
        self.assertEqual(dialog.spin_long_interval.value(), 4)

    def test_contrast_ratio_wcag(self):
        """Verify WCAG 2.1 contrast formula calculations."""
        # Pure black and pure white have maximum contrast 21:1
        ratio_bw = get_contrast_ratio("#000000", "#ffffff")
        self.assertAlmostEqual(ratio_bw, 21.0, places=1)

        # Same colors have 1:1 contrast
        ratio_same = get_contrast_ratio("#123456", "#123456")
        self.assertAlmostEqual(ratio_same, 1.0, places=1)

        # Solarized Dark secondary text against bg_primary >= 4.5
        sd_bg = THEME_PRESETS["solarized_dark"]["bg_primary"]
        sd_sec = THEME_PRESETS["solarized_dark"]["text_secondary"]
        self.assertGreaterEqual(get_contrast_ratio(sd_bg, sd_sec), 4.5)

        # Warm Paper secondary text against bg_primary >= 4.5
        wp_bg = THEME_PRESETS["warm_paper"]["bg_primary"]
        wp_sec = THEME_PRESETS["warm_paper"]["text_secondary"]
        self.assertGreaterEqual(get_contrast_ratio(wp_bg, wp_sec), 4.5)

    def test_accessible_text_color(self):
        """Verify get_accessible_text_color chooses high-contrast text against any background."""
        # Against pure white, dark text should be chosen
        self.assertEqual(get_accessible_text_color("#ffffff"), "#0f172a")
        # Against pure black, light text should be chosen
        self.assertEqual(get_accessible_text_color("#000000"), "#ffffff")
        # Against light yellow/amber, dark text should be chosen
        self.assertEqual(get_accessible_text_color("#fef08a"), "#0f172a")

    def test_study_and_ansbut_contrast_in_css(self):
        """Verify #study and #ansbut use dynamic accessible text color."""
        # Light theme with light background/accent
        light_preset = dict(THEME_PRESETS["clean_light"])
        css_light = generate_global_theme_css(light_preset)
        expected_light_txt = get_accessible_text_color(light_preset["accent"])
        self.assertIn(f"color: {expected_light_txt} !important;", css_light)

        # Dark theme with dark accent
        dark_preset = dict(THEME_PRESETS["nord_dark"])
        css_dark = generate_global_theme_css(dark_preset)
        expected_dark_txt = get_accessible_text_color(dark_preset["accent"])
        self.assertIn(f"color: {expected_dark_txt} !important;", css_dark)

    def test_qt_dialog_stylesheet_contrast(self):
        """Verify Qt dialog stylesheet sets accessible colors on tabs and headers."""
        colors = THEME_PRESETS["warm_paper"]
        qss = get_qt_dialog_stylesheet(colors)
        self.assertIn("QTabBar::tab:selected", qss)
        self.assertIn("QHeaderView::section", qss)
        self.assertIn("QGroupBox::title", qss)

    def test_review_interval_time_labels_contrast(self):
        """Verify .nobold and .stattxt review interval labels have high contrast in both dark and light themes."""
        # 1. Dark theme (OLED): time texts floating above buttons must be bright white, NOT dark navy
        oled_colors = THEME_PRESETS["oled_dark"]
        css_oled = generate_global_theme_css(oled_colors)
        self.assertIn(".nobold, .stattxt", css_oled)
        self.assertIn("rgba(255, 255, 255,", css_oled)
        # Verify Again (ease 1) and Good (ease 3) have light text in dark theme
        self.assertIn('button[data-ease="1"] .nobold', css_oled)
        self.assertIn('button[data-ease="3"] .nobold', css_oled)
        self.assertIn('button.ease3 .nobold', css_oled)
        self.assertIn('button#defease .nobold', css_oled)

        # 2. Light theme (Clean Light): time texts floating above buttons must be dark charcoal
        light_colors = THEME_PRESETS["clean_light"]
        css_light = generate_global_theme_css(light_colors)
        self.assertIn("rgba(15, 23, 42,", css_light)

    def test_congratulations_screen_theming(self):
        """Verify .congrats, #congrats, and action buttons are properly themed in global CSS."""
        colors = THEME_PRESETS["catppuccin_mocha"]
        css = generate_global_theme_css(colors)

        # Tokens
        self.assertIn("--fg-link:", css)
        self.assertIn("--link-hover:", css)

        # Card container & selectors
        self.assertIn(".congrats, #congrats, .congrats-container, .congrats-message, main.congrats", css)
        self.assertIn(colors["bg_card"], css)
        self.assertIn(colors["border_color"], css)

        # Title & text styling
        self.assertIn(".congrats h1, .congrats h2, .congrats h3", css)
        self.assertIn(colors["accent"], css)
        self.assertIn(".congrats p, #congrats p", css)

        # Action buttons (custom study, unbury, opts)
        self.assertIn('.congrats a[href*="customStudy"]', css)
        self.assertIn('button[onclick*="customStudy"]', css)
        self.assertIn('button[onclick*="unbury"]', css)
        self.assertIn('button[onclick*="opts"]', css)

    def test_editor_contrast_and_accessibility_light_themes(self):
        """Verify editor fields and labels have WCAG 2.1 AA compliant contrast (>= 4.5:1) in light presets."""
        for preset_key in ("clean_light", "warm_paper"):
            preset = THEME_PRESETS[preset_key]
            css = generate_global_theme_css(preset)

            # Editor text color against background card & primary
            text_pri = preset["text_primary"]
            bg_card = preset["bg_card"]
            bg_pri = preset["bg_primary"]
            contrast_card = get_contrast_ratio(text_pri, bg_card)
            contrast_pri = get_contrast_ratio(text_pri, bg_pri)
            self.assertGreaterEqual(contrast_card, 4.5, f"Low contrast in {preset_key} text vs card")
            self.assertGreaterEqual(contrast_pri, 4.5, f"Low contrast in {preset_key} text vs primary")

            # Field labels, editable area, and CodeMirror selectors
            self.assertIn(".label-name", css)
            self.assertIn(".rich-text-input", css)
            self.assertIn("anki-editable, .rich-text-editable", css)
            self.assertIn(".CodeMirror", css)
            self.assertIn(".rich-text-input, .rich-text-input *", css)
            self.assertIn("anki-editable, anki-editable *", css)

            # Native selection and CodeMirror highlight tokens
            self.assertIn("--highlight-bg:", css)
            self.assertIn("--highlight-fg:", css)
            self.assertIn("--selected-bg:", css)
            self.assertIn("--selected-fg:", css)
            self.assertIn(".CodeMirror-selected", css)
            self.assertIn(".CodeMirror ::selection", css)

            # CodeMirror syntax tokens for light themes (red/green/amber/purple)
            self.assertIn(".CodeMirror .cm-tag", css)
            self.assertIn(".CodeMirror .cm-attribute", css)
            self.assertIn(".CodeMirror .cm-string", css)
            self.assertIn(".CodeMirror .cm-keyword", css)
            self.assertIn("#991b1b", css)  # Deep red for tags
            self.assertIn("#14532d", css)  # Deep forest green for attributes
            self.assertIn("#78350f", css)  # Deep amber for strings

            # Bridge script and Shadow DOM injection
            self.assertIn("syncEditorTheme", css)
            self.assertIn("anki-suite-shadow-style", css)
            self.assertIn("applyShadowStyles", css)
            self.assertIn("applyStylesToShadow", css)
            self.assertIn("userBase", css)
            self.assertIn("-webkit-text-fill-color", css)
            self.assertIn("_obsidian_obs", css)
            self.assertIn("_obsidianEditorSyncInterval", css)
            self.assertIn("isLight = true", css)

    def test_editor_qtoolbutton_styling_in_dialog(self):
        """Verify QToolButton is styled identically to QPushButton in dialog stylesheet for AddCards."""
        for preset_key in ("clean_light", "warm_paper", "dracula", "nord_dark"):
            preset = THEME_PRESETS[preset_key]
            qss = get_qt_dialog_stylesheet(preset)
            self.assertIn("QPushButton, QToolButton", qss)
            self.assertIn("QPushButton:hover, QToolButton:hover", qss)
            self.assertIn("QPushButton:pressed, QToolButton:pressed", qss)
            self.assertIn("QPushButton:disabled, QToolButton:disabled", qss)


    def test_settings_hub_dialog_theme_adaptation(self):
        """Verify settings hub dialog conforms dynamically to active theme and updates in real-time."""
        from modules.unified_config.settings_dialog import ObsidianSuiteHubDialog

        for preset_key in ("warm_paper", "clean_light", "oled_dark", "dracula"):
            preset = THEME_PRESETS[preset_key]
            qss = get_qt_dialog_stylesheet(preset)
            self.assertIn("QScrollArea", qss)
            self.assertIn("QScrollArea QWidget#qt_scrollarea_viewport", qss)
            self.assertIn("QCheckBox::indicator", qss)
            self.assertIn("QSlider::groove:horizontal", qss)
            self.assertIn("QScrollBar:vertical", qss)
            self.assertIn("QSpinBox::up-button", qss)
            self.assertIn(preset["bg_primary"], qss)

        dialog = ObsidianSuiteHubDialog()
        self.assertTrue(hasattr(dialog, "_current_theme_colors"))
        
        # Test real-time preview on preset changed
        wp_idx = dialog.combo_presets.findData("warm_paper")
        dialog.combo_presets.setCurrentIndex(wp_idx)
        dialog._on_preset_changed()
        self.assertEqual(dialog._current_theme_colors["bg_primary"], THEME_PRESETS["warm_paper"]["bg_primary"])

        # Test real-time preview on custom color picked
        dialog.color_buttons["bg_primary"].color_hex = "#112233"
        dialog._on_custom_color_picked()
        self.assertEqual(dialog._current_theme_colors["bg_primary"], "#112233")


if __name__ == "__main__":
    unittest.main()


