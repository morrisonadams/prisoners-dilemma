"""Media network utilities used to circulate match outcomes between strategies."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .strategies.base import BaseStrategy

MatchID = Tuple[int, str, str, int]


@dataclass(frozen=True)
class MatchOutcome:
    """Normalized data describing the result of a single match."""

    match_id: MatchID
    rep: int
    ordinal: int
    player_a: str
    player_b: str
    rounds: int
    scores: Dict[str, float]
    averages: Dict[str, float]
    history: Dict[str, str]

    def _named(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {self.player_a: data.get("A"), self.player_b: data.get("B")}

    def named_scores(self) -> Dict[str, float]:
        return self._named(self.scores)

    def named_averages(self) -> Dict[str, float]:
        return self._named(self.averages)

    def named_history(self) -> Dict[str, str]:
        return self._named(self.history)

    def to_payload(self, *, accurate: bool = True) -> Dict[str, Any]:
        """Return a serializable payload describing the outcome."""

        payload = {
            "match_id": self.match_id,
            "rep": self.rep,
            "ordinal": self.ordinal,
            "players": {"A": self.player_a, "B": self.player_b},
            "rounds": self.rounds,
            "scores": self.named_scores(),
            "averages": self.named_averages(),
            "history": self.named_history(),
        }
        if accurate:
            return payload
        swapped_scores = {
            self.player_a: payload["scores"][self.player_b],
            self.player_b: payload["scores"][self.player_a],
        }
        swapped_averages = {
            self.player_a: payload["averages"][self.player_b],
            self.player_b: payload["averages"][self.player_a],
        }
        swapped_history = {
            self.player_a: payload["history"][self.player_b],
            self.player_b: payload["history"][self.player_a],
        }
        rumor = dict(payload)
        rumor.update({
            "scores": swapped_scores,
            "averages": swapped_averages,
            "history": swapped_history,
            "rumor": True,
        })
        return rumor


@dataclass
class MediaReport:
    """A report emitted by a media outlet."""

    match_id: MatchID
    outlet: str
    outcome: MatchOutcome
    payload: Dict[str, Any]
    accurate: bool
    delay: int = 0

    def for_broadcast(self) -> Dict[str, Any]:
        data = dict(self.payload)
        data.setdefault("match_id", self.match_id)
        data.setdefault("source", self.outlet)
        data.setdefault("accurate", self.accurate)
        return data


@dataclass
class MediaOutlet:
    """A media outlet with configurable coverage, accuracy and delivery delay."""

    name: str
    coverage: float = 1.0
    accuracy: float = 1.0
    delay: int | Sequence[int] | Tuple[int, int] = 0
    avoid_duplicates: bool = True
    _reported_ids: set[MatchID] = field(default_factory=set, init=False, repr=False)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def consider(self, outcome: MatchOutcome, rng: random.Random) -> MediaReport | None:
        """Return a report if the outlet chooses to cover the outcome."""

        if self.avoid_duplicates and outcome.match_id in self._reported_ids:
            return None
        if rng.random() > self._clamp(self.coverage):
            return None
        accurate = rng.random() <= self._clamp(self.accuracy)
        delay = self._sample_delay(rng)
        payload = outcome.to_payload(accurate=accurate)
        payload = dict(payload)
        payload.setdefault("match_id", outcome.match_id)
        payload.setdefault("source", self.name)
        payload.setdefault("accurate", accurate)
        report = MediaReport(
            match_id=outcome.match_id,
            outlet=self.name,
            outcome=outcome,
            payload=payload,
            accurate=accurate,
            delay=delay,
        )
        if self.avoid_duplicates:
            self._reported_ids.add(outcome.match_id)
        return report

    def _sample_delay(self, rng: random.Random) -> int:
        delay = self.delay
        if isinstance(delay, dict):  # type: ignore[unreachable]
            choices = delay.get("choices")
            if choices:
                clean = [int(v) for v in choices]
                return max(0, int(rng.choice(clean)))
            low = int(delay.get("min", 0))
            high = int(delay.get("max", low))
            if high < low:
                low, high = high, low
            return max(0, int(rng.randint(low, high)))
        if isinstance(delay, tuple):
            if len(delay) == 2:
                low, high = delay
                low_i = int(low)
                high_i = int(high)
                if high_i < low_i:
                    low_i, high_i = high_i, low_i
                return max(0, int(rng.randint(low_i, high_i)))
            choices = [int(v) for v in delay]
            return max(0, int(rng.choice(choices))) if choices else 0
        if isinstance(delay, Sequence) and not isinstance(delay, (str, bytes, bytearray)):
            choices = [int(v) for v in delay]
            return max(0, int(rng.choice(choices))) if choices else 0
        try:
            return max(0, int(delay))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "MediaOutlet":
        if isinstance(config, MediaOutlet):
            return config
        if not isinstance(config, dict):
            raise TypeError("Outlet configuration must be a dict or MediaOutlet instance")
        cfg = dict(config)
        name = cfg.pop("name")
        coverage = float(cfg.pop("coverage", 1.0))
        accuracy = float(cfg.pop("accuracy", 1.0))
        delay = cfg.pop("delay", 0)
        avoid_duplicates = bool(cfg.pop("avoid_duplicates", True))
        if isinstance(delay, dict):
            if "choices" in delay:
                delay = [int(v) for v in delay["choices"]]
            else:
                low = int(delay.get("min", 0))
                high = int(delay.get("max", low))
                delay = (low, high)
        return cls(
            name=name,
            coverage=coverage,
            accuracy=accuracy,
            delay=delay,
            avoid_duplicates=avoid_duplicates,
        )


@dataclass
class MediaNetwork:
    """Coordinates a collection of media outlets and delivers reports to strategies."""

    outlets: Sequence[MediaOutlet] = field(default_factory=list)
    rng: random.Random | None = None
    _pending: List[Tuple[int, MediaReport]] = field(default_factory=list, init=False, repr=False)
    _listeners: List[BaseStrategy] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.outlets = [MediaOutlet.from_config(o) if not isinstance(o, MediaOutlet) else o for o in self.outlets]
        if self.rng is None:
            self.rng = random.Random()

    def bind_players(self, players: Sequence[BaseStrategy], *, reset_pending: bool = True) -> None:
        """Attach player instances that should receive future broadcasts."""

        self._listeners = list(players)
        if reset_pending:
            self._pending.clear()
        for player in self._listeners:
            player.media_reset()

    def set_rng(self, rng: random.Random | None) -> None:
        self.rng = rng if rng is not None else random.Random()

    def publish(self, outcome: MatchOutcome) -> List[MediaReport]:
        """Publish an outcome to all outlets and deliver any ready reports."""

        if self.rng is None:
            self.rng = random.Random()
        delivered = []
        delivered.extend(self._advance_pending())
        for outlet in self.outlets:
            report = outlet.consider(outcome, self.rng)
            if not report:
                continue
            if report.delay > 0:
                self._pending.append((report.delay, report))
            else:
                self._broadcast(report)
                delivered.append(report)
        return delivered

    def drain(self) -> List[MediaReport]:
        """Force delivery of any pending reports."""

        delivered = []
        while self._pending:
            delivered.extend(self._advance_pending(force=True))
        return delivered

    def _advance_pending(self, *, force: bool = False) -> List[MediaReport]:
        if not self._pending:
            return []
        ready: List[MediaReport] = []
        remaining: List[Tuple[int, MediaReport]] = []
        for delay, report in self._pending:
            next_delay = 0 if force else max(0, delay - 1)
            if next_delay == 0:
                ready.append(report)
            else:
                remaining.append((next_delay, report))
        self._pending = remaining
        for report in ready:
            self._broadcast(report)
        return ready

    def _broadcast(self, report: MediaReport) -> None:
        if not self._listeners:
            return
        for player in self._listeners:
            player.receive_media(report)

    @classmethod
    def from_config(cls, config: Dict[str, Any], *, rng: random.Random | None = None) -> "MediaNetwork":
        if isinstance(config, MediaNetwork):
            network = config
            if rng is not None:
                network.set_rng(rng)
            return network
        if not isinstance(config, dict):
            raise TypeError("Media config must be a dict or MediaNetwork instance")
        outlets_cfg: Iterable[Any] = config.get("outlets", [])
        outlets = [MediaOutlet.from_config(item) for item in outlets_cfg]
        network = cls(outlets=outlets, rng=rng)
        return network
