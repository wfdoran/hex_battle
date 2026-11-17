# Hex Battle — Report 6 (response to PROMPT6.md)

## Summary

Both changes are in:

1. **Fatigue now lowers movement as well as defense**, each by 1 and never
   below 1.
2. **The damage chart is revised.** A +3 edge always does at least 1 damage,
   and a +4 edge always does at least 2.

The changes didn't widen the gaps between levels. As the measurements below
show, attacks with a +3 or +4 edge are rare. Most of the luck comes from the
rows the new chart left alone.

Nothing has been staged or committed. `RULES.md` is updated.

## Answers to your notes on REPORT5

1. **Fatigue is forever.** Unchanged.
2. **Retuning hard.** Waiting, as you asked, until these changes settle.

## The changes

### Fatigue lowers movement

When fatigue strikes, every living unit loses 1 defense and 1 movement.
Each stat stops at 1 (`MIN_DEFENSE` and `MIN_MOVEMENT` in `game.py`). A unit
with defense 1 still loses movement, and the other way round.

- Each lowered stat is drawn in yellow on the tile, so a unit can show just
  one yellow number.
- Hovering shows each lowered stat with its old value, for example
  "movement 1 (tired; was 2)".
- The log and side panel now say "defense and movement".
- The game keeps each unit's original value for only the stats fatigue
  lowered (`Game.rested`, which replaces `rested_defense`).

### Damage chart

| attack − defense | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| +4 | | | 34% | 33% | 33% |
| +3 | | 34% | 33% | 33% | |

The other rows are unchanged. The battle-odds pop-up and the computer use
the new chart automatically, because they read the same table as combat.

## How the changes affect play

Each figure is from AI-vs-AI games on the same seeds, played from both
sides. The two full columns use 800 games per match-up. The single-change
columns use 400.

| Match-up | Round 5 rules | New chart only | Movement fatigue only | Both (now) |
|---|---|---|---|---|
| Medium vs Easy | 82% | 84% | 82% | **82%** |
| Hard vs Medium | 62% | 62% | 61% | **64%** |
| Hard vs Easy | 84% | — | — | **84%** |

All of these differences are within the noise. That is about ±2.4 points
for 800 games and ±3.4 for 400, at 95% confidence. Game length (about 39
turns), radiation (in 10–16% of games) and fatigue (in about a third of
games) are also unchanged.

**Why the new chart does so little.** I counted every attack roll, both
ranged and in battles, over 450 games. This is how often each
attack-minus-defense difference came up:

| Difference | −4 | −3 | −2 | −1 | 0 | +1 | +2 | +3 | +4 |
|---|---|---|---|---|---|---|---|---|---|
| Share of rolls | 5% | 11% | 19% | 22% | 25% | 12% | 4% | 1.5% | 0.4% |

- **Only about 2% of rolls use the rows you changed.** A +3 or +4 needs
  attack 4–5 against defense 1–2, and few units have that.
- **About 81% of rolls are at 0 or below**, where 67–86% of attacks do no
  damage. That is where the luck is. These rolls dominate partly because
  battles at a poor edge last many rounds, since most rolls miss, so each
  such battle produces many rolls.
- **Fatigue doesn't change this,** because it lowers defense on both sides.
  It shifts the differences up by 1 only once it strikes, and it strikes in
  only a third of games.

If you want less luck, the lever is the rows from +1 down to −4. For
example, if an even fight (0) did at least some damage more often, every
battle would be shorter and less swingy.

## Testing

- **47 unit tests**, all passing. New and changed tests cover:
  - fatigue lowering defense and movement, each to no lower than 1, and
    recording only the stats that dropped
  - a +3 edge never missing and a +4 edge always doing at least 2 damage
  - **Two tests needed new numbers.** They depended on a +4 edge missing.
    Under the new chart, two 1-health units at +4 always destroy each other.
    The tests now use a +2 matchup, where all three outcomes are still
    possible, and check the exact odds for it.
- **GUI:**
  - I played quiet turns in the window until fatigue struck, and checked the
    screenshot: each lowered stat was in yellow, a unit with defense 1 showed
    only its movement in yellow, and the hover and panel text were right.
  - The round-2 smoke test passed with no errors. It covers the start
    screen, a 43-turn game against hard in which fatigue struck, seed
    replay, hot seat with four loss pop-ups, and radiation. Getting there
    took two fixes to my test script, not to the game:
    - The seed-replay check compared the finished game's unit stats, which
      fatigue can now lower. It now compares the rosters dealt.
    - The script never stubbed the round-3 loss pop-up, so it waited for a
      click whenever a hot-seat unit died.

## Decisions I made

1. **Fatigue lowers each stat independently.** A unit at defense 1 still
   loses movement, and a unit at movement 1 still loses defense.
2. **Blank cells mean 0%,** as in the rest of the chart.

## Questions for you

1. **Less luck.** Since the +3/+4 rows rarely come up, do you want to
   revise the rows from +1 down to −4? I can measure any candidate chart the
   same way before you decide.
2. **Retuning hard.** Are the rules settled enough to retune hard now?
