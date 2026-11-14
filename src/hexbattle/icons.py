"""Small vector icons drawn on a Tk canvas.

Each function draws an icon centered on (x, y) that fits in a square of side
`s`.  They are drawn from canvas primitives so they look the same on every
system, with no dependence on emoji fonts.
"""

from __future__ import annotations

import math


def _width(s: float) -> float:
    return max(1.0, s / 9)


def heart(cv, x, y, s, fill, outline, tags=()):
    k = s / 32
    pts = []
    for i in range(32):
        t = 2 * math.pi * i / 32
        hx = 16 * math.sin(t) ** 3
        hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts += [x + hx * k, y - (hy + 2.5) * k]
    cv.create_polygon(pts, fill=fill, outline=outline, width=max(1.0, s / 14), tags=tags)


def swords(cv, x, y, s, color, tags=()):
    a = s * 0.40
    w = _width(s)
    guard = s * 0.16 / math.sqrt(2)
    for sign in (1, -1):
        hx, hy = x - sign * a, y + a  # handle end
        tx, ty = x + sign * a, y - a  # tip
        cv.create_line(hx, hy, tx, ty, fill=color, width=w, capstyle="round", tags=tags)
        gx, gy = hx + (tx - hx) * 0.28, hy + (ty - hy) * 0.28
        cv.create_line(gx - guard, gy - guard * sign, gx + guard, gy + guard * sign,
                       fill=color, width=w, capstyle="round", tags=tags)


def shield(cv, x, y, s, color, tags=()):
    pts = [(-0.40, -0.46), (0.40, -0.46), (0.40, 0.04), (0.0, 0.48), (-0.40, 0.04)]
    cv.create_polygon([c for px, py in pts for c in (x + px * s, y + py * s)],
                      fill="", outline=color, width=_width(s), joinstyle="round", tags=tags)
    cv.create_line(x, y - 0.40 * s, x, y + 0.36 * s, fill=color, width=_width(s) * 0.7, tags=tags)


def target(cv, x, y, s, color, tags=()):
    w = _width(s) * 0.8
    for r in (0.46, 0.25):
        cv.create_oval(x - r * s, y - r * s, x + r * s, y + r * s, outline=color, width=w, tags=tags)
    r = 0.07 * s
    cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color, tags=tags)


def feet(cv, x, y, s, color, tags=()):
    for dx, dy in ((-0.19, 0.12), (0.19, -0.10)):
        cx, cy = x + dx * s, y + dy * s
        cv.create_oval(cx - 0.11 * s, cy - 0.14 * s, cx + 0.11 * s, cy + 0.26 * s,
                       fill=color, outline=color, tags=tags)
        for tx, ty in ((-0.08, -0.25), (0.0, -0.29), (0.08, -0.25)):
            r = 0.045 * s
            px, py = cx + tx * s, cy + ty * s
            cv.create_oval(px - r, py - r, px + r, py + r, fill=color, outline=color, tags=tags)


def eye(cv, x, y, s, color, tags=()):
    pts = [(-0.50, 0.0), (-0.25, -0.26), (0.25, -0.26), (0.50, 0.0), (0.25, 0.26), (-0.25, 0.26)]
    cv.create_polygon([c for px, py in pts for c in (x + px * s, y + py * s)], smooth=True,
                      fill="", outline=color, width=_width(s) * 0.8, tags=tags)
    r = 0.14 * s
    cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color, tags=tags)


def radiation(cv, x, y, s, color, background, tags=()):
    """The radiation trefoil: three blades around a central dot."""
    r = s * 0.5
    for start in (0, 120, 240):
        cv.create_arc(x - r, y - r, x + r, y + r, start=start, extent=60, style="pieslice",
                      fill=color, outline="", tags=tags)
    gap = s * 0.17
    cv.create_oval(x - gap, y - gap, x + gap, y + gap, fill=background, outline="", tags=tags)
    dot = s * 0.11
    cv.create_oval(x - dot, y - dot, x + dot, y + dot, fill=color, outline="", tags=tags)


# Icon for each fixed stat, in the order they appear on a tile.
STAT_ICONS = (
    ("attack", swords),
    ("defense", shield),
    ("range", target),
    ("movement", feet),
    ("sight", eye),
)
