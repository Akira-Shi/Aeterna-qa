"""
Exhaustive ground-truth search over the (column, operation) space (2026-09-29,
updated same night to match pipeline.py's third revision -- fit-on-train/
apply-to-test evaluation and the Nadeau-Bengio corrected SE + t-distribution
threshold, so this script and modules.pipeline are directly comparable).

Not part of the LLM-driven pipeline -- a diagnostic/validation script. It
enumerates every combination of {none, fill_mode, drop_rows, fill_unknown}
for the 3 real-missingness columns (4^3 = 64 combinations, including doing
nothing) using calculate_f1_candidate (the SAME fit-on-train, fold-safe
evaluation the pipeline uses) and reports every combination's measured
effect vs. the true as-is baseline, ranked, with a Bonferroni correction
sized to the true number of comparisons made here (64), not the pipeline's
MAX_ITERATIONS -- the two scripts' printed threshold values are correctly
on different scales for that reason (12 look-backs vs. 64 combinations);
compare outcomes (does anything commit / clear), not the raw numbers.

Matches pipeline.py's fifth revision: there is no "committed" dataframe
here at all (this script has no notion of a committed baseline -- every
combo is evaluated independently against the true as-is baseline), so it
never had the v4 committed-operations leak pipeline.py had. It's updated
only because evaluator.calculate_f1_candidate's signature changed to
(raw_df, folds, committed_ops=None, candidate_ops=None) -- calls here
just drop the old redundant duplicate raw_df argument and omit
committed_ops (defaults to {}).

Diagnostic ranking sweep uses 5 folds / 1 repeat (not the full repeated
CV config.CV_REPEATS) purely to keep 64 combinations tractable to run --
the pipeline itself still uses the full repeated CV for actual
accept/commit decisions, so treat this script's numbers as a ranking
sweep, not the final calibrated comparison.

CHECKPOINTED: results are written to logs/exhaustive_search_results.json
as each combo finishes. Re-running this script resumes from whatever's
already in that file -- run it repeatedly until it prints "ALL
COMBINATIONS DONE". Delete that file first to force a full recompute
after a methodology change (e.g. this one).

Usage: python -m modules.exhaustive_search
"""
import itertools
import json
import time
from pathlib import Path

from . import config
from .evaluator import load_raw_dataset, make_fixed_folds, calculate_f1_candidate, paired_delta_corrected, commit_threshold

CATEGORICAL_OPS = ["none", "fill_mode", "drop_rows", "fill_unknown"]
RESULTS_PATH = Path(__file__).resolve().parent.parent / "logs" / "exhaustive_search_results.json"
TIME_BUDGET_SECONDS = 100


def run() -> None:
    raw_df = load_raw_dataset()
    folds = make_fixed_folds(raw_df, n_splits=5, n_repeats=1)
    columns = config.KNOWN_MISSING_COLUMNS

    baseline = calculate_f1_candidate(raw_df, folds)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    done: dict[str, dict] = {}
    if RESULTS_PATH.exists():
        done = json.loads(RESULTS_PATH.read_text())

    combos = list(itertools.product(CATEGORICAL_OPS, repeat=len(columns)))
    all_combo_dicts = [dict(zip(columns, combo)) for combo in combos]
    n_total = len(all_combo_dicts)

    t_start = time.time()
    newly_done = 0
    for combo_dict in all_combo_dicts:
        key = json.dumps(combo_dict, sort_keys=True)
        if key in done:
            continue
        if time.time() - t_start > TIME_BUDGET_SECONDS:
            break
        candidate_ops = {c: op for c, op in combo_dict.items() if op != "none"}
        candidate = calculate_f1_candidate(raw_df, folds, candidate_ops=candidate_ops)
        stats = paired_delta_corrected(baseline["scores"], candidate["scores"], candidate["n_train"], candidate["n_test"])
        threshold = commit_threshold(stats["se_delta"], stats["dof"], n_total)
        done[key] = {
            "combo": combo_dict,
            "mean_f1": candidate["mean"],
            "delta": stats["mean_delta"],
            "se_delta": stats["se_delta"],
            "threshold": threshold,
            "clears_threshold": stats["mean_delta"] >= threshold,
        }
        RESULTS_PATH.write_text(json.dumps(done, indent=2))
        newly_done += 1
        print(f"[{len(done)}/{n_total}] {combo_dict} -> delta={stats['mean_delta']:+.4f} "
              f"se={stats['se_delta']:.4f} threshold={threshold:.4f}")

    print(f"\nComputed {newly_done} new combo(s) this run, {len(done)}/{n_total} total done.")
    if len(done) < n_total:
        print(f"Not finished -- re-run `python -m modules.exhaustive_search` to continue "
              f"({n_total - len(done)} combos left).")
        return

    print("\nALL COMBINATIONS DONE\n")
    print(f"True as-is baseline (fixed-fold, fit-on-train): {baseline['mean']:.4f} +/- {baseline['std']:.4f} "
          f"(n={len(folds)} folds)\n")

    results = sorted(done.values(), key=lambda r: r["delta"], reverse=True)
    print(f"{'rank':<5}{'delta':>9}{'se':>8}{'thresh':>9}{'clears?':>9}   combo")
    for rank, r in enumerate(results, 1):
        combo_str = ", ".join(f"{c}={op}" for c, op in r["combo"].items())
        print(f"{rank:<5}{r['delta']:>+9.4f}{r['se_delta']:>8.4f}{r['threshold']:>9.4f}"
              f"{'YES' if r['clears_threshold'] else 'no':>9}   {combo_str}")

    print()
    best = results[0]
    do_nothing = next(r for r in results if all(op == "none" for op in r["combo"].values()))
    print(f"Best combo: {best['combo']} -> delta={best['delta']:+.4f} (clears threshold: {best['clears_threshold']})")
    print(f"Do-nothing (as-is): delta={do_nothing['delta']:+.4f} (rank {results.index(do_nothing)+1} of {len(results)})")
    if not any(r["clears_threshold"] for r in results):
        print("\nNo combination clears the corrected threshold against the true as-is baseline -- "
              "'leave the data alone' is the defensible conclusion on this dataset.")


if __name__ == "__main__":
    run()
