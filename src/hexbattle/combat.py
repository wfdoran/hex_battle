"""Damage table and battle resolution."""

from __future__ import annotations

import random
from functools import lru_cache

# attack - defense -> percent chance of 0, 1, 2, ... damage in a single attack.
DAMAGE_TABLE: dict[int, tuple[int, ...]] = {
    4: (0, 0, 34, 33, 33),
    3: (0, 34, 33, 33),
    2: (34, 33, 33),
    1: (50, 50),
    0: (67, 33),
    -1: (75, 25),
    -2: (80, 20),
    -3: (84, 16),
    -4: (86, 14),
}


def damage_odds(attack: int, defense: int) -> tuple[int, ...]:
    diff = max(-4, min(4, attack - defense))
    return DAMAGE_TABLE[diff]


def roll_damage(attack: int, defense: int, rng: random.Random) -> int:
    odds = damage_odds(attack, defense)
    return rng.choices(range(len(odds)), weights=odds)[0]


def expected_damage(attack: int, defense: int) -> float:
    return sum(dmg * pct for dmg, pct in enumerate(damage_odds(attack, defense))) / 100


def kill_chance(attack: int, defense: int, health: int) -> float:
    """Probability that a single attack does at least `health` damage."""
    return sum(damage_odds(attack, defense)[health:]) / 100


def battle_rounds(att_health: int, att_attack: int, att_defense: int,
                  def_health: int, def_attack: int, def_defense: int,
                  rng: random.Random) -> tuple[list[tuple[int, int]], int, int]:
    """Fight until one or both sides reach zero health.

    Each round both units attack at the same time.  Returns the list of
    rounds as (damage to defender, damage to attacker) and the final health
    of the attacker and defender.
    """
    rounds = []
    while att_health > 0 and def_health > 0:
        to_def = roll_damage(att_attack, def_defense, rng)
        to_att = roll_damage(def_attack, att_defense, rng)
        def_health = max(0, def_health - to_def)
        att_health = max(0, att_health - to_att)
        rounds.append((to_def, to_att))
    return rounds, att_health, def_health


@lru_cache(maxsize=None)
def battle_odds(att_health: int, att_attack: int, att_defense: int,
                def_health: int, def_attack: int, def_defense: int) -> tuple[float, float, float]:
    """Exact probabilities that a battle ends with (attacker wins, defender wins, both destroyed)."""
    to_def = damage_odds(att_attack, def_defense)
    to_att = damage_odds(def_attack, att_defense)
    # Rounds where nobody takes damage change nothing, so condition them away.
    p_nothing = to_def[0] * to_att[0] / 10000

    @lru_cache(maxsize=None)
    def outcome(ah: int, dh: int) -> tuple[float, float, float]:
        if ah <= 0 and dh <= 0:
            return (0.0, 0.0, 1.0)
        if dh <= 0:
            return (1.0, 0.0, 0.0)
        if ah <= 0:
            return (0.0, 1.0, 0.0)
        win = lose = both = 0.0
        for dealt, p_dealt in enumerate(to_def):
            for taken, p_taken in enumerate(to_att):
                if dealt == taken == 0:
                    continue
                p = p_dealt * p_taken / 10000
                w, l, b = outcome(ah - taken, dh - dealt)
                win += p * w
                lose += p * l
                both += p * b
        scale = 1 - p_nothing
        return (win / scale, lose / scale, both / scale)

    return outcome(att_health, def_health)


@lru_cache(maxsize=None)
def battle_outcomes(att_health: int, att_attack: int, att_defense: int,
                    def_health: int, def_attack: int, def_defense: int) -> dict[tuple[int, int], float]:
    """Exact probability of each final (attacker health, defender health) of a battle."""
    to_def = damage_odds(att_attack, def_defense)
    to_att = damage_odds(def_attack, att_defense)
    p_nothing = to_def[0] * to_att[0] / 10000

    @lru_cache(maxsize=None)
    def outcome(ah: int, dh: int) -> dict[tuple[int, int], float]:
        if ah <= 0 or dh <= 0:
            return {(max(0, ah), max(0, dh)): 1.0}
        dist: dict[tuple[int, int], float] = {}
        for dealt, p_dealt in enumerate(to_def):
            for taken, p_taken in enumerate(to_att):
                if dealt == taken == 0:
                    continue
                p = p_dealt * p_taken / 10000 / (1 - p_nothing)
                for end, q in outcome(ah - taken, dh - dealt).items():
                    dist[end] = dist.get(end, 0.0) + p * q
        return dist

    return outcome(att_health, def_health)


@lru_cache(maxsize=None)
def attacker_health_if_won(att_health: int, att_attack: int, att_defense: int,
                           def_health: int, def_attack: int, def_defense: int) -> int:
    """The attacker's expected health left after a battle it wins, rounded, at least 1."""
    outcomes = battle_outcomes(att_health, att_attack, att_defense,
                               def_health, def_attack, def_defense)
    p_win = sum(p for (ah, dh), p in outcomes.items() if ah > 0 and dh == 0)
    if p_win == 0:
        return att_health
    mean = sum(ah * p for (ah, dh), p in outcomes.items() if ah > 0 and dh == 0) / p_win
    return max(1, round(mean))
