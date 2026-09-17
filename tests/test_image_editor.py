# -*- coding: utf-8 -*-
"""
Unit tests for the Image Annotation & Crop Editor and Recent Images integrity.
Verifies arrowhead trigonometry, rectangle normalization, i18n completeness,
and the mandatory business rule that recent history preserves pristine original images.
"""

import unittest
from unittest.mock import MagicMock, patch
import math

from modules.image_search.ui.image_editor import (
    calculate_arrowhead_points,
    normalize_rect_coords,
    ImageAnnotationCanvas,
    ImageEditorDialog,
)
from modules.image_search.search_engine import ImageResultItem
from utils.i18n import tr, set_language_override


class TestImageEditor(unittest.TestCase):

    def setUp(self):
        set_language_override(None)

    def tearDown(self):
        set_language_override(None)

    def test_calculate_arrowhead_points_right(self):
        """Validates trigonometry for an arrow pointing horizontally to the right."""
        start_x, start_y = 0.0, 0.0
        end_x, end_y = 100.0, 0.0
        arrow_size = 20.0
        angle_deg = 30.0

        tip, p1, p2 = calculate_arrowhead_points(
            start_x, start_y, end_x, end_y, arrow_size=arrow_size, angle_deg=angle_deg
        )

        self.assertEqual(tip, (100.0, 0.0))
        # Points should be to the left of the tip (x < 100)
        self.assertLess(p1[0], end_x)
        self.assertLess(p2[0], end_x)
        # Expected distance ~ 20*cos(30 deg) = 20 * 0.866 = 17.32 => x ~ 82.68
        self.assertAlmostEqual(p1[0], 100.0 - 20.0 * math.cos(math.radians(30)), places=2)
        # Symmetric in y: p1_y = - p2_y
        self.assertAlmostEqual(p1[1], -p2[1], places=2)

    def test_calculate_arrowhead_points_down(self):
        """Validates trigonometry for an arrow pointing vertically downwards."""
        start_x, start_y = 50.0, 10.0
        end_x, end_y = 50.0, 150.0
        arrow_size = 25.0

        tip, p1, p2 = calculate_arrowhead_points(start_x, start_y, end_x, end_y, arrow_size=arrow_size)

        self.assertEqual(tip, (50.0, 150.0))
        # Arrow wings should be above the tip (y < 150)
        self.assertLess(p1[1], end_y)
        self.assertLess(p2[1], end_y)
        # Symmetrical across x=50
        self.assertAlmostEqual(50.0 - p1[0], p2[0] - 50.0, places=2)

    def test_normalize_rect_coords(self):
        """Validates that arbitrary diagonal corners normalize to (left, top, width, height)."""
        # Top-left to bottom-right
        l, t, w, h = normalize_rect_coords(10.0, 20.0, 110.0, 140.0)
        self.assertEqual((l, t, w, h), (10.0, 20.0, 100.0, 120.0))

        # Bottom-right to top-left (inverted drag)
        l2, t2, w2, h2 = normalize_rect_coords(110.0, 140.0, 10.0, 20.0)
        self.assertEqual((l2, t2, w2, h2), (10.0, 20.0, 100.0, 120.0))

        # Top-right to bottom-left
        l3, t3, w3, h3 = normalize_rect_coords(200.0, 50.0, 80.0, 180.0)
        self.assertEqual((l3, t3, w3, h3), (80.0, 50.0, 120.0, 130.0))

    def test_editor_i18n_keys_all_four_languages(self):
        """Ensures all 11 image editor translation keys exist in PT, EN, ES, and FR."""
        required_keys = [
            "image_search_btn_edit",
            "image_search_editor_title",
            "image_search_tool_arrow",
            "image_search_tool_circle",
            "image_search_tool_crop",
            "image_search_apply_crop",
            "image_search_undo",
            "image_search_reset",
            "image_search_insert_edited",
            "image_search_stroke_width",
            "image_search_editor_hint",
        ]

        for lang in ["pt", "en", "es", "fr"]:
            set_language_override(lang)
            for k in required_keys:
                translated = tr(k)
                self.assertNotEqual(
                    translated,
                    k,
                    f"Missing translation for key '{k}' in language '{lang}'",
                )
                self.assertTrue(
                    len(translated.strip()) > 0,
                    f"Empty translation for key '{k}' in language '{lang}'",
                )

    def test_recent_image_keeps_original_on_edit(self):
        """
        MANDATORY BUSINESS RULE:
        When an image is edited and inserted into an Anki card,
        the recent images collection MUST store the pristine ORIGINAL image item,
        not the edited version.
        """
        original_item = ImageResultItem(
            title="Normal Anatomy and Necrotizing Pancreatitis CT",
            original_url="https://radiopaedia.org/images/12345/download.jpg",
            thumb_url="https://radiopaedia.org/thumbs/12345/thumb.jpg",
            source="https://radiopaedia.org/cases/pancreatitis-1",
            width=1920,
            height=1080,
        )

        mock_editor = MagicMock()
        mock_dialog = MagicMock()
        mock_dialog.editor = mock_editor
        mock_dialog.search_input = MagicMock()
        mock_dialog.search_input.text.return_value = "pancreatite"
        mock_dialog.current_preview_item = original_item
        mock_pixmap = MagicMock()
        mock_pixmap.isNull.return_value = False
        mock_dialog.lbl_zoom_image = MagicMock()
        mock_dialog.lbl_zoom_image.pixmap.return_value = mock_pixmap

        recorded_recent_items = []

        def fake_add_recent(item):
            recorded_recent_items.append(item)

        with patch("modules.image_search.ui.search_dialog.add_recent_image", side_effect=fake_add_recent), \
             patch("modules.image_search.ui.search_dialog.ImageEditorDialog") as MockEditorDialogClass:

            # Mock dialog execution
            mock_editor_instance = MagicMock()
            mock_editor_instance.exec.return_value = 1
            mock_editor_instance.result_data = b"FAKE_EDITED_IMAGE_WITH_ARROWS_BYTES"
            mock_editor_instance.result_ext = ".jpg"
            MockEditorDialogClass.return_value = mock_editor_instance

            # Import the actual method
            from modules.image_search.ui.search_dialog import ImageSearchDialog
            
            # Execute editor flow on mock
            ImageSearchDialog.open_editor_for_item(mock_dialog, original_item)

            # 1. Verify editor insertion received the EDITED bytes
            mock_dialog._insert_into_anki_editor.assert_called_once_with(
                b"FAKE_EDITED_IMAGE_WITH_ARROWS_BYTES", ".jpg", "pancreatite_edited"
            )

            # 2. Verify recent storage received the PRISTINE ORIGINAL item
            self.assertEqual(len(recorded_recent_items), 1)
            saved_item = recorded_recent_items[0]
            self.assertEqual(saved_item.original_url, "https://radiopaedia.org/images/12345/download.jpg")
            self.assertEqual(saved_item.thumb_url, "https://radiopaedia.org/thumbs/12345/thumb.jpg")
            self.assertEqual(saved_item.title, "Normal Anatomy and Necrotizing Pancreatitis CT")


if __name__ == "__main__":
    unittest.main()
