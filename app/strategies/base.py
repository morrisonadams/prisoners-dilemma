from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Base class for strategies. Implement decide and optionally reset.
    decide should return "C" or "D".
    """
    def __init__(self):
        self.reset()

    def name(self) -> str:
        return self.__class__.__name__

    def reset(self):
        # Reset any internal state between matches
        pass

    @abstractmethod
    def decide(self, my_history, opp_history, round_index: int) -> str:
        ...

    def __repr__(self):
        return f"{self.name()}"
