import random
import unittest

from hexbattle.ai import ComputerPlayer
from hexbattle.game import DRAW, Game, Phase, RuleError
from hexbattle.grid import ALL_HEXES, hexes_within, neighbors


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

    def test_pinned_at_start(self):
        g, units = make_game([((4, 6), (5, 1, 1, 0, 3, 5))],
                             [((5, 5), (5, 1, 1, 0, 1, 1)), ((5, 7), (5, 1, 1, 0, 1, 1))])
        self.assertEqual(set(g.legal_moves(units[(4, 6)])), {(5, 5), (5, 7)})

    def test_pinned_along_path(self):
        g, units = make_game([((2, 6), (5, 1, 1, 0, 4, 5))],
                             [((4, 4), (5, 1, 1, 0, 1, 1)), ((4, 8), (5, 1, 1, 0, 1, 1))])
        vis = g.visible_hexes(1)
        for dest, path in g.legal_moves(units[(2, 6)]).items():
            for h in path[:-1]:
                self.assertLess(g._adjacent_enemies(h, 1, vis), 2, (dest, path))

    def test_hidden_enemy_stops_move(self):
        mover = ((2, 6), (5, 1, 1, 0, 2, 1))
        spotter = ((2, 10), (5, 1, 1, 0, 1, 1))  # lets the mover see (3, 9)
        seen = ((2, 8), (5, 1, 1, 0, 1, 1))
        hidden = ((4, 8), (5, 1, 1, 0, 1, 1))  # next to (3, 7) but in fog
        g, units = make_game([mover, spotter], [seen, hidden])
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
    def test_ai_games_finish_legally(self):
        finished = 0
        for seed in range(6):
            g = Game(seed=seed)
            players = {p: ComputerPlayer(p, random.Random(seed * 10 + p), trials=40) for p in (1, 2)}
            for p in (1, 2):
                players[p].place_units(g)
            g.start()
            for _ in range(5000):
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
            finished += g.over
        self.assertGreaterEqual(finished, 4)


if __name__ == "__main__":
    unittest.main()
