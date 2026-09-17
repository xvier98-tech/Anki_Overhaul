# -*- coding: utf-8 -*-
"""
Fatigue & Cognitive Performance Analytics for Pomodoro Study Cycles.
Tracks cards reviewed, pace, and retention rate degradation across consecutive cycles.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import time


@dataclass
class PomodoroCycleRecord:
    cycle_index: int
    start_time: float
    end_time: float
    cards_reviewed: int = 0
    total_time_seconds: float = 0.0
    again_count: int = 0
    hard_count: int = 0
    good_count: int = 0
    easy_count: int = 0

    @property
    def total_answers(self) -> int:
        return self.again_count + self.hard_count + self.good_count + self.easy_count

    @property
    def retention_rate(self) -> float:
        total = self.total_answers
        if total == 0:
            return 0.0
        passed = self.hard_count + self.good_count + self.easy_count
        return (passed / total) * 100.0

    @property
    def average_seconds_per_card(self) -> float:
        if self.cards_reviewed == 0:
            return 0.0
        return self.total_time_seconds / self.cards_reviewed


class FatigueTracker:
    """Tracks session-level pomodoro cycles and detects cognitive fatigue."""

    def __init__(self):
        self.history: List[PomodoroCycleRecord] = []
        self.current_record: Optional[PomodoroCycleRecord] = None

    def start_cycle(self, cycle_index: int):
        now = time.time()
        self.current_record = PomodoroCycleRecord(
            cycle_index=cycle_index,
            start_time=now,
            end_time=now,
        )

    def record_card_answer(self, ease: int, time_spent_sec: float = 0.0):
        if not self.current_record:
            self.start_cycle(len(self.history) + 1)
        if self.current_record:
            self.current_record.cards_reviewed += 1
            self.current_record.total_time_seconds += time_spent_sec

            if ease == 1:
                self.current_record.again_count += 1
            elif ease == 2:
                self.current_record.hard_count += 1
            elif ease == 3:
                self.current_record.good_count += 1
            elif ease == 4:
                self.current_record.easy_count += 1

    def finish_cycle(self):
        if self.current_record:
            self.current_record.end_time = time.time()
            if self.current_record.total_time_seconds == 0:
                self.current_record.total_time_seconds = max(1.0, self.current_record.end_time - self.current_record.start_time)
            self.history.append(self.current_record)
            self.current_record = None

    def record_cycle(
        self,
        cycle_index: int,
        phase_type: str = "work",
        duration_seconds: float = 1500.0,
        cards_reviewed: int = 0,
        correct_count: int = 0,
    ):
        """Convenience method to register a completed cycle."""
        now = time.time()
        wrong_count = max(0, cards_reviewed - correct_count)
        record = PomodoroCycleRecord(
            cycle_index=cycle_index,
            start_time=now - duration_seconds,
            end_time=now,
            cards_reviewed=cards_reviewed,
            total_time_seconds=duration_seconds,
            again_count=wrong_count,
            good_count=correct_count,
        )
        self.history.append(record)
        self.current_record = None

    def get_average_pace_seconds(self) -> float:
        """Returns average seconds per card across recent cycles (default: 10s if no data)."""
        total_cards = sum(r.cards_reviewed for r in self.history)
        if self.current_record:
            total_cards += self.current_record.cards_reviewed

        total_time = sum(r.total_time_seconds for r in self.history)
        if self.current_record:
            total_time += self.current_record.total_time_seconds

        if total_cards > 0 and total_time > 0:
            return total_time / total_cards
        return 10.0

    def compute_eta(self, remaining_cards: int, work_duration_min: int = 25) -> Dict[str, Any]:
        """
        Computes predictive ETA (time in minutes and estimated pomodoros) to clear remaining cards.
        """
        pace_sec = self.get_average_pace_seconds()
        total_sec_needed = remaining_cards * pace_sec
        total_min_needed = total_sec_needed / 60.0
        pomodoros_needed = total_min_needed / max(1, work_duration_min)

        return {
            "pace_seconds": pace_sec,
            "estimated_seconds": int(total_sec_needed),
            "total_minutes": total_min_needed,
            "pomodoros_needed": max(1, round(pomodoros_needed, 1)) if remaining_cards > 0 else 0,
            "formatted_eta": f"~{int(total_min_needed)}m ({round(pomodoros_needed, 1)} 🍅)" if remaining_cards > 0 else "0m",
        }

    def analyze_fatigue(self) -> Dict[str, Any]:
        """
        Analyzes retention rate progression across successive cycles to detect fatigue.
        """
        if len(self.history) < 2:
            return {
                "fatigue_detected": False,
                "summary": "Dados insuficientes para análise de fadiga (mínimo 2 ciclos concluídos).",
                "cycles_data": [],
            }

        cycles_data = []
        retentions = []
        for r in self.history:
            ret = r.retention_rate
            retentions.append(ret)
            cycles_data.append({
                "cycle": r.cycle_index,
                "cards": r.cards_reviewed,
                "pace_sec": round(r.average_seconds_per_card, 1),
                "retention_pct": round(ret, 1),
                "again_count": r.again_count,
            })

        first_half = sum(retentions[:len(retentions)//2]) / (len(retentions)//2)
        second_half = sum(retentions[len(retentions)//2:]) / (len(retentions) - len(retentions)//2)

        drop = first_half - second_half
        fatigue_detected = drop >= 8.0

        summary = f"Retenção média inicial: {first_half:.1f}% | Final: {second_half:.1f}%."
        if fatigue_detected:
            summary += f" Queda de {drop:.1f}% detectada! Considere fazer uma pausa longa de 15 a 20 minutos."

        return {
            "fatigue_detected": fatigue_detected,
            "drop_percentage": round(drop, 1),
            "summary": summary,
            "cycles_data": cycles_data,
        }
