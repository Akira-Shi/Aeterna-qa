"""
Executor for AETERNA-QA.

Applies one operation to one column via a plain dict-to-function map --
no exec(), no code generation, no freeform transformation of any kind.
This is a deliberate safety/reliability choice (see Documentation.md,
2026-09-04 decision, carried forward): freeform exec() on LLM output is a
real code-injection risk and a debugging sink from hallucinated syntax; a
fixed menu is faster to build, safer, and still demonstrates LLM
reasoning (it's choosing among options, not writing code).

Two entry points, for two different, deliberately separate jobs (2026-09-29,
third pass -- a review found that using only the first for candidate
evaluation was a real bug):

- fit_and_apply(train_df, test_df, column, operation): used to EVALUATE a
  not-yet-decided candidate operation. Fits any needed statistic (a mean,
  median, mode, or clip bound) from TRAINING data only, then applies that
  SAME fitted value to both train and test. This is what makes the
  evaluation match how the operation would actually behave in deployment
  -- fit once on data you have, apply to new data as it arrives, missing
  or not. Before this fix, fill-type operations were applied globally
  before fold-splitting, which meant training data ended up with zero
  missingness in the column while test data (always drawn from the raw,
  unmodified dataset) still had real missingness there -- a train/test
  mismatch that made the "before/after" comparison measure something
  incoherent, not the operation's real effect. drop_rows is the
  exception: it only ever removes TRAINING rows. Test rows are never
  dropped -- the model must always be scored on every original test row.
  A test row still missing this column simply keeps its real, unfilled
  value and falls to the model's own missingness handling (the one-hot
  encoding's dedicated NaN indicator column) -- that IS the fallback
  policy, made explicit here rather than left implicit.

- execute(df, column, operation): used to FINALIZE an operation ONCE a
  chain has already been decided (committed) via fit_and_apply-based
  evaluation. Fits on and applies to the whole dataframe -- appropriate
  here because the decision has already been made and this is just
  materializing it as a real, permanent preprocessing step, the same way
  a production pipeline bakes in a confirmed transform. Never use this
  function to evaluate whether a candidate operation should be accepted.
"""
import pandas as pd

from .detectors import find_sentinel_value, find_unit_shift, norm_key

_NUMERIC_ONLY = {"fill_mean", "fill_median", "clip_outliers", "sentinel_to_median", "rescale_units"}
_TEXT_ONLY = {"normalize_categories"}
_ROW_LEVEL = {"dedupe_rows"}  # act on whole rows; column key is "*"


def _fit_stat(train_col: pd.Series, operation: str, column: str):
    """Compute whatever statistic `operation` needs from TRAINING data
    only. Returns None for operations that need no fitted statistic
    (drop_rows)."""
    if operation == "fill_mean":
        return train_col.mean()
    if operation == "fill_median":
        return train_col.median()
    if operation == "fill_mode":
        mode_series = train_col.mode(dropna=True)
        if mode_series.empty:
            raise ValueError(f"Cannot compute mode for '{column}' -- no non-null training values.")
        return mode_series.iloc[0]
    if operation == "clip_outliers":
        s = train_col.dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            raise ValueError(f"clip_outliers refused on '{column}': IQR is 0 (mostly one value), "
                             f"clipping would flatten the column to that value")
        return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    if operation == "fill_unknown":
        return "Unknown"
    if operation == "sentinel_to_median":
        sv = find_sentinel_value(train_col)
        if sv is None:
            return (None, None)  # nothing to repair in the training rows -> no-op
        return (sv, train_col[train_col != sv].median())
    if operation == "rescale_units":
        fit = find_unit_shift(train_col)
        return fit if fit is not None else (None, None)  # no shift found in training rows -> no-op
    if operation == "normalize_categories":
        # canonical spelling per normalised key = the most frequent raw form in TRAINING
        s = train_col.dropna().astype(str)
        canon = {}
        for key, grp in s.groupby(s.map(norm_key)):
            canon[key] = grp.value_counts().index[0]
        return canon
    raise ValueError(f"Unknown operation '{operation}'. Valid: {list(_OPERATIONS)}")


def _apply_stat(series: pd.Series, operation: str, stat) -> pd.Series:
    if operation == "clip_outliers":
        lower, upper = stat
        return series.clip(lower=lower, upper=upper)
    if operation == "fill_unknown":
        return series.astype(object).where(series.notna(), stat)
    if operation == "sentinel_to_median":
        sv, med = stat
        return series if sv is None else series.mask(series == sv, med)
    if operation == "rescale_units":
        cut, factor = stat
        return series if cut is None else series.mask(series > cut, series / factor)
    if operation == "normalize_categories":
        return series.map(lambda x: stat.get(norm_key(x), x) if isinstance(x, str) else x)
    # fill_mean / fill_median / fill_mode all reduce to a plain fillna
    return series.fillna(stat)


