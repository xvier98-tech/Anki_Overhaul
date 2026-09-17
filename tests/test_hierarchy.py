# -*- coding: utf-8 -*-
"""
Unit tests for hierarchy and bottom-up inheritance resolution.
"""

import unittest
from core.hierarchy import build_deck_tree, get_root_deck_ids, get_deck_subtree_ids


class TestHierarchy(unittest.TestCase):

    def setUp(self):
        # Sample deck list representing a realistic collection hierarchy
        self.raw_decks = [
            {"id": 1, "name": "Default"},
            {"id": 10, "name": "Medicina"},
            {"id": 11, "name": "Medicina::Farmacologia"},
            {"id": 12, "name": "Medicina::Farmacologia::Antibióticos"},
            {"id": 13, "name": "Medicina::Farmacologia::Anti-inflamatórios"},
            {"id": 14, "name": "Medicina::Anatomia"},
            {"id": 20, "name": "Idiomas"},
            {"id": 21, "name": "Idiomas::Inglês"},
            {"id": 22, "name": "Idiomas::Espanhol"},
        ]

    def test_default_inheritance(self):
        """When no explicit priorities are set, all decks should have default_priority."""
        tree = build_deck_tree(self.raw_decks, explicit_priorities={}, default_priority=100)
        for did, node in tree.items():
            self.assertEqual(node.effective_priority, 100)

    def test_parent_priority_propagation(self):
        """Subdecks should inherit priority from parent if they don't have explicit one."""
        explicit = {
            10: 5,  # Medicina = 5
        }
        tree = build_deck_tree(self.raw_decks, explicit_priorities=explicit, default_priority=100)

        # Medicina and all its children should inherit priority 5
        self.assertEqual(tree[10].effective_priority, 5)
        self.assertEqual(tree[11].effective_priority, 5)
        self.assertEqual(tree[12].effective_priority, 5)
        self.assertEqual(tree[13].effective_priority, 5)
        self.assertEqual(tree[14].effective_priority, 5)

        # Idiomas should have default 100
        self.assertEqual(tree[20].effective_priority, 100)
        self.assertEqual(tree[21].effective_priority, 100)

    def test_child_override_specific_prevalence(self):
        """A subdeck or sub-subdeck with manual priority overrides parent for itself and children."""
        explicit = {
            10: 10,  # Medicina = 10
            11: 3,   # Medicina::Farmacologia = 3 (overrides parent 10)
            13: 1,   # Medicina::Farmacologia::Anti-inflamatórios = 1 (overrides 3)
        }
        tree = build_deck_tree(self.raw_decks, explicit_priorities=explicit, default_priority=100)

        self.assertEqual(tree[10].effective_priority, 10)  # Medicina (explicit)
        self.assertEqual(tree[14].effective_priority, 10)  # Medicina::Anatomia (inherited from Medicina)
        self.assertEqual(tree[11].effective_priority, 3)   # Medicina::Farmacologia (explicit)
        self.assertEqual(tree[12].effective_priority, 3)   # Antibióticos (inherited from Farmacologia)
        self.assertEqual(tree[13].effective_priority, 1)   # Anti-inflamatórios (explicit override)

    def test_get_root_and_subtrees(self):
        tree = build_deck_tree(self.raw_decks, explicit_priorities={}, default_priority=100)
        roots = get_root_deck_ids(tree)
        # Roots should be Default (1), Idiomas (20), Medicina (10)
        self.assertIn(1, roots)
        self.assertIn(10, roots)
        self.assertIn(20, roots)
        self.assertEqual(len(roots), 3)

        # Subtree of Medicina (10) should contain 10, 11, 12, 13, 14
        subtree_med = get_deck_subtree_ids(tree, 10)
        self.assertEqual(set(subtree_med), {10, 11, 12, 13, 14})

    def test_string_and_dual_key_priorities(self):
        """String keys from JSON config must be normalized and correctly resolve effective priorities."""
        from utils.config_manager import _DualKeyPriorityDict
        string_explicit = {"10": 15, "11": 5}
        tree = build_deck_tree(self.raw_decks, explicit_priorities=string_explicit, default_priority=100)
        self.assertEqual(tree[10].explicit_priority, 15)
        self.assertEqual(tree[10].effective_priority, 15)
        self.assertEqual(tree[11].explicit_priority, 5)
        self.assertEqual(tree[11].effective_priority, 5)
        self.assertEqual(tree[12].effective_priority, 5)  # Inherited from 11
        self.assertEqual(tree[14].effective_priority, 15)  # Inherited from 10

        # DualKey dict test
        dual = _DualKeyPriorityDict({"10": 20})
        self.assertEqual(dual[10], 20)
        self.assertEqual(dual["10"], 20)
        self.assertEqual(dual.get(10), 20)
        self.assertEqual(dual.get("10"), 20)
        self.assertIn(10, dual)
        self.assertIn("10", dual)

        dual_tree = build_deck_tree(self.raw_decks, explicit_priorities=dual, default_priority=100)
        self.assertEqual(dual_tree[10].effective_priority, 20)
        self.assertEqual(dual_tree[11].effective_priority, 20)


if __name__ == "__main__":
    unittest.main()
