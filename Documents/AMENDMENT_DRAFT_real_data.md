# DRAFT - proposed PREREGISTRATION section 12 amendment: real-data evaluation (phase 3)

**Status: DRAFT for Akira. Nothing here is decided, signed or run. `PREREGISTRATION.md` is not edited.** If accepted, the accepted items become dated rows appended to section 12 by Akira (or on Akira's instruction). Every item below is a proposal to accept, reject or change. No dataset has been run, opened for results, or scored for this draft; candidates are listed from general knowledge of public benchmarks only.

Context read: PREREGISTRATION sections 1-13, RESULTS.md, BUILD_PLAN.md, CLAUDE.md. Facts used: the v1 study is synthetic damage on one dataset (Adult) and cannot claim anything about arbitrary real dirty tables (section 1). The only real-data result so far is real Adult `?` values: nothing commits under the Brier gate, which matches ground truth (section 12, 2026-09-30; BUILD_PLAN). Section 12 already narrowed the evaluator to LR alone (RF dropped); CLAUDE.md still says "report RF and LR separately", see open question Q6.

## A. Purpose and what it can claim (proposal)

- Question: on real tables with natural (not injected by us) defects, does the unchanged agent commit only repairs that help a held-out downstream score, and roll back otherwise?
- It can claim: behaviour of the unchanged gate on N named real datasets, as k/n per dataset. It cannot claim general effectiveness on arbitrary tables.
- Outcome of interest is the gate decision and its audit trail, not a leaderboard score.

## B. Frozen, reused unchanged (not up for amendment)

Evaluator (`evaluator.py`, fixed 5x3 folds, Nadeau-Bengio corrected SE), LR with in-fold StandardScaler, gate = Brier with F1 reported beside every decision, commit rule `delta > 0 and delta >= bar` at Bonferroni alpha = 0.05 / (candidate ops in that run), staging rule (25% of own bar), op menu, detectors, planner menu constraint, planner blindness. Scenarios C1-C5 are untouched and keep their synthetic labels.

## C. Dataset and task selection (proposal)

**C1. Selection rule, written before any run.** A table is eligible only if all hold, checked from metadata and a row count, never from agent output or model scores:
1. Publicly downloadable with a stable URL/DOI and a licence permitting use.
2. A tabular supervised target already defined by the source (binary or multiclass), no target engineering by us.
3. At least 5,000 rows after dropping the target-missing rows (needed for the 5x3 CV with a usable SE; Adult pilot SE was ~0.0005-0.0017 at 6k-24k rows).
4. At least one documented, natural data-quality issue (missing codes, mixed units, inconsistent categories, duplicates) stated by the source or by a published cleaning benchmark.
5. Not Adult (already observed).

**C2. Picking among eligible tables:** fixed by a mechanical rule, not by judgment: order eligible candidates by a pre-written key (proposal: arXiv/benchmark publication year, then alphabetical name), take the first N. Proposed N = 3 (Q1).

**C3. Candidate pool (illustrative, to be confirmed or replaced by Akira before any run):** datasets from the Raha/Baran cleaning benchmarks that ship a dirty and a hand-cleaned version (Hospital, Flights, Beers, Rayyan, Tax; most are small or lack a clean supervised target, so many will fail rule 2 or 3), and OpenML/UCI tables with documented missing codes (for example Bank Marketing "unknown", Census-Income KDD, Credit-g). Eligibility of each is unchecked. If fewer than N pass, the study runs on those that pass and says so; the rule is not relaxed.

**C4. No dataset is added, dropped or swapped after the first run on any dataset.** A dataset that errors out for engineering reasons (parse failure) is logged as "not evaluated" with the reason; it is not replaced.

## D. Ground truth on real data (proposal; this is the hardest item)

There is no injection manifest on real tables, so "correct" cannot mean "restored the injected value". Options, to be chosen in Q2:
- **G1 (strongest, scarce):** a dataset with a published hand-cleaned counterpart. Ground truth = cell-level agreement with that counterpart; downstream gate is secondary.
- **G2 (documented-defect):** the source documents a specific defect (for example "unknown" codes). Ground truth = the documented defect is the only thing the agent may reasonably repair; a commit on an undocumented column is reported as "unexplained commit", not as success or failure.
- **G3 (null expectation):** where no defect is documented, the pre-stated expectation is "nothing commits" (as for Adult `?`). A commit is then reported as a finding to investigate, not as an error by default, because natural data can carry a real gain.
- Expected outcome per dataset is written down (commit col X / nothing) BEFORE running, in a locked file with a timestamp and commit hash, using only metadata and documentation (not pilot or eval scores). Whether to use a pilot partition at all on real data is Q3.

## E. Hypotheses and success/failure criteria (stated in advance; proposal)

- **H1 (safety):** on datasets where the registered expectation is "nothing commits", the agent commits nothing. Success: k of n datasets with no commit; failure for any dataset that commits. Each failure is reported.
- **H2 (sensitivity):** on datasets with a documented defect expected to commit, the agent commits the matching repair. Success: k of n. A miss is reported as a miss; no severity or threshold change.
- **H3 (no harm):** every committed op has a final gate delta >= 0 on the held-out evaluation partition and no collateral damage measurable against ground truth where G1 applies. Any commit with negative delta on a partition not used for the commit decision is a failure of the gate and is reported prominently.
- **Reporting of the inevitable:** positives (H2) and negatives (H1) are reported separately as k/n, never pooled. No overall accuracy number across both.
- A "pass" for the phase is not defined as all-hypotheses-true; the deliverable is the pre-stated table and an honest reading, including false commits and misses.

## F. Statistics (proposal)

- **Bonferroni family:** unchanged per run (alpha / candidate ops in that run), as the commit rule requires. A family-wide correction across datasets x ops is NOT applied to the commit rule (that would change it). Proposal: additionally report, for information only, the number of runs and an across-dataset family size (= total candidate ops tried over all N datasets), and flag any commit that would not survive it. Q4.
- **Seeds:** the planner/ops are deterministic on real data (no injection), so the seed matters only for planner randomness and fold assignment. Proposal: reuse the fixed folds scheme; run seeds 401, 402, 403 (new, disjoint from 101-103, 201-203, 301) for the Groq planner only; the rule planner runs once. Q5.
- **Splits:** if a pilot/eval split is used (Q3), 20/80 stratified on the target with a new fixed seed (proposal 20261101-style value chosen by Akira before any run) and grouped on duplicate feature vectors as in section 2.

## G. Reporting (proposal)

- Per dataset: expected outcome, committed ops, gate delta with 95% CI, bar, F1 beside it, rollback count, audit-log path.
- LR is the study model. RF is reported only if Akira re-enables it (Q6); if both, always separately, never pooled.
- Every result labelled "real (not injected)", separate from synthetic C1-C5, in tables, file names and docs.
- Planner comparison (Groq vs rule) reported as efficiency only, as in RESULTS.md; no accuracy claim.
- The Explain HTML report stays unchanged (no banner rule); provenance lives in the audit log and docs.

## H. What may NOT change after seeing any real-data result

Dataset list and N; the selection and tie-break rule; expected outcomes; ground-truth definition; gate metric (Brier); commit rule and Bonferroni definition; staging fraction; op menu and detectors; folds and seeds; hypotheses and success/failure wording; the set of reported metrics. Anything outside this list that must change (bug fix, parse error) needs a dated, append-only entry stating that it was made after seeing results, as was done for the staging rule on 2026-09-30. No result is selected, discarded or re-run because of its value.

## I. Known weaknesses stated up front

- Real tables may have no recoverable ground truth, so H2 is weak without G1 datasets.
- The agent only has the v1 op menu (fill, drop_rows, clip, fill_unknown, normalize_categories, sentinel_to_median, rescale_units); defects outside it cannot be repaired (misses are expected).
- LR with the Brier gate has low power where the damaged columns carry little signal (age: 0.00096 headroom in v1).
- Natural defects that are actually informative (for example "unknown" as a real category) may legitimately make a commit hurt or not help; the gate may roll back a "correct" repair.
- Small N, no family-wide correction in the commit rule, planner-blindness retained but dataset documentation is public and may be in the LLM's training data.

## J. Open questions for Akira

1. N: how many datasets (draft: 3)? Any you want named up front, before running anything?
2. Ground truth: G1 only (needs a clean counterpart), G1+G2, or include G3 null-expectation datasets? How to label an "unexplained commit"?
3. Use a pilot/eval split on real data, or evaluate on the full table with expectations fixed from documentation only?
4. Report an across-dataset family-wide Bonferroni figure for information only, or omit it?
5. Seeds for Groq runs (draft 401-403) and whether the rule planner also gets repeats; Groq free-tier rate limits and cost.
6. RF: section 12 dropped RF, CLAUDE.md says report RF and LR separately. Which holds for real data?
7. Is any real Adult run beyond `?` (for example other columns) in scope, or is Adult closed?
8. Should H1/H2 thresholds (for example "at least 2 of 3") be stated, or stay descriptive k/n?
9. Who signs the expected-outcome file and when (before first run, with commit hash)?
10. Do v2 phases P4 (any-CSV TaskSpec) change how a task/target is specified for these datasets, and must TaskSpec be frozen before this amendment is signed?
11. Licensing/PII check for candidate datasets: who clears it?
12. If fewer than N tables pass the eligibility rule, is a smaller N acceptable, or must the pool be widened (by a rule written before looking)?
