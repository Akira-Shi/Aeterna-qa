# DRAFT v2 - proposed PREREGISTRATION section 12 amendment: real-data evaluation (phase 3)

**Status: DRAFT v4, ready for Akira's signature (2026-11-01): evaluator v1.1, positive labels, licences, rule-6 type check applied. Not signed. No pre-registered run has been made. `PREREGISTRATION.md` is not edited.** Signing happens after P4 is tagged (section K). On signing, the accepted items become dated rows appended to section 12 by Akira (or on Akira's instruction). The datasets were downloaded and opened for P4 acceptance only (column types, row counts, label coding; one exploratory sandbox run on Marketing, never interpreted, no expectation derived from it). Error types come from CleanML's `DatasetDescriptions.pdf`.

Context read: PREREGISTRATION sections 1-13, RESULTS.md, BUILD_PLAN.md, CLAUDE.md. Facts used: the v1 study is synthetic damage on one dataset (Adult) and cannot claim anything about arbitrary real dirty tables (section 1). The only real-data result so far is real Adult `?` values: nothing commits under the Brier gate, which matches ground truth (section 12, 2026-09-30; BUILD_PLAN). Section 12 already narrowed the evaluator to LR alone (RF dropped); CLAUDE.md's RF/LR line is updated for real data (LR only; RF reproduces old numbers only).

## A. Purpose and what it can claim (proposal)

- Question: on real tables with natural (not injected by us) defects, does the unchanged agent commit only repairs that help a held-out downstream score, and roll back otherwise?
- It can claim: behaviour of the unchanged gate on N named real datasets, as k/n per dataset. It cannot claim general effectiveness on arbitrary tables.
- Outcome of interest is the gate decision and its audit trail, not a leaderboard score.

## B. Frozen, reused unchanged (not up for amendment)

**Evaluator version: v1.1** (2026-11-01, signed off by Akira; changelog entry "evaluator v1.1" in `Documentation.md`). v1.1 adds one thing to v1: in each CV fold, numeric columns containing NaN are median-imputed by a `SimpleImputer` fitted on that fold's TRAINING rows only (a no-op when no NaN is present, so every v1 Adult/C1-C5 number reproduces exactly: 15/15 runs matched RESULTS.md). Nothing else changed.

**Consequence for expected outcomes on continuous-NaN columns:** because the evaluator already median-imputes numeric NaN inside every fold, `fill_median` / `fill_mean` on a continuous numeric column is, to the gate, equivalent to doing nothing, so the expected outcome for those ops is **no commit** (paired delta approximately 0, below the bar). A commit there is an "unexplained commit", reported separately. `drop_rows`, `fill_unknown` and categorical fills are unaffected by this note. Expected-outcome files (section K) apply this rule per column.

Evaluator (`evaluator.py`, fixed 5x3 folds, Nadeau-Bengio corrected SE), LR with in-fold StandardScaler, gate = Brier with F1 reported beside every decision, commit rule `delta > 0 and delta >= bar` at Bonferroni alpha = 0.05 / (candidate ops in that run), staging rule (25% of own bar), op menu, detectors, planner menu constraint, planner blindness. Scenarios C1-C5 are untouched and keep their synthetic labels.

## C. Dataset and task selection (proposal)

**C1. Selection rule, written before any run.** A table is eligible only if all hold, checked from metadata and a row count, never from agent output or model scores:
1. Publicly downloadable with a stable URL/DOI and a licence permitting use.
2. A tabular supervised target already defined by the source (binary or multiclass), no target engineering by us.
3. At least 5,000 rows after dropping the target-missing rows (needed for the 5x3 CV with a usable SE; Adult pilot SE was ~0.0005-0.0017 at 6k-24k rows).
4. At least one documented, natural data-quality issue (missing codes, mixed units, inconsistent categories, duplicates) stated by the source or by a published cleaning benchmark.
5. Not Adult (already observed), and not any dataset of the Adult family: USCensus (UCI Census income, 32,561 rows, 14 attributes) is excluded on the same ground (Q4 resolved).
6. At least 3 non-text feature columns (numeric or categorical; free-text columns do not count). **Added after viewing the CleanML dataset list (`DatasetDescriptions.pdf` metadata), before any dataset was opened or run.** The v1 op menu and LR evaluator are tabular; this rule is disclosed here as a post-listing addition (Q2 resolved).

