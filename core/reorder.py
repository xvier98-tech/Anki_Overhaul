# -*- coding: utf-8 -*-
"""
Core reordering logic for Anki new cards.
Assigns sequential 'due' positions ensuring closed block study and priority order.
"""

import time
import random
from typing import Dict, List, Tuple, Optional, Any
from .models import DeckNode, CardItem, ReorderResult, IntegrityReport
from .hierarchy import build_deck_tree

try:
    from PyQt6.QtCore import QTimer
except ImportError:
    try:
        from PyQt5.QtCore import QTimer
    except ImportError:
        QTimer = None

try:
    from ..ui.feedback_dialog import ReorderProgressDialog, ReorderSummaryDialog
except Exception:
    try:
        from ui.feedback_dialog import ReorderProgressDialog, ReorderSummaryDialog
    except Exception:
        try:
            from modules.priority_sequencer.ui.feedback_dialog import ReorderProgressDialog, ReorderSummaryDialog
        except Exception:
            ReorderProgressDialog = None
            ReorderSummaryDialog = None

try:
    from .integrity import verify_and_repair_card_order
except Exception:
    try:
        from integrity import verify_and_repair_card_order
    except Exception:
        try:
            from modules.priority_sequencer.integrity import verify_and_repair_card_order
        except Exception:
            verify_and_repair_card_order = None

try:
    from aqt import mw
    from aqt.operations import CollectionOp, QueryOp
    from aqt.utils import tooltip, askUserCustom, showWarning
except ImportError:
    mw = None
    CollectionOp = None
    QueryOp = None
    tooltip = None
    askUserCustom = None
    showWarning = None


def compute_new_card_order(
    deck_tree: Dict[int, DeckNode],
    cards: List[CardItem],
    randomize_same_priority_decks: bool = True,
    randomize_cards_within_deck: bool = False,
    random_seed: Optional[int] = None,
) -> List[Tuple[int, int]]:
    """
    Pure logic function that computes the new (card_id, new_due) pairs.
    
    :param deck_tree: Dict of deck_id -> DeckNode (with resolved effective_priority).
    :param cards: List of new CardItem objects.
    :param randomize_same_priority_decks: If True, decks with same priority are shuffled.
                                          Otherwise sorted alphabetically by deck name.
    :param randomize_cards_within_deck: If True, cards within a deck are shuffled.
                                        Otherwise sorted by original due/id.
    :param random_seed: Optional seed for deterministic testing.
    :return: List of tuples (card_id, new_due) starting from due = 1.
    """
    rng = random.Random(random_seed)

    # 1. Group cards by deck_id
    deck_cards: Dict[int, List[CardItem]] = {}
    for card in cards:
        if card.deck_id not in deck_cards:
            deck_cards[card.deck_id] = []
        deck_cards[card.deck_id].append(card)

    # Only consider decks that actually contain new cards
    active_deck_ids = list(deck_cards.keys())

    # 2. Group active decks by effective_priority
    prio_to_decks: Dict[int, List[int]] = {}
    for did in active_deck_ids:
        node = deck_tree.get(did)
        prio = node.effective_priority if node else 100
        if prio not in prio_to_decks:
            prio_to_decks[prio] = []
        prio_to_decks[prio].append(did)

    # 3. Sort priority levels ascending (lower number = higher priority)
    sorted_prios = sorted(prio_to_decks.keys())

    # 4. Build ordered list of decks
    final_deck_order: List[int] = []
    for prio in sorted_prios:
        decks_at_prio = prio_to_decks[prio]
        if randomize_same_priority_decks:
            rng.shuffle(decks_at_prio)
        else:
            # Deterministic sorting by deck name path
            decks_at_prio.sort(
                key=lambda did: (
                    deck_tree[did].name.lower() if did in deck_tree else "",
                    did,
                )
            )
        final_deck_order.extend(decks_at_prio)

    # 5. Order cards within each deck (closed block guarantees 100% contiguity)
    final_card_order: List[int] = []
    for did in final_deck_order:
        cards_in_deck = deck_cards[did]
        if randomize_cards_within_deck:
            rng.shuffle(cards_in_deck)
        else:
            # Keep relative order by current due, then card creation/id
            cards_in_deck.sort(key=lambda c: (c.current_due, c.created_time, c.id))

        for card in cards_in_deck:
            final_card_order.append(card.id)

    # 6. Generate sequential (card_id, new_due) starting from 1
    reordered_pairs = [(cid, idx + 1) for idx, cid in enumerate(final_card_order)]
    return reordered_pairs


def fetch_new_cards_from_col(col) -> List[CardItem]:
    """
    Fetch all new cards from the Anki collection database.
    In Anki SQLite:
    - queue = 0 indicates a new card.
    - due column is the position in new card queue.
    """
    # Query all new cards (queue = 0)
    # Return card id, did (deck id), due, id (for creation timestamp)
    rows = col.db.all("SELECT id, did, due FROM cards WHERE queue = 0")
    return [
        CardItem(id=row[0], deck_id=row[1], current_due=row[2], created_time=row[0])
        for row in rows
    ]


