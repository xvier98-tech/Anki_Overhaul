# -*- coding: utf-8 -*-
"""
Unit tests for the Internationalization (i18n) module.
"""

import unittest
from utils.i18n import (
    normalize_language_code,
    get_current_language,
    set_language_override,
    tr,
    TRANSLATIONS,
)


class TestI18n(unittest.TestCase):

    def setUp(self):
        set_language_override(None)

    def tearDown(self):
        set_language_override(None)

    def test_normalize_language_code(self):
        # Portuguese variants (Brazil & Portugal unified)
        self.assertEqual(normalize_language_code("pt"), "pt")
        self.assertEqual(normalize_language_code("pt_BR"), "pt")
        self.assertEqual(normalize_language_code("pt-BR"), "pt")
        self.assertEqual(normalize_language_code("pt_PT"), "pt")
        self.assertEqual(normalize_language_code("pt-pt"), "pt")

        # Spanish variants
        self.assertEqual(normalize_language_code("es"), "es")
        self.assertEqual(normalize_language_code("es_ES"), "es")
        self.assertEqual(normalize_language_code("es_419"), "es")
        self.assertEqual(normalize_language_code("es-es"), "es")

        # French variants
        self.assertEqual(normalize_language_code("fr"), "fr")
        self.assertEqual(normalize_language_code("fr_FR"), "fr")
        self.assertEqual(normalize_language_code("fr_CA"), "fr")

        # Unsupported languages must fallback to English ('en')
        self.assertEqual(normalize_language_code("pl"), "en")       # Polish (explicit user requirement)
        self.assertEqual(normalize_language_code("pl_PL"), "en")
        self.assertEqual(normalize_language_code("de"), "en")       # German
        self.assertEqual(normalize_language_code("it"), "en")       # Italian
        self.assertEqual(normalize_language_code("ja"), "en")       # Japanese
        self.assertEqual(normalize_language_code("zh_CN"), "en")    # Chinese
        self.assertEqual(normalize_language_code(""), "en")
        self.assertEqual(normalize_language_code(None), "en")

    def test_translation_languages(self):
        # English
        set_language_override("en")
        self.assertEqual(get_current_language(), "en")
        self.assertIn("Settings Hub", tr("hub_title"))
        self.assertEqual(tr("btn_cancel"), "Cancel")
        self.assertIn("Focus (min)", tr("pomo_focus_min"))

        # Portuguese
        set_language_override("pt")
        self.assertEqual(get_current_language(), "pt")
        self.assertIn("Central de Configurações", tr("hub_title"))
        self.assertEqual(tr("btn_cancel"), "Cancelar")
        self.assertIn("Foco (min)", tr("pomo_focus_min"))

        # Spanish
        set_language_override("es")
        self.assertEqual(get_current_language(), "es")
        self.assertIn("Centro de Ajustes", tr("hub_title"))
        self.assertEqual(tr("btn_cancel"), "Cancelar")
        self.assertIn("Enfoque (min)", tr("pomo_focus_min"))

        # French
        set_language_override("fr")
        self.assertEqual(get_current_language(), "fr")
        self.assertIn("Centre de Configuration", tr("hub_title"))
        self.assertEqual(tr("btn_cancel"), "Annuler")
        self.assertIn("Concentration (min)", tr("pomo_focus_min"))

    def test_unsupported_language_fallback_to_english(self):
        # When language is Polish or other, must fallback to English
        set_language_override("pl")
        self.assertEqual(get_current_language(), "en")
        self.assertIn("Settings Hub", tr("hub_title"))
        self.assertEqual(tr("btn_cancel"), "Cancel")

    def test_missing_key_fallback(self):
        set_language_override("en")
        self.assertEqual(tr("non_existent_key", default="Custom Default"), "Custom Default")
        self.assertEqual(tr("non_existent_key_without_default"), "non_existent_key_without_default")


if __name__ == "__main__":
    unittest.main()
