# -*- coding: utf-8 -*-
"""
Tests for Image Search Recent Images Tab & Persistence Manager.
Validates:
1. MRU tracking of recent images (newest at index 0).
2. Strict cap at 15 items.
3. Deduplication of images by original_url and thumb_url.
4. Serialization and deserialization to/from JSON.
5. Integration with ImageSearchDialog (tab structure, refresh, download_and_insert).
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import shutil
import json

from modules.image_search.search_engine import ImageResultItem
from modules.image_search.recent_manager import (
    get_recent_images,
    add_recent_image,
    clear_recent_images,
    item_to_dict,
    dict_to_item,
    MAX_RECENT_IMAGES,
)
from modules.image_search.ui.search_dialog import ImageSearchDialog


class TestImageSearchRecent(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch(
            "modules.image_search.recent_manager._get_storage_filepath",
            return_value=os.path.join(self.test_dir, "recent_images.json"),
        )
        self.patcher.start()
        clear_recent_images()

    def tearDown(self):
        clear_recent_images()
        self.patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_serialization_and_deserialization(self):
        item = ImageResultItem(
            title="Necrotizing Pancreatitis CT",
            thumb_url="https://example.com/thumb.jpg",
            original_url="https://radiopaedia.org/cases/pancreatitis.png",
            width=800,
            height=600,
            source="https://radiopaedia.org",
            relevance_score=95,
        )
        d = item_to_dict(item)
        self.assertEqual(d["title"], "Necrotizing Pancreatitis CT")
        self.assertEqual(d["original_url"], "https://radiopaedia.org/cases/pancreatitis.png")
        self.assertEqual(d["width"], 800)

        restored = dict_to_item(d)
        self.assertEqual(restored.title, item.title)
        self.assertEqual(restored.original_url, item.original_url)
        self.assertEqual(restored.width, item.width)
        self.assertEqual(restored.height, item.height)
        self.assertEqual(restored.source, item.source)
        self.assertEqual(restored.relevance_score, item.relevance_score)

    def test_add_and_get_recent_images_mru_order(self):
        item1 = ImageResultItem(title="Image 1", thumb_url="t1", original_url="https://example.com/1.jpg")
        item2 = ImageResultItem(title="Image 2", thumb_url="t2", original_url="https://example.com/2.jpg")
        item3 = ImageResultItem(title="Image 3", thumb_url="t3", original_url="https://example.com/3.jpg")

        add_recent_image(item1)
        add_recent_image(item2)
        add_recent_image(item3)

        recents = get_recent_images()
        self.assertEqual(len(recents), 3)
        # Most recent must be item3, then item2, then item1
        self.assertEqual(recents[0].original_url, "https://example.com/3.jpg")
        self.assertEqual(recents[1].original_url, "https://example.com/2.jpg")
        self.assertEqual(recents[2].original_url, "https://example.com/1.jpg")

    def test_strict_cap_at_15_items(self):
        self.assertEqual(MAX_RECENT_IMAGES, 15)
        for i in range(25):
            it = ImageResultItem(
                title=f"Image {i}",
                thumb_url=f"https://example.com/thumb_{i}.jpg",
                original_url=f"https://example.com/orig_{i}.jpg",
            )
            add_recent_image(it)

        recents = get_recent_images()
        self.assertEqual(len(recents), 15)
        # The most recent should be Image 24
        self.assertEqual(recents[0].title, "Image 24")
        # The 15th item should be Image 10 (24 - 14 = 10)
        self.assertEqual(recents[14].title, "Image 10")

    def test_deduplication_moves_to_front(self):
        item1 = ImageResultItem(title="Image 1", thumb_url="t1", original_url="https://example.com/1.jpg")
        item2 = ImageResultItem(title="Image 2", thumb_url="t2", original_url="https://example.com/2.jpg")
        item3 = ImageResultItem(title="Image 3", thumb_url="t3", original_url="https://example.com/3.jpg")

        add_recent_image(item1)
        add_recent_image(item2)
        add_recent_image(item3)

        # Re-insert item1 (should be moved to index 0, total count remains 3)
        add_recent_image(item1)

        recents = get_recent_images()
        self.assertEqual(len(recents), 3)
        self.assertEqual(recents[0].original_url, "https://example.com/1.jpg")
        self.assertEqual(recents[1].original_url, "https://example.com/3.jpg")
        self.assertEqual(recents[2].original_url, "https://example.com/2.jpg")

    def test_clear_recent_images(self):
        item = ImageResultItem(title="Image 1", thumb_url="t1", original_url="https://example.com/1.jpg")
        add_recent_image(item)
        self.assertEqual(len(get_recent_images()), 1)

        clear_recent_images()
        self.assertEqual(len(get_recent_images()), 0)

    def test_empty_or_invalid_item_ignored(self):
        add_recent_image(None)
        empty_item = ImageResultItem(title="Empty", thumb_url="", original_url="")
        add_recent_image(empty_item)
        self.assertEqual(len(get_recent_images()), 0)

    def test_dialog_attributes_and_tab_integration(self):
        fake_editor = MagicMock()
        fake_editor.currentField = 0
        dialog = ImageSearchDialog(parent=None, editor=fake_editor, initial_query="test")

        self.assertTrue(hasattr(dialog, "_recent_items"))
        self.assertTrue(hasattr(dialog, "_current_inserting_item"))
        self.assertTrue(hasattr(dialog, "tab_widget"))
        self.assertTrue(hasattr(dialog, "tab_search"))
        self.assertTrue(hasattr(dialog, "tab_recent"))
        self.assertTrue(hasattr(dialog, "_refresh_recent_tab"))
        self.assertTrue(hasattr(dialog, "_on_tab_changed"))

    def test_dialog_download_and_insert_records_recent(self):
        fake_editor = MagicMock()
        fake_editor.currentField = 1
        dialog = ImageSearchDialog(parent=None, editor=fake_editor)

        item = ImageResultItem(
            title="Pancreatitis Balthazar E",
            thumb_url="https://example.com/t.jpg",
            original_url="https://radiopaedia.org/balthazar.jpg",
        )

        with patch("modules.image_search.ui.search_dialog.download_image_bytes", return_value=(b"fakebytes", ".jpg")):
            dialog._current_inserting_item = item
            dialog._on_download_success(b"fakebytes", ".jpg")

        recents = get_recent_images()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0].original_url, "https://radiopaedia.org/balthazar.jpg")
        self.assertEqual(dialog.downloaded_data[0], b"fakebytes")
        self.assertEqual(dialog.downloaded_data[1], ".jpg")

    def test_get_recent_images_force_reload(self):
        item = ImageResultItem(title="Image A", thumb_url="tA", original_url="https://example.com/A.jpg")
        add_recent_image(item)

        # Direct disk update simulation
        filepath = self.test_dir + "/recent_images.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([{
                "title": "Direct From Disk",
                "thumb_url": "tDisk",
                "original_url": "https://example.com/disk.jpg",
                "width": 100,
                "height": 100,
                "source": "https://example.com",
                "relevance_score": 10
            }], f)

        # Without force_reload, should return cached
        cached = get_recent_images(force_reload=False)
        self.assertEqual(cached[0].title, "Image A")

        # With force_reload=True, should read fresh from disk
        reloaded = get_recent_images(force_reload=True)
        self.assertEqual(reloaded[0].title, "Direct From Disk")

    def test_items_with_only_thumb_url_accepted(self):
        filepath = self.test_dir + "/recent_images.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([{
                "title": "Thumb Only Item",
                "thumb_url": "https://example.com/only_thumb.jpg",
                "original_url": "",
                "width": 200,
                "height": 200,
                "source": "https://example.com",
                "relevance_score": 5
            }], f)

        reloaded = get_recent_images(force_reload=True)
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].thumb_url, "https://example.com/only_thumb.jpg")

    def test_recent_tab_layout_and_card_population(self):
        fake_editor = MagicMock()
        fake_editor.currentField = 0
        dialog = ImageSearchDialog(parent=None, editor=fake_editor)

        # In headless environments without PyQt6, mock UI elements to verify layout logic
        if dialog.recent_grid_layout is None:
            dialog.recent_grid_layout = MagicMock()
            dialog.recent_grid_layout.count.return_value = 0
            dialog.lbl_recent_empty = MagicMock()
            dialog.recent_scroll_area = MagicMock()
            dialog.tab_widget = MagicMock()
            dialog.recent_grid_content = MagicMock()

        # 1. When no recents, empty label is shown and scroll area is hidden
        clear_recent_images()
        dialog._refresh_recent_tab()
        dialog.lbl_recent_empty.show.assert_called()
        dialog.recent_scroll_area.hide.assert_called()
        self.assertEqual(len(dialog._recent_items), 0)

        # 2. Add items to recents and refresh
        item1 = ImageResultItem(title="Test CT 1", thumb_url="t1", original_url="https://example.com/ct1.jpg")
        item2 = ImageResultItem(title="Test CT 2", thumb_url="t2", original_url="https://example.com/ct2.jpg")
        add_recent_image(item1)
        add_recent_image(item2)

        dialog._refresh_recent_tab()
        self.assertEqual(len(dialog._recent_items), 2)
        dialog.lbl_recent_empty.hide.assert_called()
        dialog.recent_scroll_area.show.assert_called()
        self.assertEqual(dialog.recent_grid_layout.addWidget.call_count, 2)


if __name__ == "__main__":
    unittest.main()
