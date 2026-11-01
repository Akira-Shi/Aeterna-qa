# RESULTS_REAL - pre-registered real-data evaluation (CleanML Marketing and Airbnb)

Real (not injected) data with natural defects. Separate from the synthetic C1-C5 study in `RESULTS.md`; never pooled with it. LR + Brier gate only (evaluator v1.1). Positive labels: Marketing `Income = 0`, Airbnb `Rating = Y`. Expectations come from CleanML-derived dirty-vs-clean diffs (signed `EXPECTED_OUTCOMES_real_data.md`), not from the real-world ground truth.

## 1. Headline

- **No run committed anything**: 12 of 12 eval runs (Marketing and Airbnb, rule and Groq, seeds 401-403). Wrong-op commits: **0** (the failure condition did not occur). Unexplained commits: **0**.
- H2 (sensitivity, positives): Marketing **0/9** hit in every run; Airbnb **0/55** hit in every run.
- H1 (safety, negatives): Marketing **17/17** correct no-commit in every run; Airbnb **23/23**. Positives and negatives are separate k/n, never pooled.
- Every miss is labelled by pipeline stage (section 4). Airbnb misses are mostly detector-miss and planner-miss; gate-reject is small (Marketing 5, Airbnb 4 per rule run).
- 5 of 6 Groq-planner runs ended early on a planner or API error (section 6); reported as they happened, not re-run to change that.

## 2. What was run

| Item | Value |
|---|---|
| Code state when the runs started | HEAD `a24c16c9cb82695a3807a7e59ca8be9e47fda924` on main (signing commit `8136971`; section 12 row commit `1e68bc6`; frozen_check baseline commit `1e68bc6`, manifest committed in `a24c16c`) |
| TaskSpec release | tag `v2-p4` = commit `02f63d3e9d58d215c806efbf3f576b3c38da42bb` |
| Expected outcomes | blob `a40c7790b19d1cc45a0e1f29d16e1ce431e13fb3`; sha256 of `git show` bytes `65eab5608c78949466b2d8307e82c82c45026cf7d0746972ef24050f901fab55` |
| Amendment | blob `4dc26b58ad68d49194355b41d4fdba710f1bae1b` |
| Data (sha256 verified before every load) | Marketing `raw/raw.csv` `6a05ac3f7579d07c9731741f53012534de72a9b93ebf482e709d5c1da6e8e1a3`; Airbnb `raw/raw.csv` `e5e37131e92cbc4edeeaecaf14c2acdc404994e8d1e725b8ab7c65fe214b504d` |
| Split | 20/80 pilot/eval, stratified on the target, assigned in groups of identical feature vectors (same construction as `study.base_and_split`), split seed 20261101. Marketing 8,993 rows: pilot 1,772 / eval 7,221. Airbnb 33,145 rows: pilot 6,612 / eval 26,533. No complete-case filter (the NaN cells are the error cells). No host name or host ID column exists in the Airbnb file, so nothing was dropped. |
| Pilot | One rule-planner pipeline-check run per dataset (seed 401); both committed nothing. Used for nothing else; no expectation or setting derived from it. |
| Registered runs | eval partition; seeds 401, 402, 403; planners rule and Groq (`openai/gpt-oss-20b`, temperature 0.2); LR only; 12 eval runs in total. |
| Labels | audit `scenario` = `real_marketing` / `real_airbnb`; file names `real_<dataset>_<planner>_<seed>_<partition>_*`; label text "REAL DATA ... natural defects, not injected". |
| Drivers | `tools/run_real_study.py` (calls the unchanged pipeline), `tools/score_real_study.py` (scoring, offer reconstruction), `tools/make_results_real_md.py` (this file). No pipeline, detector, op, menu, gate or evaluator change. |
| Audit logs | `Documents/real_results/audit/` (copies of the gitignored `aeterna_qa/logs/study_real/` JSONs); derived scores `Documents/real_results/real_results.json`. |

Seeds. The pipeline has no injection and its folds and model are fixed by `config.RANDOM_STATE`, so the seed only labels a replicate. The rule planner is deterministic: its three seeds are identical by construction. Only the Groq planner (sampling) can differ between seeds. This was noticed when the runs were set up, before any result.

