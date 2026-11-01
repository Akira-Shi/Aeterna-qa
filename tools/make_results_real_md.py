#!/usr/bin/env python3
"""Render Documents/RESULTS_REAL.md from Documents/real_results/real_results.json (written by score_real_study.py).

Reporting rules (Akira, 2026-11-01): rule-planner runs are the primary result. A Groq run with any API error is
"invalid: infrastructure failure" and carries no hit/miss/stage/delta numbers. A Groq run that ended on a planner
validation error (not an API error) is listed as pending Akira's classification and is not scored. Reads only existing
logs and the derived scores; it runs no pipeline, no Groq call and no rerun.
"""
import json, glob, re
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "Documents/real_results/real_results.json"))
RES = D["results"]
AUD = {Path(f).name: json.load(open(f)) for f in glob.glob(str(ROOT / "Documents/real_results/audit/real_*_eval_*.json"))}
ABORT = json.load(open(next(glob.iglob(str(ROOT / "Documents/real_results/audit/ABORTED_attempt1_*.json")))))
CODE = {"gate-reject": "G", "planner-miss": "P", "detector-miss": "D", "unclassified (error)": "U"}
PENDING = "planner error (not an API error) - Akira to classify"
INVALID = "invalid: infrastructure failure"


def status(r):
    """Classification strictly from the audit log (the per-iteration `error` field)."""
    if r["planner"] == "rule" or r["n_errors"] == 0:
        return "valid"
    return INVALID if r["errors"][0]["error"].startswith("Error code:") else PENDING


def code(x):
    if x["obs"] == "hit": return "H"
    if x["obs"] == "correct no-commit": return "ok"
    if x["obs"] == "miss": return CODE.get(x["stage"], "N")
    return "X"


def get(ds, pl, seed):
    return next(r for r in RES if r["dataset"] == ds and r["planner"] == pl and r["seed"] == seed)


def counts(r):
    pos = [x for x in r["rows"] if x["expected"] == "commit"]
    neg = [x for x in r["rows"] if x["expected"] != "commit"]
    st = defaultdict(int)
    for x in pos:
        if x["stage"]: st[x["stage"]] += 1
    return pos, neg, st


def sig(r):
    return json.dumps([(x["col"], x["typ"], x["obs"], x["stage"]) for x in r["rows"]])


def clip(e, n=2000):
    # the planner-validation message embeds the whole option list; keep the head and mark the cut
    return e if len(e) <= n else e[:n] + " [...]"


def full_err(r):
    return AUD[r["file"]]["iterations"][-1]["error"]


for ds in ("Marketing", "Airbnb"):
    assert len({sig(get(ds, "rule", s)) for s in (401, 402, 403)}) == 1, "rule seeds should be identical by construction"

VALID_GROQ = [r for r in RES if r["planner"] == "groq" and status(r) == "valid"]
INV = [r for r in RES if r["planner"] == "groq" and status(r) == INVALID]
PEN = [r for r in RES if r["planner"] == "groq" and status(r) == PENDING]
RULE = [r for r in RES if r["planner"] == "rule"]
assert not any(r["committed_ops"] for r in RULE + VALID_GROQ)
assert not any(r["unexplained"] or r["wrong_op"] for r in RULE + VALID_GROQ)

