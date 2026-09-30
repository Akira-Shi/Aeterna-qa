"""
Leak tests for the LR evaluator (2026-09-30, guide-agreed). Run BEFORE trusting
any LR number; evaluator is frozen once these pass.  python -m modules.evaluator_tests

Test 1 (guard bites): fit a scaler on train+test on purpose; the in-code assert
        assert_scaler_fit_on_train_only MUST raise. Proves the guard is live.
Test 2 (independent reference): our LR baseline per-fold F1 on the fixed folds must
        match sklearn's own cross_val_score(Pipeline(StandardScaler, LR)) on the
        SAME folds, computed with a separate, plain global encoding.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score

from . import config
from .evaluator import (load_raw_dataset, make_fixed_folds, calculate_f1_candidate, make_model,
                        assert_scaler_fit_on_train_only, _prepare_xy, _encode_train_test)


def test_guard_bites(raw, folds):
    train_idx, test_idx = folds[0]
    tr, te = raw.loc[train_idx], raw.loc[test_idx]
    Xtr, Xte = _encode_train_test(tr, te)
    Xtr, Xte = Xtr.astype(float), Xte.astype(float)
    y = (raw[config.TARGET_COLUMN].astype(str).str.strip() == config.POSITIVE_CLASS).astype(int)
    good = make_model("lr").fit(Xtr, y.loc[tr.index])
    assert_scaler_fit_on_train_only(good, Xtr)                      # must pass
    leaky = make_model("lr")
    leaky[0].fit(pd.concat([Xtr, Xte]))                             # scaler sees TEST rows
    leaky[1].fit(leaky[0].transform(Xtr), y.loc[tr.index])
    try:
        assert_scaler_fit_on_train_only(leaky, Xtr)
    except AssertionError:
        print("  test 1 PASS: guard passes a train-only scaler and raises on a train+test scaler")
        return True
    print("  test 1 FAIL: guard did not detect a leaky scaler")
    return False


def test_matches_sklearn(raw, folds):
    out = calculate_f1_candidate(raw, folds, model="lr")
    ours, ours_brier = out["f1_scores"], np.array(out["brier_scores"])
    X, y = _prepare_xy(raw)
    X = X.astype(float)
    pos_folds = [(np.asarray(tr), np.asarray(te)) for tr, te in folds]  # RangeIndex: labels == positions
    ref = cross_val_score(make_model("lr"), X, y, cv=pos_folds, scoring="f1")
    diff = np.abs(np.array(ours) - ref)
    print(f"  ours   mean F1 {np.mean(ours):.4f}   sklearn mean F1 {ref.mean():.4f}   max per-fold |diff| {diff.max():.2e}")
    ref_b = -cross_val_score(make_model("lr"), X, y, cv=pos_folds, scoring="neg_brier_score")
    diff_b = np.abs(ours_brier - ref_b)
    print(f"  ours   mean Brier {ours_brier.mean():.4f}   sklearn mean Brier {ref_b.mean():.4f}   max per-fold |diff| {diff_b.max():.2e}")
    ok = diff.max() < 1e-3 and diff_b.max() < 1e-3
    print(f"  test 2 {'PASS' if ok else 'FAIL'}: LR baseline vs sklearn cross_val_score on the same folds")
    return ok


if __name__ == "__main__":
    raw = load_raw_dataset()
    folds = make_fixed_folds(raw, n_repeats=1)
    print("LR evaluator leak tests")
    a = test_guard_bites(raw, folds)
    b = test_matches_sklearn(raw, folds)
    print("ALL PASS - LR evaluator may be frozen" if a and b else "FAILED - do not use LR numbers")
