"""P4 acceptance: the Adult study still reproduces RESULTS.md exactly after the TaskSpec layer.

Re-runs a subset of the registered eval rows (offline rule planner, full eval partition) through the
unchanged study code path, with the task applied via TaskSpec (taskspec.applied(adult_spec())), and
compares to the committed numbers in Documents/RESULTS.md (4 decimals) and logs/study/eval.json
(1e-9, when present). Subset = one hit (C5/201), one correct rollback (C3/203), one false commit (C4/201);
REPRO_FULL=1 runs every offline row (15 pipeline runs, slow).

  python tests/test_reproduce_v1.py        (or: pytest tests/test_reproduce_v1.py)
"""
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aeterna_qa"))

from modules import config, pipeline, study, taskspec                       # noqa: E402
from modules.evaluator import calculate_f1_candidate, make_fixed_folds     # noqa: E402
from modules.injection import inject                                        # noqa: E402

SUBSET = [("C5", 201), ("C3", 203), ("C4", 201)]
RESULTS_MD = (ROOT / "Documents" / "RESULTS.md").read_text(encoding="utf-8")
EVAL_JSON = ROOT / "aeterna_qa" / "logs" / "study" / "eval.json"


def _rows():
    if EVAL_JSON.exists():
        return {(r["scenario"], r["seed"]): r for r in json.loads(EVAL_JSON.read_text())["results"]}
    return {}


def _md_row(sc, seed):
    for line in RESULTS_MD.splitlines():
        if line.startswith(f"| {sc} | {seed} | ") and "Gate inj" not in line:
            return line
    return None


def test_adult_study_reproduces_results_md():
    ref = _rows()
    keys = list(ref) if os.environ.get("REPRO_FULL") else SUBSET
    _, ev = study.base_and_split()
    assert len(ev) == 24128, len(ev)                   # RESULTS.md: eval rows
    old_log = config.LOG_DIR
    with tempfile.TemporaryDirectory() as tmp:
        config.LOG_DIR = Path(tmp)
        try:
            for sc, seed in keys:
                rate = ref[(sc, seed)]["rate"] if ref else {"C5": 0.01, "C3": 0.15, "C4": 0.30}[sc]
                spec = study._spec(sc, rate)
                spec["expected_commit"] = bool(ref[(sc, seed)]["expected_commit"]) if ref else sc == "C5"
                df, manifest = inject(ev, [spec], seed=seed)
                folds = make_fixed_folds(df)
                with taskspec.applied(taskspec.adult_spec()), contextlib.redirect_stdout(io.StringIO()):
                    res = pipeline.run(offline_planner=True, raw_df=df, manifest=manifest, run_explain=False,
                                       scenario_meta=[{k: v for k, v in m.items() if k not in ("rows", "original")} for m in manifest])
                    inj = calculate_f1_candidate(df, folds)
                    fin = calculate_f1_candidate(df, folds, committed_ops=res["committed_ops"])
                    clean = calculate_f1_candidate(ev, folds)
                line = _md_row(sc, seed)
                assert line, f"{sc}/{seed} not in RESULTS.md"
                assert str(res["committed_ops"] or "none") in line or (not res["committed_ops"] and "| none |" in line), (line, res["committed_ops"])
                needle = f"{inj['mean']:.4f} -> {fin['mean']:.4f} ({clean['mean']:.4f})"
                assert needle in line, f"{sc}/{seed}: {needle} not in RESULTS.md row {line}"
                if ref:
                    r = ref[(sc, seed)]
                    assert res["committed_ops"] == r["committed_ops"]
                    for got, want in ((inj["mean"], r["gate_injected"]), (fin["mean"], r["gate_final"]), (clean["mean"], r["gate_clean"])):
                        assert abs(got - want) < 1e-9, (sc, seed, got, want)
                print(f"reproduced {sc}/{seed}: {res['committed_ops'] or 'none'}  {needle}")
        finally:
            config.LOG_DIR = old_log
    assert config.TARGET_COLUMN == "income"


if __name__ == "__main__":
    test_adult_study_reproduces_results_md()
    print("test_reproduce_v1: passed")
