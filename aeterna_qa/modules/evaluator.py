"""
F1 evaluator for AETERNA-QA.

Fits a RandomForestClassifier on the (possibly modified) dataframe and
returns F1 on a held-out test set. Every split and every model fit uses
config.RANDOM_STATE so results are reproducible and comparable across
iterations of the pipeline -- this matters because the accept/rollback
decision is a direct comparison of two F1 numbers.

2026-09-29 (evening, second pass) -- test-set leakage fix:
calculate_f1_cv (below) was found to reward drop_rows unfairly: it fits
AND evaluates on the cleaned dataframe, so dropping rows also removes
those rows from every test fold. If the dropped rows were disproportionately
hard to predict (real missingness often correlates with harder cases --
confirmed here: after dropping native.country/workclass '?' rows, only 7
rows are still missing occupation, all "Never-worked", a small
idiosyncratic group), the model looks better mainly because it's being
graded on an easier test set, not because training on cleaner data
produced a better model. A second problem compounded this: comparing two
independently-computed CV runs (each with its own StratifiedKFold(shuffle
=True) call) means even a tiny row-count change (e.g. -7 rows) produces a
DIFFERENT fold partition, not the same partition minus 7 rows -- so most
of an observed "delta" between two close configurations can be fold
reshuffling noise rather than a real effect. Both were confirmed on a
real case: two chains differing only in whether 7 "Never-worked" rows
were dropped or filled measured F1 0.0049 apart, right at the size of the
acceptance threshold.

calculate_f1_fixed_folds is the fix: fold membership is computed ONCE
from the RAW, uncleaned dataset, by row ID (make_fixed_folds), and reused
identically for every operation evaluated in a run. A cleaning operation
can change what's available for TRAINING (drop_rows shrinks the training
rows used; fill_* changes training values) -- but the TEST fold is always
built from raw_df's original rows for those row IDs, '?' and all, no
matter what was cleaned. This removes the reward for deleting hard test
rows, and paired_delta compares the SAME fold indices between two
conditions, so common fold-level noise cancels out instead of compounding.

calculate_f1 and calculate_f1_cv are kept below for reference/comparison
(and because they're a legitimate demonstration of exactly the failure
mode above) but the pipeline no longer uses either for accept/commit
decisions.
"""
import math

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from sklearn.model_selection import train_test_split, StratifiedKFold, RepeatedStratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, brier_score_loss

from . import config
from .executor import fit_and_apply, execute


def _prepare_xy(df: pd.DataFrame):
    """Split a cleaned/dirty dataframe into (X, y), one-hot encoding
    categoricals with an explicit NaN category so missingness itself is
    visible to the model rather than silently imputed by pandas."""
    d = df.copy()
    d.columns = [c.strip() for c in d.columns]
    y = (d[config.TARGET_COLUMN].astype(str).str.strip() == config.POSITIVE_CLASS).astype(int)
    X = d.drop(columns=[config.TARGET_COLUMN])
    X = pd.get_dummies(X, dummy_na=True)
    return X, y


def calculate_f1(df: pd.DataFrame) -> float:
    """Single train/test split -> fit RandomForest -> return F1 on the
    positive class (income > $50k). Reference/comparison only -- see the
    module docstring for why this and calculate_f1_cv are no longer used
    for accept/commit decisions."""
    X, y = _prepare_xy(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
        stratify=y,
    )
    clf = RandomForestClassifier(random_state=config.RANDOM_STATE, n_jobs=-1)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    return f1_score(y_test, preds)


def calculate_f1_cv(df: pd.DataFrame, n_splits: int = None) -> dict:
    """Stratified K-fold CV -> fit RandomForest per fold -> return mean and
    std F1 across folds, plus the raw per-fold scores. Reference/
    comparison only (see module docstring) -- this still trains AND tests
    on the cleaned dataframe, so it still rewards drop_rows for deleting
    hard test rows, and its fold partition changes with row count, making
    two close configurations' numbers not directly comparable.
    """
    n_splits = n_splits or config.CV_FOLDS
    X, y = _prepare_xy(df)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=config.RANDOM_STATE)
    scores = []
    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        clf = RandomForestClassifier(random_state=config.RANDOM_STATE, n_jobs=-1)
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        scores.append(f1_score(y_test, preds))
    scores = np.array(scores)
    return {"mean": float(scores.mean()), "std": float(scores.std(ddof=1)), "scores": scores.tolist()}


