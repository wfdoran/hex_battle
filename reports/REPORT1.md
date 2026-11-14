# Hex Battle — Project Report

## Summary

The first version is complete and playable: a native Linux GUI game, human
(Blue) against the computer (Red). It covers every rule in
`prompts/PROMPT1.md`:

- random balanced units
- blind setup
- shared fog of war
- movement with the pinning rule
- battles fought to the death
- ranged attacks with spotting and no counter-attack
- all three ways the game can end

Nothing has been staged or committed.

- **Run:** `cd src && python3 -m hexbattle` (see `src/README.md`)
- **Rules for players:** `RULES.md`

## Technology choice

**Python 3 + Tkinter.** Tkinter comes with Python, so the game is a native
Linux program from the start and the interim web version wasn't needed. On
Ubuntu the only requirement is `sudo apt install python3 python3-tk`, and
both were already installed here (Python 3.14, Tk 9.0). The code uses no
third-party packages and works with Python 3.10 or newer.

All icons (hearts, swords, shield, target, feet, eye) are drawn from canvas
shapes rather than emoji, so they look the same on any system. The board
resizes with the window.

## Structure

About 1,650 lines of Python in `src/`:

| File | Contents |
|---|---|
| `grid.py` | Hex coordinates, neighbors, distance, labels |
| `units.py` | Unit stats and roster generation |
| `combat.py` | Damage table and battles |
| `game.py` | The rules engine, with no GUI code |
| `ai.py` | The computer player |
| `icons.py` | Vector icons |
| `gui.py` | The Tkinter front end |

Because the rules engine stands alone, a stronger AI or a different front
end can be built without touching the rules.

Hexes use "doubled" coordinates internally: column, plus the y position in
half-hex steps. This gives every hex the same six neighbor offsets and a
one-line distance formula. On screen and in the log, hexes are named **A1**
to **K5**.

## Testing

- **31 unit tests** (`python3 -m unittest discover -s tests -t .` in `src`)
  cover:
  - board shape
  - neighbors
  - distance checked against brute-force search
  - stat generation
  - the damage table
  - placement zones
  - fog of war blocking moves
  - friendly blocking
  - moves ending on an enemy
  - pinning at the start and along a path
  - ambush by a hidden enemy
  - board consistency after battles
  - all three battle outcomes (win, loss, draw)
  - ranged spotting and no counter-attack
  - one shot per turn
  - the idle-turn draw
  - six complete AI-vs-AI games in which every AI action must pass the rules
    engine
- **AI-vs-AI:** in 20 simulated games, Blue won 11, Red won 8, and one was a
  draw. Games lasted 9–48 turns, and all 20 took under 2 seconds in total.
- **GUI:** a script drove the real window on your display. It placed units
  by clicking, then played full games of moves, battles and ranged attacks
  against the AI through to the game-over message, with no errors. I checked
  the rendered board, roster and legend visually. Your desktop blocks screen
  capture, so I couldn't capture the plain Tk widgets (buttons and log). They
  were checked through the code instead.

## Decisions I made where the prompt was silent

1. **Board size.** Six columns of 5 plus five columns of 6 is **60 hexes**.
   Each setup zone (3 columns) has 16 hexes for 10 units.
2. **Sight** uses hex distance and always includes the unit's own hex.
   Nothing blocks line of sight.
3. **Pinning and fog (ambush).** When the game shows where a unit can move,
   it counts only *visible* enemies for the "two neighboring enemies" rule.
   Counting hidden ones would leak their positions, because some hexes would
   be missing from the highlights for no visible reason. If a hidden enemy
   does pin the unit partway, it stops on that hex, still counts as having
   moved, and the log says so.
4. **Attacking by moving.** The enemy's hex counts toward the unit's
   movement, so a unit with movement 1 can attack only adjacent enemies.
5. **Ranged attacks** use the attacker's attack against the target's defense
   with the same damage table, and can reach targets 1 to `range` hexes
   away.
6. **Idle-turn draw.** The game is a draw after two consecutive turns, one
   per player, with no move and no attack.
7. **Setup order.** The computer places its units first, where you can't see
   them, and then you place yours.
8. **What you learn about hidden enemies.** Enemy moves that end out of
   sight are not logged. A shot from a hidden enemy is reported as "A hidden
   Red unit fired at …".
9. **Health display.** Filled hearts show health left and hollow hearts show
   health lost, so you can see the unit's maximum too. Units with more than 4
   health get two rows of hearts.
10. **Unit numbers.** Each roster unit is numbered #1 to #10, and both sides'
    copies share the number. The number appears under the tile and in the
    log.
11. **Visual cues.** Units that have already acted in the current phase are
    drawn faded. Battles and hits flash orange. Moves are animated one hex
    at a time, and the computer's moves are animated only where you can see
    them.
12. **Random units.** As requested, every combination that adds up to 15 is
    equally likely. There are 1,229 such combinations. For reference, the
    average unit has health 3.9, attack 2.5, defense 2.5, range 1.5,
    movement 2.2 and sight 2.5, and about 30% of units have range 0.

## The computer player

It is a simple heuristic player:

- **Setup:** sturdy units go to the front column and ranged units to the
  back. Rows are random.
- **Movement:**
  - Each step, it finds the best move across all of its units. For possible
    battles, it simulates the fight about 150 times and attacks only if the
    expected gain is clearly positive. Otherwise it moves to improve its
    position.
  - Melee units close in while avoiding being pinned and the enemies that
    could reach them next turn.
  - Ranged units try to stand at about their range from the nearest enemy.
- **Ranged attacks:** it fires at the target with the best combination of
  kill chance and expected damage.
- **Information:** as allowed for now, it knows where all your units are. It
  still obeys the rules, so it can move only through hexes its own units can
  see, and can shoot only at targets they can see.

## Questions for you

1. **Stalemate loophole.** The idle-turn draw can be dodged by moving one
   unit back and forth forever. Do you want a hard turn limit, or a "no
   battle or hit in N turns" rule?
2. **Ambush.** Is the interpretation in decision 3 what you intended? The
   alternative is to count hidden enemies when showing legal moves, which
   gives away where they are.
3. **Battle presentation.** Battles are currently shown as an orange flash
   plus a round-by-round line in the log. Would you like a pop-up that plays
   out each round?
4. **Unit balance.** Many uniformly generated units end up with range 0 or
   with low health. Which way would you like to take generation when you
   revisit it, for example a minimum health, or weighting?
5. **Next steps for the AI.** Should the next AI drop the cheating first, or
   play stronger first? Making it honest means it has to keep track of
   enemies it last saw.
6. **Human vs. human.** The rules engine already supports two human
   players. Do you want a hot-seat mode, with a screen hiding the board
   between turns?

## Housekeeping

- I added a root `.gitignore` for Python's `__pycache__/` folders.
- `prompts/PROMPT1.md~` is an editor backup file. I left it alone.