def count_new_cards_by_deck(col) -> Dict[int, int]:
    """
    Returns a dict mapping deck_id -> count of new cards in that deck.
    """
    rows = col.db.all("SELECT did, count() FROM cards WHERE queue = 0 GROUP BY did")
    return {row[0]: row[1] for row in rows}


def ensure_deck_gather_priority_ascending(col) -> None:
    """
    Ensures that Anki v3 scheduler gathers new cards across all subdecks
    in ascending position order (due) rather than alphabetical deck order.
    newGatherPriority: 1 = Lowest position (ascending due)
    """
    try:
        if hasattr(col, "decks"):
            if hasattr(col.decks, "all_config"):
                configs = col.decks.all_config()
                modified = False
                for conf in configs:
                    if conf.get("newGatherPriority") != 1:
                        conf["newGatherPriority"] = 1
                        if hasattr(col.decks, "update_config"):
                            col.decks.update_config(conf)
                        elif hasattr(col.decks, "save_config"):
                            col.decks.save_config(conf)
                        elif hasattr(col.decks, "save"):
                            col.decks.save(conf)
                        modified = True
                if modified and hasattr(col, "save"):
                    col.save()
    except Exception as e:
        print(f"[Priority Sequencer] Note on newGatherPriority: {e}")


def execute_reorder_in_col(
    col,
    explicit_priorities: Dict[int, int],
    default_priority: int = 100,
    randomize_same_priority_decks: bool = True,
    randomize_cards_within_deck: bool = False,
) -> ReorderResult:
    """
    Executes the full reorder procedure directly on an Anki collection.
    """
    start_time = time.time()
    try:
        ensure_deck_gather_priority_ascending(col)

        # 1. Fetch raw decks
        raw_decks = col.decks.all()

        # 2. Fetch new cards count
        new_counts = count_new_cards_by_deck(col)

        # 3. Build hierarchy tree
        deck_tree = build_deck_tree(
            raw_decks=raw_decks,
            explicit_priorities=explicit_priorities,
            default_priority=default_priority,
            new_card_counts=new_counts,
        )

        # 4. Fetch all new cards
        cards = fetch_new_cards_from_col(col)
        if not cards:
            return ReorderResult(
                cards_reordered=0,
                decks_affected=0,
                elapsed_seconds=time.time() - start_time,
            )

        # 5. Compute new sequential positions
        updates = compute_new_card_order(
            deck_tree=deck_tree,
            cards=cards,
            randomize_same_priority_decks=randomize_same_priority_decks,
            randomize_cards_within_deck=randomize_cards_within_deck,
        )

        # Performance optimization: only modify cards whose due value has actually changed!
        current_due_map = {c.id: c.current_due for c in cards}
        actual_updates = [
            (cid, new_due)
            for cid, new_due in updates
            if current_due_map.get(cid) != new_due
        ]

        if actual_updates:
            mod_time = int(time.time())
            db_params = [(new_due, mod_time, cid) for cid, new_due in actual_updates]
            chunk_size = 1000
            for i in range(0, len(db_params), chunk_size):
                col.db.executemany("UPDATE cards SET due = ?, mod = ? WHERE id = ?", db_params[i:i + chunk_size])
            col.save()

        # DNA Proofreading & Verification pass (exonuclease 3'->5' pattern)
        integrity_rep = None
        if verify_and_repair_card_order is not None:
            try:
                integrity_rep = verify_and_repair_card_order(col, deck_tree, auto_repair=True)
            except Exception as e:
                integrity_rep = IntegrityReport(violations_detected=1, details=[f"DNA Proofreading audit failed: {e}"])

        affected_decks = len({c.deck_id for c in cards})
        elapsed = time.time() - start_time

        total_reordered = len(actual_updates)
        if integrity_rep and integrity_rep.auto_repaired:
            total_reordered = max(total_reordered, integrity_rep.repaired_count)

        return ReorderResult(
            cards_reordered=total_reordered,
            decks_affected=affected_decks,
            elapsed_seconds=elapsed,
            integrity_report=integrity_rep,
        )
    except Exception as e:
        return ReorderResult(
            cards_reordered=0,
            decks_affected=0,
            elapsed_seconds=time.time() - start_time,
            error_message=str(e),
            integrity_report=IntegrityReport(violations_detected=1, details=[str(e)]),
        )


def count_total_new_cards(col) -> int:
    try:
        val = col.db.scalar("SELECT count() FROM cards WHERE queue = 0")
        return int(val or 0)
    except Exception:
        return 0