def make_fixed_folds(raw_df: pd.DataFrame, n_splits: int = None, n_repeats: int = None):
    """Compute fold membership ONCE from the raw (uncleaned) dataset, by
    row ID (raw_df.index). Call this once per pipeline run and reuse the
    same `folds` for the baseline and every candidate evaluated in that
    run -- this is what makes "before" and "after" a paired comparison
    instead of two independently-noisy numbers whose fold assignment
    quietly shifts with row count.

    Returns a list of (train_idx, test_idx) pairs of raw_df's original
    index values (NOT positions) -- n_splits * n_repeats pairs total.
    """
    n_splits = n_splits or config.CV_FOLDS
    n_repeats = n_repeats or config.CV_REPEATS
    y = (raw_df[config.TARGET_COLUMN].astype(str).str.strip() == config.POSITIVE_CLASS).astype(int)
    rskf = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=config.RANDOM_STATE)
    folds = []
    for train_pos, test_pos in rskf.split(raw_df, y):
        folds.append((raw_df.index[train_pos], raw_df.index[test_pos]))
    return folds


def _encode_train_test(train_df: pd.DataFrame, test_df: pd.DataFrame):
    """One-hot encode train and test feature columns TOGETHER so both end
    up with identical columns. Needed because training data may have had
    a column's missingness fully resolved (e.g. all NaN filled) while the
    test data -- always the raw, uncleaned rows -- may still have NaNs in
    that column, or vice versa; encoding them separately could silently
    misalign or drop columns between the two matrices."""
    train_X = train_df.drop(columns=[config.TARGET_COLUMN])
    test_X = test_df.drop(columns=[config.TARGET_COLUMN])
    combined = pd.concat([train_X, test_X], keys=["train", "test"])
    combined = pd.get_dummies(combined, dummy_na=True)
    return combined.xs("train"), combined.xs("test")


def materialize(raw_df: pd.DataFrame, committed_ops: dict[str, str]) -> pd.DataFrame:
    """Apply every CONFIRMED operation globally, for PROFILING/DISPLAY
    ONLY -- e.g. so profiler.profile() can see which columns still have
    missingness after prior commits, and so log messages can show a
    readable current-state F1. NEVER pass this dataframe's F1 into an
    accept/commit decision -- see calculate_f1_candidate, which replays
    committed_ops fold-locally instead precisely to avoid the leak this
    function's global fit would reintroduce."""
    df = raw_df
    for column, operation in committed_ops.items():
        df = execute(df, column, operation)
    return df


def make_model(kind: str):
    """The declared evaluator models. "lr" scales INSIDE the estimator (a sklearn
    Pipeline), so the scaler is fitted on whatever rows .fit() receives -- the
    fold's training rows -- never on test rows."""
    if kind == "rf":
        return RandomForestClassifier(random_state=config.RANDOM_STATE, n_jobs=-1)
    if kind == "lr":
        return make_pipeline(StandardScaler(),
                             LogisticRegression(max_iter=2000, random_state=config.RANDOM_STATE))
    raise ValueError(f"Unknown evaluator '{kind}'. Valid: {config.EVALUATORS}")


def assert_scaler_fit_on_train_only(clf, X_train) -> None:
    """In-code leak guard for the LR evaluator: the fitted scaler's means must equal
    the TRAINING fold's column means exactly. If someone ever fits the scaler on
    train+test (or the full data), this fails loudly."""
    sc = clf[0]
    expected = np.asarray(X_train, dtype=float).mean(axis=0)
    assert np.allclose(sc.mean_, expected), "LEAK: scaler statistics were not fitted on the training fold only"


