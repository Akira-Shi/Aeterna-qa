"""Job logic: Stage 1 (wraps pipeline.run), Stage 2 suggest/approve, artifacts. One pipeline run at a time
(v1 reads module-level config), guarded by RUN_LOCK."""
from __future__ import annotations

import dataclasses
import json
import pickle
import shutil
import threading
from pathlib import Path

import pandas as pd

from modules import audit, config, explain, pipeline, planner, taskspec
from modules.taskspec import TaskSpec
from stage2 import build, compare, rules

from . import cleaning, store

RUN_LOCK = threading.Lock()
BANNER = "EXPLORATORY RUN - arbitrary CSV, no ground truth, not a pre-registered result, never cited"
ARTIFACTS = ("cleaned.csv", "pipeline.joblib", "report.html", "audit.json", "preview.json")

NUM_IMPUTE = ("median", "mean", "median+indicator")
CAT_IMPUTE = ("most_frequent", "constant_missing")
ALLOWED = {"encoding": ("onehot", "onehot_capped", "ordinal"), "scaling": ("none", "standard", "robust", "yeo_johnson")}


def _wjson(path: Path, obj):
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- Stage 1
def run_stage1(job_id: str) -> None:
    job = store.get_job(job_id)
    spec = TaskSpec.from_dict(job["spec"])
    jd = store.job_dir(job_id)
    with RUN_LOCK:
        store.update_job(job_id, status="running", iteration=0)
        api_error = {}
        orig_log, orig_plan, orig_llm = audit.log_iteration, pipeline.plan, config.EXPLAIN_USE_LLM
        groq = job["planner"] == "groq"

        def log_iteration(run, *a, **kw):                      # progress: the iteration the pipeline just logged
            orig_log(run, *a, **kw)
            store.update_job(job_id, iteration=int(kw.get("iteration") or 0))

        def guarded_plan(findings, rejected=None):             # any Groq/API error (not a menu ValueError) is recorded
            try:
                return planner.plan(findings, rejected=rejected)
            except ValueError:
                raise
            except Exception as e:                             # noqa: BLE001
                api_error.setdefault("msg", f"{type(e).__name__}: {str(e)[:300]}")
                raise

        try:
            audit.log_iteration, pipeline.plan = log_iteration, guarded_plan
            config.EXPLAIN_USE_LLM = groq
            _stage1(job_id, spec, jd, groq, api_error)
        except Exception as e:                                 # noqa: BLE001
            store.update_job(job_id, status="failed", message=f"{type(e).__name__}: {str(e)[:500]}")
        finally:
            audit.log_iteration, pipeline.plan, config.EXPLAIN_USE_LLM = orig_log, orig_plan, orig_llm


def _stage1(job_id, spec: TaskSpec, jd: Path, groq: bool, api_error: dict):
    df, prep = taskspec.load_dataset(spec)
    train_index = cleaning.split_train_index(df, spec.target)
    meta_base = {"scenario": "exploratory", "task_spec": spec.to_dict(), "prep": prep, "api_job_id": job_id}

    if not spec.gate_supported:
        from modules.detectors import detect
        with taskspec.applied(spec):
            findings = detect(df)
        _wjson(jd / "stage1_detect.json", {"mode": "detection_only", "scenario": "exploratory",
                                           "gate": "gate not supported", "findings": findings})
        audit_doc = {**meta_base, "label": BANNER, "mode": "detection_only", "gate": "gate not supported",
                     "findings": findings, "stage2": None}
        _finish_artifacts(jd, df, df, [], train_index, audit_doc, report_src=None)
        store.update_job(job_id, status="done", message="gate not supported: detection only")
        return

    pos = taskspec.resolve_positive_label(spec, df)
    explicit = spec.positive_label is not None
    pos_txt = pos if explicit else f"{pos} (defaulted)"
    meta = {**meta_base, "label": f"{BANNER}; positive label: {pos_txt}", "positive_label_used": pos,
            "positive_label_explicit": explicit, "positive_label_text": pos_txt}
    with taskspec.applied(spec, positive_label=pos):
        res = pipeline.run(raw_df=df, offline_planner=not groq, task_meta=meta,
                           log_prefix=f"exploratory_api_{job_id[:8]}_", run_explain=True)
    if api_error:
        store.update_job(job_id, status="planner_unavailable",
                         message=f"Groq planner unavailable ({api_error['msg']}). Rerun with the rule planner.")
        return
    log_path = Path(res["log_path"])
    run_doc = json.loads(log_path.read_text(encoding="utf-8"))
    committed = res["committed_ops"]
    cleaned, fitted = cleaning.clean_with_train_fit(df, committed, train_index)
    audit_doc = {**meta_base, "label": meta["label"], "mode": "gated", "committed_ops": committed,
                 "stage1_log": run_doc, "stage2": None}
    _finish_artifacts(jd, df, cleaned, fitted, train_index, audit_doc,
                      report_src=log_path.with_name(f"report_{log_path.stem}.html"))
    _wjson(jd / "stage1_run.json", run_doc)
    store.update_job(job_id, status="done")


