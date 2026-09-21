"""
recommender.py
Generates a "next workout" recommendation by treating muscle-group balance
as a greedy scheduling problem: repeatedly hand the next slot to whichever
muscle group is currently most under-trained relative to an equal-share
target, exactly the max-heap pattern behind problems like Task Scheduler /
Reorganize String.

Why a heap instead of the obvious "just call idxmax() in a loop": picking
the single most-deficient group by scanning is O(g) per pick, so filling a
k-slot session costs O(k*g). A binary heap makes each pick-and-reinsert
O(log g), for O(k log g) overall - the gap widens as the exercise catalog
(g = number of muscle groups) grows.

The greedy choice (always fully address the current worst deficit before
moving on) is provably locally optimal for this formulation, but not
globally optimal in general - e.g. it can't look ahead to avoid starving a
group of its only remaining exercise. That's a deliberate, explainable
tradeoff (simplicity and speed over exhaustive search), not an oversight.
"""

import heapq
from datetime import date

import analytics
import db

DAYS_WINDOW = 30
NICHE_BONUS_DAYS = 14  # treat a niche exercise as ~2 extra weeks "overdue" -
                        # surfacing under-the-radar lifts is a project goal,
                        # not just filling the deficit fastest
NEVER_TRAINED_RECENCY = 10_000  # sentinel "days since last trained" for a cold-start exercise
DEFAULT_SESSION_VOLUME = 250.0  # fallback volume estimate for an exercise with no history yet
MIN_DEFICIT_TO_REQUEUE = 0.5    # stop re-queuing a group once its gap is this small (percentage points)


def muscle_group_deficits(days: int = DAYS_WINDOW) -> dict:
    """
    target share for every muscle group in the catalog = 100 / (number of
    groups) - a simple, defensible balance heuristic: no single group should
    dominate training volume. deficit = target% - actual% over the trailing
    window, so a muscle group you've never trained starts at its full target
    as a deficit (correct cold-start behavior), and an over-trained group
    gets a negative deficit (never recommended).
    """
    catalog = db.get_all_exercises()  # (id, name, muscle_group, is_niche)
    groups = sorted({row[2] for row in catalog})
    if not groups:
        return {}
    target_pct = 100.0 / len(groups)

    balance_df = analytics.muscle_group_balance(days=days)
    actual_pct = (
        dict(zip(balance_df["muscle_group"], balance_df["pct_of_total"]))
        if not balance_df.empty else {}
    )

    return {g: round(target_pct - actual_pct.get(g, 0.0), 2) for g in groups}


def recommend_next_workout(session_size: int = 4, days: int = DAYS_WINDOW) -> list[dict]:
    """
    Greedily builds a `session_size`-exercise workout: pop the most deficient
    muscle group off a max-heap, assign it the best available exercise
    (favoring the longest-untrained and, as a tiebreak/bonus, niche lifts),
    then re-queue that group with a reduced deficit if there's still gap left
    and another exercise to fill it with. Returns [] if the exercise catalog
    is empty.
    """
    deficits = muscle_group_deficits(days=days)
    if not deficits:
        return []

    last_trained = db.get_exercise_last_trained()
    avg_volume = db.get_exercise_avg_session_volume()

    by_group: dict[str, list[dict]] = {}
    for _id, name, group, is_niche in db.get_all_exercises():
        by_group.setdefault(group, []).append({"name": name, "is_niche": bool(is_niche)})

    today = date.today()

    def recency_days(name: str) -> int:
        last = last_trained.get(name)
        if not last:
            return NEVER_TRAINED_RECENCY
        return (today - date.fromisoformat(last)).days

    def score(exercise: dict) -> float:
        bonus = NICHE_BONUS_DAYS if exercise["is_niche"] else 0
        return recency_days(exercise["name"]) + bonus

    heap = [(-deficit, group) for group, deficit in deficits.items()]
    heapq.heapify(heap)

    used_exercises: set[str] = set()
    picks: list[dict] = []

    while heap and len(picks) < session_size:
        neg_deficit, group = heapq.heappop(heap)
        deficit = -neg_deficit
        if deficit <= 0:
            continue  # already at or above its target share - nothing to correct

        candidates = [e for e in by_group.get(group, []) if e["name"] not in used_exercises]
        if not candidates:
            continue  # this group is tapped out of exercises for this session

        chosen = max(candidates, key=score)
        used_exercises.add(chosen["name"])
        picks.append({
            "exercise": chosen["name"],
            "muscle_group": group,
            "is_niche": chosen["is_niche"],
            "days_since_trained": None if recency_days(chosen["name"]) == NEVER_TRAINED_RECENCY
                                  else recency_days(chosen["name"]),
            "deficit_pct": round(deficit, 1),
            "est_volume": round(avg_volume.get(chosen["name"], DEFAULT_SESSION_VOLUME), 1),
        })

        remaining_candidates = [e for e in by_group.get(group, []) if e["name"] not in used_exercises]
        # Model one session as closing an equal share of what's left among the
        # exercises still available for this group (including the one just used) -
        # bounded, strictly decreasing, and needs no cross-group volume units.
        share_closed = deficit / (len(remaining_candidates) + 1)
        remaining_deficit = deficit - share_closed
        if remaining_deficit > MIN_DEFICIT_TO_REQUEUE and remaining_candidates:
            heapq.heappush(heap, (-remaining_deficit, group))

    return picks