def run_reorder_with_ui(
    parent_widget=None,
    on_complete=None,
    ask_confirmation: bool = False,
    interactive: bool = True,
) -> None:
    """
    Runs the reorder routine with Anki UI integration, Undo checkpoint,
    DNA Proofreading validation, and rich visual feedback.
    """
    from ..utils.config_manager import get_config, get_deck_priorities

    if not mw or not mw.col:
        return

    total_new = count_total_new_cards(mw.col)
    if total_new == 0:
        if interactive and ReorderSummaryDialog is not None and (parent_widget or mw):
            try:
                empty_res = ReorderResult(0, 0, 0.0, integrity_report=IntegrityReport())
                dlg = ReorderSummaryDialog(parent=parent_widget or mw, result=empty_res, total_new=0)
                dlg.exec()
            except Exception:
                if tooltip:
                    tooltip("ℹ️ Nenhum cartão novo encontrado para reordenar.", parent=parent_widget)
        else:
            if tooltip:
                tooltip("ℹ️ Nenhum cartão novo encontrado para reordenar.", parent=parent_widget)
        if on_complete:
            on_complete(ReorderResult(0, 0, 0.0, integrity_report=IntegrityReport()))
        return

    if ask_confirmation:
        try:
            from aqt.utils import askUserCustom
            new_counts = count_new_cards_by_deck(mw.col)
            choice = askUserCustom(
                f"<b>⚡ Reordenar Novos Cartões por Prioridade</b><br><br>"
                f"Foram identificados <b>{total_new}</b> cartões novos em <b>{len(new_counts)}</b> baralhos.<br><br>"
                f"Deseja reordenar agora em segundo plano?<br>",
                default=0,
                parent=parent_widget or mw,
                btn0="⚡ Reordenar Agora",
                btn1="Cancelar",
            )
            if choice != 0:
                return
        except Exception:
            pass

    config = get_config()
    explicit_priorities = get_deck_priorities()
    default_priority = int(config.get("default_priority", 100))
    randomize_same = bool(config.get("randomize_same_priority_decks", True))
    randomize_cards = bool(config.get("randomize_cards_within_deck", False))

    progress_dlg = None
    if interactive and ReorderProgressDialog is not None and (parent_widget or mw):
        try:
            progress_dlg = ReorderProgressDialog(parent=parent_widget or mw, total_cards=total_new)
            progress_dlg.show()
            progress_dlg.set_stage(0, "Mapeando baralhos e hierarquia de herança...")
            if QTimer is not None:
                timer = QTimer(progress_dlg)
                def _advance():
                    if not progress_dlg or not progress_dlg.isVisible():
                        return
                    curr = progress_dlg.current_stage
                    if curr < 3:
                        progress_dlg.set_stage(curr + 1)
                timer.timeout.connect(_advance)
                timer.start(250)
                progress_dlg._timer = timer
        except Exception as e:
            print(f"[Priority Sequencer] Progress dialog init error: {e}")
            progress_dlg = None

    def _close_progress():
        nonlocal progress_dlg
        if progress_dlg:
            try:
                if hasattr(progress_dlg, "_timer") and progress_dlg._timer:
                    progress_dlg._timer.stop()
                progress_dlg.close()
            except Exception:
                pass
            progress_dlg = None

    def _show_fallback_feedback(res: ReorderResult):
        if res.success:
            badge = f" [{res.integrity_report.status_badge}]" if res.integrity_report else ""
            if res.cards_reordered == 0:
                msg = f"⚡ Todos os {total_new} cartões novos já estão na ordem correta de prioridade!{badge}"
            else:
                msg = f"⚡ Prioridade aplicada! {res.cards_reordered} cartões novos em {res.decks_affected} baralhos reordenados ({res.elapsed_seconds:.2f}s).{badge}"
            if tooltip:
                tooltip(msg, parent=parent_widget)
        else:
            if showWarning:
                showWarning(f"Erro ao reordenar cartões: {res.error_message}", parent=parent_widget)

    def _do_reorder(col):
        return execute_reorder_in_col(
            col=col,
            explicit_priorities=explicit_priorities,
            default_priority=default_priority,
            randomize_same_priority_decks=randomize_same,
            randomize_cards_within_deck=randomize_cards,
        )

    def _on_success(result: ReorderResult):
        _close_progress()

        if mw:
            mw.reset()

        if interactive and ReorderSummaryDialog is not None and (parent_widget or mw):
            try:
                dlg = ReorderSummaryDialog(parent=parent_widget or mw, result=result, total_new=total_new)
                dlg.exec()
            except Exception as ex:
                print(f"[Priority Sequencer] Summary dialog display error: {ex}")
                _show_fallback_feedback(result)
        else:
            _show_fallback_feedback(result)

        if on_complete:
            on_complete(result)

    if QueryOp is not None:
        try:
            mw.checkpoint("Reordenar Cartões por Prioridade")
            op = QueryOp(
                parent=parent_widget or mw,
                op=_do_reorder,
                success=_on_success,
            )
            if not progress_dlg:
                op = op.with_progress("⚡ Reordenando novos cartões por prioridade...")
            op.run_in_background()
            return
        except Exception:
            pass

    if mw:
        mw.checkpoint("Reordenar Cartões por Prioridade")
        if not progress_dlg and mw.progress:
            mw.progress.start(label="Reordenando cartões novos...", parent=parent_widget)

    try:
        res = _do_reorder(mw.col)
    finally:
        _close_progress()
        if mw and mw.progress and not progress_dlg:
            mw.progress.finish()

    _on_success(res)
