# How to Play Hex Battle

You command **Blue** (Player 1) against the computer's **Red** (Player 2).
Destroy every enemy unit to win.

To start the game, run `python3 -m hexbattle` from the `src` directory. See
`src/README.md` for details.

## The board

The battlefield has 11 columns of hexes, labeled **A** to **K** from left to
right. Columns alternate between 5 and 6 hexes, starting and ending with 5,
for 60 hexes in all. Rows are numbered from the top, so the top hex of the
first column is **A1**. Each hex shows its label at the top, and hovering the
mouse over a hex shows its label and any unit there below the buttons.

## Units

Each side has the same 10 units, numbered #1 to #10. A new set is
generated at random for every game. Each unit has six properties, which
always add up to 15:

| Icon | Property | Range | Meaning |
|------|----------|-------|---------|
| hearts | Health | 2–8 | Damage the unit can take. Filled hearts are left, hollow hearts are lost. At 0 the unit is destroyed. |
| crossed swords | Attack | 1–5 | How hard it hits. |
| shield | Defense | 1–5 | How well it resists hits. |
| target | Range | 0–4 | How far it can shoot in the ranged-attack phase. 0 means it cannot shoot. |
| feet | Movement | 1–4 | How many hexes it can move per turn. |
| eye | Sight | 1–5 | How far it can see. |

Only health changes during the game.

## Setup

1. A unit from your roster on the right is already selected. Click a hex in
   the **three left columns** to place it. The next unit is then selected
   automatically. You can click any roster tile to choose a different one.
2. To move a placed unit, click it, then click another hex in your zone.
   Right-click a placed unit to return it to the roster.
3. **Random placement** places all of your units at once.
4. When all 10 are placed, click **Start battle**.

Setup is blind. The computer places its units in the three right columns,
and you cannot see them.

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
- **Pinned units:** if a unit starts on, or reaches, a hex next to **two or
  more** enemy units, it can move no further except to attack one of those
  neighbors. If one of your other units destroys one of those enemies, the
  unit may be free to move again.
- **Ambush:** a path is planned using only the enemies you can see. If an
  enemy hidden in the fog turns out to pin your unit partway along the path,
  the unit stops there. The log reports when this happens.
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
- Click **End turn** when you are done. The computer then plays its turn.

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

## Winning

- You win when every enemy unit is destroyed, and lose when all of yours are.
- If the last two units destroy each other in a battle, the game is a
  **draw**.
- If both players go a full turn each without moving or attacking, the game
  is a **draw**.

When the game ends, the whole board is revealed. Click **New game** to play
again.
