# From PROMPT1.md

## Decisions

I read over all of your decisions.  I am happy with all of them.  In
particular the decision on ambush is good.  I had not thought of that
edge case.


## Questions

1. **Stalemate loophole.** The idle-turn draw can be dodged by moving one
   unit back and forth forever. Do you want a hard turn limit, or a "no
   battle or hit in N turns" rule?

How about this: after N (say N = 10) turns with no battles or ranged
attacks (successful or not), declare the two outer most columns
"radioactive" (find some fun way to mark this on the field).  Then two
turns later (one by each player), the radioactive columns and any units
on them are removed.  And the clock restarts.  


2. **Ambush.** Is the interpretation in decision 3 what you intended? The
   alternative is to count hidden enemies when showing legal moves, which
   gives away where they are.

I like your decision.

3. **Battle presentation.** Battles are currently shown as an orange flash
   plus a round-by-round line in the log. Would you like a pop-up that plays
   out each round?

This is good for now.

4. **Unit balance.** Many uniformly generated units end up with range 0 or
   with low health. Which way would you like to take generation when you
   revisit it, for example a minimum health, or weighting?

Changes to make:
- health: 4-8
- sight: 1-4
- cap the number of units with range 0 at 4 of 10. 


5. **Next steps for the AI.** Should the next AI drop the cheating first, or
   play stronger first? Making it honest means it has to keep track of
   enemies it last saw.

I would like to have an easy, medium and hard AI.  If you have ideas
for how to do this, please implement it.  Let's wait one more iteration
to drop the cheating.  

6. **Human vs. human.** The rules engine already supports two human
   players. Do you want a hot-seat mode, with a screen hiding the board
   between turns?

Yes, add human vs human.  We will need an initial splash screen to
select human-vs-human or human-vs-computer and to select the AI level.


# Other Changes

- Somewhere in the interface show the current number of units each
  side has.

- Show the seed in case you want to replay the set of units.  Maybe it
  is already in the log.


# Report

For each prompts/PROMPTx.md, but your response in reports/REPORTx.md


