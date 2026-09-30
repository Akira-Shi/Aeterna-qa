"""
Positive control for AETERNA-QA (2026-09-29).

Deliberately corrupts a genuinely predictive numeric feature
(education.num by default) with synthetic MCAR missingness at increasing
rates, to give the leak-free evaluator (calculate_f1_candidate, fifth
revision) a case it SHOULD recognize as worth repairing -- the
counterpart to every real-data run so far, which correctly find nothing
to fix and therefore never exercise the commit path (committed_ops
non-empty, a fill statistic or a drop_rows carried across folds) at all.

Not part of the LLM-driven pipeline -- a standalone diagnostic, same
spirit as exhaustive_search.py. For each rate in CORRUPTION_RATES it:
  1. corrupts CORRUPTION_COLUMN (replaces `rate` fraction of its values
     with NaN, chosen uniformly at random -- MCAR, the simplest case),
  2. computes the leak-free as-is baseline against the SAME fixed folds
     used throughout this project,
  3. evaluates every numeric-valid repair op (fill_mean, fill_median,
     drop_rows) with the same Nadeau-Bengio corrected paired delta and
     the SAME Bonferroni/t-distribution threshold modules.pipeline itself
     uses (n_tests=config.MAX_ITERATIONS -- the question being asked is
     "would the real deployed pipeline, at its real threshold, actually
     commit this repair", not this script's own comparison count, which
     is why this differs from exhaustive_search.py's n_tests=64 choice),
  4. re-scores the baseline with that best repair placed in committed_ops
     (non-empty) and checks that the test-fold size hasn't shrunk -- this
     is the first place in the whole project committed_ops is ever
     non-empty, so it's the first real (not just code-reviewed) exercise
     of the fifth-revision committed-operations leak fix.

fill_unknown and clip_outliers are deliberately excluded from
NUMERIC_REPAIR_OPS: fill_unknown would coerce the column to object/mixed
dtype (a string "Unknown" mixed with floats), which get_dummies would
then one-hot-encode per unique numeric value -- not a sane repair for a
continuous column, and not what's being tested here. clip_outliers
doesn't touch missingness at all.

CORRUPTION_SEED is separate from config.RANDOM_STATE: it controls WHICH
rows get corrupted, not model or fold randomness, so the corruption
pattern doesn't change if config.RANDOM_STATE is ever revisited.

Usage: python -m modules.positive_control
"""
import numpy as np
import pandas as pd

from . import config
from .evaluator import (
    load_raw_dataset, make_fixed_folds, calculate_f1_candidate,
    paired_delta_corrected, commit_threshold,
)

CORRUPTION_COLUMN = "education.num"  # numeric, genuinely predictive -- see Documentation.md
CORRUPTION_RATES = [0.10, 0.20, 0.30]
NUMERIC_REPAIR_OPS = ["fill_mean", "fill_median", "drop_rows"]
CORRUPTION_SEED = 20260929


def corrupt(raw_df: pd.DataFrame, column: str, rate: float, seed: int = CORRUPTION_SEED) -> pd.DataFrame:
    """Return a copy of raw_df with `rate` fraction of `column`'s values
    (MCAR, chosen uniformly at random) replaced with NaN. Row IDs are
    preserved so the project's fixed folds still apply unchanged."""
    rng = np.random.RandomState(seed)
    df = raw_df.copy()
    n_corrupt = int(round(rate * len(df)))
    corrupt_positions = rng.choice(len(df), size=n_corrupt, replace=False)
    corrupt_index = df.index[corrupt_positions]
    df.loc[corrupt_index, column] = np.nan
    return df


