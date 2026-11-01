# RESULTS_REAL - pre-registered real-data evaluation (CleanML Marketing and Airbnb)

Real (not injected) data with natural defects. Separate from the synthetic C1-C5 study in `RESULTS.md`; never pooled with it. LR + Brier gate only (evaluator v1.1). Positive labels: Marketing `Income = 0`, Airbnb `Rating = Y`. Expectations come from CleanML-derived dirty-vs-clean diffs (signed `EXPECTED_OUTCOMES_real_data.md`), not from the real-world ground truth.

Status of this file (2026-11-01): re-rendered after Groq hit API limits during P5. The rule-planner runs are the primary result and are reported first. Every Groq run with an API error is marked invalid (infrastructure failure) and carries no hit, miss or stage numbers. Two Groq runs (Marketing 401, 402) ended on a planner-validation error that is not an API error; per Akira (2026-11-01) they are valid runs with outcome "terminated: planner violated menu constraint (re-proposed an evaluated pair)", reported under their own heading (section 6b) as a planner-reliability finding, and are not rerun. No Groq-vs-rule comparison is made until the three invalid Airbnb Groq runs are rerun under the rerun rule. No rerun has been done under the rerun rule (section 8).

## 1. Headline

- **Primary result, rule planner (6 eval runs: Marketing and Airbnb, seeds 401-403; the three seeds are identical by construction)**: no run committed anything. Wrong-op commits: 0. Unexplained commits: 0.
- H2 (positives, expected commit), rule planner: Marketing **0/9** hit; Airbnb **0/55** hit.
- H1 (negatives, expected no commit), rule planner: Marketing **17/17** correct no-commit; Airbnb **23/23**. Positives and negatives are separate k/n, never pooled.
- Miss stages, rule planner (detector / planner / gate): Marketing 0 / 4 / 5; Airbnb 28 / 23 / 4 (section 4).
- Groq planner (6 runs): 1 completed valid, 2 valid but terminated early (planner violated the menu constraint; section 6b), 3 invalid (infrastructure failure: API error; section 6a). Groq-vs-rule comparison waits until the invalid Airbnb Groq runs are rerun under the rerun rule.

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
| Registered runs | eval partition; seeds 401, 402, 403; planners rule and Groq (`openai/gpt-oss-20b`, temperature 0.2); LR only; 12 eval runs in total (6 rule, 6 Groq). |
| Labels | audit `scenario` = `real_marketing` / `real_airbnb`; file names `real_<dataset>_<planner>_<seed>_<partition>_*`; label text "REAL DATA ... natural defects, not injected". |
| Drivers | `tools/run_real_study.py` (calls the unchanged pipeline), `tools/score_real_study.py` (scoring, offer reconstruction), `tools/make_results_real_md.py` (this file). No pipeline, detector, op, menu, gate or evaluator change. |
| Audit logs | `Documents/real_results/audit/` (copies of the gitignored `aeterna_qa/logs/study_real/` JSONs); derived scores `Documents/real_results/real_results.json`. |

Seeds. The pipeline has no injection and its folds and model are fixed by `config.RANDOM_STATE`, so the seed only labels a replicate. The rule planner is deterministic: its three seeds are identical by construction (checked: the per-row outcomes of seeds 401, 402, 403 are identical in both datasets). Only the Groq planner (sampling) can differ between seeds. This was noticed when the runs were set up, before any result.

## 3. Rule-planner results (PRIMARY), k/n per dataset and seed

H2 = positives (expected commit) hit, k/n. H1 = negatives (expected no commit) with no commit, k/n. Misses D / P / G / U = detector-miss / planner-miss / gate-reject / unclassified (error) among the positives that did not commit. Evals = candidate evaluations run (max 16). All six rule runs used the full 16-iteration budget with no error.

