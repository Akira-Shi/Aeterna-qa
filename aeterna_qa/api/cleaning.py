"""Cleaned-CSV writer. Applies ONLY the committed ops, with every fitted parameter (fill value, clip bounds,
sentinel median, canonical spellings) fitted on the TRAINING rows and then applied to all rows. Never refits on
the full file. Uses executor.fit_and_apply (public, v1) unchanged; pipeline.py is not touched.

Row-level ops follow the evaluator's policy: drop_rows / dedupe_rows remove TRAINING rows only; rows outside the
training split are never dropped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from modules import config, executor

TRAIN_FRAC = 0.8


def split_train_index(df: pd.DataFrame, target: str, stratify: bool = True) -> list:
    """Deterministic 80/20 split (random_state=config.RANDOM_STATE). Returns the TRAINING row labels of df."""
    strat = None
    if stratify and target in df.columns and df[target].nunique() <= 20:
        vc = df[target].astype(str).value_counts()
        if vc.min() >= 2:
            strat = df[target].astype(str)
    tr, _ = train_test_split(df.index.to_numpy(), train_size=TRAIN_FRAC, random_state=config.RANDOM_STATE, stratify=strat)
    return sorted(tr.tolist())


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


def clean_with_train_fit(df: pd.DataFrame, committed_ops: dict, train_index) -> tuple[pd.DataFrame, list]:
    """df: prepared dataset (unique index labels). Returns (cleaned_df, fitted) where fitted lists, per op, the
    parameters fitted on the training rows."""
    train_cur = df.loc[list(train_index)].copy()
    full = df.copy()
    fitted = []
    for column, op in committed_ops.items():
        params = None
        if op not in ("drop_rows", "dedupe_rows"):
            params = _jsonable(executor._fit_stat(train_cur[column], op, column))   # recorded for the audit only
        new_train, new_full = executor.fit_and_apply(train_cur, full, column, op)
        removed = train_cur.index.difference(new_train.index)
        full = new_full.drop(index=removed)
        train_cur = new_train
        fitted.append({"column": column, "operation": op, "fitted_on": "training rows only",
                       "n_train_rows": int(len(train_cur) + len(removed)), "params": params,
                       "train_rows_removed": int(len(removed))})
    return full, fitted
