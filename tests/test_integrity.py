# -*- coding: utf-8 -*-
"""
Unit tests for the DNA-style Proofreading & Verification Engine (integrity.py).
Tests:
1. Flawless collection verification (closed block contiguity, monotonicity, unique due sequence).
2. Interleaving / fragmentation detection and in-flight atomic repair.
3. Priority monotonicity violation detection and repair.
4. Due collision detection and sequence normalization.
5. IntegrityReport computed properties (is_flawless, status_badge).
"""

import unittest
from typing import List, Tuple, Dict, Any

from core.models import DeckNode, IntegrityReport, CardItem
from core.hierarchy import build_deck_tree
from core.integrity import verify_and_repair_card_order


class MockDB:
    """In-memory SQLite mock for testing collection reordering and integrity verification."""

    def __init__(self, rows: List[Tuple[int, int, int]]):
        self.rows: Dict[int, Tuple[int, int, int]] = {r[0]: r for r in rows}
        self.save_called = False

    def all(self, query: str):
        if "FROM cards WHERE queue = 0" in query:
            sorted_cards = sorted(self.rows.values(), key=lambda r: (r[2], r[0]))
            return sorted_cards
        return []

    def scalar(self, query: str):
        if "count()" in query and "queue = 0" in query:
            return len(self.rows)
        return 0

    def executemany(self, query: str, params_list):
        if "UPDATE cards SET due = ?, mod = ? WHERE id = ?" in query:
            for new_due, mod_time, cid in params_list:
                if cid in self.rows:
                    _, did, _ = self.rows[cid]
                    self.rows[cid] = (cid, did, new_due)

    def save(self):
        self.save_called = True


class MockCol:
    def __init__(self, rows: List[Tuple[int, int, int]]):
        self.db = MockDB(rows)

    def save(self):
        self.db.save()


class TestIntegrityProofreading(unittest.TestCase):

    def setUp(self):
        self.raw_decks = [
            {"id": 1, "name": "Direito::Constitucional"},
            {"id": 2, "name": "Direito::Civil"},
            {"id": 3, "name": "Medicina::Anatomia"},
        ]
        self.explicit = {
            1: 1,  # Prio 1 (highest)
            2: 2,  # Prio 2
            3: 3,  # Prio 3
        }
        self.tree = build_deck_tree(self.raw_decks, self.explicit)

    def test_flawless_order(self):
        """A properly ordered collection passes all checks with 0 violations."""
        rows = [
            (101, 1, 1),
            (102, 1, 2),
            (201, 2, 3),
            (202, 2, 4),
            (301, 3, 5),
        ]
        col = MockCol(rows)
        report = verify_and_repair_card_order(col, self.tree, auto_repair=True)

        self.assertTrue(report.is_flawless)
        self.assertEqual(report.violations_detected, 0)
        self.assertTrue(report.block_contiguity_valid)
        self.assertTrue(report.monotonicity_valid)
        self.assertTrue(report.no_due_collisions)
        self.assertFalse(report.auto_repaired)
        self.assertEqual(report.repaired_count, 0)
        self.assertIn("100% Íntegro", report.status_badge)

    def test_interleaved_fragmentation_detected_and_repaired(self):
        """Fragmented cards (Deck 1 -> Deck 2 -> Deck 1) are detected and healed."""
        rows = [
            (101, 1, 1),
            (201, 2, 2),
            (102, 1, 3),  # Fragmentation! Deck 1 reappears
        ]
        col = MockCol(rows)

        # Audit only (no repair)
        report_audit = verify_and_repair_card_order(col, self.tree, auto_repair=False)
        self.assertFalse(report_audit.block_contiguity_valid)
        self.assertFalse(report_audit.is_flawless)
        self.assertGreater(report_audit.violations_detected, 0)

        # Audit with auto-repair
        col2 = MockCol(rows)
        report_repair = verify_and_repair_card_order(col2, self.tree, auto_repair=True)
        self.assertTrue(report_repair.auto_repaired)
        self.assertTrue(report_repair.is_flawless)
        self.assertTrue(report_repair.block_contiguity_valid)
        self.assertTrue(col2.db.save_called)
        self.assertIn("Corrigido via Autocura", report_repair.status_badge)

        # Verify new order in col2: Deck 1 cards come together before Deck 2
        updated_rows = col2.db.all("SELECT id, did, due FROM cards WHERE queue = 0")
        updated_dids = [r[1] for r in updated_rows]
        self.assertEqual(updated_dids, [1, 1, 2])

    def test_monotonicity_violation_detected_and_repaired(self):
        """Cards from a low priority deck appearing before a high priority deck are detected and fixed."""
        rows = [
            (301, 3, 1),
            (302, 3, 2),
            (101, 1, 3),
            (102, 1, 4),
        ]
        col = MockCol(rows)
        report = verify_and_repair_card_order(col, self.tree, auto_repair=True)

        self.assertTrue(report.auto_repaired)
        self.assertTrue(report.is_flawless)
        self.assertTrue(report.monotonicity_valid)

        updated_rows = col.db.all("SELECT id, did, due FROM cards WHERE queue = 0")
        updated_dids = [r[1] for r in updated_rows]
        self.assertEqual(updated_dids, [1, 1, 3, 3])

    def test_due_collision_detected_and_repaired(self):
        """Colliding due values (multiple cards with same due) are normalized to distinct ascending integers."""
        rows = [
            (101, 1, 1),
            (102, 1, 1),
            (201, 2, 1),
        ]
        col = MockCol(rows)
        report = verify_and_repair_card_order(col, self.tree, auto_repair=True)

        self.assertTrue(report.auto_repaired)
        self.assertTrue(report.is_flawless)
        self.assertTrue(report.no_due_collisions)

        updated_rows = col.db.all("SELECT id, did, due FROM cards WHERE queue = 0")
        due_values = [r[2] for r in updated_rows]
        self.assertEqual(due_values, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