L = []
a = L.append
a("# RESULTS_REAL - pre-registered real-data evaluation (CleanML Marketing and Airbnb)\n")
a("Real (not injected) data with natural defects. Separate from the synthetic C1-C5 study in `RESULTS.md`; never pooled with it. LR + Brier gate only (evaluator v1.1). Positive labels: Marketing `Income = 0`, Airbnb `Rating = Y`. Expectations come from CleanML-derived dirty-vs-clean diffs (signed `EXPECTED_OUTCOMES_real_data.md`), not from the real-world ground truth.\n")
a("Status of this file (2026-11-01): re-rendered after Groq hit API limits during P5. The rule-planner runs are the primary result and are reported first. Every Groq run with an API error is marked invalid (infrastructure failure) and carries no hit, miss or stage numbers. Two Groq runs ended on a planner-validation error that is not an API error; they are listed separately and not scored until Akira classifies them. No Groq-vs-rule comparison is made. No rerun has been done under the rerun rule (section 8).\n")
a("## 1. Headline\n")
a("- **Primary result, rule planner (6 eval runs: Marketing and Airbnb, seeds 401-403; the three seeds are identical by construction)**: no run committed anything. Wrong-op commits: 0. Unexplained commits: 0.")
a("- H2 (positives, expected commit), rule planner: Marketing **0/9** hit; Airbnb **0/55** hit.")
a("- H1 (negatives, expected no commit), rule planner: Marketing **17/17** correct no-commit; Airbnb **23/23**. Positives and negatives are separate k/n, never pooled.")
a("- Miss stages, rule planner (detector / planner / gate): Marketing 0 / 4 / 5; Airbnb 28 / 23 / 4 (section 4).")
a(f"- Groq planner (6 runs): {len(VALID_GROQ)} valid, {len(INV)} invalid (infrastructure failure: API error), {len(PEN)} pending Akira's classification (planner-validation error, not an API error). Details in section 6. Groq-vs-rule comparison waits until every Groq run is valid.\n")
a("## 2. What was run\n")
a("| Item | Value |\n|---|---|")
a("| Code state when the runs started | HEAD `a24c16c9cb82695a3807a7e59ca8be9e47fda924` on main (signing commit `8136971`; section 12 row commit `1e68bc6`; frozen_check baseline commit `1e68bc6`, manifest committed in `a24c16c`) |")
a("| TaskSpec release | tag `v2-p4` = commit `02f63d3e9d58d215c806efbf3f576b3c38da42bb` |")
a("| Expected outcomes | blob `a40c7790b19d1cc45a0e1f29d16e1ce431e13fb3`; sha256 of `git show` bytes `65eab5608c78949466b2d8307e82c82c45026cf7d0746972ef24050f901fab55` |")
a("| Amendment | blob `4dc26b58ad68d49194355b41d4fdba710f1bae1b` |")
a("| Data (sha256 verified before every load) | Marketing `raw/raw.csv` `6a05ac3f7579d07c9731741f53012534de72a9b93ebf482e709d5c1da6e8e1a3`; Airbnb `raw/raw.csv` `e5e37131e92cbc4edeeaecaf14c2acdc404994e8d1e725b8ab7c65fe214b504d` |")
a("| Split | 20/80 pilot/eval, stratified on the target, assigned in groups of identical feature vectors (same construction as `study.base_and_split`), split seed 20261101. Marketing 8,993 rows: pilot 1,772 / eval 7,221. Airbnb 33,145 rows: pilot 6,612 / eval 26,533. No complete-case filter (the NaN cells are the error cells). No host name or host ID column exists in the Airbnb file, so nothing was dropped. |")
a("| Pilot | One rule-planner pipeline-check run per dataset (seed 401); both committed nothing. Used for nothing else; no expectation or setting derived from it. |")
a("| Registered runs | eval partition; seeds 401, 402, 403; planners rule and Groq (`openai/gpt-oss-20b`, temperature 0.2); LR only; 12 eval runs in total (6 rule, 6 Groq). |")
a("| Labels | audit `scenario` = `real_marketing` / `real_airbnb`; file names `real_<dataset>_<planner>_<seed>_<partition>_*`; label text \"REAL DATA ... natural defects, not injected\". |")
a("| Drivers | `tools/run_real_study.py` (calls the unchanged pipeline), `tools/score_real_study.py` (scoring, offer reconstruction), `tools/make_results_real_md.py` (this file). No pipeline, detector, op, menu, gate or evaluator change. |")
a("| Audit logs | `Documents/real_results/audit/` (copies of the gitignored `aeterna_qa/logs/study_real/` JSONs); derived scores `Documents/real_results/real_results.json`. |\n")
a("Seeds. The pipeline has no injection and its folds and model are fixed by `config.RANDOM_STATE`, so the seed only labels a replicate. The rule planner is deterministic: its three seeds are identical by construction (checked: the per-row outcomes of seeds 401, 402, 403 are identical in both datasets). Only the Groq planner (sampling) can differ between seeds. This was noticed when the runs were set up, before any result.\n")

