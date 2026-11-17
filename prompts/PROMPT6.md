
I agree with all of your decisions in the "Decisions I made" section of
REPORT5.md. 

# Questions from REPORT5.md

1. **Recovery.** Should fatigue wear off once fighting resumes, for example
   when any unit takes damage? As it stands, an early fatigue drop lasts all
   game, and units with defense 1 are effectively unaffected by it.

No.  Fatique is forever.

2. **Retuning hard.** Hard's weights were tuned under the old rules. Should
   I retune them now, or wait until the rules settle?

Not yet.  I have another set of changes in this prompt.  Let's retune after
we have have made these changes.

# Changes

## Fatique

When fatique strikes, reduce movement by 1 as well (minimum 1).

## Revised Damage Chart


| attack - defense   | 0    | 1   | 2   | 3   | 4   |
|--------------------|------|-----|-----|-----|-----|
|      +4            |      |     | 34% | 33% | 33% |
|      +3            |      | 34% | 33% | 33% |     |
|      +2            | 34%  | 33% | 33% |     |     |
|      +1            | 50%  | 50% |     |     |     |
|      0             | 67%  | 33% |     |     |     |
|      -1            | 75%  | 25% |     |     |     |
|      -2            | 80%  | 20% |     |     |     |
|      -3            | 84%  | 16% |     |     |     |
|      -4            | 86%  | 14% |     |     |     |

This should reduce the luck factor some.

