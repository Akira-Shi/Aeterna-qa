"""Stage 2 comparison: recommended pipeline vs the default (median fill + one-hot + scale) on the evaluator's fixed
5x3 folds. REPORT ONLY: mean paired difference and its Nadeau-Bengio corrected SE. No gate, no commit rule, no threshold.

Metric: negative Brier (higher is better), the study's gate metric, shown with F1. Binary targets only; for
multiclass / regression the comparison is not supported (no gate is invented).

The evaluator is imported read-only (make_fixed_folds, paired_delta_corrected); both pipelines are fitted inside each
fold on the training rows only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import brier_score_loss, f1_score

from modules import taskspec
from modules.evaluator import make_fixed_folds, paired_delta_corrected
from .build import build_default, build_pipeline
from .rules import recommend


class CompareNotSupported(ValueError):
    """Comparison needs the binary gate folds; other task types are not supported."""


def compare(df: pd.DataFrame, spec, steps=None) -> dict:
    """df: the loaded dataset (target included). spec: TaskSpec (binary). steps: recommended steps, or None to
    compute them from df. Returns a report dict."""
    if spec.task_type != "binary":
        raise CompareNotSupported("comparison not supported: the fixed-fold evaluator is binary only (no gate is invented)")
    drop = [spec.target, *spec.id_columns, *spec.drop_columns]
    X = df.drop(columns=[c for c in drop if c in df.columns])
    pos = taskspec.resolve_positive_label(spec, df)
    with taskspec.applied(spec, positive_label=pos):
        folds = make_fixed_folds(df)
    y = (df[spec.target].astype(str).str.strip() == pos).astype(int)
    if steps is None:
        steps = recommend(spec.task_type, spec.model_family, X, y)
    rec = build_pipeline(steps, spec.task_type, spec.model_family)
    base = build_default(X, spec.task_type, spec.model_family)
    s_rec, s_base, f_rec, f_base, n_tr, n_te = [], [], [], [], [], []
    for tr, te in folds:
        res = []
        for pipe in (base, rec):
            m = clone(pipe).fit(X.loc[tr], y.loc[tr])
            p = m.predict_proba(X.loc[te])[:, 1]
            res.append((-brier_score_loss(y.loc[te], p), f1_score(y.loc[te], (p >= 0.5).astype(int), zero_division=0)))
        s_base.append(res[0][0]); s_rec.append(res[1][0])
        f_base.append(res[0][1]); f_rec.append(res[1][1])
        n_tr.append(len(tr)); n_te.append(len(te))
    ntr, nte = float(np.mean(n_tr)), float(np.mean(n_te))
    brier = paired_delta_corrected(s_base, s_rec, ntr, nte)
    f1 = paired_delta_corrected(f_base, f_rec, ntr, nte)
    return _decide({
        "task": "binary", "model_family": spec.model_family, "n_folds": len(folds), "metric": "neg_brier (higher is better)",
        "default_mean": float(np.mean(s_base)), "recommended_mean": float(np.mean(s_rec)),
        "mean_diff": brier["mean_delta"], "se_corrected": brier["se_delta"],
        "f1_default_mean": float(np.mean(f_base)), "f1_recommended_mean": float(np.mean(f_rec)),
        "f1_mean_diff": f1["mean_delta"], "f1_se_corrected": f1["se_delta"],
        "steps": [s.to_dict() for s in steps],
        "note": "report only: recommended minus default; no gate, no commit decision",
    })


FALLBACK_SE = 2.0
FALLBACK_TEXT = "fallback: default outperformed recommendation"


def _decide(r: dict) -> dict:
    """If the recommended pipeline is worse than the default by more than 2 corrected SE on neg-Brier, recommend the
    default pipeline instead. `steps` is kept (what the rules proposed); `final` says what is recommended."""
    worse = r["mean_diff"] < -FALLBACK_SE * r["se_corrected"]
    r["fallback"] = bool(worse)
    r["final"] = "default" if worse else "recommended"
    if worse:
        r["fallback_note"] = FALLBACK_TEXT
        r["note"] = FALLBACK_TEXT + "; " + r["note"]
    return r


def format_report(r: dict) -> str:
    return (f"Stage 2 ({r['model_family']}, {r['n_folds']} folds, {r['metric']}): recommended minus default = "
            f"{r['mean_diff']:+.4f} +/- {r['se_corrected']:.4f} (corrected SE); "
            f"F1 diff {r['f1_mean_diff']:+.4f} +/- {r['f1_se_corrected']:.4f}. Report only, no gate."
            + (f" {FALLBACK_TEXT}; recommend the default pipeline." if r.get("fallback") else ""))
