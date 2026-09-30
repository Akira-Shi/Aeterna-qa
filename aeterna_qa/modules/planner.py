"""
LLM planner for AETERNA-QA.

2026-09-30: now driven by detectors.detect() FINDINGS (defect, column, row
count, evidence), not the profiler's null_pct report -- the planner is told
what is wrong and where, and picks the repair. plan_offline() is a no-LLM
rule-based twin (testing without a key, and an LLM-vs-rule ablation baseline).

Sends the findings to Groq (config.MODEL_NAME) and asks for a
JSON decision: which column to act on, which operation to apply, and why.
The model is constrained to config.OPERATION_MENU only -- it reasons about
which option to pick, it does not generate code (see Documentation.md,
2026-09-04 decision, carried forward).

Uses a strict JSON schema (response_format type json_schema) restricted
to UNTRIED, dtype-valid (column, operation) combinations, computed
deterministically in Python -- not left to the model's judgment. Two
earlier approaches were tried and both failed in practice:
  1. Plain json_object mode with no enum constraint -> the model returned
     syntactically valid but all-null JSON.
  2. An enum constraint plus a "ban this operation after 2 failures"
     heuristic -> with only 2 operations valid for text columns
     (fill_mode, drop_rows) and 3 candidate columns, both operations hit
     the ban threshold before every column had been tried, leaving zero
     dtype-valid options and forcing invalid combinations (e.g. fill_mean
     on a string column) into the remaining iterations. The model also
     never explored the lowest-missingness column on its own, anchoring
     on "highest missingness" reasoning every time even though nothing in
     the prompt or schema prevented it from choosing otherwise.
This version removes the guesswork: it computes the actual set of
dtype-valid, not-yet-tried (column, operation) pairs and restricts the
schema to exactly those, so real progress through the search space is
guaranteed rather than hoped for.
"""
import json

from groq import Groq

from . import config


def _op_valid_for_dtype(operation: str, dtype: str) -> bool:
    """Kept for backward compatibility (positive_control/exhaustive_search import
    style). The detector-driven planner no longer needs it: detectors only
    propose ops that fit the column's type."""
    if operation in {"fill_mean", "fill_median", "clip_outliers", "sentinel_to_median", "rescale_units"}:
        return "int" in dtype or "float" in dtype
    if operation == "normalize_categories":
        return not ("int" in dtype or "float" in dtype)
    return True


_SYSTEM_PROMPT = """You are a data-cleaning planner for a tabular dataset. \
You are given "findings": defects that deterministic detectors found in the \
data, each with its column, the number/percentage of rows affected, and \
evidence. You are also given "remaining_options": the only \
(column, operation) pairs you may choose from (already filtered to pairs \
that fit the defect and have not been tried yet).

Pick exactly ONE pair from remaining_options. Choose the operation that \
directly repairs the defect named in the evidence: a missing-value code \
(sentinel) needs sentinel_to_median, not a clip; a column that mixes two units (mixed_units) needs rescale_units; spelling variants need \
normalize_categories; exact duplicate rows need dedupe_rows. Prefer defects \
that affect more rows or damage a feature the model relies on. Your reason \
must cite the evidence (row counts, values) for the pair you chose. \
Do not claim the fix will improve the model score: that is measured after \
you choose, not predicted by you. If earlier attempts appear in \
"already_tried_and_rejected", weigh them and do not repeat their logic."""


# Lower = tried earlier by the offline (no-LLM) planner. Defects whose repair is
# a direct inverse of the corruption go first; ambiguous ones last.
_DEFECT_PRIORITY = {"sentinel": 0, "mixed_units": 1, "category_variants": 2, "duplicates": 3, "missing": 4, "top_coded": 5}


def _client() -> Groq:
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY not set. Create a .env file at the Capstone repo "
            "root with GROQ_API_KEY=your_key_here."
        )
    return Groq(api_key=config.GROQ_API_KEY)


def remaining_options(findings: list[dict], rejected: list[tuple[str, str]] | None = None):
    """Deterministically enumerate untried (column, operation) pairs that the
    detectors' findings justify. Returns [(column, operation, finding), ...];
    a pair reachable from several findings keeps the higher-priority one."""
    rejected_set = set(rejected or [])
    seen, out = set(), []
    for f in sorted(findings, key=lambda f: (_DEFECT_PRIORITY.get(f["defect"], 9), -f["n_rows"])):
        for op in f["candidate_ops"]:
            pair = (f["column"], op)
            if op not in config.OPERATION_MENU or pair in rejected_set or pair in seen:
                continue
            seen.add(pair)
            out.append((f["column"], op, f))
    return out


def plan_offline(findings: list[dict], rejected: list[tuple[str, str]] | None = None) -> dict:
    """No-LLM planner: first remaining option by defect priority, then size.
    Exists (a) so the pipeline can be run and tested without a Groq key and
    (b) as an ablation baseline -- does the LLM add anything over a fixed rule?"""
    opts = remaining_options(findings, rejected)
    if not opts:
        raise ValueError("No untried, dtype-valid (column, operation) combinations remain.")
    column, operation, f = opts[0]
    return {"column": column, "operation": operation,
            "reason": f"[offline rule] {f['defect']} in {column}: {f['evidence']}."}


def plan(findings: list[dict], rejected: list[tuple[str, str]] | None = None) -> dict:
    """Given detectors.detect()'s findings, return {"column", "operation",
    "reason"}. Raises ValueError if no untried pair remains -- the pipeline
    treats that as "nothing more to try", not a failure."""
    rejected = rejected or []
    opts = remaining_options(findings, rejected)
    if not opts:
        raise ValueError("No untried, dtype-valid (column, operation) combinations remain.")
    remaining_pairs = [(c, op) for c, op, _ in opts]
    allowed_columns = sorted({c for c, _ in remaining_pairs})
    allowed_operations = sorted({op for _, op in remaining_pairs})

    client = _client()
    payload = {
        "findings": [
            {k: f[k] for k in ("defect", "column", "n_rows", "pct", "evidence", "candidate_ops")}
            for f in findings
        ],
        "remaining_options": [{"column": c, "operation": o} for c, o in remaining_pairs],
    }
    if rejected:
        payload["already_tried_and_rejected"] = [{"column": c, "operation": o} for c, o in rejected]

    schema = {
        "type": "object",
        "properties": {
            "column": {"type": "string", "enum": allowed_columns},
            "operation": {"type": "string", "enum": allowed_operations},
            "reason": {"type": "string"},
        },
        "required": ["column", "operation", "reason"],
        "additionalProperties": False,
    }
    resp = client.chat.completions.create(
        model=config.MODEL_NAME,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_schema", "json_schema": {"name": "cleaning_plan", "schema": schema, "strict": True}},
        temperature=0.2,
    )
    raw = resp.choices[0].message.content
    decision = json.loads(raw)
    for key in ("column", "operation", "reason"):
        if not decision.get(key):
            raise ValueError(f"Planner response missing/null '{key}': {raw}")
    if (decision["column"], decision["operation"]) not in remaining_pairs:
        raise ValueError(
            f"Planner chose ({decision['column']}, {decision['operation']}), which is not "
            f"in remaining_options: {remaining_pairs}"
        )
    return decision


if __name__ == "__main__":
    from .evaluator import load_raw_dataset
    from .detectors import detect

    df = load_raw_dataset()
    decision = plan(detect(df))
    print(json.dumps(decision, indent=2))
