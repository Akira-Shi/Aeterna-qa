"""
The pre-registered controlled-corruption study (Documents/PREREGISTRATION.md).

  python -m modules.study pilot     # 20% pilot partition: pick severity, set expected outcomes
  python -m modules.study eval      # 80% eval partition: full agent, graded against the answer key
  python -m modules.study confirm   # apply committed fixes to the pilot partition with a fresh seed

Rules that are enforced here, not just promised:
  * eval refuses to run until pilot.json exists (expected outcomes are fixed BEFORE eval).
  * the agent (pipeline.run) only receives the corrupted dataframe; the manifest is used
    only after it finishes, for the answer-key check and grading.
  * nothing is re-tuned after eval: severity ladders, seeds and the gate are constants below.
All results are SYNTHETIC-corruption results on one dataset; see PREREGISTRATION section 1.
"""
import contextlib
import io
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import config, pipeline
from .detectors import detect
from .evaluator import (load_raw_dataset, make_fixed_folds, calculate_f1_candidate, materialize,
                        paired_delta_corrected, commit_threshold)
from .executor import _fit_stat, _apply_stat
from .injection import inject
from .planner import remaining_options

SPLIT_SEED = 20261001
PILOT_FRAC = 0.20
PILOT_SEEDS = (101, 102, 103)
EVAL_SEEDS = (201, 202, 203)
CONFIRM_SEED = 301
MDE_Z = 0.84   # 80% power

SCENARIOS = {
    "C1": dict(kind="category_variants", column="occupation", ladder=[0.10, 0.30, 0.60], expected_fix="normalize_categories"),
    "C2": dict(kind="mixed_units", column="age", factor=12, ladder=[0.05, 0.15, 0.30], expected_fix="rescale_units"),
    "C3": dict(kind="sentinel", column="age", value=999, ladder=[0.03, 0.08, 0.15], expected_fix="sentinel_to_median"),
    "C4": dict(kind="category_variants", column="native.country", ladder=[0.30], expected_fix=None),   # harmless decoy
    # C5 added by amendment 2026-09-30 after the C1-C4 pilot showed age/native.country have too little headroom
    # (see `ceilings`): a missing-value code in the one column with real headroom, capital.gain.
    "C5": dict(kind="sentinel", column="capital.gain", value=9999999, ladder=[0.01, 0.03, 0.06], expected_fix="sentinel_to_median"),
}

OUT = config.AETERNA_ROOT / "logs" / "study"
CLEAN_DIR = config.AETERNA_ROOT / "outputs"
DOCS = config.AETERNA_ROOT.parent / "Documents"


# ---------------------------------------------------------------- data / split
def base_and_split():
    """Complete-case Adult (no '?'), split 20/80 by GROUPS of identical feature vectors,
    stratified on income, fixed seed. Returns (pilot_df, eval_df); row ids preserved."""
    df = load_raw_dataset().dropna()
    feat = df.drop(columns=[config.TARGET_COLUMN]).astype(str)
    codes, _ = pd.factorize(feat.agg("|".join, axis=1))
    lab = df[config.TARGET_COLUMN].astype(str).str.strip().groupby(codes).first()
    rng = np.random.RandomState(SPLIT_SEED)
    pilot_groups = []
    for cls in sorted(lab.unique()):
        g = lab.index[lab.values == cls].values
        g = g[rng.permutation(len(g))]
        pilot_groups.extend(g[: int(round(PILOT_FRAC * len(g)))])
    is_pilot = np.isin(codes, pilot_groups)
    return df[is_pilot], df[~is_pilot]


def _spec(sc: str, rate: float):
    d = SCENARIOS[sc]
    spec = {"id": sc, "kind": d["kind"], "column": d["column"], "rate": rate, "expected_fix": d["expected_fix"]}
    for k in ("factor", "value"):
        if k in d:
            spec[k] = d[k]
    return spec


