from .base import BaseStrategy
class Grudger(BaseStrategy):
    def reset(self):
        super().reset()
        self.grudge = False
    def decide(self, my_history, opp_history, round_index):
        if "D" in opp_history:
            self.grudge = True
        return "D" if self.grudge else "C"
