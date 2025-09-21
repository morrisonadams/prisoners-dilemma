from .base import BaseStrategy
class TitForTat(BaseStrategy):
    def decide(self, my_history, opp_history, round_index):
        if not opp_history:
            return "C"
        return opp_history[-1]
