"""Shared tournament helpers used by both CLI and the web UI."""

from __future__ import annotations

import random
from dataclasses import asdict
from typing import Any, Dict, List, Sequence, Type

from .engine import Payoffs, play_match
from . import strategies as S
from .strategies import BaseStrategy

StrategyClass = Type[BaseStrategy]


def _canon(name: str) -> str:
    """Normalize a strategy name for comparisons."""
    return name.lower().strip().replace("-", "").replace("_", "")


def list_available_strategies() -> List[Dict[str, str]]:
    """Return metadata about all built-in strategies."""
    items: List[Dict[str, str]] = []
    for cls in S.ALL_STRATEGIES:
        items.append({
            "name": cls.__name__,
            "description": (cls.__doc__ or "").strip(),
        })
    return items


def resolve_strategies(only: Sequence[str] | None = None, exclude: Sequence[str] | None = None) -> List[StrategyClass]:
    """Select strategies based on optional inclusion/exclusion lists."""
    only_canon = {_canon(x) for x in only} if only else None
    exclude_canon = {_canon(x) for x in exclude} if exclude else set()

    selected: List[StrategyClass] = []
    for cls in S.ALL_STRATEGIES:
        name = _canon(cls.__name__)
        if only_canon is not None and name not in only_canon:
            continue
        if name in exclude_canon:
            continue
        selected.append(cls)
    return selected


def run_tournament(
    *,
    rounds: int = 150,
    continuation: float = 0.0,
    noise: float = 0.0,
    repeats: int = 1,
    seed: int | None = None,
    payoffs: Payoffs | None = None,
    only: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    strategy_classes: Sequence[StrategyClass] | None = None,
    rng: random.Random | None = None,
) -> Dict[str, Any]:
    """Run a full round-robin tournament and return serialized results."""
    if payoffs is None:
        payoffs = Payoffs()

    if strategy_classes is None:
        strategy_classes = resolve_strategies(only=only, exclude=exclude)

    strategy_classes = list(strategy_classes)
    if len(strategy_classes) < 2:
        raise ValueError("Need at least two strategies to run a tournament")

    if rng is None:
        rng = random.Random(seed)
    else:
        if seed is not None:
            rng.seed(seed)

    matches: List[Dict[str, Any]] = []

    totals: Dict[str, float] = {}
    rounds_played: Dict[str, int] = {}

    for rep in range(max(1, repeats)):
        players = [cls() for cls in strategy_classes]
        names = [p.__class__.__name__ for p in players]

        for i, player_a in enumerate(players):
            for j, player_b in enumerate(players):
                if j <= i:
                    continue
                result = play_match(
                    player_a,
                    player_b,
                    rounds=rounds,
                    continuation=continuation,
                    noise=noise,
                    payoffs=payoffs,
                    rng=rng,
                )
                row = {
                    "rep": rep,
                    "A": names[i],
                    "B": names[j],
                    "rounds": result["rounds"],
                    "score_A": result["scores"]["A"],
                    "score_B": result["scores"]["B"],
                    "avg_A": round(result["avg"]["A"], 4),
                    "avg_B": round(result["avg"]["B"], 4),
                    "history_A": result["history"]["A"],
                    "history_B": result["history"]["B"],
                }
                matches.append(row)

                totals[names[i]] = totals.get(names[i], 0.0) + row["score_A"]
                totals[names[j]] = totals.get(names[j], 0.0) + row["score_B"]
                rounds_played[names[i]] = rounds_played.get(names[i], 0) + row["rounds"]
                rounds_played[names[j]] = rounds_played.get(names[j], 0) + row["rounds"]

    standings = [
        {
            "strategy": name,
            "total_score": totals[name],
            "total_rounds": rounds_played[name],
            "avg_per_round": round(totals[name] / rounds_played[name], 4) if rounds_played[name] else 0.0,
        }
        for name in totals
    ]
    standings.sort(key=lambda r: (-r["avg_per_round"], -r["total_score"], r["strategy"]))

    result: Dict[str, Any] = {
        "params": {
            "rounds": rounds,
            "continuation": continuation,
            "noise": noise,
            "repeats": repeats,
            "seed": seed,
            "payoffs": asdict(payoffs),
        },
        "strategies": [cls.__name__ for cls in strategy_classes],
        "matches": matches,
        "standings": standings,
    }
    return result
