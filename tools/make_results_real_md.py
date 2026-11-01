#!/usr/bin/env python3
"""Render Documents/RESULTS_REAL.md from Documents/real_results/real_results.json (written by score_real_study.py)."""
import json, glob
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "Documents/real_results/real_results.json"))
RES = D["results"]
AUD = {Path(f).name: json.load(open(f)) for f in glob.glob(str(ROOT / "Documents/real_results/audit/real_*_eval_*.json"))}
CODE = {"gate-reject": "G", "planner-miss": "P", "detector-miss": "D", "unclassified (error)": "U"}


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


L = []
a = L.append
a("# RESULTS_REAL - pre-registered real-data evaluation (CleanML Marketing and Airbnb)\n")
a("Real (not injected) data with natural defects. Separate from the synthetic C1-C5 study in `RESULTS.md`; never pooled with it. LR + Brier gate only (evaluator v1.1). Positive labels: Marketing `Income = 0`, Airbnb `Rating = Y`. Expectations come from CleanML-derived dirty-vs-clean diffs (signed `EXPECTED_OUTCOMES_real_data.md`), not from the real-world ground truth.\n")
a("## 1. Headline\n")
a("- **No run committed anything**: 12 of 12 eval runs (Marketing and Airbnb, rule and Groq, seeds 401-403). Wrong-op commits: **0** (the failure condition did not occur). Unexplained commits: **0**.")
a("- H2 (sensitivity, positives): Marketing **0/9** hit in every run; Airbnb **0/55** hit in every run.")
a("- H1 (safety, negatives): Marketing **17/17** correct no-commit in every run; Airbnb **23/23**. Positives and negatives are separate k/n, never pooled.")
a("- Every miss is labelled by pipeline stage (section 4). Airbnb misses are mostly detector-miss and planner-miss; gate-reject is small (Marketing 5, Airbnb 4 per rule run).")
a("- 5 of 6 Groq-planner runs ended early on a planner or API error (section 6); reported as they happened, not re-run to change that.\n")
a("## 2. What was run\n")
a("| Item | Value |\n|---|---|")
a("| Code state when the runs started | HEAD `a24c16c9cb82695a3807a7e59ca8be9e47fda924` on main (signing commit `8136971`; section 12 row commit `1e68bc6`; frozen_check baseline commit `1e68bc6`, manifest committed in `a24c16c`) |")
a("| TaskSpec release | tag `v2-p4` = commit `02f63d3e9d58d215c806efbf3f576b3c38da42bb` |")
a("| Expected outcomes | blob `a40c7790b19d1cc45a0e1f29d16e1ce431e13fb3`; sha256 of `git show` bytes `65eab5608c78949466b2d8307e82c82c45026cf7d0746972ef24050f901fab55` |")
a("| Amendment | blob `4dc26b58ad68d49194355b41d4fdba710f1bae1b` |")
a("| Data (sha256 verified before every load) | Marketing `raw/raw.csv` `6a05ac3f7579d07c9731741f53012534de72a9b93ebf482e709d5c1da6e8e1a3`; Airbnb `raw/raw.csv` `e5e37131e92cbc4edeeaecaf14c2acdc404994e8d1e725b8ab7c65fe214b504d` |")
a("| Split | 20/80 pilot/eval, stratified on the target, assigned in groups of identical feature vectors (same construction as `study.base_and_split`), split seed 20261101. Marketing 8,993 rows: pilot 1,772 / eval 7,221. Airbnb 33,145 rows: pilot 6,612 / eval 26,533. No complete-case filter (the NaN cells are the error cells). No host name or host ID column exists in the Airbnb file, so nothing was dropped. |")
a("| Pilot | One rule-planner pipeline-check run per dataset (seed 401); both committed nothing. Used for nothing else; no expectation or setting derived from it. |")
a("| Registered runs | eval partition; seeds 401, 402, 403; planners rule and Groq (`openai/gpt-oss-20b`, temperature 0.2); LR only; 12 eval runs in total. |")
a("| Labels | audit `scenario` = `real_marketing` / `real_airbnb`; file names `real_<dataset>_<planner>_<seed>_<partition>_*`; label text \"REAL DATA ... natural defects, not injected\". |")
a("| Drivers | `tools/run_real_study.py` (calls the unchanged pipeline), `tools/score_real_study.py` (scoring, offer reconstruction), `tools/make_results_real_md.py` (this file). No pipeline, detector, op, menu, gate or evaluator change. |")
a("| Audit logs | `Documents/real_results/audit/` (copies of the gitignored `aeterna_qa/logs/study_real/` JSONs); derived scores `Documents/real_results/real_results.json`. |\n")
a("Seeds. The pipeline has no injection and its folds and model are fixed by `config.RANDOM_STATE`, so the seed only labels a replicate. The rule planner is deterministic: its three seeds are identical by construction. Only the Groq planner (sampling) can differ between seeds. This was noticed when the runs were set up, before any result.\n")
a("## 3. k/n per dataset, per planner, per seed\n")
a("H2 = positives (expected commit) hit, k/n. H1 = negatives (expected no commit) with no commit, k/n. Misses D / P / G / U = detector-miss / planner-miss / gate-reject / unclassified (error) among the positives that did not commit. Evals = candidate evaluations run (max 16).\n")
a("| Dataset | Planner | Seed | H2 hit | H1 correct | Misses D / P / G / U | Commits | Evals | Ended |\n|---|---|---|---|---|---|---|---|---|")
for ds in ("Marketing", "Airbnb"):
    for pl in ("rule", "groq"):
        for seed in (401, 402, 403):
            r = get(ds, pl, seed)
            pos, neg, st = counts(r)
            if r["n_errors"] == 0:
                ended = "16 iterations"
            else:
                e = r["errors"][0]["error"]
                ended = "planner error: invalid pair" if e.startswith("Planner chose") else ("API 429 daily tokens (TPD)" if "429" in e else "API 400 JSON validate")
            a(f"| {ds} | {pl} | {seed} | {sum(x['obs']=='hit' for x in pos)}/{len(pos)} | {sum(x['obs']=='correct no-commit' for x in neg)}/{len(neg)} | {st['detector-miss']} / {st['planner-miss']} / {st['gate-reject']} / {st['unclassified (error)']} | none | {r['n_evaluated']} | {ended} |")
