from .base import BaseStrategy
class Prober(BaseStrategy):
    """
    D, C, C start. If opponent retaliates during probe, switch to TFT. Else exploit with D.
    """
    def reset(self):
        super().reset()
        self.mode = "probe"  # "probe" -> "tft" or "exploit"
    def decide(self, my_history, opp_history, round_index):
        if len(my_history) < 1:
            return "D"
        if len(my_history) == 1:
            return "C"
        if len(my_history) == 2:
            return "C"
        if self.mode == "probe":
            if "D" in opp_history[:3]:
                self.mode = "tft"
            else:
                self.mode = "exploit"
        if self.mode == "tft":
            return opp_history[-1] if opp_history else "C"
        else:
            return "D"
