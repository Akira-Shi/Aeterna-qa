p = "modules/evaluator.py"
s = open(p, encoding="utf-8").read()

old = '''def calculate_f1_candidate(committed_df: pd.DataFrame, raw_df: pd.DataFrame, folds,
                            candidate_ops: dict[str, str] | None = None) -> dict:
    """THE accept/commit measurement (2026-09-29, third pass -- fixes a
    real fit/apply bug found by review, see module docstring in
    executor.py). `folds` must come from make_fixed_folds(raw_df),
    computed once per run and reused for every call.

    `committed_df` reflects every operation already CONFIRMED in this run
    (a fixed, finalized preprocessing state -- fills baked in via
    executor.execute, drops already removed). `candidate_ops` (optional)
    is the NOT-YET-decided operation(s) being evaluated on top of that --
    for each fold, these are fit ONLY on that fold's training rows
    (executor.fit_and_apply) and applied consistently to both that fold's
    train and test rows. Calling with candidate_ops=None (or {}) evaluates
    committed_df as-is, with no new candidate layered on.

    Per fold: training rows come from committed_df intersected with the
    fold's train row IDs (so an already-committed or candidate drop_rows
    legitimately shrinks what's available for training); test rows come
    from committed_df intersected with the fold's test row IDs too (NOT
    raw_df) -- this reflects already-CONFIRMED transforms (they're now a
    real, permanent part of the pipeline) while candidate_ops are still
    fit fold-locally to avoid leakage. If a prior commit already dropped
    a row for good, it is legitimately absent from every fold from then
    on; a NOT-yet-committed candidate's drop_rows never removes a row
    from a test split, only from training, for exactly this fold's
    evaluation.

    Returns: {"mean", "std", "scores", "n_train", "n_test"} where scores[i]
    corresponds to folds[i] (enabling paired_delta_corrected below), and
    n_train/n_test are the (approximate, stratified-k-fold-typical) per-fold
    training/test set sizes needed for the Nadeau-Bengio SE correction.
    """
    candidate_ops = candidate_ops or {}
    y_committed = (committed_df[config.TARGET_COLUMN].astype(str).str.strip() == config.POSITIVE_CLASS).astype(int)
    scores = []
    n_trains, n_tests = [], []
    for train_idx, test_idx in folds:
        train_avail = train_idx.intersection(committed_df.index)
        test_avail = test_idx.intersection(committed_df.index)
        train_df = committed_df.loc[train_avail]
        test_df = committed_df.loc[test_avail]

        for column, operation in candidate_ops.items():
            train_df, test_df = fit_and_apply(train_df, test_df, column, operation)

        X_train, X_test = _encode_train_test(train_df, test_df)
        y_train = y_committed.loc[train_df.index]
        y_test = y_committed.loc[test_df.index]
        clf = RandomForestClassifier(random_state=config.RANDOM_STATE, n_jobs=-1)
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        scores.append(f1_score(y_test, preds))
        n_trains.append(len(train_df))
        n_tests.append(len(test_df))
    scores = np.array(scores)
    return {
        "mean": float(scores.mean()),
        "std": float(scores.std(ddof=1)),
        "scores": scores.tolist(),
        "n_train": float(np.mean(n_trains)),
        "n_test": float(np.mean(n_tests)),
    }'''

new = '''def materialize(raw_df: pd.DataFrame, committed_ops: dict[str, str]) -> pd.DataFrame:
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


def calculate_f1_candidate(raw_df: pd.DataFrame, folds, committed_ops: dict[str, str] | None = None,
                            candidate_ops: dict[str, str] | None = None) -> dict:
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
    committed_ops = committed_ops or {}
    candidate_ops = candidate_ops or {}
    all_ops = {**committed_ops, **candidate_ops}
    y_raw = (raw_df[config.TARGET_COLUMN].astype(str).str.strip() == config.POSITIVE_CLASS).astype(int)
    scores = []
    n_trains, n_tests = [], []
    for train_idx, test_idx in folds:
        train_df = raw_df.loc[train_idx]
        test_df = raw_df.loc[test_idx]

        for column, operation in all_ops.items():
            train_df, test_df = fit_and_apply(train_df, test_df, column, operation)

        X_train, X_test = _encode_train_test(train_df, test_df)
        y_train = y_raw.loc[train_df.index]
        y_test = y_raw.loc[test_df.index]
        clf = RandomForestClassifier(random_state=config.RANDOM_STATE, n_jobs=-1)
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        scores.append(f1_score(y_test, preds))
        n_trains.append(len(train_df))
        n_tests.append(len(test_df))
    scores = np.array(scores)
    return {
        "mean": float(scores.mean()),
        "std": float(scores.std(ddof=1)),
        "scores": scores.tolist(),
        "n_train": float(np.mean(n_trains)),
        "n_test": float(np.mean(n_tests)),
    }'''

assert old in s
s = s.replace(old, new)

# executor.execute is now used by materialize() (profiling-only helper)
old_import = "from .executor import fit_and_apply"
new_import = "from .executor import fit_and_apply, execute"
assert old_import in s
s = s.replace(old_import, new_import)

open(p, "w", encoding="utf-8").write(s)
print("evaluator.py patched")
