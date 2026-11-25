I agree with your decisions in REPORT7.md

# Questions from REPORT7.md


1. **Enemy x+1.** Is it OK that x+1 on a visible enemy reveals it hasn't
   moved since its last turn, even if it was in the fog then? The
   alternative is to show x+1 only on your own units.

I agree with this.

2. **Setup as a turn.** Should units count as having stayed put during
   setup, so they can be anchored on their first turn? That would make the
   opening favor the side that sits back and shoots.

No setup does not count as a turn.


# This iteration

You said you could evaluate different damage charts.  Below are three.
Evaluate all three.  Pick the best one, then tune the AI to these values.


## Plan A

| attack - defense   | 0    | 1   | 2   | 3   | 4   |
|--------------------|------|-----|-----|-----|-----|
|      +4            |      |     | 34% | 33% | 33% |
|      +3            |      | 34% | 33% | 33% |     |
|      +2            | 34%  | 33% | 33% |     |     |
|      +1            | 50%  | 50% |     |     |     |
|      0             | 60%  | 40% |     |     |     |
|      -1            | 70%  | 30% |     |     |     |
|      -2            | 75%  | 25% |     |     |     |
|      -3            | 80%  | 20% |     |     |     |
|      -4            | 85%  | 15% |     |     |     |



## Plan B

| attack - defense   | 0    | 1   | 2   | 3   | 4   |
|--------------------|------|-----|-----|-----|-----|
|      +4            |      |     | 25% | 50% | 25% |
|      +3            |      | 20% | 60% | 30% |     |
|      +2            | 10%  | 75% | 15% |     |     |
|      +1            | 30%  | 70% |     |     |     |
|      0             | 50%  | 50% |     |     |     |
|      -1            | 60%  | 40% |     |     |     |
|      -2            | 70%  | 30% |     |     |     |
|      -3            | 80%  | 20% |     |     |     |
|      -4            | 85%  | 15% |     |     |     |

## Plan C (the current)

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
