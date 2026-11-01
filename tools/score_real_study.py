#!/usr/bin/env python3
"""Score the registered real-data runs per the signed amendment (PREREGISTRATION s12, 2026-11-01).

  python tools/score_real_study.py            # writes Documents/real_results/real_results.json and prints a summary

Read-only on the pipeline. Parses Documents/EXPECTED_OUTCOMES_real_data.md (signed blob), reads the audit logs in
aeterna_qa/logs/study_real/ (eval partition, not the aborted/ folder), and reconstructs the offered options AFTER the
runs by re-running detect() on the exact input of each iteration (eval partition, materialised with that iteration's
committed ops), as the pipeline does. Sanity check: every evaluated (column, op) must be in that iteration's offers;
if any run fails it, the three-way stage split is dropped for everything and only the combined count is reported.
"""
import json, re, sys, glob
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "aeterna_qa")); sys.path.insert(0, str(ROOT / "tools"))
import run_real_study as R                                   # noqa: E402
from modules import config, taskspec                          # noqa: E402
from modules.detectors import detect                          # noqa: E402
from modules.evaluator import materialize, commit_threshold   # noqa: E402
from modules.planner import remaining_options                 # noqa: E402

LOGS = ROOT / "aeterna_qa" / "logs" / "study_real"
EXP = ROOT / "Documents" / "EXPECTED_OUTCOMES_real_data.md"
OUTJ = ROOT / "Documents" / "real_results" / "real_results.json"
MISSING_OPS = {"fill_mean", "fill_median", "fill_mode", "fill_unknown", "drop_rows"}
CLASS_OF = {**{o: "missing" for o in MISSING_OPS}, "clip_outliers": "outliers", "normalize_categories": "inconsistency"}


def parse_expected():
    rows = []
    for ln in EXP.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (Airbnb|Marketing) \| (.*?) \| (missing|outliers|inconsistency) \| (.*?) \| (commit|no commit) \|", ln)
        if m:
            ds, col, typ, ops, exp = m.groups()
            rows.append(dict(ds=ds, col=col, typ=typ, ops=[o.strip() for o in ops.split(",")], exp=exp))
    return rows


def load_runs():
    runs = []
    for f in sorted(glob.glob(str(LOGS / "real_*_eval_*.json"))):
        d = json.load(open(f))
        m = d["meta"]
        runs.append(dict(file=Path(f).name, ds=m["dataset"], planner=m["planner_kind"], seed=m["run_seed"], log=d))
    return runs


def committed_of(log):
    ops, deltas = {}, {}
    for it in log["iterations"]:
        if it["status"] == "committed":
            for c, o in (it["chain_ops"] or {}).items():
                ops[c] = o
            deltas[f"{it['column']}:{it['operation']}"] = dict(delta=it["delta"], bar=it["threshold"], se=it["se"],
                                                                f1_before=it.get("f1_before"), f1_after=it.get("f1_after"))
    return ops, deltas


