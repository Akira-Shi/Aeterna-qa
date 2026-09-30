"""
Data quality profiler for AETERNA-QA.

Reports, per column: dtype, null percentage, and (numeric columns only) a
naive IQR-based outlier count. The IQR check is known to be unreliable on
skewed columns (see Documentation.md) -- it's kept in the report for
completeness and because clip_outliers stays in the operation menu, but
the planner should be steered toward null_pct as the primary signal this
milestone, not outlier_count.
"""
import pandas as pd

from . import config


def _iqr_outlier_count(series: pd.Series) -> int:
    s = series.dropna()
    if s.empty:
        return 0
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((s < lower) | (s > upper)).sum())


def profile(df: pd.DataFrame) -> dict:
    """Return {column: {dtype, null_pct, outlier_count}} for every column
    except the target. outlier_count is only computed for numeric dtypes;
    non-numeric columns get None, not 0, so the planner can tell
    "not applicable" apart from "checked, found none"."""
    report = {}
    n = len(df)
    for col in df.columns:
        if col == config.TARGET_COLUMN:
            continue
        s = df[col]
        null_pct = round(100 * s.isna().sum() / n, 2)
        if pd.api.types.is_numeric_dtype(s):
            outlier_count = _iqr_outlier_count(s)
        else:
            outlier_count = None
        report[col] = {
            "dtype": str(s.dtype),
            "null_pct": null_pct,
            "outlier_count": outlier_count,
        }
    return report


if __name__ == "__main__":
    from .evaluator import load_raw_dataset
    import json

    df = load_raw_dataset()
    result = profile(df)
    print(json.dumps(result, indent=2))
    flagged = [c for c, r in result.items() if r["null_pct"] > 0]
    print(f"\nColumns with any missingness: {flagged}")
    assert set(flagged) == set(config.KNOWN_MISSING_COLUMNS), (
        f"Expected exactly {config.KNOWN_MISSING_COLUMNS} to show missingness, got {flagged}"
    )
    print("OK: profiler correctly isolates the known real-missingness columns.")
