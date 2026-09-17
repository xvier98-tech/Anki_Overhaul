# -*- coding: utf-8 -*-
"""
Hierarchy resolver for Anki decks.
Calculates bottom-up effective priorities across the deck tree.
"""

from typing import Dict, List, Optional, Any
from .models import DeckNode


def build_deck_tree(
    raw_decks: List[Dict[str, Any]],
    explicit_priorities: Optional[Dict[int, int]] = None,
    default_priority: int = 100,
    new_card_counts: Optional[Dict[int, int]] = None,
) -> Dict[int, DeckNode]:
    """
    Builds a tree of DeckNodes and resolves effective priorities bottom-up.
    """
    if explicit_priorities is None:
        explicit_priorities = {}
    if new_card_counts is None:
        new_card_counts = {}

    # Normalizar explicit_priorities para lookup consistente com did (int)
    normalized_priorities: Dict[int, int] = {}
    for k, v in explicit_priorities.items():
        try:
            normalized_priorities[int(k)] = int(v)
        except (ValueError, TypeError):
            continue

    nodes: Dict[int, DeckNode] = {}
    name_to_id: Dict[str, int] = {}

    # 1. Create nodes
    for d in raw_decks:
        did = int(d["id"])
        name = str(d["name"]).replace("\x1f", "::")
        name_to_id[name] = did
        exp_prio = normalized_priorities.get(did)
        
        nodes[did] = DeckNode(
            id=did,
            name=name,
            explicit_priority=exp_prio,
            effective_priority=default_priority,
            new_card_count=new_card_counts.get(did, 0),
        )

    # 2. Establish parent-child relationships via deck name '::' path
    for did, node in nodes.items():
        parts = node.name.split("::")
        if len(parts) > 1:
            parent_name = "::".join(parts[:-1])
            if parent_name in name_to_id:
                parent_id = name_to_id[parent_name]
                node.parent_id = parent_id
                nodes[parent_id].children_ids.append(did)

    # Sort children deterministically by name
    for node in nodes.values():
        node.children_ids.sort(key=lambda cid: nodes[cid].name.lower())

    # 3. Propagate effective priorities bottom-up
    def resolve_effective(did: int, inherited_priority: int) -> None:
        node = nodes[did]
        if node.explicit_priority is not None:
            current_priority = node.explicit_priority
        else:
            current_priority = inherited_priority
        
        node.effective_priority = current_priority

        for child_id in node.children_ids:
            resolve_effective(child_id, current_priority)

    # Resolve from root decks
    roots = [did for did, node in nodes.items() if node.parent_id is None]
    roots.sort(key=lambda did: nodes[did].name.lower())
    for root_id in roots:
        resolve_effective(root_id, default_priority)

    return nodes


def get_root_deck_ids(deck_tree: Dict[int, DeckNode]) -> List[int]:
    """Returns sorted list of root deck IDs."""
    roots = [did for did, node in deck_tree.items() if node.parent_id is None]
    roots.sort(key=lambda did: deck_tree[did].name.lower())
    return roots


def get_deck_subtree_ids(deck_tree: Dict[int, DeckNode], root_id: int) -> List[int]:
    """Returns all deck IDs in the subtree of root_id (including root_id)."""
    result: List[int] = []
    
    def collect(did: int):
        result.append(did)
        if did in deck_tree:
            for cid in deck_tree[did].children_ids:
                collect(cid)
                
    collect(root_id)
    return result
