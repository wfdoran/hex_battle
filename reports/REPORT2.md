# Hex Battle — Report 2 (response to PROMPT2.md)

## Summary

Everything in PROMPT2 is implemented and tested:

- radioactive columns for stalemates
- the new unit limits
- easy, medium and hard computer levels
- human vs human (hot seat) with a start screen
- unit counts on screen
- the seed on screen

Nothing has been staged or committed. `RULES.md` and `src/README.md` are
updated to match.

## What changed

### 1. Radiation (stalemate rule)

- The side panel shows **"Turns without combat: n of 10"**. A turn is one
  player's turn. Any battle or ranged attack, hit or miss, resets the count
  to 0.
- At 10, the two outermost columns still on the board become radioactive.
  Those hexes turn yellow with a radiation trefoil, in fog as well. The side
  panel shows an orange warning with a countdown, and both logs announce it.
- After two more turns (one per player), those columns are destroyed along
  with any units on them. Destroyed columns are drawn as dark voids, can't be
  entered or seen into, and drop out of the game. Each player's log names
  the units they lost and gives only a *count* of enemy losses, so a hidden
  unit's identity isn't revealed.
- The clock then restarts, so a long standoff keeps shrinking the board, from
  11 columns to 9, 7, 5, 3 and 1. If the last column is destroyed with units
  of both sides on it, the game is a draw.
- The computer avoids radioactive hexes at every level and leaves them if it
  is standing on one.

### 2. Unit generation

- Health is now 4–8 and sight 1–4. There are 596 valid stat lines summing
  to 15, down from 1,229.
- **Range-0 cap:** each stat line is still drawn uniformly. If a roster has
  more than 4 range-0 units, the whole roster is redrawn. This keeps every
  allowed roster equally likely. About 36% of stat lines have range 0, so
  about 80% of rosters pass on the first draw.

### 3. Computer levels: easy, medium, hard

| Level | How it plays |
|---|---|
| Easy | Places units randomly. Each turn about 30% of its units sit idle. Judges fights by comparing raw stats, moves with a lot of randomness, and shoots at random targets. |
| Medium | The round-1 AI, but battle odds are now computed exactly instead of simulated. Attacks only when it expects to gain. Melee units close in, and ranged units keep their distance. |
| Hard | Weighs the expected loss from every enemy that could reach a hex next turn. Seeks out enemies it is likely to beat. Gets a bonus for joining an attack on an enemy that is already in contact, which pins it. Places ranged units only where a target is both in range and visible. Prioritizes shots that can kill a valuable unit. |

Over 200 games per pairing (100 seeds, each played from both sides):

| Match-up | Result |
|---|---|
| Medium vs Easy | Medium wins 73%, no draws |
| Hard vs Medium | Hard wins 62%, 2% draws |
| Hard vs Easy | Hard wins 76%, 1% draw |

All three levels still cheat by knowing your positions, as you asked. That
is next round's job.

I also added an exact **battle-odds calculator**. It works out win, loss
and mutual-destruction probabilities directly from the damage table, and I
checked it against 40,000 simulated battles. It is faster than simulation
and gives the same answer every time.

**Fix found while testing:** in round 1, many AI-vs-AI games ended in the
idle-turn draw, sometimes with the winning side ahead by 5 units to 1. Its
units stopped moving once no single move looked worthwhile. A human could
exploit this by passing whenever the computer had nothing obvious to do. Now
the computer never passes a whole turn when it is ahead or level on
material. When it is behind, it still accepts a draw.

### 4. Human vs human (hot seat) and the start screen

- **Start screen:**
  - Choose **Human vs Computer** or **Human vs Human**.
  - Choose the computer level. The level buttons are disabled for human vs
    human.
  - Optionally enter a seed.
  - **New game** returns to this screen, after a confirmation if a game is
    in progress.
- **Setup:** Blue places and clicks **Done placing**. A hand-off screen
  hides the board. Red clicks when ready, places, and clicks **Start
  battle**. Blue then gets the first turn, after another hand-off.
- **Turns:** each **End turn** brings up the hand-off screen ("Red's turn —
  Blue, please look away"). The board, roster, hover info and log stay
  hidden until the next player clicks.
- **No information leaks:** each player has their own log. Logs report
  only what that player could know:
  - An enemy move is reported only if it ends where you can see it.
  - Shots from the fog read "A hidden Red unit fired at …".
  - Radiation losses on the enemy side are given only as a count.

  The automated test checks that neither log ever reports the other side's
  hidden moves.

### 5. Unit counts and seed

- The side panel shows **"Blue: 7 units   Red: 6 units"**, updated after
  every action.
- Every game now has a seed, chosen at random when none is given. It is
  shown at the bottom of the side panel ("Seed: 123456") and is the first
  line of the log. Entering it on the start screen reproduces the same 10
  units. `--seed` on the command line pre-fills that box.
- Replaying a seed gives the same units and setup-zone layout. The dice only
  repeat if every action is also the same.

## Testing

- **38 unit tests**, all passing. New ones cover:
  - the radiation cycle (warning, countdown, destruction, the clock
    restarting, the next pair of columns)
  - combat resetting the clock
  - the last column being destroyed and causing a draw
  - the range-0 cap
  - the new stat limits
  - exact odds against simulation
  - complete legal games for every pairing of levels
- **GUI:** a scripted run on your display covered:
  - the start screen
  - a full human-vs-computer game on hard, with seed 4242
  - starting a new game with the same seed and confirming the same units
  - a hot-seat game: both blind placements, eight turns with hand-offs, and
    the log-leak check
  - forced radiation, to check how radioactive and destroyed columns look

  The run had no errors, and I reviewed the rendered images.

## Decisions I made

1. **"Turn" means one player's turn.** So 10 quiet turns is 5 per player,
   matching "two turns later (one by each player)".
2. **Once declared, radiation always happens.** Fighting during the two-turn
   warning doesn't cancel it. The clock restarts only after the columns are
   gone.
3. **Units may still walk into radioactive hexes during the warning.** It's
   their funeral.
4. **The idle-turn draw (both players pass) is kept** alongside radiation.
5. **Unit counts are shown for both sides,** including the enemy. You can
   deduce this from the log anyway, except for losses to radiation in the
   fog.

## Questions for you

1. **Radiation timing.** Is 10 quiet turns (5 each) right? In AI-vs-AI
   games, columns were destroyed in about a third of hard-vs-medium games.
2. **Hot-seat hand-off.** Should a player see a short summary of what
   happened to their units during the other player's turn when they take
   the screen? The log has it, but a pop-up would be harder to miss.
3. **Next AI step.** For the honest (non-cheating) AI, I plan to have it
   remember where it last saw each enemy and guess where the enemy might
   have moved. Should easy stay a cheater (it's weak anyway), or should all
   three levels go honest?
4. **Difficulty spread.** Hard beats medium 62% of the time. Is that enough
   separation, or should hard be stronger, for example with look-ahead?
