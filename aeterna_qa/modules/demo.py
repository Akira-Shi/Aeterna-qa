"""
D1: a labelled SYNTHETIC DEMO scenario (2026-09-30). NOT a study result.

Four declared defects on the eval partition, so that the commit gate is exercised on
several columns in one run. Spec declared in Documents/Documentation.md ("D1 demo
scenario spec") BEFORE the first run; never tuned afterwards. Never pooled with C1-C5,
not in RESULTS.md, not pre-registered.

  python -m modules.pipeline --scenario D1 --seed 201
"""
import json

from . import config, pipeline
from .evaluator import make_fixed_folds, calculate_f1_candidate, materialize
from .injection import inject
from .study import base_and_split, grade, _mismatch, CLEAN_DIR

D1_SCENARIO = "synthetic_D1_demo"
D1_SPEC = [
    {"id": "D1_capital_gain", "kind": "sentinel", "column": "capital.gain", "rate": 0.02,
     "value": 9999999, "expected_fix": "sentinel_to_median"},
    {"id": "D1_capital_loss", "kind": "sentinel", "column": "capital.loss", "rate": 0.03,
     "value": 9999999, "expected_fix": "sentinel_to_median"},
    {"id": "D1_hours_units", "kind": "mixed_units", "column": "hours.per.week", "rate": 0.30,
     "factor": 12, "expected_fix": "rescale_units"},
    {"id": "D1_occupation", "kind": "category_variants", "column": "occupation", "rate": 0.60,
     "expected_fix": "normalize_categories"},
]
BANNER = "*** SYNTHETIC DEMO (D1): declared damage injected into Adult. Not real data, not a study result. ***"


def run_d1(seed: int = 201, offline_planner: bool = False) -> dict:
    _, ev = base_and_split()
    spec = [dict(s, expected_commit=True) for s in D1_SPEC]
    df, manifest = inject(ev, spec, seed=seed)
    print(BANNER)
    for m in manifest:
        print(f"    injected {m['id']}: {m['kind']} in '{m['column']}' at {m['rate']:.0%} ({len(m['rows'])} rows)")
    print()
    res = pipeline.run(offline_planner=offline_planner, raw_df=df, manifest=manifest,
                       label=f"SYNTHETIC DEMO D1 seed {seed} (not a study result)",
                       scenario_meta=[{k: v for k, v in m.items() if k not in ("rows", "original")} for m in manifest],
                       scenario_name=D1_SCENARIO)
    ops = res["committed_ops"]
    if ops:
        cleaned = materialize(df, ops)
        tag = "" if offline_planner else "_groq"
        stem = f"adult_clean{tag}_D1_{seed}"
        CLEAN_DIR.mkdir(exist_ok=True)
        cleaned.to_csv(CLEAN_DIR / f"{stem}.csv", index=False)
        common = cleaned.index.intersection(df.index)
        (CLEAN_DIR / f"{stem}.manifest.json").write_text(json.dumps(
            {"scenario": D1_SCENARIO, "label": "SYNTHETIC DEMO, not a study result", "seed": seed,
             "synthetic_corruption": [{k: v for k, v in m.items() if k not in ("rows", "original")} for m in manifest],
             "committed_ops": ops, "rows_in": len(df), "rows_out": len(cleaned),
             "cells_changed_vs_corrupted": int(_mismatch(cleaned.loc[common], df.loc[common]).to_numpy().sum())},
            indent=1, default=str))
        print(f"Cleaned file: {CLEAN_DIR / (stem + '.csv')}")
    print("\nGrading against the answer key (SYNTHETIC DEMO):")
    for m in manifest:
        got = ops.get(m["column"])
        g = grade(ev, df, materialize(df, ops), m)
        print(f"  {m['id']}: expected {m['expected_fix']}, committed {got}, grading {g}")
    return res
