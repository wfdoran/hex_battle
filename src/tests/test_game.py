import random
import unittest
from unittest import mock

from hexbattle import ai
from hexbattle.ai import ComputerPlayer, EnemyTracker
from hexbattle.game import DRAW, QUIET_TURNS_FOR_RADIATION, Game, Phase, RuleError
from hexbattle.grid import ALL_HEXES, distance, hexes_within, neighbors


def make_game(p1, p2, seed=0):
    """Start a game, then put units exactly where a test wants them.

    p1 and p2 are lists of (hex, stats) with stats in the order
    (health, attack, defense, range, movement, sight).  Units not listed are
    removed from play.
    """
    g = Game(seed=seed)
    g.auto_place(1)
    g.auto_place(2)
    g.start()
    g.board.clear()
    placed = {}
    for player, specs in ((1, p1), (2, p2)):
        units = [u for u in g.units if u.owner == player]
        for u in units:
            u.health = 0
            u.pos = None
        for u, (h, stats) in zip(units, specs):
            u.max_health, u.attack, u.defense, u.range, u.movement, u.sight = stats
            u.health = u.max_health
            u.pos = h
            g.board[h] = u
            placed[h] = u
    return g, placed


class PlacementTest(unittest.TestCase):
    def test_setup_zone(self):
        g = Game(seed=1)
        u = g.units_of(1)[0]
        self.assertTrue(g.can_place(u, (2, 4)))
        self.assertFalse(g.can_place(u, (3, 5)))  # middle columns
        self.assertFalse(g.can_place(u, (9, 5)))  # opponent's zone
        g.place(u, (2, 4))
        self.assertFalse(g.can_place(g.units_of(1)[1], (2, 4)))  # occupied

    def test_both_sides_share_roster(self):
        g = Game(seed=2)
        stats = lambda u: (u.max_health, u.attack, u.defense, u.range, u.movement, u.sight)
        self.assertEqual([stats(u) for u in g.units_of(1)], [stats(u) for u in g.units_of(2)])

    def test_start_requires_all_placed(self):
        g = Game(seed=1)
        g.auto_place(1)
        with self.assertRaises(RuleError):
            g.start()
        g.auto_place(2)
        g.start()
        self.assertIs(g.phase, Phase.MOVEMENT)
        self.assertEqual(g.current, 1)

    def test_visibility_during_placement(self):
        g = Game(seed=1)
        self.assertEqual(g.visible_hexes(1), set(g.setup_hexes(1)))


