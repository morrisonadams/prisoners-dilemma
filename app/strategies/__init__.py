from .base import BaseStrategy
from .always_cooperate import AlwaysCooperate
from .always_defect import AlwaysDefect
from .tit_for_tat import TitForTat
from .grim_trigger import GrimTrigger
from .win_stay_lose_shift import WinStayLoseShift
from .random_strategy import RandomStrategy
from .prober import Prober
from .soft_grudger import SoftGrudger
from .responsive import Responsive
from .grudger import Grudger

ALL_STRATEGIES = [
    AlwaysCooperate,
    AlwaysDefect,
    TitForTat,
    GrimTrigger,
    WinStayLoseShift,
    RandomStrategy,
    Prober,
    SoftGrudger,
    Responsive,
    Grudger,
]
