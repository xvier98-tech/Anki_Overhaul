# -*- coding: utf-8 -*-
"""
Core reordering logic for Anki new cards.
Assigns sequential 'due' positions ensuring closed block study and priority order.
"""

import time
import random
from typing import Dict, List, Tuple, Optional
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
    from .ui.feedback_dialog import ReorderProgressDialog, ReorderSummaryDialog
except Exception:
    try:
        from ui.feedback_dialog import ReorderProgressDialog, ReorderSummaryDialog
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
            from core.integrity import verify_and_repair_card_order
        except Exception:
            verify_and_repair_card_order = None

try:
    from aqt import mw
    from aqt.utils import tooltip, askUserCustom, showWarning, showInfo
    from aqt.operations import QueryOp
except ImportError:
    mw = None
    tooltip = None
    askUserCustom = None
    showWarning = None
    showInfo = None
    QueryOp = None


def count_total_new_cards(col) -> int:
    """Returns total count of new cards in queue 0 across the entire collection."""
    try:
        val = col.db.scalar("SELECT count() FROM cards WHERE queue = 0")
        return int(val or 0)
    except Exception:
        return 0


def confirm_reorder_prompt(parent, total_new: int, deck_count: int) -> bool:
    """
    Shows a clean confirmation dialog to prevent accidental triggers from the Tools menu.
    Returns True only if the user explicitly confirms.
    """
    try:
        from aqt.utils import askUserCustom
        msg = (
            f"<h3 style='color: #38bdf8; margin-top: 0;'>⚡ Reordenar Novos Cartões por Prioridade</h3>"
            f"Foram identificados <b>{total_new}</b> cartões novos em <b>{deck_count}</b> baralhos.<br><br>"
            f"Deseja reordenar a sequência de apresentação agora conforme a hierarquia de prioridades configurada (estudo em blocos fechados contíguos)?<br><br>"
            f"<small style='color: #94a3b8;'><i>A operação é otimizada e executa em segundo plano sem congelar o Anki.</i></small>"
        )
        choice = askUserCustom(
            msg,
            default=0,
            parent=parent,
            btn0="⚡ Reordenar Agora",
            btn1="Cancelar",
        )
        return choice == 0
    except Exception:
        try:
            from aqt.utils import askUser
            return bool(askUser(
                f"Reordenar {total_new} cartões novos por prioridade?\n\n(Se clicou por engano na lista de ferramentas, clique em Cancelar)",
                parent=parent,
                defaultno=True,
            ))
        except Exception:
            return True


def compute_new_card_order(
    deck_tree: Dict[int, DeckNode],
    cards: List[CardItem],
    randomize_same_priority_decks: bool = True,
    randomize_cards_within_deck: bool = False,
    random_seed: Optional[int] = None,
) -> List[Tuple[int, int]]:
    """
    Pure logic function that computes the new (card_id, new_due) pairs.
    """
    rng = random.Random(random_seed)

    # 1. Group cards by deck_id
    deck_cards: Dict[int, List[CardItem]] = {}
    for card in cards:
        if card.deck_id not in deck_cards:
            deck_cards[card.deck_id] = []
        deck_cards[card.deck_id].append(card)

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
            cards_in_deck.sort(key=lambda c: (c.current_due, c.created_time, c.id))

        for card in cards_in_deck:
            final_card_order.append(card.id)

    # 6. Generate sequential (card_id, new_due) starting from 1
    reordered_pairs = [(cid, idx + 1) for idx, cid in enumerate(final_card_order)]
    return reordered_pairs


def fetch_new_cards_from_col(col) -> List[CardItem]:
    rows = col.db.all("SELECT id, did, due FROM cards WHERE queue = 0")
    return [
        CardItem(id=row[0], deck_id=row[1], current_due=row[2], created_time=row[0])
        for row in rows
    ]


def count_new_cards_by_deck(col) -> Dict[int, int]:
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
    Executes the reordering in collection with diff-checking and chunked SQLite updates
    to maximize performance on low-end hardware and prevent system lockups.
    """
    start_time = time.time()
    try:
        ensure_deck_gather_priority_ascending(col)

        raw_decks = col.decks.all()
        new_counts = count_new_cards_by_deck(col)

        deck_tree = build_deck_tree(
            raw_decks=raw_decks,
            explicit_priorities=explicit_priorities,
            default_priority=default_priority,
            new_card_counts=new_counts,
        )

        cards = fetch_new_cards_from_col(col)
        if not cards:
            return ReorderResult(
                cards_reordered=0,
                decks_affected=0,
                elapsed_seconds=time.time() - start_time,
            )

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

        # Apply batch updates in lightweight chunks of 1000 to prevent database lockups
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


def run_reorder_with_ui(
    parent_widget=None,
    on_complete=None,
    ask_confirmation: bool = False,
    interactive: bool = True,
) -> None:
    """
    Runs the reorder routine with non-blocking background execution (QueryOp),
    accidental trigger protection, Undo checkpoint, DNA Proofreading validation,
    and rich visual feedback (ReorderProgressDialog / ReorderSummaryDialog).
    """
    try:
        from ...utils.config_manager import get_module_config, get_deck_priorities
    except (ImportError, ValueError):
        from utils.config_manager import get_module_config, get_deck_priorities

    if not mw or not mw.col:
        return

    # 1. Quick pre-check: are there any new cards at all?
    total_new = count_total_new_cards(mw.col)
    if total_new == 0:
        if interactive and ReorderSummaryDialog is not None and (parent_widget or mw):
            try:
                empty_res = ReorderResult(0, 0, 0.0, integrity_report=IntegrityReport())
                dlg = ReorderSummaryDialog(parent=parent_widget or mw, result=empty_res, total_new=0)
                dlg.exec()
            except Exception:
                if tooltip:
                    tooltip("ℹ️ Nenhum cartão novo encontrado na coleção para reordenar.", parent=parent_widget)
        else:
            if tooltip:
                tooltip("ℹ️ Nenhum cartão novo encontrado na coleção para reordenar.", parent=parent_widget)
        if on_complete:
            on_complete(ReorderResult(0, 0, 0.0, integrity_report=IntegrityReport()))
        return

    # 2. Accidental trigger confirmation
    if ask_confirmation:
        new_counts = count_new_cards_by_deck(mw.col)
        deck_count = len(new_counts)
        if not confirm_reorder_prompt(parent=parent_widget or mw, total_new=total_new, deck_count=deck_count):
            return  # Cancelled by user

    config = get_module_config("priority_sequencer")
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

    # 3. Modern Anki Background Execution via QueryOp (Non-blocking UI)
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
        except Exception as e:
            print(f"[Priority Sequencer] QueryOp background launch error: {e}")

    # 4. Fallback execution
    if mw:
        mw.checkpoint("Reordenar Cartões por Prioridade")
        if not progress_dlg and mw.progress:
            mw.progress.start(label="Reordenando cartões novos...", parent=parent_widget)

    try:
        result = _do_reorder(mw.col)
    finally:
        _close_progress()
        if mw and mw.progress and not progress_dlg:
            mw.progress.finish()

    _on_success(result)
