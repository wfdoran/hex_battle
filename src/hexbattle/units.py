"""Unit definitions and random roster generation."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from functools import lru_cache

from .grid import Hex

STATS = ("health", "attack", "defense", "range", "movement", "sight")
STAT_RANGES = {
    "health": (2, 8),
    "attack": (1, 5),
    "defense": (1, 5),
    "range": (0, 4),
    "movement": (1, 4),
    "sight": (1, 5),
}
STAT_TOTAL = 15
ROSTER_SIZE = 10

# A stat line in STATS order: (health, attack, defense, range, movement, sight).
StatLine = tuple[int, int, int, int, int, int]


@lru_cache(maxsize=None)
def stat_combinations() -> tuple[StatLine, ...]:
    """Every stat line within STAT_RANGES whose six values sum to STAT_TOTAL."""
    ranges = [range(lo, hi + 1) for lo, hi in (STAT_RANGES[s] for s in STATS)]
    return tuple(c for c in itertools.product(*ranges) if sum(c) == STAT_TOTAL)


def random_roster(rng: random.Random, size: int = ROSTER_SIZE) -> list[StatLine]:
    """Pick `size` stat lines, each uniformly from all valid combinations."""
    combos = stat_combinations()
    return [rng.choice(combos) for _ in range(size)]


@dataclass(eq=False)
class Unit:
    owner: int  # 1 or 2
    kind: int  # 1-based roster number; both sides' copies of a unit share it
    max_health: int
    attack: int
    defense: int
    range: int
    movement: int
    sight: int
    health: int = 0
    pos: Hex | None = None
    moved: bool = False
    fired: bool = False

    def __post_init__(self) -> None:
        if not self.health:
            self.health = self.max_health

    @classmethod
    def from_stats(cls, owner: int, kind: int, stats: StatLine) -> Unit:
        health, attack, defense, rng, movement, sight = stats
        return cls(owner, kind, health, attack, defense, rng, movement, sight)

    @property
    def alive(self) -> bool:
        return self.health > 0
