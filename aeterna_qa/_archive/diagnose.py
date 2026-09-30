"""
Diagnose stage runner (2026-09-30): show what the detectors find on
(1) the real Adult data and (2) the same data after the DECLARED synthetic
injection, and score the detections against the injection's answer key.

No LLM, no F1 verification yet -- this only answers "does the agent know what
is wrong and where?". Usage: python -m modules.diagnose
"""
from rich.console import Console
from rich.table import Table

from .evaluator import load_raw_dataset
from .detectors import detect
from .injection import inject, DECLARED_SPEC

console = Console()


def _table(findings, title):
    t = Table(title=title, show_lines=False)
    for c in ("defect", "column", "rows", "%", "evidence", "candidate fixes"):
        t.add_column(c)
    for f in findings:
        t.add_row(f["defect"], f["column"], str(f["n_rows"]), f"{f['pct']:.2f}",
                  f["evidence"], ", ".join(f["candidate_ops"]))
    console.print(t)


def score_against_manifest(findings, manifest, corrupted_df):
    t = Table(title="Detections vs injection answer key (SYNTHETIC)")
    for c in ("injected", "column", "detected?", "detected as", "row-level check"):
        t.add_column(c)
    for m in manifest:
        hit = [f for f in findings if f["column"] == m["column"] and f["defect"] == m["kind"]]
        if not hit:
            t.add_row(m["id"], m["column"], "MISSED", "-", "-")
            continue
        f = hit[0]
        if m["kind"] == "sentinel":
            flagged = set(corrupted_df.index[corrupted_df[m["column"]] == f["detail"]["value"]])
            truth = set(m["rows"])
            tp = len(flagged & truth)
            rowchk = f"precision {tp/max(len(flagged),1):.3f}, recall {tp/max(len(truth),1):.3f}"
        else:
            canon = f["detail"]["canonical"]
            is_changed = corrupted_df[m["column"]].map(lambda x: isinstance(x, str) and canon.get(x, x) != x).astype(bool)
            changed = set(corrupted_df.index[is_changed])
            truth = set(m["rows"])
            tp = len(changed & truth)
            rowchk = f"precision {tp/max(len(changed),1):.3f}, recall {tp/max(len(truth),1):.3f}"
        t.add_row(m["id"], m["column"], "YES", f["defect"], rowchk)
    console.print(t)

    injected_cols = {(m["column"], m["kind"]) for m in manifest}
    extra = [f for f in findings if f["defect"] in ("sentinel", "category_variants") and (f["column"], f["defect"]) not in injected_cols]
    console.print(f"Findings not in the answer key (real Adult quirks, not false alarms by default): "
                  f"{[(f['column'], f['defect']) for f in extra] or 'none'}")


def run():
    raw = load_raw_dataset()
    console.rule("[bold]REAL DATA[/bold] (Adult Census, untouched)")
    real_findings = detect(raw)
    _table(real_findings, "Detector findings - real data")

    console.rule("[bold]SYNTHETIC INJECTION[/bold] (declared spec, not real)")
    for m in DECLARED_SPEC:
        console.print(f"  declared: {m['id']}: {m['kind']} in '{m['column']}' at {m['rate']:.0%}"
                      + (f", value={m['value']}" if 'value' in m else "") + f"  -> expected fix: {m['expected_fix']}")
    corrupted, manifest = inject(raw)
    findings = detect(corrupted)
    _table(findings, "Detector findings - after injection (SYNTHETIC)")
    score_against_manifest(findings, manifest, corrupted)


if __name__ == "__main__":
    run()
