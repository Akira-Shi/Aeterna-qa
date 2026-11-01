"""Stage 2 builder: recommended steps -> an UNFITTED sklearn Pipeline (ColumnTransformer + estimator).

Nothing is fitted here. `fit_on_train` fits on the training rows only. `save_pipeline` writes the (unfitted or
fitted) pipeline with joblib, plus a sidecar JSON with the steps (rule_id, reason, alternative).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (OneHotEncoder, OrdinalEncoder, PowerTransformer, RobustScaler, StandardScaler)

from modules import config
from .rules import Step, FAMILIES, TASK_TYPES, UnsupportedModel

_MISSING_LEVEL = "__missing__"
_CAP = 15


def _transformer(stage: str, method: str):
    if stage == "imputation":
        return {
            "median": lambda: SimpleImputer(strategy="median"),
            "mean": lambda: SimpleImputer(strategy="mean"),
            "median+indicator": lambda: SimpleImputer(strategy="median", add_indicator=True),
            "most_frequent": lambda: SimpleImputer(strategy="most_frequent"),
            "constant_missing": lambda: SimpleImputer(strategy="constant", fill_value=_MISSING_LEVEL),
        }[method]()
    if stage == "encoding":
        return {
            "onehot": lambda: OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            "onehot_capped": lambda: OneHotEncoder(handle_unknown="infrequent_if_exist", max_categories=_CAP, sparse_output=False),
            "ordinal": lambda: OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
        }[method]()
    if stage == "scaling":
        return {
            "none": lambda: "passthrough",
            "standard": lambda: StandardScaler(),
            "robust": lambda: RobustScaler(),
            "yeo_johnson": lambda: PowerTransformer(method="yeo-johnson", standardize=True),
        }[method]()
    raise ValueError(f"no transformer for stage {stage!r}")


def make_estimator(task_type: str, family: str, class_weight=None):
    if task_type not in TASK_TYPES:
        raise ValueError(f"task_type must be one of {TASK_TYPES}")
    if family not in FAMILIES:
        raise UnsupportedModel(f"family must be one of {FAMILIES}")
    rs = config.RANDOM_STATE
    clf = task_type != "regression"
    if family == "linear":
        return LogisticRegression(max_iter=1000, class_weight=class_weight, random_state=rs) if clf else Ridge()
    if family == "tree_ensemble":
        return (RandomForestClassifier(n_estimators=100, class_weight=class_weight, random_state=rs, n_jobs=-1) if clf
                else RandomForestRegressor(n_estimators=100, random_state=rs, n_jobs=-1))
    if family == "distance":
        return KNeighborsClassifier() if clf else KNeighborsRegressor()
    return (MLPClassifier(hidden_layer_sizes=(64,), max_iter=300, random_state=rs) if clf
            else MLPRegressor(hidden_layer_sizes=(64,), max_iter=300, random_state=rs))


def build_pipeline(steps, task_type: str, family: str) -> Pipeline:
    """Unfitted Pipeline([('prep', ColumnTransformer), ('model', estimator)]) from the recommended steps."""
    per_col: dict = {}
    class_weight = None
    for st in steps:
        if st.stage == "imbalance":
            class_weight = st.params.get("class_weight")
            continue
        for c in st.columns:
            per_col.setdefault(c, []).append(st)
    chains: dict = {}
    for c, sts in per_col.items():
        sts = sorted(sts, key=lambda s: {"imputation": 0, "encoding": 1, "scaling": 2}[s.stage])
        chains.setdefault(tuple((s.stage, s.method) for s in sts), []).append(c)
    blocks = []
    for i, (chain, cols) in enumerate(chains.items()):
        parts = [(f"{stage}_{method}", _transformer(stage, method)) for stage, method in chain]
        parts = [p for p in parts if p[1] != "passthrough"]
        inner = "passthrough" if not parts else Pipeline(parts)
        blocks.append((f"g{i}", inner, cols))
    prep = ColumnTransformer(blocks, remainder="drop", verbose_feature_names_out=False)
    return Pipeline([("prep", prep), ("model", make_estimator(task_type, family, class_weight))])


def build_default(X, task_type: str, family: str) -> Pipeline:
    """The baseline: median fill + one-hot + standard scaling (most-frequent fill for categoricals), same estimator."""
    from .rules import profile_columns
    num = [c for c, p in profile_columns(X).items() if p.kind == "numeric"]
    cat = [c for c, p in profile_columns(X).items() if p.kind == "categorical"]
    blocks = []
    if num:
        blocks.append(("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num))
    if cat:
        blocks.append(("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                        ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat))
    prep = ColumnTransformer(blocks, remainder="drop", verbose_feature_names_out=False)
    return Pipeline([("prep", prep), ("model", make_estimator(task_type, family))])


def fit_on_train(pipe: Pipeline, X, y, train_index):
    """Fit on the training rows only (rows selected by index label); returns the fitted pipeline."""
    return pipe.fit(X.loc[train_index], y.loc[train_index])


def save_pipeline(pipe: Pipeline, path, steps=None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, path)
    if steps is not None:
        path.with_suffix(path.suffix + ".steps.json").write_text(
            json.dumps([s.to_dict() for s in steps], indent=2), encoding="utf-8")
    return path
