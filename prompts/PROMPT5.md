# Questions from REPORT4.md

1. **Difficulty gaps.** Would you like to reduce the luck in combat to widen
   the gaps, for example with fewer zero-damage results? Or should easy get
   weaker still?

I have a couple of tweaks below which I would like for this iteration.
Depending on how they impact game play, we may return to this option.

2. **Hard's thinking time.** It is short now. Would you accept a slower hard,
   with a "thinking…" indicator, if it played somewhat better? My tests
   suggest only small gains from more search.

Not yet.  Eventually we may add an "extreme" AI.

3. **Odds in the ranged phase.** Should hovering a target in the ranged phase
   show the chance of each damage amount, and the kill chance?

No.

# Tweaks

1. Sight paramter is now 1-3.

2. Radation kicks in after 10 turns where no unit takes damage.

3. Big Change: After 6 turns where no unit takes damage, all units defense
   values drop by 1 ("due to fatigue") to a minimum value of 1.

