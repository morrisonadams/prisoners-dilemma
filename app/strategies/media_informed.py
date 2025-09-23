"""Strategies that consult media reports to guide their behaviour."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Tuple, TYPE_CHECKING

from .base import BaseStrategy

if TYPE_CHECKING:
    from ..media import MediaReport


class MediaSentinel(BaseStrategy):
    """Tit-for-tat that opens cautiously when outlets report frequent defections."""

    def __init__(self, window: int = 30, caution_threshold: float = 0.55) -> None:
        self._window = max(1, int(window))
        self._caution_threshold = max(0.0, min(1.0, caution_threshold))
        self._recent_counts: Deque[Tuple[int, int]] = deque()
        self._coop_total = 0
        self._defect_total = 0
        super().__init__()

    def media_reset(self) -> None:
        self._recent_counts.clear()
        self._coop_total = 0
        self._defect_total = 0

    def reset(self) -> None:
        super().reset()
        self._starting_move = "C"

    def receive_media(self, report: "MediaReport") -> None:
        super().receive_media(report)
        if not getattr(report, "accurate", False):
            return
        history = report.payload.get("history", {})
        coop = 0
        defect = 0
        for actions in history.values():
            if not actions:
                continue
            coop += actions.count("C")
            defect += actions.count("D")
        if coop or defect:
            self._recent_counts.append((coop, defect))
            self._coop_total += coop
            self._defect_total += defect
            while len(self._recent_counts) > self._window:
                old_coop, old_defect = self._recent_counts.popleft()
                self._coop_total -= old_coop
                self._defect_total -= old_defect

    def _hostile_environment(self) -> bool:
        total = self._coop_total + self._defect_total
        if total < 1:
            return False
        return (self._defect_total / total) >= self._caution_threshold

    def decide(self, my_history, opp_history, round_index: int) -> str:
        if round_index == 0:
            self._starting_move = "D" if self._hostile_environment() else "C"
            return self._starting_move
        if opp_history and opp_history[-1] == "D":
            return "D"
        return "C"


class MediaTrendFollower(BaseStrategy):
    """Win-stay/lose-shift with openings guided by the highest scoring reported strategy."""

    def __init__(self) -> None:
        self._best_player: str | None = None
        self._best_score: float = float("-inf")
        self._best_action: str = "C"
        super().__init__()

    def media_reset(self) -> None:
        self._best_player = None
        self._best_score = float("-inf")
        self._best_action = "C"

    def receive_media(self, report: "MediaReport") -> None:
        super().receive_media(report)
        if not getattr(report, "accurate", False):
            return
        averages = report.payload.get("averages", {})
        history = report.payload.get("history", {})
        if not averages:
            return
        # Pick the strategy with the best reported average score.
        best_name, best_score = max(
            ((name, float(score)) for name, score in averages.items()),
            key=lambda item: item[1],
        )
        sequence = history.get(best_name, "")
        last_move = sequence[-1] if sequence else "C"
        self._best_player = best_name
        self._best_score = best_score
        self._best_action = last_move if last_move in ("C", "D") else "C"

    def decide(self, my_history, opp_history, round_index: int) -> str:
        if round_index == 0:
            return self._best_action
        if not my_history:
            return self._best_action
        last_me = my_history[-1]
        last_opp = opp_history[-1] if opp_history else "C"
        if last_me == last_opp:
            if last_me == "D":
                # Falling back to the media trend prevents locking into mutual defection.
                return self._best_action
            return last_me
        if last_me == "C" and last_opp == "D":
            return "D"
        # We defected while the opponent cooperated; lean on the trend rather than persist.
        return self._best_action


class MediaWatchdog(BaseStrategy):
    """Adjusts between grim and generous modes based on outlet reliability."""

    def __init__(self, strict_threshold: float = 0.75) -> None:
        self._strict_threshold = max(0.0, min(1.0, strict_threshold))
        self._outlet_stats: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0])
        self._grim_active = False
        super().__init__()

    def media_reset(self) -> None:
        self._outlet_stats = defaultdict(lambda: [0, 0])

    def reset(self) -> None:
        super().reset()
        self._grim_active = False

    def receive_media(self, report: "MediaReport") -> None:
        super().receive_media(report)
        stats = self._outlet_stats[report.outlet]
        if report.accurate:
            stats[0] += 1
        else:
            stats[1] += 1

    def _network_reliability(self) -> float:
        if not self._outlet_stats:
            return 0.5
        weighted_sum = 0.0
        total_weight = 0
        for accurate, rumors in self._outlet_stats.values():
            total = accurate + rumors
            if total <= 0:
                continue
            weighted_sum += accurate / total * total
            total_weight += total
        if total_weight == 0:
            return 0.5
        return weighted_sum / total_weight

    def decide(self, my_history, opp_history, round_index: int) -> str:
        reliability = self._network_reliability()
        if reliability >= self._strict_threshold:
            if opp_history and opp_history[-1] == "D":
                self._grim_active = True
            if self._grim_active:
                return "D"
            return "C"
        # Low trust in the network encourages a forgiving posture.
        recent = opp_history[-2:] if len(opp_history) >= 2 else opp_history
        if recent == ["D", "D"]:
            return "D"
        if opp_history and opp_history[-1] == "D":
            return "C"
        if round_index == 0:
            return "C"
        if my_history and my_history[-1] == "D":
            # If we defected last round without provocation, ease back to cooperation.
            return "C"
        return "C"
