# build-demo-D1 (labelled SYNTHETIC DEMO; not a study result)

## Spec (declared in Documentation.md before the run)
Eval partition (24,128 rows), injection seed 201, planner Groq openai/gpt-oss-20b:
1. capital.gain sentinel 9999999 @2% -> sentinel_to_median
2. capital.loss sentinel 9999999 @3% -> sentinel_to_median
3. hours.per.week mixed_units x12 @30% -> rescale_units
4. occupation category_variants @60% -> normalize_categories

## Files
- new: aeterna_qa/modules/demo.py, aeterna_qa/modules/demo_tests.py
- edited: aeterna_qa/modules/pipeline.py (optional `scenario_name`, CLI --scenario/--seed), Documents/Documentation.md (spec + changelog)
- outputs: aeterna_qa/logs/run_20260930T113058Z.json, report_run_20260930T113058Z.html, aeterna_qa/outputs/adult_clean_groq_D1_201.csv + .manifest.json
- untouched: evaluator*, PREREGISTRATION, config, study, injection, C1-C5, models, STATE.json

## Run (python -m modules.pipeline --scenario D1 --seed 201)
First attempt crashed with UnicodeEncodeError (cp1252 console vs non-breaking hyphen in a Groq reason) at iteration 2 before any result; re-run with PYTHONIOENCODING=utf-8, same spec/seed.
committed_ops per iteration (pre-evaluation set): it1 {} occupation; it2 {} capital.loss; it3 {occupation, capital.loss} capital.gain; it4 all three, dedupe_rows; it5 error (no options).
| Iter | Tested | Delta | Bar | Outcome |
|---|---|---|---|---|
| 1 | occupation normalize_categories | +0.0005 | 0.0006 | staged |
| 2 | +capital.loss sentinel_to_median | +0.0015 (chain) | 0.0008 | COMMITTED chain |
| 3 | capital.gain sentinel_to_median | +0.0094 | 0.0019 | COMMITTED |
| 4 | dedupe_rows | -0.0000 | 0.0000 | dropped |
Final neg-Brier -0.1171 -> -0.1062 (F1 0.6171 -> 0.6579). 3 columns committed, 3/4 answer-key hits; hours.per.week undetected (find_unit_shift None) so never proposed. Not retuned.
Grading: capital.gain/loss MAE equals median reference (expected), occupation restored 0.9997, 0 rows dropped.

## Tests
frozen_check exit 0; ops_tests, evaluator_tests (ALL PASS), explain_tests, demo_tests all pass.
