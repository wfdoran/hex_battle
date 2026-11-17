# Hex Battle — Report 7 (response to PROMPT7.md)

## Summary

**Anchored units** are in. A unit with range 1 or more that stays put
through two of its side's movement phases in a row, last turn's and this
turn's, adds 1 to its attack when it fires. The bonus counts only for ranged
attacks, and it ends as soon as the unit moves.

Its attack is shown as **x+1**, for example "3+1". To make room for that, I
regrouped the stats on each tile, as described below.

Nothing has been staged or committed. `RULES.md` and `src/README.md` are
updated. Round 6 wasn't committed when I started, so this round's changes
sit on top of it in the working tree.

## Answers to your notes on REPORT6

1. **Less luck.** Damage chart left alone.
2. **Retuning hard.** Waiting, as you asked.

## How anchoring works

Each unit counts how many of its side's movement phases in a row it has
ended on the hex it started on. Moving, including attacking (which is a
move), resets the count to 0.

The game reports a unit as anchored, and shows x+1, in two situations:

- **In its own ranged phase**, if it stayed put in this turn's movement phase
  and in the one before. This is when the +1 applies.
- **At any other time**, if it stayed put in its last movement phase and
  hasn't moved since. In other words, it will be anchored when it fires, as
  long as it doesn't move first.

So the x+1 shows ahead of time. You can see during the movement phase
which units will lose their bonus if you move them. The moment a unit
moves, its x+1 goes back to x.

Details:

- **Only ranged attacks.** Battles use the plain attack, and the attack stat
  itself never changes.
- **Units with range 0 are never anchored.** They can't shoot, so x+1 would
  mislead.
- **First turn.** No unit can be anchored, because there was no earlier
  turn to stay put through. Setup doesn't count.
- **Ambush.** A unit whose move is stopped by a hidden enemy before it leaves
  its hex still counts as staying put.
- **Log.** A shot fired with the bonus says so, for example: "Blue #1 at D3
  (anchored, attack 5+1) fired at Red #1 at E3: 2 damage, 6 health left."
- **Hover.** The hover text reads, for example, "attack 5+1 (anchored: +1
  when it fires)".

**The computer.**
- Medium and hard pick their targets using the bonus.
- When hard decides whether to move a unit, it counts the bonus the unit
  would keep by staying put.
- Easy still picks targets at random.
- I haven't otherwise retuned the AI, per your note.

## Tile layout

"5+1" didn't fit in the old top row of three stats. It ran into the swords
and shield icons. The tile now groups the stats in two rows:

- **Top row:** attack and defense, with room for "x+1".
- **Second row:** range, movement and sight.

The hearts are unchanged. Numbers sit just right of their icons, so single
digits look the same as before. I checked the board, the setup roster and
the start-screen tiles at full size.

## How it affects play

Each figure is from 800 AI-vs-AI games: 400 seeds, each played from both
sides. The baseline is this same code with the bonus set to 0. It
reproduced round 6's results exactly, which confirms that the bonus is the
only difference.

| Match-up | No bonus | Anchoring (now) |
|---|---|---|
| Medium vs Easy | Medium 82% | **Medium 86%** |
| Hard vs Medium | Hard 64% | **Hard 64%** |
| Hard vs Easy | Hard 84% | **Hard 86%** |

- **About a quarter of all shots are anchored**, even though the computer
  doesn't yet seek out the bonus, apart from hard counting it when deciding
  whether to move.
- **Medium vs easy widened by about 4 points.** That is just past the noise,
  which is about ±2.4 points at 95% confidence.
- **Hard vs medium didn't move**, and hard vs easy rose within the noise.
- Game length, radiation and fatigue are about the same as before. Games
  have slightly fewer shots each, about 66 instead of 69.

## Testing

- **51 unit tests**, all passing. The new ones cover:
  - no anchoring on the first turn
  - the +1 after two movement phases in place, and lasting while the unit
    stays
  - moving ending it at once, and two more turns in place needed to get it
    back
  - battles using the plain attack, with attacking ending anchoring
  - units with range 0 never being anchored
- **GUI:**
  - I rendered an anchored unit and checked that its tile showed "5+1"
    without overlap, and that the hover text and log line were right.
  - The round-2 smoke test passed with no errors. It covers the start
    screen, a full game against hard, seed replay, hot seat with five loss
    pop-ups, and radiation.

## Decisions I made

1. **x+1 shows ahead of time,** meaning "anchored when it fires, if it stays
   put", rather than only during the ranged phase. Otherwise the x+1 would
   appear only after you had finished moving.
2. **Enemy units show x+1 too, when visible.** This tells you a visible
   enemy has held its position since its last turn, even if you couldn't
   see it then. I treated that as part of what you can see, like dug-in
   troops.
3. **Units with range 0 never show x+1.**
4. **The setup doesn't count as a turn in place.**
5. **Attack and defense now share the top row of each tile.**

## Questions for you

1. **Enemy x+1.** Is it OK that x+1 on a visible enemy reveals it hasn't
   moved since its last turn, even if it was in the fog then? The
   alternative is to show x+1 only on your own units.
2. **Setup as a turn.** Should units count as having stayed put during
   setup, so they can be anchored on their first turn? That would make the
   opening favor the side that sits back and shoots.
