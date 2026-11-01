"""
Sandbox runner (P4): run the unchanged v1 agent on any CSV.

    python -m aeterna_qa.run --csv Dataset/sandbox/my.csv --target label [--task binary] [--groq]
    (or, from aeterna_qa/:  python run.py --csv ... --target ...)

EXPLORATORY ONLY: audit scenario is "exploratory", outputs and logs are prefixed exploratory_, and
nothing produced here is ever cited as a result (no pre-registered ground truth, no answer key).
Gate = LR + Brier for binary targets. For multiclass / regression only detection runs and the report
says "gate not supported". Put inputs in Dataset/sandbox/ (gitignored).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from modules import config, taskspec                      # noqa: E402
from modules.taskspec import TaskSpec, SpecError          # noqa: E402

BANNER = "EXPLORATORY RUN - arbitrary CSV, no ground truth, not a pre-registered result, never cited"


def _paths(csv: Path):
    out = config.AETERNA_ROOT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out, csv.stem


def run_spec(spec: TaskSpec, groq: bool = False, explain: bool = True) -> dict:
    """Validate, prepare and run. Returns a small result dict. Raises SpecError on invalid input."""
    from modules import pipeline
    from modules.detectors import detect
    from modules.evaluator import materialize

    df, prep = taskspec.load_dataset(spec)
    print(BANNER)
    for w in prep["warnings"]:
        print(f"  WARNING: {w}")
    for c in prep["coerced_to_categorical"]:
        print(f"  note: numeric column {c!r} has missing values and few distinct values; treated as categorical")
    out, stem = _paths(Path(spec.path))
    print(f"  {len(df)} rows x {df.shape[1]} columns, target={spec.target!r}, task={spec.task_type}\n")

    if not spec.gate_supported:
        with taskspec.applied(spec):
            findings = detect(df)
        res = {"mode": "detection_only", "gate": "gate not supported", "task_type": spec.task_type,
               "n_findings": len(findings)}
        for f in findings:
            print(f"  detected: {f['defect']} in {f['column']!r}: {f['evidence']}")
        print(f"\nGate not supported for task_type={spec.task_type!r} (the gate is LR + Brier on binary targets only). "
              f"Detection only; no repair was evaluated or applied.")
        p = out / f"exploratory_{stem}_detect.json"
        p.write_text(json.dumps({"scenario": "exploratory", "spec": spec.to_dict(), "prep": prep,
                                 "gate": "gate not supported", "findings": findings}, indent=1, default=str))
        res["detect_path"] = str(p)
        return res

    pos = taskspec.resolve_positive_label(spec, df)
    meta = {"scenario": "exploratory", "label": BANNER, "task_spec": spec.to_dict(),
            "positive_label_used": pos, "positive_label_explicit": spec.positive_label is not None,
            "prep": prep}
    config.EXPLAIN_USE_LLM = bool(groq)
    with taskspec.applied(spec, positive_label=pos):
        res = pipeline.run(raw_df=df, offline_planner=not groq, task_meta=meta,
                           log_prefix="exploratory_run_", run_explain=explain)
        cleaned = materialize(df, res["committed_ops"])
    cp = out / f"exploratory_{stem}_clean.csv"
    cleaned.to_csv(cp, index=False)
    (out / f"exploratory_{stem}_clean.manifest.json").write_text(json.dumps(
        {"scenario": "exploratory", "spec": spec.to_dict(), "committed_ops": res["committed_ops"],
         "rows_in": len(df), "rows_out": len(cleaned), "log_path": res["log_path"]}, indent=1, default=str))
    res["clean_path"] = str(cp)
    res["mode"] = "gated"
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="AETERNA-QA sandbox runner (exploratory, never cited)")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--task", choices=taskspec.TASK_TYPES, default="binary")
    ap.add_argument("--positive", default=None, help="positive class label (binary); default = minority class")
    ap.add_argument("--model-family", choices=taskspec.MODEL_FAMILIES, default="linear")
    ap.add_argument("--id", dest="ids", nargs="*", default=[], help="ID columns to exclude")
    ap.add_argument("--drop", nargs="*", default=[], help="other columns to exclude")
    ap.add_argument("--groq", action="store_true", help="use the Groq planner (default: rule planner)")
    ap.add_argument("--no-explain", action="store_true")
    a = ap.parse_args(argv)
    try:
        spec = TaskSpec(path=a.csv, target=a.target, task_type=a.task, positive_label=a.positive,
                        model_family=a.model_family, id_columns=a.ids, drop_columns=a.drop)
        run_spec(spec, groq=a.groq, explain=not a.no_explain)
    except SpecError as e:
        print(f"Cannot run: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
