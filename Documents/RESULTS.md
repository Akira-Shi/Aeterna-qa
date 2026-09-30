# AETERNA-QA study results (synthetic corruption on Adult)

Append-only; see PREREGISTRATION.md.

## Pilot (frozen before eval)

Pilot rows 6034, eval rows 24128, noise scale 0.500. Gate: Brier, LR.

| Scenario | Rate | Pilot effect | SE | Bar | MDE (scaled) | MDE (unscaled) |
|---|---|---|---|---|---|---|
| C1 | 10% | +0.0019 | 0.0006 | 0.0021 | 0.0013 | 0.0026 |
| C1 | 30% | +0.0019 | 0.0008 | 0.0025 | 0.0016 | 0.0032 |
| C1 | 60% | +0.0021 | 0.0006 | 0.0021 | 0.0013 | 0.0026 |
| C2 | 5% | +0.0010 | 0.0006 | 0.0018 | 0.0012 | 0.0023 |
| C2 | 15% | +0.0010 | 0.0006 | 0.0018 | 0.0012 | 0.0023 |
| C2 | 30% | +0.0009 | 0.0005 | 0.0017 | 0.0011 | 0.0022 |
| C3 | 3% | +0.0009 | 0.0006 | 0.0019 | 0.0012 | 0.0024 |
| C3 | 8% | +0.0009 | 0.0005 | 0.0016 | 0.0010 | 0.0020 |
| C3 | 15% | +0.0008 | 0.0005 | 0.0015 | 0.0009 | 0.0019 |
| C4 | 30% | +0.0008 | 0.0005 | 0.0017 | 0.0011 | 0.0021 |

Expected outcomes for the eval run (set by the pilot, not by hope):

- C1 at 10%: COMMIT normalize_categories on occupation
- C2 at 30%: NO COMMIT
- C3 at 15%: NO COMMIT
- C4 at 30%: NO COMMIT

## Pilot (frozen before eval) -- added scenarios ['C5']

Pilot rows 6034, eval rows 24128, noise scale 0.500. Gate: Brier, LR.

| Scenario | Rate | Pilot effect | SE | Bar | MDE (scaled) | MDE (unscaled) |
|---|---|---|---|---|---|---|
| C5 | 1% | +0.0120 | 0.0017 | 0.0054 | 0.0034 | 0.0069 |
| C5 | 3% | +0.0120 | 0.0017 | 0.0053 | 0.0034 | 0.0067 |
| C5 | 6% | +0.0115 | 0.0016 | 0.0053 | 0.0033 | 0.0067 |

Expected outcomes for the eval run (set by the pilot, not by hope):

- C5 at 1%: COMMIT sentinel_to_median on capital.gain

## Column headroom (pilot partition)

Gate-score loss (Brier, LR) if the column is destroyed, pilot partition. Positive = column carries signal.

| Column | Ceiling |
|---|---|
| capital.gain | +0.01212 |
| occupation | +0.00295 |
| capital.loss | +0.00173 |
| hours.per.week | +0.00143 |
| age | +0.00096 |
| workclass | +0.00072 |
| sex | +0.00010 |
| relationship | +0.00006 |
| fnlwgt | +0.00004 |
| education.num | -0.00000 |
| race | -0.00008 |
| marital.status | -0.00022 |
| education | -0.00050 |
| native.country | -0.00154 |

## Eval (offline planner)

