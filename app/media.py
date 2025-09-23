"""Media network utilities used to circulate match outcomes between strategies."""

from __future__ import annotations

import copy
import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .strategies.base import BaseStrategy

MatchID = Tuple[int, str, str, int]


# Preset configurations that can be reused across the CLI and web UI.
MEDIA_PRESETS: Dict[str, Dict[str, Any]] = {
    "none": {
        "outlets": [],
        "subscriptions": {"limit": 0, "defaults": {}}
    },
    "basic": {
        "outlets": [
            {
                "name": "GlobalTruth",
                "coverage": 0.85,
                "accuracy": 0.98,
                "delay": [0, 1],
            },
            {
                "name": "AxelrodTimes",
                "coverage": 0.65,
                "accuracy": 0.9,
                "delay": [0, 1, 2],
            },
            {
                "name": "RumorMill",
                "coverage": 0.5,
                "accuracy": 0.55,
                "delay": [0, 1, 2, 3],
            },
        ],
        "subscriptions": {
            "limit": 2,
            "defaults": {},
        },
    },
}

DEFAULT_MEDIA_PRESET = "basic"


def clone_media_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of the provided media configuration."""

    return copy.deepcopy(config)


def resolve_media_config(spec: Any) -> Dict[str, Any] | None:
    """Normalize a media configuration or preset reference.

    Accepts dictionaries, preset names, or JSON strings. Returns a copy of the
    resolved configuration or ``None`` if the specification is falsy.
    """

    if spec in (None, "", False):
        return None
    if isinstance(spec, dict):
        return clone_media_config(spec)
    if isinstance(spec, str):
        value = spec.strip()
        if not value:
            return None
        preset = MEDIA_PRESETS.get(value) or MEDIA_PRESETS.get(value.lower())
        if preset is not None:
            return clone_media_config(preset)
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid media configuration: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Media configuration JSON must decode to an object")
        return clone_media_config(parsed)
    raise TypeError("Media configuration must be a dict, preset name, or JSON string")


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

    def to_config(self) -> Dict[str, Any]:
        delay = self.delay
        if isinstance(delay, tuple):
            delay_value: Sequence[int] = list(delay)
        else:
            delay_value = delay  # type: ignore[assignment]
        return {
            "name": self.name,
            "coverage": self.coverage,
            "accuracy": self.accuracy,
            "delay": delay_value,
            "avoid_duplicates": self.avoid_duplicates,
        }


@dataclass
class MediaNetwork:
    """Coordinates a collection of media outlets and delivers reports to strategies."""

    outlets: Sequence[MediaOutlet] = field(default_factory=list)
    subscription_limit: int | None = None
    default_enrollments: Dict[str, Sequence[str]] = field(default_factory=dict)
    enrollments: Dict[str, Sequence[str]] = field(default_factory=dict)
    rng: random.Random | None = None
    _pending: List[Tuple[int, MediaReport]] = field(default_factory=list, init=False, repr=False)
    _listeners: List[BaseStrategy] = field(default_factory=list, init=False, repr=False)
    _resolved_enrollments: Dict[str, List[str]] = field(default_factory=dict, init=False, repr=False)
    _auto_enrollments: Dict[str, List[str]] = field(default_factory=dict, init=False, repr=False)
    _report_log: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.outlets = [MediaOutlet.from_config(o) if not isinstance(o, MediaOutlet) else o for o in self.outlets]
        if self.rng is None:
            self.rng = random.Random()
        if self.subscription_limit is not None:
            try:
                self.subscription_limit = max(0, int(self.subscription_limit))
            except (TypeError, ValueError):
                self.subscription_limit = None
        self.default_enrollments = {
            key: list(value)
            for key, value in (self.default_enrollments or {}).items()
        }
        self.enrollments = {
            key: list(value)
            for key, value in (self.enrollments or {}).items()
        }
        self._resolve_subscriptions()

    def reset_logs(self) -> None:
        self._report_log.clear()

    def bind_players(self, players: Sequence[BaseStrategy], *, reset_pending: bool = True) -> None:
        """Attach player instances that should receive future broadcasts."""

        self._listeners = list(players)
        if reset_pending:
            self._pending.clear()
        for player in self._listeners:
            player.media_reset()
        active = {player.name() for player in self._listeners}
        self._auto_enrollments = self._determine_auto_enrollments()
        self._resolve_subscriptions()
        self._apply_active_players(active)

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
        outlet_name = report.outlet
        has_enrollment_rules = bool(self._resolved_enrollments)
        for player in self._listeners:
            name = player.name()
            if has_enrollment_rules:
                allowed = self._resolved_enrollments.get(name)
                if not allowed or outlet_name not in allowed:
                    continue
            player.receive_media(report)
            self._log_delivery(report, name)

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
        subscriptions = config.get("subscriptions") or {}
        limit = subscriptions.get("limit")
        defaults = subscriptions.get("defaults") or {}
        enrollments = subscriptions.get("enrollments") or {}
        network = cls(
            outlets=outlets,
            subscription_limit=limit,
            default_enrollments=defaults,
            enrollments=enrollments,
            rng=rng,
        )
        return network

    # Internal helpers -------------------------------------------------

    def _normalize_choices(self, choices: Sequence[str] | None) -> List[str]:
        available = {outlet.name for outlet in self.outlets}
        limit = self.subscription_limit
        result: List[str] = []
        if not choices:
            return result
        for choice in choices:
            name = str(choice)
            if name not in available or name in result:
                continue
            result.append(name)
            if limit is not None and len(result) >= limit:
                break
        return result

    def _resolve_subscriptions(self) -> None:
        resolved: Dict[str, List[str]] = {}
        for strategy, outlets in (self.default_enrollments or {}).items():
            resolved[strategy] = self._normalize_choices(outlets)
        for strategy, outlets in (self._auto_enrollments or {}).items():
            normalized = self._normalize_choices(outlets)
            if normalized:
                resolved[strategy] = normalized
        for strategy, outlets in (self.enrollments or {}).items():
            resolved[strategy] = self._normalize_choices(outlets)
        self._resolved_enrollments = resolved
        self._prune_enrollments()

    def _determine_auto_enrollments(self) -> Dict[str, List[str]]:
        if not self._listeners:
            return {}
        auto: Dict[str, List[str]] = {}
        for player in self._listeners:
            try:
                choices = player.preferred_media_outlets(self.outlets)
            except AttributeError:
                continue
            normalized = self._normalize_choices(choices)
            if normalized:
                auto[player.name()] = normalized
        return auto

    def _apply_active_players(self, active: set[str]) -> None:
        if not active:
            return
        has_rules = bool(self.default_enrollments or self.enrollments or self.subscription_limit is not None)
        if not has_rules:
            self._resolved_enrollments = {}
            return
        resolved: Dict[str, List[str]] = {}
        for name in active:
            if name in self._resolved_enrollments:
                resolved[name] = self._resolved_enrollments[name]
            else:
                defaults = self.default_enrollments.get(name)
                resolved[name] = self._normalize_choices(defaults)
        self._resolved_enrollments = resolved


    def _prune_enrollments(self) -> None:
        if not self._resolved_enrollments:
            return
        available = {outlet.name for outlet in self.outlets}
        for strategy, outlets in list(self._resolved_enrollments.items()):
            clean = [name for name in outlets if name in available]
            if clean:
                self._resolved_enrollments[strategy] = clean
            else:
                self._resolved_enrollments.pop(strategy, None)

    def _log_delivery(self, report: MediaReport, recipient: str) -> None:
        payload = dict(report.for_broadcast())
        match_id_value = payload.get("match_id", report.match_id)
        if isinstance(match_id_value, tuple):
            match_id_value = list(match_id_value)
            payload["match_id"] = match_id_value
        entry = {
            "recipient": recipient,
            "outlet": report.outlet,
            "accurate": report.accurate,
            "delay": report.delay,
            "rep": report.outcome.rep,
            "ordinal": report.outcome.ordinal,
            "match_id": match_id_value,
            "payload": payload,
        }
        self._report_log.append(entry)

    def export_state(self, *, include_reports: bool = True, reset_reports: bool = False) -> Dict[str, Any]:
        """Return a serializable snapshot of the network configuration and logs."""

        subscriptions: Dict[str, Any] = {
            "limit": self.subscription_limit,
            "defaults": {
                name: list(outlets)
                for name, outlets in (self.default_enrollments or {}).items()
            },
            "enrollments": {
                name: list(outlets)
                for name, outlets in self._resolved_enrollments.items()
            },
        }
        data: Dict[str, Any] = {
            "config": {
                "outlets": [outlet.to_config() for outlet in self.outlets],
                "subscriptions": subscriptions,
            }
        }
        if include_reports:
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for entry in self._report_log:
                recipient = entry.get("recipient")
                payload = {k: v for k, v in entry.items() if k != "recipient"}
                grouped.setdefault(recipient, []).append(payload)
            data["reports"] = grouped
        if reset_reports:
            self._report_log.clear()
        return data
