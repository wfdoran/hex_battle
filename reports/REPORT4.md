# Hex Battle — Report 4 (response to PROMPT4.md)

## Summary

- **The computer no longer cheats**, at any level. It sees only what its own
  units see, remembers where it last saw your units, and guesses where they
  have gone.
- **Easy is weaker**, so it works as an introduction for new players.
- **Hard looks ahead.** It plays its best few moves forward in imagined
  games, through your reply, and picks the one that works out best.
- **Battle-odds pop-up.** With a unit selected during movement, hovering over
  an enemy shows the chances of each outcome.

Hard now beats medium 66% of the time, up from about 60% after the cheating
was removed. That is short of the 80% you hoped for. Details are below.

Nothing has been staged or committed. `RULES.md` and `src/README.md` are
updated.

## Results

Every match-up below was played over 300 games: 150 fresh seeds, each played
from both sides. All levels play honestly.

| Match-up | Round 3 (cheating) | Now |
|---|---|---|
| Medium vs Easy | Medium 80% | **Medium 83%** |
| Hard vs Medium | Hard 56% | **Hard 66%** |
| Hard vs Easy | Hard 73% | **Hard 84%** |

With 300 games, each figure is good to about ±3 points.

## 1. Honest computer (all levels)

I made all three levels honest. Easy doesn't need the help, and "the
computer never sees through the fog" is a simpler rule to explain.

Each computer player keeps an **enemy tracker**. For every one of your units
it keeps the set of hexes the unit could be on:

- **Before contact:** the unit could be anywhere in your setup zone.
- **When seen:** exactly where it is, with its current health.
- **After each of your turns:** every hex within the unit's movement of where
  it could have been.
- **Every hex the computer can currently see** is struck off, because the
  unit would be visible there.
- **Deaths:** battle and ranged-attack deaths are public, since both players'
  logs report them. Radiation deaths in the fog are known only as a count, the
  same as for you. The tracker writes off the units most likely to have been
  caught. If it guesses wrong and the unit turns up later, it is tracked
  again.

To plan, the computer puts each hidden unit at its best guess. That is the
last place it was seen if it could still be there, otherwise the nearest
place it could be. Units never seen are assumed to be at the front of your
setup zone.

**What honesty costs.** Before adding look-ahead, I gave hard back its
cheating and played it against honest medium. It won 63% instead of 60%. The
fog matters less than I expected. The tracker's guesses are good enough, and
most fighting happens at close range, where units are visible anyway.

**A test proves honesty.** The same position is played with one of your
units hidden in three different places, and each level must choose exactly
the same action every time.

## 2. Easy is weaker

Easy now leaves 45% of its units idle each turn, up from 30%, and its moves
are noisier. Its fight-picking is unchanged: it compares raw stats and
ignores battle odds. Medium now beats it 83% of the time, up from 80%.

I also tried making easy attack recklessly. That made it *stronger*, because
aggression pays in this game, so I left that alone.

## 3. Hard: look-ahead and other changes

The look-ahead made the biggest difference. Each time hard is about to move:

1. It scores every legal move with its usual judgment.
2. It takes the top 5 candidates. For each one, it plays 8 imagined games in
   which:
   - your hidden units are placed at its guesses
   - it finishes its turn normally
   - you reply, modeled as the medium AI
3. It scores what material is left after your reply, and picks the candidate
   with the best average.

Its usual judgment also got smarter:

- **Attacks look ahead.** Hard considers every possible outcome of a battle,
  including what a weakened winner on the captured hex faces next turn.
- **Mutual support.** A unit is in less real danger if friends nearby could
  finish off an enemy that beats it. This pulls hard's units together.

**Cost.** Hard takes about 0.1 s per turn on median, and at most about 1.5 s
in the turns I measured. The board waits while it thinks, which RULES.md
mentions.

**What didn't help:**

| Change tried | Hard vs medium |
|---|---|
| Retuning hard's weights (danger, approach, appetite, surrounding) | flat around 60% |
| Waiting for medium to come to hard | worse, 50% |
| A longer look-ahead, through hard's next turn as well | 61% |
| More rollouts (16 instead of 8) | 67%, same as 8, at twice the time |
| Giving every candidate the same dice | no gain |

## On the 80% target

I don't think 80% between neighbouring levels is reachable with this rule
set, at least not without much heavier search. Two experiments suggest the
game itself is very luck-heavy:

- A computer that **never moves**, and only shoots what wanders into range,
  still beat medium about 11% of the time and hard about 8%. (That was
  measured before hard had look-ahead.) Defending is strong, because
  attackers walk into free ranged fire.
- Hard beats easy only 84% of the time, though easy sits out nearly half its
  units every turn.

If you want bigger gaps, the most direct lever is to make the game less
random, for example by reducing the zero-damage chances in the damage table.
That is a design question for you. Short of that, easy could be made weaker
still.

## 4. Battle-odds pop-up

During movement, with one of your units selected, hovering over a visible
enemy pops up a box beside the pointer:

```
Battle odds
Blue #1 wins          89%
Red #1 wins            8%
Both destroyed         3%
```

- The odds are computed exactly from the damage table, using both units'
  current health, and they are instant.
- If the enemy can't be reached this move, the box says "Out of reach this
  move", so you can still compare matchups.
- Tiny chances show as "<1%" or ">99%" rather than rounding to 0 or 100.
- Nothing pops up when no unit is selected, or during the other side's turn.
- It works in hot seat too, for the player at the screen.

## Testing

- **43 unit tests**, all passing. New ones cover:
  - the tracker: unseen units, units that were seen and then slipped into the
    fog, and deaths becoming known
  - the honesty test described above
  - complete legal games for every pairing of levels, including the hard
    look-ahead. This test plays fewer imagined games to stay quick.
- **GUI:**
  - I rendered the odds pop-up for a reachable and an unreachable enemy and
    checked the images, and confirmed it doesn't appear without a selection.
  - The round-2 smoke test passed with no errors. It covers the start
    screen, a full game against hard, seed replay, hot seat and radiation.

## Decisions I made

1. **All three levels are honest**, not just medium and hard.
2. **The odds pop-up also shows for enemies out of reach,** marked as such.
3. **Hard's look-ahead models you as the medium AI.** It is the opponent
   model that tested best. A human who plays differently from medium may
   make hard's look-ahead less accurate.

## Questions for you

1. **Difficulty gaps.** Would you like to reduce the luck in combat to widen
   the gaps, for example with fewer zero-damage results? Or should easy get
   weaker still?
2. **Hard's thinking time.** It is short now. Would you accept a slower hard,
   with a "thinking…" indicator, if it played somewhat better? My tests
   suggest only small gains from more search.
3. **Odds in the ranged phase.** Should hovering a target in the ranged phase
   show the chance of each damage amount, and the kill chance?
