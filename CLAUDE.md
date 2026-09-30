# AETERNA-QA — Project State (as of 2026-09-30)

Capstone: closed-loop data-cleaning agent (detect → plan → execute → verify → rollback) that commits a repair only if a cross-validated gate says it helps. Owner: Akira. Claude acts as advisor/think tank: discuss before building, and update `Documents/Documentation.md` after every change.

## Completed
- **Evaluator (FROZEN):** fixed 5×3 CV folds, Nadeau-Bengio corrected SE, Bonferroni-corrected commit bar. LR (in-fold StandardScaler) is the study evaluator; RF is kept only to reproduce old numbers. Gate = **Brier**; F1 reported beside every decision. Leak tests pass. Any change needs a changelog entry and re-run of the leak tests.
- **Pipeline:** detectors → planner (Groq, menu-constrained) → executor → verify/rollback → audit log. Ops are fit on training rows only: fill_*, drop_rows, clip_outliers, fill_unknown, normalize_categories, sentinel_to_median, rescale_units. `ops_tests` passes.
- **Pre-registration:** signed v1 (`PREREGISTRATION.md`, append-only amendments in §12). Scenarios C1–C5 with injected damage, 20/80 pilot/eval split, manifest hidden from the planner.
- **Study results** (`RESULTS.md`, 24,128 eval rows, seeds 201–203):
  - Rule planner and Groq planner gave identical outcomes in 15/15 runs.
  - Registered labels: 4 hit, 2 miss, 2 correct rollback, 7 false commit.
  - All 11 commits used the correct repair; 0 wrong-op commits, 0 collateral cells, 0 rows dropped.
  - The false-commit labels come from mis-set pilot expectations. Nothing was re-tuned.
  - Groq reached the correct commit on evaluation 1.0 vs 1.55 for the rule planner. This is an efficiency claim only.
- **Real Adult (`?` values):** nothing commits, which matches ground truth.
- **Explain module:** deterministic verdict + verbatim planner reason + guarded Groq note, with `rich` console and HTML report.
- **Guide decisions:** a labelled synthetic positive control is acceptable, even as the end product. Retraction slide is not needed.

## Files
- **Code** (`aeterna_qa/modules/`): `audit, config, detectors, evaluator (frozen), evaluator_tests, executor, explain, injection, ops_tests, pipeline, planner, study`
- **Other code:** `_archive/` has old experiments and `_scratch/` has throwaway scripts. Neither is part of the pipeline.
- **Data:** `Dataset/adult.csv` and `aeterna_qa/data/adult.csv`
- **Outputs:** `aeterna_qa/outputs/adult_clean_[groq_]<scenario>_<seed>.csv` plus `.manifest.json`
- **Logs:** `aeterna_qa/logs/run_*.json`, `report_*.html`, and `logs/study/` (pilot, eval, eval_groq)
- **Docs** (`Documents/`): `Documentation.md` (changelog, source of truth), `PREREGISTRATION.md`, `RESULTS.md`, `BUILD_PLAN.md`, `README.md`, the two decks (`AETERNA_QA_50pct_Review.pptx`, `AETERNA_QA_Project_Proposal_Akira.pptx`)
- **Reference papers:** `Resources/` (DeepPrep, LLM agents for cleaning, iterative verification loops)
- **Secrets:** `.env` holds the Groq key. Never read, print or commit it.

## Tech stack
- Python 3.10/3.13, pandas ≥2, scikit-learn ≥1.4, python-dotenv, groq ≥0.11, rich ≥13
- Planner LLM: Groq free tier, `openai/gpt-oss-20b`
- Runs on the user's Windows machine (Groq key lives there). sklearn study runs can be done in a cloud workspace.
- Kaggle GPU: not needed so far.

## Pending (priority order)
1. **Check `committed_ops: None`:** every audit JSON shows it, including runs that committed. It may be stored elsewhere or may be a logging bug. Verify, because Explain's chain logic depends on it.
2. **Explain guard check:** confirm the Groq notes pass the number-check guard on real runs.
3. **Git:** the whole rebuild is uncommitted (only 2 pre-rebuild commits exist).
4. **Planner-critic add-on (Phase 7):** a pre-execution review step. The guide asked for one novel idea. Check Du et al. (arXiv:2305.14325) before calling it novel.
5. **Real dataset where cleaning measurably helps:** unresolved risk. All positive results are on damage we injected into one dataset.
6. **Minor:** demo date blank in `BUILD_PLAN.md`; `positive_control.py` doesn't call `audit`; IQR outlier detection is unreliable on skewed columns.

## Rules that stay on
- Label every synthetic result "synthetic" (banner, audit `scenario`, file names, report titles).
- Don't choose a scenario, metric or model after seeing its result without a written rule.
- Report RF and LR separately, never pooled. Report positive and negative scenarios as k/n, never pooled.
- Don't call the top-coded values `99999`, `99`, `90` "errors"; they are censored real values.
- Don't cite the retracted numbers: +0.0175 drop-rows gain, F1 ≈ 0.688, the "2.0× SE" threshold, `calculate_f1_cv`.
- The planner sees only detector output, never the injection manifest.
