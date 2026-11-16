import random
import unittest
from collections import deque

from hexbattle.combat import (DAMAGE_TABLE, battle_odds, battle_rounds, damage_odds,
                               expected_damage)
from hexbattle.grid import ALL_HEXES, column_height, distance, label, neighbors
from hexbattle.units import (MAX_RANGE_ZERO, STAT_RANGES, STAT_TOTAL, STATS, random_roster,
                             stat_combinations)


class GridTest(unittest.TestCase):
    def test_board_shape(self):
        self.assertEqual([column_height(c) for c in range(11)], [5, 6] * 5 + [5])
        self.assertEqual(len(ALL_HEXES), 60)

    def test_neighbors(self):
        for h in ALL_HEXES:
            ns = neighbors(h)
            self.assertLessEqual(len(ns), 6)
            for n in ns:
                self.assertIn(h, neighbors(n))
                self.assertEqual(distance(h, n), 1)
        self.assertEqual(len(neighbors((5, 5))), 6)  # interior
        self.assertEqual(len(neighbors((0, 2))), 3)  # top-left corner

    def test_distance_matches_bfs(self):
        for start in ALL_HEXES:
            dist = {start: 0}
            queue = deque([start])
            while queue:
                h = queue.popleft()
                for n in neighbors(h):
                    if n not in dist:
                        dist[n] = dist[h] + 1
                        queue.append(n)
            for h in ALL_HEXES:
                self.assertEqual(distance(start, h), dist[h], (start, h))

    def test_diagram_ring_sizes(self):
        center = (5, 5)
        self.assertEqual(sum(distance(center, h) == 1 for h in ALL_HEXES), 6)
        self.assertEqual(sum(distance(center, h) == 2 for h in ALL_HEXES), 12)

    def test_labels(self):
        self.assertEqual(label((0, 2)), "A1")
        self.assertEqual(label((1, 11)), "B6")
        self.assertEqual(label((10, 10)), "K5")


class UnitsTest(unittest.TestCase):
    def test_combinations_are_valid(self):
        combos = stat_combinations()
        self.assertGreater(len(combos), 0)
        self.assertEqual(len(set(combos)), len(combos))
        for combo in combos:
            self.assertEqual(sum(combo), STAT_TOTAL)
            for name, value in zip(STATS, combo):
                lo, hi = STAT_RANGES[name]
                self.assertTrue(lo <= value <= hi)

    def test_roster(self):
        roster = random_roster(random.Random(3))
        self.assertEqual(len(roster), 10)
        for line in roster:
            self.assertIn(line, stat_combinations())

    def test_range_zero_cap(self):
        rng = random.Random(4)
        for _ in range(300):
            roster = random_roster(rng)
            self.assertLessEqual(sum(line[3] == 0 for line in roster), MAX_RANGE_ZERO)

    def test_new_stat_limits(self):
        self.assertEqual(STAT_RANGES["health"], (4, 8))
        self.assertEqual(STAT_RANGES["sight"], (1, 3))


class CombatTest(unittest.TestCase):
    def test_table_rows_sum_to_100(self):
        for diff, odds in DAMAGE_TABLE.items():
            self.assertEqual(sum(odds), 100, diff)

    def test_all_stat_differences_covered(self):
        for a in range(1, 6):
            for d in range(1, 6):
                self.assertIs(damage_odds(a, d), DAMAGE_TABLE[a - d])

    def test_expected_damage_increases_with_attack(self):
        values = [expected_damage(a, 3) for a in range(1, 6)]
        self.assertEqual(values, sorted(values))

    def test_battle_ends_with_a_death(self):
        rng = random.Random(7)
        for _ in range(200):
            rounds, ah, dh = battle_rounds(5, 3, 2, 4, 2, 4, rng)
            self.assertTrue(ah == 0 or dh == 0)
            self.assertGreaterEqual(min(ah, dh), 0)
            self.assertEqual(5 - ah, min(5, sum(r[1] for r in rounds)))
            self.assertEqual(4 - dh, min(4, sum(r[0] for r in rounds)))

    def test_battle_odds_exact(self):
        win, lose, both = battle_odds(5, 3, 2, 4, 2, 4)
        self.assertAlmostEqual(win + lose + both, 1.0)
        rng = random.Random(11)
        n = 20000
        wins = sum(battle_rounds(5, 3, 2, 4, 2, 4, rng)[2] == 0 and True for _ in range(n))
        # wins here counts defender deaths, i.e. attacker wins plus mutual destruction
        self.assertAlmostEqual(wins / n, win + both, delta=0.015)
        self.assertEqual(battle_odds(1, 5, 1, 1, 5, 1)[2], 0.64 / (1 - 0.04))


if __name__ == "__main__":
    unittest.main()
