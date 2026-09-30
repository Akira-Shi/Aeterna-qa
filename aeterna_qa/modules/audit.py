"""
Audit logger for AETERNA-QA.

Records one entry per pipeline iteration -- column, operation, reason,
F1 before/after, delta, and accept/reject -- and writes the whole run to a
timestamped JSON file under logs/. This is the stand-in for the original
pitch's "Explain" module: honest about being basic (a log, not a
generated natural-language narrative yet), and it's real. Restoring a full
Explain step is an accepted post-demo enhancement (see Documentation.md).

Staged/commit model (2026-09-29, multi-op combination hardening): a
single operation's cumulative delta vs. the last committed baseline is
logged at proposal time, but whether it ultimately survives isn't known
until later -- an op that looks like noise alone can turn out to matter
once another op is layered on top. So a "staged" entry is written
immediately with its own delta, and once the pipeline resolves the whole
chain (commits it or discards it), resolve_chain() goes back and rewrites
every "staged" entry in that chain to its final status. The JSON log
always reflects the final outcome; nothing is left ambiguously "pending".
"""
import json
from datetime import datetime, timezone

from . import config


def new_run(meta: dict | None = None) -> dict:
    # meta (2026-09-30, Explain module): free-form provenance for the
    # report, e.g. {"scenario": "real_adult"} or
    # {"scenario": "synthetic_positive_control"} so a synthetic run is
    # never mistaken for a real one on screen.
    return {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
        "iterations": [],
    }


def log_iteration(
    run: dict,
    *,
    iteration: int,
    column: str,
    operation: str,
    reason: str,
    f1_before: float,
    f1_after: float,
    threshold: float,
    accepted: bool,
    error: str | None = None,
    std_before: float | None = None,
    std_after: float | None = None,
    se: float | None = None,
    status: str | None = None,
    chain_id: int | None = None,
    chain_ops: dict | None = None,
    committed_ops: dict | None = None,
) -> None:
    run["iterations"].append({
        "iteration": iteration,
        "column": column,
        "operation": operation,
        "reason": reason,
        "f1_before": round(f1_before, 4) if f1_before is not None else None,
        "f1_after": round(f1_after, 4) if f1_after is not None else None,
        "delta": round(f1_after - f1_before, 4) if (f1_before is not None and f1_after is not None) else None,
        # CV hardening (2026-09-29): std_before/std_after are the
        # fold-to-fold standard deviation of F1 (5-fold CV), se is the
        # standard error of the mean derived from std_before, and
        # threshold is se * config.THRESHOLD_SE_MULTIPLIER -- so the bar
        # for acceptance is now measured noise, not a fixed guess.
        "std_before": round(std_before, 4) if std_before is not None else None,
        "std_after": round(std_after, 4) if std_after is not None else None,
        "se": round(se, 4) if se is not None else None,
        "threshold": round(threshold, 4) if threshold is not None else None,
        "accepted": accepted,
        "error": error,
        # Multi-op combination hardening (2026-09-29): status is one of
        # "committed" / "staged" / "discarded" / "error". chain_id groups
        # entries that were evaluated together as one provisional chain --
        # see resolve_chain(), which rewrites "staged" entries once the
        # chain's outcome is known.
        "status": status,
        "chain_id": chain_id,
        # Explain module (2026-09-30): f1_after/delta above are measured on
        # the WHOLE staged chain layered on the committed baseline, not on
        # (column, operation) alone. Without these two fields a reader of the
        # log cannot tell what was actually tested. chain_ops = the staged
        # chain including this proposal; committed_ops = already-confirmed
        # operations at the time of the evaluation.
        "chain_ops": dict(chain_ops) if chain_ops is not None else None,
        "committed_ops": dict(committed_ops) if committed_ops is not None else None,
    })


def resolve_chain(run: dict, chain_id: int, new_status: str) -> None:
    """Rewrite every entry tagged with this chain_id and still 'staged' to
    new_status ('committed' or 'discarded'), and flip its `accepted` flag
    to match. Called once the pipeline knows how a provisional chain of
    operations resolved."""
    for entry in run["iterations"]:
        if entry.get("chain_id") == chain_id and entry.get("status") == "staged":
            entry["status"] = new_status
            entry["accepted"] = (new_status == "committed")


def save(run: dict, baseline_f1: float, final_f1: float) -> str:
    run["baseline_f1"] = round(baseline_f1, 4)
    run["final_f1"] = round(final_f1, 4)
    run["finished_at"] = datetime.now(timezone.utc).isoformat()

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = config.LOG_DIR / f"run_{ts}.json"
    path.write_text(json.dumps(run, indent=2))
    return str(path)
