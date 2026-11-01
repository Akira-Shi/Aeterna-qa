"""P6a leak tests: the Stage 2 preprocessing is fitted on training rows only.

The >15-levels rule (ENC-H1) uses capped one-hot, NOT target encoding, so no label-dependent encoder exists. These tests
prove it anyway: (1) no target-style encoder in any built pipeline; (2) shuffling/perturbing the test-fold labels leaves
the fitted preprocessing and model identical; (3) the encoders see only train rows (a level present only in test rows is
absent from the fitted categories); (4) CV refits per fold (compare clones the Pipeline and fits on train rows).

  python tests/test_stage2_leak.py        (or: pytest tests/test_stage2_leak.py)
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aeterna_qa"))
sys.path.insert(0, str(ROOT / "tests"))

from stage2 import rules, build                      # noqa: E402
from test_stage2_rules import make_df                # noqa: E402


def _encoders(pipe):
    out = []
    for _, inner, _ in pipe.named_steps["prep"].transformers:
        if hasattr(inner, "steps"):
            out += [t for _, t in inner.steps]
        else:
            out.append(inner)
    return out


def _data():
    df = make_df(n=400, seed=5)
    X, y = df.drop(columns="y"), (df["y"] == "yes").astype(int)
    tr, te = X.index[:300], X.index[300:]
    X = X.copy()
    X.loc[te[:5], "cat_hi"] = "TEST_ONLY_LEVEL"   # level that exists only in test rows
    return X, y, tr, te


def test_no_target_encoder():
    X, y, _, _ = _data()
    assert X["cat_hi"].nunique() > rules.HIGH_CARD
    for fam in rules.FAMILIES:
        steps = rules.recommend("binary", fam, X, y)
        pipe = build.build_pipeline(steps, "binary", fam)
        for t in _encoders(pipe):
            assert "target" not in type(t).__name__.lower(), (fam, t)
    print("  PASS: no label-dependent encoder in any built pipeline")


def test_perturbed_test_labels_do_not_change_fit():
    X, y, tr, te = _data()
    rng = np.random.default_rng(0)
    y_pert = y.copy()
    y_pert.loc[te] = rng.permutation(y.loc[te].to_numpy())          # shuffle test labels
    y_flip = y.copy()
    y_flip.loc[te] = 1 - y.loc[te]                                   # flip test labels
    for fam in rules.FAMILIES:
        steps = rules.recommend("binary", fam, X, y)
        fits = []
        for yy in (y, y_pert, y_flip):
            pipe = build.fit_on_train(build.build_pipeline(steps, "binary", fam), X, yy, tr)
            Z = pipe.named_steps["prep"].transform(X.loc[tr])
            fits.append((Z, pipe.predict_proba(X.loc[tr])[:, 1]))
        for Z, p in fits[1:]:
            assert np.array_equal(Z, fits[0][0]), fam
            assert np.array_equal(p, fits[0][1]), fam
    print("  PASS: shuffling / flipping test-fold labels leaves fitted encoding and model unchanged")


def test_encoder_sees_only_train_rows():
    X, y, tr, te = _data()
    steps = rules.recommend("binary", "linear", X, y)
    pipe = build.fit_on_train(build.build_pipeline(steps, "binary", "linear"), X, y, tr)
    cats = [lvl for t in _encoders(pipe) if hasattr(t, "categories_") for arr in t.categories_ for lvl in arr]
    assert "TEST_ONLY_LEVEL" not in cats
    assert set(X.loc[tr, "cat_hi"].dropna()) >= {c for c in cats if str(c).startswith("L")}
    # numeric imputer / scaler statistics equal those computed from train rows alone
    num = pipe.named_steps["prep"].transformers_
    for name, inner, cols in num:
        for t in (inner.steps if hasattr(inner, "steps") else []):
            if type(t[1]).__name__ == "SimpleImputer" and t[1].strategy == "median":
                assert np.allclose(t[1].statistics_, X.loc[tr, cols].median().to_numpy())
    print("  PASS: encoders / imputers fitted on train rows only (test-only level absent, medians match train)")


def test_cv_clones_and_refits_per_fold():
    import inspect
    from stage2 import compare
    src = inspect.getsource(compare.compare)
    assert "clone(pipe).fit(X.loc[tr]" in src and "predict_proba(X.loc[te])" in src
    print("  PASS: compare refits a cloned Pipeline on each fold's training rows")


def test_pandas_na_in_object_columns_fits():
    X, y, tr, te = _data()
    X = X.astype({"cat_miss": object}).copy()
    X.loc[X["cat_miss"].isna(), "cat_miss"] = pd.NA
    X["x_sym"] = X["x_sym"].astype("Float64")   # nullable numeric with pd.NA
    for fam in rules.FAMILIES:
        steps = rules.recommend("binary", fam, X, y)
        pipe = build.fit_on_train(build.build_pipeline(steps, "binary", fam), X, y, tr)
        assert len(pipe.predict(X.loc[te])) == len(te)
        build.fit_on_train(build.build_default(X, "binary", fam), X, y, tr)
    print("  PASS: pandas NA in object columns (TaskSpec loading) fits for recommended and default pipelines")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("stage2 leak tests: all passed")