class MovementTest(unittest.TestCase):
    FAR = ((10, 10), (5, 1, 1, 0, 1, 1))

    def test_cannot_enter_fog(self):
        g, units = make_game([((4, 6), (5, 1, 1, 0, 3, 1))], [self.FAR])
        moves = g.legal_moves(units[(4, 6)])
        self.assertEqual(set(moves), set(neighbors((4, 6))))

    def test_full_reach_when_visible(self):
        g, units = make_game([((4, 6), (5, 1, 1, 0, 2, 5))], [self.FAR])
        moves = g.legal_moves(units[(4, 6)])
        self.assertEqual(set(moves), hexes_within((4, 6), 2) - {(4, 6)})

    def test_friendly_units_block(self):
        g, units = make_game([((4, 2), (5, 1, 1, 0, 2, 5)), ((4, 4), (5, 1, 1, 0, 1, 1))],
                             [self.FAR])
        moves = g.legal_moves(units[(4, 2)])
        self.assertNotIn((4, 4), moves)
        for path in moves.values():
            self.assertNotIn((4, 4), path)

    def test_enemy_ends_move(self):
        g, units = make_game([((4, 6), (5, 1, 1, 0, 3, 5))], [((5, 7), (5, 1, 1, 0, 1, 1))])
        moves = g.legal_moves(units[(4, 6)])
        self.assertEqual(moves[(5, 7)], [(5, 7)])
        for dest, path in moves.items():
            self.assertNotIn((5, 7), path[:-1])

    def test_zone_of_control_at_start(self):
        # Next to an enemy: the unit may attack or step away, but not slide
        # to (4, 8) or (5, 5), which are also next to the enemy.
        g, units = make_game([((4, 6), (5, 1, 1, 0, 1, 5))], [((5, 7), (5, 1, 1, 0, 1, 1))])
        self.assertEqual(set(g.legal_moves(units[(4, 6)])), {(5, 7), (4, 4), (3, 5), (3, 7)})

    def test_retreat(self):
        g, units = make_game([((4, 6), (5, 1, 1, 0, 3, 5))], [((5, 7), (5, 1, 1, 0, 1, 1))])
        unit = units[(4, 6)]
        self.assertIn((2, 2), g.legal_moves(unit))
        result = g.move(unit, (2, 2))
        self.assertFalse(result.stopped_early)
        self.assertEqual(unit.pos, (2, 2))

    def test_zone_of_control_along_path(self):
        g, units = make_game([((2, 6), (5, 1, 1, 0, 4, 5))],
                             [((5, 5), (5, 1, 1, 0, 1, 1)), ((5, 9), (5, 1, 1, 0, 1, 1))])
        vis = g.visible_hexes(1)
        moves = g.legal_moves(units[(2, 6)])
        self.assertIn((4, 8), moves)  # approaching an enemy is allowed
        self.assertIn((5, 5), moves)  # and so is attacking one
        for dest, path in moves.items():
            steps = [(2, 6)] + path
            for a, b in zip(steps, steps[1:]):
                if g.unit_at(b) is None:
                    self.assertFalse(g._adjacent_enemies(a, 1, vis) and g._adjacent_enemies(b, 1, vis),
                                     (dest, path))

    def test_hidden_enemy_stops_move(self):
        mover = ((2, 6), (5, 1, 1, 0, 2, 1))
        spotter = ((2, 8), (5, 1, 1, 0, 1, 1))  # lets the mover see (3, 9)
        hidden = ((4, 8), (5, 1, 1, 0, 1, 1))  # next to (3, 7) and (3, 9) but in fog
        g, units = make_game([mover, spotter], [hidden])
        unit = units[(2, 6)]
        self.assertNotIn((4, 8), g.visible_hexes(1))
        self.assertEqual(g.legal_moves(unit)[(3, 9)], [(3, 7), (3, 9)])
        result = g.move(unit, (3, 9))
        self.assertTrue(result.stopped_early)
        self.assertEqual(unit.pos, (3, 7))
        self.assertTrue(unit.moved)

    def test_unit_moves_once(self):
        g, units = make_game([((4, 6), (5, 1, 1, 0, 2, 5))], [self.FAR])
        unit = units[(4, 6)]
        g.move(unit, (4, 8))
        self.assertEqual(g.legal_moves(unit), {})
        with self.assertRaises(RuleError):
            g.move(unit, (4, 6))


class BattleTest(unittest.TestCase):
    def test_board_consistent_after_battles(self):
        for seed in range(100):
            g, units = make_game(
                [((4, 6), (3, 3, 2, 0, 2, 5)), ((0, 2), (5, 1, 1, 0, 1, 1))],
                [((5, 7), (3, 3, 2, 0, 1, 1)), ((10, 10), (5, 1, 1, 0, 1, 1))], seed=seed)
            att, dfn = units[(4, 6)], units[(5, 7)]
            result = g.move(att, (5, 7))
            self.assertIsNotNone(result.battle)
            self.assertTrue(not att.alive or not dfn.alive)
            survivor = att if att.alive else dfn if dfn.alive else None
            self.assertIs(g.unit_at((5, 7)), survivor)
            self.assertIsNone(g.unit_at((4, 6)))
            for u in g.units:
                if u.alive:
                    self.assertIs(g.board[u.pos], u)
                else:
                    self.assertIsNone(u.pos)

    def test_last_units_can_draw_or_win(self):
        outcomes = set()
        for seed in range(200):
            g, units = make_game([((4, 6), (1, 5, 1, 0, 1, 5))],
                                 [((5, 7), (1, 5, 1, 0, 1, 1))], seed=seed)
            g.move(units[(4, 6)], (5, 7))
            self.assertTrue(g.over)
            outcomes.add(g.winner)
        self.assertEqual(outcomes, {1, 2, DRAW})


class RangedTest(unittest.TestCase):
    def test_target_must_be_visible(self):
        archer = ((2, 6), (5, 1, 1, 4, 1, 1))
        enemy = ((5, 7), (5, 1, 1, 0, 1, 1))
        g, units = make_game([archer], [enemy])
        g.end_movement()
        self.assertEqual(g.ranged_targets(units[(2, 6)]), [])

        g, units = make_game([archer, ((4, 6), (5, 1, 1, 0, 1, 1))], [enemy])
        g.end_movement()
        self.assertEqual(g.ranged_targets(units[(2, 6)]), [units[(5, 7)]])

    def test_ranged_attack_no_counter(self):
        g, units = make_game([((2, 6), (5, 5, 1, 3, 1, 4))], [((4, 6), (8, 5, 1, 0, 1, 1))])
        g.end_movement()
        archer, target = units[(2, 6)], units[(4, 6)]
        result = g.ranged_attack(archer, target)
        self.assertEqual(archer.health, 5)
        self.assertEqual(target.health, 8 - result.damage)
        self.assertEqual(g.ranged_targets(archer), [])  # only one shot per turn

    def test_range_zero_cannot_fire(self):
        g, units = make_game([((4, 6), (5, 5, 1, 0, 1, 4))], [((5, 7), (5, 1, 1, 0, 1, 1))])
        g.end_movement()
        self.assertEqual(g.ranged_targets(units[(4, 6)]), [])


