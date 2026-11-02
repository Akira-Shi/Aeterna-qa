"""P6a tests: Stage 2 rule engine, builder and comparison. Every model family x task type.

  python tests/test_stage2_rules.py        (or: pytest tests/test_stage2_rules.py)
"""
import json
import sys
import tempfile
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.exceptions import ConvergenceWarning  # noqa: E402
warnings.filterwarnings("ignore", category=ConvergenceWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aeterna_qa"))

from modules.taskspec import TaskSpec                                               # noqa: E402
from stage2 import rules, build, compare                                            # noqa: E402

FAMILIES = rules.FAMILIES
TASKS = rules.TASK_TYPES


def make_df(n=300, seed=0, imbalance=False, task="binary"):
    rng = np.random.default_rng(seed)
    x_sym = rng.normal(size=n)
    x_skew = rng.lognormal(size=n)
    cat_lo = rng.choice(["a", "b", "c"], n)
    cat_hi = rng.choice([f"L{i}" for i in range(25)], n)
    cat_miss = rng.choice(["u", "v"], n).astype(object)
    x_sym[rng.random(n) < 0.1] = np.nan
    x_skew[rng.random(n) < 0.1] = np.nan
    cat_miss[rng.random(n) < 0.2] = None
    lat = np.nan_to_num(x_sym) + 0.3 * np.log1p(np.nan_to_num(x_skew)) + (cat_lo == "a")
    if task == "regression":
        y = lat + rng.normal(scale=0.3, size=n)
    elif task == "multiclass":
        y = pd.qcut(lat + rng.normal(scale=0.5, size=n), 3, labels=["lo", "mid", "hi"]).astype(str)
    else:
        thr = np.quantile(lat, 0.9 if imbalance else 0.5)
        y = np.where(lat + rng.normal(scale=0.5, size=n) > thr, "yes", "no")
    return pd.DataFrame({"x_sym": x_sym, "x_skew": x_skew, "cat_lo": cat_lo, "cat_hi": cat_hi,
                         "cat_miss": cat_miss, "y": y})


def by(steps, stage):
    return {s.rule_id: s for s in steps if s.stage == stage}


def test_every_family_task_builds_fits_and_saves():
    for task in TASKS:
        df = make_df(task=task, imbalance=(task == "binary"))
        X, y = df.drop(columns="y"), df["y"]
        for fam in FAMILIES:
            steps = rules.recommend(task, fam, X, y)
            assert steps, (task, fam)
            for s in steps:
                assert s.rule_id and s.reason and s.alternative, (task, fam, s)
            pipe = build.build_pipeline(steps, task, fam)
            assert not hasattr(pipe.named_steps["model"], "classes_") and not hasattr(pipe.named_steps["model"], "coef_")
            tr = X.index[:200]
            fitted = build.fit_on_train(pipe, X, y, tr)
            pred = fitted.predict(X.iloc[200:])
            assert len(pred) == 100
            with tempfile.TemporaryDirectory() as d:
                p = build.save_pipeline(fitted, Path(d) / "p.joblib", steps)
                assert len(joblib.load(p).predict(X.iloc[200:])) == 100
                side = json.loads(Path(str(p) + ".steps.json").read_text())
                assert {"rule_id", "reason", "alternative"} <= set(side[0])
    print("  PASS: every family x task type recommends, builds, fits on train rows, saves")


def test_family_rules():
    df = make_df()
    X, y = df.drop(columns="y"), df["y"]
    lin = rules.recommend("binary", "linear", X, y)
    assert by(lin, "imputation")["IMP-N2"].columns == ("x_skew",)          # skewed -> median
    assert by(lin, "imputation")["IMP-N3"].columns == ("x_sym",)           # symmetric -> mean
    assert "SCL-S1" not in by(lin, "scaling")                              # yeo-johnson removed in P6a
    assert set(by(lin, "scaling")["SCL-G1"].columns) == {"x_sym", "x_skew"}
    assert by(lin, "imputation")["IMP-C1"].columns == ("cat_miss",)        # 20% missing -> own level
    assert by(lin, "encoding")["ENC-H1"].columns == ("cat_hi",)            # capped one-hot
    assert set(by(lin, "encoding")["ENC-L1"].columns) == {"cat_lo", "cat_miss"}
    tree = rules.recommend("binary", "tree_ensemble", X, y)
    assert set(by(tree, "imputation")["IMP-N1"].columns) == {"x_sym", "x_skew"}
    assert by(tree, "scaling")["SCL-T1"].method == "none"
    assert set(by(tree, "encoding")) == {"ENC-T1"}
    dist = rules.recommend("binary", "distance", X, y)
    assert by(dist, "scaling")["SCL-D1"].method == "robust"
    neu = rules.recommend("binary", "neural", X, y)
    assert by(neu, "scaling")["SCL-G1"].method == "standard"
    print("  PASS: per-family rule choices")


def test_imbalance_rules():
    df = make_df(imbalance=True)
    X, y = df.drop(columns="y"), df["y"]
    for fam, rid in (("linear", "IMB-1"), ("tree_ensemble", "IMB-1"), ("distance", "IMB-2"), ("neural", "IMB-2")):
        assert by(rules.recommend("binary", fam, X, y), "imbalance").keys() == {rid}, fam
    assert by(rules.recommend("multiclass", "linear", X, y.where(df.index % 10 == 0, "yes")), "imbalance")
    assert not by(rules.recommend("regression", "linear", X, np.arange(len(X))), "imbalance")
    bal = make_df()
    assert not by(rules.recommend("binary", "linear", bal.drop(columns="y"), bal["y"]), "imbalance")
    pipe = build.build_pipeline(rules.recommend("binary", "linear", X, y), "binary", "linear")
    assert pipe.named_steps["model"].class_weight == "balanced"
    print("  PASS: imbalance step by family / task")


def test_deterministic_and_unfitted():
    df = make_df()
    X, y = df.drop(columns="y"), df["y"]
    a = [s.to_dict() for s in rules.recommend("binary", "linear", X, y)]
    b = [s.to_dict() for s in rules.recommend("binary", "linear", X, y)]
    assert a == b
    print("  PASS: deterministic")


def test_unsupported_model():
    assert rules.resolve_family("linear") == "linear"
    assert rules.resolve_family("RandomForestClassifier") == "tree_ensemble"
    from sklearn.neighbors import KNeighborsClassifier
    assert rules.resolve_family(KNeighborsClassifier()) == "distance"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert rules.resolve_family("XGBClassifier") == "tree_ensemble"
        assert any("nearest family" in str(x.message) for x in w)
    try:
        rules.resolve_family("QuantumOracle")
    except rules.UnsupportedModel:
        pass
    else:
        raise AssertionError("expected UnsupportedModel")
    try:
        rules.recommend("binary", "bogus", make_df().drop(columns="y"))
    except rules.UnsupportedModel:
        pass
    else:
        raise AssertionError("expected UnsupportedModel")
    print("  PASS: nearest family with warning, else UnsupportedModel")


def test_compare():
    df = make_df(n=400, seed=3)
    for fam in FAMILIES:
        spec = TaskSpec(path="x.csv", target="y", task_type="binary", positive_label="yes", model_family=fam)
        r = compare.compare(df, spec)
        assert r["n_folds"] == 15 and np.isfinite(r["mean_diff"]) and r["se_corrected"] >= 0
        assert "commit" not in r and "gate" not in r
        assert abs(r["mean_diff"] - (r["recommended_mean"] - r["default_mean"])) < 1e-12
        assert "Report only" in compare.format_report(r)
    for task in ("multiclass", "regression"):
        spec = TaskSpec(path="x.csv", target="y", task_type=task, model_family="linear")
        try:
            compare.compare(make_df(task=task), spec)
        except compare.CompareNotSupported:
            pass
        else:
            raise AssertionError("expected CompareNotSupported")
    print("  PASS: compare (binary, all families; non-binary unsupported), report only")


def test_fallback_to_default():
    base = {"steps": [], "note": "report only"}
    worse = compare._decide({**base, "mean_diff": -0.0046, "se_corrected": 0.0002})        # -23 SE
    assert worse["fallback"] and worse["final"] == "default"
    assert "fallback: default outperformed recommendation" in worse["note"] and worse["fallback_note"] == compare.FALLBACK_TEXT
    edge = compare._decide({**base, "mean_diff": -0.0040, "se_corrected": 0.0020})         # exactly -2 SE: not beyond
    assert not edge["fallback"] and edge["final"] == "recommended" and "fallback_note" not in edge
    better = compare._decide({**base, "mean_diff": 0.003, "se_corrected": 0.0001})
    assert not better["fallback"] and better["final"] == "recommended"
    r = {**base, "model_family": "linear", "n_folds": 15, "metric": "m", "mean_diff": -1.0, "se_corrected": 0.1,
         "f1_mean_diff": 0.0, "f1_se_corrected": 0.0, "fallback": True}
    assert "fallback: default outperformed recommendation" in compare.format_report(r)
    # end to end: a deliberately harmful recommendation (informative-missing numeric column dropped to a constant is
    # not available, so force harm by a recommender that scales nothing but one-hot-encodes a unique-id-like column)
    rng = np.random.default_rng(5)
    n = 600
    sig = rng.normal(size=n)
    df = pd.DataFrame({"sig": sig, "uid": [f"u{i}" for i in range(n)],
                       "y": np.where(sig + rng.normal(scale=0.5, size=n) > 0, "yes", "no")})
    spec = TaskSpec(path="x.csv", target="y", task_type="binary", positive_label="yes", model_family="linear")
    bad = [rules.Step("encoding", ("uid",), "onehot", "TEST-BAD", "forced", "none"),
           rules.Step("scaling", ("sig",), "none", "TEST-BAD2", "forced", "standard")]
    out = compare.compare(df, spec, steps=bad)
    assert out["final"] in ("default", "recommended") and out["fallback"] == (out["mean_diff"] < -2 * out["se_corrected"])
    print("  PASS: fallback to default when recommendation is worse by > 2 SE")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("stage2 tests: all passed")
