"""Computer opponents at three levels.

No level sees through the fog of war.  Each keeps an EnemyTracker: where it
last saw every enemy unit and where that unit could have moved since, and
plays against its best guess of where the hidden units are.  It only makes
moves the rules allow, so fog also limits where its units can go and what
they can shoot.

- easy:   approaches the enemy loosely, judges fights by comparing stats,
          leaves nearly half its units idle each turn, and shoots at random
          targets.
- medium: computes exact battle odds and only attacks when it expects to
          come out ahead; melee units close in, ranged units keep their
          distance.
- hard:   medium, plus it accounts for enemies that can reach a hex next
          turn (and for friends that could strike back), looks ahead to what
          a winning unit faces after a battle, seeks out fights it can win,
          positions ranged units where they can actually see and shoot a
          target, and focuses fire on enemies it can finish off.  It then
          plays its best few moves forward in imagined games, through the
          opponent's reply, and picks the one that does best.

Every level steers clear of radioactive columns.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass

from .combat import (attacker_health_if_won, battle_odds, battle_outcomes, expected_damage,
                     kill_chance)
from .game import Game, Phase, opponent
from .grid import ALL_HEXES, COLS, Hex, column_ys, distance, hexes_within, neighbors
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
HARD_DANGER_CAP = 1.0  # a unit can only be lost once, times its value
HARD_SUPPORT = 0.5  # how much a friendly counterattack offsets the danger
HARD_PIN = 0.15  # bonus for helping surround an enemy, times its value
SEARCH_WIDTH = 5  # candidate moves the hard level plays forward
SEARCH_ROLLOUTS = 8  # games played forward per candidate
SEARCH_HORIZON = 1  # turns played forward after this one (1 = the opponent's reply)


@dataclass(frozen=True)
class Profile:
    attack_threshold: float  # minimum expected gain before attacking
    noise: float  # random jitter added to every score
    idle_chance: float  # chance a unit just stays put this turn


PROFILES = {
    "easy": Profile(attack_threshold=0.0, noise=2.5, idle_chance=0.45),
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
    return unit_value_at(u, u.health)


def unit_value_at(u: Unit, health: int) -> float:
    """What unit_value would be with the given health."""
    return health + u.attack + u.defense + 0.7 * u.range + 0.3 * u.movement


class EnemyTracker:
    """What one side knows about the enemy's units, without seeing through fog.

    For each enemy unit it keeps the set of hexes the unit could be on: the
    hex where it was seen, grown by the unit's movement every enemy turn, less
    every hex this side can see now (it isn't there, or it would be seen).
    Battle and ranged-attack deaths are public.  Radiation deaths in the fog
    are only known as a count, so the units most likely to have been caught
    are written off.
    """

    def __init__(self, game: Game, player: int):
        self.player = player
        self.enemy = opponent(player)
        zone = game.setup_hexes(self.enemy)
        enemies = [e for e in game.units if e.owner == self.enemy]
        self.possible: dict[Unit, set[Hex]] = {e: set(zone) for e in enemies}
        self.last_seen: dict[Unit, Hex] = {}
        self.health = {e: e.max_health for e in enemies}
        self.turn = 0  # the game turn when this was last updated

    def update(self, game: Game) -> None:
        if game.turn != self.turn:
            # Turns alternate, so every other turn since the last update was the enemy's.
            for _ in range((game.turn - self.turn) // 2 if self.turn else game.turn - 1):
                self._spread(game)
            self.turn = game.turn
        for e in list(self.possible):
            if not e.alive and e not in game.lost_to_radiation:
                del self.possible[e]
        vis = game.visible_hexes(self.player)
        mine = {u.pos for u in game.units_of(self.player)}
        seen = {e for e in game.units_of(self.enemy) if e.pos in vis}
        for e in seen:
            # A unit wrongly written off after radiation has turned up again.
            self.possible.setdefault(e, set())
        for e in self.possible:
            if e in seen:
                self.possible[e] = {e.pos}
                self.last_seen[e] = e.pos
                self.health[e] = e.health
            else:
                self.possible[e] = {h for h in self.possible[e]
                                    if h not in vis and h not in mine and game.on_board(h)}
        # Reconcile with the unit count, which both sides can see.
        unseen = sorted((e for e in self.possible if e not in seen),
                        key=lambda e: (len(self.possible[e]), e.kind))
        for e in unseen[:max(0, len(self.possible) - len(game.units_of(self.enemy)))]:
            del self.possible[e]
        for e in self.possible:
            if not self.possible[e]:
                # It moved somewhere this model didn't allow for; it could be anywhere unseen.
                self.possible[e] = {h for h in ALL_HEXES if game.on_board(h)
                                    and h not in vis and h not in mine}

    def _spread(self, game: Game) -> None:
        for e, hexes in self.possible.items():
            grown: set[Hex] = set()
            for h in hexes:
                grown |= hexes_within(h, e.movement)
            self.possible[e] = {h for h in grown if game.on_board(h)}

    def guesses(self) -> list[Unit]:
        """A stand-in for each enemy unit, placed where it most likely is.

        That is where it was last seen if it could still be there, otherwise
        the nearest hex it could be on.  Units never seen are guessed at the
        front of their setup zone.  Stand-ins are spread over different hexes.
        """
        front = (COLS // 2, 6)
        taken: set[Hex] = set()
        stand_ins = []
        for e in sorted(self.possible, key=lambda e: (len(self.possible[e]), e.kind)):
            hexes = self.possible[e] - taken or self.possible[e]
            anchor = self.last_seen.get(e, front)
            h = min(hexes, key=lambda h: (distance(h, anchor), h))
            taken.add(h)
            stand_in = copy.copy(e)
            stand_in.pos, stand_in.health = h, self.health[e]
            stand_ins.append(stand_in)
        return stand_ins


class ComputerPlayer:
    def __init__(self, player: int, level: str = "medium", rng: random.Random | None = None,
                 sees_all: bool = False):
        if level not in PROFILES:
            raise ValueError(f"unknown level {level!r}")
        self.player = player
        # Knows where every enemy is: used in the hard level's imagined games, where
        # the enemies are only guesses anyway, and to measure what fog costs.
        self.sees_all = sees_all
        self.tracker: EnemyTracker | None = None
        self._enemies: list[Unit] = []  # where this side believes the enemy units are
        self._friends: list[Unit] = []
        self.search = level == "hard" and SEARCH_ROLLOUTS > 0
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
        self._friends = game.units_of(self.player)
        if self.sees_all:
            self._enemies = game.units_of(opponent(self.player))
        else:
            if self.tracker is None:
                self.tracker = EnemyTracker(game, self.player)
            self.tracker.update(game)
            self._enemies = self.tracker.guesses()
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
        options = []
        for u in units:
            if u.moved or u in self._holding:
                continue
            unit_best = self._best_move_for(game, u)
            if unit_best is None or unit_best[0] < MOVE_THRESHOLD:
                self._holding.add(u)
            else:
                options.append(unit_best)
                if best is None or unit_best[0] > best[0]:
                    best = unit_best
        if self.search and len(options) > 1:
            options.sort(key=lambda o: o[0], reverse=True)
            return self._search(game, [Action("move", o[1], o[2]) for o in options[:SEARCH_WIDTH]])
        if best is None and not game.acted and self._ahead(game):
            # Sitting out a whole turn while ahead only offers the opponent a draw.
            options = [o for o in (self._best_move_for(game, u) for u in units if not u.moved) if o]
            best = max(options, key=lambda o: o[0], default=None)
        if best is None:
            return Action("end_movement")
        return Action("move", best[1], best[2])

    # ----- look-ahead (hard) -------------------------------------------------

    def _search(self, game: Game, candidates: list[Action]) -> Action:
        """Pick the candidate that does best when the game is played forward.

        Each candidate is tried in copies of the game, with hidden enemies put
        where they were guessed to be.  The rest of this turn is played with
        the normal policy (every unit deciding afresh), then the opponent's
        reply, modeled as a medium player.  The material left decides.
        """
        best, best_score = candidates[0], None
        for action in candidates:
            score = 0.0
            for _ in range(SEARCH_ROLLOUTS):
                rng = random.Random(self.rng.random())
                world = self._imagine(game, rng)
                unit = next(u for u in world.units if u.owner == self.player
                            and u.kind == action.unit.kind)
                world.move(unit, action.target)
                score += self._rollout(world, rng)
            if best_score is None or score > best_score:
                best, best_score = action, score
        return best

    def _imagine(self, game: Game, rng: random.Random) -> Game:
        """A copy of the game with the enemy units where this side believes they are."""
        world = copy.deepcopy(game)
        world.rng = random.Random(rng.random())
        guesses = {e.kind: e for e in self._enemies}
        for e in world.units:
            if e.owner == self.player or not e.alive:
                continue
            del world.board[e.pos]
            e.pos = None
        for e in world.units:
            if e.owner == self.player:
                continue
            guess = guesses.get(e.kind)
            if guess is None:
                e.health = 0
            else:
                e.health, e.pos = guess.health, guess.pos
                world.board[e.pos] = e
        return world

    def _rollout(self, world: Game, rng: random.Random) -> float:
        me = ComputerPlayer(self.player, "hard", random.Random(rng.random()), sees_all=True)
        me.search = False
        them = ComputerPlayer(opponent(self.player), "medium", random.Random(rng.random()),
                              sees_all=True)
        start = world.turn
        while not world.over and world.turn <= start + SEARCH_HORIZON:
            player = me if world.current == self.player else them
            a = player.next_action(world)
            if a.kind == "move":
                world.move(a.unit, a.target)
            elif a.kind == "end_movement":
                world.end_movement()
            elif a.kind == "ranged":
                world.ranged_attack(a.unit, a.target)
            else:
                world.end_turn()
        if world.over:
            return {self.player: 100.0, opponent(self.player): -100.0}.get(world.winner, 0.0)
        return (sum(unit_value(u) for u in world.units_of(self.player))
                - sum(unit_value(u) for u in world.units_of(opponent(self.player))))

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
        theirs = sum(unit_value(u) for u in self._enemies)
        return mine >= theirs

    def _next_shot(self, game: Game) -> Action:
        for u in game.units_of(self.player):
            targets = game.ranged_targets(u)
            if not targets:
                continue
            attack = game.ranged_attack_strength(u)
            if self.level == "easy":
                target = self.rng.choice(targets)
            elif self.level == "medium":
                target = max(targets, key=lambda t: 5 * kill_chance(attack, t.defense, t.health)
                             + expected_damage(attack, t.defense))
            else:
                target = max(targets, key=lambda t: self._shot_value(attack, t))
            return Action("ranged", u, target)
        return Action("end_turn")

    # ----- scoring -----------------------------------------------------------

    @staticmethod
    def _shot_value(attack: int, t: Unit) -> float:
        return (kill_chance(attack, t.defense, t.health) * unit_value(t)
                + expected_damage(attack, t.defense) * (1 + 1 / t.health))

    def _attack_gain(self, game: Game, u: Unit, enemy: Unit, dest: Hex) -> float:
        if self.level == "easy":
            return (u.attack - enemy.defense) + 0.3 * (u.health - enemy.health)
        if self.level == "hard":
            return self._hard_attack_gain(game, u, enemy, dest)
        win, lose, both = battle_odds(u.health, u.attack, u.defense,
                                      enemy.health, enemy.attack, enemy.defense)
        gain = (win + both) * unit_value(enemy) - (lose + both) * unit_value(u)
        if dest[0] in game.radioactive_cols:
            gain -= win * RADIATION_PENALTY
        return gain

    def _position_score(self, game: Game, u: Unit, h: Hex) -> float:
        enemies = self._enemies
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

    def _hard_attack_gain(self, game: Game, u: Unit, enemy: Unit, dest: Hex) -> float:
        """Expected gain from a battle, looking ahead to the enemy's reply.

        A unit that wins is left on the enemy's hex with whatever health it
        has left, where other enemies may attack it next turn.
        """
        others = [e for e in self._enemies if e.pos != dest]
        gain = 0.0
        for (ah, dh), p in battle_outcomes(u.health, u.attack, u.defense,
                                           enemy.health, enemy.attack, enemy.defense).items():
            if ah == 0:
                gain -= p * unit_value(u)
            if dh == 0:
                gain += p * unit_value(enemy)
                if ah > 0:
                    survivor = copy.copy(u)
                    survivor.health = ah
                    risk = RADIATION_PENALTY if dest[0] in game.radioactive_cols else 0.0
                    gain -= p * (risk + HARD_DANGER * self._danger(survivor, dest, others))
            else:
                # The enemy survives, weakened; it is worth less to them now.
                gain += p * (unit_value(enemy) - unit_value_at(enemy, dh))
        return gain

    def _danger(self, u: Unit, h: Hex, enemies: list[Unit]) -> float:
        """Expected loss if the enemies that can reach h next turn attack it.

        An enemy that wins is left on h, weakened, where other friendly units
        may be able to finish it off, so support nearby lowers the danger.
        """
        friends = [f for f in self._friends if f is not u and distance(f.pos, h) <= f.movement]
        danger = 0.0
        for e in enemies:
            if distance(h, e.pos) <= e.movement:
                win, lose, both = battle_odds(e.health, e.attack, e.defense,
                                              u.health, u.attack, u.defense)
                loss = (win + both) * unit_value(u) - (lose + both) * unit_value(e)
                if friends and win:
                    left = attacker_health_if_won(e.health, e.attack, e.defense,
                                                  u.health, u.attack, u.defense)
                    loss -= win * HARD_SUPPORT * max(
                        self._counter_gain(f, e, left) for f in friends)
                danger += max(0.0, loss)
        return min(danger, HARD_DANGER_CAP * unit_value(u))

    @staticmethod
    def _counter_gain(f: Unit, e: Unit, health: int) -> float:
        win, lose, both = battle_odds(f.health, f.attack, f.defense, health, e.attack, e.defense)
        return max(0.0, (win + both) * unit_value_at(e, health) - (lose + both) * unit_value(f))

    def _hard_position_score(self, game: Game, u: Unit, h: Hex,
                             enemies: list[Unit], dists: list[int]) -> float:
        score = -HARD_DANGER * self._danger(u, h, enemies)
        if u.range:
            # Best shot available from here, if this side could see the target.
            # Staying put keeps an anchored unit's bonus.
            attack = game.ranged_attack_strength(u) if h == u.pos else u.attack
            sight = self._visible | hexes_within(h, u.sight)
            shots = [self._shot_value(attack, e) for e, d in zip(enemies, dists)
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
        # Standing next to an enemy that another friendly unit already touches
        # narrows where zone of control lets it retreat to.
        friends = {f.pos for f in game.units_of(self.player) if f is not u}
        for e, d in zip(enemies, dists):
            if d == 1 and any(n in friends for n in neighbors(e.pos)):
                score += HARD_PIN * unit_value(e)
        return score
