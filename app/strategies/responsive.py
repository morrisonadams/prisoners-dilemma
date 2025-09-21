from .base import BaseStrategy
class Responsive(BaseStrategy):
    def decide(self, my_history, opp_history, round_index):
        if not opp_history:
            return "C"
        c = opp_history.count("C")
        d = opp_history.count("D")
        return "C" if c >= d else "D"
