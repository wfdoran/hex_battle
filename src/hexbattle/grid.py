"""Hex grid geometry for the battlefield.

The board has 11 columns of flat-topped hexes.  Even columns (0, 2, ..., 10)
hold 5 hexes and odd columns hold 6, so the odd columns stick out half a hex
above and below their neighbors.

Hexes are addressed with "doubled" coordinates (col, y), where y counts
half-hex steps from the top of the board.  Odd columns use y = 1, 3, ..., 11
and even columns use y = 2, 4, ..., 10.  In this system every hex has the
same six neighbor offsets and distance has a simple closed form.
"""

from __future__ import annotations

from functools import lru_cache

COLS = 11
COLUMN_LETTERS = "ABCDEFGHIJK"
NEIGHBOR_OFFSETS = ((0, -2), (1, -1), (1, 1), (0, 2), (-1, 1), (-1, -1))

Hex = tuple[int, int]


def column_height(col: int) -> int:
    return 6 if col % 2 else 5


def column_ys(col: int) -> range:
    first = 1 if col % 2 else 2
    return range(first, first + 2 * column_height(col), 2)


ALL_HEXES: tuple[Hex, ...] = tuple((c, y) for c in range(COLS) for y in column_ys(c))
_VALID = frozenset(ALL_HEXES)


def is_valid(h: Hex) -> bool:
    return h in _VALID


def neighbors(h: Hex) -> list[Hex]:
    c, y = h
    return [n for n in ((c + dc, y + dy) for dc, dy in NEIGHBOR_OFFSETS) if n in _VALID]


def distance(a: Hex, b: Hex) -> int:
    dc = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return dc + max(0, (dy - dc) // 2)


@lru_cache(maxsize=None)
def hexes_within(h: Hex, radius: int) -> frozenset[Hex]:
    """All board hexes at distance <= radius from h, including h itself."""
    return frozenset(o for o in ALL_HEXES if distance(h, o) <= radius)


def row_index(h: Hex) -> int:
    """0-based position of the hex within its column, counting from the top."""
    c, y = h
    return (y - (1 if c % 2 else 2)) // 2


def label(h: Hex) -> str:
    """Human-readable name such as "C4" (column letter, row number)."""
    return f"{COLUMN_LETTERS[h[0]]}{row_index(h) + 1}"