def _gate_delta(df, folds, ops):
    base = calculate_f1_candidate(df, folds)
    cand = calculate_f1_candidate(df, folds, candidate_ops=ops)
    st = paired_delta_corrected(base["scores"], cand["scores"], cand["n_train"], cand["n_test"])
    return st, commit_threshold(st["se_delta"], st["dof"], config.MAX_ITERATIONS)


# ---------------------------------------------------------------- pilot
def pilot(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    pil, ev = base_and_split()
    scale = float(np.sqrt(len(pil) / len(ev)))
    print(f"Pilot partition {len(pil)} rows, eval partition {len(ev)} rows; noise scale sqrt(n_pilot/n_eval) = {scale:.3f}\n")
    result = {"n_pilot": len(pil), "n_eval": len(ev), "scale": scale, "scenarios": {}}
    if only and (OUT / "pilot.json").exists():
        result = json.loads((OUT / "pilot.json").read_text())   # keep earlier scenarios' frozen results
    for sc, d in SCENARIOS.items():
        if only and sc not in only:
            continue
        rows = []
        for rate in d["ladder"]:
            effs, ses, bars = [], [], []
            for seed in PILOT_SEEDS:
                df, _ = inject(pil, [_spec(sc, rate)], seed=seed)
                folds = make_fixed_folds(df)
                fix = d["expected_fix"] or "normalize_categories"   # C4: diagnostic only (the wrong repair)
                st, bar = _gate_delta(df, folds, {d["column"]: fix})
                effs.append(st["mean_delta"]); ses.append(st["se_delta"]); bars.append(bar)
            eff, se, bar = float(np.mean(effs)), float(np.mean(ses)), float(np.mean(bars))
            mde_scaled = bar * scale + MDE_Z * se * scale
            rows.append({"rate": rate, "effects": effs, "effect": eff, "se": se, "bar": bar,
                         "mde_eval_scaled": mde_scaled, "mde_unscaled": bar + MDE_Z * se})
            print(f"{sc} rate {rate:>4.0%}: effect {eff:+.4f} (seeds {[round(e, 4) for e in effs]})  "
                  f"SE {se:.4f}  bar {bar:.4f}  MDE_eval(scaled) {mde_scaled:.4f}  (unscaled {bar + MDE_Z * se:.4f})", flush=True)
        chosen = next((r for r in rows if d["expected_fix"] and r["effect"] >= r["mde_eval_scaled"]), None)
        if chosen is not None:
            designation, level = "positive", chosen
        else:
            designation, level = "negative", rows[-1]
        result["scenarios"][sc] = {"designation": designation, "rate": level["rate"], "ladder": rows,
                                   "expected_fix": d["expected_fix"]}
        print(f"  -> {sc}: run at {level['rate']:.0%}, expected outcome = "
              f"{'COMMIT ' + d['expected_fix'] if designation == 'positive' else 'NO COMMIT (rollback)'}\n", flush=True)
    (OUT / "pilot.json").write_text(json.dumps(result, indent=1))
    _append_results("Pilot (frozen before eval)" + (f" -- added scenarios {only}" if only else ""), _pilot_md(result, only))
    print(f"written {OUT / 'pilot.json'}")


def _pilot_md(res, only=None):
    lines = [f"Pilot rows {res['n_pilot']}, eval rows {res['n_eval']}, noise scale {res['scale']:.3f}. Gate: Brier, LR.", "",
             "| Scenario | Rate | Pilot effect | SE | Bar | MDE (scaled) | MDE (unscaled) |", "|---|---|---|---|---|---|---|"]
    for sc, v in res["scenarios"].items():
        if only and sc not in only:
            continue
        for r in v["ladder"]:
            lines.append(f"| {sc} | {r['rate']:.0%} | {r['effect']:+.4f} | {r['se']:.4f} | {r['bar']:.4f} | "
                         f"{r['mde_eval_scaled']:.4f} | {r['mde_unscaled']:.4f} |")
    lines += ["", "Expected outcomes for the eval run (set by the pilot, not by hope):", ""]
    for sc, v in res["scenarios"].items():
        if only and sc not in only:
            continue
        exp = f"COMMIT {v['expected_fix']} on {SCENARIOS[sc]['column']}" if v["designation"] == "positive" else "NO COMMIT"
        lines.append(f"- {sc} at {v['rate']:.0%}: {exp}")
    return "\n".join(lines)


def _append_results(title, body):
    p = DOCS / "RESULTS.md" if DOCS.exists() else OUT / "RESULTS.md"
    head = "" if p.exists() else "# AETERNA-QA study results (synthetic corruption on Adult)\n\nAppend-only; see PREREGISTRATION.md.\n"
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"{head}\n## {title}\n\n{body}\n")