| Dataset | Planner | Seed | H2 hit | H1 correct | Misses D / P / G / U | Commits | Evals | Ended |
|---|---|---|---|---|---|---|---|---|
| Marketing | rule | 401 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Marketing | rule | 402 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Marketing | rule | 403 | 0/9 | 17/17 | 0 / 4 / 5 / 0 | none | 16 | 16 iterations |
| Airbnb | rule | 401 | 0/55 | 23/23 | 28 / 23 / 4 / 0 | none | 16 | 16 iterations |
| Airbnb | rule | 402 | 0/55 | 23/23 | 28 / 23 / 4 / 0 | none | 16 | 16 iterations |
| Airbnb | rule | 403 | 0/55 | 23/23 | 28 / 23 / 4 / 0 | none | 16 | 16 iterations |

Nothing committed, so there are no committed-op deltas. Descriptive: largest evaluated paired delta per rule run with its Bonferroni bar (a commit needs delta > 0 and delta >= bar):

| Dataset | Planner | Seed | Largest delta (bar) | Evaluated pairs with delta > 0 |
|---|---|---|---|---|
| Marketing | rule | 401 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Marketing | rule | 402 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Marketing | rule | 403 | +0.0001 (bar 0.0002) on Hometype: fill_mode | 3 of 16 |
| Airbnb | rule | 401 | +0.0000 (bar 0.0004) on LocationName: normalize_categories | 0 of 16 |
| Airbnb | rule | 402 | +0.0000 (bar 0.0004) on LocationName: normalize_categories | 0 of 16 |
| Airbnb | rule | 403 | +0.0000 (bar 0.0004) on LocationName: normalize_categories | 0 of 16 |

Baselines (neg-Brier, fixed-fold LR): Marketing -0.1556; Airbnb -0.2041, unchanged in every run.

## 4. Failure-stage counts for expected-commit rows that did not commit (rule runs)

Labels only (amendment section E); scoring is unchanged. Unit: one row per (dataset, column, error type). Counts per rule run:

- **Marketing** (9 expected-commit rows, 0 hit), rule: 401: 0 detector-miss, 4 planner-miss, 5 gate-reject; 402: 0 detector-miss, 4 planner-miss, 5 gate-reject; 403: 0 detector-miss, 4 planner-miss, 5 gate-reject
- **Airbnb** (55 expected-commit rows, 0 hit), rule: 401: 28 detector-miss, 23 planner-miss, 4 gate-reject; 402: 28 detector-miss, 23 planner-miss, 4 gate-reject; 403: 28 detector-miss, 23 planner-miss, 4 gate-reject