class TurnTest(unittest.TestCase):
    def test_idle_turns_draw(self):
        g, _ = make_game([((0, 2), (5, 1, 1, 0, 1, 1))], [((10, 10), (5, 1, 1, 0, 1, 1))])
        g.end_movement()
        g.end_turn()
        self.assertFalse(g.over)
        self.assertEqual(g.current, 2)
        g.end_movement()
        g.end_turn()
        self.assertTrue(g.over)
        self.assertEqual(g.winner, DRAW)

    def test_action_resets_idle_count(self):
        g, units = make_game([((0, 2), (5, 1, 1, 0, 1, 1))], [((10, 10), (5, 1, 1, 0, 1, 1))])
        g.end_movement()
        g.end_turn()
        g.move(units[(10, 10)], (10, 8))
        g.end_movement()
        g.end_turn()
        self.assertFalse(g.over)


class ComputerTest(unittest.TestCase):
    def play(self, seed, level1, level2):
        g = Game(seed=seed)
        players = {1: ComputerPlayer(1, level1, random.Random(seed * 10 + 1)),
                   2: ComputerPlayer(2, level2, random.Random(seed * 10 + 2))}
        for p in (1, 2):
            players[p].place_units(g)
        g.start()
        for _ in range(20000):
            if g.over:
                break
            action = players[g.current].next_action(g)
            if action.kind == "move":
                g.move(action.unit, action.target)
            elif action.kind == "end_movement":
                g.end_movement()
            elif action.kind == "ranged":
                g.ranged_attack(action.unit, action.target)
            else:
                g.end_turn()
        return g

    @mock.patch.object(ai, "SEARCH_ROLLOUTS", 2)  # keeps the hard games quick
    def test_every_level_plays_legal_games(self):
        # Any illegal action would raise RuleError.
        for seed, (l1, l2) in enumerate([("easy", "medium"), ("medium", "hard"),
                                         ("hard", "easy"), ("easy", "easy"),
                                         ("medium", "medium"), ("hard", "hard")]):
            self.assertTrue(self.play(seed, l1, l2).over, (l1, l2))

    def test_unknown_level(self):
        with self.assertRaises(ValueError):
            ComputerPlayer(1, "impossible")

    def test_hidden_units_do_not_change_decisions(self):
        # The same game except where one Blue unit hides in the fog.
        for level in ai.LEVELS:
            actions = set()
            for hidden in ((0, 2), (0, 10), (1, 5)):
                g, units = make_game([((4, 6), (5, 3, 2, 1, 2, 2)), (hidden, (5, 3, 2, 1, 2, 2))],
                                     [((8, 6), (5, 3, 2, 2, 2, 2)), ((9, 9), (5, 2, 3, 0, 2, 2))])
                g.current = 2
                self.assertNotIn(hidden, g.visible_hexes(2))
                a = ComputerPlayer(2, level, random.Random(5)).next_action(g)
                actions.add((a.kind, a.unit.kind if a.unit else None, a.target))
            self.assertEqual(len(actions), 1, (level, actions))


