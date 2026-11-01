#!/usr/bin/env python3
"""P5 driver: registered real-data runs (Marketing, Airbnb) per the signed amendment (PREREGISTRATION s12, 2026-11-01).

  python tools/run_real_study.py --dataset Marketing --planner rule --partition eval --seeds 401 402 403
  python tools/run_real_study.py --dataset Airbnb --planner groq --partition eval --seeds 401 402 403
  python tools/run_real_study.py --dataset Marketing --planner rule --partition pilot --seeds 401   # pipeline check only

Wraps the unchanged v1 pipeline (no pipeline, detector, op, menu or gate change). Split: 20/80 pilot/eval, stratified on
the target, assigned in GROUPS of identical feature vectors (same construction as study.base_and_split), split seed
20261101. No complete-case filter (the NaN cells are the error cells). LR + Brier only. Scenario label real_<dataset>.
The seed (401-403) is a replicate label: the pipeline has no injection and its folds/model are fixed by
config.RANDOM_STATE, so only the Groq planner (temperature 0.2) can differ between seeds.
"""
import argparse, contextlib, hashlib, io, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "aeterna_qa"))
from modules import config, pipeline, taskspec          # noqa: E402
from modules.taskspec import TaskSpec                    # noqa: E402

SPLIT_SEED = 20261101
PILOT_FRAC = 0.20
DATASETS = {
    "Marketing": dict(path="Dataset/real/Marketing/raw/raw.csv", target="Income", positive="0",
                      sha="6a05ac3f7579d07c9731741f53012534de72a9b93ebf482e709d5c1da6e8e1a3",
                      source="CleanML Marketing"),
    "Airbnb": dict(path="Dataset/real/Airbnb/raw/raw.csv", target="Rating", positive="Y",
                   sha="e5e37131e92cbc4edeeaecaf14c2acdc404994e8d1e725b8ab7c65fe214b504d",
                   source="CleanML Airbnb (Inside Airbnb, CC BY)"),
}
HOST_COLS = ("host_name", "host_id", "host name", "host id", "hostname", "hostid")
OUT = ROOT / "aeterna_qa" / "logs" / "study_real"


def split(df: pd.DataFrame, target: str):
    feat = df.drop(columns=[target]).apply(lambda c: c.map(lambda v: "<NA>" if pd.isna(v) else str(v)))
    codes, _ = pd.factorize(feat.agg("|".join, axis=1))
    lab = df[target].astype(str).str.strip().groupby(codes).first()
    rng = np.random.RandomState(SPLIT_SEED)
    pilot_groups = []
    for cls in sorted(lab.unique()):
        g = lab.index[lab.values == cls].values
        g = g[rng.permutation(len(g))]
        pilot_groups.extend(g[: int(round(PILOT_FRAC * len(g)))])
    is_pilot = np.isin(codes, pilot_groups)
    return df[is_pilot], df[~is_pilot]


def load(ds: str):
    d = DATASETS[ds]
    p = ROOT / d["path"]
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha != d["sha"]:
        raise SystemExit(f"{ds}: data sha256 mismatch {sha} != {d['sha']}")
    cols = pd.read_csv(p, nrows=0).columns
    drop = [c for c in cols if c.strip().lower() in HOST_COLS]
    spec = TaskSpec(path=str(p), target=d["target"], task_type="binary", positive_label=d["positive"],
                    model_family="linear", id_columns=[], drop_columns=drop)
    df, prep = taskspec.load_dataset(spec)
    return spec, df, prep, sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(DATASETS))
    ap.add_argument("--planner", required=True, choices=["rule", "groq"])
    ap.add_argument("--partition", required=True, choices=["pilot", "eval"])
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    config.LOG_DIR = OUT
    config.EXPLAIN_USE_LLM = False
    spec, df, prep, sha = load(a.dataset)
    pil, ev = split(df, spec.target)
    part = pil if a.partition == "pilot" else ev
    idx_sha = hashlib.sha256(",".join(map(str, part.index)).encode()).hexdigest()
    (OUT / f"split_{a.dataset}.json").write_text(json.dumps(
        {"dataset": a.dataset, "split_seed": SPLIT_SEED, "rows": len(df), "pilot": len(pil), "eval": len(ev),
         "pilot_idx_sha256": hashlib.sha256(",".join(map(str, pil.index)).encode()).hexdigest(),
         "eval_idx_sha256": hashlib.sha256(",".join(map(str, ev.index)).encode()).hexdigest()}, indent=1))
    for seed in a.seeds:
        np.random.seed(seed)
        scen = f"real_{a.dataset.lower()}"
        stem = f"{scen}_{a.planner}_{seed}_{a.partition}"
        meta = {"scenario": scen,
                "label": f"REAL DATA ({DATASETS[a.dataset]['source']}; natural defects, not injected; "
                         f"pre-registered real-data study; partition {a.partition}; positive label "
                         f"{spec.positive_label} (explicit))",
                "task_spec": spec.to_dict(), "positive_label_used": spec.positive_label,
                "positive_label_explicit": True, "positive_label_text": spec.positive_label, "prep": prep,
                "dataset": a.dataset, "data_sha256": sha, "split_seed": SPLIT_SEED, "run_seed": seed,
                "partition": a.partition, "partition_rows": len(part), "partition_index_sha256": idx_sha,
                "planner_kind": a.planner, "git_head": __import__("subprocess").run(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()}
        buf = io.StringIO()
        print(f"=== {stem}: {len(part)} rows ===", flush=True)
        class Tee(io.TextIOBase):
            def write(self, s):
                buf.write(s); sys.__stdout__.write(s); return len(s)
        with contextlib.redirect_stdout(Tee()):
            with taskspec.applied(spec, positive_label=spec.positive_label):
                res = pipeline.run(raw_df=part, offline_planner=(a.planner == "rule"), task_meta=meta,
                                   log_prefix=stem + "_", run_explain=True)
        (OUT / f"{stem}.txt").write_text(buf.getvalue(), encoding="utf-8")
        print(f"=== done {stem}: committed {res['committed_ops']} log {res['log_path']}", flush=True)


if __name__ == "__main__":
    main()
