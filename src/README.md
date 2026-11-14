# Hex Battle — building and running

Hex Battle is written in Python 3 with Tkinter, the GUI toolkit that ships
with Python, so it runs as a native Linux desktop program. There is nothing to
compile.

## Requirements

- Python 3.10 or newer
- Tkinter

On Ubuntu:

```sh
sudo apt install python3 python3-tk
```

(Both were already installed on the development machine: Python 3.14, Tk 9.0.)

## Run

From this `src` directory:

```sh
python3 -m hexbattle
```

To replay the same first game (same units, same dice), pass a seed:

```sh
python3 -m hexbattle --seed 42
```

See `../RULES.md` for how to play.

## Tests

```sh
python3 -m unittest discover -s tests -t .
```

## Layout

| File | Contents |
|------|----------|
| `hexbattle/grid.py`   | Hex coordinates, neighbors, distance, labels (A1–K5) |
| `hexbattle/units.py`  | Unit stats and random roster generation |
| `hexbattle/combat.py` | Damage table, single attacks, battles |
| `hexbattle/game.py`   | Rules engine: setup, fog of war, movement, ranged attacks, turns, end of game |
| `hexbattle/ai.py`     | Computer player |
| `hexbattle/icons.py`  | Vector icons (heart, swords, shield, target, feet, eye) |
| `hexbattle/gui.py`    | Tkinter window, board drawing, input, animation, log |
| `tests/`              | Unit tests for the rules, plus whole AI-vs-AI games |

The rules engine (`game.py`) does not depend on the GUI, so a different
front end or a stronger AI can be built on top of it.
