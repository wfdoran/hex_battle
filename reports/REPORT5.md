# Hex Battle — Report 5 (response to PROMPT5.md)

## Summary

All three tweaks are in:

1. **Sight is now 1–3.**
2. **Radiation counts turns without damage.** A ranged attack that does no
   damage no longer resets the count.
3. **Fatigue.** After 6 turns without damage, every unit's defense drops by
   1, but never below 1.

Nothing has been staged or committed. `RULES.md` and `src/README.md` are
updated.

## Answers to your notes on REPORT4

1. **Difficulty gaps.** Combat luck is left alone for now. The results below
   show how the tweaks changed things.
2. **Slower hard.** Not done. Noted for a possible "extreme" level later.
3. **Odds in the ranged phase.** Not done.

## The tweaks

### 1. Sight 1–3

`STAT_RANGES["sight"]` is now `(1, 3)`. The other ranges and the total of 15
are unchanged, so the point that sight 4 used to take goes to the other
stats.

### 2. Turns without damage

The count now resets only when some unit loses health:

- **Battles** always reset it, because a battle goes on until a unit is
  destroyed.
- **Ranged attacks** reset it only if they do at least 1 damage.

The side panel says "Turns without damage" and names the next event, for
example "Turns without damage: 4 (fatigue at 6)".

### 3. Fatigue

When the count reaches 6:

- Every living unit on both sides loses 1 defense. A unit already at defense
  1 stays at 1.
- Both players' logs say so.
- On each tile, a lowered defense is drawn in yellow instead of white.
- Hovering a tired unit shows, for example, "defense 1 (tired; was 2)".
- The side panel adds a line, "Fatigue has lowered defense by 1."

The count keeps running, so radiation still comes at 10. The battle-odds
pop-up and the computer use the lowered defense automatically, because they
read the same values as combat.

The constants sit next to the radiation ones in `src/hexbattle/game.py`:
`QUIET_TURNS_FOR_FATIGUE = 6` and `MIN_DEFENSE = 1`.

## How the tweaks change play

Each figure is from 800 AI-vs-AI games: 400 seeds, each played from both
sides. The same seeds were used for the old and new rules.

| Match-up | Old rules | New rules |
|---|---|---|
| Medium vs Easy | Medium 83% | Medium 82% |
| Hard vs Medium | Hard 65% | Hard 62% |
| Hard vs Easy | Hard 81% | Hard 84% |

| Game flow (average over all match-ups) | Old rules | New rules |
|---|---|---|
| Game length | 40 turns | 39 turns |
| Games where radiation destroyed columns | 8% | 14% |
| Games with at least one fatigue drop | — | 33% |

What I take from this:

- **The gaps barely moved.** Hard vs medium dropped about 3 points. That is
  at the edge of the noise (about ±2.4 points at 95% confidence over 800
  games). It could also be that hard's weights were tuned under the old
  rules. Hard vs easy rose about the same amount.
- **Radiation now comes more often.** Missed shots used to keep the clock
  from running out, and now they don't. Smaller sight probably adds to this,
  since units find each other later.
- **Fatigue works as a late-game stalemate breaker.** It strikes in about a
  third of games. Of 367 fatigue drops in a separate 600-game sample, only 1
  came before the first hit of the game. Half came after turn 40.
- **Games are about the same length.** The extra attack value from fatigue
  is offset by units seeing less.

**A correction to REPORT4.** That report said hard beats medium 66%, good
to about ±3 points. With the same code, a run on 300 games gave 60%, and the
800-game run above gave 65%. The computer's choices depend slightly on the
order in which Python stores its units, which differs between runs, so
repeat runs don't match exactly. The ±3 points in REPORT4 was one standard
error, and the true 95% range was closer to ±5. I've used 800 games here to
tighten it.

## Testing

- **46 unit tests**, all passing. New and changed tests cover:
  - a ranged hit resetting the count, and a miss not resetting it
  - fatigue at 6 quiet turns: every defense drops by 1 to no lower than 1,
    and the event lists the units that got tired
  - fatigue lasting for the rest of the game, damage not undoing it, and a
    second drop after another 6 quiet turns once radiation has reset the
    count
  - radiation still coming at 10, alongside fatigue
- **GUI:**
  - I played quiet turns through the window until fatigue struck, and
    checked the screenshot: the yellow defense, the hover text and the panel
    line were all right.
  - The round-2 smoke test passed with no errors. It covers the start
    screen, a full game against hard, seed replay, hot seat and radiation.

## Decisions I made

1. **Fatigue is permanent.** It isn't undone when units start fighting
   again.
2. **It can strike again.** Once radiation destroys columns, the count
   restarts. Another 6 quiet turns lower defense again. Each quiet spell
   gives at most one drop.
3. **Every unit is affected,** on both sides, visible or not. Fatigue is
   public, so the computer knows your units' defense dropped too.
4. **Radiation deaths don't count as damage.** They already restart the
   count when the columns are destroyed, as before.

## Questions for you

1. **Recovery.** Should fatigue wear off once fighting resumes, for example
   when any unit takes damage? As it stands, an early fatigue drop lasts all
   game, and units with defense 1 are effectively unaffected by it.
2. **Retuning hard.** Hard's weights were tuned under the old rules. Should
   I retune them now, or wait until the rules settle?