def _finish_artifacts(jd: Path, before: pd.DataFrame, cleaned: pd.DataFrame, fitted: list, train_index, audit_doc, report_src):
    cleaned.to_csv(jd / "cleaned.csv", index=False, lineterminator="\n")
    with open(jd / "frames.pkl", "wb") as f:                   # internal, trusted: dtypes survive for Stage 2
        pickle.dump({"before": before, "cleaned": cleaned, "train_index": list(train_index)}, f)
    audit_doc["cleaning"] = {"split": f"deterministic {cleaning.TRAIN_FRAC:.0%} train split, random_state={config.RANDOM_STATE}",
                             "n_train_rows": len(train_index), "ops_fitted_on_training_rows": fitted,
                             "rows_in": len(before), "rows_out": len(cleaned)}
    _wjson(jd / "audit.json", audit_doc)
    _wjson(jd / "preview.json", preview(before, cleaned))
    if report_src is not None and Path(report_src).is_file():
        shutil.copyfile(report_src, jd / "report.html")
    else:
        (jd / "report.html").write_text("<!doctype html><meta charset='utf-8'><title>Report</title>"
                                        "<p>No Explain report for this run (gate not supported: detection only).</p>",
                                        encoding="utf-8", newline="\n")


def preview(before: pd.DataFrame, cleaned: pd.DataFrame, n: int = 20) -> dict:
    """Up to 20 rows, changed rows first (by original row label), before and after."""
    common = cleaned.index.intersection(before.index)
    b, a = before.loc[common], cleaned.loc[common]
    diff = ~((b == a) | (b.isna() & a.isna()))
    changed = diff.any(axis=1).to_numpy()
    order = list(common[changed]) + list(common[~changed])
    pick = order[:n]

    def rows(d):
        return json.loads(d.loc[pick].to_json(orient="records"))
    return {"columns": list(cleaned.columns), "row_labels": [int(i) for i in pick],
            "n_changed_rows_total": int(changed.sum()),
            "changed_cells_per_row": [int(diff.loc[i].sum()) for i in pick], "before": rows(b), "after": rows(a),
            "rows_dropped": int(len(before) - len(cleaned))}


# ---------------------------------------------------------------- Stage 1 results
def stage1_results(job_id: str) -> dict:
    jd = store.job_dir(job_id)
    det = jd / "stage1_detect.json"
    if det.is_file():
        return json.loads(det.read_text(encoding="utf-8"))
    run = json.loads((jd / "stage1_run.json").read_text(encoding="utf-8"))
    facts = explain.build_facts(run)
    keep = ("iteration", "column", "operation", "reason", "f1_before", "f1_after", "delta", "se", "threshold", "status",
            "chain_id", "chain_ops", "committed_ops", "error", "own_clears", "ratio", "z", "verdict")
    its = [{k: i.get(k) for k in keep} for i in facts["iterations"]]
    for it in its:
        it["plain_fix"] = explain.plain_fix(it["column"], it["operation"]) if it["column"] else None
    return {"mode": "gated", "scenario": facts["scenario"], "label": facts["label"], "metric": facts["metric"],
            "headline": explain.headline(facts), "baseline": facts["baseline"], "final": facts["final"],
            "committed_ops": facts["committed_ops"], "n_committed": facts["n_committed"], "n_chains": facts["n_chains"],
            "n_evaluations": facts["n_evaluations"], "repairs": its,
            "note": "f1_before/f1_after/delta/se/threshold hold the GATE score (neg-Brier); F1 is not the gate."}


# ---------------------------------------------------------------- Stage 2
class Stage2Error(ValueError):
    pass


def _load_frames(job_id):
    with open(store.job_dir(job_id) / "frames.pkl", "rb") as f:
        return pickle.load(f)


def _xy(cleaned: pd.DataFrame, spec: TaskSpec):
    X = cleaned.drop(columns=[spec.target])
    if spec.task_type == "binary":
        pos = taskspec.resolve_positive_label(spec, cleaned)
        y = (cleaned[spec.target].astype(str).str.strip() == pos).astype(int)
    else:
        y = cleaned[spec.target]
    return X, y