def calculate_f1_candidate(raw_df: pd.DataFrame, folds, committed_ops: dict[str, str] | None = None,
                            candidate_ops: dict[str, str] | None = None, model: str | None = None) -> dict:
    """THE accept/commit measurement (2026-09-29, fourth pass -- fixes a
    real leak found by review: an earlier version materialized committed
    operations into a single global dataframe and intersected each fold's
    row IDs against it, which meant a committed drop_rows permanently
    removed those rows from every later TEST fold too, not just training
    -- reintroducing exactly the "graded on an easier test set" leak this
    module exists to prevent, one level up). `folds` must come from
    make_fixed_folds(raw_df), computed once per run and reused for every
    call.

    Every fold ALWAYS starts from raw_df's original rows for that fold's
    train/test row IDs -- nothing is ever pre-removed globally. Both
    `committed_ops` (every operation already CONFIRMED this run) and
    `candidate_ops` (the NOT-yet-decided operation(s) being tested on top)
    are replayed together, per fold, via executor.fit_and_apply: any
    needed statistic is fit from that fold's TRAINING rows only, then
    applied to both that fold's train and test rows. A drop_rows in
    EITHER committed_ops or candidate_ops only ever removes rows from
    that fold's training portion -- test rows are never dropped, for the
    whole run, regardless of how many things have committed. A test row
    still missing a value after a committed or candidate drop_rows keeps
    its real value and falls through to the model's own missingness
    handling (the one-hot encoding's dedicated NaN indicator column,
    which the model never saw a nonzero training example of for that
    column, since none of the training rows retain a NaN there) -- this
    is a deliberate, documented fallback, not an oversight.

    Calling with candidate_ops=None (or {}) evaluates committed_ops alone
    -- this is how the pipeline gets the current baseline's own scores,
    now leak-free the same way a candidate's are.

    Returns: {"mean", "std", "scores", "n_train", "n_test"} where scores[i]
    corresponds to folds[i] (enabling paired_delta_corrected below), and
    n_train/n_test are the (approximate, stratified-k-fold-typical) per-fold
    training/test set sizes needed for the Nadeau-Bengio SE correction.
    """
    model = model or config.EVALUATOR
    committed_ops = committed_ops or {}
    candidate_ops = candidate_ops or {}
    all_ops = {**committed_ops, **candidate_ops}
    y_raw = (raw_df[config.TARGET_COLUMN].astype(str).str.strip() == config.POSITIVE_CLASS).astype(int)
    f1s, briers = [], []
    n_trains, n_tests = [], []
    for train_idx, test_idx in folds:
        train_df = raw_df.loc[train_idx]
        test_df = raw_df.loc[test_idx]

        for column, operation in all_ops.items():
            train_df, test_df = fit_and_apply(train_df, test_df, column, operation)

        X_train, X_test = _encode_train_test(train_df, test_df)
        y_train = y_raw.loc[train_df.index]
        y_test = y_raw.loc[test_df.index]
        clf = make_model(model)
        if model == "lr":
            X_train, X_test = X_train.astype(float), X_test.astype(float)
        clf.fit(X_train, y_train)
        if model == "lr":
            assert_scaler_fit_on_train_only(clf, X_train)
        preds = clf.predict(X_test)
        f1s.append(f1_score(y_test, preds))
        briers.append(brier_score_loss(y_test, clf.predict_proba(X_test)[:, 1]))
        n_trains.append(len(train_df))
        n_tests.append(len(test_df))
    f1s, briers = np.array(f1s), np.array(briers)
    scores = -briers if config.GATE_METRIC == "brier" else f1s   # higher = better, always
    return {
        "mean": float(scores.mean()),
        "std": float(scores.std(ddof=1)),
        "scores": scores.tolist(),
        "f1_mean": float(f1s.mean()),
        "f1_scores": f1s.tolist(),
        "brier_mean": float(briers.mean()),
        "brier_scores": briers.tolist(),
        "metric": config.GATE_METRIC,
        "n_train": float(np.mean(n_trains)),
        "n_test": float(np.mean(n_tests)),
    }


