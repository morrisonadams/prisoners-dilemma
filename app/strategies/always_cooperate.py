from .base import BaseStrategy
class AlwaysCooperate(BaseStrategy):
    def decide(self, my_history, opp_history, round_index):
        return "C"
