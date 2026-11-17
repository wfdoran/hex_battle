"""Game state and rules: placement, fog of war, movement, battles, turns."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .combat import battle_rounds, roll_damage
from .grid import ALL_HEXES, COLS, Hex, distance, hexes_within, neighbors
from .units import StatLine, Unit, random_roster

SETUP_COLUMNS = {1: (0, 1, 2), 2: (8, 9, 10)}
# The game is a draw after this many consecutive turns with no move or attack.
IDLE_TURNS_FOR_DRAW = 2
# A quiet turn is one in which no unit takes any damage.  After
# QUIET_TURNS_FOR_FATIGUE quiet turns in a row, every unit's defense and
# movement drop by 1 (to no less than MIN_DEFENSE and MIN_MOVEMENT) for the
# rest of the game.  After
# QUIET_TURNS_FOR_RADIATION, the two outermost columns become radioactive, and
# they are destroyed (with any units on them) once RADIATION_DELAY more turns
# have been played.
QUIET_TURNS_FOR_FATIGUE = 6
QUIET_TURNS_FOR_RADIATION = 10
RADIATION_DELAY = 2
MIN_DEFENSE = 1
MIN_MOVEMENT = 1
# An anchored unit, one that stayed put through its previous movement phase
# and the one before, adds this to its attack when it fires.
ANCHOR_BONUS = 1
DRAW = 0


class Phase(Enum):
    PLACEMENT = "placement"
    MOVEMENT = "movement"
    RANGED = "ranged"
    OVER = "over"


class RuleError(Exception):
    """Raised when an action is not allowed by the rules."""


def opponent(player: int) -> int:
    return 3 - player


@dataclass
class BattleResult:
    attacker: Unit
    defender: Unit
    hex: Hex
    rounds: list[tuple[int, int]]  # (damage to defender, damage to attacker)


@dataclass
class MoveResult:
    unit: Unit
    start: Hex
    planned: list[Hex]  # the path the player chose, excluding the start
    path: list[Hex]  # the hexes actually entered (shorter if a hidden enemy stopped it)
    battle: BattleResult | None

    @property
    def stopped_early(self) -> bool:
        return len(self.path) < len(self.planned)


@dataclass
class RangedResult:
    attacker: Unit
    target: Unit
    hex: Hex
    damage: int
    anchored: bool  # whether the attacker fired with the anchor bonus

    @property
    def killed(self) -> bool:
        return not self.target.alive


@dataclass
class RadiationEvent:
    kind: str  # "warning" when columns become radioactive, "destroyed" when they are removed
    columns: tuple[int, ...]
    casualties: list[Unit]


@dataclass
class FatigueEvent:
    tired: list[Unit]  # living units with a stat that dropped (not every stat was at its minimum)


class Game:
    def __init__(self, seed: int | None = None, roster: list[StatLine] | None = None):
        # Always have a seed, so any game's units can be replayed.
        self.seed = seed if seed is not None else random.randrange(1, 1_000_000)
        self.rng = random.Random(self.seed)
        self.roster = list(roster) if roster else random_roster(self.rng)
        # Both sides get identical copies of the same roster.
        self.units = [Unit.from_stats(owner, kind, stats)
                      for owner in (1, 2)
                      for kind, stats in enumerate(self.roster, 1)]
        self.board: dict[Hex, Unit] = {}
        self.phase = Phase.PLACEMENT
        self.current = 1
        self.turn = 0
        self.winner: int | None = None  # 1, 2, or DRAW once the game is over
        self.idle_turns = 0
        self.acted = False  # whether the current player has moved or attacked this turn
        self.damaged = False  # whether any unit took damage this turn
        self.quiet_turns = 0
        # Columns still on the board run from first_col to last_col.
        self.first_col = 0
        self.last_col = COLS - 1
        self.radioactive_cols: tuple[int, ...] = ()
        self.radiation_countdown = 0  # turns left before the radioactive columns go
        self.fatigue = 0  # how many times fatigue has struck
        # Stat values before fatigue, for each stat it lowered: rested[unit]["defense"].
        self.rested: dict[Unit, dict[str, int]] = {}
        # Unlike battle deaths, these aren't all public: a player only learns
        # how many of the enemy's hidden units radiation destroyed.
        self.lost_to_radiation: set[Unit] = set()

    # ----- queries -------------------------------------------------------

    @property
    def over(self) -> bool:
        return self.phase is Phase.OVER

    def on_board(self, h: Hex) -> bool:
        """False for hexes in columns that radiation has destroyed."""
        return self.first_col <= h[0] <= self.last_col

    def units_of(self, player: int) -> list[Unit]:
        """The player's living units."""
        return [u for u in self.units if u.owner == player and u.alive]

    def unit_at(self, h: Hex) -> Unit | None:
        return self.board.get(h)

    def setup_hexes(self, player: int) -> frozenset[Hex]:
        return frozenset(h for h in ALL_HEXES if h[0] in SETUP_COLUMNS[player])

    def visible_hexes(self, player: int) -> set[Hex]:
        """Hexes the player can currently see (the union of their units' sight)."""
        if self.phase is Phase.OVER:
            return {h for h in ALL_HEXES if self.on_board(h)}
        if self.phase is Phase.PLACEMENT:
            return set(self.setup_hexes(player))
        vis: set[Hex] = set()
        for u in self.units_of(player):
            vis |= hexes_within(u.pos, u.sight)
        return {h for h in vis if self.on_board(h)}

    def anchored(self, unit: Unit) -> bool:
        """Whether the unit gets ANCHOR_BONUS on ranged attacks.

        In its own ranged phase, a unit is anchored if it stayed put in this
        turn's movement phase and in its previous one.  At other times this
        tells whether it will be anchored when it next fires, provided it
        doesn't move before then: it stayed put last time and hasn't moved
        since.  Units that can't shoot are never anchored.
        """
        if not unit.alive or unit.range == 0 or self.phase in (Phase.PLACEMENT, Phase.OVER):
            return False
        if unit.owner == self.current and self.phase is Phase.RANGED:
            return unit.stays >= 2
        return unit.stays >= 1 and not unit.relocated

    def ranged_attack_strength(self, unit: Unit) -> int:
        """The attack the unit fires with, counting the anchor bonus."""
        return unit.attack + (ANCHOR_BONUS if self.anchored(unit) else 0)

    def _adjacent_enemies(self, h: Hex, player: int, known: set[Hex] | None = None) -> int:
        """Count enemy units next to h, optionally only those in `known` hexes."""
        count = 0
        for n in neighbors(h):
            occ = self.board.get(n)
            if occ is not None and occ.owner != player and (known is None or n in known):
                count += 1
        return count

    # ----- placement -----------------------------------------------------

    def can_place(self, unit: Unit, h: Hex) -> bool:
        return (self.phase is Phase.PLACEMENT
                and h in self.setup_hexes(unit.owner)
                and self.board.get(h) in (None, unit))

    def place(self, unit: Unit, h: Hex) -> None:
        if not self.can_place(unit, h):
            raise RuleError("cannot place a unit there")
        if unit.pos is not None:
            del self.board[unit.pos]
        unit.pos = h
        self.board[h] = unit

    def unplace(self, unit: Unit) -> None:
        if self.phase is not Phase.PLACEMENT:
            raise RuleError("units can only be taken back during setup")
        if unit.pos is not None:
            del self.board[unit.pos]
            unit.pos = None

    def auto_place(self, player: int) -> None:
        """Place all of the player's units on random hexes of their setup zone."""
        units = self.units_of(player)
        for u in units:
            self.unplace(u)
        hexes = self.rng.sample(sorted(self.setup_hexes(player)), len(units))
        for u, h in zip(units, hexes):
            self.place(u, h)

    def placement_done(self, player: int) -> bool:
        return all(u.pos is not None for u in self.units_of(player))

    def start(self) -> None:
        if self.phase is not Phase.PLACEMENT:
            raise RuleError("the game has already started")
        if not (self.placement_done(1) and self.placement_done(2)):
            raise RuleError("both players must place all of their units")
        self.current = 1
        self.turn = 1
        self._begin_turn()

    # ----- movement ------------------------------------------------------

    def legal_moves(self, unit: Unit) -> dict[Hex, list[Hex]]:
        """Map each hex the unit may move to onto the path it would take.

        Zone of control: a unit may not step from a hex next to an enemy to
        another hex next to an enemy, though it may always attack.  Only what
        the owner can see is used: every hex on the path must be visible, and
        zone of control counts visible enemies.  Enemies hidden in fog can
        still stop the unit; see move().
        """
        if (self.phase is not Phase.MOVEMENT or unit.owner != self.current
                or not unit.alive or unit.moved):
            return {}
        vis = self.visible_hexes(unit.owner)
        start = unit.pos
        paths: dict[Hex, list[Hex]] = {start: []}
        frontier = [start]
        for _ in range(unit.movement):
            next_frontier = []
            for h in frontier:
                in_zoc = self._adjacent_enemies(h, unit.owner, vis) > 0
                for n in neighbors(h):
                    if n in paths or n not in vis:
                        continue
                    occ = self.board.get(n)
                    if occ is None:
                        if in_zoc and self._adjacent_enemies(n, unit.owner, vis) > 0:
                            continue
                        paths[n] = paths[h] + [n]
                        next_frontier.append(n)
                    elif occ.owner != unit.owner:
                        # Moving onto an enemy starts a battle and ends the move.
                        paths[n] = paths[h] + [n]
            frontier = next_frontier
        del paths[start]
        return paths

    def move(self, unit: Unit, dest: Hex) -> MoveResult:
        moves = self.legal_moves(unit)
        if dest not in moves:
            raise RuleError("illegal move")
        planned = moves[dest]
        start = unit.pos
        del self.board[start]
        here = start
        taken: list[Hex] = []
        battle = None
        for step in planned:
            enemy = self.board.get(step)
            if enemy is not None:
                taken.append(step)
                # Battles go on until a unit is destroyed, so there is always damage.
                battle = self._battle(unit, enemy, step)
                self.damaged = True
                break
            # An enemy hidden in the fog may put the step in a zone of control.
            if (self._adjacent_enemies(here, unit.owner) > 0
                    and self._adjacent_enemies(step, unit.owner) > 0):
                break
            here = step
            taken.append(step)
        if battle is None:
            unit.pos = here
            self.board[here] = unit
        unit.moved = True
        unit.relocated = bool(taken)
        self.acted = True
        self._check_over()
        return MoveResult(unit, start, planned, taken, battle)

    def _battle(self, attacker: Unit, defender: Unit, h: Hex) -> BattleResult:
        rounds, attacker.health, defender.health = battle_rounds(
            attacker.health, attacker.attack, attacker.defense,
            defender.health, defender.attack, defender.defense, self.rng)
        if not defender.alive:
            self._remove(defender)
        if attacker.alive:
            attacker.pos = h
            self.board[h] = attacker
        else:
            attacker.pos = None
        return BattleResult(attacker, defender, h, rounds)

    def _remove(self, unit: Unit) -> None:
        if unit.pos is not None and self.board.get(unit.pos) is unit:
            del self.board[unit.pos]
        unit.pos = None

    def end_movement(self) -> None:
        if self.phase is not Phase.MOVEMENT:
            raise RuleError("not in the movement phase")
        for u in self.units_of(self.current):
            u.stays = 0 if u.relocated else u.stays + 1
        self.phase = Phase.RANGED

    # ----- ranged attacks ------------------------------------------------

    def ranged_targets(self, unit: Unit) -> list[Unit]:
        if (self.phase is not Phase.RANGED or unit.owner != self.current
                or not unit.alive or unit.range == 0 or unit.fired):
            return []
        vis = self.visible_hexes(unit.owner)
        return [e for e in self.units_of(opponent(unit.owner))
                if e.pos in vis and distance(unit.pos, e.pos) <= unit.range]

    def ranged_attack(self, unit: Unit, target: Unit) -> RangedResult:
        if target not in self.ranged_targets(unit):
            raise RuleError("illegal ranged attack")
        h = target.pos
        anchored = self.anchored(unit)
        damage = roll_damage(self.ranged_attack_strength(unit), target.defense, self.rng)
        target.health = max(0, target.health - damage)
        if not target.alive:
            self._remove(target)
        unit.fired = True
        self.acted = True
        self.damaged = self.damaged or damage > 0
        self._check_over()
        return RangedResult(unit, target, h, damage, anchored)

    # ----- turns ---------------------------------------------------------

    def end_turn(self) -> list[RadiationEvent | FatigueEvent]:
        """Finish the current player's turn and return any fatigue or radiation events."""
        if self.phase is not Phase.RANGED:
            raise RuleError("end the movement phase first")
        events = self._advance_radiation()
        self._check_over()
        if self.over:
            return events
        self.idle_turns = 0 if self.acted else self.idle_turns + 1
        if self.idle_turns >= IDLE_TURNS_FOR_DRAW:
            self._finish(DRAW)
            return events
        self.current = opponent(self.current)
        self.turn += 1
        self._begin_turn()
        return events

    def _advance_radiation(self) -> list[RadiationEvent | FatigueEvent]:
        if self.radiation_countdown:
            self.radiation_countdown -= 1
            if self.radiation_countdown:
                return []
            return [self._destroy_radioactive_columns()]
        self.quiet_turns = 0 if self.damaged else self.quiet_turns + 1
        if self.quiet_turns == QUIET_TURNS_FOR_FATIGUE:
            return [self._tire()]
        if self.quiet_turns < QUIET_TURNS_FOR_RADIATION:
            return []
        self.radioactive_cols = tuple(sorted({self.first_col, self.last_col}))
        self.radiation_countdown = RADIATION_DELAY
        return [RadiationEvent("warning", self.radioactive_cols, [])]

    def _tire(self) -> FatigueEvent:
        tired = []
        for u in self.units:
            if not u.alive:
                continue
            lowered = False
            for stat, floor in (("defense", MIN_DEFENSE), ("movement", MIN_MOVEMENT)):
                value = getattr(u, stat)
                if value > floor:
                    self.rested.setdefault(u, {}).setdefault(stat, value)
                    setattr(u, stat, value - 1)
                    lowered = True
            if lowered:
                tired.append(u)
        self.fatigue += 1
        return FatigueEvent(tired)

    def _destroy_radioactive_columns(self) -> RadiationEvent:
        cols = self.radioactive_cols
        casualties = [u for u in self.units if u.alive and u.pos[0] in cols]
        for u in casualties:
            u.health = 0
            self._remove(u)
        self.lost_to_radiation.update(casualties)
        self.first_col += 1
        self.last_col -= 1
        self.radioactive_cols = ()
        self.quiet_turns = 0
        return RadiationEvent("destroyed", cols, casualties)

    def _begin_turn(self) -> None:
        self.phase = Phase.MOVEMENT
        self.acted = False
        self.damaged = False
        for u in self.units:
            u.moved = u.relocated = u.fired = False

    def _check_over(self) -> None:
        alive1 = bool(self.units_of(1))
        alive2 = bool(self.units_of(2))
        if not alive1 and not alive2:
            self._finish(DRAW)
        elif not alive1:
            self._finish(2)
        elif not alive2:
            self._finish(1)

    def _finish(self, winner: int) -> None:
        self.phase = Phase.OVER
        self.winner = winner