## 3. k/n per dataset, per planner, per seed

H2 = positives (expected commit) hit, k/n. H1 = negatives (expected no commit) with no commit, k/n. Misses D / P / G / U = detector-miss / planner-miss / gate-reject / unclassified (error) among the positives that did not commit. Evals = candidate evaluations run (max 16).

| Dataset | Planner | Seed | H2 hit | H1 correct | Misses D / P / G / U | Commits | Evals | Ended |
|---|---|---|---|---|---|---|---|---|
| Marketing | rule | 401 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Marketing | rule | 402 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Marketing | rule | 403 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Marketing | groq | 401 | 0/9 | 17/17 | 0 / 7 / 2 / 0 | none | 5 | planner error: invalid pair |
| Marketing | groq | 402 | 0/9 | 17/17 | 0 / 7 / 2 / 0 | none | 5 | planner error: invalid pair |
| Marketing | groq | 403 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Airbnb | rule | 401 | 0/55 | 23/23 | 28 / 23 / 4 / 0 | none | 16 | 16 iterations |
| Airbnb | rule | 402 | 0/55 | 23/23 | 28 / 23 / 4 / 0 | none | 16 | 16 iterations |
| Airbnb | rule | 403 | 0/55 | 23/23 | 28 / 23 / 4 / 0 | none | 16 | 16 iterations |
| Airbnb | groq | 401 | 0/55 | 23/23 | 28 / 25 / 2 / 0 | none | 11 | API 400 JSON validate |
| Airbnb | groq | 402 | 0/55 | 23/23 | 28 / 26 / 1 / 0 | none | 8 | API 400 JSON validate |
| Airbnb | groq | 403 | 0/55 | 23/23 | 28 / 26 / 1 / 0 | none | 3 | API 429 daily tokens (TPD) |

Nothing committed, so there are no committed-op deltas. Descriptive: largest evaluated paired delta per run with its Bonferroni bar (a commit needs delta > 0 and delta >= bar):

| Dataset | Planner | Seed | Largest delta (bar) | Evaluated pairs with delta > 0 |
|---|---|---|---|---|
| Marketing | rule | 401 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Marketing | rule | 402 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Marketing | rule | 403 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Marketing | groq | 401 | +0.0000 (bar 0.0004) on Live: fill_mode | 0 of 5 |
| Marketing | groq | 402 | +0.0000 (bar 0.0004) on Live: fill_mode | 0 of 5 |
| Marketing | groq | 403 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Airbnb | rule | 401 | +0.0000 (bar 0.0004) on LocationName: normalize_categories | 0 of 16 |
| Airbnb | rule | 402 | +0.0000 (bar 0.0004) on LocationName: normalize_categories | 0 of 16 |
| Airbnb | rule | 403 | +0.0000 (bar 0.0004) on LocationName: normalize_categories | 0 of 16 |
| Airbnb | groq | 401 | +0.0000 (bar 0.0004) on *: dedupe_rows | 0 of 11 |
| Airbnb | groq | 402 | +0.0000 (bar 0.0004) on *: dedupe_rows | 0 of 8 |
| Airbnb | groq | 403 | +0.0000 (bar 0.0004) on *: dedupe_rows | 0 of 3 |

Baselines (neg-Brier, fixed-fold LR): Marketing -0.1556; Airbnb -0.2041, unchanged in every run.

## 4. Failure-stage counts for expected-commit rows that did not commit

Labels only (amendment section E); scoring is unchanged. Unit: one row per (dataset, column, error type). Counts per run:

- **Marketing** (9 expected-commit rows, 0 hit):
  - rule: 401: 0 detector-miss, 4 planner-miss, 5 gate-reject; 402: 0 detector-miss, 4 planner-miss, 5 gate-reject; 403: 0 detector-miss, 4 planner-miss, 5 gate-reject
  - groq: 401: 0 detector-miss, 7 planner-miss, 2 gate-reject; 402: 0 detector-miss, 7 planner-miss, 2 gate-reject; 403: 0 detector-miss, 4 planner-miss, 5 gate-reject