a("")
a("Nothing committed, so there are no committed-op deltas. Descriptive: largest evaluated paired delta per run with its Bonferroni bar (a commit needs delta > 0 and delta >= bar):\n")
a("| Dataset | Planner | Seed | Largest delta (bar) | Evaluated pairs with delta > 0 |\n|---|---|---|---|---|")
for ds in ("Marketing", "Airbnb"):
    for pl in ("rule", "groq"):
        for seed in (401, 402, 403):
            r = get(ds, pl, seed)
            its = [i for i in AUD[r["file"]]["iterations"] if i["error"] is None and i["column"] is not None]
            b = max(its, key=lambda i: i["delta"])
            a(f"| {ds} | {pl} | {seed} | {b['delta']:+.4f} (bar {b['threshold']:.4f}) on {b['column']}: {b['operation']} | {sum(i['delta']>0 for i in its)} of {len(its)} |")
a("")
a("Baselines (neg-Brier, fixed-fold LR): Marketing -0.1556; Airbnb -0.2041, unchanged in every run.\n")
a("## 4. Failure-stage counts for expected-commit rows that did not commit\n")
a("Labels only (amendment section E); scoring is unchanged. Unit: one row per (dataset, column, error type). Counts per run:\n")
for ds in ("Marketing", "Airbnb"):
    n = sum(1 for x in get(ds, "rule", 401)["rows"] if x["expected"] == "commit")
    a(f"- **{ds}** ({n} expected-commit rows, 0 hit):")
    for pl in ("rule", "groq"):
        parts = []
        for seed in (401, 402, 403):
            _, _, st = counts(get(ds, pl, seed))
            parts.append(f"{seed}: {st['detector-miss']} detector-miss, {st['planner-miss']} planner-miss, {st['gate-reject']} gate-reject")
        a(f"  - {pl}: " + "; ".join(parts))
