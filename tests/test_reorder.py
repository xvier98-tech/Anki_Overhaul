# -*- coding: utf-8 -*-
"""
Unit tests for the closed-block card reordering algorithm.
"""

import unittest
from core.models import CardItem, DeckNode
from core.hierarchy import build_deck_tree
from core.reorder import compute_new_card_order


class TestReorder(unittest.TestCase):

    def setUp(self):
        self.raw_decks = [
            {"id": 1, "name": "Direito::Constitucional"},
            {"id": 2, "name": "Direito::Civil"},
            {"id": 3, "name": "Medicina::Anatomia"},
            {"id": 4, "name": "Medicina::Fisiologia"},
        ]

    def test_priority_ordering(self):
        """Cards from higher priority decks (lower numeric value) must come before lower priority."""
        explicit = {
            1: 1,  # Direito::Constitucional = 1 (highest)
            2: 2,  # Direito::Civil = 2
            3: 3,  # Medicina::Anatomia = 3
            4: 4,  # Medicina::Fisiologia = 4
        }
        tree = build_deck_tree(self.raw_decks, explicit)

        cards = [
            CardItem(id=101, deck_id=3, current_due=1),
            CardItem(id=102, deck_id=1, current_due=2),
            CardItem(id=103, deck_id=4, current_due=3),
            CardItem(id=104, deck_id=2, current_due=4),
            CardItem(id=105, deck_id=1, current_due=5),
        ]

        ordered_pairs = compute_new_card_order(
            deck_tree=tree,
            cards=cards,
            randomize_same_priority_decks=False,
            randomize_cards_within_deck=False,
        )

        # Expected card IDs order:
        # Deck 1 (prio 1): cards 102, 105
        # Deck 2 (prio 2): card 104
        # Deck 3 (prio 3): card 101
        # Deck 4 (prio 4): card 103
        card_ids_in_order = [cid for cid, _ in ordered_pairs]
        self.assertEqual(card_ids_in_order, [102, 105, 104, 101, 103])

        # Verify due values are strictly 1, 2, 3, 4, 5
        due_values = [due for _, due in ordered_pairs]
        self.assertEqual(due_values, [1, 2, 3, 4, 5])

    def test_closed_block_no_interleaving(self):
        """Cards belonging to the same deck must be 100% contiguous (closed block)."""
        # All decks have same priority 10
        explicit = {1: 10, 2: 10, 3: 10}
        tree = build_deck_tree(self.raw_decks, explicit)

        cards = [
            CardItem(id=1, deck_id=1, current_due=10),
            CardItem(id=2, deck_id=2, current_due=20),
            CardItem(id=3, deck_id=1, current_due=30),
            CardItem(id=4, deck_id=3, current_due=40),
            CardItem(id=5, deck_id=2, current_due=50),
            CardItem(id=6, deck_id=1, current_due=60),
            CardItem(id=7, deck_id=3, current_due=70),
        ]

        ordered_pairs = compute_new_card_order(
            deck_tree=tree,
            cards=cards,
            randomize_same_priority_decks=True,
            randomize_cards_within_deck=False,
            random_seed=42,
        )

        card_id_to_deck = {c.id: c.deck_id for c in cards}
        deck_sequence = [card_id_to_deck[cid] for cid, _ in ordered_pairs]

        # Verify each deck appears in a single contiguous segment
        seen_decks = set()
        current_deck = None
        for did in deck_sequence:
            if did != current_deck:
                self.assertNotIn(did, seen_decks, f"Deck {did} was interleaved!")
                seen_decks.add(did)
                current_deck = did

    def test_same_priority_deterministic_alphabetical(self):
        """When randomize_same_priority_decks is False, decks of same prio sort alphabetically."""
        tree = build_deck_tree(self.raw_decks, explicit_priorities={1: 5, 2: 5, 3: 5, 4: 5})

        cards = [
            CardItem(id=1, deck_id=4, current_due=1),  # Medicina::Fisiologia
            CardItem(id=2, deck_id=3, current_due=2),  # Medicina::Anatomia
            CardItem(id=3, deck_id=2, current_due=3),  # Direito::Civil
            CardItem(id=4, deck_id=1, current_due=4),  # Direito::Constitucional
        ]

        ordered_pairs = compute_new_card_order(
            deck_tree=tree,
            cards=cards,
            randomize_same_priority_decks=False,
            randomize_cards_within_deck=False,
        )

        # Alphabetical by deck name:
        # 1. Direito::Civil (deck 2, card 3)
        # 2. Direito::Constitucional (deck 1, card 4)
        # 3. Medicina::Anatomia (deck 3, card 2)
        # 4. Medicina::Fisiologia (deck 4, card 1)
        card_ids_in_order = [cid for cid, _ in ordered_pairs]
        self.assertEqual(card_ids_in_order, [3, 4, 2, 1])

    def test_same_priority_randomization_with_seed(self):
        """When randomize_same_priority_decks is True, random tie-breaker shuffles decks in closed blocks."""
        tree = build_deck_tree(self.raw_decks, explicit_priorities={1: 5, 2: 5, 3: 5, 4: 5})

        cards = [
            CardItem(id=1, deck_id=1, current_due=1),
            CardItem(id=2, deck_id=2, current_due=2),
            CardItem(id=3, deck_id=3, current_due=3),
            CardItem(id=4, deck_id=4, current_due=4),
        ]

        # Seed 1
        order1 = compute_new_card_order(
            deck_tree=tree,
            cards=cards,
            randomize_same_priority_decks=True,
            random_seed=123,
        )
        # Seed 2
        order2 = compute_new_card_order(
            deck_tree=tree,
            cards=cards,
            randomize_same_priority_decks=True,
            random_seed=999,
        )

        self.assertEqual(len(order1), 4)
        self.assertEqual(len(order2), 4)
        # Verify valid permutation of all 4 cards
        self.assertEqual(set([c for c, _ in order1]), {1, 2, 3, 4})
        self.assertEqual(set([c for c, _ in order2]), {1, 2, 3, 4})

    def test_execute_reorder_diff_optimization_and_chunking(self):
        """Verify execute_reorder_in_col only writes changed cards and batches updates."""
        from modules.priority_sequencer.reorder import execute_reorder_in_col, count_total_new_cards

        class MockDecks:
            def all(self):
                return [
                    {"id": 1, "name": "DeckA"},
                    {"id": 2, "name": "DeckB"},
                ]

        class MockDB:
            def __init__(self, cards_data):
                self.cards_data = cards_data
                self.executemany_calls = []

            def all(self, query):
                if "queue = 0 GROUP BY did" in query:
                    # Return did, count()
                    return [(1, 2), (2, 2)]
                elif "SELECT id, did, due FROM cards WHERE queue = 0" in query:
                    return self.cards_data
                return []

            def scalar(self, query):
                return len(self.cards_data)

            def executemany(self, sql, params):
                self.executemany_calls.append((sql, list(params)))

        class MockCol:
            def __init__(self, cards_data):
                self.decks = MockDecks()
                self.db = MockDB(cards_data)
                self.saved = False

            def save(self):
                self.saved = True

        # Case 1: Cards are already in perfect order (due = 1, 2, 3, 4)
        # Deck 1 (prio 1), Deck 2 (prio 2)
        already_ordered = [
            (10, 1, 1),
            (11, 1, 2),
            (20, 2, 3),
            (21, 2, 4),
        ]
        col1 = MockCol(already_ordered)
        res1 = execute_reorder_in_col(
            col=col1,
            explicit_priorities={1: 1, 2: 2},
            randomize_same_priority_decks=False,
            randomize_cards_within_deck=False,
        )
        self.assertTrue(res1.success)
        self.assertEqual(res1.cards_reordered, 0)
        # ZERO executemany calls and no disk save needed!
        self.assertEqual(len(col1.db.executemany_calls), 0)
        self.assertFalse(col1.saved)

        # Case 2: Cards are reversed and need updates
        inverted = [
            (20, 2, 1),
            (21, 2, 2),
            (10, 1, 3),
            (11, 1, 4),
        ]
        col2 = MockCol(inverted)
        res2 = execute_reorder_in_col(
            col=col2,
            explicit_priorities={1: 1, 2: 2},
            randomize_same_priority_decks=False,
            randomize_cards_within_deck=False,
        )
        self.assertTrue(res2.success)
        self.assertEqual(res2.cards_reordered, 4)
        self.assertTrue(col2.saved)
        self.assertGreater(len(col2.db.executemany_calls), 0)

        # Verify count_total_new_cards
        self.assertEqual(count_total_new_cards(col2), 4)


if __name__ == "__main__":
    unittest.main()
