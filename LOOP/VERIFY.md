# VERIFY.md — checklist the verifier (Cowork) runs on each ready_for_verify

1. `git log` shows exactly one new commit per task; message matches the changelog entry.
2. `python tools/frozen_check.py` exits 0 (run independently, not from the builder's report).
3. `ops_tests` and `evaluator_tests` pass (re-run).
4. Diff touches only files the task allowed; no edits under evaluator*, PREREGISTRATION (except appended signed rows), config gate constants.
5. Documentation.md entry exists and matches the diff.
6. Rule grep over changed text/output: "synthetic" label present on synthetic results; RF and LR never pooled; retracted numbers (+0.0175, F1 ~0.688, "2.0x SE", calculate_f1_cv) not cited; positives and negatives reported as k/n; planner never sees the manifest.
7. Task acceptance criteria met with evidence, not assertion.
8. Write LOOP/reports/verify-<iter>.md: PASS / NEEDS_FIX with findings; set STATE.json status = verified | needs_fix.