a("")
a(f"**Sanity check (reconstruction): {'PASSED' if D['sanity_ok'] else 'FAILED'}.** Offers were reconstructed after the runs by re-running `detect()` and the `remaining_options` logic, read-only, on the exact input of every logged iteration (the eval partition materialised with that iteration's committed ops; nothing committed, so it equals the eval partition), under the same TaskSpec settings, with no pipeline change. Every (column, op) the audit log shows as evaluated appeared in that iteration's reconstructed offers, in all 12 runs, so the three-way split is reported. Notes: (1) a row is planner-miss if a reachable op was offered at any logged iteration but never evaluated; (2) for a Groq run that ended early on a planner or API error, an offered op that was never reached is counted as planner-miss, because the planner stage did not select it (the end reason is in section 3); (3) the `unclassified (error)` rule (the row's only entries are error entries) applied to no row.\n")
a("## 5. Other outcomes\n")
a("| Item | Result |\n|---|---|")
a("| Unexplained commits (commit on a column with no error cells; listed separately) | none |")
a("| Wrong-op commits (failure condition) | **0** |")
a("| Committed ops | none in any run |")
a("| Evaluation counts | rule: 16 per run in both datasets (budget exhausted). Groq: Marketing 5, 5, 16; Airbnb 11, 8, 3 (early ends, section 6). Aborted first attempt of Airbnb Groq 401: 0. |")
a("| Primary statistic | per-run Bonferroni (alpha / 16 look-backs = `MAX_ITERATIONS`), unchanged |")
a("| Secondary (across-dataset, information only) | family = 16 look-backs x 12 eval runs = 192; it can only flag commits, and there are none |")
a("| H3 (no harm) | vacuous: 0 committed ops (details below) |\n")
a("**H3.** Definition (amendment section E): every committed op has a final gate delta >= 0 on the held-out evaluation partition, and no collateral damage measurable against ground truth where G1 applies; a commit with negative delta on a partition not used for the commit decision is a failure of the gate. Evaluated as written: there are 0 committed ops, so the first clause is vacuously satisfied (0 of 0 violate) and no gate failure occurred. Not computable without making a choice: (a) the \"partition not used for the commit decision\" is not named (the pilot is declared a pipeline check only, and the eval partition is where the commit decision is made), so no out-of-decision delta was computed; (b) \"ground truth where G1 applies\" is not defined in the amendment text, and there is no committed repair to compare in any case. Nothing was chosen for those two parts.\n")
a("## 6. Errors and incomplete runs (verbatim)\n")
a("- **Marketing Groq 401 and 402**, iteration 6: `Planner chose (Person, fill_mode), which is not in remaining_options: [...]`. The strict JSON schema constrains column and operation independently, so Groq proposed a pair that is not on the menu (Person/fill_mode was already evaluated at iteration 5). The unchanged pipeline treats a planner exception as the end of the run. 5 evaluations each.")
a("- **Marketing Groq 403**: completed 16 evaluations, no error.")
for seed in (401, 402, 403):
    r = get("Airbnb", "groq", seed)
    e = r["errors"][0]
    a(f"- **Airbnb Groq {seed}**, iteration {e['iteration']}: `{e['error']}` ({r['n_evaluated']} evaluations before it).")