def fit_and_apply(train_df: pd.DataFrame, test_df: pd.DataFrame, column: str, operation: str):
    """Fit `operation` on train_df[column] only, apply consistently to
    both train_df and test_df. Returns (new_train_df, new_test_df), both
    copies -- inputs are never mutated. Raises ValueError for an unknown
    operation, missing column, or a dtype mismatch (e.g. fill_mean on a
    categorical column)."""
    if operation not in _OPERATIONS:
        raise ValueError(f"Unknown operation '{operation}'. Valid: {list(_OPERATIONS)}")
    if operation in _ROW_LEVEL:
        # Whole-row op: drops exact duplicates from TRAINING only; test rows are
        # never touched (same policy as drop_rows -- never grade on an easier set).
        new_train = train_df[~train_df.duplicated(keep="first")].copy()
        return new_train, test_df.copy()
    for df, name in [(train_df, "train_df"), (test_df, "test_df")]:
        if column not in df.columns:
            raise ValueError(f"Unknown column '{column}' in {name}")
    if operation in _TEXT_ONLY and pd.api.types.is_numeric_dtype(train_df[column]):
        raise ValueError(f"{operation} requires a text column, got dtype {train_df[column].dtype} for '{column}'")
    if operation in _NUMERIC_ONLY and not pd.api.types.is_numeric_dtype(train_df[column]):
        raise ValueError(f"{operation} requires a numeric column, got dtype {train_df[column].dtype} for '{column}'")

    if operation == "drop_rows":
        # Training-only: test rows are NEVER dropped (see module docstring).
        new_train = train_df[train_df[column].notna()].copy()
        return new_train, test_df.copy()

    stat = _fit_stat(train_df[column], operation, column)
    new_train = train_df.copy()
    new_test = test_df.copy()
    new_train[column] = _apply_stat(new_train[column], operation, stat)
    new_test[column] = _apply_stat(new_test[column], operation, stat)
    return new_train, new_test


def _fill_mean(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"fill_mean requires a numeric column, got dtype {df[column].dtype} for '{column}'")
    out = df.copy()
    out[column] = out[column].fillna(out[column].mean())
    return out


def _fill_median(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"fill_median requires a numeric column, got dtype {df[column].dtype} for '{column}'")
    out = df.copy()
    out[column] = out[column].fillna(out[column].median())
    return out


def _fill_mode(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = df.copy()
    mode_series = out[column].mode(dropna=True)
    if mode_series.empty:
        raise ValueError(f"Cannot compute mode for '{column}' -- no non-null values.")
    out[column] = out[column].fillna(mode_series.iloc[0])
    return out


def _drop_rows(df: pd.DataFrame, column: str) -> pd.DataFrame:
    # Deliberately does NOT reset_index: row identity must survive so the
    # fixed-fold evaluator can always recover a row's original raw values.
    return df[df[column].notna()].copy()


def _clip_outliers(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"clip_outliers requires a numeric column, got dtype {df[column].dtype} for '{column}'")
    out = df.copy()
    s = out[column].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        raise ValueError(f"clip_outliers refused on '{column}': IQR is 0 (mostly one value), "
                         f"clipping would flatten the column to that value")
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    out[column] = out[column].clip(lower=lower, upper=upper)
    return out


def _fill_unknown(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = df.copy()
    out[column] = out[column].astype(object).where(out[column].notna(), "Unknown")
    return out


def _via_fit_and_apply(operation):
    """Finalize a fitted op on the whole dataframe: fit on all rows, apply to all rows."""
    def _run(df: pd.DataFrame, column: str) -> pd.DataFrame:
        return fit_and_apply(df, df.iloc[0:0].copy(), column, operation)[0]
    return _run


_OPERATIONS = {
    "normalize_categories": _via_fit_and_apply("normalize_categories"),
    "sentinel_to_median": _via_fit_and_apply("sentinel_to_median"),
    "rescale_units": _via_fit_and_apply("rescale_units"),
    "dedupe_rows": _via_fit_and_apply("dedupe_rows"),
    "fill_mean": _fill_mean,
    "fill_median": _fill_median,
    "fill_mode": _fill_mode,
    "drop_rows": _drop_rows,
    "clip_outliers": _clip_outliers,
    "fill_unknown": _fill_unknown,
}


def execute(df: pd.DataFrame, column: str, operation: str) -> pd.DataFrame:
    """FINALIZE an already-decided operation across the whole dataframe --
    see module docstring. Do NOT use this to evaluate a candidate; use
    fit_and_apply for that."""
    if operation not in _OPERATIONS:
        raise ValueError(f"Unknown operation '{operation}'. Valid: {list(_OPERATIONS)}")
    if column not in df.columns and operation not in _ROW_LEVEL:
        raise ValueError(f"Unknown column '{column}'")
    return _OPERATIONS[operation](df, column)