| Scenario | Seed | Rate | Expected | Committed | Outcome | Gate inj -> final (clean) | Delta 95% CI | Recovery | Blind-clean gate | Restored / MAE | Collateral cells | Rows dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 201 | 10% | commit | none | miss | -0.1051 -> -0.1051 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1054 | 0.000 | 0 | 0 |
| C1 | 202 | 10% | commit | none | miss | -0.1050 -> -0.1050 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1054 | 0.000 | 0 | 0 |
| C1 | 203 | 10% | commit | {'occupation': 'normalize_categories'} | hit | -0.1052 -> -0.1046 (-0.1046) | [+0.0003, +0.0010] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C2 | 201 | 30% | none | {'age': 'rescale_units'} | false_commit | -0.1058 -> -0.1046 (-0.1046) | [+0.0006, +0.0018] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C2 | 202 | 30% | none | {'age': 'rescale_units'} | false_commit | -0.1057 -> -0.1046 (-0.1046) | [+0.0006, +0.0017] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C2 | 203 | 30% | none | {'age': 'rescale_units'} | false_commit | -0.1058 -> -0.1046 (-0.1046) | [+0.0006, +0.0019] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C3 | 201 | 15% | none | {'age': 'sentinel_to_median'} | false_commit | -0.1058 -> -0.1046 (-0.1046) | [+0.0006, +0.0017] | 0.96 | -0.1054 | MAE 10.74 (median ref 10.74, unrepaired 960.79) | 0 | 0 |
| C3 | 202 | 15% | none | {'age': 'sentinel_to_median'} | false_commit | -0.1058 -> -0.1047 (-0.1046) | [+0.0005, +0.0016] | 0.89 | -0.1055 | MAE 10.70 (median ref 10.70, unrepaired 960.49) | 0 | 0 |
| C3 | 203 | 15% | none | none | correct_rollback | -0.1058 -> -0.1058 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1056 | MAE 961.08 (median ref 10.49, unrepaired 961.08) | 0 | 0 |
| C4 | 201 | 30% | none | {'native.country': 'normalize_categories'} | false_commit | -0.1054 -> -0.1046 (-0.1046) | [+0.0004, +0.0014] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C4 | 202 | 30% | none | {'native.country': 'normalize_categories'} | false_commit | -0.1055 -> -0.1046 (-0.1046) | [+0.0004, +0.0014] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C4 | 203 | 30% | none | none | correct_rollback | -0.1058 -> -0.1058 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1054 | 0.000 | 0 | 0 |
| C5 | 201 | 1% | commit | {'capital.gain': 'sentinel_to_median'} | hit | -0.1138 -> -0.1046 (-0.1046) | [+0.0079, +0.0103] | 0.99 | -0.1045 | MAE 621.62 (median ref 621.62, unrepaired 9999377.38) | 0 | 0 |
| C5 | 202 | 1% | commit | {'capital.gain': 'sentinel_to_median'} | hit | -0.1138 -> -0.1046 (-0.1046) | [+0.0079, +0.0104] | 0.99 | -0.1045 | MAE 391.25 (median ref 391.25, unrepaired 9999607.75) | 0 | 0 |
| C5 | 203 | 1% | commit | {'capital.gain': 'sentinel_to_median'} | hit | -0.1138 -> -0.1047 (-0.1046) | [+0.0079, +0.0103] | 0.99 | -0.1046 | MAE 1064.76 (median ref 1064.76, unrepaired 9998934.24) | 0 | 0 |

Counts: {'miss': 2, 'hit': 4, 'false_commit': 7, 'correct_rollback': 2}. Reported as k/n per scenario in the table; no pooling of positive and negative scenarios.

## Confirmation on the pilot partition (fresh seed)

- C2 (ops {'age': 'rescale_units'}) on pilot partition, seed 301: {'rows_dropped': 0, 'collateral_cells': 0, 'injected_rows': 1810, 'injected_rows_present': 1810, 'restored_share': 1.0}
- C3 (ops {'age': 'sentinel_to_median'}) on pilot partition, seed 301: {'rows_dropped': 0, 'collateral_cells': 0, 'injected_rows': 905, 'injected_rows_present': 905, 'mae': 10.758011049723757, 'mae_median_reference': 10.758011049723757, 'mae_unrepaired': 960.232044198895}
- C4 (ops {'native.country': 'normalize_categories'}) on pilot partition, seed 301: {'rows_dropped': 0, 'collateral_cells': 0, 'injected_rows': 1766, 'injected_rows_present': 1766, 'restored_share': 1.0}
- C5 (ops {'capital.gain': 'sentinel_to_median'}) on pilot partition, seed 301: {'rows_dropped': 0, 'collateral_cells': 0, 'injected_rows': 60, 'injected_rows_present': 60, 'mae': 584.65, 'mae_median_reference': 584.65, 'mae_unrepaired': 9999414.35}

## Reading of the results (written after eval; the tables above are the record)

Counts against the pre-registered expectations (LR, Brier gate, offline rule planner, 3 eval seeds per scenario): HIT 4 (C1 1/3, C5 3/3), MISS 2 (C1 2/3), CORRECT ROLLBACK 2 (C3 1/3, C4 1/3), FALSE COMMIT 7 (C2 3/3, C3 2/3, C4 2/3). By the registered rule these 7 are false commits and they are reported as such.

What the label hides: in all 11 commits the committed op was the correct repair for a real injected defect. Zero wrong-op commits, zero collateral cells, zero rows dropped. Restoration was 100% for C1, C2, C4 (exact / within 0.5); the sentinel repairs (C3, C5) replace the code with the training median, so their error equals the median-reference error by construction, i.e. they remove the code but cannot recover the true value. Recovery of the gate loss was 0.89-1.00 in every commit.

Why the pilot expectations were wrong for C2/C3/C4 and C1: the pilot estimated effects on 6,034 rows and scaled the bar by sqrt(n_pilot/n_eval) = 0.5; the eval bars came out near 0.0009 and true eval effects were 0.0011-0.0012 for age defects (just above) and 0.0009 for the native.country "decoy" (also above, so it was never harmless on this partition), while C1 at 10% cost only about 0.0005-0.0006 on eval against 0.0019 in the pilot (below the bar in 2 of 3 seeds). The pilot SE is a within-partition fold SE and does not capture partition-to-partition variation. Nothing was re-run or re-tuned.

Baselines: the blind "clean everything the detectors flag" baseline (capital.gain, occupation, dedupe, hours clip) scored -0.1054 on C1-C4, worse than doing nothing on C1 and worse than the agent everywhere except C5, where it matched the agent to within 0.0001. The agent's committed repairs reached the clean-data score (-0.1046) in every commit.

