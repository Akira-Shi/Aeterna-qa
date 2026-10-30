# verify-1 — T1 (commit ce381ec) — PASS

Verifier: Cowork, independent. Ran in a scratch clone of committed HEAD (working folder untouched).

| # | Check | Result |
|---|---|---|
| 1 | One commit for T1, message matches changelog | PASS — ce381ec, 4 files (explain.py, explain_tests.py, Documentation.md, build-1.md) |
| 2 | frozen_check | PASS — exit 0 on HEAD; baseline re-derived from committed blobs matches manifest on all 4 keys; manifest/frozen files unchanged since 0798d58 |
| 3 | Tests re-run | PASS — ops_tests, evaluator_tests (LR leak tests, ALL PASS), explain_tests |
| 4 | Diff scope | PASS — no evaluator*, PREREGISTRATION, config, study, injection changes; audit schema untouched |
| 5 | Changelog matches diff | PASS — entry describes build_facts flag + headline branch + new tests |
| 6 | Rule grep | PASS on retracted numbers (none). See note 1 on labelling |
| 7 | Acceptance evidence | PASS — independently reproduced: 30 logs, 11 key-missing (29 Sep), 19 key-present, 0 None; 12 committed runs, last committed_ops == union of chain_ops in 12/12 |

## Notes (non-blocking)
1. (Likely) The old-log Explain output "F1 0.6733 -> 0.6816" carries no scenario/synthetic label because 29-Sep logs have no scenario/meta keys. Provenance of those runs is unknown to me. Do not quote that run in any deck or result without confirming what it was. Not a T1 defect.
2. TASKS.md test invocation was wrong (`aeterna_qa.modules.*`); corrected to run from `aeterna_qa/` as `python -m modules.*`.
3. One edge in the new logic: `ops_recorded` is True when no chain committed (all() over empty). Correct behaviour, and covered by the no-commit test.
4. STATE.json and this report are uncommitted working-tree changes; commit with T2.

## Verdict
T1 verified. Cleared to proceed to T2 (needs the Windows session: Groq key lives there; verifier never reads .env).
