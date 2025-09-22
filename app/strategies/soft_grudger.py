from .base import BaseStrategy
class SoftGrudger(BaseStrategy):
    def reset(self):
        super().reset()
        self.punish = 0
    def decide(self, my_history, opp_history, round_index):
        if opp_history and opp_history[-1] == "D":
            self.punish = 2  # punish next two rounds
        if self.punish > 0:
            self.punish -= 1
            return "D"
        return "C"
