# AETERNA-QA v2 — phase prompts (copied from the Claude Project, 2026-11-01)

Done: P0, P1 (v1.1), P2 (NOVELTY.md), P3 draft v2. Remaining phases below.

## P4 — Any-CSV TaskSpec + sandbox runner [PLAN]
Branch phase/4-taskspec. Goal: pipeline runs on any CSV.
- Add modules/taskspec.py: TaskSpec(path, target, task_type in {binary, multiclass, regression}, positive_label, model_family, id_columns, drop_columns).
- Replace Adult-specific assumptions in detectors, planner, executor, pipeline with TaskSpec fields.
- config.py and study.py are WATCHED: list the exact edits and wait for Akira's OK before touching them.
- Gate stays LR + Brier. If task_type != binary, Stage 1 runs detection only and reports "gate not supported". Do not invent a gate.
- Sandbox runner: `python -m aeterna_qa.run --csv <path> --target <col> [--task binary] [--groq]`. Inputs in Dataset/sandbox/ (gitignored). Audit scenario = "exploratory"; outputs/logs prefixed exploratory_. Exploratory runs are never cited as results.
- Validate before running: target exists; binary target has exactly 2 classes; warn on >50 MB, ID-like columns, columns >40% missing.
- Accept when: frozen_check exit 0; tests/test_reproduce_v1.py shows the Adult study reproduces RESULTS.md exactly; sandbox runner works on one non-Adult CSV (use the Marketing dataset from P3, exploratory only).
- Commit per logical step. Tag v2-p4 when accepted (the amendment cites this tag).

## P5 — Real-data evaluation (after Akira signs the amendment)
Branch phase/5-real-eval.
- Append the signed amendment to PREREGISTRATION.md §12 (append-only row with the expected-outcome file hash).
- Run the study on the selected datasets with the frozen evaluator, seeds 401-403, both planners.
- Write Documents/RESULTS_REAL.md: k/n per dataset, LR only, never pooled with synthetic; unexplained commits reported separately; any wrong-op commit = failure.
- Commit, show Akira the results, then merge and tag v1.2-real.

## P6a — Stage 2 rule engine [PLAN]
Branch phase/6-stage2. Build aeterna_qa/stage2/ (no LLM in this step):
- rules.py: deterministic table (task_type, model_family, column profile) -> steps for imputation, encoding, scaling/transforms, imbalance. Families: linear, tree_ensemble, distance, neural. Each step stores rule_id, reason, alternative.
- build.py: unfitted sklearn Pipeline/ColumnTransformer; fit on training rows only; save via joblib.
- compare.py: recommended vs default (median fill + one-hot + scale) on the evaluator's 5x3 folds (read-only import). Report mean diff ± corrected SE. Report only, no gate.
- Unsupported model -> nearest family with a warning, else raise UnsupportedModel.
- Tests: tests/test_stage2_rules.py covering every family x task type.

## P6b — Intent parser + audit
- stage2/parse_intent.py: Groq via the existing config path turns free text into TaskSpec JSON restricted to the allowed enums. Return spec + per-field confidence. Nothing runs until the user confirms.
- List-picker path builds the same TaskSpec with no LLM.
- stage2/explain_pipeline.py: LLM explanation passed through Explain's guard.
- Audit: each Stage 2 step logs decided_by (rule | user_override), rule_id, user_edit.
- Tests mock Groq. Never read .env. Merge, tag v2.0-core.

## P7 — FastAPI backend [PLAN]
Branch phase/7-api. FastAPI app in aeterna_qa/api/:
- POST /datasets (CSV upload -> profile + columns); POST /taskspec/parse
- POST /jobs/stage1; GET /jobs/{id} (status, progress); GET /jobs/{id}/stage1
- POST /jobs/{id}/stage2/suggest; POST /jobs/{id}/stage2/approve
- GET /jobs/{id}/artifacts (cleaned CSV, pipeline.joblib, report.html, audit.json, 20-row before/after preview)
- Background jobs with a SQLite job store. No Redis/Celery (Windows). CSV only, size limit, Pydantic schemas. Tests with TestClient.

## P8 — Web frontend [PLAN]
Enable first: /plugin enable frontend-design@claude-plugins-official
Branch phase/8-web. Use the frontend-design skill.
- web/ with Vite + React + TypeScript, plain CSS. Steep style (light, serif headings, peach accent); reuse the Explain report's tokens.
- Screens: 1 Upload; 2 Task (list picker | free text -> parsed spec to confirm); 3 Stage 1 (per repair: verdict, effect ± SE, committed/rolled back, plain reason); 4 Stage 2 (per step: rule, reason, alternative, accept/edit); 5 Download.
- Poll job progress. No synthetic banner in the UI (decision 2026-10-04).
- Playwright screenshots at desktop and 390px. Commit per screen.
Afterwards: /plugin disable frontend-design@claude-plugins-official

## P9 — Release
Branch phase/9-release.
- Code-review plugin on the diff since v1-study-frozen; fix real issues only.
- Playwright end-to-end: Adult + one real dataset through all 5 screens.
- Update README (Windows run steps), Documentation.md, BUILD_PLAN.md (ask Akira for the demo date). List deck slides needing changes; do not edit .pptx.
- Merge, tag v2.0.

## Testing tiers
| Tier | Where | Ground truth | Citable? |
|---|---|---|---|
| Exploratory | Dataset/sandbox/, sandbox runner | none | no |
| Synthetic | injection.py | manifest | yes, labelled synthetic, pre-registered |
| Real | Dataset/real/ (CleanML) | dirty-vs-clean diff | yes, only after §12 amendment |

## Cut line
Drop P6b first (keep the list picker), then trim P8 to 3 screens. Never drop P3 or P5.
