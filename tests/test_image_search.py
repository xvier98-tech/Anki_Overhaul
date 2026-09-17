# -*- coding: utf-8 -*-
"""
Unit tests for the Card Editor Image Search & Inserter module.
"""

import unittest
from unittest.mock import MagicMock, patch
import io
import json

from modules.image_search.search_engine import (
    ImageResultItem,
    search_web_images,
    search_wikimedia,
    search_images,
    download_image_bytes,
)
from modules.image_search import on_editor_did_init_buttons
from utils.i18n import tr, set_language_override


class TestImageSearch(unittest.TestCase):

    def setUp(self):
        set_language_override(None)

    def tearDown(self):
        set_language_override(None)

    def test_image_result_item(self):
        item = ImageResultItem(
            title="Mitochondria Diagram",
            thumb_url="https://example.com/thumb.jpg",
            original_url="https://example.com/mito.png",
            width=1920,
            height=1080,
            source="https://nature.com/article",
        )
        self.assertEqual(item.title, "Mitochondria Diagram")
        self.assertEqual(item.width, 1920)
        self.assertEqual(item.height, 1080)
        self.assertTrue(item.original_url.endswith(".png"))

    @patch("urllib.request.urlopen")
    def test_search_web_images_parsing(self, mock_urlopen):
        fake_html = """
        <html><body>
        <script>
        AF_initDataCallback({key: 'ds:1', hash: '2', data: [
          null,
          [
            null,
            [
              "id_1",
              [null, null, null],
              ["https://encrypted-tbn0.gstatic.com/images?q=tbn:thumb1", 100, 100],
              ["https://cdn.example.com/heart.jpg", 800, 1200],
              null, null, null, null, null,
              ["https://health.org", "Human Heart Anatomy", "Health Org"]
            ],
            [
              "id_2",
              [null, null, null],
              ["https://encrypted-tbn0.gstatic.com/images?q=tbn:thumb2", 100, 100],
              ["https://cdn.example.com/brain.png", 1080, 1920],
              null, null, null, null, null,
              ["https://brain.org", "Human Brain", "Brain Org"]
            ]
          ]
        ], sideChannel: {}});
        </script>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_html.encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results = search_web_images("human anatomy", max_results=10)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Human Heart Anatomy")
        self.assertEqual(results[0].original_url, "https://cdn.example.com/heart.jpg")
        self.assertEqual(results[0].width, 1200)
        self.assertEqual(results[0].height, 800)

        self.assertEqual(results[1].title, "Human Brain")
        self.assertEqual(results[1].original_url, "https://cdn.example.com/brain.png")

    @patch("urllib.request.urlopen")
    def test_search_wikimedia_parsing(self, mock_urlopen):
        fake_data = {
            "query": {
                "pages": {
                    "101": {
                        "title": "File:Mitochondria_organelle.svg",
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/wikipedia/commons/mito.png",
                            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/mito.png",
                            "width": 800,
                            "height": 600,
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Mitochondria"
                        }]
                    }
                }
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results = search_wikimedia("mitochondria", max_results=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Mitochondria_organelle.svg")
        self.assertEqual(results[0].original_url, "https://upload.wikimedia.org/wikipedia/commons/mito.png")
        self.assertEqual(results[0].width, 800)

    @patch("urllib.request.urlopen")
    def test_download_image_bytes_content_type(self, mock_urlopen):
        fake_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "image/png; charset=utf-8"}
        mock_resp.read.return_value = fake_bytes
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        data, ext = download_image_bytes("https://example.com/image_without_extension")
        self.assertEqual(data, fake_bytes)
        self.assertEqual(ext, ".png")

    def test_i18n_image_search_all_languages(self):
        keys = [
            "image_search_tooltip",
            "image_search_title",
            "image_search_placeholder",
            "image_search_btn_search",
            "image_search_searching",
            "image_search_download_insert",
            "image_search_downloading",
            "image_search_no_results",
            "image_search_back",
            "image_search_engine_all",
            "image_search_engine_google",
            "image_search_engine_wikimedia",
            "image_search_engine_wikipedia",
            "image_search_engine_web",
            "image_search_engine_wiki",
            "image_search_error",
            "image_search_zoom_hint",
            "image_search_loading_more",
            "image_search_end_of_results",
            "image_search_tab_search",
            "image_search_tab_recent",
            "image_search_recent_hint",
            "image_search_recent_empty",
        ]
        for lang in ("en", "pt", "es", "fr"):
            set_language_override(lang)
            for k in keys:
                translated = tr(k)
                self.assertNotEqual(translated, k, f"Key '{k}' not found in language '{lang}'")
                self.assertTrue(len(translated) > 0)

    def test_editor_button_hook(self):
        mock_editor = MagicMock()
        mock_editor.addButton.return_value = "<button id='obsidian_image_search_btn'></button>"
        buttons = []

        on_editor_did_init_buttons(buttons, mock_editor)
        self.assertEqual(len(buttons), 1)
        self.assertIn("obsidian_image_search_btn", buttons[0])
        mock_editor.addButton.assert_called_once()
        call_kwargs = mock_editor.addButton.call_args[1]
        self.assertEqual(call_kwargs.get("cmd"), "obsidian_image_search")
        self.assertEqual(call_kwargs.get("keys"), "Ctrl+Shift+I")

    def test_insert_into_anki_editor(self):
        from modules.image_search.ui.search_dialog import ImageSearchDialog

        mock_editor = MagicMock()
        mock_editor.mw.col.media.write_data.return_value = "obsidian_img_test.jpg"
        mock_editor.note.fields = ["Front Text", "Back Text"]
        mock_editor.addMode = True
        
        dialog = ImageSearchDialog.__new__(ImageSearchDialog)
        dialog.editor = mock_editor
        dialog.saved_field_index = 1
        dialog._insert_into_anki_editor(b"image_bytes", ".jpg", "test query")

        mock_editor.mw.col.media.write_data.assert_called_once()
        self.assertIn("obsidian_test_query_", mock_editor.mw.col.media.write_data.call_args[0][0])
        mock_editor.web.eval.assert_any_call("focusField(1);")
        mock_editor.doPaste.assert_called_once_with('<img src="obsidian_img_test.jpg">', internal=False)
        mock_editor.loadNote.assert_called_once_with(focusTo=1)
        self.assertIn('<img src="obsidian_img_test.jpg">', mock_editor.note.fields[1])

    def test_medical_synonyms_and_spam_filtering(self):
        from modules.image_search.search_engine import (
            _calculate_relevance_score,
            _get_medical_synonyms,
        )

        # Test synonym extraction
        syns = _get_medical_synonyms("glandulas parauretrais")
        self.assertTrue(any("skene" in s or "paraurethral" in s for s in syns))

        syns_bartholin = _get_medical_synonyms("glandula de bartholin")
        self.assertTrue(any("bartholin" in s for s in syns_bartholin))

        # Test spam domain rejection
        score_spam = _calculate_relevance_score(
            title="Glandulas Parauretrais De Skene",
            source="https://pim-staging.cpcompany.com/study/glandulas-parauretrais-de-skene.html",
            query_words=["glandulas", "parauretrais"],
            is_anatomical=True,
        )
        self.assertLess(score_spam, 0)

        # Test disconnected celebrity rejection
        score_ronaldo = _calculate_relevance_score(
            title="Cristiano Ronaldo posa em treino",
            source="https://globoesporte.globo.com/futebol",
            query_words=["glandulas", "parauretrais"],
            is_anatomical=True,
        )
        self.assertLess(score_ronaldo, 0)

        # Test authoritative medical boost
        score_kenhub = _calculate_relevance_score(
            title="Paraurethral glands anatomy and histology",
            source="https://www.kenhub.com/en/library/anatomy/urinary-system",
            query_words=["paraurethral", "glands"],
            is_anatomical=True,
        )
        self.assertGreater(score_kenhub, 20)

        # Test unconditional adult tube and anime rejection (even when is_anatomical=False)
        score_porn = _calculate_relevance_score(
            title="She fucks him hardcore raw",
            source="https://adulttube.xxx/video123",
            query_words=["sifilis"],
            is_anatomical=False,
        )
        self.assertLess(score_porn, 0)

        score_anime = _calculate_relevance_score(
            title="LGBTQ anime manga characters",
            source="https://gelbooru.com/post/view/123",
            query_words=["lactobacilos"],
            is_anatomical=False,
        )
        self.assertLess(score_anime, 0)

        score_scraper_club = _calculate_relevance_score(
            title="Lactobacillus shape",
            source="https://fity.club/lists/suggestions/123",
            query_words=["lactobacilos"],
            is_anatomical=False,
        )
        self.assertLess(score_scraper_club, 0)

        # Test anchor word enforcement: weak acronym 'dip' cannot pass without anchor 'cardiotocografia'
        score_weak_dip = _calculate_relevance_score(
            title="Dip into the pool - summer party",
            source="https://partyblog.com/summer",
            query_words=["cardiotocografia", "dip"],
            is_anatomical=True,
        )
        self.assertLess(score_weak_dip, 0)

        # Test rejection of viral memes / celebrities (Minotauro, mulher mais bonita, blowjob)
        for bad_title in (
            "Minotauro mitologia grega",
            "A mulher mais bonita do mundo posa para revista",
            "Blowjob adult animation dip",
        ):
            bad_score = _calculate_relevance_score(
                title=bad_title,
                source="https://randomdomain.com",
                query_words=["cardiotocografia", "dip"],
                is_anatomical=True,
            )
            self.assertLess(bad_score, 0, f"Deveria rejeitar: {bad_title}")

        # Test valid cardiotocography matching
        good_score = _calculate_relevance_score(
            title="Cardiotocografia Dip 1 2 3 - RETOEDU",
            source="https://medscape.com/cardio",
            query_words=["cardiotocografia", "dip"],
            is_anatomical=True,
        )
        self.assertGreater(good_score, 0)

    def test_extract_base_concept(self):
        from modules.image_search.search_engine import _extract_base_concept
        self.assertEqual(_extract_base_concept("cardiotocografia DIP 3"), "cardiotocografia")
        self.assertEqual(_extract_base_concept("cardiotografia DIP 3"), "cardiotografia")
        self.assertEqual(_extract_base_concept("cancer de mama estagio 2"), "cancer de mama")

    def test_extract_google_images(self):
        from modules.image_search.search_engine import _extract_google_results
        fake_html = """
        <html><body>
        <script>
        AF_initDataCallback({key: 'ds:1', hash: '2', data: [
          null,
          [
            null,
            [
              "id_1",
              [null, null, null],
              ["https://encrypted-tbn0.gstatic.com/images?q=tbn:ctg", 100, 100],
              ["https://radiopaedia.org/cases/cardiotocografia.jpg", 800, 1200],
              null, null, null, null, null,
              ["https://radiopaedia.org/cases/ctg", "Cardiotocografia Normal", "Radiopaedia.org"]
            ]
          ]
        ], sideChannel: {}});
        </script>
        <script>
        var x = [["https://cdn.example.com/fallback_ctg.png\\u003fq\\u003d1\\u0026w\\u003d2", 600, 900]];
        </script>
        </body></html>
        """
        results = _extract_google_results(fake_html)
        self.assertGreaterEqual(len(results), 2)
        # 1. First item from AF_initDataCallback
        self.assertEqual(results[0]["original_url"], "https://radiopaedia.org/cases/cardiotocografia.jpg")
        self.assertEqual(results[0]["title"], "Cardiotocografia Normal")
        self.assertEqual(results[0]["width"], 1200)
        self.assertEqual(results[0]["height"], 800)
        # 2. Second item from triples fallback with unicode unescaping
        self.assertEqual(results[1]["original_url"], "https://cdn.example.com/fallback_ctg.png?q=1&w=2")
        self.assertEqual(results[1]["width"], 900)
        self.assertEqual(results[1]["height"], 600)

    # Backward compatibility alias
    test_extract_bing_results_dom_isolation = test_extract_google_images

    @patch("modules.image_search.search_engine.search_google_images")
    @patch("modules.image_search.search_engine.search_duckduckgo_images")
    @patch("modules.image_search.search_engine.search_wikimedia")
    @patch("modules.image_search.search_engine.search_wikipedia_articles")
    def test_search_images_fallback(self, mock_wiki_art, mock_wiki_commons, mock_ddg, mock_google):
        mock_google.return_value = []
        mock_ddg.return_value = []
        mock_wiki_art.return_value = []
        mock_wiki_commons.return_value = [ImageResultItem("Wiki Result", "https://wiki.org/t.jpg", "https://wiki.org/o.jpg", relevance_score=10)]

        # Combined 'all' mode: Web returns 0, includes wiki
        res = search_images("test", engine="all")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].title, "Wiki Result")

    def test_translate_query_to_english(self):
        from modules.image_search.search_engine import (
            translate_query_to_english,
            _TRANSLATION_CACHE,
            _get_medical_synonyms,
        )

        # 1. English returns as-is
        self.assertEqual(translate_query_to_english("cardiotocography", source_lang="en"), "cardiotocography")

        # 2. Empty query returns empty
        self.assertEqual(translate_query_to_english("   "), "")

        # 3. Cache test: insert a mock translation into cache and verify immediate retrieval
        _TRANSLATION_CACHE["pt:teste doença rara"] = "rare disease test"
        res = translate_query_to_english("teste doença rara", source_lang="pt")
        self.assertEqual(res, "rare disease test")

        # 4. Integration with _get_medical_synonyms
        syns = _get_medical_synonyms("teste doença rara")
        self.assertIn("rare disease test", syns)

    def test_download_fallback_to_thumbnail(self):
        """Verifies that download_and_insert falls back to thumb_url when original_url fails."""
        from modules.image_search.ui.search_dialog import ImageSearchDialog
        import threading

        mock_editor = MagicMock()
        mock_editor.mw.col.media.write_data.return_value = "obsidian_img_thumb.jpg"
        mock_editor.note.fields = ["", ""]
        mock_editor.addMode = True

        dialog = ImageSearchDialog.__new__(ImageSearchDialog)
        dialog.editor = mock_editor
        dialog.saved_field_index = 0
        dialog.download_signals = MagicMock()

        item = ImageResultItem(
            title="Necrotizing Pancreatitis CT",
            thumb_url="https://cdn.example.com/thumb.jpg",
            original_url="https://blocked-medical-site.com/huge.jpg",
        )

        def mock_downloader(url, timeout=10):
            if "blocked-medical-site.com" in url:
                raise RuntimeError("HTTP Error 403: Forbidden")
            if "thumb.jpg" in url:
                return (b"thumb_bytes_data", ".jpg")
            raise RuntimeError("Unexpected URL")

        with patch("modules.image_search.ui.search_dialog.download_image_bytes", side_effect=mock_downloader):
            # We run the worker directly or let download_and_insert run
            dialog.download_and_insert(item)
            # Find and join worker thread
            for t in threading.enumerate():
                if t != threading.current_thread() and t.daemon:
                    t.join(timeout=2.0)

            dialog.download_signals.download_done.emit.assert_called_once_with(b"thumb_bytes_data", ".jpg")
            dialog.download_signals.download_failed.emit.assert_not_called()


if __name__ == "__main__":
    unittest.main()