**C2. Picking among eligible tables (decided: N = 2).** Source = the CleanML benchmark (Li et al., https://arxiv.org/abs/1904.09483; repo https://github.com/chu-data-lab/CleanML). Order = the order of entries in the repo file `schema/dataset.py` (https://raw.githubusercontent.com/chu-data-lab/CleanML/master/schema/dataset.py), read by fetch: Citation, Marketing, Airbnb, Titanic, EEG, USCensus, Restaurant, Credit, Sensor, Movie, Company, University, then synthetic-mislabel variants (excluded: injected, not natural), BabyProduct, Clothing. The paper's Table 3 order could not be recovered from the HTML extraction (unverified), so the repo order is the written key. Take the first 2 datasets passing C1; if one fails for any reason (including rule 6 below), take the next in this order.

**C1 rule 6 application (mechanical, from `DatasetDescriptions.pdf` metadata only; no dataset opened):**

| Order | Dataset | Rows | Check | Result |
|---|---|---|---|---|
| 1 | Citation | 5,005 | titles only (single text column; duplicates): fails rule 6 | skipped |
| 2 | Marketing | 8,993 | 14 demographic attributes, label income < $25k, so 13 feature columns; the PDF describes them as demographic survey fields (not free text), so >= 3 non-text. **Verified from `raw/raw.csv` (8,993 rows x 14 columns): 13 feature columns, all categorical text-coded demographics (Sex, Marital, Age brackets, Education, Occupation, Live, Dual, Person, Person under 18, Householder, Hometype, Ethnic, Language), 2-10 levels each, none free text, 0.8%-10.2% missing; 1,154 exact duplicate rows.** Rule 6 passes | **selected #1** |
| 3 | Airbnb | 42,492 | 40 attributes; label rating = 5; includes some free-text fields but also numeric and categorical listing attributes (price, counts, room type, city-data.com attributes), so >= 3 non-text. **Verified from `raw/raw.csv` (33,145 rows x 40 columns; the PDF says 42,492, the file is what is used): 39 feature columns, 38 numeric (listing counts, price, latitude/longitude, zipcode, city-data.com demographics) and 1 categorical (LocationName, 276 levels); no free-text column; no host name or host ID column exists in the file, so nothing needs dropping.** Rules 3 and 6 pass | **selected #2** (licence confirmed by Akira, section J) |
| 4 | Titanic | 891 | fails rule 3 (< 5,000 rows) | skipped |
| 5 | EEG | 14,980 | 14 numeric attributes, outliers; passes | **fallback #1** |
| 6 | USCensus | 32,561 | Adult family; fails rule 5 | skipped (Q4) |
| 7 | Restaurant | (unverified) | next in order after USCensus | **fallback #2 candidate**, to be checked against rules 1-6 if reached |

Consistency check after the changes: rule 6 leaves Marketing and Airbnb eligible (column types now verified from the files), so the selection is unchanged and Citation is the only dataset skipped by rule 6. Removing USCensus means the fallback chain is EEG, then the next passing dataset in order (Restaurant onward); no entry depends on USCensus.

Airbnb's licence was confirmed by Akira (section J), so no swap is needed. Had it been rejected, the fallback would be EEG, then the next passing dataset in order. Swaps are logged; a dataset is never replaced after its first run (C4).

**C4. No dataset is added, dropped or swapped after the first run on any dataset.** A dataset that errors out for engineering reasons (parse failure) is logged as "not evaluated" with the reason; it is not replaced.

## D. Ground truth on real data (decided)

- **Ground truth = the published cleaned version.** For CleanML the benchmark ships several cleaned files per error type (multiple cleaning algorithms). **Error cells for an error type = the union of the differing cells over all CleanML cleaned files for that error type** (Q1 resolved); the expected-outcome file lists the files used.
- **Hit** = a commit on a column that contains error cells of type T, with the matching op class: missing values -> fill_* or drop_rows; outliers -> clip_outliers; inconsistency -> normalize_categories. **Miss** = the diff shows a menu-reachable defect and nothing commits for it. **Correct rollback** = no commit and no menu-reachable diff.
- **Unexplained commit** = a commit on a column with no diff. Reported separately; not a hit, not a failure by itself.
- **Wrong-op commit** (op type does not match the diff error type on that column) = failure.
- Expectations are qualitative only (commit / no commit, per column), derived from the diff, not from scores, and written in the expected-outcome file (section K).
- **Positive label (the class scored by F1 and used as the Brier target), stated per dataset before any run:**
  - **Marketing: `Income = 0`.** CleanML's README defines the task as predicting annual household income `<= 4` (bracket codes 1-9; 1-4 = below $25k). Checked row by row against `raw/orgin.csv`: original brackets 1-4 (4,000 rows) are exactly `Income = 0` in `raw.csv`; brackets 5-9 (4,993 rows) are `Income = 1`. The positive class is the low-income class, which is also the minority class (the TaskSpec default would give the same answer).
  - **Airbnb: `Rating = Y`.** CleanML states the task as "predict rating = 5 or not"; `Y` is the file's coding for rating = 5 (22,437 Y vs 10,708 N). The coding is inferred from the PDF wording and the Y/N column, not from a documented codebook. **Akira to confirm.** `Y` is the majority class, so it differs from the TaskSpec minority default and must be passed explicitly (`--positive Y`).
  - The Brier gate is symmetric in this choice; F1 (reported beside every decision) is not.
  - Runner output, the audit meta and the Explain label print "(defaulted)" next to the positive label whenever it was not given explicitly; in the registered runs it is always explicit.
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
| Marketing | https://sites.google.com/site/anhaidgroup/useful-stuff/data (per CleanML refs); originally Impact Resources, Inc., Columbus, OH (1987) | No licence stated. **Confirmed by Akira (2026-11-01): academic use only, no redistribution, no per-ethnicity findings.** | demographic survey records; no identifier column in the file (checked); `Ethnic` is a sensitive attribute, kept as a feature, never reported per group | **Confirmed by Akira** |
| Airbnb | CleanML-authored, scraped from Airbnb.com plus city-data.com attributes; "We will release this dataset in the code repository" (`DatasetDescriptions.pdf`) | CC BY (Inside Airbnb); **confirmed by Akira (2026-11-01)**; credit Inside Airbnb in docs | listing-level data; latitude/longitude and zipcode are present and kept as features; no host name or host ID column in the file (checked; would be dropped if present) | **Confirmed by Akira** |
| EEG (fallback #1) | https://archive.ics.uci.edu/dataset/264/eeg+eye+state | CC BY 4.0 (stated on the UCI page) | UCI page has no PII statement; EEG channel recordings | Akira to confirm |
| CleanML repo (code, cleaned files) | https://github.com/chu-data-lab/CleanML | GitHub API `license` = null (none declared) | n/a | **Still open:** terms for using the data zip (Dropbox `CleanML-datasets-2020.zip`, per the README). Fetched by `tools/fetch_real_data.py` (prints URL and sha256; archive sha256 `d640bdb0fd6aa9420fa61852b38a78aa05ae7a886341750be38b1cb5aa6cb053`); data lives in gitignored `Dataset/real/` and is never committed |

## K. Procedure: expected-outcome file, signing, P4 dependency

1. After datasets are confirmed and before any run, `Documents/EXPECTED_OUTCOMES_real_data.md` is written from the dirty-vs-clean diff only (per dataset: reference cleaned file, columns and error types in the diff, expected commit / no commit per column, split seed). It uses no pilot or eval scores.
2. Akira reviews and signs it (signature line left blank; Claude does not sign).
3. The file is committed. Its git commit hash and SHA-256 are recorded in the new section 12 row. No run may start before this commit exists.
4. This amendment cites the TaskSpec release tag `v2-p4` (git tag on commit 02f63d3, merge of phase/4-taskspec into main; evaluator v1.1 included). It is signed only after P4 is tagged, and TaskSpec is then frozen for this study.

## L. Open questions (status after Akira's answers, 2026-11-01)

- **Q-new-1 (resolved):** error cells = union of all CleanML cleaned files for that error type; hit = commit on such a column with the matching op class (missing -> fill_*/drop_rows, outliers -> clip_outliers, inconsistency -> normalize_categories). Applied in section D.
- **Q-new-2 (resolved):** rule 6 added, "at least 3 non-text feature columns", disclosed as added after viewing the dataset list and before any run. Applied in C1.
- **Q-new-3 (resolved):** Airbnb kept; Inside Airbnb licence (CC BY) confirmed by Akira 2026-11-01; credit Inside Airbnb in docs.
- **Q-new-4 (resolved):** USCensus excluded (Adult family). Applied in C1 rule 5 and the C2 table.
- **Q-new-5 (resolved):** Marketing: no licence stated; academic use only, no redistribution, no per-ethnicity findings (confirmed by Akira 2026-11-01).
- **Q-new-6 (resolved):** repo order in `schema/dataset.py` accepted as the key; the paper's Table 3 order is unverified and not used.

Still open for Akira before signing: (1) licence/terms for the CleanML data zip (section J); (2) confirm the Airbnb positive label `Rating = Y` (section D); (3) choose the split seed before any run (section F); (4) review and sign `EXPECTED_OUTCOMES_real_data.md` once written (section K). Resolved this round: evaluator v1.1 and the continuous-NaN expectation (section B), rule-6 column types (section C2), Marketing positive label (section D), licences (section J).

Resolved by earlier decisions (2026-11-01): N = 2 with next-in-order fallback; ground truth = published cleaned version; 20/80 split with pilot as pipeline check only; per-run Bonferroni primary, across-dataset secondary; seeds 401-403 both planners; LR only; Adult beyond `?` closed; descriptive k/n with wrong-op = failure; signing procedure and P4 dependency.
