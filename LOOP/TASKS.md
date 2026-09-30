# LOOP/TASKS.md — lane A (autonomous engineering). Owner: verifier writes, builder consumes.

Rules for every task
- Read CLAUDE.md first. Do not touch: evaluator.py, evaluator_tests.py, PREREGISTRATION.md (except appending a signed row), gate metric, commit rule, scenarios, models.
- Before each commit run: `python tools/frozen_check.py` (must exit 0; exit 2 = stop and ask Akira), `python -m aeterna_qa.modules.ops_tests`, `python -m aeterna_qa.modules.evaluator_tests` (adjust invocation to how they are run today).
- Add a Documentation.md changelog entry for every change. One commit per task. Write LOOP/reports/build-<iter>.md (what changed, files, test output).
- Then set STATE.json status = ready_for_verify. Do not verify your own work.
- Synthetic results stay labelled "synthetic". No new study runs unless a task says so.

## T1 — Resolve `committed_ops: None` (pending item 1)  [P1]
Verifier's finding (Likely, not yet confirmed in code): audit.log_iteration stores dict(committed_ops), pipeline.py passes the live dict at every call. A survey of logs found 19 logs with the field populated and 11 logs with the key MISSING (older logs, before the Explain-module field was added). So the "None" is probably a read of old logs, not a logging bug.
Do: (a) for post-field logs where the run committed, show that later iterations carry a non-empty committed_ops and the final value equals the run's committed set; (b) find where "None" is produced (likely a .get() on old logs in explain.py); (c) if it is only old logs, make Explain handle a missing key explicitly (say "not recorded in this older log") instead of guessing chains; (d) if a real bug exists, fix and add a test.
Accept when: written evidence in build report with log filenames; Explain output on one old log and one new log verified by eye; no change to audit schema unless a real bug is proven; changelog entry.

## T2 — Explain guard check (pending item 2)  [P2]
Do: run Explain with the Groq note on at least 3 existing runs (different scenarios) and record, per run, whether the number-check guard passed, and any note rejected.
Accept when: table of run x guard result in the build report; any false rejection or false pass described with the exact note text; no guard logic change without Akira's OK (report only).
Constraint: never read or print .env. Groq calls only through the existing config path.

## T3 — Minor cleanups (pending item 6)  [P3]
(a) BUILD_PLAN.md demo date is blank — leave blank and list as "needs Akira" (do not invent a date).
(b) positive_control.py does not call audit — add the audit call so its run is logged and labelled synthetic. Locate the file first; it is not in modules/.
(c) IQR outlier detection unreliable on skewed columns — DOCUMENT only (known limitation, with the capital.gain example), do not change detector behaviour (would alter study inputs).
Accept when: (b) produces a run_*.json with scenario labelled synthetic; (a) and (c) noted in Documentation.md.

## Exit for lane A
T1-T3 verified, frozen_check exit 0, both test suites pass, Documentation.md current, committed. Then STOP and report. Do not look for more work.
