# DRAFT v2 - proposed PREREGISTRATION section 12 amendment: real-data evaluation (phase 3)

**Status: DRAFT v2, Akira's decisions applied (2026-11-01). Not signed, not run. `PREREGISTRATION.md` is not edited.** Signing happens after P4 is tagged (section K). On signing, the accepted items become dated rows appended to section 12 by Akira (or on Akira's instruction). No dataset has been run or scored for this draft. Row counts and error types below come from CleanML's `DatasetDescriptions.pdf` metadata only.

Context read: PREREGISTRATION sections 1-13, RESULTS.md, BUILD_PLAN.md, CLAUDE.md. Facts used: the v1 study is synthetic damage on one dataset (Adult) and cannot claim anything about arbitrary real dirty tables (section 1). The only real-data result so far is real Adult `?` values: nothing commits under the Brier gate, which matches ground truth (section 12, 2026-09-30; BUILD_PLAN). Section 12 already narrowed the evaluator to LR alone (RF dropped); CLAUDE.md's RF/LR line is updated for real data (LR only; RF reproduces old numbers only).

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

**C2. Picking among eligible tables (decided: N = 2).** Source = the CleanML benchmark (Li et al., https://arxiv.org/abs/1904.09483; repo https://github.com/chu-data-lab/CleanML). Order = the order of entries in the repo file `schema/dataset.py` (https://raw.githubusercontent.com/chu-data-lab/CleanML/master/schema/dataset.py), read by fetch: Citation, Marketing, Airbnb, Titanic, EEG, USCensus, Restaurant, Credit, Sensor, Movie, Company, University, then synthetic-mislabel variants (excluded: injected, not natural), BabyProduct, Clothing. The paper's Table 3 order could not be recovered from the HTML extraction (unverified), so the repo order is the written key. Take the first 2 datasets passing C1; if one fails for any reason (including rule 6 below), take the next in this order.

**C1 rule 6 (proposed, before any run):** at least 3 feature columns, at least one numeric or low-cardinality categorical (the v1 op menu and LR evaluator are tabular). Mechanical application, from `DatasetDescriptions.pdf` metadata:

| Order | Dataset | Rows | Check | Result |
|---|---|---|---|---|
| 1 | Citation | 5,005 | titles only (single text column; duplicates): fails rule 6 | skipped |
| 2 | Marketing | 8,993 | 14 demographic attrs, missing values, label income < $25k | **selected #1** |
| 3 | Airbnb | 42,492 | 40 attrs; missing, outliers, duplicates; label rating = 5 | **selected #2** (licence/PII concern, section J) |
| 4 | Titanic | 891 | fails rule 3 (< 5,000 rows) | skipped |
| 5 | EEG | 14,980 | 14 numeric attrs, outliers | **fallback #1** |
| 6 | USCensus | 32,561 | UCI Census, 14 attrs (Adult-like; rule 5 question, Q-new-4) | **fallback #2 candidate** |

If Airbnb is rejected on licence/PII grounds (Akira's call), the fallback is EEG, then the next passing dataset in order. Swaps are logged; a dataset is never replaced after its first run (C4).

**C4. No dataset is added, dropped or swapped after the first run on any dataset.** A dataset that errors out for engineering reasons (parse failure) is logged as "not evaluated" with the reason; it is not replaced.

## D. Ground truth on real data (decided)

- **Ground truth = the published cleaned version.** For CleanML this is the benchmark's cleaned file per error type. The paper abstract says the benchmark applies "multiple cleaning algorithms per error type", so the reference cleaned file must be named per dataset in the expected-outcome file before any run (Q-new-1).
- **Hit** = the committed op targets a column and an error type that both appear in the dirty-vs-clean diff. **Miss** = the diff shows a menu-reachable defect and nothing commits for it. **Correct rollback** = no commit and no menu-reachable diff.
- **Unexplained commit** = a commit on a column with no diff. Reported separately; not a hit, not a failure by itself.
- **Wrong-op commit** (op type does not match the diff error type on that column) = failure.
- Expectations are qualitative only (commit / no commit, per column), derived from the diff, not from scores, and written in the expected-outcome file (section K).
- **Split:** 20/80 pilot/eval. The pilot only checks that the pipeline runs end to end; it sets no expectations and tunes nothing.

## E. Hypotheses and success/failure criteria (stated in advance; proposal)

- **H1 (safety):** on datasets where the registered expectation is "nothing commits", the agent commits nothing. Success: k of n. A commit on a no-diff column is an "unexplained commit", reported separately.
- **H2 (sensitivity):** on datasets with a documented defect expected to commit, the agent commits the matching repair. Success: k of n. A miss is reported as a miss; no severity or threshold change.
- **Failure condition (decided):** any wrong-op commit fails the phase. Everything else is descriptive k/n; no thresholds such as "2 of 3".
- **H3 (no harm):** every committed op has a final gate delta >= 0 on the held-out evaluation partition and no collateral damage measurable against ground truth where G1 applies. Any commit with negative delta on a partition not used for the commit decision is a failure of the gate and is reported prominently.
- **Reporting of the inevitable:** positives (H2) and negatives (H1) are reported separately as k/n, never pooled. No overall accuracy number across both.
- A "pass" for the phase is not defined as all-hypotheses-true; the deliverable is the pre-stated table and an honest reading, including false commits and misses.

## F. Statistics (decided)

- **Primary:** Bonferroni per run, unchanged (alpha / candidate ops in that run).
- **Secondary (information only):** an across-dataset correction (family = total candidate ops over all datasets and runs); flag any commit that would not survive it. It never changes a decision.
- **Seeds:** 401, 402, 403, both planners (rule and Groq). Evaluator: LR only.
- **Splits:** 20/80 pilot/eval, stratified on the target, grouped on duplicate feature vectors as in section 2; split seed chosen by Akira before any run and recorded in the expected-outcome file.

## G. Reporting (proposal)

- Per dataset: expected outcome, committed ops, gate delta with 95% CI, bar, F1 beside it, rollback count, audit-log path.
- LR is the only model for real-data evaluation. RF reproduces old numbers only.
- Every result labelled "real (not injected)", separate from synthetic C1-C5, in tables, file names and docs.
- Planner comparison (Groq vs rule, both run) reported as efficiency only, as in RESULTS.md; no accuracy claim.
- The Explain HTML report stays unchanged (no banner rule); provenance lives in the audit log and docs.

## H. What may NOT change after seeing any real-data result

Dataset list and N; the selection and tie-break rule; expected outcomes; ground-truth definition; gate metric (Brier); commit rule and Bonferroni definition; staging fraction; op menu and detectors; folds and seeds; hypotheses and success/failure wording; the set of reported metrics. Anything outside this list that must change (bug fix, parse error) needs a dated, append-only entry stating that it was made after seeing results, as was done for the staging rule on 2026-09-30. No result is selected, discarded or re-run because of its value.

## I. Known weaknesses stated up front

- Real tables may have no recoverable ground truth, so H2 is weak without G1 datasets.
- The agent only has the v1 op menu (fill, drop_rows, clip, fill_unknown, normalize_categories, sentinel_to_median, rescale_units); defects outside it cannot be repaired (misses are expected).
- LR with the Brier gate has low power where the damaged columns carry little signal (age: 0.00096 headroom in v1).
- Natural defects that are actually informative (for example "unknown" as a real category) may legitimately make a commit hurt or not help; the gate may roll back a "correct" repair.
- Small N, no family-wide correction in the commit rule, planner-blindness retained but dataset documentation is public and may be in the LLM's training data.

## J. Licence and PII status per chosen dataset (for Akira to confirm)

| Dataset | Source | Licence | PII | Status |
|---|---|---|---|---|
| Marketing | https://sites.google.com/site/anhaidgroup/useful-stuff/data (per CleanML refs) | (unverified) | demographic survey records (sex, education, etc.); no identifiers described (unverified) | Akira to confirm |
| Airbnb | CleanML-authored, scraped from Airbnb.com plus city-data.com attributes; "We will release this dataset in the code repository" (`DatasetDescriptions.pdf`) | (unverified); scraping terms of Airbnb.com may apply (unverified) | listing-level data; host or location fields may be present (unverified) | Akira to confirm; if rejected, fallback EEG |
| EEG (fallback #1) | https://archive.ics.uci.edu/dataset/264/eeg+eye+state | CC BY 4.0 (stated on the UCI page) | UCI page has no PII statement; EEG channel recordings | Akira to confirm |
| CleanML repo (code, cleaned files) | https://github.com/chu-data-lab/CleanML | GitHub API `license` = null (none declared) | n/a | Akira to confirm terms for using the data zip (Dropbox `CleanML-datasets-2020.zip`, per the README) |

## K. Procedure: expected-outcome file, signing, P4 dependency

1. After datasets are confirmed and before any run, `Documents/EXPECTED_OUTCOMES_real_data.md` is written from the dirty-vs-clean diff only (per dataset: reference cleaned file, columns and error types in the diff, expected commit / no commit per column, split seed). It uses no pilot or eval scores.
2. Akira reviews and signs it (signature line left blank; Claude does not sign).
3. The file is committed. Its git commit hash and SHA-256 are recorded in the new section 12 row. No run may start before this commit exists.
4. This amendment cites the TaskSpec release tag `v2-p4` (placeholder until P4 is tagged). It is signed only after P4 is tagged, and TaskSpec is then frozen for this study.

## L. Open questions still needing Akira

- **Q-new-1:** CleanML ships cleaned files per cleaning method. Which is the reference per dataset?
- **Q-new-2:** Add C1 rule 6 (at least 3 feature columns, one numeric or low-cardinality categorical)? It skips Citation. Without it Citation is #1 and Marketing #2.
- **Q-new-3:** Airbnb licence/PII (section J): accept, or move to fallback EEG?
- **Q-new-4:** Does USCensus count as Adult for rule 5 (UCI Census data, 32,561 records, 14 attributes)?
- **Q-new-5:** Marketing licence and PII are unverified.
- **Q-new-6:** The key is the repo order in `schema/dataset.py`; the paper's Table 3 order is unverified. Confirm the repo order.

Resolved by decisions (2026-11-01): N = 2 with next-in-order fallback; ground truth = published cleaned version; 20/80 split with pilot as pipeline check only; per-run Bonferroni primary, across-dataset secondary; seeds 401-403 both planners; LR only; Adult beyond `?` closed; descriptive k/n with wrong-op = failure; signing procedure and P4 dependency.
