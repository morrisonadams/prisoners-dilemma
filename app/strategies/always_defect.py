from .base import BaseStrategy
class AlwaysDefect(BaseStrategy):
    def decide(self, my_history, opp_history, round_index):
        return "D"
