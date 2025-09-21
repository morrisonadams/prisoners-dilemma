from .base import BaseStrategy
class WinStayLoseShift(BaseStrategy):
    def reset(self):
        self.last_move = "C"
    def decide(self, my_history, opp_history, round_index):
        if not my_history:
            self.last_move = "C"
            return self.last_move
        last_my = my_history[-1]
        last_opp = opp_history[-1]
        win = (last_my == last_opp)  # CC or DD treated as win
        if win:
            return last_my
        else:
            self.last_move = "C" if last_my == "D" else "D"
            return self.last_move
