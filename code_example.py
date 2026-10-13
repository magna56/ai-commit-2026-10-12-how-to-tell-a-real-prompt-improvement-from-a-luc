"""Is the gain your prompt hill-climb reports real, or selected-for luck?

A hill-climb proposes one prompt patch per round, re-runs the eval, and keeps the
patch if the score went up. A common keep rule is "train AND test both improved".
That rule reads the test split every round, so the test score of the surviving
prompt is the best of many noisy draws, not one honest draw.

This file has two liftable pieces:
  noise_floor(...)  -> the smallest gain your eval can tell from chance
  hillclimb(...)    -> the loop, with a third split that is scored exactly twice

Point N_TRAIN / N_TEST / REPEATS at your own eval and read the last column.

Run: python3 code_example.py        (stdlib only, no network, no API key)
"""

import math
import random

# --- your eval. Defaults are the size of the worked example in the playbook ----
N_TRAIN = 30      # cases the optimizer may read transcripts for
N_TEST = 14       # cases the keep rule consults every round
N_FINAL = 14      # cases scored once before round 1 and once after the last round
REPEATS = 3       # runs per case. Raise this and the noise floor drops.
ROUNDS = 20       # prompt patches tried. More rounds = more chances to get lucky.
BASELINE = 0.75   # pass rate of the prompt you start from
TRIALS = 600      # simulated hill-climbs per row. Only affects smoothness.

# --- what a patch really does, hidden from the loop ---------------------------
REAL_SHARE = 0.25   # one patch in four fixes a root cause...
REAL_GAIN = 0.04    # ...and is worth 4 points everywhere, production included
HARM_SHARE = 0.20   # some patches quietly cost 2 points
TRAIN_ONLY = 0.03   # every patch is written from train failures, so it helps train


def noise_floor(pass_rate, n_cases, repeats=1):
    """Smallest before/after difference worth acting on, as a fraction.

    Two scores, each a mean of n pass/fail runs, differ by chance with a standard
    error of sqrt(2*p*(1-p)/n). Twice that is the usual bar. Repeats on one case
    are not fully independent, so this is the optimistic end of the range.
    """
    n = n_cases * repeats
    return 2 * math.sqrt(2 * pass_rate * (1 - pass_rate) / n)


def cases_needed(pass_rate, min_gain, repeats=1):
    """Cases a split needs before a gain of `min_gain` clears the noise floor."""
    return math.ceil(8 * pass_rate * (1 - pass_rate) / (min_gain ** 2) / repeats)


def run_eval(rng, pass_rate, n_cases):
    """One eval run: n_cases x REPEATS model calls, each graded pass or fail."""
    n = n_cases * REPEATS
    p = min(1.0, max(0.0, pass_rate))
    return sum(rng.random() < p for _ in range(n)) / n


def hillclimb(rng, gate, n_test=N_TEST, real_share=REAL_SHARE):
    """One full hill-climb. Returns (gain on test, gain on final, true gain).

    gate="test"  -> keep a patch only if train AND test both improved
    gate="train" -> keep a patch if train improved; test is not consulted
    """
    true = BASELINE          # what production would see. The loop never sees this.
    train_bonus = 0.0        # accumulated gains that exist only on the train cases
    train = run_eval(rng, true, N_TRAIN)
    test = test_start = run_eval(rng, true, n_test)
    final_start = run_eval(rng, true, N_FINAL)      # scored once, before round 1

    for _ in range(ROUNDS):
        roll = rng.random()
        effect = REAL_GAIN if roll < real_share else (-0.02 if roll > 1 - HARM_SHARE else 0.0)
        new_train = run_eval(rng, true + effect + train_bonus + TRAIN_ONLY, N_TRAIN)
        new_test = run_eval(rng, true + effect, n_test)
        # The decision below is the whole article. Any split named in it is spent.
        keep = new_train > train and (gate == "train" or new_test > test)
        if keep:
            true += effect
            train_bonus += TRAIN_ONLY
            train, test = new_train, new_test

    if gate == "train":      # test was never read by the loop: score it now, once
        test = run_eval(rng, true, n_test)
    final_end = run_eval(rng, true, N_FINAL)        # scored once, after the last round
    return test - test_start, final_end - final_start, true - BASELINE


def summarize(gate, n_test=N_TEST, real_share=REAL_SHARE, seed=7):
    rng = random.Random(seed)
    runs = [hillclimb(rng, gate, n_test, real_share) for _ in range(TRIALS)]
    mean = lambda i: 100 * sum(r[i] for r in runs) / len(runs)
    fooled = 100 * sum(r[0] >= 0.05 for r in runs) / len(runs)
    return mean(0), mean(1), mean(2), fooled


def main():
    floor = noise_floor(BASELINE, N_TEST, REPEATS)
    print("1. THE NOISE FLOOR")
    print(f"   test split: {N_TEST} cases x {REPEATS} repeats at a {BASELINE:.0%} pass rate")
    print(f"   smallest gain it can tell from chance: {100 * floor:.1f} points")
    print(f"   cases needed to see a 5-point gain:   {cases_needed(BASELINE, 0.05, REPEATS)}")
    print(f"   cases needed to see a 10-point gain:  {cases_needed(BASELINE, 0.10, REPEATS)}")

    head = f"   {'keep rule':<26}{'test split':>11}{'reported':>10}{'final split':>13}{'true':>7}"
    print(f"\n2. {ROUNDS} ROUNDS, ONE PATCH IN FOUR IS REAL  (mean gain, points)")
    print(head)
    for label, gate, n in (("train AND test improve", "test", 14),
                           ("train AND test improve", "test", 60),
                           ("train AND test improve", "test", 200),
                           ("train improves", "train", 14)):
        rep, fin, tru, _ = summarize(gate, n)
        print(f"   {label:<26}{n:>11}{rep:>+10.1f}{fin:>+13.1f}{tru:>+7.1f}")
    print("   'reported' is the split the keep rule read. 'final' was scored twice, ever.")

    print(f"\n3. THE SAME LOOP WHEN NO PATCH HELPS AT ALL")
    print(f"   {'keep rule':<26}{'reported':>10}{'final split':>13}{'true':>7}{'runs claiming +5':>19}")
    for label, gate in (("train AND test improve", "test"), ("train improves", "train")):
        rep, fin, tru, fooled = summarize(gate, 14, real_share=0.0)
        print(f"   {label:<26}{rep:>+10.1f}{fin:>+13.1f}{tru:>+7.1f}{fooled:>18.0f}%")
    print("   A split that gates the loop reports a gain from nothing. The final split does not.")


if __name__ == "__main__":
    main()
