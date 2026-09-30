"""Tests for detectors + executor ops that need only pandas (2026-09-30).
Run: python -m modules.ops_tests"""
import numpy as np
import pandas as pd

from .detectors import detect, find_unit_shift
from .executor import fit_and_apply, execute
from .injection import inject
from . import config


def _raw():
    return pd.read_csv(config.DATA_PATH).replace("?", np.nan) if hasattr(config, "DATA_PATH") else pd.read_csv("data/adult.csv").replace("?", np.nan)


def main():
    raw = _raw()
    assert not [f for f in detect(raw) if f["defect"] == "mixed_units"], "false mixed_units finding on real data"
    for rate in (0.05, 0.15, 0.30):
        df, m = inject(raw, [{"id": "u", "kind": "mixed_units", "column": "age", "rate": rate, "factor": 12}], seed=101)
        fs = [f for f in detect(df) if f["defect"] == "mixed_units"]
        assert len(fs) == 1 and fs[0]["column"] == "age" and fs[0]["n_rows"] == len(m[0]["rows"]), rate
        fixed = execute(df, "age", "rescale_units")
        rows = m[0]["rows"]
        assert (fixed.loc[rows, "age"] == m[0]["original"]).all()
        assert (fixed.drop(rows)["age"] == raw.drop(rows)["age"]).all(), "collateral change"
    df, _ = inject(raw, [{"id": "u", "kind": "mixed_units", "column": "age", "rate": 0.15, "factor": 12}], seed=101)
    tr, te = df.iloc[:20000], df.iloc[20000:]
    a, b = fit_and_apply(tr, te, "age", "rescale_units")
    assert a["age"].max() <= 90 and b["age"].max() <= 90
    a, _ = fit_and_apply(raw.iloc[:20000], raw.iloc[20000:], "age", "rescale_units")
    assert (a["age"] == raw.iloc[:20000]["age"]).all(), "must be a no-op on clean data"
    d2, _ = inject(raw, [{"id": "s", "kind": "sentinel", "column": "age", "rate": 0.08, "value": 999}], seed=1)
    assert find_unit_shift(d2["age"]) is None, "999 code must not read as a unit shift"
    # blindness: nothing that decides or plans may know about the answer key
    import pathlib, re
    here = pathlib.Path(__file__).parent
    for name in ("planner.py", "detectors.py", "executor.py", "evaluator.py"):
        src = (here / name).read_text(encoding="utf-8")
        assert not re.search(r"\bmanifest\b|expected_fix|expected_commit|from \.injection|import injection", src), f"{name} references the answer key"
    body = (here / "pipeline.py").read_text(encoding="utf-8")
    loop = body[body.index("for i in range(1, config.MAX_ITERATIONS + 1):"):body.index("path = audit.save(")]
    assert "manifest" not in loop, "decision loop must not touch the manifest"
    print("ops_tests: all passed")


if __name__ == "__main__":
    main()