a("## 3. Rule-planner results (PRIMARY), k/n per dataset and seed\n")
a("H2 = positives (expected commit) hit, k/n. H1 = negatives (expected no commit) with no commit, k/n. Misses D / P / G / U = detector-miss / planner-miss / gate-reject / unclassified (error) among the positives that did not commit. Evals = candidate evaluations run (max 16). All six rule runs used the full 16-iteration budget with no error.\n")
a("| Dataset | Planner | Seed | H2 hit | H1 correct | Misses D / P / G / U | Commits | Evals | Ended |\n|---|---|---|---|---|---|---|---|---|")
for ds in ("Marketing", "Airbnb"):
    for seed in (401, 402, 403):
        r = get(ds, "rule", seed)
        pos, neg, st = counts(r)
        a(f"| {ds} | rule | {seed} | {sum(x['obs']=='hit' for x in pos)}/{len(pos)} | {sum(x['obs']=='correct no-commit' for x in neg)}/{len(neg)} | {st['detector-miss']} / {st['planner-miss']} / {st['gate-reject']} / {st['unclassified (error)']} | none | {r['n_evaluated']} | 16 iterations |")
a("")
a("Nothing committed, so there are no committed-op deltas. Descriptive: largest evaluated paired delta per rule run with its Bonferroni bar (a commit needs delta > 0 and delta >= bar):\n")
a("| Dataset | Planner | Seed | Largest delta (bar) | Evaluated pairs with delta > 0 |\n|---|---|---|---|---|")
for ds in ("Marketing", "Airbnb"):
    for seed in (401, 402, 403):
        r = get(ds, "rule", seed)
        its = [i for i in AUD[r["file"]]["iterations"] if i["error"] is None and i["column"] is not None]
        b = max(its, key=lambda i: i["delta"])
        a(f"| {ds} | rule | {seed} | {b['delta']:+.4f} (bar {b['threshold']:.4f}) on {b['column']}: {b['operation']} | {sum(i['delta']>0 for i in its)} of {len(its)} |")
a("")
a("Baselines (neg-Brier, fixed-fold LR): Marketing -0.1556; Airbnb -0.2041, unchanged in every run.\n")

a("## 4. Failure-stage counts for expected-commit rows that did not commit (rule runs)\n")
a("Labels only (amendment section E); scoring is unchanged. Unit: one row per (dataset, column, error type). Counts per rule run:\n")
for ds in ("Marketing", "Airbnb"):
    n = sum(1 for x in get(ds, "rule", 401)["rows"] if x["expected"] == "commit")
    parts = []
    for seed in (401, 402, 403):
        _, _, st = counts(get(ds, "rule", seed))
        parts.append(f"{seed}: {st['detector-miss']} detector-miss, {st['planner-miss']} planner-miss, {st['gate-reject']} gate-reject")
    a(f"- **{ds}** ({n} expected-commit rows, 0 hit), rule: " + "; ".join(parts))
a("")
a(f"**Sanity check (reconstruction): {'PASSED' if D['sanity_ok'] else 'FAILED'}.** Offers were reconstructed after the runs by re-running `detect()` and the `remaining_options` logic, read-only, on the exact input of every logged iteration (the eval partition materialised with that iteration's committed ops; nothing committed, so it equals the eval partition), under the same TaskSpec settings, with no pipeline change. Every (column, op) the audit log shows as evaluated appeared in that iteration's reconstructed offers, in all 12 runs. A row is planner-miss if a reachable op was offered at any logged iteration but never evaluated; the `unclassified (error)` rule applied to no row. No stage counts are reported for invalid or pending Groq runs.\n")

a("## 5. Other outcomes (rule runs; valid Groq runs listed separately)\n")
a("| Item | Result |\n|---|---|")
a("| Unexplained commits (commit on a column with no error cells; listed separately) | rule: none. Valid Groq runs (Marketing 403 only): none |")
a("| Wrong-op commits (failure condition) | rule: **0**. Valid Groq runs (Marketing 403 only): 0 |")
a("| Committed ops | rule: none in any run. Valid Groq run: none |")
a("| Evaluation counts | rule: 16 per run in both datasets (budget exhausted) |")
a("| Primary statistic | per-run Bonferroni (alpha / 16 look-backs = `MAX_ITERATIONS`), unchanged |")
a("| Secondary (across-dataset, information only) | family = 16 look-backs x 12 eval runs = 192; it can only flag commits, and there are none |")
a("| H3 (no harm), rule runs | vacuous: 0 committed ops (details below) |\n")
a("**H3 (rule runs only; no Groq data is used here).** Definition (amendment section E): every committed op has a final gate delta >= 0 on the held-out evaluation partition, and no collateral damage measurable against ground truth where G1 applies; a commit with negative delta on a partition not used for the commit decision is a failure of the gate. Evaluated as written for the six rule runs: there are 0 committed ops, so the first clause is vacuously satisfied (0 of 0 violate) and no gate failure occurred. Not computable without making a choice: (a) the \"partition not used for the commit decision\" is not named (the pilot is declared a pipeline check only, and the eval partition is where the commit decision is made), so no out-of-decision delta was computed; (b) \"ground truth where G1 applies\" is not defined in the amendment text, and there is no committed repair to compare in any case. Nothing was chosen for those two parts. (The earlier version of this file computed H3 from zero committed ops across all runs; it used no Groq-specific data, so the result is unchanged.)\n")