def _step_view(i, st: rules.Step, X: pd.DataFrame) -> dict:
    d = st.to_dict()
    d["index"] = i
    prof = rules.profile_columns(X[list(st.columns)]) if st.columns else {}
    kinds = {p.kind for p in prof.values()}
    if st.stage == "imputation":
        d["allowed_methods"] = list(NUM_IMPUTE if kinds == {"numeric"} else CAT_IMPUTE)
    elif st.stage in ALLOWED:
        d["allowed_methods"] = list(ALLOWED[st.stage])
    else:
        d["allowed_methods"] = []          # estimator-level (imbalance) steps are not editable
    d["editable"] = bool(d["allowed_methods"])
    return d


def suggest(job_id: str) -> dict:
    job = store.get_job(job_id)
    spec = TaskSpec.from_dict(job["spec"])
    fr = _load_frames(job_id)
    X, y = _xy(fr["cleaned"], spec)
    with RUN_LOCK:
        steps = rules.recommend(spec.task_type, spec.model_family, X, y)   # gate_metric never passed: config's (Brier)
        rep, note = None, None
        try:
            rep = compare.compare(fr["cleaned"], spec, steps=steps)
        except compare.CompareNotSupported as e:
            note = str(e)
    out = {"steps": [_step_view(i, s, X) for i, s in enumerate(steps)], "compare": rep, "compare_note": note,
           "fallback": bool(rep and rep.get("fallback")), "fallback_note": rep.get("fallback_note") if rep else None,
           "final": rep["final"] if rep else "recommended", "approved": False}
    store.update_job(job_id, stage2=out)
    return out


def approve(job_id: str, decisions: list) -> dict:
    job = store.get_job(job_id)
    s2 = job["stage2"]
    if not s2:
        raise Stage2Error("run /stage2/suggest first")
    spec = TaskSpec.from_dict(job["spec"])
    fr = _load_frames(job_id)
    X, y = _xy(fr["cleaned"], spec)
    steps = [rules.Step(d["stage"], tuple(d["columns"]), d["method"], d["rule_id"], d["reason"], d["alternative"], d["params"])
             for d in s2["steps"]]
    by_step = {}
    for d in decisions:
        if d.step >= len(steps):
            raise Stage2Error(f"step {d.step} does not exist (0..{len(steps) - 1})")
        if d.step in by_step:
            raise Stage2Error(f"step {d.step} listed twice")
        by_step[d.step] = d
    final_steps, log = [], []
    for i, st in enumerate(steps):
        d = by_step.get(i)
        edit = None
        if d is not None and d.action == "edit":
            allowed = s2["steps"][i]["allowed_methods"]
            if not d.method or d.method not in allowed:
                raise Stage2Error(f"step {i} ({st.stage}) cannot be edited to {d.method!r}; allowed: {allowed}")
            if d.method != st.method:
                edit = {"from": st.method, "to": d.method}
                st = dataclasses.replace(st, method=d.method)
        final_steps.append(st)
        log.append({"index": i, "stage": st.stage, "columns": list(st.columns), "method": st.method,
                    "rule_id": st.rule_id, "reason": steps[i].reason, "alternative": st.alternative,
                    "decided_by": "user_override" if edit else "rule", "user_edit": edit})
    any_edit = any(e["user_edit"] for e in log)
    use_default = bool(s2.get("fallback")) and not any_edit
    jd = store.job_dir(job_id)
    train = [i for i in fr["train_index"] if i in fr["cleaned"].index]
    try:
        with RUN_LOCK:
            pipe = (build.build_default(X, spec.task_type, spec.model_family) if use_default
                    else build.build_pipeline(final_steps, spec.task_type, spec.model_family))
            build.fit_on_train(pipe, X, y, train)                 # training rows only
    except Exception as e:                                         # noqa: BLE001
        raise Stage2Error(f"pipeline could not be fitted with these steps: {type(e).__name__}: {str(e)[:300]}")
    build.save_pipeline(pipe, jd / "pipeline.joblib", None if use_default else final_steps)
    s2.update({"approved": True, "decisions": log, "n_train_rows": len(train),
               "pipeline_used": "default (fallback fired, no user edit)" if use_default else "approved steps"})
    store.update_job(job_id, stage2=s2)
    a = json.loads((jd / "audit.json").read_text(encoding="utf-8"))
    a["stage2"] = {"steps": log, "pipeline_used": s2["pipeline_used"], "fallback": s2.get("fallback"),
                   "fallback_note": s2.get("fallback_note"), "compare": s2.get("compare"),
                   "model_family": spec.model_family, "fit_on": "training rows only"}
    _wjson(jd / "audit.json", a)
    return s2
