"""P6a acceptance demo driver (report only, no gate). Writes aggregate tables as markdown to stdout.
Columns are reported as counts, never by name. Usage: python tools/p6a_demo.py <Adult|Marketing> <family>"""
import hashlib, sys, time, warnings
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aeterna_qa"))
warnings.filterwarnings("ignore")
from modules import taskspec                       # noqa: E402
from modules.taskspec import TaskSpec              # noqa: E402
from stage2 import rules, compare                  # noqa: E402

MK_SHA = "6a05ac3f7579d07c9731741f53012534de72a9b93ebf482e709d5c1da6e8e1a3"


def main(ds, fam):
    if ds == "Adult":
        spec = taskspec.adult_spec()
        spec = TaskSpec(**{**spec.to_dict(), "model_family": fam})
        label_note = f"positive label {spec.positive_label!r} from config.POSITIVE_CLASS (explicit in the TaskSpec, not defaulted)"
    else:
        p = ROOT / "Dataset/real/Marketing/raw/raw.csv"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == MK_SHA, "sha mismatch"
        spec = TaskSpec(path=str(p), target="Income", task_type="binary", positive_label="0", model_family=fam)
        label_note = "positive label '0' (Income=0), explicit, same as the registered P5 runs"
    df, prep = taskspec.load_dataset(spec)
    t = time.time()
    r = compare.compare(df, spec)
    print(f"### {ds} x {fam}\n")
    print(f"{label_note}. Rows {len(df)}, features {df.shape[1]-1}, rows dropped for missing target {prep['rows_dropped_missing_target']}.\n")
    print("| step | rule_id | n columns | method | reason | alternative |\n|---|---|---|---|---|---|")
    for s in r["steps"]:
        print(f"| {s['stage']} | {s['rule_id']} | {len(s['columns']) or 'estimator'} | {s['method']} | {s['reason']} | {s['alternative']} |")
    print(f"\n- neg-Brier: default {r['default_mean']:.4f}, recommended {r['recommended_mean']:.4f}, "
          f"diff (rec - default) {r['mean_diff']:+.4f} +/- {r['se_corrected']:.4f} (NB-corrected SE)")
    print(f"- F1: default {r['f1_default_mean']:.4f}, recommended {r['f1_recommended_mean']:.4f}, "
          f"diff {r['f1_mean_diff']:+.4f} +/- {r['f1_se_corrected']:.4f}")
    print(f"- final recommendation: {r['final']}" + (f" ({r['fallback_note']})" if r["fallback"] else ""))
    print(f"- {r['n_folds']} fixed folds; report only, no gate, no commit decision. ({time.time()-t:.0f}s)\n")


main(sys.argv[1], sys.argv[2])
