# -*- coding: utf-8 -*-
"""
Unit tests for Modern Stats Dashboard Engine & Renderer.
"""

import unittest
import sqlite3
import time
from modules.dashboard.stats_engine import compute_dashboard_stats, format_duration
from modules.dashboard.renderer import render_dashboard_html


class MockDeckManager:
    def __init__(self, decks):
        self._decks = {d["id"]: d for d in decks}

    def get(self, did):
        return self._decks.get(did)

    def all(self):
        return list(self._decks.values())

    def config_dict_for_deck_id(self, did):
        return {"new": {"perDay": 20}, "rev": {"perDay": 200}}


class MockSched:
    def __init__(self, day_cutoff_sec):
        self.day_cutoff = day_cutoff_sec
        self.today = int(day_cutoff_sec / 86400)


class MockCol:
    def __init__(self, db_conn, decks, day_cutoff_sec):
        self.db = db_conn
        self.decks = MockDeckManager(decks)
        self.sched = MockSched(day_cutoff_sec)


class MockDbWrapper:
    """Wrapper matching Anki's col.db interface."""
    def __init__(self, conn):
        self.conn = conn

    def all(self, sql, *args, **kwargs):
        cur = self.conn.cursor()
        cur.execute(sql, args)
        return cur.fetchall()

    def first(self, sql, *args, **kwargs):
        rows = self.all(sql, *args, **kwargs)
        return rows[0] if rows else None


