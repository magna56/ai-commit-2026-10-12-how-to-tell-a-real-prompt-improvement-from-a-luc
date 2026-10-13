# How to Tell a Real Prompt Improvement From a Lucky Eval Run

**TL;DR:** A score you used to choose a prompt cannot also tell you how good that prompt is. Every time a score decides what to keep, some luck gets kept with it. Hold back cases the tuning loop never sees, and score them once at the end.

Published from [The AI Commit](https://theaicommit.com/#2026-10-12/code) — Evals & Reliability, 2026-10-12.

## Run

```bash
python3 code_example.py
```

## Output

```
1. THE NOISE FLOOR
   test split: 14 cases x 3 repeats at a 75% pass rate
   smallest gain it can tell from chance: 18.9 points
   cases needed to see a 5-point gain:   200
   cases needed to see a 10-point gain:  50

2. 20 ROUNDS, ONE PATCH IN FOUR IS REAL  (mean gain, points)
   keep rule                  test split  reported  final split   true
   train AND test improve             14     +13.2         +3.6   +4.2
   train AND test improve             60     +11.0         +7.7   +7.7
   train AND test improve            200     +11.1         +9.9  +10.4
   train improves                     14      +6.8         +6.6   +7.3
   'reported' is the split the keep rule read. 'final' was scored twice, ever.

3. THE SAME LOOP WHEN NO PATCH HELPS AT ALL
   keep rule                   reported  final split   true   runs claiming +5
   train AND test improve          +8.6         -0.9   -0.3                60%
   train improves                  -1.9         -2.1   -1.4                20%
   A split that gates the loop reports a gain from nothing. The final split does not.

```

## Code

See [`code_example.py`](code_example.py).