Not established: any result with the Groq planner (only the rule planner was run); any planner ablation; behaviour on real dirty data. The real-`?` check (nothing committed) is recorded in PREREGISTRATION section 12.

## Eval (groq planner)

| Scenario | Seed | Rate | Expected | Committed | Outcome | Gate inj -> final (clean) | Delta 95% CI | Recovery | Blind-clean gate | Restored / MAE | Collateral cells | Rows dropped |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 201 | 10% | commit | none | miss | -0.1051 -> -0.1051 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1054 | 0.000 | 0 | 0 |
| C1 | 202 | 10% | commit | none | miss | -0.1050 -> -0.1050 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1054 | 0.000 | 0 | 0 |
| C1 | 203 | 10% | commit | {'occupation': 'normalize_categories'} | hit | -0.1052 -> -0.1046 (-0.1046) | [+0.0003, +0.0010] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C2 | 201 | 30% | none | {'age': 'rescale_units'} | false_commit | -0.1058 -> -0.1046 (-0.1046) | [+0.0006, +0.0018] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C2 | 202 | 30% | none | {'age': 'rescale_units'} | false_commit | -0.1057 -> -0.1046 (-0.1046) | [+0.0006, +0.0017] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C2 | 203 | 30% | none | {'age': 'rescale_units'} | false_commit | -0.1058 -> -0.1046 (-0.1046) | [+0.0006, +0.0019] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C3 | 201 | 15% | none | {'age': 'sentinel_to_median'} | false_commit | -0.1058 -> -0.1046 (-0.1046) | [+0.0006, +0.0017] | 0.96 | -0.1054 | MAE 10.74 (median ref 10.74, unrepaired 960.79) | 0 | 0 |
| C3 | 202 | 15% | none | {'age': 'sentinel_to_median'} | false_commit | -0.1058 -> -0.1047 (-0.1046) | [+0.0005, +0.0016] | 0.89 | -0.1055 | MAE 10.70 (median ref 10.70, unrepaired 960.49) | 0 | 0 |
| C3 | 203 | 15% | none | none | correct_rollback | -0.1058 -> -0.1058 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1056 | MAE 961.08 (median ref 10.49, unrepaired 961.08) | 0 | 0 |
| C4 | 201 | 30% | none | {'native.country': 'normalize_categories'} | false_commit | -0.1054 -> -0.1046 (-0.1046) | [+0.0004, +0.0014] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C4 | 202 | 30% | none | {'native.country': 'normalize_categories'} | false_commit | -0.1055 -> -0.1046 (-0.1046) | [+0.0004, +0.0014] | 1.00 | -0.1054 | 1.000 | 0 | 0 |
| C4 | 203 | 30% | none | none | correct_rollback | -0.1058 -> -0.1058 (-0.1046) | [+0.0000, +0.0000] | 0.00 | -0.1054 | 0.000 | 0 | 0 |
| C5 | 201 | 1% | commit | {'capital.gain': 'sentinel_to_median'} | hit | -0.1138 -> -0.1046 (-0.1046) | [+0.0079, +0.0103] | 0.99 | -0.1045 | MAE 621.62 (median ref 621.62, unrepaired 9999377.38) | 0 | 0 |
| C5 | 202 | 1% | commit | {'capital.gain': 'sentinel_to_median'} | hit | -0.1138 -> -0.1046 (-0.1046) | [+0.0079, +0.0104] | 0.99 | -0.1045 | MAE 391.25 (median ref 391.25, unrepaired 9999607.75) | 0 | 0 |
| C5 | 203 | 1% | commit | {'capital.gain': 'sentinel_to_median'} | hit | -0.1138 -> -0.1047 (-0.1046) | [+0.0079, +0.0103] | 0.99 | -0.1046 | MAE 1064.76 (median ref 1064.76, unrepaired 9998934.24) | 0 | 0 |

Counts: {'miss': 2, 'hit': 4, 'false_commit': 7, 'correct_rollback': 2}. Reported as k/n per scenario in the table; no pooling of positive and negative scenarios.

## Planner comparison: Groq vs rule (added 2026-09-30 after the Groq eval)

Same 15 runs (5 scenarios x seeds 201-203), same gate, same eval partition. Outcomes were identical in 15/15 runs: same committed op or none, same registered label, final gate scores equal to 5 decimals. Efficiency: among the 11 runs that committed under both planners, the correct commit came on evaluation 1.0 (Groq) vs 1.55 (rule) on average; the rule planner always tries the real `capital.gain = 99999` value first, which is rejected. On the 4 runs where nothing committed, Groq used one more evaluation in 3 (C1 seeds 201 and 202, C4 seed 203: 7 vs 6) and the same number in 1 (C3 seed 203: 9 vs 9). Files: `logs/study/eval_groq.json`, `eval_groq_<scenario>_<seed>.txt`. Small sample; efficiency only. No claim that the LLM changes what gets committed.
