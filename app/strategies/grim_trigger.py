from .base import BaseStrategy
class GrimTrigger(BaseStrategy):
    def reset(self):
        super().reset()
        self.grim = False
    def decide(self, my_history, opp_history, round_index):
        if "D" in opp_history:
            self.grim = True
        return "D" if self.grim else "C"