class EnemyTrackerTest(unittest.TestCase):
    def test_unseen_units_start_in_their_setup_zone(self):
        g, units = make_game([((1, 5), (5, 1, 1, 0, 1, 1))], [((9, 5), (5, 1, 1, 0, 1, 1))])
        t = EnemyTracker(g, 2)
        g.current, g.turn = 2, 2  # Blue has had one turn to move
        t.update(g)
        blue = units[(1, 5)]
        self.assertIn((1, 5), t.possible[blue])
        self.assertTrue(all(h[0] <= 3 for h in t.possible[blue]))
        self.assertFalse(t.possible[blue] & g.visible_hexes(2))

    def test_seen_then_hidden(self):
        g, units = make_game([((6, 6), (5, 1, 1, 0, 2, 1))], [((8, 6), (5, 1, 1, 0, 1, 2))])
        blue = units[(6, 6)]
        g.current, g.turn = 2, 2
        t = EnemyTracker(g, 2)
        t.update(g)
        self.assertEqual(t.possible[blue], {(6, 6)})
        self.assertEqual([e.pos for e in t.guesses()], [(6, 6)])
        # Blue slips away into the fog during its turn.
        del g.board[(6, 6)]
        blue.pos = (4, 6)
        g.board[(4, 6)] = blue
        g.turn = 4
        t.update(g)
        self.assertIn((4, 6), t.possible[blue])
        self.assertFalse(t.possible[blue] & g.visible_hexes(2))
        self.assertTrue(all(distance(h, (6, 6)) <= 2 for h in t.possible[blue]))
        guess = t.guesses()[0]
        self.assertNotIn(guess.pos, g.visible_hexes(2))
        self.assertEqual(distance(guess.pos, (6, 6)), 1)  # the nearest hex it could be on

    def test_battle_deaths_are_known(self):
        g, units = make_game([((6, 6), (5, 1, 1, 0, 2, 1)), ((0, 2), (5, 1, 1, 0, 1, 1))],
                             [((8, 6), (5, 1, 1, 0, 1, 2))])
        t = EnemyTracker(g, 2)
        blue = units[(0, 2)]
        blue.health = 0
        g._remove(blue)
        t.update(g)
        self.assertNotIn(blue, t.possible)


class RadiationTest(unittest.TestCase):
    """Blue and Red each walk one unit back and forth in mid-board (so the
    game is never idle) while other units sit on the edge columns."""

    STILL = (5, 1, 1, 0, 1, 1)

    def setUp(self):
        self.g, units = make_game(
            [((4, 6), (5, 1, 1, 3, 1, 4)), ((0, 4), self.STILL)],
            [((6, 6), (8, 1, 5, 0, 1, 1)), ((10, 6), self.STILL)])
        self.walkers = {1: units[(4, 6)], 2: units[(6, 6)]}
        self.doomed = {units[(0, 4)], units[(10, 6)]}

    def walk(self):
        """Play a turn with no combat: the current walker steps down or back up."""
        g = self.g
        u = self.walkers[g.current]
        g.move(u, (u.pos[0], u.pos[1] + (2 if u.pos[1] == 6 else -2)))
        g.end_movement()
        return g.end_turn()

    def test_columns_become_radioactive_then_vanish(self):
        g = self.g
        for _ in range(QUIET_TURNS_FOR_RADIATION - 1):
            self.assertEqual(self.walk(), [])
        events = self.walk()
        self.assertEqual([e.kind for e in events], ["warning"])
        self.assertEqual(events[0].columns, (0, 10))
        self.assertEqual(g.radioactive_cols, (0, 10))
        self.assertEqual(self.walk(), [])
        events = self.walk()
        self.assertEqual([e.kind for e in events], ["destroyed"])
        self.assertEqual(set(events[0].casualties), self.doomed)
        self.assertEqual((g.first_col, g.last_col), (1, 9))
        self.assertEqual((g.radioactive_cols, g.quiet_turns), ((), 0))
        self.assertFalse(any(h[0] in (0, 10) for h in g.visible_hexes(1)))
        self.assertFalse(g.over)
        # The clock restarts: the next two columns go after another quiet spell.
        for _ in range(QUIET_TURNS_FOR_RADIATION):
            self.walk()
        self.assertEqual(g.radioactive_cols, (1, 9))

    def test_combat_resets_the_clock(self):
        g = self.g
        for _ in range(QUIET_TURNS_FOR_RADIATION - 2):
            self.walk()
        self.assertEqual(g.current, 1)
        archer, red = self.walkers[1], self.walkers[2]
        g.end_movement()
        g.ranged_attack(archer, red)  # counts as combat even if it misses
        g.end_turn()
        self.assertEqual(g.quiet_turns, 0)

    def test_last_column_destroys_everyone(self):
        g = self.g
        g.first_col = g.last_col = 5
        for u in g.units:
            if u.alive:
                g.board.pop(u.pos)
        for u, h in zip([self.walkers[1], self.walkers[2]], [(5, 5), (5, 9)]):
            u.pos = h
            g.board[h] = u
        for u in self.doomed:
            u.health, u.pos = 0, None
        g.radioactive_cols, g.radiation_countdown = (5,), 1
        g.end_movement()
        events = g.end_turn()
        self.assertEqual(events[0].columns, (5,))
        self.assertTrue(g.over)
        self.assertEqual(g.winner, DRAW)


if __name__ == "__main__":
    unittest.main()