def ceilings():
    """Headroom check on the PILOT partition only: how much gate score is lost if a column is
    destroyed (numeric -> constant median, text -> constant). A defect in a column cannot cost more
    than this, so a column whose ceiling is below the commit bar can never yield a detectable effect."""
    pil, _ = base_and_split()
    folds = make_fixed_folds(pil)
    b = calculate_f1_candidate(pil, folds)["mean"]
    rows = []
    for col in pil.columns:
        if col == config.TARGET_COLUMN:
            continue
        d = pil.copy()
        d[col] = d[col].median() if pd.api.types.is_numeric_dtype(d[col]) else "x"
        rows.append((col, b - calculate_f1_candidate(d, folds)["mean"]))
    rows.sort(key=lambda r: -r[1])
    body = "Gate-score loss (Brier, LR) if the column is destroyed, pilot partition. Positive = column carries signal.\n\n| Column | Ceiling |\n|---|---|\n" + \
        "\n".join(f"| {c} | {v:+.5f} |" for c, v in rows)
    print(body)
    _append_results("Column headroom (pilot partition)", body)


# ---------------------------------------------------------------- grading
def _mismatch(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    return a.ne(b) & ~(a.isna() & b.isna())


def grade(truth: pd.DataFrame, corrupted: pd.DataFrame, cleaned: pd.DataFrame, m: dict) -> dict:
    col, rows = m["column"], m["rows"]
    common = truth.index.intersection(cleaned.index)
    mism = _mismatch(cleaned.loc[common], truth.loc[common])
    inj = pd.DataFrame(False, index=common, columns=truth.columns)
    inj_rows = rows.intersection(common)
    inj.loc[inj_rows, col] = True
    g = {"rows_dropped": int(len(truth) - len(cleaned)),
         "collateral_cells": int((mism & ~inj).to_numpy().sum()),
         "injected_rows": int(len(rows)), "injected_rows_present": int(len(inj_rows))}
    orig = m["original"].loc[inj_rows]
    now = cleaned.loc[inj_rows, col]
    if m["kind"] == "category_variants":
        g["restored_share"] = float((now == orig).mean()) if len(orig) else None
    elif m["kind"] == "mixed_units":
        g["restored_share"] = float(((now - orig).abs() <= 0.5).mean()) if len(orig) else None
    elif m["kind"] == "sentinel":
        g["mae"] = float((now.astype(float) - orig.astype(float)).abs().mean()) if len(orig) else None
        g["mae_median_reference"] = float((orig.astype(float) - truth[col].median()).abs().mean()) if len(orig) else None
        g["mae_unrepaired"] = float((corrupted.loc[inj_rows, col].astype(float) - orig.astype(float)).abs().mean()) if len(orig) else None
    return g


def _ci(delta_stats):
    t = sps.t.ppf(0.975, delta_stats["dof"])
    return [delta_stats["mean_delta"] - t * delta_stats["se_delta"], delta_stats["mean_delta"] + t * delta_stats["se_delta"]]


def _blind_ops(df):
    """Baseline: apply EVERY detector-justified op, highest-priority op per column, no gate."""
    ops = {}
    for c, op, _ in remaining_options(detect(df)):
        ops.setdefault(c, op)
    return ops


# ---------------------------------------------------------------- eval
def evaluate(planner="offline"):
    tag = "" if planner == "offline" else f"_{planner}"   # keep the rule-planner results when a Groq run is added
    pj = OUT / "pilot.json"
    if not pj.exists():
        sys.exit("Refusing to run: pilot.json missing. Run `python -m modules.study pilot` first (expected outcomes must be fixed before eval).")
    pilot_res = json.loads(pj.read_text())
    _, ev = base_and_split()
    OUT.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(exist_ok=True)
    results = []
    for sc, d in SCENARIOS.items():
        pv = pilot_res["scenarios"][sc]
        for seed in EVAL_SEEDS:
            spec = _spec(sc, pv["rate"]); spec["expected_commit"] = pv["designation"] == "positive"
            df, manifest = inject(ev, [spec], seed=seed)
            folds = make_fixed_folds(df)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = pipeline.run(offline_planner=(planner == "offline"), raw_df=df, manifest=manifest,
                                   label=f"STUDY {sc} rate {pv['rate']:.0%} seed {seed} (SYNTHETIC)",
                                   scenario_meta=[{k: v for k, v in m.items() if k not in ("rows", "original")} for m in manifest],
                                   run_explain=False)
            (OUT / f"eval{tag}_{sc}_{seed}.txt").write_text(buf.getvalue(), encoding="utf-8")
            ops = res["committed_ops"]
            cleaned = materialize(df, ops)
            m = manifest[0]
            inj_base = calculate_f1_candidate(df, folds)
            fin = calculate_f1_candidate(df, folds, committed_ops=ops)
            clean = calculate_f1_candidate(ev, folds)
            st = paired_delta_corrected(inj_base["scores"], fin["scores"], fin["n_train"], fin["n_test"])
            loss = clean["mean"] - inj_base["mean"]
            try:
                bops = _blind_ops(df)
                blind = calculate_f1_candidate(df, folds, candidate_ops=bops)["mean"]
            except Exception as e:  # noqa: BLE001
                bops, blind = str(e), None
            expected = pv["designation"] == "positive"
            correct = (ops.get(d["column"]) == d["expected_fix"]) if expected else (len(ops) == 0)
            row = {"scenario": sc, "seed": seed, "rate": pv["rate"], "expected_commit": expected,
                   "committed_ops": ops, "outcome_as_expected": bool(correct),
                   "kind": ("hit" if expected and correct else "miss" if expected else
                            "correct_rollback" if correct else "false_commit"),
                   "gate_injected": inj_base["mean"], "gate_final": fin["mean"], "gate_clean": clean["mean"],
                   "delta_vs_injected": st["mean_delta"], "delta_ci95": _ci(st),
                   "recovery_fraction": (fin["mean"] - inj_base["mean"]) / loss if loss > 1e-9 else None,
                   "blind_clean_ops": bops, "gate_blind_clean": blind,
                   "grading": grade(ev, df, cleaned, m), "log_path": res["log_path"]}
            results.append(row)
            print(f"{sc} seed {seed}: expected {'COMMIT' if expected else 'none'} | committed {ops or 'none'} | {row['kind'].upper()} | "
                  f"gate {inj_base['mean']:.4f} -> {fin['mean']:.4f} (clean {clean['mean']:.4f}) | grading {row['grading']}", flush=True)
            if ops:
                stem = f"adult_clean{tag}_{sc}_{seed}"
                cleaned.to_csv(CLEAN_DIR / f"{stem}.csv", index=False)
                (CLEAN_DIR / f"{stem}.manifest.json").write_text(json.dumps(
                    {"scenario": sc, "seed": seed, "synthetic_corruption": spec | {"rows": None},
                     "committed_ops": ops, "rows_in": len(df), "rows_out": len(cleaned),
                     "cells_changed_vs_corrupted": int(_mismatch(cleaned.loc[cleaned.index.intersection(df.index)],
                                                                df.loc[cleaned.index.intersection(df.index)]).to_numpy().sum())}, indent=1, default=str))
    (OUT / f"eval{tag}.json").write_text(json.dumps({"planner": planner, "results": results}, indent=1, default=str))
    _append_results(f"Eval ({planner} planner)", _eval_md(results))
    print(f"\nwritten {OUT / f'eval{tag}.json'}")


def _eval_md(results):
    lines = ["| Scenario | Seed | Rate | Expected | Committed | Outcome | Gate inj -> final (clean) | Delta 95% CI | Recovery | Blind-clean gate | Restored / MAE | Collateral cells | Rows dropped |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        g = r["grading"]
        restored = (f"{g['restored_share']:.3f}" if g.get("restored_share") is not None else
                    f"MAE {g['mae']:.2f} (median ref {g['mae_median_reference']:.2f}, unrepaired {g['mae_unrepaired']:.2f})" if g.get("mae") is not None else "-")
        rec = "-" if r["recovery_fraction"] is None else f"{r['recovery_fraction']:.2f}"
        blind = "-" if r["gate_blind_clean"] is None else f"{r['gate_blind_clean']:.4f}"
        lines.append(f"| {r['scenario']} | {r['seed']} | {r['rate']:.0%} | {'commit' if r['expected_commit'] else 'none'} | "
                     f"{r['committed_ops'] or 'none'} | {r['kind']} | {r['gate_injected']:.4f} -> {r['gate_final']:.4f} ({r['gate_clean']:.4f}) | "
                     f"[{r['delta_ci95'][0]:+.4f}, {r['delta_ci95'][1]:+.4f}] | {rec} | {blind} | {restored} | {g['collateral_cells']} | {g['rows_dropped']} |")
    k = {}
    for r in results:
        k.setdefault(r["kind"], 0); k[r["kind"]] += 1
    lines += ["", f"Counts: {k}. Reported as k/n per scenario in the table; no pooling of positive and negative scenarios."]
    return "\n".join(lines)


# ---------------------------------------------------------------- confirm
def confirm():
    ej = OUT / "eval.json"
    if not ej.exists():
        sys.exit("Run eval first.")
    ev_res = json.loads(ej.read_text())["results"]
    pil, ev = base_and_split()
    lines = []
    for r in ev_res:
        if not r["committed_ops"] or r["seed"] != EVAL_SEEDS[0]:
            continue
        sc = r["scenario"]
        spec = _spec(sc, r["rate"])
        eval_df, _ = inject(ev, [spec], seed=r["seed"])
        conf_df, man = inject(pil, [spec], seed=CONFIRM_SEED)
        cleaned = conf_df.copy()
        for col, op in r["committed_ops"].items():
            if op == "dedupe_rows":
                cleaned = cleaned[~cleaned.duplicated()]
                continue
            stat = _fit_stat(eval_df[col], op, col)          # fitted on the EVAL partition only
            cleaned[col] = _apply_stat(cleaned[col], op, stat)
        g = grade(pil, conf_df, cleaned, man[0])
        lines.append(f"- {sc} (ops {r['committed_ops']}) on pilot partition, seed {CONFIRM_SEED}: {g}")
        print(lines[-1], flush=True)
    _append_results("Confirmation on the pilot partition (fresh seed)", "\n".join(lines) or "No committed fixes to confirm.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pilot":
        pilot(only=sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None)
    elif cmd == "ceilings":
        ceilings()
    elif cmd == "eval":
        evaluate(planner=sys.argv[sys.argv.index("--planner") + 1] if "--planner" in sys.argv else "offline")
    elif cmd == "confirm":
        confirm()
    else:
        sys.exit("usage: python -m modules.study {pilot|eval|confirm} [--planner offline|groq]")
