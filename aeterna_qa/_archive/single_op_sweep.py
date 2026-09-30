"""
Single-operation sweep (2026-09-30): for one scenario (real Adult, or Adult
with the DECLARED synthetic injection) evaluate EVERY (column, operation)
that the detectors justify, ALONE, against the untouched baseline on the same
fixed folds -- no chains, no stacking, so one harmful op cannot contaminate
the measurement of another. Same Nadeau-Bengio + t + Bonferroni bar as the
pipeline. This is the ground-truth table the planner's choices should be
judged against (same role exhaustive_search.py plays for missingness).

Usage: python -m modules.single_op_sweep [--inject]
"""
import sys
import json

from . import config
from .evaluator import (load_raw_dataset, make_fixed_folds, calculate_f1_candidate,
                        paired_delta_corrected, commit_threshold, clears_bar)
from .detectors import detect
from .injection import inject
from .planner import remaining_options


def run(use_injection: bool = False) -> list[dict]:
    raw = load_raw_dataset()
    if use_injection:
        raw, _manifest = inject(raw)
    folds = make_fixed_folds(raw)
    base = calculate_f1_candidate(raw, folds)
    findings = detect(raw)
    opts = remaining_options(findings)
    n_tests = len(opts)
    print(f"[{config.EVALUATOR.upper()}] {'SYNTHETIC-injected' if use_injection else 'REAL'} data | baseline F1 {base['mean']:.4f} "
          f"+/- {base['std']:.4f} | {n_tests} single-op candidates, Bonferroni over {n_tests}\n", flush=True)
    rows = []
    for col, op, f in opts:
        try:
            cand = calculate_f1_candidate(raw, folds, candidate_ops={col: op})
        except Exception as e:  # noqa: BLE001
            print(f"  {col:<16}{op:<22} ERROR {e}", flush=True)
            continue
        st = paired_delta_corrected(base["scores"], cand["scores"], cand["n_train"], cand["n_test"])
        thr = commit_threshold(st["se_delta"], st["dof"], n_tests)
        rows.append({"column": col, "operation": op, "defect": f["defect"], "delta": st["mean_delta"],
                     "se": st["se_delta"], "threshold": thr, "clears": bool(clears_bar(st["mean_delta"], thr)),
                     "rows_touched": f["n_rows"]})
        print(f"  {col:<16}{op:<22}{f['defect']:<18} delta={st['mean_delta']:+.4f}  bar={thr:.4f}  "
              f"{'CLEARS' if clears_bar(st['mean_delta'], thr) else 'no'}", flush=True)
    config.LOG_DIR.mkdir(exist_ok=True)
    out = config.LOG_DIR / f"single_op_sweep_{'inject' if use_injection else 'real'}_{config.EVALUATOR}.json"
    with open(out, "w") as fh:
        json.dump({"baseline": base["mean"], "rows": rows}, fh, indent=1)
    print(f"\nwritten: {out}")
    return rows


if __name__ == "__main__":
    if "--evaluator" in sys.argv:
        config.EVALUATOR = sys.argv[sys.argv.index("--evaluator") + 1]
    run(use_injection="--inject" in sys.argv)
