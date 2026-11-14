"""A simple computer opponent.

For now the computer cheats: it knows where every enemy unit is.  It still
only makes moves the rules allow, so fog of war limits where its units can
go and what they can shoot.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .combat import battle_rounds, expected_damage, kill_chance
from .game import Game, Phase, opponent
from .grid import Hex, column_ys, distance
from .units import Unit

# Setup columns ordered from the front line to the back.
FRONT_TO_BACK = {1: (2, 1, 0), 2: (8, 9, 10)}
UNITS_PER_COLUMN = (4, 3, 3)
# Minimum expected gain before the computer bothers to attack or move.
ATTACK_THRESHOLD = 0.5
MOVE_THRESHOLD = 0.05


@dataclass
class Action:
    kind: str  # "move", "end_movement", "ranged", or "end_turn"
    unit: Unit | None = None
    target: Hex | Unit | None = None  # destination hex for "move", enemy unit for "ranged"


class ComputerPlayer:
    def __init__(self, player: int, rng: random.Random | None = None, trials: int = 150):
        self.player = player
        self.rng = rng or random.Random()
        self.trials = trials  # simulated battles per attack the computer considers
        self._turn = None
        self._holding: set[Unit] = set()  # units that decided to stay put this turn

    def place_units(self, game: Game) -> None:
        """Sturdy units in front, ranged units at the back, random rows."""
        units = sorted(game.units_of(self.player),
                       key=lambda u: (u.defense + u.health - 2 * u.range, self.rng.random()),
                       reverse=True)
        it = iter(units)
        for col, count in zip(FRONT_TO_BACK[self.player], UNITS_PER_COLUMN):
            ys = list(column_ys(col))
            self.rng.shuffle(ys)
            for y in ys[:count]:
                game.place(next(it), (col, y))

    def next_action(self, game: Game) -> Action:
        if game.turn != self._turn:
            self._turn = game.turn
            self._holding = set()
        if game.phase is Phase.MOVEMENT:
            return self._next_move(game)
        return self._next_shot(game)

    def _next_move(self, game: Game) -> Action:
        best = None  # (gain, unit, dest)
        for u in game.units_of(self.player):
            if u.moved or u in self._holding:
                continue
            stay = self._position_score(game, u, u.pos)
            unit_best = None
            for dest in game.legal_moves(u):
                enemy = game.unit_at(dest)
                if enemy is not None:
                    gain = self._attack_score(u, enemy)
                    if gain < ATTACK_THRESHOLD:
                        continue
                else:
                    gain = self._position_score(game, u, dest) - stay
                gain += self.rng.uniform(0, 0.01)
                if unit_best is None or gain > unit_best[0]:
                    unit_best = (gain, u, dest)
            if unit_best is None or unit_best[0] < MOVE_THRESHOLD:
                self._holding.add(u)
            elif best is None or unit_best[0] > best[0]:
                best = unit_best
        if best is None:
            return Action("end_movement")
        return Action("move", best[1], best[2])

    def _next_shot(self, game: Game) -> Action:
        for u in game.units_of(self.player):
            targets = game.ranged_targets(u)
            if targets:
                target = max(targets, key=lambda t: 5 * kill_chance(u.attack, t.defense, t.health)
                             + expected_damage(u.attack, t.defense))
                return Action("ranged", u, target)
        return Action("end_turn")

    @staticmethod
    def _value(u: Unit) -> float:
        return u.health + u.attack + u.defense + u.range

    def _attack_score(self, u: Unit, enemy: Unit) -> float:
        """Expected material swing of attacking, estimated by simulation."""
        kills = deaths = 0
        for _ in range(self.trials):
            _, att_left, def_left = battle_rounds(u.health, u.attack, u.defense,
                                                  enemy.health, enemy.attack, enemy.defense,
                                                  self.rng)
            kills += def_left == 0
            deaths += att_left == 0
        return (kills * self._value(enemy) - deaths * self._value(u)) / self.trials

    def _position_score(self, game: Game, u: Unit, h: Hex) -> float:
        enemies = game.units_of(opponent(self.player))
        if not enemies:
            return 0.0
        dists = [distance(h, e.pos) for e in enemies]
        nearest = min(dists)
        adjacent = sum(d == 1 for d in dists)
        # Enemies that could reach this hex next turn and hurt this unit.
        threats = sum(1 for e, d in zip(enemies, dists)
                      if d <= e.movement and e.attack >= u.defense)
        if u.range:
            in_range = any(1 <= d <= u.range for d in dists)
            return (2.0 * in_range - 0.5 * abs(nearest - u.range)
                    - 2.0 * adjacent - 0.5 * threats)
        return -0.8 * nearest - 1.5 * max(0, adjacent - 1) - 0.3 * threats
