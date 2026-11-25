# Hex Battle — Report 8 (response to PROMPT8.md)

## Summary

- **I evaluated all three damage charts and picked Plan B.** It cuts the
  luck the most: fewer misses, more decisive battles, and shorter games
  with fewer stalemates. The gaps between AI levels are about the same
  under all three charts.
- **Plan B has a typo.** Its +3 row adds up to 110% (20/60/30). I used
  20/60/20, which matches the shape of the +4 row (25/50/25). Please confirm
  or correct it. Only about 1.5% of attack rolls use this row, so the choice
  barely affects play.
- **I tuned hard for Plan B.** One weight changed: hard now weighs the
  danger of a hex more heavily. This lifted hard vs easy to 90%, but hard vs
  medium stayed at about 62%. Weight tuning has hit the same ceiling as in
  round 4. More below.

Nothing has been staged or committed. `RULES.md` is updated with the new
chart.

## Answers to your notes on REPORT7

1. **Enemy x+1.** Kept as is.
2. **Setup as a turn.** Kept as is: setup doesn't count.

## Comparing the charts

### Luck, independent of the AI

I took 4,000 random pairs of units from the roster generator and computed
exact battle odds and single-shot odds under each chart:

| Measure | C (old) | A | B |
|---|---|---|---|
| A random shot does no damage | 59% | 55% | **44%** |
| Average damage per battle round (both sides) | 1.11 | 1.18 | **1.36** |
| Battles where the favorite wins more than 80% of the time | 45% | 42% | **48%** |
| Average chance the favorite wins a battle | 77% | 75% | 77% |

- **B** misses far less and deals more damage per round. Battles are as
  often won by the stronger unit as under C, and more of them are clear-cut.
- **A** helps the underdog more than the favorite, because it mostly raises
  the damage of attacks at a poor edge. Battles become slightly *less*
  predictable.

### AI-vs-AI play

These were run before tuning: all three charts with the round-7 AI. Each
figure is from 800 games on the same seeds.

| | C (old) | A | B |
|---|---|---|---|
| Medium vs Easy | Medium 86% | Medium 82% | Medium 85% |
| Hard vs Medium | Hard 64% | Hard 64% | Hard 62% |
| Hard vs Easy | Hard 86% | Hard 86% | Hard 87% |
| Average game length | 38 turns | 37 turns | **34 turns** |
| Games where radiation destroyed columns | 13% | 12% | **10%** |
| Games with fatigue | 32% | 27% | **23%** |

The win rates are within noise of each other, except A's drop for medium
vs easy. B gives shorter games with fewer stalemates, which fits there being
more damage per round.

**Why B.** It reduces luck the most, it plays faster, and it doesn't hurt
the level gaps. A is worse on luck, and it hurt medium vs easy.

## Tuning hard for Plan B

**Method.** I tuned on one set of seeds (1000–1999) and then checked the
result on the standard set (0–399), which tuning never saw. That guards
against picking a setting that just got lucky on its seeds.

To make the sweep fast enough, I tuned with hard's look-ahead switched off.
That takes 8 seconds per 2,000 games, instead of 7 minutes per 600. The
look-ahead builds on the same scoring, and I checked the winner with it
switched back on.

**One weight at a time** (2,000 games each, about ±2 points at 95%):

| Weight | Lower | Current | Higher |
|---|---|---|---|
| Danger of a hex (0.6) | 0.3: 58% | 62% | **0.9: 64%**, 1.2: 63%, 1.5: 60%, 2.0: 58% |
| Pull toward enemies (0.7) | 0.4: 60% | | 1.0: 62% |
| Appetite for winnable fights (3.0) | 1.5: 62% | | 4.5: 61% |
| Danger cap (1.0) | 0.7: 61% | | 1.5: 62% |
| Credit for friendly support (0.5) | 0.25: 61% | | 0.75: 60% |
| Bonus for surrounding (0.15) | 0: 63% | | 0.3: 61% |
| Attack threshold (0) | −0.3: 62% | | 0.3: 63% |
| Move threshold (0.05) | 0: 62% | | 0.3: 62% |

Only the danger weight showed a clear effect. I set it to 0.9.

**Two shooting-order changes,** both tried and dropped:

| Change | Hard vs medium |
|---|---|
| Fire the most valuable shot first, from any unit | 62% (vs 64%) |
| Pick the best target, then shoot it with the weakest unit that can | 62.5% (vs 64%) |

**The look-ahead still helps.** On the tuning seeds, with danger 0.9, hard
beat medium 65% with look-ahead and 62.5% without.

### Result on the held-out seeds

Each figure is from 800 games on the standard seeds, all under Plan B:

| Match-up | Before tuning | After tuning |
|---|---|---|
| Medium vs Easy | Medium 85% | Medium 85% (unchanged, as expected) |
| Hard vs Medium | Hard 62% | **Hard 62%** |
| Hard vs Easy | Hard 87% | **Hard 90%** |

The gain against medium on the tuning seeds didn't hold up on the held-out
seeds. Across all three tests, the new weight is worth about 0 to 2 points
against medium, and about 3 against easy. I've kept it, since it's no
worse anywhere.

**Where this leaves the 80% goal.** Medium vs easy (85%) meets it. Hard vs
medium (62%) is well short, under every chart and every weight I tried. The
remaining gap is about hard's play, not the dice. Hard and medium share
most of their judgment, and tuning hard's weights can't make it play much
differently. Closing the gap would take a new kind of thinking for hard,
for example:

- planning attacks by several units on one enemy in the same turn
- a deeper or wider search, which would make it slower

That is a bigger project, and it may fit the "extreme" level you mentioned.

## Testing

- **51 unit tests**, all passing. One exact-odds test now reads the miss
  chance from the table, instead of hard-coding the old number.
- **GUI:** the round-2 smoke test passed with no errors. It covers the start
  screen, a full game against hard, seed replay, hot seat with five loss
  pop-ups, and radiation. The battle-odds pop-up uses the new chart
  automatically, since it reads the same table as combat.

## Decisions I made

1. **Plan B's +3 row is 20/60/20,** pending your confirmation.
2. **Only hard was tuned.** Medium already beats easy 85%, so I left medium
   and easy alone.
3. **The danger weight is 0.9.** No other weights changed.

## Questions for you

1. **Plan B's +3 row.** Is 20/60/20 what you meant? If you meant 10/60/30
   or 20/50/30, it's a one-line change, and it would hardly affect play.
2. **Hard vs medium.** Hard sits at about 62%. Should the next AI step be a
   new kind of planning for hard, such as coordinated attacks? Or should
   that wait for an "extreme" level, with medium weakened a little instead
   to widen the hard–medium gap?