**Sanity check (reconstruction): PASSED.** Offers were reconstructed after the runs by re-running `detect()` and the `remaining_options` logic, read-only, on the exact input of every logged iteration (the eval partition materialised with that iteration's committed ops; nothing committed, so it equals the eval partition), under the same TaskSpec settings, with no pipeline change. Every (column, op) the audit log shows as evaluated appeared in that iteration's reconstructed offers, in all 12 runs. A row is planner-miss if a reachable op was offered at any logged iteration but never evaluated; the `unclassified (error)` rule applied to no row. No stage counts are reported for invalid or terminated Groq runs.

## 5. Other outcomes (rule runs; valid Groq runs listed separately)

| Item | Result |
|---|---|
| Unexplained commits (commit on a column with no error cells; listed separately) | rule: none. Valid Groq runs (Marketing 403 only): none |
| Wrong-op commits (failure condition) | rule: **0**. Valid Groq runs (Marketing 403 only): 0 |
| Committed ops | rule: none in any run. Valid Groq run: none |
| Evaluation counts | rule: 16 per run in both datasets (budget exhausted) |
| Primary statistic | per-run Bonferroni (alpha / 16 look-backs = `MAX_ITERATIONS`), unchanged |
| Secondary (across-dataset, information only) | family = 16 look-backs x 12 eval runs = 192; it can only flag commits, and there are none |
| H3 (no harm), rule runs | vacuous: 0 committed ops (details below) |

**H3 (rule runs only; no Groq data is used here).** Definition (amendment section E): every committed op has a final gate delta >= 0 on the held-out evaluation partition, and no collateral damage measurable against ground truth where G1 applies; a commit with negative delta on a partition not used for the commit decision is a failure of the gate. Evaluated as written for the six rule runs: there are 0 committed ops, so the first clause is vacuously satisfied (0 of 0 violate) and no gate failure occurred. Not computable without making a choice: (a) the "partition not used for the commit decision" is not named (the pilot is declared a pipeline check only, and the eval partition is where the commit decision is made), so no out-of-decision delta was computed; (b) "ground truth where G1 applies" is not defined in the amendment text, and there is no committed repair to compare in any case. Nothing was chosen for those two parts. (The earlier version of this file computed H3 from zero committed ops across all runs; it used no Groq-specific data, so the result is unchanged.)

## 6. Groq-planner runs: validity (classified strictly from the audit logs)

Rule used: a Groq run with any API error (HTTP status error from the Groq client: 429, 400 or other) is `invalid: infrastructure failure`; it gets no hit/miss/stage/delta numbers. A planner exception that is not an API error is a valid run (Akira, 2026-11-01) and is listed under its own heading as a planner-reliability finding. Error text is the audit-log `error` field of the last iteration, verbatim.

| Dataset | Seed | Status | Evaluations done before the error | Iteration of error | Error kind |
|---|---|---|---|---|---|
| Marketing | 401 | **valid - terminated: planner violated menu constraint (re-proposed an evaluated pair)** | 5 | 6 | planner raised ValueError (pair not in remaining_options) |
| Marketing | 402 | **valid - terminated: planner violated menu constraint (re-proposed an evaluated pair)** | 5 | 6 | planner raised ValueError (pair not in remaining_options) |
| Marketing | 403 | valid (16 iterations, no `error` entry in the audit log) | 16 | - | none |
| Airbnb | 401 | **invalid: infrastructure failure** | 11 | 12 | API 400 json_validate_failed |
| Airbnb | 402 | **invalid: infrastructure failure** | 8 | 9 | API 400 json_validate_failed |
| Airbnb | 403 | **invalid: infrastructure failure** | 3 | 4 | API 429 rate_limit_exceeded |

### 6a. Invalid: infrastructure failure (API error). Reported as `invalid` only.

- **Airbnb Groq 401** (`real_airbnb_groq_401_eval_20261101T134654Z.json`): iteration 12, 11 evaluations completed before the error. Verbatim: `Error code: 400 - {'error': {'message': "Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details.", 'type': 'invalid_request_error', 'code': 'json_validate_failed', 'failed_generation': ''}}`
- **Airbnb Groq 402** (`real_airbnb_groq_402_eval_20261101T135206Z.json`): iteration 9, 8 evaluations completed before the error. Verbatim: `Error code: 400 - {'error': {'message': "Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details.", 'type': 'invalid_request_error', 'code': 'json_validate_failed', 'failed_generation': ''}}`
- **Airbnb Groq 403** (`real_airbnb_groq_403_eval_20261101T135401Z.json`): iteration 4, 3 evaluations completed before the error. Verbatim: `Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01m3nh5yj0e3t989zj64nrgv7b` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 195832, Requested 5703. Please try again in 11m3.12s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **Aborted first attempt, Airbnb Groq 401** (`ABORTED_attempt1_real_airbnb_groq_401_eval_20261101T133459Z.json`): iteration 1, 0 evaluations. Verbatim: `Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01m3nh5yj0e3t989zj64nrgv7b` service tier `on_demand` on tokens per minute (TPM): Limit 8000, Used 7585, Requested 4861. Please try again in 33.345s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`

### 6b. Valid, terminated early: planner violated menu constraint (re-proposed an evaluated pair). Planner-reliability finding.

Akira's decision (2026-11-01): these two runs are VALID, not infrastructure failures, and are not rerun. Outcome label: "terminated: planner violated menu constraint (re-proposed an evaluated pair)". The Groq API call succeeded; the model returned a (column, operation) pair that had already been evaluated and so was not in `remaining_options`. The planner's menu check (`planner.py`, `plan()`) rejected it with a `ValueError`, which prevented any invalid op from executing; the unchanged pipeline treats a planner exception as the end of the run. Nothing committed in either run. This is a reliability finding about the Groq planner, reported here as observed, not as a hit or miss.

- **Marketing Groq 401** (`real_marketing_groq_401_eval_20261101T133354Z.json`): ended at iteration 6 after 5 evaluations; no commit. Verbatim: `Planner chose (Person, fill_mode), which is not in remaining_options: [('Person', 'fill_unknown'), ('Person', 'drop_rows'), ('Language', 'fill_mode'), ('Languag [...]`  (the message continues with the full remaining-options list).
- **Marketing Groq 402** (`real_marketing_groq_402_eval_20261101T133528Z.json`): ended at iteration 6 after 5 evaluations; no commit. Verbatim: `Planner chose (Person, fill_mode), which is not in remaining_options: [('Person', 'fill_unknown'), ('Person', 'drop_rows'), ('Language', 'fill_mode'), ('Languag [...]`  (the message continues with the full remaining-options list).

### 6c. Valid Groq run

- **Marketing Groq 403** (`real_marketing_groq_403_eval_20261101T133945Z.json`): 16 iterations, every `error` field is `None`, and the driver console output (`_driver_eval_Marketing_groq_403.out`, `real_marketing_groq_403_eval.txt`) contains no error text. H2 0/9, H1 17/17, misses D / P / G / U = 0 / 4 / 5 / 0, commits none, unexplained 0, wrong-op 0. This is a single valid Groq run; no comparison with the rule planner is made.

Limit on this classification. The Groq Python client (`groq` 1.7.0) is created with its defaults (`Groq(api_key=...)` in `planner.py`); the library default is to retry some failed requests (default `DEFAULT_MAX_RETRIES` = 2) without logging them. The audit log records only errors that reached the pipeline, so "no API error in the log" means no error survived the client's own retries; whether the client silently retried inside any run cannot be established from the saved files. This applies to the valid Groq run (Marketing 403) and to the Marketing 401/402 runs.

Other notes from the incident (unchanged facts):

- The Explain step was skipped for the two pilot runs (console `UnicodeEncodeError`); the audit logs are unaffected. Eval runs used `PYTHONIOENCODING=utf-8` and have Explain reports in `aeterna_qa/logs/study_real/`. Explain LLM notes were switched off for these runs (`EXPLAIN_USE_LLM = False`, to avoid extra Groq calls); the verdicts are deterministic.
- Cosmetic, from existing code: the console baseline line prints "exploratory data" because the TaskSpec path passes `task_meta`; the audit `scenario` and label are the real-data ones.

## 7. Reruns done so far (original and rerun side by side; none is preferred)

All reruns so far were decided by the driver operator on 2026-11-01 before any result of the rerun was seen, and were launches of the same command after an interrupted parallel launch. They were made before the rerun rule (section 8) was written, so they are not governed by it. Times are UTC from the audit logs. Sources: audit logs, `aeterna_qa/logs/study_real/_driver_*.out`, `aborted/`, and the old RESULTS_REAL.md section 6 (commit `de141ac`).

| # | Run id | Why rerun | Original outcome | Rerun outcome | Files |
|---|---|---|---|---|---|
| 1 | Airbnb Groq 401 | First launch ran the Marketing and Airbnb Groq jobs in parallel; the Airbnb job hit a per-minute token limit at iteration 1. | Started 13:34:04, ended 13:34:59: iteration 1 failed with `Error code: 429 ... tokens per minute (TPM): Limit 8000, Used 7585, Requested 4861`, 0 evaluations, no result. API error: invalid under Akira's rule. | Started 13:40:28, ended 13:46:54: 11 evaluations, then iteration 12 failed with `Error code: 400 ... json_validate_failed`. API error: invalid under Akira's rule. | Original: `audit/ABORTED_attempt1_real_airbnb_groq_401_eval_20261101T133459Z.json` (also `aeterna_qa/logs/study_real/aborted/*`, `_driver_eval_Airbnb_groq.out`). Rerun: `audit/real_airbnb_groq_401_eval_20261101T134654Z.json`, `_driver_eval_Airbnb_groq_rerun.out`. |
| 2 | Airbnb Groq 402 | Same parallel launch; process was stopped by the operator after the 401 failure. | Started in the first launch (header `=== real_airbnb_groq_402_eval` is the last line of `_driver_eval_Airbnb_groq.out`); no audit JSON, no iteration output. No outcome exists. | Started 13:47:21, ended 13:52:06: 8 evaluations, then iteration 9 failed with `Error code: 400 ... json_validate_failed`. API error: invalid. | Original: only the header line in `_driver_eval_Airbnb_groq.out`. Rerun: `audit/real_airbnb_groq_402_eval_20261101T135206Z.json`. |
| 3 | Marketing Groq 403 | Same parallel launch; process was stopped by the operator while 403 was starting. | Started in the first launch (header `=== real_marketing_groq_403_eval` is the last line of `_driver_eval_Marketing_groq.out`); no audit JSON, no iteration output. No outcome exists. | Started 13:36:14, ended 13:39:45: 16 evaluations, no `error` entry. Valid by the log (see limit in section 6). | Original: only the header line in `_driver_eval_Marketing_groq.out`. Rerun: `audit/real_marketing_groq_403_eval_20261101T133945Z.json`, `_driver_eval_Marketing_groq_403.out`. |

Not a rerun: Airbnb Groq 403 was not started in the first launch (no header line in `_driver_eval_Airbnb_groq.out`); its one execution (13:52:33 to 13:54:01) ended on `Error code: 429 ... tokens per day (TPD): Limit 200000, Used 195832, Requested 5703` after 3 evaluations (invalid, section 6a).

Where the original and the rerun both exist (row 1), both are API-error runs and both are invalid; no choice between them is made. For rows 2 and 3 no original outcome exists to compare.

What is unknowable from the saved files:

- Exactly when and how the first-launch processes in rows 2 and 3 were stopped, and whether they made Groq API calls before being stopped (the console files hold only the header line; no audit JSON was written). Any such calls count towards the Groq token counters and are not recorded.
- Whether the Groq client silently retried requests inside any run (section 6).
- The text-file outputs `real_<...>_eval.txt` carry no timestamp in their name and are overwritten by a rerun of the same run id; the earlier `real_airbnb_groq_401_eval.txt` survives only because it was moved to `aborted/`. The JSON audit logs carry a UTC stamp in the file name and none was overwritten: every (dataset, planner, seed, partition) has exactly one JSON in `aeterna_qa/logs/study_real/` apart from the aborted Airbnb Groq 401 attempt (12 eval and 2 pilot JSONs, plus the aborted one kept in `aborted/`). Reruns that left no JSON and no console file cannot be ruled out, but none is recorded anywhere (driver outputs, the old RESULTS_REAL.md, `Documentation.md`, or the single commit `de141ac`).
- How much of the Groq daily token counter (195,832 of 200,000 at the time of the TPD error) was used by P5 runs versus other Groq use on the same organisation earlier that day (for example the pre-signing exploratory runs); the log does not say.

## 8. Rerun rule (written before any rerun)

Dated 2026-11-01. Written by the operator on Akira's instruction, before any rerun is made. No rerun has been done under this rule yet.

1. Rerun **all** Groq runs that had an API error (every run listed in section 6a, including any run later reclassified as an API-error run by Akira). A Groq run that is **completed and valid is never rerun**.
2. Timing: rerun only after the daily Groq quota has reset (rolling 24 hours; the TPD counter reached 195,832 of 200,000 on 2026-11-01).
3. On a 429, wait the server's retry-after time and retry, at most 5 retries per call; pause between calls to stay under the per-minute limit.
4. A rerun replaces the invalid status only. The original invalid record stays listed in sections 6a and 7; an original is never deleted, overwritten or hidden. The rerun's own result, if valid, is reported as that run's result, with its start and end time.
5. A rerun that again hits an API error is again invalid, is listed, and is subject to this rule after the next quota reset.
6. The two runs in section 6b (Marketing Groq 401, 402) are valid terminated runs (Akira, 2026-11-01) and are not rerun.
7. No change to the pipeline, detectors, ops, menu, gate, prompt, temperature, model or evaluator for a rerun. Seeds and partition are as originally registered.

## 9. Groq-vs-rule comparison

Groq-vs-rule comparison waits until every Groq run is valid.

## 10. Full per-row table

Codes: **H** hit; **ok** correct no-commit (expected no commit, none occurred); **X** commit on an expected-no-commit row; misses: **D** detector-miss, **P** planner-miss, **G** gate-reject, **U** unclassified (error), **N** not separable. Columns: rule seeds 401/402/403, then the valid Groq run (Marketing 403 only; invalid and terminated Groq runs have no per-row entries). "Reachable ops" are those of the signed file; any one committing is a hit.

| Dataset | Column | Error type | Reachable ops | Expected | Rule 401 | 402 | 403 | Groq 403 |
|---|---|---|---|---|---|---|---|---|
| Marketing | Age | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Dual | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Education | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Ethnic | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Hometype | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Householder | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Language | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Live | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Marital | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Occupation | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Person | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Person under 18 | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Sex | inconsistency | normalize_categories | no commit | ok | ok | ok | ok |
| Marketing | Age | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok |
| Marketing | Dual | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok |
| Marketing | Education | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P |
| Marketing | Ethnic | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P |
| Marketing | Hometype | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G |
| Marketing | Householder | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G |
| Marketing | Language | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G |
| Marketing | Live | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G |
| Marketing | Marital | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P |
| Marketing | Occupation | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P | P |
| Marketing | Person | missing | fill_mode, fill_unknown, drop_rows | commit | G | G | G | G |
| Marketing | Person under 18 | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok |
| Marketing | Sex | missing | fill_mode, fill_unknown, drop_rows | no commit | ok | ok | ok | ok |

| Dataset | Column | Error type | Reachable ops | Expected | Rule 401 | 402 | 403 |
|---|---|---|---|---|---|---|---|
| Airbnb | LocationName | inconsistency | normalize_categories | no commit | ok | ok | ok |
| Airbnb | Average Abnb Price (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average NumReviews (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average Number of Bathrooms (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average Number of Bedrooms (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average Number of Beds (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average Number of Guests (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average Rating (by zipcode) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Bathrooms | missing | drop_rows | commit | P | P | P |
| Airbnb | Bedrooms | missing | drop_rows | commit | P | P | P |
| Airbnb | Beds | missing | drop_rows | commit | P | P | P |
| Airbnb | Count of Abnb | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Density of Abnb (%) | missing | drop_rows | commit | P | P | P |
| Airbnb | LocationName | missing | fill_mode, fill_unknown, drop_rows | commit | P | P | P |
| Airbnb | NumGuests | missing | drop_rows | commit | P | P | P |
| Airbnb | NumReviews | missing | drop_rows | commit | P | P | P |
| Airbnb | Number of Homes | missing | drop_rows | commit | P | P | P |
| Airbnb | Price | missing | drop_rows | commit | P | P | P |
| Airbnb | cost_living_index (US avg. = 100) | missing | drop_rows | commit | P | P | P |
| Airbnb | land_area (sq.mi.) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | latitude | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | longitude | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | median asking price for vacant for-sale home/condo | missing | drop_rows | commit | P | P | P |
| Airbnb | median gross rent | missing | drop_rows | commit | P | P | P |
| Airbnb | median house value | missing | drop_rows | commit | P | P | P |
| Airbnb | median houshold income | missing | drop_rows | commit | P | P | P |
| Airbnb | median monthly owner costs (no mortgage) | missing | drop_rows | commit | G | G | G |
| Airbnb | median monthly owner costs (with mortgage) | missing | drop_rows | commit | G | G | G |
| Airbnb | median taxes (no mortgage) | missing | drop_rows | commit | G | G | G |
| Airbnb | median taxes (with mortgage | missing | drop_rows | commit | G | G | G |
| Airbnb | number of females | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | number of males | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | pop2000 | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | pop2010 | missing | drop_rows | commit | P | P | P |
| Airbnb | pop2016 | missing | drop_rows | commit | P | P | P |
| Airbnb | pop_density (people per mile) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | prop taxes paid 2016 | missing | drop_rows | commit | P | P | P |
| Airbnb | unemployment (%) | missing | drop_rows | commit | P | P | P |
| Airbnb | water_area (sq.mi.) | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | zipcode | missing | drop_rows | no commit | ok | ok | ok |
| Airbnb | Average Abnb Price (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Average NumReviews (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Average Number of Bathrooms (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Average Number of Bedrooms (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Average Number of Beds (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Average Number of Guests (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Average Rating (by zipcode) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Bathrooms | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Bedrooms | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Beds | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Count of Abnb | outliers | clip_outliers | commit | P | P | P |
| Airbnb | Density of Abnb (%) | outliers | clip_outliers | commit | P | P | P |
| Airbnb | NumGuests | outliers | clip_outliers | commit | D | D | D |
| Airbnb | NumReviews | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Number of Homes | outliers | clip_outliers | commit | D | D | D |
| Airbnb | Price | outliers | clip_outliers | commit | D | D | D |
| Airbnb | cost_living_index (US avg. = 100) | outliers | clip_outliers | no commit | ok | ok | ok |
| Airbnb | land_area (sq.mi.) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | latitude | outliers | clip_outliers | commit | D | D | D |
| Airbnb | longitude | outliers | clip_outliers | commit | D | D | D |
| Airbnb | median asking price for vacant for-sale home/condo | outliers | clip_outliers | commit | D | D | D |
| Airbnb | median gross rent | outliers | clip_outliers | commit | D | D | D |
| Airbnb | median house value | outliers | clip_outliers | commit | D | D | D |
| Airbnb | median houshold income | outliers | clip_outliers | commit | P | P | P |
| Airbnb | median monthly owner costs (no mortgage) | outliers | clip_outliers | no commit | ok | ok | ok |
| Airbnb | median monthly owner costs (with mortgage) | outliers | clip_outliers | no commit | ok | ok | ok |
| Airbnb | median taxes (no mortgage) | outliers | clip_outliers | commit | P | P | P |
| Airbnb | median taxes (with mortgage | outliers | clip_outliers | no commit | ok | ok | ok |
| Airbnb | number of females | outliers | clip_outliers | commit | D | D | D |
| Airbnb | number of males | outliers | clip_outliers | commit | D | D | D |
| Airbnb | pop2000 | outliers | clip_outliers | commit | D | D | D |
| Airbnb | pop2010 | outliers | clip_outliers | commit | D | D | D |
| Airbnb | pop2016 | outliers | clip_outliers | commit | D | D | D |
| Airbnb | pop_density (people per mile) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | prop taxes paid 2016 | outliers | clip_outliers | commit | D | D | D |
| Airbnb | unemployment (%) | outliers | clip_outliers | commit | D | D | D |
| Airbnb | water_area (sq.mi.) | outliers | clip_outliers | commit | P | P | P |
| Airbnb | zipcode | outliers | clip_outliers | no commit | ok | ok | ok |

## 11. Exploratory-run disclosure

On 2026-11-01, before the amendment was signed, the unchanged pipeline was run on the full datasets for pipeline acceptance (P4): Marketing (`--positive 0`, rule planner) and Airbnb (`--positive Y`), scenario label `exploratory`. They are not study results and no expectation was derived from them. Outcomes as recorded then: Marketing, 16 of 16 candidate evaluations rolled back, nothing committed; Airbnb, no commits, `fill_median` / `fill_mean` delta +0.0000. The registered runs here are separate runs on the eval partition. Note: nine `exploratory_run_*.json` logs exist locally (gitignored, UTC 12:01 to 13:18 on 2026-11-01, scenario `exploratory`; their meta does not record a dataset name), so this disclosure is of at least one run per dataset, not of exactly one; see section 13.

## 12. Honest limits

- Expectations are derived from CleanML dirty-vs-clean diffs (and the dirty file's NaN cells), not from the real-world ground truth. "Expected commit" means CleanML shows error cells there, not that repairing them helps a downstream LR.
- Scoring is per run under per-run Bonferroni (alpha / 16). The numbers in section 3 are what the unchanged agent produced with LR + Brier on these tables for the rule planner; they are not evidence about whether the defects are harmless or whether the gate is right.
- Many Airbnb misses are detector-misses and planner-misses: the detectors never offered some reachable ops, and a 16-iteration budget cannot reach 55 expected-commit rows. Both are properties of the unchanged agent.
- The Groq side of the study is incomplete: of 6 Groq runs, 1 is completed and valid, 2 are valid but terminated early (planner menu-constraint violation, section 6b) and 3 are invalid (API errors, Airbnb) and await rerun. No Groq-vs-rule statement is made until the Airbnb reruns are done.
- `Ethnic` in Marketing is a sensitive attribute; no per-group result is reported. The Airbnb file has 33,145 rows versus 42,492 in the CleanML description; the file was used as is.
- Small N (2 datasets), one split seed, no family-wide correction in the commit rule. This file describes outcomes; it draws no conclusion about the pipeline's usefulness.

## 13. Open questions (for Akira)

1. **`dedupe_rows` is in the v1 operation menu, but the signed amendment says no such op exists.** Read-only findings. `aeterna_qa/modules/config.py`, `OPERATION_MENU` contains `"dedupe_rows",           # drop exact duplicate rows from TRAINING only (column key "*")`. `aeterna_qa/modules/detectors.py` emits a finding with `"defect": "duplicates", "column": "*"` and `"candidate_ops": ["dedupe_rows"]`. `aeterna_qa/modules/executor.py` has `_ROW_LEVEL = {"dedupe_rows"}  # act on whole rows; column key is "*"` and `"dedupe_rows": _via_fit_and_apply("dedupe_rows")` in `_OPERATIONS`. The planner prompt also names it ("exact duplicate rows need dedupe_rows"). The amendment draft (`Documents/AMENDMENT_DRAFT_real_data.md`) says: "No dedupe op exists in the v1 menu; Marketing has 1,154 exact duplicate rows and Airbnb ships CleanML duplicate files. Duplicates are therefore outside the op menu for this study. The op is not added here." and `EXPECTED_OUTCOMES_real_data.md` says "R6 (duplicates). Outside the op menu (section M): no rows." What the logs show: the op was offered and evaluated as `*: dedupe_rows` in the runs (rule Marketing at iteration 1, rule Airbnb at iteration 2, and as iteration 1 of every Airbnb Groq run); it was rolled back every time, and no duplicate row is a scored row, so no k/n in this file is affected. Nothing was edited. The question is whether to record this discrepancy as a dated note (the signed text is not edited).
2. Resolved (Akira, 2026-11-01): Marketing Groq 401 and 402 are valid terminated runs (section 6b); not rerun.
3. Rerun timing for the three invalid Airbnb Groq runs (section 8): approve the rule as written, including the quota-reset wait.
4. Section 11: nine local `exploratory_run_*.json` logs exist while the disclosure text says one run per dataset. Confirm the wording, or list the runs.

## 14. Observations (not re-scoring)

These are descriptive notes. They do not change any registered label or k/n.

- (a) Largest real-data delta is +0.0001 against a Bonferroni bar of 0.0002 (rule runs, Marketing: `Householder` `fill_unknown` / `fill_mode`, `Hometype` `fill_mode`; checked against the audit logs of all 12 eval runs). On this evidence the defects did not measurably affect the LR gate score.
- (b) Planner-miss is largely structural: Airbnb has 55 expected-commit rows against `MAX_ITERATIONS` = 16 (`config.py`), so the budget cannot reach every expected row even with a perfect planner.
- (c) Detector-miss 28/55 on Airbnb is consistent with the documented IQR limit on skewed columns.
- Registered k/n are unchanged.

## 15. Product backlog (not this study)

- On a planner `ValueError` (e.g. a re-proposed, already-evaluated pair), re-prompt the planner instead of ending the run. Not part of this study; the pipeline is unchanged here.

## 16. Credit and licence

- Marketing: CleanML benchmark (Li et al., https://arxiv.org/abs/1904.09483; https://github.com/chu-data-lab/CleanML); data originally Impact Resources, Inc. (Columbus, OH, 1987). No licence stated: academic use only, not redistributed, no per-ethnicity findings.
- Airbnb data: Inside Airbnb (CC BY), via CleanML. The data files are in the gitignored `Dataset/real/` and are not committed.
