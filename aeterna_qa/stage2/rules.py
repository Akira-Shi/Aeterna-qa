"""Stage 2 rule table: (task_type, model_family, column profile) -> preprocessing steps.

Deterministic, no LLM. Every Step carries rule_id, reason and alternative so the choice can be shown and overridden.
Stages: imputation, encoding (categorical), scaling (numeric), imbalance (classification, estimator level).
For each column and stage the FIRST matching rule in COLUMN_RULES wins.

Thresholds live in stage2/constants.py (product defaults, not tuned on any study dataset).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

TASK_TYPES = ("binary", "multiclass", "regression")
FAMILIES = ("linear", "tree_ensemble", "distance", "neural")

from .constants import SKEW_LIMIT, HIGH_CARD, MISSING_INFORMATIVE, IMBALANCE_RATIO  # noqa: E402,F401  (see constants.py)


class UnsupportedModel(ValueError):
    """The model cannot be mapped to a supported family."""


# exact sklearn / common class names (lower-case, no separators)
_KNOWN = {
    "logisticregression": "linear", "linearregression": "linear", "ridge": "linear", "lasso": "linear",
    "elasticnet": "linear", "sgdclassifier": "linear", "sgdregressor": "linear", "linearsvc": "linear",
    "randomforestclassifier": "tree_ensemble", "randomforestregressor": "tree_ensemble",
    "extratreesclassifier": "tree_ensemble", "extratreesregressor": "tree_ensemble",
    "gradientboostingclassifier": "tree_ensemble", "gradientboostingregressor": "tree_ensemble",
    "histgradientboostingclassifier": "tree_ensemble", "histgradientboostingregressor": "tree_ensemble",
    "kneighborsclassifier": "distance", "kneighborsregressor": "distance", "svc": "distance", "svr": "distance",
    "mlpclassifier": "neural", "mlpregressor": "neural",
}
# substring hints for the nearest-family fallback, checked in order
_HINTS = (("forest", "tree_ensemble"), ("boost", "tree_ensemble"), ("xgb", "tree_ensemble"), ("lgbm", "tree_ensemble"),
          ("tree", "tree_ensemble"),
          ("neighbor", "distance"), ("knn", "distance"), ("svm", "distance"), ("svc", "distance"), ("svr", "distance"),
          ("mlp", "neural"), ("neural", "neural"), ("perceptron", "neural"),
          ("logistic", "linear"), ("linear", "linear"), ("ridge", "linear"), ("lasso", "linear"), ("elastic", "linear"),
          ("regress", "linear"))


def resolve_family(model) -> str:
    """Family name, model name, class or instance -> one of FAMILIES. An unknown name maps to the nearest family
    (name-substring match) with a UserWarning; no match raises UnsupportedModel."""
    if not isinstance(model, str):
        model = model.__name__ if isinstance(model, type) else type(model).__name__
    low = model.strip().lower()
    if low in FAMILIES:
        return low
    key = low.replace("_", "").replace("-", "").replace(" ", "")
    if key in _KNOWN:
        return _KNOWN[key]
    for hint, fam in _HINTS:
        if hint in key:
            warnings.warn(f"model {model!r} is not a known model; using nearest family {fam!r} (matched {hint!r})",
                          UserWarning, stacklevel=2)
            return fam
    raise UnsupportedModel(f"model {model!r} is not supported; supported families: {FAMILIES}")


@dataclass(frozen=True)
class ColProfile:
    name: str
    kind: str            # "numeric" | "categorical"
    missing_frac: float
    skew: float          # numeric only, else 0.0
    n_unique: int


@dataclass(frozen=True)
class Step:
    stage: str           # imputation | encoding | scaling | imbalance
    columns: tuple       # () for estimator-level steps
    method: str
    rule_id: str
    reason: str
    alternative: str
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["columns"] = list(self.columns)
        return d


def profile_columns(X: pd.DataFrame) -> dict:
    out = {}
    for c in X.columns:
        s = X[c]
        numeric = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        skew = 0.0
        if numeric:
            v = s.dropna()
            if len(v) > 2 and v.nunique() > 1:
                skew = float(v.skew())
                if not np.isfinite(skew):
                    skew = 0.0
        out[c] = ColProfile(c, "numeric" if numeric else "categorical", float(s.isna().mean()), skew,
                            int(s.nunique(dropna=True)))
    return out


def _num(p): return p.kind == "numeric"
def _cat(p): return p.kind == "categorical"
def _skewed(p): return abs(p.skew) > SKEW_LIMIT


# (rule_id, stage, applies(task_type, family, profile), method, reason, alternative)
COLUMN_RULES = [
    # imputation (only columns that have missing values)
    ("IMP-N1", "imputation", lambda t, f, p: _num(p) and p.missing_frac > 0 and f == "tree_ensemble",
     "median+indicator", "Trees split on the value: fill with the median and add a missing-indicator column so the missingness stays visible.",
     "mean fill, no indicator"),
    ("IMP-N2", "imputation", lambda t, f, p: _num(p) and p.missing_frac > 0 and _skewed(p),
     "median", "Skewed numeric column: the mean is pulled by the tail, the median is not.", "mean fill"),
    ("IMP-N3", "imputation", lambda t, f, p: _num(p) and p.missing_frac > 0,
     "mean", "Roughly symmetric numeric column: the mean keeps the column mean unchanged.", "median fill"),
    ("IMP-C1", "imputation", lambda t, f, p: _cat(p) and p.missing_frac >= MISSING_INFORMATIVE,
     "constant_missing", f"At least {MISSING_INFORMATIVE:.0%} of the values are missing: keep 'missing' as its own level instead of guessing.",
     "most frequent value"),
    ("IMP-C2", "imputation", lambda t, f, p: _cat(p) and p.missing_frac > 0,
     "most_frequent", f"Fewer than {MISSING_INFORMATIVE:.0%} missing: the most frequent level is the least disruptive fill.",
     "constant 'missing' level"),
    # encoding (categorical)
    ("ENC-T1", "encoding", lambda t, f, p: _cat(p) and f == "tree_ensemble",
     "ordinal", "Trees do not need one-hot columns; ordinal codes keep the matrix narrow at any cardinality.", "one-hot"),
    ("ENC-H1", "encoding", lambda t, f, p: _cat(p) and p.n_unique > HIGH_CARD,
     "onehot_capped", f"More than {HIGH_CARD} levels: one-hot with rare levels grouped into one 'infrequent' column (at most {HIGH_CARD} columns).",
     "ordinal codes (imposes an order), or drop the column"),
    ("ENC-L1", "encoding", lambda t, f, p: _cat(p),
     "onehot", "Linear, distance and neural models need an unordered encoding: one-hot.", "ordinal codes (imposes an order)"),
    # scaling (numeric)
    ("SCL-T1", "scaling", lambda t, f, p: _num(p) and f == "tree_ensemble",
     "none", "Trees are invariant to monotone scaling; leave the column as is.", "standard scaling"),
    ("SCL-S1", "scaling", lambda t, f, p: _num(p) and _skewed(p) and f in ("linear", "neural"),
     "yeo_johnson", "Skewed numeric column and a model that prefers roughly symmetric inputs: Yeo-Johnson, then standardise (handles zeros and negatives).",
     "standard scaling"),
    ("SCL-D1", "scaling", lambda t, f, p: _num(p) and _skewed(p) and f == "distance",
     "robust", "Skewed column and a distance model: median/IQR scaling stops a long tail from dominating distances.", "standard scaling"),
    ("SCL-G1", "scaling", lambda t, f, p: _num(p),
     "standard", "Scale-sensitive model: zero mean and unit variance so every column has a comparable range.", "robust scaling"),
]
_STAGE_ORDER = {"imputation": 0, "encoding": 1, "scaling": 2}


def _imbalance_step(task_type, family, y):
    if task_type == "regression" or y is None:
        return None
    counts = pd.Series(y).value_counts()
    if len(counts) < 2 or counts.min() / counts.max() >= IMBALANCE_RATIO:
        return None
    share = counts.min() / counts.max()
    alt = "resample (needs imbalanced-learn, not a dependency)"
    if family in ("linear", "tree_ensemble"):
        return Step("imbalance", (), "class_weight_balanced", "IMB-1",
                    f"Smallest class is {share:.0%} of the largest (below {IMBALANCE_RATIO:.0%}): weight classes inversely to their frequency.",
                    alt, {"class_weight": "balanced"})
    return Step("imbalance", (), "none", "IMB-2",
                f"Smallest class is {share:.0%} of the largest, but this estimator family has no class_weight in scikit-learn; nothing is applied.",
                alt)


def recommend(task_type: str, family: str, X: pd.DataFrame, y=None) -> list:
    """Deterministic steps for the feature frame X (target, id and dropped columns already removed) and target y."""
    if task_type not in TASK_TYPES:
        raise ValueError(f"task_type must be one of {TASK_TYPES}, got {task_type!r}")
    if family not in FAMILIES:
        raise UnsupportedModel(f"family must be one of {FAMILIES}, got {family!r}")
    groups, meta = {}, {}
    for col, p in profile_columns(X).items():
        done = set()
        for rid, stage, when, method, reason, alt in COLUMN_RULES:
            if stage in done or not when(task_type, family, p):
                continue
            done.add(stage)
            groups.setdefault((stage, rid), []).append(col)
            meta[(stage, rid)] = (method, reason, alt)
    steps = []
    for stage, rid in sorted(groups, key=lambda k: (_STAGE_ORDER[k[0]], k[1])):
        method, reason, alt = meta[(stage, rid)]
        steps.append(Step(stage, tuple(groups[(stage, rid)]), method, rid, reason, alt))
    imb = _imbalance_step(task_type, family, y)
    if imb is not None:
        steps.append(imb)
    return steps
