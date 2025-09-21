import random
from .base import BaseStrategy
class RandomStrategy(BaseStrategy):
    def decide(self, my_history, opp_history, round_index):
        return random.choice(["C", "D"])
