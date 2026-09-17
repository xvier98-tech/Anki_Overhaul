# -*- coding: utf-8 -*-
"""
DNA-style Proofreading and Verification Engine for Deck Priorities.
Performs post-reorder validation and atomic self-repair (exonuclease 3'->5' pattern):
1. Verifies Closed Block Invariance (contiguity of decks).
2. Verifies Priority Monotonicity (P_A <= P_B along due sequence).
3. Verifies Unique Due Sequence (no collisions).
4. Auto-repairs any discrepancy in-flight before returning.
"""

import time
from typing import Dict, List, Tuple, Optional
from .models import DeckNode, IntegrityReport, CardItem


def verify_and_repair_card_order(
    col,
    deck_tree: Dict[int, DeckNode],
    auto_repair: bool = True,
) -> IntegrityReport:
    """
    DNA Proofreading algorithm:
    1. Reads actual ordered new cards from SQLite.
    2. Audits contiguity, monotonicity, and due collisions.
    3. If anomalies are found and auto_repair is True, corrects the database immediately.
    4. Re-validates to guarantee 100% integrity.
    """
    report = IntegrityReport()
    
    if not col or not hasattr(col, "db"):
        return report

    def _fetch_rows():
        return col.db.all("SELECT id, did, due FROM cards WHERE queue = 0 ORDER BY due ASC, id ASC")

    rows = _fetch_rows()
    report.total_cards_checked = len(rows)
    if not rows:
        return report

    # --- Phase 1: Audit Current State ---
    violations = []
    seen_decks = set()
    deck_blocks: List[Tuple[int, int]] = []  # list of (did, priority) in order of appearance
    last_did = None
    due_set = set()
    has_collisions = False

    for idx, (cid, did, due) in enumerate(rows):
        # Check due collisions
        if due in due_set:
            has_collisions = True
        due_set.add(due)

        # Check block transitions
        if did != last_did:
            if did in seen_decks:
                violations.append(f"Fragmentação: baralho {did} reapareceu dividido na posição {idx + 1}")
            seen_decks.add(did)
            prio = deck_tree[did].effective_priority if did in deck_tree else 100
            deck_blocks.append((did, prio))
            last_did = did

    # Check monotonicity across deck blocks (smaller number = higher priority)
    for i in range(len(deck_blocks) - 1):
        did1, p1 = deck_blocks[i]
        did2, p2 = deck_blocks[i + 1]
        if p1 > p2:
            violations.append(f"Monotonicidade: baralho {did1} (prio {p1}) precede baralho {did2} (prio {p2})")

    report.no_due_collisions = not has_collisions
    report.block_contiguity_valid = len(seen_decks) == len(deck_blocks)
    report.monotonicity_valid = not any("Monotonicidade" in v for v in violations)
    report.violations_detected = len(violations) + (1 if has_collisions else 0)
    report.details = violations

    # --- Phase 2: DNA Self-Repair Pass (if anomalies found) ---
    if (not report.is_flawless or has_collisions) and auto_repair:
        try:
            cards = [CardItem(id=r[0], deck_id=r[1], current_due=r[2]) for r in rows]
            try:
                from .reorder import compute_new_card_order
            except (ImportError, ValueError):
                from reorder import compute_new_card_order

            corrected_pairs = compute_new_card_order(
                deck_tree=deck_tree,
                cards=cards,
                randomize_same_priority_decks=False,
                randomize_cards_within_deck=False,
            )
            
            repair_params = [(new_due, int(time.time()), cid) for cid, new_due in corrected_pairs]
            chunk_size = 1000
            for i in range(0, len(repair_params), chunk_size):
                col.db.executemany("UPDATE cards SET due = ?, mod = ? WHERE id = ?", repair_params[i:i + chunk_size])
            col.save()

            report.auto_repaired = True
            report.repaired_count = len(repair_params)

            # Re-check Phase
            second_rows = _fetch_rows()
            second_seen = set()
            second_blocks = []
            second_last = None
            second_collisions = False
            second_due_set = set()

            for idx, (cid, did, due) in enumerate(second_rows):
                if due in second_due_set:
                    second_collisions = True
                second_due_set.add(due)
                if did != second_last:
                    second_seen.add(did)
                    prio = deck_tree[did].effective_priority if did in deck_tree else 100
                    second_blocks.append((did, prio))
                    second_last = did

            monotonicity_ok = True
            for i in range(len(second_blocks) - 1):
                if second_blocks[i][1] > second_blocks[i + 1][1]:
                    monotonicity_ok = False
                    break

            report.no_due_collisions = not second_collisions
            report.block_contiguity_valid = len(second_seen) == len(second_blocks)
            report.monotonicity_valid = monotonicity_ok
            if report.no_due_collisions and report.block_contiguity_valid and report.monotonicity_valid:
                report.details.append("🧬 Autocura realizada com sucesso: sequência restabelecida com 100% de conformidade.")
        except Exception as e:
            report.details.append(f"Erro durante autocura: {e}")

    return report
