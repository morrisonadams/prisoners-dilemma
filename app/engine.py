from dataclasses import dataclass
from typing import List, Tuple
import random

Move = str  # "C" or "D"

@dataclass
class Payoffs:
    T: int = 5  # Temptation to defect
    R: int = 3  # Reward for mutual cooperation
    P: int = 1  # Punishment for mutual defection
    S: int = 0  # Sucker payoff

def play_round(a: Move, b: Move, p: Payoffs) -> tuple[int, int]:
    if a == "C" and b == "C":
        return p.R, p.R
    if a == "C" and b == "D":
        return p.S, p.T
    if a == "D" and b == "C":
        return p.T, p.S
    return p.P, p.P

def noisy(move: Move, noise: float) -> Move:
    if noise <= 0.0:
        return move
    return ("D" if move == "C" else "C") if random.random() < noise else move

def play_match(playerA, playerB, rounds: int, continuation: float, noise: float, payoffs: Payoffs, rng: random.Random):
    playerA.reset()
    playerB.reset()
    a_hist: List[Move] = []
    b_hist: List[Move] = []
    total_a = 0
    total_b = 0
    r = 0
    while True:
        a_move = playerA.decide(a_hist, b_hist, r)
        b_move = playerB.decide(b_hist, a_hist, r)  # symmetric view
        a_play = noisy(a_move, noise)
        b_play = noisy(b_move, noise)
        s_a, s_b = play_round(a_play, b_play, payoffs)
        total_a += s_a
        total_b += s_b
        a_hist.append(a_play)
        b_hist.append(b_play)
        r += 1
        if continuation > 0.0:
            if rng.random() >= continuation:
                break
        else:
            if r >= rounds:
                break
    return {
        "rounds": r,
        "history": {"A": "".join(a_hist), "B": "".join(b_hist)},
        "scores": {"A": total_a, "B": total_b},
        "avg": {"A": total_a / r, "B": total_b / r}
    }
