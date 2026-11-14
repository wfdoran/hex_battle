"""Computer opponents at three levels.

For now every level cheats: it knows where every enemy unit is.  It still
only makes moves the rules allow, so fog of war limits where its units can
go and what they can shoot.

- easy:   approaches the enemy loosely, judges fights by comparing stats,
          leaves some units idle, and shoots at random targets.
- medium: computes exact battle odds and only attacks when it expects to
          come out ahead; melee units close in, ranged units keep their
          distance.
- hard:   medium, plus it accounts for enemies that can reach a hex next
          turn, seeks out fights it can win, pins enemies by surrounding
          them, positions ranged units where they can actually see and shoot
          a target, and focuses fire on enemies it can finish off.

Every level steers clear of radioactive columns.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .combat import battle_odds, expected_damage, kill_chance
from .game import Game, Phase, opponent
from .grid import Hex, column_ys, distance, hexes_within, neighbors
from .units import Unit

LEVELS = ("easy", "medium", "hard")

# Setup columns ordered from the front line to the back.
FRONT_TO_BACK = {1: (2, 1, 0), 2: (8, 9, 10)}
UNITS_PER_COLUMN = (4, 3, 3)
MOVE_THRESHOLD = 0.05  # minimum improvement before a unit bothers to move
RADIATION_PENALTY = 20.0
# Weights for the hard level's position score.
HARD_DANGER = 0.6  # expected loss from enemies that can reach the hex next turn
HARD_APPROACH = 0.7  # pull toward enemies, per hex of distance
HARD_APPETITE = 3.0  # extra pull toward enemies the unit is likely to beat
HARD_PIN = 0.15  # bonus for helping surround (pin) an enemy, times its value


@dataclass(frozen=True)
class Profile:
    attack_threshold: float  # minimum expected gain before attacking
    noise: float  # random jitter added to every score
    idle_chance: float  # chance a unit just stays put this turn


PROFILES = {
    "easy": Profile(attack_threshold=0.0, noise=1.5, idle_chance=0.3),
    "medium": Profile(attack_threshold=0.5, noise=0.01, idle_chance=0.0),
    "hard": Profile(attack_threshold=0.0, noise=0.0, idle_chance=0.0),
}


@dataclass
class Action:
    kind: str  # "move", "end_movement", "ranged", or "end_turn"
    unit: Unit | None = None
    target: Hex | Unit | None = None  # destination hex for "move", enemy unit for "ranged"


def unit_value(u: Unit) -> float:
    """Rough worth of a unit as it stands, for weighing trades."""
    return u.health + u.attack + u.defense + 0.7 * u.range + 0.3 * u.movement


class ComputerPlayer:
    def __init__(self, player: int, level: str = "medium", rng: random.Random | None = None):
        if level not in PROFILES:
            raise ValueError(f"unknown level {level!r}")
        self.player = player
        self.level = level
        self.profile = PROFILES[level]
        self.rng = rng or random.Random()
        self._turn = None
        self._holding: set[Unit] = set()  # units that decided to stay put this turn
        self._visible: set[Hex] = set()  # hexes this side sees, refreshed every decision

    # ----- setup -----------------------------------------------------------

    def place_units(self, game: Game) -> None:
        if self.level == "easy":
            game.auto_place(self.player)
            return
        # Sturdy units in front, ranged units at the back, random rows.
        units = sorted(game.units_of(self.player),
                       key=lambda u: (u.defense + u.health - 2 * u.range, self.rng.random()),
                       reverse=True)
        it = iter(units)
        for col, count in zip(FRONT_TO_BACK[self.player], UNITS_PER_COLUMN):
            ys = list(column_ys(col))
            self.rng.shuffle(ys)
            for y in ys[:count]:
                game.place(next(it), (col, y))

    # ----- turns -----------------------------------------------------------

    def next_action(self, game: Game) -> Action:
        if game.turn != self._turn:
            self._turn = game.turn
            self._holding = {u for u in game.units_of(self.player)
                             if self.rng.random() < self.profile.idle_chance
                             and u.pos[0] not in game.radioactive_cols}
        if game.phase is Phase.MOVEMENT:
            return self._next_move(game)
        return self._next_shot(game)

    def _next_move(self, game: Game) -> Action:
        best = None  # (gain, unit, dest)
        self._visible = game.visible_hexes(self.player)
        units = game.units_of(self.player)
        for u in units:
            if u.moved or u in self._holding:
                continue
            unit_best = self._best_move_for(game, u)
            if unit_best is None or unit_best[0] < MOVE_THRESHOLD:
                self._holding.add(u)
            elif best is None or unit_best[0] > best[0]:
                best = unit_best
        if best is None and not game.acted and self._ahead(game):
            # Sitting out a whole turn while ahead only offers the opponent a draw.
            options = [o for o in (self._best_move_for(game, u) for u in units if not u.moved) if o]
            best = max(options, key=lambda o: o[0], default=None)
        if best is None:
            return Action("end_movement")
        return Action("move", best[1], best[2])

    def _best_move_for(self, game: Game, u: Unit) -> tuple[float, Unit, Hex] | None:
        stay = self._position_score(game, u, u.pos)
        unit_best = None
        for dest in game.legal_moves(u):
            enemy = game.unit_at(dest)
            if enemy is not None:
                gain = self._attack_gain(game, u, enemy, dest)
                if gain < self.profile.attack_threshold:
                    continue
            else:
                gain = self._position_score(game, u, dest) - stay
            gain += self.rng.uniform(0, self.profile.noise)
            if unit_best is None or gain > unit_best[0]:
                unit_best = (gain, u, dest)
        return unit_best

    def _ahead(self, game: Game) -> bool:
        mine = sum(unit_value(u) for u in game.units_of(self.player))
        theirs = sum(unit_value(u) for u in game.units_of(opponent(self.player)))
        return mine >= theirs

    def _next_shot(self, game: Game) -> Action:
        for u in game.units_of(self.player):
            targets = game.ranged_targets(u)
            if not targets:
                continue
            if self.level == "easy":
                target = self.rng.choice(targets)
            elif self.level == "medium":
                target = max(targets, key=lambda t: 5 * kill_chance(u.attack, t.defense, t.health)
                             + expected_damage(u.attack, t.defense))
            else:
                target = max(targets, key=lambda t: self._shot_value(u, t))
            return Action("ranged", u, target)
        return Action("end_turn")

    # ----- scoring -----------------------------------------------------------

    @staticmethod
    def _shot_value(u: Unit, t: Unit) -> float:
        return (kill_chance(u.attack, t.defense, t.health) * unit_value(t)
                + expected_damage(u.attack, t.defense) * (1 + 1 / t.health))

    def _attack_gain(self, game: Game, u: Unit, enemy: Unit, dest: Hex) -> float:
        if self.level == "easy":
            return (u.attack - enemy.defense) + 0.3 * (u.health - enemy.health)
        win, lose, both = battle_odds(u.health, u.attack, u.defense,
                                      enemy.health, enemy.attack, enemy.defense)
        gain = (win + both) * unit_value(enemy) - (lose + both) * unit_value(u)
        if dest[0] in game.radioactive_cols:
            gain -= win * RADIATION_PENALTY
        return gain

    def _position_score(self, game: Game, u: Unit, h: Hex) -> float:
        enemies = game.units_of(opponent(self.player))
        if not enemies:
            return 0.0
        radiation = -RADIATION_PENALTY if h[0] in game.radioactive_cols else 0.0
        dists = [distance(h, e.pos) for e in enemies]
        nearest = min(dists)
        if self.level == "easy":
            return radiation - nearest
        adjacent = sum(d == 1 for d in dists)
        if self.level == "medium":
            threats = sum(1 for e, d in zip(enemies, dists)
                          if d <= e.movement and e.attack >= u.defense)
            if u.range:
                in_range = any(1 <= d <= u.range for d in dists)
                return (radiation + 2.0 * in_range - 0.5 * abs(nearest - u.range)
                        - 2.0 * adjacent - 0.5 * threats)
            return radiation - 0.8 * nearest - 1.5 * max(0, adjacent - 1) - 0.3 * threats
        return radiation + self._hard_position_score(game, u, h, enemies, dists)

    def _hard_position_score(self, game: Game, u: Unit, h: Hex,
                             enemies: list[Unit], dists: list[int]) -> float:
        # Expected loss if enemies that can reach this hex next turn attack it.
        danger = 0.0
        for e, d in zip(enemies, dists):
            if d <= e.movement:
                win, lose, both = battle_odds(e.health, e.attack, e.defense,
                                              u.health, u.attack, u.defense)
                danger += max(0.0, (win + both) * unit_value(u) - (lose + both) * unit_value(e))
        score = -HARD_DANGER * danger
        if u.range:
            # Best shot available from here, if this side could see the target.
            sight = self._visible | hexes_within(h, u.sight)
            shots = [self._shot_value(u, e) for e, d in zip(enemies, dists)
                     if 1 <= d <= u.range and e.pos in sight]
            score += max(shots, default=0.0)
            score -= 0.4 * max(0, min(dists) - u.range)
        else:
            # Head for the enemy this unit is best placed to beat.
            def appeal(e: Unit, d: int) -> float:
                win, lose, both = battle_odds(u.health, u.attack, u.defense,
                                              e.health, e.attack, e.defense)
                return HARD_APPROACH * d - HARD_APPETITE * (win - lose)
            score -= min(appeal(e, d) for e, d in zip(enemies, dists))
        # Standing next to an enemy that another friendly unit already touches pins it.
        friends = {f.pos for f in game.units_of(self.player) if f is not u}
        for e, d in zip(enemies, dists):
            if d == 1 and any(n in friends for n in neighbors(e.pos)):
                score += HARD_PIN * unit_value(e)
        return score
