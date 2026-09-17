# -*- coding: utf-8 -*-
"""
Unit tests for Card Editor Image Search - Medical Routing, Engine Isolation,
Wikidata Biography Exclusion, and Source URL Resolution.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import urllib.parse
import re

from modules.image_search.search_engine import (
    ImageResultItem,
    search_wikipedia_articles,
    search_wikimedia,
    search_google_images,
    search_duckduckgo_images,
    search_images,
)
from modules.image_search.ui.search_dialog import ImageSearchDialog
from modules.image_search.ui.image_card import ImageCardWidget
from utils.i18n import set_language_override


class TestImageSearchMedicalRouting(unittest.TestCase):
    """
    Test suite for medical query routing, engine isolation,
    Wikidata biography filtering, and source URL resolution.
    """

    def setUp(self):
        set_language_override(None)

    def tearDown(self):
        set_language_override(None)

    @patch("urllib.request.urlopen")
    def test_wikipedia_biography_exclusion(self, mock_urlopen):
        """
        Validates:
        1. Medical queries include '-haswbstatement:P31=Q5' in the Wikipedia search API request.
        2. Non-medical queries do not include this parameter.
        3. Items whose Wikidata description contains biographical terms
           ('santo', 'beata', 'arcebispo', 'compositor', 'político') are discarded.
        """
        fake_wiki_response = {
            "query": {
                "pages": {
                    "101": {
                        "title": "Apendicite Santo Antônio",
                        "terms": {"description": ["Santo e mártir cristão do século XIII"]},
                        "original": {"source": "https://upload.wikimedia.org/santo.jpg", "width": 800, "height": 600},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_santo.jpg"},
                    },
                    "102": {
                        "title": "Apendicite Beata Maria",
                        "terms": {"description": ["Beata da igreja católica beatificada em 1900"]},
                        "original": {"source": "https://upload.wikimedia.org/beata.jpg", "width": 800, "height": 600},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_beata.jpg"},
                    },
                    "103": {
                        "title": "Apendicite Dom Arcebispo João",
                        "terms": {"description": ["Arcebispo metropolitano de Braga"]},
                        "original": {"source": "https://upload.wikimedia.org/arcebispo.jpg", "width": 800, "height": 600},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_arcebispo.jpg"},
                    },
                    "104": {
                        "title": "Apendicite Compositor Silva",
                        "terms": {"description": ["Compositor e maestro brasileiro"]},
                        "original": {"source": "https://upload.wikimedia.org/compositor.jpg", "width": 800, "height": 600},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_compositor.jpg"},
                    },
                    "105": {
                        "title": "Apendicite Político Santos",
                        "terms": {"description": ["Político e deputado provincial"]},
                        "original": {"source": "https://upload.wikimedia.org/politico.jpg", "width": 800, "height": 600},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_politico.jpg"},
                    },
                    "106": {
                        "title": "Apendicite",
                        "terms": {"description": ["Inflamação e condição patológica do apêndice cecal"]},
                        "original": {"source": "https://upload.wikimedia.org/apendicite_med.jpg", "width": 1024, "height": 768},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_apendicite_med.jpg"},
                    },
                }
            }
        }

        def fake_urlopen(req, timeout=8):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            resp = MagicMock()
            resp.__enter__.return_value = resp
            if "translate.googleapis.com" in url:
                resp.read.return_value = json.dumps([[["appendicitis", "apendicite", None, None]]]).encode("utf-8")
                return resp
            if "wikipedia.org" in url:
                resp.read.return_value = json.dumps(fake_wiki_response).encode("utf-8")
                return resp
            resp.read.return_value = b"{}"
            return resp

        mock_urlopen.side_effect = fake_urlopen

        # 1. Execute medical query
        results = search_wikipedia_articles("Apendicite", lang="pt")

        # Verify that outgoing request to Wikipedia included the Wikidata human exclusion token
        wiki_calls = [
            args[0] for args, _ in mock_urlopen.call_args_list
            if "wikipedia.org" in (args[0].full_url if hasattr(args[0], "full_url") else str(args[0]))
        ]
        self.assertTrue(wiki_calls, "No call made to Wikipedia API")
        request_url = wiki_calls[0].full_url if hasattr(wiki_calls[0], "full_url") else str(wiki_calls[0])
        decoded_url = urllib.parse.unquote(request_url)
        self.assertIn("-haswbstatement:P31=Q5", decoded_url)

        # 2. Verify that all 5 biographical articles were discarded and only the clinical article was returned
        self.assertEqual(len(results), 1)
        clinical_item = results[0]
        self.assertIn("Apendicite", clinical_item.title)
        self.assertEqual(clinical_item.original_url, "https://upload.wikimedia.org/apendicite_med.jpg")

        # Discarded titles check
        titles = [r.title for r in results]
        self.assertFalse(any("Santo" in t for t in titles))
        self.assertFalse(any("Beata" in t for t in titles))
        self.assertFalse(any("Arcebispo" in t for t in titles))
        self.assertFalse(any("Compositor" in t for t in titles))
        self.assertFalse(any("Político" in t for t in titles))

        # 3. Verify non-medical query does NOT include -haswbstatement:P31=Q5
        mock_urlopen.reset_mock()
        def non_med_urlopen(req, timeout=8):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            resp = MagicMock()
            resp.__enter__.return_value = resp
            if "translate.googleapis.com" in url:
                resp.read.return_value = json.dumps([[["Eiffel Tower", "Torre Eiffel", None, None]]]).encode("utf-8")
                return resp
            resp.read.return_value = json.dumps({"query": {"pages": {}}}).encode("utf-8")
            return resp

        mock_urlopen.side_effect = non_med_urlopen
        search_wikipedia_articles("Torre Eiffel", lang="pt")

        non_med_wiki_calls = [
            args[0] for args, _ in mock_urlopen.call_args_list
            if "wikipedia.org" in (args[0].full_url if hasattr(args[0], "full_url") else str(args[0]))
        ]
        self.assertTrue(non_med_wiki_calls, "No call made to Wikipedia API for non-medical query")
        non_med_url = non_med_wiki_calls[0].full_url if hasattr(non_med_wiki_calls[0], "full_url") else str(non_med_wiki_calls[0])
        self.assertNotIn("-haswbstatement:P31=Q5", urllib.parse.unquote(non_med_url))

    @patch("urllib.request.urlopen")
    def test_wikipedia_source_url_format(self, mock_urlopen):
        """
        Validates:
        ImageResultItem.source returned by search_wikipedia_articles is a valid canonical HTTP URL
        (e.g., 'https://pt.wikipedia.org/wiki/Pancreatite_aguda') and NOT a static string like 'Wikipedia (PT)'.
        """
        fake_wiki_response = {
            "query": {
                "pages": {
                    "201": {
                        "title": "Pancreatite aguda",
                        "terms": {"description": ["Processo inflamatório do pâncreas"]},
                        "original": {"source": "https://upload.wikimedia.org/pancreas.jpg", "width": 800, "height": 600},
                        "thumbnail": {"source": "https://upload.wikimedia.org/thumb_pancreas.jpg"},
                    }
                }
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_wiki_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results = search_wikipedia_articles("Pancreatite aguda", lang="pt")
        self.assertEqual(len(results), 1)
        item = results[0]

        # Check that item.source is a valid URL and not the legacy static string
        self.assertNotEqual(item.source, "Wikipedia (PT)")
        self.assertNotEqual(item.source, "Wikipedia")
        self.assertTrue(item.source.startswith("https://pt.wikipedia.org/wiki/"))
        self.assertEqual(item.source, "https://pt.wikipedia.org/wiki/Pancreatite_aguda")
        self.assertRegex(item.source, r"^https://[a-z]{2}\.wikipedia\.org/wiki/\S+$")

    @patch("modules.image_search.search_engine.search_duckduckgo_images")
    @patch("modules.image_search.search_engine.search_google_images")
    @patch("modules.image_search.search_engine.search_wikipedia_articles")
    @patch("modules.image_search.search_engine.search_wikimedia")
    def test_engine_routing_isolation(
        self,
        mock_wikimedia,
        mock_wikipedia,
        mock_google,
        mock_ddg,
    ):
        """
        Validates engine isolation rules:
        1. engine="wikimedia" exclusively calls search_wikimedia.
        2. engine="wikipedia" exclusively calls search_wikipedia_articles.
        3. engine="google" calls search_google_images (and DDG as fallback),
           but NEVER dumps Wikipedia or Wikimedia into Google results.
        """
        sample_item = ImageResultItem(
            title="Sample",
            thumb_url="https://example.com/thumb.jpg",
            original_url="https://example.com/orig.jpg",
            source="https://example.com",
        )

        mock_wikimedia.return_value = [sample_item]
        mock_wikipedia.return_value = [sample_item]
        mock_google.return_value = [sample_item]
        mock_ddg.return_value = [sample_item]

        # 1. Engine 'wikimedia'
        res_wikimedia = search_images("miocárdio", engine="wikimedia")
        self.assertEqual(len(res_wikimedia), 1)
        mock_wikimedia.assert_called_once_with("miocárdio", max_results=50, page=1)
        mock_wikipedia.assert_not_called()
        mock_google.assert_not_called()
        mock_ddg.assert_not_called()

        # Reset mocks
        mock_wikimedia.reset_mock()
        mock_wikipedia.reset_mock()
        mock_google.reset_mock()
        mock_ddg.reset_mock()

        # 2. Engine 'wikipedia'
        res_wikipedia = search_images("miocárdio", engine="wikipedia")
        self.assertEqual(len(res_wikipedia), 1)
        mock_wikipedia.assert_called_once_with("miocárdio", max_results=50, page=1)
        mock_wikimedia.assert_not_called()
        mock_google.assert_not_called()
        mock_ddg.assert_not_called()

        # Reset mocks
        mock_wikimedia.reset_mock()
        mock_wikipedia.reset_mock()
        mock_google.reset_mock()
        mock_ddg.reset_mock()

        # 3. Engine 'google' with Google succeeding
        res_google = search_images("miocárdio", engine="google")
        self.assertEqual(len(res_google), 1)
        mock_google.assert_called_once()
        mock_ddg.assert_not_called()
        mock_wikipedia.assert_not_called()
        mock_wikimedia.assert_not_called()

        # Reset mocks
        mock_wikimedia.reset_mock()
        mock_wikipedia.reset_mock()
        mock_google.reset_mock()
        mock_ddg.reset_mock()

        # 4. Engine 'google' with Google returning empty -> fallback to DDG, NEVER Wikipedia
        mock_google.return_value = []
        mock_ddg.return_value = [sample_item]
        res_google_ddg = search_images("miocárdio", engine="google")
        self.assertEqual(len(res_google_ddg), 1)
        mock_google.assert_called_once()
        mock_ddg.assert_called_once()
        mock_wikipedia.assert_not_called()
        mock_wikimedia.assert_not_called()

        # Reset mocks
        mock_wikimedia.reset_mock()
        mock_wikipedia.reset_mock()
        mock_google.reset_mock()
        mock_ddg.reset_mock()

        # 5. Engine 'google' with both Google and DDG empty -> NEVER spill into Wikipedia
        mock_google.return_value = []
        mock_ddg.return_value = []
        res_google_empty = search_images("miocárdio", engine="google")
        self.assertEqual(res_google_empty, [])
        mock_google.assert_called_once()
        mock_ddg.assert_called_once()
        mock_wikipedia.assert_not_called()
        mock_wikimedia.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_duckduckgo_vqd_regex(self, mock_urlopen):
        """
        Validates that modern DuckDuckGo vqd tokens containing alphanumeric characters,
        hyphens, and underscores are extracted properly via regex patterns.
        """
        # Test 1: Direct regex extraction across various modern DDG HTML payload formats
        modern_vqd_samples = [
            ('<html><script>vqd=4-12345678901234567890123456789012&other=1</script></html>', '4-12345678901234567890123456789012'),
            ('<html><div vqd="4-25381643919485720194827394857201"></div></html>', '4-25381643919485720194827394857201'),
            ('<script>vqd="3-2194832948239048-2948209348";</script>', '3-2194832948239048-2948209348'),
            ('{vqd: "4-abc123DEF_xyz-7890"}', '4-abc123DEF_xyz-7890'),
            ("vqd: '4-9876543210-abcdef'", '4-9876543210-abcdef'),
        ]

        for sample_html, expected_vqd in modern_vqd_samples:
            match = (
                re.search(r'vqd=([0-9a-zA-Z_-]+)', sample_html)
                or re.search(r'vqd="([0-9a-zA-Z_-]+)"', sample_html)
                or re.search(r'vqd:\s*["\']([^"\']+)["\']', sample_html)
            )
            self.assertIsNotNone(match, f"Failed to match vqd in: {sample_html}")
            extracted = match.group(1)
            self.assertEqual(extracted, expected_vqd)

        # Test 2: Functional search_duckduckgo_images execution with mock response
        token_html = '<html><script>vqd="4-998877665544332211-alpha-beta";</script></html>'
        api_json = {
            "results": [
                {
                    "title": "Pancreas CT Scan",
                    "image": "https://example.com/pancreas_ct.jpg",
                    "thumbnail": "https://example.com/thumb_ct.jpg",
                    "width": 1200,
                    "height": 900,
                    "url": "https://radiologycases.com",
                }
            ]
        }

        mock_token_resp = MagicMock()
        mock_token_resp.read.return_value = token_html.encode("utf-8")
        mock_token_resp.headers = {}
        mock_token_resp.__enter__.return_value = mock_token_resp

        mock_api_resp = MagicMock()
        mock_api_resp.read.return_value = json.dumps(api_json).encode("utf-8")
        mock_api_resp.__enter__.return_value = mock_api_resp

        mock_urlopen.side_effect = [mock_token_resp, mock_api_resp]

        ddg_results = search_duckduckgo_images("Pancreas CT")
        self.assertEqual(len(ddg_results), 1)
        self.assertEqual(ddg_results[0].title, "Pancreas CT Scan")

        # Verify that second call to urlopen passed the captured modern vqd token in the URL
        self.assertEqual(mock_urlopen.call_count, 2)
        second_call_req = mock_urlopen.call_args_list[1][0][0]
        second_url = second_call_req.full_url if hasattr(second_call_req, "full_url") else str(second_call_req)
        self.assertIn("vqd=4-998877665544332211-alpha-beta", second_url)

    @patch("modules.image_search.search_engine.search_duckduckgo_images")
    @patch("modules.image_search.search_engine.search_google_images")
    @patch("modules.image_search.search_engine.search_wikipedia_articles")
    @patch("modules.image_search.search_engine.search_wikimedia")
    def test_combined_mode_filters_negative_scores(
        self,
        mock_wikimedia,
        mock_wikipedia,
        mock_google,
        mock_ddg,
    ):
        """
        Validates that in engine='all', items with relevance_score < 0
        are strictly filtered out and never appear in the final results,
        while remaining items are sorted strictly by relevance_score descending.
        """
        item_web_good = ImageResultItem(
            title="Apendicite aguda ultrassom",
            thumb_url="https://example.com/thumb1.jpg",
            original_url="https://example.com/good1.jpg",
            source="radiopaedia.org",
            relevance_score=65,
        )
        item_web_spam = ImageResultItem(
            title="Wallpaper royalty free stock apendicite",
            thumb_url="https://example.com/thumb2.jpg",
            original_url="https://example.com/spam.jpg",
            source="shutterstock.com",
            relevance_score=-50,
        )
        item_wiki_good = ImageResultItem(
            title="Apendicite - Anatomia Patológica",
            thumb_url="https://example.com/thumb3.jpg",
            original_url="https://example.com/wiki_good.jpg",
            source="https://pt.wikipedia.org/wiki/Apendicite",
            relevance_score=85,
        )
        item_wiki_negative = ImageResultItem(
            title="Descartado irrelevante",
            thumb_url="https://example.com/thumb4.jpg",
            original_url="https://example.com/wiki_bad.jpg",
            source="https://pt.wikipedia.org/wiki/Descartado",
            relevance_score=-10,
        )
        item_commons_good = ImageResultItem(
            title="Appendix inflammation diagram",
            thumb_url="https://example.com/thumb5.jpg",
            original_url="https://example.com/commons_good.jpg",
            source="https://commons.wikimedia.org/wiki/File:Appendix.svg",
            relevance_score=40,
        )
        item_commons_negative = ImageResultItem(
            title="Commons negative score asset",
            thumb_url="https://example.com/thumb6.jpg",
            original_url="https://example.com/commons_bad.jpg",
            source="https://commons.wikimedia.org/wiki/File:Bad.svg",
            relevance_score=-5,
        )

        mock_google.return_value = [item_web_good, item_web_spam]
        mock_wikipedia.return_value = [item_wiki_good, item_wiki_negative]
        mock_wikimedia.return_value = [item_commons_good, item_commons_negative]
        mock_ddg.return_value = []

        combined_results = search_images("apendicite aguda", engine="all")

        # Check that none of the items with negative score made it through
        result_urls = [item.original_url for item in combined_results]
        self.assertNotIn("https://example.com/spam.jpg", result_urls)
        self.assertNotIn("https://example.com/wiki_bad.jpg", result_urls)
        self.assertNotIn("https://example.com/commons_bad.jpg", result_urls)

        # Check that all returned items have relevance_score >= 0
        for item in combined_results:
            self.assertGreaterEqual(
                item.relevance_score, 0,
                f"Item '{item.title}' has negative relevance_score: {item.relevance_score}"
            )

        # Check total passing items (should be exactly 3: wiki_good, web_good, commons_good)
        self.assertEqual(len(combined_results), 3)

        # Verify strict descending order by relevance_score:
        # 85 (wiki_good) -> 65 (web_good) -> 40 (commons_good)
        expected_scores = [85, 65, 40]
        actual_scores = [item.relevance_score for item in combined_results]
        self.assertEqual(actual_scores, expected_scores)
        self.assertEqual(combined_results[0].original_url, "https://example.com/wiki_good.jpg")
        self.assertEqual(combined_results[1].original_url, "https://example.com/good1.jpg")
        self.assertEqual(combined_results[2].original_url, "https://example.com/commons_good.jpg")

    def test_resolve_source_url(self):
        """
        Validates resolution of item.source:
        1. Complete URL (http:// or https://) is preserved.
        2. Bare domain (e.g. 'radiopaedia.org') is prepended with 'https://'.
        3. Empty, invalid or missing source falls back to item.original_url.
        4. None item returns empty string.
        Tested on both ImageSearchDialog._resolve_source_url and ImageCardWidget._resolve_source_url.
        """
        # Case 1: Complete HTTPS URL
        item_https = ImageResultItem(
            title="Artigo Wikipedia",
            thumb_url="https://upload.wikimedia.org/thumb.jpg",
            original_url="https://upload.wikimedia.org/orig.jpg",
            source="https://pt.wikipedia.org/wiki/Apendicite",
        )
        self.assertEqual(
            ImageSearchDialog._resolve_source_url(None, item_https),
            "https://pt.wikipedia.org/wiki/Apendicite",
        )
        card_https = ImageCardWidget(item_https)
        self.assertEqual(card_https._resolve_source_url(), "https://pt.wikipedia.org/wiki/Apendicite")

        # Case 2: Complete HTTP URL
        item_http = ImageResultItem(
            title="Caso Clínico",
            thumb_url="http://example.com/thumb.jpg",
            original_url="http://example.com/orig.jpg",
            source="http://medline.org/article/123",
        )
        self.assertEqual(
            ImageSearchDialog._resolve_source_url(None, item_http),
            "http://medline.org/article/123",
        )
        card_http = ImageCardWidget(item_http)
        self.assertEqual(card_http._resolve_source_url(), "http://medline.org/article/123")

        # Case 3: Bare domain without protocol
        item_domain = ImageResultItem(
            title="Radiopaedia Scan",
            thumb_url="https://radiopaedia.org/thumb.jpg",
            original_url="https://radiopaedia.org/cases/scan.jpg",
            source="radiopaedia.org",
        )
        self.assertEqual(
            ImageSearchDialog._resolve_source_url(None, item_domain),
            "https://radiopaedia.org",
        )
        card_domain = ImageCardWidget(item_domain)
        self.assertEqual(card_domain._resolve_source_url(), "https://radiopaedia.org")

        # Case 4: Subdomain without protocol
        item_subdomain = ImageResultItem(
            title="Medscape Article",
            thumb_url="https://img.medscape.com/thumb.jpg",
            original_url="https://img.medscape.com/large.jpg",
            source="img.medscape.com",
        )
        self.assertEqual(
            ImageSearchDialog._resolve_source_url(None, item_subdomain),
            "https://img.medscape.com",
        )
        card_subdomain = ImageCardWidget(item_subdomain)
        self.assertEqual(card_subdomain._resolve_source_url(), "https://img.medscape.com")

        # Case 5: Empty source falls back to original_url
        item_empty_source = ImageResultItem(
            title="No Source Image",
            thumb_url="https://cdn.example.com/thumb.png",
            original_url="https://cdn.example.com/actual_full_image.png",
            source="",
        )
        self.assertEqual(
            ImageSearchDialog._resolve_source_url(None, item_empty_source),
            "https://cdn.example.com/actual_full_image.png",
        )
        card_empty = ImageCardWidget(item_empty_source)
        self.assertEqual(card_empty._resolve_source_url(), "https://cdn.example.com/actual_full_image.png")

        # Case 6: Source with invalid string (contains spaces, not a valid domain) falls back to original_url
        item_invalid_source = ImageResultItem(
            title="Text description source",
            thumb_url="https://cdn.example.com/thumb.png",
            original_url="https://cdn.example.com/fallback.jpg",
            source="Google Images Medical Result",
        )
        self.assertEqual(
            ImageSearchDialog._resolve_source_url(None, item_invalid_source),
            "https://cdn.example.com/fallback.jpg",
        )
        card_invalid = ImageCardWidget(item_invalid_source)
        self.assertEqual(card_invalid._resolve_source_url(), "https://cdn.example.com/fallback.jpg")

        # Case 7: None item returns empty string
        self.assertEqual(ImageSearchDialog._resolve_source_url(None, None), "")
        card_none = ImageCardWidget(None)
        self.assertEqual(card_none._resolve_source_url(), "")


if __name__ == "__main__":
    unittest.main()