a("## 6. Groq-planner runs: validity (classified strictly from the audit logs)\n")
a("Rule used: a Groq run with any API error (HTTP status error from the Groq client: 429, 400 or other) is `invalid: infrastructure failure`; it gets no hit/miss/stage/delta numbers. A planner exception that is not an API error is listed under its own heading and is not scored until Akira rules. Error text is the audit-log `error` field of the last iteration, verbatim.\n")
a("| Dataset | Seed | Status | Evaluations done before the error | Iteration of error | Error kind |\n|---|---|---|---|---|---|")
for ds in ("Marketing", "Airbnb"):
    for seed in (401, 402, 403):
        r = get(ds, "groq", seed)
        stt = status(r)
        if stt == "valid":
            a(f"| {ds} | {seed} | valid (16 iterations, no `error` entry in the audit log) | 16 | - | none |")
        else:
            e = r["errors"][0]
            kind = re.match(r"Error code: (\d+) - .*?'code': '([a-z_]+)'", e["error"], re.S)
            kind = f"API {kind.group(1)} {kind.group(2)}" if e["error"].startswith("Error code:") else "planner raised ValueError (pair not in remaining_options)"
            a(f"| {ds} | {seed} | **{stt}** | {r['n_evaluated']} | {e['iteration']} | {kind} |")
a("")
a("### 6a. Invalid: infrastructure failure (API error). Reported as `invalid` only.\n")
for r in INV:
    e = r["errors"][0]
    a(f"- **{r['dataset']} Groq {r['seed']}** (`{r['file']}`): iteration {e['iteration']}, {r['n_evaluated']} evaluations completed before the error. Verbatim: `{full_err(r)}`")
a(f"- **Aborted first attempt, Airbnb Groq 401** (`ABORTED_attempt1_real_airbnb_groq_401_eval_20261101T133459Z.json`): iteration {ABORT['iterations'][0]['iteration']}, 0 evaluations. Verbatim: `{ABORT['iterations'][0]['error']}`")
a("")
a("### 6b. Planner error that is not an API error: Akira to classify. Not scored as hit/miss.\n")
for r in PEN:
    e = r["errors"][0]
    a(f"- **{r['dataset']} Groq {r['seed']}** (`{r['file']}`): iteration {e['iteration']}, {r['n_evaluated']} evaluations completed before it. The Groq API call itself succeeded and returned a response; the planner's own validation (`planner.py`, `plan()`) then raised a `ValueError` because the returned (column, operation) pair is not in `remaining_options`. Verbatim: `{clip(full_err(r), 160)}`  (the message continues with the full remaining-options list; the pair `(Person, fill_mode)` had already been evaluated at iteration 5). The unchanged pipeline treats a planner exception as the end of the run. Under the rule as given (API errors only) this is not labelled invalid here. Whether it is a valid miss/no-result or invalid is Akira's decision.")
a("")
a("### 6c. Valid Groq run\n")
for r in VALID_GROQ:
    pos, neg, st = counts(r)
    a(f"- **{r['dataset']} Groq {r['seed']}** (`{r['file']}`): 16 iterations, every `error` field is `None`, and the driver console output (`_driver_eval_Marketing_groq_403.out`, `real_marketing_groq_403_eval.txt`) contains no error text. H2 {sum(x['obs']=='hit' for x in pos)}/{len(pos)}, H1 {sum(x['obs']=='correct no-commit' for x in neg)}/{len(neg)}, misses D / P / G / U = {st['detector-miss']} / {st['planner-miss']} / {st['gate-reject']} / {st['unclassified (error)']}, commits none, unexplained 0, wrong-op 0. This is a single valid Groq run; no comparison with the rule planner is made.")