def paired_delta_corrected(baseline_scores, candidate_scores, n_train: float, n_test: float) -> dict:
    """Corrected-resampled paired comparison (Nadeau & Bengio, 2003;
    extended to repeated k-fold the standard way -- see e.g. Bouckaert &
    Frank 2004): naive SE = std(deltas)/sqrt(n) understates the true
    uncertainty because k-fold (let alone repeated k-fold) training sets
    overlap heavily -- they are NOT independent samples. The corrected
    variance replaces the naive "1/n" factor with "(1/n + n_test/n_train)",
    which for this project's 5-fold x 3-repeat setup (n=15,
    n_test/n_train ~= 0.25) works out to roughly 2.2x the naive SE.

    This is a widely-used, literature-grounded correction, not an exact
    guarantee -- the repeated-CV extension of the original single-CV
    formula is itself an approximation, and the per-iteration tests in a
    staged pipeline run are not fully independent (see the sequential/
    optional-stopping note in config.py's THRESHOLD comment), so treat the
    resulting p-value/critical-value as a conservative heuristic bound,
    not a rigorously exact family-wise error rate.
    """
    b = np.array(baseline_scores)
    c = np.array(candidate_scores)
    deltas = c - b
    n = len(deltas)
    naive_var = deltas.var(ddof=1) if n > 1 else 0.0
    corrected_var = naive_var * (1.0 / n + n_test / n_train) if n > 1 else 0.0
    return {
        "mean_delta": float(deltas.mean()),
        "se_delta": float(math.sqrt(corrected_var)),
        "deltas": deltas.tolist(),
        "dof": n - 1,
    }


def commit_threshold(se_delta: float, dof: int, n_tests: int, alpha: float = 0.05) -> float:
    """t-distribution critical value (not z -- with only ~14 degrees of
    freedom the gap matters) times se_delta, at a one-sided alpha
    Bonferroni-corrected for n_tests look-backs in one run
    (config.MAX_ITERATIONS by default). An approximate, conservative bound
    -- see paired_delta_corrected's docstring on what this does and does
    not guarantee."""
    if dof < 1:
        return float("inf")
    corrected_alpha = alpha / max(n_tests, 1)
    t_crit = scipy_stats.t.ppf(1 - corrected_alpha, dof)
    return float(t_crit * se_delta)


def clears_bar(delta: float, threshold: float) -> bool:
    """The ONE commit rule. Requires a strictly positive delta as well as delta >= bar:
    when two conditions produce identical predictions in every fold (e.g. LR with
    fill_unknown vs the NaN indicator column) the paired SE is 0, the bar collapses to
    0, and 'delta >= bar' (0 >= 0) would commit a no-op."""
    return delta > 0 and delta >= threshold


def load_raw_dataset() -> pd.DataFrame:
    """Load adult.csv and normalize the real '?' missing-value marker to an
    actual NaN so downstream code (profiler, executor) can use pandas'
    native null-detection instead of string matching.

    Uses pd.api.types.is_string_dtype rather than a literal `col.dtype ==
    object` check -- newer pandas (observed: 2.3.3 on Windows/Python 3.14)
    can infer text columns as its dedicated StringDtype instead of the
    legacy numpy object dtype, and the literal check silently skipped
    those columns, leaving every '?' un-replaced (null_pct showed 0.0
    everywhere). is_string_dtype covers both cases.

    The dataframe's default RangeIndex (0..N-1) after read_csv IS the
    "row ID" used throughout the fixed-fold evaluator -- executor.py's
    _drop_rows deliberately preserves this index rather than resetting
    it, so a row's identity survives any cleaning operation."""
    df = pd.read_csv(config.DATA_PATH)
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().replace("?", pd.NA)
    return df


if __name__ == "__main__":
    df = load_raw_dataset()
    baseline_f1 = calculate_f1(df)
    print(f"Baseline F1 (real '?' missingness present, as-is): {baseline_f1:.4f}")
    missing_rows = df[config.KNOWN_MISSING_COLUMNS].isna().any(axis=1).sum()
    print(f"Rows with missing values in {config.KNOWN_MISSING_COLUMNS}: {missing_rows} / {len(df)} ({100*missing_rows/len(df):.1f}%)")