def run(rates=None) -> None:
    rates = rates if rates is not None else CORRUPTION_RATES
    raw_df = load_raw_dataset()
    # Diagnostic sweep config, same tractability tradeoff exhaustive_search.py
    # makes and documents: 5-fold x 1-repeat here, not the full repeated CV
    # config.CV_FOLDS x config.CV_REPEATS -- a ranking sweep to find where
    # the threshold gets cleared, not the final calibrated number. Whatever
    # rate/op looks like it should commit here should be re-checked by
    # actually running modules.pipeline against a corrupted dataset before
    # treating it as final (the real pipeline still uses the full repeated
    # CV for its own accept/commit decisions).
    folds = make_fixed_folds(raw_df, n_splits=5, n_repeats=1)
    raw_test_size = float(np.mean([len(idx) for _, idx in folds]))
    n_tests = config.MAX_ITERATIONS  # same scope as modules.pipeline's own threshold -- see module docstring

    print(f"Positive control: corrupting '{CORRUPTION_COLUMN}' (MCAR) at "
          f"{[f'{r:.0%}' for r in rates]}, evaluated against the same fixed "
          f"{config.CV_FOLDS}-fold x {config.CV_REPEATS}-repeat folds and the same "
          f"Nadeau-Bengio + t-distribution + Bonferroni(n_tests={n_tests}) threshold as "
          f"modules.pipeline.\n")

    results = []
    for rate in rates:
        corrupted_df = corrupt(raw_df, CORRUPTION_COLUMN, rate)
        baseline = calculate_f1_candidate(corrupted_df, folds)
        n_corrupt = int(round(rate * len(raw_df)))
        print(f"--- Corruption rate {rate:.0%} ({n_corrupt} of {len(raw_df)} rows) ---", flush=True)
        print(f"As-is (corrupted) baseline F1: {baseline['mean']:.4f} +/- {baseline['std']:.4f}", flush=True)

        best_single = None
        for op in NUMERIC_REPAIR_OPS:
            candidate = calculate_f1_candidate(corrupted_df, folds, candidate_ops={CORRUPTION_COLUMN: op})
            stats = paired_delta_corrected(baseline["scores"], candidate["scores"], candidate["n_train"], candidate["n_test"])
            threshold = commit_threshold(stats["se_delta"], stats["dof"], n_tests)
            clears = stats["mean_delta"] >= threshold
            print(f"  {op:<12} delta={stats['mean_delta']:+.4f} se={stats['se_delta']:.4f} "
                  f"threshold={threshold:.4f} clears={'YES' if clears else 'no'}")
            row = {
                "rate": rate, "op": op, "delta": stats["mean_delta"], "se": stats["se_delta"],
                "threshold": threshold, "clears": clears, "baseline_f1": baseline["mean"],
                "candidate_f1": candidate["mean"],
            }
            results.append(row)
            if best_single is None or stats["mean_delta"] > best_single["delta"]:
                best_single = row

        if best_single is not None:
            committed_ops = {CORRUPTION_COLUMN: best_single["op"]}
            committed = calculate_f1_candidate(corrupted_df, folds, committed_ops=committed_ops)
            print(f"  [leak-fix check] with '{best_single['op']}' placed in committed_ops (non-empty for "
                  f"the first time in this project), re-scored F1={committed['mean']:.4f}, "
                  f"n_test={committed['n_test']:.2f} (raw per-fold test size is {raw_test_size:.2f} -- "
                  f"these must match, or the committed-operations leak is back).")
            if abs(committed["n_test"] - raw_test_size) > 1e-6:
                print(f"  *** LEAK DETECTED: committed n_test ({committed['n_test']:.2f}) != raw fold "
                      f"test size ({raw_test_size:.2f}) ***")
            else:
                print(f"  Leak check passed: test-fold size is unchanged with a committed operation in place.", flush=True)
        print()

    print("=== Summary ===", flush=True)
    print(f"{'rate':>6}{'op':>14}{'delta':>10}{'threshold':>12}{'clears?':>9}", flush=True)
    for r in results:
        print(f"{r['rate']:>6.0%}{r['op']:>14}{r['delta']:>+10.4f}{r['threshold']:>12.4f}{'YES' if r['clears'] else 'no':>9}", flush=True)

    any_clear = any(r["clears"] for r in results)
    if any_clear:
        first_clear_rate = min(r["rate"] for r in results if r["clears"])
        print(f"\nAt least one repair clears the corrected threshold, first at corruption rate "
              f"{first_clear_rate:.0%} -- the loop's threshold is reachable by a real effect of known "
              f"size, not just impossible to clear in principle.")
    else:
        print(f"\nNo repair clears the corrected threshold at any tested rate -- either this corruption "
              f"isn't strong enough yet (try a higher rate or a stronger column, e.g. 'age'), or the "
              f"threshold is stricter than intended. Escalate the corruption rate before concluding the "
              f"threshold itself is the problem.")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        for op in NUMERIC_REPAIR_OPS:
            op_results = [r for r in results if r["op"] == op]
            rates = [r["rate"] * 100 for r in op_results]
            deltas = [r["delta"] for r in op_results]
            ax.plot(rates, deltas, marker="o", label=f"{op} (paired delta)")
        threshold_rates = [r["rate"] * 100 for r in results if r["op"] == NUMERIC_REPAIR_OPS[0]]
        threshold_vals = [r["threshold"] for r in results if r["op"] == NUMERIC_REPAIR_OPS[0]]
        ax.plot(threshold_rates, threshold_vals, marker="x", linestyle="--", color="black", label="commit threshold")
        ax.axhline(0, color="gray", linewidth=0.8)
        ax.set_xlabel("Corruption rate (%)")
        ax.set_ylabel("Paired F1 delta vs. corrupted baseline")
        ax.set_title(f"Positive control: repairing synthetic '{CORRUPTION_COLUMN}' missingness")
        ax.legend()
        fig.tight_layout()
        out_path = config.AETERNA_ROOT.parent / "Documents" / "positive_control_results.png"
        fig.savefig(out_path, dpi=150)
        print(f"\nChart saved to: {out_path}", flush=True)
    except ImportError:
        print("\n(matplotlib not installed -- skipping chart; the numeric results above are complete on their own)", flush=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run(rates=[float(sys.argv[1])])
    else:
        run()
