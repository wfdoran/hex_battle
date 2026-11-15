# Questions from REPORT2.md

1. **Radiation timing.** Is 10 quiet turns (5 each) right? In AI-vs-AI
   games, columns were destroyed in about a third of hard-vs-medium games.

10 seems like a good number for now.  I assume it is a variable which
we can easily change later if we want to.

2. **Hot-seat hand-off.** Should a player see a short summary of what
   happened to their units during the other player's turn when they take
   the screen? The log has it, but a pop-up would be harder to miss.

This is a good idea, but only if one or more of their units were killed.

3. **Next AI step.** For the honest (non-cheating) AI, I plan to have it
   remember where it last saw each enemy and guess where the enemy might
   have moved. Should easy stay a cheater (it's weak anyway), or should all
   three levels go honest?

Don't worry about this yet.  We will have an AI prompt soon.

4. **Difficulty spread.** Hard beats medium 62% of the time. Is that enough
   separation, or should hard be stronger, for example with look-ahead?

There is randomness in the game.  So, the strong AI should lose
sometimes.  I would say the gaps should be roughly 80%; moving up in
AI should feel harder.  But don't worry about this in this iteration.

# Movement Rule Change

The change I want in this iteration is the movement rule.

I want to switch to the Civ I Zone of Control rule:

  You may not move a unit which adjacent to an opponent to
  a new hex were it would also be adjacent to an opponent (maybe
  a different opponent unit).

This would allow for retreating.