a("- **Aborted first attempt, Airbnb Groq 401** (kept as `Documents/real_results/audit/ABORTED_attempt1_...json`): `Error code: 429 ... Rate limit reached for model openai/gpt-oss-20b ... on tokens per minute (TPM): Limit 8000, Used 7585, Requested 4861`, at iteration 1, 0 evaluations, no result. Cause: I launched the four dataset-planner jobs in parallel and the two Groq jobs shared the organisation's per-minute token limit; the existing client retry did not wait long enough. I stopped the two parallel Groq processes and ran the Groq jobs one after another instead: Marketing Groq 403 (it had been killed mid-run, so it was started again from the start) and Airbnb Groq 401, 402, 403. That decision was made before any result of these runs was seen. The re-run of Airbnb Groq 401 then ended on the 400 error above. The aborted attempt and the parallel start spent part of the Groq daily token budget and may have contributed to the daily-limit (TPD) error that ended Airbnb Groq 403; that attribution is a judgement, not verified.")
a("- The Explain step was skipped for the two pilot runs (console `UnicodeEncodeError`); the audit logs are unaffected. Eval runs used `PYTHONIOENCODING=utf-8` and have Explain reports in `aeterna_qa/logs/study_real/`. Explain LLM notes were switched off for these runs (`EXPLAIN_USE_LLM = False`, to avoid extra Groq calls); the verdicts are deterministic.")
a("- Cosmetic, from existing code: the console baseline line prints \"exploratory data\" because the TaskSpec path passes `task_meta`; the audit `scenario` and label are the real-data ones.\n")
a("## 7. Planner comparison (exploratory, efficiency only)\n")
a("Rule and Groq gave the same final outcome (nothing committed) in every run. The rule planner used its full 16-evaluation budget every time; Groq runs used fewer evaluations only because most ended on errors, so no efficiency claim is made. Which rows were reached differs by planner and, for Groq, by seed (section 8). No accuracy claim.\n")
a("## 8. Full per-row table\n")
a("Codes: **H** hit; **ok** correct no-commit (expected no commit, none occurred); **X** commit on an expected-no-commit row; misses: **D** detector-miss, **P** planner-miss, **G** gate-reject, **U** unclassified (error), **N** not separable. Columns: rule seeds 401/402/403, then Groq seeds 401/402/403. \"Reachable ops\" are those of the signed file; any one committing is a hit.\n")
a("| Dataset | Column | Error type | Reachable ops | Expected | Rule 401 | 402 | 403 | Groq 401 | 402 | 403 |\n|---|---|---|---|---|---|---|---|---|---|---|")
for ds in ("Marketing", "Airbnb"):
    base = get(ds, "rule", 401)["rows"]
    for i, x in enumerate(base):
        cells = [code(get(ds, pl, s)["rows"][i]) for pl in ("rule", "groq") for s in (401, 402, 403)]
        a(f"| {ds} | {x['col']} | {x['typ']} | {', '.join(x['reachable'])} | {x['expected']} | " + " | ".join(cells) + " |")
a("")
a("## 9. Exploratory-run disclosure\n")
a("On 2026-11-01, before the amendment was signed, the unchanged pipeline was run once on each full dataset for pipeline acceptance (P4): Marketing (`--positive 0`, rule planner) and Airbnb (`--positive Y`), scenario label `exploratory`. They are not study results and no expectation was derived from them. Outcomes as recorded then: Marketing, 16 of 16 candidate evaluations rolled back, nothing committed; Airbnb, no commits, `fill_median` / `fill_mean` delta +0.0000. The registered runs here are separate runs on the eval partition.\n")
a("## 10. Honest limits\n")
a("- Expectations are derived from CleanML dirty-vs-clean diffs (and the dirty file's NaN cells), not from the real-world ground truth. \"Expected commit\" means CleanML shows error cells there, not that repairing them helps a downstream LR.")
a("- Scoring is per run under per-run Bonferroni (alpha / 16). With LR + Brier on these tables no repair cleared the bar, so H2 is 0 for both datasets. That is a statement about the gate and detectors on these tables, not evidence that the defects are harmless or that the gate is right.")
a("- Many Airbnb misses are detector-misses and planner-misses: the detectors never offered some reachable ops, and a 16-iteration budget cannot reach 55 expected-commit rows. Both are properties of the unchanged agent.")
a("- Groq runs ended early on planner or API errors in 5 of 6 runs, so the Groq vs rule comparison is exploratory and incomplete.")
a("- `Ethnic` in Marketing is a sensitive attribute; no per-group result is reported. The Airbnb file has 33,145 rows versus 42,492 in the CleanML description; the file was used as is.")
a("- Small N (2 datasets), one split seed, no family-wide correction in the commit rule.\n")
a("## 11. Credit and licence\n")
a("- Marketing: CleanML benchmark (Li et al., https://arxiv.org/abs/1904.09483; https://github.com/chu-data-lab/CleanML); data originally Impact Resources, Inc. (Columbus, OH, 1987). No licence stated: academic use only, not redistributed, no per-ethnicity findings.")
a("- Airbnb data: Inside Airbnb (CC BY), via CleanML. The data files are in the gitignored `Dataset/real/` and are not committed.")
(ROOT / "Documents/RESULTS_REAL.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
print("written", len(L))