a("")
a("Limit on this classification. The Groq Python client (`groq` 1.7.0) is created with its defaults (`Groq(api_key=...)` in `planner.py`); the library default is to retry some failed requests (default `DEFAULT_MAX_RETRIES` = 2) without logging them. The audit log records only errors that reached the pipeline, so \"no API error in the log\" means no error survived the client's own retries; whether the client silently retried inside any run cannot be established from the saved files. This applies to the valid Groq run (Marketing 403) and to the Marketing 401/402 runs.\n")
a("Other notes from the incident (unchanged facts):\n")
a("- The Explain step was skipped for the two pilot runs (console `UnicodeEncodeError`); the audit logs are unaffected. Eval runs used `PYTHONIOENCODING=utf-8` and have Explain reports in `aeterna_qa/logs/study_real/`. Explain LLM notes were switched off for these runs (`EXPLAIN_USE_LLM = False`, to avoid extra Groq calls); the verdicts are deterministic.")
a("- Cosmetic, from existing code: the console baseline line prints \"exploratory data\" because the TaskSpec path passes `task_meta`; the audit `scenario` and label are the real-data ones.\n")

a("## 7. Reruns done so far (original and rerun side by side; none is preferred)\n")
a("All reruns so far were decided by the driver operator on 2026-11-01 before any result of the rerun was seen, and were launches of the same command after an interrupted parallel launch. They were made before the rerun rule (section 8) was written, so they are not governed by it. Times are UTC from the audit logs. Sources: audit logs, `aeterna_qa/logs/study_real/_driver_*.out`, `aborted/`, and the old RESULTS_REAL.md section 6 (commit `de141ac`).\n")
a("| # | Run id | Why rerun | Original outcome | Rerun outcome | Files |\n|---|---|---|---|---|---|")
a("| 1 | Airbnb Groq 401 | First launch ran the Marketing and Airbnb Groq jobs in parallel; the Airbnb job hit a per-minute token limit at iteration 1. | Started 13:34:04, ended 13:34:59: iteration 1 failed with `Error code: 429 ... tokens per minute (TPM): Limit 8000, Used 7585, Requested 4861`, 0 evaluations, no result. API error: invalid under Akira's rule. | Started 13:40:28, ended 13:46:54: 11 evaluations, then iteration 12 failed with `Error code: 400 ... json_validate_failed`. API error: invalid under Akira's rule. | Original: `audit/ABORTED_attempt1_real_airbnb_groq_401_eval_20261101T133459Z.json` (also `aeterna_qa/logs/study_real/aborted/*`, `_driver_eval_Airbnb_groq.out`). Rerun: `audit/real_airbnb_groq_401_eval_20261101T134654Z.json`, `_driver_eval_Airbnb_groq_rerun.out`. |")
a("| 2 | Airbnb Groq 402 | Same parallel launch; process was stopped by the operator after the 401 failure. | Started in the first launch (header `=== real_airbnb_groq_402_eval` is the last line of `_driver_eval_Airbnb_groq.out`); no audit JSON, no iteration output. No outcome exists. | Started 13:47:21, ended 13:52:06: 8 evaluations, then iteration 9 failed with `Error code: 400 ... json_validate_failed`. API error: invalid. | Original: only the header line in `_driver_eval_Airbnb_groq.out`. Rerun: `audit/real_airbnb_groq_402_eval_20261101T135206Z.json`. |")
a("| 3 | Marketing Groq 403 | Same parallel launch; process was stopped by the operator while 403 was starting. | Started in the first launch (header `=== real_marketing_groq_403_eval` is the last line of `_driver_eval_Marketing_groq.out`); no audit JSON, no iteration output. No outcome exists. | Started 13:36:14, ended 13:39:45: 16 evaluations, no `error` entry. Valid by the log (see limit in section 6). | Original: only the header line in `_driver_eval_Marketing_groq.out`. Rerun: `audit/real_marketing_groq_403_eval_20261101T133945Z.json`, `_driver_eval_Marketing_groq_403.out`. |")
a("")
a("Not a rerun: Airbnb Groq 403 was not started in the first launch (no header line in `_driver_eval_Airbnb_groq.out`); its one execution (13:52:33 to 13:54:01) ended on `Error code: 429 ... tokens per day (TPD): Limit 200000, Used 195832, Requested 5703` after 3 evaluations (invalid, section 6a).\n")
a("Where the original and the rerun both exist (row 1), both are API-error runs and both are invalid; no choice between them is made. For rows 2 and 3 no original outcome exists to compare.\n")
a("What is unknowable from the saved files:\n")
a("- Exactly when and how the first-launch processes in rows 2 and 3 were stopped, and whether they made Groq API calls before being stopped (the console files hold only the header line; no audit JSON was written). Any such calls count towards the Groq token counters and are not recorded.\n- Whether the Groq client silently retried requests inside any run (section 6).\n- The text-file outputs `real_<...>_eval.txt` carry no timestamp in their name and are overwritten by a rerun of the same run id; the earlier `real_airbnb_groq_401_eval.txt` survives only because it was moved to `aborted/`. The JSON audit logs carry a UTC stamp in the file name and none was overwritten: every (dataset, planner, seed, partition) has exactly one JSON in `aeterna_qa/logs/study_real/` apart from the aborted Airbnb Groq 401 attempt (12 eval and 2 pilot JSONs, plus the aborted one kept in `aborted/`). Reruns that left no JSON and no console file cannot be ruled out, but none is recorded anywhere (driver outputs, the old RESULTS_REAL.md, `Documentation.md`, or the single commit `de141ac`).\n- How much of the Groq daily token counter (195,832 of 200,000 at the time of the TPD error) was used by P5 runs versus other Groq use on the same organisation earlier that day (for example the pre-signing exploratory runs); the log does not say.\n")

