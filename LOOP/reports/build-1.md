# build-1 (T1: resolve `committed_ops: None`)

## Verdict
No logging bug. The "None" comes from older logs plus an Explain headline that turned "unknown" into "(none)". Fixed in Explain only. No audit schema change.

## Evidence (all from aeterna_qa/logs/run_*.json; logs/study/ holds no run_*.json)
- Code: audit.py stores `dict(committed_ops) if committed_ops is not None else None`; all 3 `log_iteration` calls in pipeline.py pass `committed_ops=committed_ops`, so None never occurs in new logs.
- 11 logs 29 Sep (run_20260929T035527Z ... run_20260929T062818Z): key absent (also no chain_ops).
- 19 logs 30 Sep (run_20260930T033353Z ... run_20260930T094856Z): key present on every iteration, zero None values.
- Runs that committed (12 of the 19), e.g. run_20260930T055513Z (age=sentinel_to_median), run_20260930T093109Z (occupation=normalize_categories), run_20260930T093200Z (age=rescale_units), run_20260930T093903Z / 094114Z (native.country=normalize_categories), run_20260930T094529Z / 094716Z / 094856Z (capital.gain=sentinel_to_median): per-iteration len(committed_ops) is [0,1,1,1,1]-style, i.e. empty at the committing iteration (pre-commit state by design), non-empty after. Last iteration's committed_ops equals the union of chain_ops of committed iterations in every one of them (checked programmatically: 12 of 12).
- The 7 no-commit runs in the 19 show all-empty {} (never None).

## Change
- aeterna_qa/modules/explain.py: build_facts adds `committed_ops_recorded`; headline prints "committed operations not recorded in this older log" instead of "(none)" when a committed chain has no recorded ops.
- aeterna_qa/modules/explain_tests.py (new): old log, new log, no-commit cases.
- Documents/Documentation.md: changelog entry.

## Explain output (offline)
Old, run_20260929T042640Z.json:
    1 of 2 chain(s) committed (committed operations not recorded in this older log). F1 0.6733 -> 0.6816 (+0.0083).
    (before fix: "... committed ((none))")
New, run_20260930T093200Z.json:
    STUDY C2 rate 30% seed 201 (SYNTHETIC)
    1 of 2 chain(s) committed (age=rescale_units). neg-Brier -0.1058 -> -0.1046 (+0.0012).
    Chain 0: age=rescale_units -> COMMITTED

## Tests
- python tools/frozen_check.py -> "clean (baseline 2dae093)", exit 0
- python -m aeterna_qa.modules.ops_tests style (run from aeterna_qa/ as `python -m modules.ops_tests`) -> all passed
- python -m modules.evaluator_tests -> ALL PASS
- python -m modules.explain_tests -> all passed

## Notes
- Cosmetic, pre-existing (already in Known issues): discarded chain in new logs prints "(chain contents not recorded)".
- Generated report_*.html files from my Explain runs were deleted; nothing committed.
