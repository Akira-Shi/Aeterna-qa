"""Cleaning recipe: the committed ops with their fitted parameters, and a writer/replayer.

fit=True fits every parameter on the frame it is given (the FULL upload) and returns the recipe;
fit=False replays saved parameters without refitting. drop_rows / dedupe_rows remove all affected rows.
Uses executor._fit_stat / _apply_stat (v1, unchanged), the same code the pipeline's own execute() uses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modules import executor

FITTED_ON = "full_upload"
NOTE = "Fitted on your full upload; if you split your data, refit with the recipe on training rows."
ROW_OPS = ("drop_rows", "dedupe_rows")


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if pd.isna(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _apply(df: pd.DataFrame, op: str, column: str, params) -> pd.DataFrame:
    if op == "drop_rows":
        return df[df[column].notna()].copy()
    if op == "dedupe_rows":
        return df[~df.duplicated(keep="first")].copy()
    out = df.copy()
    out[column] = executor._apply_stat(out[column], op, params)
    return out


def apply_recipe(df: pd.DataFrame, recipe: list, fit: bool = False):
    """recipe: list of {"op", "column", ("params")}. Returns (cleaned_df, recipe_with_params)."""
    cur, out = df, []
    for r in recipe:
        op, column = r["op"], r["column"]
        if op in ROW_OPS:
            params = None
        elif fit:
            params = executor._fit_stat(cur[column], op, column)
        else:
            params = r["params"]
        before = len(cur)
        cur = _apply(cur, op, column, params)
        out.append({"op": op, "column": column, "params": _jsonable(params), "fitted_on": FITTED_ON,
                    "rows_removed": before - len(cur)})
    return cur, out


def recipe_from_ops(committed_ops: dict) -> list:
    return [{"op": op, "column": col} for col, op in committed_ops.items()]