a("## 8. Rerun rule (written before any rerun)\n")
a("Dated 2026-11-01. Written by the operator on Akira's instruction, before any rerun is made. No rerun has been done under this rule yet.\n")
a("1. Rerun **all** Groq runs that had an API error (every run listed in section 6a, including any run later reclassified as an API-error run by Akira). A Groq run that is **completed and valid is never rerun**.\n"
  "2. Timing: rerun only after the daily Groq quota has reset (rolling 24 hours; the TPD counter reached 195,832 of 200,000 on 2026-11-01).\n"
  "3. On a 429, wait the server's retry-after time and retry, at most 5 retries per call; pause between calls to stay under the per-minute limit.\n"
  "4. A rerun replaces the invalid status only. The original invalid record stays listed in sections 6a and 7; an original is never deleted, overwritten or hidden. The rerun's own result, if valid, is reported as that run's result, with its start and end time.\n"
  "5. A rerun that again hits an API error is again invalid, is listed, and is subject to this rule after the next quota reset.\n"
  "6. The two runs in section 6b are not rerun under this rule unless Akira classifies them as API-error runs.\n"
  "7. No change to the pipeline, detectors, ops, menu, gate, prompt, temperature, model or evaluator for a rerun. Seeds and partition are as originally registered.\n")

a("## 9. Groq-vs-rule comparison\n")
a("Groq-vs-rule comparison waits until every Groq run is valid.\n")

a("## 10. Full per-row table\n")
a("Codes: **H** hit; **ok** correct no-commit (expected no commit, none occurred); **X** commit on an expected-no-commit row; misses: **D** detector-miss, **P** planner-miss, **G** gate-reject, **U** unclassified (error), **N** not separable. Columns: rule seeds 401/402/403, then the valid Groq run (Marketing 403 only; invalid and pending Groq runs have no per-row entries). \"Reachable ops\" are those of the signed file; any one committing is a hit.\n")
for ds in ("Marketing", "Airbnb"):
    gcols = [r for r in VALID_GROQ if r["dataset"] == ds]
    hdr = "| Dataset | Column | Error type | Reachable ops | Expected | Rule 401 | 402 | 403 |" + "".join(f" Groq {r['seed']} |" for r in gcols)
    a(hdr)
    a("|---|---|---|---|---|---|---|---|" + "---|" * len(gcols))
    base = get(ds, "rule", 401)["rows"]
    for i, x in enumerate(base):
        cells = [code(get(ds, "rule", s)["rows"][i]) for s in (401, 402, 403)] + [code(r["rows"][i]) for r in gcols]
        a(f"| {ds} | {x['col']} | {x['typ']} | {', '.join(x['reachable'])} | {x['expected']} | " + " | ".join(cells) + " |")
    a("")

