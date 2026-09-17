# -*- coding: utf-8 -*-
"""
Unit tests for Image Search Pagination, Infinite Scroll State, and Radiological Precision.

Coverage:
1. test_pagination_offset_calculation:
   Validates calculation of start=... (Google Images) and gsroffset=... (Wikimedia) across page 1, 2, 3.
2. test_radiological_query_expansion:
   Validates canonical phrase expansions (e.g. 'pancreatite necrotizante tomografia contraste'
   -> 'contrast-enhanced CT', 'CECT', 'necrotizing pancreatitis').
3. test_preserve_two_letter_medical_acronyms:
   Validates that 2-letter medical acronyms ('TC', 'RM', 'CT', 'US', 'RX', 'MR') are preserved
   and not stripped during token extraction or scoring.
4. test_safesearch_relaxation_for_pathology:
   Validates that pathological/radiological queries relax SafeSearch to 'safe=off'
   to avoid censorship of necrotic tissue and clinical scans.
5. test_radiology_relevance_scoring_boost:
   Validates relevance scoring boosts (+25/+30) for radiological terms ('CT', 'tomografia', 'contrast')
   and high-authority domains like 'radiopaedia.org'.
6. test_infinite_scroll_state_resets:
   Validates integrity of pagination state (_current_page, _is_loading_more, _has_more_results, _seen_urls)
   across initial queries, page increments, duplicate filtering, and new search resets.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import re

from modules.image_search.search_engine import (
    ImageResultItem,
    search_web_images,
    search_google_images,
    search_wikimedia,
    _fetch_bing_raw,
    _fetch_google_html,
    _get_medical_synonyms,
    _build_translated_medical_query,
    _is_medical_or_pathological_query,
    _calculate_relevance_score,
    KNOWN_MEDICAL_2LETTER_WORDS,
)
from modules.image_search.ui.search_dialog import ImageSearchDialog


class TestImageSearchPagination(unittest.TestCase):
    """
    Test suite for pagination mechanics, infinite scroll state integrity,
    and radiological domain accuracy.
    """

    # -------------------------------------------------------------------------
    # 1. PAGINATION OFFSET CALCULATION
    # -------------------------------------------------------------------------
    def test_pagination_offset_calculation(self):
        """
        Validate offset calculations across multiple pages:
        - Web Images: first_idx = 1 + (page - 1) * max_results
        - Wikimedia: gsroffset = (page - 1) * max_results
        """
        # A. Web Images offset calculations (first_idx)
        with patch("modules.image_search.search_engine._fetch_bing_raw", return_value="") as mock_fetch:
            # Page 1 (max_results=40): first = 1
            search_web_images("pancreas", max_results=40, page=1)
            call_args = mock_fetch.call_args[0]
            self.assertEqual(call_args[1], 1)  # first_idx = 1

            # Page 2 (max_results=40): first = 41
            search_web_images("pancreas", max_results=40, page=2)
            call_args = mock_fetch.call_args[0]
            self.assertEqual(call_args[1], 41)  # first_idx = 41

            # Page 3 (max_results=40): first = 81
            search_web_images("pancreas", max_results=40, page=3)
            call_args = mock_fetch.call_args[0]
            self.assertEqual(call_args[1], 81)  # first_idx = 81

            # Page 2 with max_results=50: first = 51
            search_web_images("pancreas", max_results=50, page=2)
            call_args = mock_fetch.call_args[0]
            self.assertEqual(call_args[1], 51)  # first_idx = 51

        # Verify Web URL formatting in _fetch_bing_raw directly
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"<html><body></body></html>"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            _fetch_bing_raw("pancreas", first_idx=41, adlt_param="&adlt=off")
            req = mock_urlopen.call_args[0][0]
            self.assertIn("first=41", req.full_url)
            self.assertIn("adlt=off", req.full_url)

        # B. Wikimedia Commons offset calculations (gsroffset)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"query": {"pages": {}}}).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            # Page 1 (max_results=40): offset = 0 -> gsroffset=0
            search_wikimedia("mitochondria", max_results=40, page=1)
            wiki_calls_p1 = [c[0][0] for c in mock_urlopen.call_args_list if "commons.wikimedia.org" in getattr(c[0][0], "full_url", "")]
            self.assertTrue(wiki_calls_p1)
            self.assertIn("gsroffset=0", wiki_calls_p1[-1].full_url)

            # Page 2 (max_results=40): offset = 40 -> gsroffset=40
            search_wikimedia("mitochondria", max_results=40, page=2)
            wiki_calls_p2 = [c[0][0] for c in mock_urlopen.call_args_list if "commons.wikimedia.org" in getattr(c[0][0], "full_url", "")]
            self.assertTrue(wiki_calls_p2)
            self.assertIn("gsroffset=40", wiki_calls_p2[-1].full_url)

            # Page 3 (max_results=40): offset = 80 -> gsroffset=80
            search_wikimedia("mitochondria", max_results=40, page=3)
            wiki_calls_p3 = [c[0][0] for c in mock_urlopen.call_args_list if "commons.wikimedia.org" in getattr(c[0][0], "full_url", "")]
            self.assertTrue(wiki_calls_p3)
            self.assertIn("gsroffset=80", wiki_calls_p3[-1].full_url)

    # -------------------------------------------------------------------------
    # 2. RADIOLOGICAL QUERY EXPANSION
    # -------------------------------------------------------------------------
    def test_radiological_query_expansion(self):
        """
        Validate that radiological queries with anatomical qualifiers generate canonical
        English search terms such as 'contrast-enhanced CT', 'CECT', and 'necrotizing pancreatitis'.
        """
        # 1. Specialized phrase translation helper
        translated = _build_translated_medical_query("pancreatite necrotizante tomografia contraste")
        self.assertIn("necrotizing pancreatitis", translated)
        self.assertIn("contrast-enhanced CT", translated)

        translated_com_contraste = _build_translated_medical_query("pancreatite necrotizante tomografia com contraste")
        self.assertIn("necrotizing pancreatitis", translated_com_contraste)
        self.assertIn("contrast-enhanced CT", translated_com_contraste)

        translated_tc = _build_translated_medical_query("tc contraste")
        self.assertEqual(translated_tc, "contrast-enhanced CT")

        translated_rm = _build_translated_medical_query("rm com contraste")
        self.assertEqual(translated_rm, "contrast-enhanced MRI")

        # 2. Full synonym expansion integration
        syns_pancreatite = _get_medical_synonyms("pancreatite necrotizante tomografia contraste")
        self.assertTrue(
            any("necrotizing pancreatitis" in s for s in syns_pancreatite),
            f"Expected 'necrotizing pancreatitis' in {syns_pancreatite}",
        )
        self.assertTrue(
            any("contrast-enhanced CT" in s or "CECT" in s for s in syns_pancreatite),
            f"Expected 'contrast-enhanced CT' or 'CECT' in {syns_pancreatite}",
        )

        syns_tc_contraste = _get_medical_synonyms("tomografia contraste")
        self.assertTrue(any("contrast-enhanced CT" in s for s in syns_tc_contraste))
        self.assertTrue(any("CECT" in s for s in syns_tc_contraste))

        syns_rm = _get_medical_synonyms("ressonancia magnetica")
        self.assertTrue(any("MRI" in s for s in syns_rm))

    # -------------------------------------------------------------------------
    # 3. PRESERVE TWO-LETTER MEDICAL ACRONYMS
    # -------------------------------------------------------------------------
    def test_preserve_two_letter_medical_acronyms(self):
        """
        Validate that 2-letter clinical acronyms ('TC', 'RM', 'CT', 'US', 'RX', 'MR')
        are not discarded during tokenization and medical classification.
        """
        # Check dictionary presence
        expected_acronyms = {"tc", "rm", "ct", "us", "rx", "mr"}
        self.assertTrue(expected_acronyms.issubset(KNOWN_MEDICAL_2LETTER_WORDS))

        # Check medical query detection recognizes 2-letter acronyms with boundary matching
        self.assertTrue(_is_medical_or_pathological_query("TC de abdome"))
        self.assertTrue(_is_medical_or_pathological_query("RM cranio"))
        self.assertTrue(_is_medical_or_pathological_query("US pelvica"))
        self.assertTrue(_is_medical_or_pathological_query("RX torax"))
        self.assertFalse(_is_medical_or_pathological_query("gato de rua"))

        # Check token extraction preserving 2-letter medical acronyms while ignoring generic short words
        clean_query = "TC e RM de abdome"
        query_words = [
            w.lower() for w in re.findall(r"\w+", clean_query)
            if len(w) > 2 or w.lower() in KNOWN_MEDICAL_2LETTER_WORDS
        ]
        self.assertIn("tc", query_words)
        self.assertIn("rm", query_words)
        self.assertIn("abdome", query_words)
        # 'e' (1 letter) and 'de' (2 letters, non-medical) must be excluded
        self.assertNotIn("e", query_words)
        self.assertNotIn("de", query_words)

        # Check relevance scoring incorporates 2-letter acronyms
        score = _calculate_relevance_score(
            title="TC de Torax Normal e Patologico",
            source="https://radiopaedia.org/cases/1",
            query_words=["tc", "torax"],
            is_anatomical=True,
        )
        self.assertGreater(score, 0)

    # -------------------------------------------------------------------------
    # 4. SAFESEARCH RELAXATION FOR PATHOLOGY
    # -------------------------------------------------------------------------
    def test_safesearch_relaxation_for_pathology(self):
        """
        Validate that queries containing pathological or radiological terms
        ('necro', 'tomografia', 'pancreat') relax SafeSearch to 'adlt=off'
        to prevent clinical censorship.
        """
        test_queries = [
            "pancreatite necrotizante",
            "tomografia computadorizada",
            "necrose de coagulacao",
            "TC de abdome agudo",
        ]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"<html><body></body></html>"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            for query in test_queries:
                mock_urlopen.reset_mock()
                search_web_images(query, max_results=10, safe_search=False)
                self.assertTrue(mock_urlopen.called, f"Expected urlopen called for '{query}'")

                web_calls = [c[0][0] for c in mock_urlopen.call_args_list if "bing.com" in getattr(c[0][0], "full_url", "")]
                self.assertTrue(web_calls, f"Expected web call for '{query}'")
                req = web_calls[0]
                self.assertIn("adlt=off", req.full_url, f"Expected adlt=off in URL for '{query}'")
                cookie_hdr = req.headers.get("Cookie", "") or req.unredirected_hdrs.get("Cookie", "")
                self.assertIn("ADLT=OFF", cookie_hdr, f"Expected ADLT=OFF in Cookie for '{query}'")

            # Validate that a generic non-medical query with safe_search=True enforces strict SafeSearch (no adlt=off)
            mock_urlopen.reset_mock()
            search_web_images("paisagem montanhas flores", max_results=10, safe_search=True)
            self.assertTrue(mock_urlopen.called)
            web_calls_strict = [c[0][0] for c in mock_urlopen.call_args_list if "bing.com" in getattr(c[0][0], "full_url", "")]
            self.assertTrue(web_calls_strict)
            req_strict = web_calls_strict[0]
            self.assertNotIn("adlt=off", req_strict.full_url)
            self.assertIn("adlt=moderate", req_strict.full_url)

    # -------------------------------------------------------------------------
    # 5. RADIOLOGY RELEVANCE SCORING BOOST
    # -------------------------------------------------------------------------
    def test_radiology_relevance_scoring_boost(self):
        """
        Validate that items from authoritative radiological repositories (e.g. 'radiopaedia.org')
        and containing radiological imaging keywords ('CT', 'tomografia', 'contrast') receive
        a substantial relevance score boost.
        """
        # Item from Radiopaedia with CT and contrast
        score_radiopaedia = _calculate_relevance_score(
            title="Necrotizing pancreatitis with acute necrotic collection on contrast-enhanced CT",
            source="https://radiopaedia.org/cases/acute-necrotizing-pancreatitis",
            query_words=["pancreatite", "necrotizante", "tomografia", "contraste"],
            synonyms=["necrotizing pancreatitis", "contrast-enhanced CT"],
            is_anatomical=True,
        )

        # Generic blog with no radiological keywords and non-authoritative domain
        score_generic = _calculate_relevance_score(
            title="Pancreas anatomy and common diseases blog overview",
            source="https://example-blog.org/pancreas-overview",
            query_words=["pancreatite", "necrotizante", "tomografia", "contraste"],
            synonyms=["pancreatitis"],
            is_anatomical=True,
        )

        # Radiopaedia case must score significantly higher (+30 domain boost + +25 radiological boost)
        self.assertGreater(score_radiopaedia, score_generic + 30)
        self.assertGreater(score_radiopaedia, 50)

        # Contrast-enhanced CT item vs unboosted item from same generic domain
        score_ct = _calculate_relevance_score(
            title="Abdominal CT scan with contrast enhancement",
            source="https://medical-archive.net/case/1",
            query_words=["tomografia", "contraste"],
            synonyms=["contrast-enhanced CT", "contrast CT scan"],
            is_anatomical=True,
        )
        score_unboosted = _calculate_relevance_score(
            title="Abdominal visual overview without contrast enhancement",
            source="https://medical-archive.net/case/2",
            query_words=["tomografia", "contraste"],
            synonyms=["contrast-enhanced CT", "contrast CT scan"],
            is_anatomical=True,
        )
        self.assertGreater(score_ct, score_unboosted)

    # -------------------------------------------------------------------------
    # 6. INFINITE SCROLL STATE RESETS
    # -------------------------------------------------------------------------
    def test_infinite_scroll_state_resets(self):
        """
        Validate that ImageSearchDialog pagination attributes
        (_current_page, _is_loading_more, _has_more_results, _seen_urls)
        maintain integrity during initial query, page increment, and new search reset.
        """
        mock_editor = MagicMock(name="MockEditor")
        dialog = ImageSearchDialog.__new__(ImageSearchDialog)
        dialog.editor = mock_editor
        dialog.saved_field_index = 0
        dialog._current_page = 1
        dialog._is_loading_more = False
        dialog._has_more_results = True
        dialog._seen_urls = set()
        dialog.current_results = []
        dialog.grid_layout = MagicMock()
        dialog.grid_layout.count.return_value = 0
        dialog.cards_container = MagicMock()
        dialog.footer_loading_widget = MagicMock()
        dialog.lbl_footer_loading = MagicMock()
        dialog.lbl_status = MagicMock()
        dialog.progress_bar = MagicMock()
        dialog.btn_search = MagicMock()
        dialog.scroll_area = MagicMock()
        dialog.stacked_widget = MagicMock()
        dialog.search_signals = MagicMock()
        dialog.search_input = MagicMock()
        dialog.engine_combo = MagicMock()

        # 1. Initial state verification
        self.assertEqual(dialog._current_page, 1)
        self.assertFalse(dialog._is_loading_more)
        self.assertTrue(dialog._has_more_results)
        self.assertEqual(len(dialog._seen_urls), 0)

        # 2. Initial search results ready (Page 1: 2 items)
        item1 = ImageResultItem(title="CT Scan 1", thumb_url="t1", original_url="https://img.com/1.jpg")
        item2 = ImageResultItem(title="CT Scan 2", thumb_url="t2", original_url="https://img.com/2.jpg")
        dialog._on_search_results_ready([item1, item2])

        self.assertEqual(len(dialog.current_results), 2)
        self.assertIn("https://img.com/1.jpg", dialog._seen_urls)
        self.assertIn("https://img.com/2.jpg", dialog._seen_urls)
        self.assertTrue(dialog._has_more_results)
        self.assertFalse(dialog._is_loading_more)

        # 3. Infinite scroll increments page (Page 2: 2 new items + 1 duplicate)
        item3 = ImageResultItem(title="CT Scan 3", thumb_url="t3", original_url="https://img.com/3.jpg")
        item4 = ImageResultItem(title="CT Scan 4", thumb_url="t4", original_url="https://img.com/4.jpg")
        duplicate = ImageResultItem(title="CT Scan 1 Dup", thumb_url="t1", original_url="https://img.com/1.jpg")

        dialog._is_loading_more = True
        dialog._on_more_results_ready([item3, item4, duplicate], page=2)

        self.assertEqual(dialog._current_page, 2)
        self.assertFalse(dialog._is_loading_more)
        self.assertTrue(dialog._has_more_results)
        # Duplicate url was filtered; 2 original + 2 new = 4 total
        self.assertEqual(len(dialog.current_results), 4)
        self.assertEqual(len(dialog._seen_urls), 4)

        # 4. End of results when an empty page is returned
        dialog._is_loading_more = True
        dialog._on_more_results_ready([], page=3)
        self.assertFalse(dialog._has_more_results)
        self.assertFalse(dialog._is_loading_more)

        # 5. New search initiation resets all pagination attributes
        dialog.search_input.text.return_value = "nova busca radiologica"
        dialog.engine_combo.currentData.return_value = "all"
        with patch("threading.Thread") as mock_thread:
            dialog.do_search()

        self.assertEqual(dialog._current_page, 1)
        self.assertFalse(dialog._is_loading_more)
        self.assertTrue(dialog._has_more_results)
        self.assertEqual(len(dialog._seen_urls), 0)

    def test_peripancreatic_fluid_query_expansion_and_scoring(self):
        """
        Validates that 'fluido peripancreático' and accented medical terms
        are accurately detected as medical, translated to canonical English,
        and scored with high relevance on clinical/radiological items.
        """
        from modules.image_search.search_engine import (
            _is_medical_or_pathological_query,
            _build_translated_medical_query,
            _get_medical_synonyms,
            _calculate_relevance_score,
            _strip_accents,
        )

        q = "fluido peripancreático"
        self.assertTrue(_is_medical_or_pathological_query(q))
        self.assertEqual(_strip_accents(q), "fluido peripancreatico")

        en_trans = _build_translated_medical_query(q)
        self.assertEqual(en_trans, "peripancreatic fluid collection")

        syns = _get_medical_synonyms(q)
        self.assertIn("peripancreatic fluid collection", syns)
        self.assertIn("acute peripancreatic fluid collection", syns)

        # High authority ResearchGate / clinical CT item scoring
        score = _calculate_relevance_score(
            title="CT scan showing peripancreatic fluid collection abutting the gastric wall",
            source="https://www.researchgate.net/figure/CT-scan-showing-peripancreatic",
            query_words=["fluido", "peripancreático"],
            is_anatomical=True,
            synonyms=syns,
        )
        self.assertGreaterEqual(score, 50)


if __name__ == "__main__":
    unittest.main()