- **Airbnb** (55 expected-commit rows, 0 hit):
  - rule: 401: 28 detector-miss, 23 planner-miss, 4 gate-reject; 402: 28 detector-miss, 23 planner-miss, 4 gate-reject; 403: 28 detector-miss, 23 planner-miss, 4 gate-reject
  - groq: 401: 28 detector-miss, 25 planner-miss, 2 gate-reject; 402: 28 detector-miss, 26 planner-miss, 1 gate-reject; 403: 28 detector-miss, 26 planner-miss, 1 gate-reject

**Sanity check (reconstruction): PASSED.** Offers were reconstructed after the runs by re-running `detect()` and the `remaining_options` logic, read-only, on the exact input of every logged iteration (the eval partition materialised with that iteration's committed ops; nothing committed, so it equals the eval partition), under the same TaskSpec settings, with no pipeline change. Every (column, op) the audit log shows as evaluated appeared in that iteration's reconstructed offers, in all 12 runs, so the three-way split is reported. Notes: (1) a row is planner-miss if a reachable op was offered at any logged iteration but never evaluated; (2) for a Groq run that ended early on a planner or API error, an offered op that was never reached is counted as planner-miss, because the planner stage did not select it (the end reason is in section 3); (3) the `unclassified (error)` rule (the row's only entries are error entries) applied to no row.

## 5. Other outcomes

| Item | Result |
|---|---|
| Unexplained commits (commit on a column with no error cells; listed separately) | none |
| Wrong-op commits (failure condition) | **0** |
| Committed ops | none in any run |
| Evaluation counts | rule: 16 per run in both datasets (budget exhausted). Groq: Marketing 5, 5, 16; Airbnb 11, 8, 3 (early ends, section 6). Aborted first attempt of Airbnb Groq 401: 0. |
| Primary statistic | per-run Bonferroni (alpha / 16 look-backs = `MAX_ITERATIONS`), unchanged |
| Secondary (across-dataset, information only) | family = 16 look-backs x 12 eval runs = 192; it can only flag commits, and there are none |
| H3 (no harm) | vacuous: 0 committed ops (details below) |

**H3.** Definition (amendment section E): every committed op has a final gate delta >= 0 on the held-out evaluation partition, and no collateral damage measurable against ground truth where G1 applies; a commit with negative delta on a partition not used for the commit decision is a failure of the gate. Evaluated as written: there are 0 committed ops, so the first clause is vacuously satisfied (0 of 0 violate) and no gate failure occurred. Not computable without making a choice: (a) the "partition not used for the commit decision" is not named (the pilot is declared a pipeline check only, and the eval partition is where the commit decision is made), so no out-of-decision delta was computed; (b) "ground truth where G1 applies" is not defined in the amendment text, and there is no committed repair to compare in any case. Nothing was chosen for those two parts.

## 6. Errors and incomplete runs (verbatim)

- **Marketing Groq 401 and 402**, iteration 6: `Planner chose (Person, fill_mode), which is not in remaining_options: [...]`. The strict JSON schema constrains column and operation independently, so Groq proposed a pair that is not on the menu (Person/fill_mode was already evaluated at iteration 5). The unchanged pipeline treats a planner exception as the end of the run. 5 evaluations each.
- **Marketing Groq 403**: completed 16 evaluations, no error.
- **Airbnb Groq 401**, iteration 12: `Error code: 400 - {'error': {'message': "Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details.", 'type': 'invalid_request_error', 'code': 'json_validate_failed', 'failed_generation': ''}}` (11 evaluations before it).
- **Airbnb Groq 402**, iteration 9: `Error code: 400 - {'error': {'message': "Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details.", 'type': 'invalid_request_error', 'code': 'json_validate_failed', 'failed_generation': ''}}` (8 evaluations before it).
- **Airbnb Groq 403**, iteration 4: `Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01m3nh5yj0e3t989zj64nrgv7b` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 195832, Requested 5703. Please try again in 11m3.12s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}` (3 evaluations before it).
- **Aborted first attempt, Airbnb Groq 401** (kept as `Documents/real_results/audit/ABORTED_attempt1_...json`): `Error code: 429 ... Rate limit reached for model openai/gpt-oss-20b ... on tokens per minute (TPM): Limit 8000, Used 7585, Requested 4861`, at iteration 1, 0 evaluations, no result. Cause: I launched the four dataset-planner jobs in parallel and the two Groq jobs shared the organisation's per-minute token limit; the existing client retry did not wait long enough. I stopped the two parallel Groq processes and ran the Groq jobs one after another instead: Marketing Groq 403 (it had been killed mid-run, so it was started again from the start) and Airbnb Groq 401, 402, 403. That decision was made before any result of these runs was seen. The re-run of Airbnb Groq 401 then ended on the 400 error above. The aborted attempt and the parallel start spent part of the Groq daily token budget and may have contributed to the daily-limit (TPD) error that ended Airbnb Groq 403; that attribution is a judgement, not verified.
- The Explain step was skipped for the two pilot runs (console `UnicodeEncodeError`); the audit logs are unaffected. Eval runs used `PYTHONIOENCODING=utf-8` and have Explain reports in `aeterna_qa/logs/study_real/`. Explain LLM notes were switched off for these runs (`EXPLAIN_USE_LLM = False`, to avoid extra Groq calls); the verdicts are deterministic.
- Cosmetic, from existing code: the console baseline line prints "exploratory data" because the TaskSpec path passes `task_meta`; the audit `scenario` and label are the real-data ones.

## 7. Planner comparison (exploratory, efficiency only)

Rule and Groq gave the same final outcome (nothing committed) in every run. The rule planner used its full 16-evaluation budget every time; Groq runs used fewer evaluations only because most ended on errors, so no efficiency claim is made. Which rows were reached differs by planner and, for Groq, by seed (section 8). No accuracy claim.

## 8. Full per-row table

Codes: **H** hit; **ok** correct no-commit (expected no commit, none occurred); **X** commit on an expected-no-commit row; misses: **D** detector-miss, **P** planner-miss, **G** gate-reject, **U** unclassified (error), **N** not separable. Columns: rule seeds 401/402/403, then Groq seeds 401/402/403. "Reachable ops" are those of the signed file; any one committing is a hit.

| Dataset | Column | Error type | Reachable ops | Expected | Rule 401 | 402 | 403 | Groq 401 | 402 | 403 |
|---|---|---|---|---|---|---|---|---|---|---|
| Marketing | Age | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Dual | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Education | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Ethnic | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Hometype | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Householder | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Language | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Live | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Marital | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Occupation | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Person | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Person under 18 | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Sex | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Age | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Dual | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Education | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P | P | P |
| Marketing | Ethnic | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P | P | P |
| Marketing | Hometype | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | P | P | G |
| Marketing | Householder | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | P | P | G |
| Marketing | Language | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | P | P | G |
| Marketing | Live | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G | G | G |
| Marketing | Marital | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P | P | P |
| Marketing | Occupation | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P | P | P |
| Marketing | Person | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G | G | G |
| Marketing | Person under 18 | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Marketing | Sex | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | LocationName | inconsistency | normalize_categories | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Abnb Price (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average NumReviews (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Number of Bathrooms (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Number of Bedrooms (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Number of Beds (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Number of Guests (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Rating (by zipcode) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Bathrooms | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | Bedrooms | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | Beds | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | Count of Abnb | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Density of Abnb (%) | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | LocationName | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P | P | P |
| Airbnb | NumGuests | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | NumReviews | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | Number of Homes | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | Price | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | cost_living_index (US avg. = 100) | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | land_area (sq.mi.) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | latitude | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | longitude | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | median asking price for vacant for-sale home/condo | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | median gross rent | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | median house value | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | median houshold income | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | median monthly owner costs (no mortgage) | missing | drop_rows | commit | G | G | G | P | P | P |
| Airbnb | median monthly owner costs (with mortgage) | missing | drop_rows | commit | G | G | G | P | P | P |
| Airbnb | median taxes (no mortgage) | missing | drop_rows | commit | G | G | G | P | P | P |
| Airbnb | median taxes (with mortgage | missing | drop_rows | commit | G | G | G | P | P | P |
| Airbnb | number of females | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | number of males | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | pop2000 | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | pop2010 | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | pop2016 | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | pop_density (people per mile) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | prop taxes paid 2016 | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | unemployment (%) | missing | drop_rows | commit | P | P | P | P | P | P |
| Airbnb | water_area (sq.mi.) | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | zipcode | missing | drop_rows | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | Average Abnb Price (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Average NumReviews (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Average Number of Bathrooms (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Average Number of Bedrooms (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Average Number of Beds (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Average Number of Guests (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Average Rating (by zipcode) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Bathrooms | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Bedrooms | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Beds | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Count of Abnb | outliers | clip_outliers | commit | P | P | P | G | G | G |
| Airbnb | Density of Abnb (%) | outliers | clip_outliers | commit | P | P | P | G | P | P |
| Airbnb | NumGuests | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | NumReviews | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Number of Homes | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | Price | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | cost_living_index (US avg. = 100) | outliers | clip_outliers | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | land_area (sq.mi.) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | latitude | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | longitude | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | median asking price for vacant for-sale home/condo | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | median gross rent | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | median house value | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | median houshold income | outliers | clip_outliers | commit | P | P | P | P | P | P |
| Airbnb | median monthly owner costs (no mortgage) | outliers | clip_outliers | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | median monthly owner costs (with mortgage) | outliers | clip_outliers | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | median taxes (no mortgage) | outliers | clip_outliers | commit | P | P | P | P | P | P |
| Airbnb | median taxes (with mortgage | outliers | clip_outliers | no commit | ok | ok | ok | ok | ok | ok |
| Airbnb | number of females | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | number of males | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | pop2000 | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | pop2010 | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | pop2016 | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | pop_density (people per mile) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | prop taxes paid 2016 | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | unemployment (%) | outliers | clip_outliers | commit | D | D | D | D | D | D |
| Airbnb | water_area (sq.mi.) | outliers | clip_outliers | commit | P | P | P | P | P | P |
| Airbnb | zipcode | outliers | clip_outliers | no commit | ok | ok | ok | ok | ok | ok |

## 9. Exploratory-run disclosure

On 2026-11-01, before the amendment was signed, the unchanged pipeline was run once on each full dataset for pipeline acceptance (P4): Marketing (`--positive 0`, rule planner) and Airbnb (`--positive Y`), scenario label `exploratory`. They are not study results and no expectation was derived from them. Outcomes as recorded then: Marketing, 16 of 16 candidate evaluations rolled back, nothing committed; Airbnb, no commits, `fill_median` / `fill_mean` delta +0.0000. The registered runs here are separate runs on the eval partition.

## 10. Honest limits

- Expectations are derived from CleanML dirty-vs-clean diffs (and the dirty file's NaN cells), not from the real-world ground truth. "Expected commit" means CleanML shows error cells there, not that repairing them helps a downstream LR.
- Scoring is per run under per-run Bonferroni (alpha / 16). With LR + Brier on these tables no repair cleared the bar, so H2 is 0 for both datasets. That is a statement about the gate and detectors on these tables, not evidence that the defects are harmless or that the gate is right.
- Many Airbnb misses are detector-misses and planner-misses: the detectors never offered some reachable ops, and a 16-iteration budget cannot reach 55 expected-commit rows. Both are properties of the unchanged agent.
- Groq runs ended early on planner or API errors in 5 of 6 runs, so the Groq vs rule comparison is exploratory and incomplete.
- `Ethnic` in Marketing is a sensitive attribute; no per-group result is reported. The Airbnb file has 33,145 rows versus 42,492 in the CleanML description; the file was used as is.
- Small N (2 datasets), one split seed, no family-wide correction in the commit rule.

## 11. Credit and licence

- Marketing: CleanML benchmark (Li et al., https://arxiv.org/abs/1904.09483; https://github.com/chu-data-lab/CleanML); data originally Impact Resources, Inc. (Columbus, OH, 1987). No licence stated: academic use only, not redistributed, no per-ethnicity findings.
- Airbnb data: Inside Airbnb (CC BY), via CleanML. The data files are in the gitignored `Dataset/real/` and are not committed.
