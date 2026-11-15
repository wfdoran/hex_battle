# Hex Battle — Report 3 (response to PROMPT3.md)

## Summary

- Movement now uses the Civ I zone-of-control rule in place of the "two
  adjacent enemies" pinning rule.
- Hot-seat players get a pop-up when they take the screen, but only if one
  or more of their units were destroyed since their last turn.

Nothing has been staged or committed. `RULES.md` is updated to match.

## Answers to your notes on REPORT2

1. **Radiation timing.** Yes, it is one constant,
   `QUIET_TURNS_FOR_RADIATION = 10` in `src/hexbattle/game.py`. The warning
   delay is `RADIATION_DELAY = 2`, next to it. The side panel, log messages
   and tests all read these, so changing either number is a one-line edit.
2. **Hot-seat summary.** Done; see below.
3. **Honest AI.** Left alone until the AI prompt.
4. **Difficulty spread.** Noted: aim for gaps of roughly 80%. Not worked on
   this round, but the new tournament numbers are below as a baseline.

## Zone of control

**The rule:** a unit may not step from a hex next to an enemy to another hex
next to an enemy, whether or not it is the same enemy. Attacking (moving onto
an enemy) is always allowed.

How it plays:

- A unit next to an enemy can attack it, stay, or **retreat** to any hex not
  next to an enemy, and then keep moving.
- It can't slide sideways along an enemy line or slip through a gap between
  two enemies that are two hexes apart.
- Approaching is free. A unit can walk up to an enemy from open ground and
  attack on the same move, as before.
- The rule is checked at every step, not just the first. A unit can step
  away from an enemy and then step back in next to it (or next to another
  enemy) on the same move, since neither step goes from one zone of control
  directly to another. Civ I worked the same way.

**Fog and ambush:** as before, the move highlights are planned using only
the enemies you can see. When the move is carried out, hidden enemies count
too. If a hidden enemy makes a step illegal, the unit stops before that step,
and the log says: "An enemy hidden in the fog had it in its zone of control,
so it had to stop."

**The computer** needed no rule-specific changes, because it chooses only
from the legal moves the engine gives it. I updated the comments that talked
about pinning. Hard's bonus for surrounding an enemy still makes sense:
under zone of control, surrounding an enemy closes off the hexes it could
retreat to.

## Hot-seat loss pop-up

When a player clicks the hand-off screen to start their turn, a pop-up
appears if any of their units were destroyed since the end of their last
turn, for example:

> Since your last turn you lost 2 of your units:
>
> • Blue #3 was destroyed at H3, attacked by Red #6.
> • Blue #9 was shot at G3 by a hidden Red unit.

- It covers defending in a battle, ranged fire and radiation.
- That includes radiation that hits at the end of the player's own turn,
  since the hand-off screen comes up right away and they wouldn't see it.
- The pop-up reveals nothing the log doesn't. A shooter in the fog is a
  "hidden Red unit".
- No pop-up appears when nothing was lost, during setup, or in games
  against the computer.

## AI tournament under the new rule

Over 200 games per pairing, with the same seeds as round 2:

| Match-up | Round 2 | Round 3 |
|---|---|---|
| Medium vs Easy | Medium 73% | Medium 80%, 0.5% draws |
| Hard vs Medium | Hard 62%, 2% draws | Hard 56%, 5% draws |
| Hard vs Easy | Hard 76%, 1% draws | Hard 73%, 1% draws |

Hard lost some ground against medium. Its scoring was tuned for the old rule,
where touching one enemy didn't restrict movement. Hard vs medium games are
also longer (46 turns on average) and reach radiation more often. I've left
retuning for the AI prompt, as you asked.

## Testing

- **39 unit tests**, all passing. The pinning tests are replaced with tests
  for:
  - the moves allowed next to an enemy (attack, or step away, but not slide)
  - a full retreat
  - every step of every legal path obeying the rule, while approaching and
    attacking stay possible
  - a hidden enemy stopping a move partway
- **GUI:** I ran three scripted hot-seat games in the real window and
  checked each loss pop-up against what happened:
  - 19 pop-ups, covering battles and radiation
  - a separate direct check of the wording for shots from visible and
    hidden units
  - a game against the computer, which showed no pop-ups
  - no errors

## Decisions I made

1. **Any enemy counts, not just the one you start next to.** This follows
   your "(maybe a different opponent unit)".
2. **Checked at every step,** so stepping away and back in on one move is
   legal. The alternative, "a unit that starts next to an enemy may only end
   its move away from all enemies", is stricter. Say if you prefer it.
3. **The pop-up is hot-seat only.** Against the computer you watch its turn
   play out, and the log has the details.

## Questions for you

1. **Step away and back in.** Decision 2 lets a unit with movement 2 or more
   circle around an enemy by stepping out of its zone of control and back
   in. Keep that, or forbid ending next to an enemy after starting next to
   one (except by attacking)?
2. **Retreat from radiation.** A unit caught between an enemy and the
   radioactive edge may now be unable to escape. I think that's a fair
   consequence of the rule. Agreed?