def main():
    exp = parse_expected()
    runs = load_runs()
    by_exp = defaultdict(dict)
    for r in exp:
        by_exp[(r["ds"], r["col"])][r["typ"]] = r
    data = {}
    for ds in R.DATASETS:
        spec, df, prep, sha = R.load(ds)
        pil, ev = R.split(df, spec.target)
        data[ds] = (spec, ev)

    sanity_ok = True
    sanity_notes = []
    for run in runs:
        spec, ev = data[run["ds"]]
        offers_by_it, union = {}, set()
        cache = {}
        with taskspec.applied(spec, positive_label=spec.positive_label):
            for it in run["log"]["iterations"]:
                key = frozenset((it["committed_ops"] or {}).items())
                if key not in cache:
                    cache[key] = {(c, o) for c, o, _ in remaining_options(detect(materialize(ev, dict(it["committed_ops"] or {}))))}
                offers_by_it[it["iteration"]] = cache[key]
                union |= cache[key]
                if it["error"] is None and it["column"] is not None:
                    if (it["column"], it["operation"]) not in cache[key]:
                        sanity_ok = False
                        sanity_notes.append(f"{run['file']} iteration {it['iteration']}: evaluated ({it['column']}, {it['operation']}) not in reconstructed offers")
        run["offers_union"] = union
    results = []
    for run in runs:
        log = run["log"]
        c_ops, c_deltas = committed_of(log)
        evaluated = [(it["column"], it["operation"]) for it in log["iterations"] if it["error"] is None and it["column"] is not None]
        errors = [dict(iteration=it["iteration"], column=it["column"], operation=it["operation"], error=it["error"]) for it in log["iterations"] if it["error"]]
        rows_out = []
        for r in exp:
            if r["ds"] != run["ds"]:
                continue
            hit_ops = [o for o in r["ops"] if c_ops.get(r["col"]) == o]
            ev_ops = [o for o in r["ops"] if (r["col"], o) in evaluated]
            off_ops = [o for o in r["ops"] if (r["col"], o) in run["offers_union"]]
            if r["exp"] == "commit":
                if hit_ops:
                    obs, stage = "hit", None
                else:
                    obs = "miss"
                    if ev_ops:
                        stage = "gate-reject"
                    elif any(e["column"] == r["col"] for e in errors):
                        stage = "unclassified (error)"
                    elif sanity_ok:
                        stage = "planner-miss" if off_ops else "detector-miss"
                    else:
                        stage = "not evaluated (detector-miss or planner-miss, not separable)"
            else:
                obs = "correct no-commit" if not hit_ops else "commit-on-no-commit-row"
                stage = None
            rows_out.append(dict(col=r["col"], typ=r["typ"], expected=r["exp"], reachable=r["ops"], obs=obs, stage=stage,
                                 evaluated=ev_ops, offered=off_ops, committed=hit_ops))
        # commit classification
        hits_commit, unexplained, wrong_op = [], [], []
        for c, o in c_ops.items():
            cls = CLASS_OF.get(o)
            types = by_exp.get((run["ds"], c), {})
            exp_types = {t for t, rr in types.items() if rr["exp"] == "commit"}
            row = types.get(cls) if cls else None
            if row is not None and row["exp"] == "commit" and o in row["ops"]:
                hits_commit.append((c, o))
            elif not exp_types:
                unexplained.append(dict(column=c, op=o, note="column has no error cells (no expected-commit row)" + ("; duplicates are outside the scored rows" if c == "*" else "")))
            elif row is not None and row["exp"] == "commit":
                unexplained.append(dict(column=c, op=o, note="op class matches the diff but op is not a reachable op (amendment section B)"))
            else:
                wrong_op.append(dict(column=c, op=o, note=f"column has error cells of type(s) {sorted(exp_types)}; op class {cls or 'other'} does not match"))
        results.append(dict(file=run["file"], dataset=run["ds"], planner=run["planner"], seed=run["seed"],
                            committed_ops=c_ops, commit_deltas=c_deltas, n_evaluated=len(evaluated), n_errors=len(errors),
                            errors=errors, unexplained=unexplained, wrong_op=wrong_op, rows=rows_out,
                            baseline=log["baseline_f1"], final=log["final_f1"]))
    # across-dataset secondary: family = 16 look-backs x number of eval runs
    n_runs = len(runs)
    K = n_runs * config.MAX_ITERATIONS
    out = dict(sanity_ok=sanity_ok, sanity_notes=sanity_notes, family_K=K, n_runs=n_runs, results=results)
    OUTJ.parent.mkdir(parents=True, exist_ok=True)
    OUTJ.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("sanity_ok", sanity_ok, sanity_notes[:5])
    for r in results:
        pos = [x for x in r["rows"] if x["expected"] == "commit"]
        neg = [x for x in r["rows"] if x["expected"] != "commit"]
        st = defaultdict(int)
        for x in pos:
            if x["stage"]:
                st[x["stage"]] += 1
        print(r["dataset"], r["planner"], r["seed"], "H2 hit", sum(x["obs"] == "hit" for x in pos), "/", len(pos),
              "| H1 correct", sum(x["obs"] == "correct no-commit" for x in neg), "/", len(neg), "|", dict(st),
              "| commits", r["committed_ops"], "| evals", r["n_evaluated"], "| err", r["n_errors"],
              "| unexpl", len(r["unexplained"]), "| wrong", len(r["wrong_op"]))


if __name__ == "__main__":
    main()
