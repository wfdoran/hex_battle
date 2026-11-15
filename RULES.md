# How to Play Hex Battle

Two armies, **Blue** (Player 1) and **Red** (Player 2), fight on a hex board
under fog of war. Destroy every enemy unit to win.

To start the game, run `python3 -m hexbattle` from the `src` directory. See
`src/README.md` for details.

## Start screen

- **Human vs Computer:** you play Blue, and the computer plays Red. Choose
  the computer's level:
  - **Easy** plays loosely and leaves some units idle.
  - **Medium** works out battle odds and only attacks when it expects to win.
  - **Hard** also avoids danger, surrounds enemies to cut off their retreat,
    and focuses its fire.

  For now, the computer knows where your units are, even in the fog, but it
  must obey the same movement and attack rules as you.
- **Human vs Human:** two players share one screen ("hot seat"). Between
  turns a hand-off screen hides the board. Each player has their own log, so
  neither sees what the other's fog of war hides.
- **Seed:** leave it blank for a new random set of units. Every game shows
  its seed in the bottom-right corner and at the top of the log. Enter that
  seed here to replay the same units.

## The board

The battlefield has 11 columns of hexes, labeled **A** to **K** from left to
right. Columns alternate between 5 and 6 hexes, starting and ending with 5,
for 60 hexes in all. Rows are numbered from the top, so the top hex of the
first column is **A1**. Each hex shows its label at the top, and hovering the
mouse over a hex shows its label and any unit there below the buttons.

## Units

Each side has the same 10 units, numbered #1 to #10. A new set is
generated at random for every game. Each unit has six properties, which
always add up to 15, and at most 4 of the 10 units have range 0:

| Icon | Property | Range | Meaning |
|------|----------|-------|---------|
| hearts | Health | 4–8 | Damage the unit can take. Filled hearts are left, hollow hearts are lost. At 0 the unit is destroyed. |
| crossed swords | Attack | 1–5 | How hard it hits. |
| shield | Defense | 1–5 | How well it resists hits. |
| target | Range | 0–4 | How far it can shoot in the ranged-attack phase. 0 means it cannot shoot. |
| feet | Movement | 1–4 | How many hexes it can move per turn. |
| eye | Sight | 1–4 | How far it can see. |

Only health changes during the game.

## Setup

1. A unit from your roster on the right is already selected. Click a hex in
   the **three left columns** to place it. The next unit is then selected
   automatically. You can click any roster tile to choose a different one.
2. To move a placed unit, click it, then click another hex in your zone.
   Right-click a placed unit to return it to the roster.
3. **Random placement** places all of your units at once.
4. When all 10 are placed, click **Start battle**.

Setup is blind. Red places its units in the three right columns, and Blue
cannot see them. In a hot-seat game, Blue places first and clicks **Done
placing**. The screen is then handed to Red, who places and clicks **Start
battle**.

## Fog of war

You can see only the hexes within the **sight** distance of at least one of
your living units. Everything else is gray, and enemy units there are
hidden. Your view changes as your units move or are destroyed.

## Turns

Blue moves first. Each turn has two phases.

### 1. Movement

- Click one of your units. The hexes it can move to turn **green**, and
  enemies it can attack turn **red**. Click one to move there.
- Each unit moves at most once per turn, up to its movement distance. Moving
  is optional. Units that have already moved are drawn faded.
- Every hex on the path must be visible when the move starts. A unit cannot
  move into or through your own units. It cannot move *through* an enemy,
  but it can move *onto* an enemy, which starts a battle (see below).
- **Zone of control:** every hex next to an enemy unit is in that enemy's
  zone of control. A unit may not step from one hex in an enemy zone of
  control to another, even if a different enemy is next to each. Attacking
  is always allowed. So a unit next to an enemy can attack, or retreat to a
  hex that isn't next to any enemy, but it can't slide along the enemy line
  or slip past it. A unit that steps away can step back in later on the same
  move, as long as each step follows the rule.
- **Ambush:** a path is planned using only the enemies you can see. If an
  enemy hidden in the fog turns out to make a step break the zone-of-control
  rule, the unit stops before that step. The log reports when this happens.
- Moving changes what you can see, so moves that were available to other
  units may no longer be, and new ones may open up.
- Click **End movement** when you are done.

### 2. Ranged attacks

- Any of your units with range 1 or more can fire once at an enemy within
  its range, whether or not it moved this turn.
- The target must be visible, but the unit firing doesn't have to see it
  itself. Another of your units can be the spotter.
- Click a unit that can fire. Its targets are outlined in red. Click one.
  Units that cannot fire are drawn faded.
- A ranged attack is a single attack, and the target does not fire back.
- Click **End turn** when you are done. The other side then plays its turn.
  In a hot-seat game, a hand-off screen comes up first. The next player
  clicks it when the other player has looked away. If any of their units
  were destroyed since their last turn, a pop-up lists them and how they
  were lost.

## Combat

Every attack compares the attacker's **attack** with the defender's
**defense** and rolls damage from this table:

| attack − defense | 0 damage | 1 | 2 | 3 | 4 |
|------------------|----------|-----|-----|-----|-----|
| +4 | 20% | 20% | 20% | 20% | 20% |
| +3 | 25% | 25% | 25% | 25% | |
| +2 | 34% | 33% | 33% | | |
| +1 | 50% | 50% | | | |
| 0  | 67% | 33% | | | |
| −1 | 75% | 25% | | | |
| −2 | 80% | 20% | | | |
| −3 | 84% | 16% | | | |
| −4 | 86% | 14% | | | |

**Battles.** Moving a unit onto an enemy starts a battle. Both units attack
each other at the same time, round after round, until one or both are
destroyed. A surviving attacker takes over the hex, and a surviving defender
stays where it is. The log shows the damage dealt and taken in each round.

## Radiation

Long standoffs don't last. The side panel counts **turns without combat**.
A turn is one player's turn, and any battle or ranged attack resets the
count, even one that does no damage.

- After **10 turns without combat**, the two outermost columns still on the
  board become **radioactive**. They turn yellow and show the radiation
  symbol, and the side panel shows a warning.
- **Two turns later**, one turn for each player, the radioactive columns are
  destroyed, along with any units still on them. Destroyed columns are dark
  and are no longer part of the board.
- The count then starts again from zero, and the board keeps shrinking from
  both edges until somebody fights.

Get your units out of radioactive columns in time.

## Winning

- You win when every enemy unit is destroyed, and lose when all of yours
  are. The side panel shows how many units each side has left.
- If the last two units destroy each other in a battle, or radiation
  destroys everything that is left, the game is a **draw**.
- If both players go a full turn each without moving or attacking, the game
  is a **draw**.

When the game ends, the whole board is revealed. Click **New game** to play
again.
