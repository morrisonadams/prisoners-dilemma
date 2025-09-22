from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..media import MediaReport

class BaseStrategy(ABC):
    """
    Base class for strategies. Implement decide and optionally reset.
    decide should return "C" or "D".
    """
    def __init__(self):
        self._rumors: List["MediaReport"] = []
        self.reset()

    def name(self) -> str:
        return self.__class__.__name__

    def reset(self):
        # Reset any internal state between matches
        self._rumors.clear()

    def media_reset(self) -> None:
        """Hook to reset any media-related state between tournaments."""

        pass

    def receive_media(self, report: "MediaReport") -> None:
        """Handle a media report broadcast to the strategy."""

        self._rumors.append(report)

    @property
    def rumors(self) -> List["MediaReport"]:
        """Return the rumors observed by this strategy since the last reset."""

        return list(self._rumors)

    @abstractmethod
    def decide(self, my_history, opp_history, round_index: int) -> str:
        ...

    def __repr__(self):
        return f"{self.name()}"