a("## 11. Exploratory-run disclosure\n")
a("On 2026-11-01, before the amendment was signed, the unchanged pipeline was run on the full datasets for pipeline acceptance (P4): Marketing (`--positive 0`, rule planner) and Airbnb (`--positive Y`), scenario label `exploratory`. They are not study results and no expectation was derived from them. Outcomes as recorded then: Marketing, 16 of 16 candidate evaluations rolled back, nothing committed; Airbnb, no commits, `fill_median` / `fill_mean` delta +0.0000. The registered runs here are separate runs on the eval partition. Note: nine `exploratory_run_*.json` logs exist locally (gitignored, UTC 12:01 to 13:18 on 2026-11-01, scenario `exploratory`; their meta does not record a dataset name), so this disclosure is of at least one run per dataset, not of exactly one; see section 13.\n")

a("## 12. Honest limits\n")
a("- Expectations are derived from CleanML dirty-vs-clean diffs (and the dirty file's NaN cells), not from the real-world ground truth. \"Expected commit\" means CleanML shows error cells there, not that repairing them helps a downstream LR.")
a("- Scoring is per run under per-run Bonferroni (alpha / 16). The numbers in section 3 are what the unchanged agent produced with LR + Brier on these tables for the rule planner; they are not evidence about whether the defects are harmless or whether the gate is right.")
a("- Many Airbnb misses are detector-misses and planner-misses: the detectors never offered some reachable ops, and a 16-iteration budget cannot reach 55 expected-commit rows. Both are properties of the unchanged agent.")
a("- The Groq side of the study is incomplete: of 6 Groq runs, 1 is valid, 3 are invalid (API errors) and 2 await Akira's classification. No Groq result other than the one valid run is reported, and no Groq-vs-rule statement is made.")
a("- `Ethnic` in Marketing is a sensitive attribute; no per-group result is reported. The Airbnb file has 33,145 rows versus 42,492 in the CleanML description; the file was used as is.")
a("- Small N (2 datasets), one split seed, no family-wide correction in the commit rule. This file describes outcomes; it draws no conclusion about the pipeline's usefulness.\n")

a("## 13. Open questions (for Akira)\n")
a("1. **`dedupe_rows` is in the v1 operation menu, but the signed amendment says no such op exists.** Read-only findings. `aeterna_qa/modules/config.py`, `OPERATION_MENU` contains `\"dedupe_rows\",           # drop exact duplicate rows from TRAINING only (column key \"*\")`. `aeterna_qa/modules/detectors.py` emits a finding with `\"defect\": \"duplicates\", \"column\": \"*\"` and `\"candidate_ops\": [\"dedupe_rows\"]`. `aeterna_qa/modules/executor.py` has `_ROW_LEVEL = {\"dedupe_rows\"}  # act on whole rows; column key is \"*\"` and `\"dedupe_rows\": _via_fit_and_apply(\"dedupe_rows\")` in `_OPERATIONS`. The planner prompt also names it (\"exact duplicate rows need dedupe_rows\"). The amendment draft (`Documents/AMENDMENT_DRAFT_real_data.md`) says: \"No dedupe op exists in the v1 menu; Marketing has 1,154 exact duplicate rows and Airbnb ships CleanML duplicate files. Duplicates are therefore outside the op menu for this study. The op is not added here.\" and `EXPECTED_OUTCOMES_real_data.md` says \"R6 (duplicates). Outside the op menu (section M): no rows.\" What the logs show: the op was offered and evaluated as `*: dedupe_rows` in the runs (rule Marketing at iteration 1, rule Airbnb at iteration 2, and as iteration 1 of every Airbnb Groq run); it was rolled back every time, and no duplicate row is a scored row, so no k/n in this file is affected. Nothing was edited. The question is whether to record this discrepancy as a dated note (the signed text is not edited).")
a("2. Classification of the two Marketing Groq runs (401, 402) that ended on a planner-validation `ValueError` (section 6b): invalid, or a valid no-result?")
a("3. Rerun timing for the invalid Groq runs (section 8): approve the rule as written, including the quota-reset wait.")
a("4. Section 11: nine local `exploratory_run_*.json` logs exist while the disclosure text says one run per dataset. Confirm the wording, or list the runs.\n")

a("## 14. Credit and licence\n")
a("- Marketing: CleanML benchmark (Li et al., https://arxiv.org/abs/1904.09483; https://github.com/chu-data-lab/CleanML); data originally Impact Resources, Inc. (Columbus, OH, 1987). No licence stated: academic use only, not redistributed, no per-ethnicity findings.")
a("- Airbnb data: Inside Airbnb (CC BY), via CleanML. The data files are in the gitignored `Dataset/real/` and are not committed.")
(ROOT / "Documents/RESULTS_REAL.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
print("written", len(L))
