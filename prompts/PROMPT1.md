# Goal: write a Linux-native GUI turn-based war game.

## Overview

The game is played on a hex grid, alternating 5 and 6 hexes high (5 at
the ends) in each column and 11 columns wide.  Each player starts with
10 units, the skills of which vary from game to game.  With Player 1
moving first, players take turns moving their units and then choosing
where to attack.  Play continues until all of one side's units are
eliminated.


## Details

### Hex Grid

Each hex has up to 6 neighbors depending on whether it is on the edge
or not.  Given that you are at x, here is a diagram of hexes which are
distance 1 away and 2 away.


                        2   
                     2     2
                  2     1     2
                     1     1
                  2     x     2
                     1     1
                  2     1     2
                     2     2
                        2


### Units

Each unit has 6 properties:

| property | values | icon |
|----------|--------|------|
| health   | 2-8 | hearts              | 
| attack   | 1-5 | two crossing swords |
| defense  | 1-5 | a shield            |
| range    | 0-4 | a target            |
| movement | 1-4 | feet                |
| sight    | 1-5 | an eye              |

All of the properties except health are fixed.  During battles, health
drops.  Once health drops to 0, that unit is killed and removed from
play.

I imagine that the units are represented by square tiles that fit in
a hex.  There are hearts on the bottom of the tile to represent health
left.  Then the five fixed values are above, each next to its icon (I
have given possible icons above).

In each game, both sides start with 10 units.  The units are randomly
generated at the beginning of the game with values in the above
ranges and the sum of the six values being 15.  To start, have every
combination that adds up to 15 be equally likely.  As we play the
game, we will likely change this.  For balance, each side
starts with the same set of 10 units.

### Initialization

After the units are selected, each player places their 10 units in the
three columns on the left (for Player 1) or the right (for Player 2).
The middle 5 columns are not available during initialization.

The setup is done blind.  You set your units without knowledge of what
the opponent has done.

### Fog of War

You can only see hexes that are within the sight distance of your
remaining units.  Note that each unit has its own sight distance.  The
other hexes are grayed out.  The fog of war is collective among your
units: the union of the areas each unit can see.   

During initialization, fog of war does not apply.  You have visibility
to your three columns.  Once all units on both sides have been placed,
fog of war starts.

### Movement

When a unit moves, it can move up to its movement amount along a path to
the target hex.  The path must satisfy the following rules:

- All hexes, including the target hex, on the movement path are
  visible to your units at the time when the move starts.  
  
- It cannot move into or through a hex containing another of your units.

- It cannot move through a hex containing an opponent unit; it may
  end its move on a hex containing an opponent unit, which initiates a
  battle.

- If you start on or move to a hex with two or more neighboring hexes
  containing opponent units, you cannot move to an empty hex.  Either
  your movement ends there or you initiate a battle with a neighboring
  opponent by moving onto that hex.

If you start your turn next to two or more opponents, your options are to stay
put or attack a neighbor.  However, if another unit on your side kills
one of these neighbors, you may be freed up to move.  

### Battle

Damage (health reduction) in a single attack is probabilistic and
depends on the attacker's attack value minus the defender's defense
value according to this chart.

| attack - defense   | 0    | 1   | 2   | 3   | 4   |
|--------------------|------|-----|-----|-----|-----|
|      +4            | 20%  | 20% | 20% | 20% | 20% |
|      +3            | 25%  | 25% | 25% | 25% |     |
|      +2            | 34%  | 33% | 33% |     |     |
|      +1            | 50%  | 50% |     |     |     |
|      0             | 67%  | 33% |     |     |     |
|      -1            | 75%  | 25% |     |     |     |
|      -2            | 80%  | 20% |     |     |     |
|      -3            | 84%  | 16% |     |     |     |
|      -4            | 86%  | 14% |     |     |     |


When one player moves a unit into the hex occupied by the opponent, a
battle ensues.  In a battle, the units attack each other until one (or
both) is eliminated.  They simultaneously perform a single attack on
the other, the health of each is reduced, and they continue until one
or both go to zero health and are removed from the board.  Any
surviving unit ends in that hex.

### Turn Sequence

Players alternate turns.  Each turn consists of two phases: movement
and ranged attack.

1. Movement

In the movement phase, the player selects their units in any order.
When selected, the hexes they are allowed to move to should be
highlighted and the player selects one.  If they select a hex with an
opponent, a battle takes place and is resolved before any other unit
moves.  Note that movement is all that matters here; a unit's range
does not affect movement or whether it is allowed to start a battle.

Units are not required to move their full movement distance.  However,
once they do move, they cannot move again in this turn.  Also, units
are not required to move at all.  There should be an "end movement"
button to allow the player to end the movement phase.

Once a unit moves, the fog of war shifts.  New hexes may be visible
and old hexes might now be obscured.  This might mean that paths for
other units that had been available might now be unavailable.

2. Ranged Attack

Once all of the movement is done, any unit with a range greater than
zero, whether it moved or not, can perform one attack on an opponent
unit within its range.  Click on the unit, the possible targets should
become highlighted, and click on a target.  The target must be
visible under the fog of war rules, but that visibility might come from
another unit on your side.  Once the attack has been chosen, use the
above chart to determine how much health is removed.  There is no
counter-attack.

The "end movement" button should become "end turn".  

### Termination

Play continues until all of one player's units are eliminated.
Draws are possible when the last two units battle and both are
killed in that battle.  

The game also ends in draw if for both players make no moves
and no attacks in successive turns. 


## Source Code

- All source code goes in the src directory.
- You may choose among C, Python, Rust, and Go (or JavaScript for
  the interim web version).
- You may not stage or commit any files.  I will always review and
  commit. 

## GUI

Ultimately, I want this to be a Linux-native program.  You may choose a
graphics library so long as it is supported by Ubuntu.  Give me
specific "sudo apt install" commands if necessary.

Initially, this can be a web app which plays in Firefox if that makes
things easier and transition to native Linux later.

## Computer Player

In the first version, let's only support human (Player 1) vs computer
(Player 2).  The computer AI does not need to be great.  Also, at
first, it can cheat and look at the opponent's position.  However, the
fog of war does apply to its allowed moves.  I expect that writing a
good AI that does not cheat will be an ongoing project.  I want to get
the game mechanics and graphics set up first.


## Deliverable

- Source code for the game in src along with instructions on how
  to build and run it.

- Instructions for how to play the game in RULES.md.

- A report with details on the project and any questions for me in REPORT.md.