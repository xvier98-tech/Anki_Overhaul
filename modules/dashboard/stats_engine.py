# -*- coding: utf-8 -*-
"""
High-Performance Statistics Engine for Modern Dashboard.
Accurately calculates today's completed cards, daily limits/goals, and collection inventory
using Anki's native revlog column names (lastIvl, ivl) and event types.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time

try:
    from aqt import mw
except ImportError:
    mw = None

from ..priority_sequencer.hierarchy import build_deck_tree, get_deck_subtree_ids

# Anki Revlog Types
REVLOG_LRN = 0
REVLOG_REV = 1
REVLOG_RELRN = 2
REVLOG_CRAM = 3
REVLOG_RESCHED = 4


def format_duration(seconds: float) -> str:
    """Formats seconds into human-readable duration (e.g. 45s, 12m 30s, 1h 15m)."""
    sec = int(seconds)
    if sec < 60:
        return f"{sec}s"
    minutes = sec // 60
    rem_sec = sec % 60
    if minutes < 60:
        if rem_sec > 0:
            return f"{minutes}m {rem_sec:02d}s"
        return f"{minutes}m"
    hours = minutes // 60
    rem_min = minutes % 60
    return f"{hours}h {rem_min:02d}m"


@dataclass
class TodayProgressStats:
    studied_count: int = 0
    time_spent_seconds: float = 0.0
    formatted_time: str = "0s"
    seconds_per_card: float = 0.0
    cards_per_minute: float = 0.0
    retention_rate_pct: float = 0.0
    streak_days: int = 0


@dataclass
class RemainingStats:
    new_cards: int = 0
    learn_cards: int = 0
    review_cards: int = 0
    total_remaining: int = 0
    tomorrow_forecast: int = 0


@dataclass
class DoneTodayBreakdown:
    new_learned: int = 0
    learn_reps: int = 0
    review_reps: int = 0
    mature_reviewed: int = 0
    again_count: int = 0
    fail_rate_pct: float = 0.0


@dataclass
class DailyGoalsStats:
    new_limit: int = 20
    new_done: int = 0
    new_pct: float = 0.0
    rev_limit: int = 200
    rev_done: int = 0
    rev_pct: float = 0.0


@dataclass
class DeckCompositionStats:
    total_cards: int = 0
    mature: int = 0
    young: int = 0
    unseen: int = 0
    suspended: int = 0
    buried: int = 0
    mature_pct: float = 0.0
    due_reviews_total: int = 0


@dataclass
class DeckDashboardStats:
    deck_id: Optional[int]
    deck_name: str
    is_per_deck: bool
    today: TodayProgressStats = field(default_factory=TodayProgressStats)
    remaining: RemainingStats = field(default_factory=RemainingStats)
    done: DoneTodayBreakdown = field(default_factory=DoneTodayBreakdown)
    goals: DailyGoalsStats = field(default_factory=DailyGoalsStats)
    composition: DeckCompositionStats = field(default_factory=DeckCompositionStats)


def compute_study_streak(col) -> int:
    """Computes continuous study streak in days."""
    try:
        rows = col.db.all("""
            SELECT DISTINCT cast((id/1000 - ? + 86400) / 86400 as integer) as day_idx
            FROM revlog
            WHERE type != 4
            ORDER BY day_idx DESC
        """, col.sched.day_cutoff)

        if not rows:
            return 0

        days = [r[0] for r in rows if r[0] <= 0]
        if not days:
            return 0

        streak = 0
        expected = 0
        if 0 not in days and -1 in days:
            expected = -1

        for d in sorted(days, reverse=True):
            if d == expected:
                streak += 1
                expected -= 1
            else:
                break
        return max(0, streak)
    except Exception:
        return 0


def compute_dashboard_stats(
    col,
    deck_id: Optional[int] = None,
    include_new_in_remaining: bool = True,
) -> DeckDashboardStats:
    """
    Computes all statistics for the Modern Stats Dashboard.
    Accurately integrates native revlog reviews done today and deck daily study limits.
    """
    is_per_deck = (deck_id is not None)
    deck_name = "Coleção Global"
    target_dids = []

    try:
        if is_per_deck and deck_id is not None:
            raw_decks = col.decks.all()
            tree = build_deck_tree(raw_decks)
            target_dids = get_deck_subtree_ids(tree, deck_id)
            deck_obj = col.decks.get(deck_id)
            if deck_obj:
                deck_name = deck_obj.get("name", "Baralho")
    except Exception as e:
        print(f"Error resolving target dids: {e}")

    # Native Limits
    new_limit = 20
    rev_limit = 200
    try:
        ref_did = deck_id if is_per_deck and deck_id is not None else col.decks.get_current_id()
        conf = col.decks.config_dict_for_deck_id(ref_did)
        if conf:
            new_limit = conf.get("new", {}).get("perDay", 20)
            rev_limit = conf.get("rev", {}).get("perDay", 200)
    except Exception:
        pass

    day_cutoff_sec = getattr(col.sched, "day_cutoff", time.time() + 86400)
    start_of_today_sec = day_cutoff_sec - 86400
    start_of_today_ms = int(start_of_today_sec * 1000)

    # 1. Revlog Query for Today's Activity (Using official column lastIvl)
    try:
        if is_per_deck and target_dids:
            placeholders = ",".join("?" for _ in target_dids)
            rev_sql = f"""
                SELECT
                    r.cid,
                    r.ease,
                    r.time,
                    r.type,
                    r.lastIvl,
                    r.ivl
                FROM revlog r
                JOIN cards c ON r.cid = c.id
                WHERE r.id > ? AND r.type != 4 AND (c.did IN ({placeholders}) OR c.odid IN ({placeholders}))
            """
            rev_rows = col.db.all(rev_sql, start_of_today_ms, *target_dids, *target_dids)
        else:
            rev_sql = """
                SELECT
                    cid,
                    ease,
                    time,
                    type,
                    lastIvl,
                    ivl
                FROM revlog
                WHERE id > ? AND type != 4
            """
            rev_rows = col.db.all(rev_sql, start_of_today_ms)
    except Exception as e:
        print(f"Error querying revlog: {e}")
        rev_rows = []

    studied_count = len(rev_rows)
    total_time_ms = 0
    pass_count = 0
    learn_reps = 0
    review_reps = 0
    mature_reviewed = 0
    again_count = 0
    new_card_cids = set()

    for row in rev_rows:
        cid, ease, r_time, r_type, last_ivl, ivl = row[0], row[1], row[2], row[3], row[4], row[5]
        total_time_ms += max(0, r_time)
        if ease > 1:
            pass_count += 1
        if ease == 1:
            again_count += 1

        if r_type == REVLOG_LRN:
            learn_reps += 1
            if last_ivl <= 0:
                new_card_cids.add(cid)
        elif r_type in (REVLOG_REV, REVLOG_RELRN, REVLOG_CRAM):
            review_reps += 1
            if last_ivl >= 21:
                mature_reviewed += 1

    new_learned = len(new_card_cids)
    time_spent_seconds = total_time_ms / 1000.0
    seconds_per_card = (time_spent_seconds / studied_count) if studied_count > 0 else 0.0
    cards_per_minute = (studied_count / (time_spent_seconds / 60.0)) if time_spent_seconds > 0 else 0.0
    retention_rate = (pass_count / studied_count * 100.0) if studied_count > 0 else 100.0
    fail_rate = (again_count / studied_count * 100.0) if studied_count > 0 else 0.0

    # 2. Cards Inventory & Composition Query
    today_sched_day = getattr(col.sched, "today", int(start_of_today_sec / 86400))

    try:
        if is_per_deck and target_dids:
            placeholders = ",".join("?" for _ in target_dids)
            card_sql = f"""
                SELECT
                    sum(CASE WHEN queue = 0 THEN 1 ELSE 0 END) as new_total,
                    sum(CASE WHEN queue IN (1, 3) THEN 1 ELSE 0 END) as learn_total,
                    sum(CASE WHEN queue = 2 AND due <= ? THEN 1 ELSE 0 END) as rev_due_today_total,
                    sum(CASE WHEN queue = 2 AND due = ? THEN 1 ELSE 0 END) as tomorrow_total,
                    sum(CASE WHEN queue = 2 AND ivl >= 21 THEN 1 ELSE 0 END) as mature_total,
                    sum(CASE WHEN queue = 2 AND ivl < 21 THEN 1 ELSE 0 END) as young_total,
                    sum(CASE WHEN queue = -1 THEN 1 ELSE 0 END) as suspended_total,
                    sum(CASE WHEN queue = -2 THEN 1 ELSE 0 END) as buried_total,
                    count(*) as total_cards
                FROM cards
                WHERE (did IN ({placeholders}) OR odid IN ({placeholders}))
            """
            card_row = col.db.first(card_sql, today_sched_day, today_sched_day + 1, *target_dids, *target_dids)
        else:
            card_sql = """
                SELECT
                    sum(CASE WHEN queue = 0 THEN 1 ELSE 0 END) as new_total,
                    sum(CASE WHEN queue IN (1, 3) THEN 1 ELSE 0 END) as learn_total,
                    sum(CASE WHEN queue = 2 AND due <= ? THEN 1 ELSE 0 END) as rev_due_today_total,
                    sum(CASE WHEN queue = 2 AND due = ? THEN 1 ELSE 0 END) as tomorrow_total,
                    sum(CASE WHEN queue = 2 AND ivl >= 21 THEN 1 ELSE 0 END) as mature_total,
                    sum(CASE WHEN queue = 2 AND ivl < 21 THEN 1 ELSE 0 END) as young_total,
                    sum(CASE WHEN queue = -1 THEN 1 ELSE 0 END) as suspended_total,
                    sum(CASE WHEN queue = -2 THEN 1 ELSE 0 END) as buried_total,
                    count(*) as total_cards
                FROM cards
            """
            card_row = col.db.first(card_sql, today_sched_day, today_sched_day + 1)
    except Exception as e:
        print(f"Error querying cards table: {e}")
        card_row = None

    if not card_row:
        card_row = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    unseen_total = card_row[0] or 0
    learn_total = card_row[1] or 0
    due_reviews_total = card_row[2] or 0
    tomorrow_forecast = card_row[3] or 0
    mature_total = card_row[4] or 0
    young_total = card_row[5] or 0
    suspended_total = card_row[6] or 0
    buried_total = card_row[7] or 0
    total_cards = card_row[8] or 0

    mature_pct = (mature_total / total_cards * 100.0) if total_cards > 0 else 0.0

    # 3. Calculate Cards Remaining FOR TODAY'S SESSION
    new_due_today = max(0, min(unseen_total, new_limit - new_learned))
    rev_due_today = max(0, min(due_reviews_total, rev_limit - review_reps))
    learn_due_today = learn_total

    total_remaining_today = (new_due_today if include_new_in_remaining else 0) + learn_due_today + rev_due_today

    streak_days = compute_study_streak(col)

    new_goal_pct = min(100.0, (new_learned / max(1, new_limit)) * 100.0)
    rev_goal_pct = min(100.0, (review_reps / max(1, rev_limit)) * 100.0)

    return DeckDashboardStats(
        deck_id=deck_id,
        deck_name=deck_name,
        is_per_deck=is_per_deck,
        today=TodayProgressStats(
            studied_count=studied_count,
            time_spent_seconds=time_spent_seconds,
            formatted_time=format_duration(time_spent_seconds),
            seconds_per_card=seconds_per_card,
            cards_per_minute=cards_per_minute,
            retention_rate_pct=retention_rate,
            streak_days=streak_days,
        ),
        remaining=RemainingStats(
            new_cards=new_due_today,
            learn_cards=learn_due_today,
            review_cards=rev_due_today,
            total_remaining=total_remaining_today,
            tomorrow_forecast=tomorrow_forecast,
        ),
        done=DoneTodayBreakdown(
            new_learned=new_learned,
            learn_reps=learn_reps,
            review_reps=review_reps,
            mature_reviewed=mature_reviewed,
            again_count=again_count,
            fail_rate_pct=fail_rate,
        ),
        goals=DailyGoalsStats(
            new_limit=new_limit,
            new_done=new_learned,
            new_pct=new_goal_pct,
            rev_limit=rev_limit,
            rev_done=review_reps,
            rev_pct=rev_goal_pct,
        ),
        composition=DeckCompositionStats(
            total_cards=total_cards,
            mature=mature_total,
            young=young_total,
            unseen=unseen_total,
            suspended=suspended_total,
            buried=buried_total,
            mature_pct=mature_pct,
            due_reviews_total=due_reviews_total,
        ),
    )