class TestDashboardStats(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE revlog (
                id INTEGER PRIMARY KEY,
                cid INTEGER,
                usn INTEGER,
                ease INTEGER,
                time INTEGER,
                factor INTEGER,
                lastIvl INTEGER,
                ivl INTEGER,
                type INTEGER
            )
        """)

        cur.execute("""
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY,
                nid INTEGER,
                did INTEGER,
                ord INTEGER,
                mod INTEGER,
                usn INTEGER,
                type INTEGER,
                queue INTEGER,
                due INTEGER,
                ivl INTEGER,
                factor INTEGER,
                reps INTEGER,
                lapses INTEGER,
                left INTEGER,
                odue INTEGER,
                odid INTEGER
            )
        """)

        now_sec = time.time()
        self.day_cutoff_sec = now_sec + 82800
        start_of_day_ms = int((now_sec - 3600) * 1000)

        self.raw_decks = [
            {"id": 1, "name": "Medicina"},
            {"id": 2, "name": "Medicina::Farmacologia"},
            {"id": 3, "name": "Idiomas"},
        ]

        # Populate Cards
        cur.executemany("""
            INSERT INTO cards (id, did, queue, due, ivl, odid) VALUES (?, ?, ?, ?, ?, 0)
        """, [
            (101, 1, 0, 1, 0),
            (102, 1, 0, 2, 0),
            (103, 1, 2, 10, 25),  # mature (ivl 25 >= 21)
            (104, 1, 2, 11, 5),   # young, tomorrow
            (201, 2, 0, 3, 0),
            (202, 2, 0, 4, 0),
            (203, 2, 0, 5, 0),
            (204, 2, 1, 10, 0),   # learn
            (205, 2, 1, 10, 0),   # learn
            (301, 3, 0, 6, 0),
            (302, 3, 0, 7, 0),
            (303, 3, 0, 8, 0),
            (304, 3, 0, 9, 0),
            (305, 3, 0, 10, 0),
            (306, 3, 2, 10, 10),  # young (ivl 10 < 21)
            (307, 3, 2, 10, 30),  # mature
            (308, 3, 2, 10, 45),  # mature
            (309, 3, 2, 10, 60),  # mature
        ])

        # Populate Revlog for today (> start_of_day_ms)
        # Card 103 (Medicina): 2 reviews (ease 3, ease 4, type 1) -> 2 passes, total 10s
        # Card 204 (Farmacologia): 1 review (ease 1, type 0, lastIvl 0) -> 1 again, total 8s
        # Card 306 (Idiomas): 1 review (ease 3, type 1, lastIvl 5) -> 1 pass, total 12s
        cur.executemany("""
            INSERT INTO revlog (id, cid, ease, time, type, lastIvl, ivl) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (start_of_day_ms + 1000, 103, 3, 6000, 1, 20, 25),
            (start_of_day_ms + 2000, 103, 4, 4000, 1, 25, 35),
            (start_of_day_ms + 3000, 204, 1, 8000, 0, 0, 0),
            (start_of_day_ms + 4000, 306, 3, 12000, 1, 5, 10),
        ])

        self.conn.commit()
        self.col = MockCol(MockDbWrapper(self.conn), self.raw_decks, self.day_cutoff_sec)
        self.col.sched.today = 10

    def test_global_collection_stats(self):
        stats = compute_dashboard_stats(self.col, deck_id=None)
        self.assertFalse(stats.is_per_deck)
        self.assertEqual(stats.today.studied_count, 4)
        self.assertEqual(stats.today.time_spent_seconds, 30.0)
        self.assertEqual(stats.today.seconds_per_card, 7.5)
        self.assertEqual(stats.today.cards_per_minute, 8.0)
        self.assertEqual(stats.today.retention_rate_pct, 75.0)
        self.assertEqual(stats.done.again_count, 1)
        self.assertEqual(stats.done.new_learned, 1)
        self.assertEqual(stats.done.review_reps, 3)
        self.assertEqual(stats.remaining.new_cards, 10)
        self.assertEqual(stats.remaining.learn_cards, 2)
        self.assertEqual(stats.remaining.review_cards, 5)
        self.assertEqual(stats.remaining.total_remaining, 17)
        self.assertEqual(stats.composition.total_cards, 18)

    def test_per_deck_subtree_stats(self):
        # Query Medicina (ID 1), which should include Medicina::Farmacologia (ID 2)
        stats = compute_dashboard_stats(self.col, deck_id=1)
        self.assertTrue(stats.is_per_deck)
        self.assertEqual(stats.deck_name, "Medicina")
        self.assertEqual(stats.today.studied_count, 3)  # 2 on 103, 1 on 204
        self.assertEqual(stats.today.time_spent_seconds, 18.0)
        self.assertEqual(stats.done.again_count, 1)
        self.assertEqual(stats.done.new_learned, 1)
        self.assertEqual(stats.done.review_reps, 2)
        self.assertEqual(stats.remaining.new_cards, 5)  # 2 in deck 1 + 3 in deck 2
        self.assertEqual(stats.remaining.learn_cards, 2)  # 2 in deck 2
        self.assertEqual(stats.remaining.review_cards, 1)  # 1 in deck 1
        self.assertEqual(stats.remaining.total_remaining, 8)
        self.assertEqual(stats.composition.total_cards, 9)

    def test_leaf_subdeck_stats(self):
        # Query Medicina::Farmacologia (ID 2) only
        stats = compute_dashboard_stats(self.col, deck_id=2)
        self.assertTrue(stats.is_per_deck)
        self.assertEqual(stats.deck_name, "Medicina::Farmacologia")
        self.assertEqual(stats.today.studied_count, 1)
        self.assertEqual(stats.today.time_spent_seconds, 8.0)
        self.assertEqual(stats.done.again_count, 1)
        self.assertEqual(stats.done.new_learned, 1)
        self.assertEqual(stats.done.review_reps, 0)
        self.assertEqual(stats.remaining.new_cards, 3)
        self.assertEqual(stats.remaining.learn_cards, 2)
        self.assertEqual(stats.remaining.review_cards, 0)
        self.assertEqual(stats.remaining.total_remaining, 5)

    def test_format_duration(self):
        self.assertEqual(format_duration(45), "45s")
        self.assertEqual(format_duration(60), "1m")
        self.assertEqual(format_duration(125), "2m 05s")
        self.assertEqual(format_duration(3600), "1h 00m")
        self.assertEqual(format_duration(3750), "1h 02m")

    def test_renderer_output(self):
        from utils.i18n import set_language_override
        stats = compute_dashboard_stats(self.col, deck_id=1)
        config = {
            "show_daily_goals": True,
            "show_deck_composition": True,
            "show_today_progress": True,
            "show_remaining": True,
            "show_done_today": True,
            "layout_columns": 3,
        }

        # Test Portuguese
        set_language_override("pt")
        html_pt = render_dashboard_html(stats, config)
        self.assertIn("dash-card", html_pt)
        self.assertIn("Progresso de Hoje", html_pt)
        self.assertIn("Metas", html_pt)
        self.assertIn("Acervo Total", html_pt)
        self.assertIn("Medicina", html_pt)

        # Test English
        set_language_override("en")
        html_en = render_dashboard_html(stats, config)
        self.assertIn("dash-card", html_en)
        self.assertIn("Today's Progress", html_en)
        self.assertIn("Daily Goals", html_en)
        self.assertIn("Deck Collection", html_en)

        set_language_override(None)


if __name__ == "__main__":
    unittest.main()
