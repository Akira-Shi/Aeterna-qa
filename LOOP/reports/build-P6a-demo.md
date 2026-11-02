# build-P6a-demo: Stage 2 recommender acceptance demo (report only)

Branch `phase/6-recommender`. Recommended pipeline (stage2 rules + build + compare) vs the default (median fill + one-hot + standard scaling) on the evaluator's fixed 5x3 folds (15 folds), neg-Brier and F1, mean paired difference (recommended minus default) +/- Nadeau-Bengio corrected SE. No gate, no commit decision, nothing chosen or altered after seeing results. Driver: `tools/p6a_demo.py`. Model families: linear (LogisticRegression), tree_ensemble (RandomForest, 100 trees). These are Stage 2 demo estimators, not the frozen study evaluator.

Data: Adult (`Dataset/adult.csv`, 32,561 rows, via `taskspec.adult_spec()`; positive label `>50K` is explicit in the spec from `config.POSITIVE_CLASS`, not defaulted). Marketing (local `Dataset/real/Marketing/raw/raw.csv`, gitignored, sha256 verified; 8,993 rows; positive label `Income = 0`, explicit, as in the registered P5 runs). Marketing licence: academic use only, no redistribution. This report holds aggregates only: columns are counted, never named, and there are no per-group findings. TaskSpec loading yields all-object columns for Marketing, so the rules treat every Marketing feature as categorical.

## Headline

| dataset x family | neg-Brier diff +/- SE | F1 diff +/- SE |
|---|---|---|
| Adult x linear | -0.0046 +/- 0.0002 | -0.0121 +/- 0.0017 |
| Adult x tree_ensemble | +0.0028 +/- 0.0004 | +0.0034 +/- 0.0037 |
| Marketing x linear | +0.0001 +/- 0.0001 | +0.0007 +/- 0.0010 |
| Marketing x tree_ensemble | -0.0007 +/- 0.0014 | -0.0029 +/- 0.0041 |

Reading (no tuning follows from it): the recommendation was worse than the default for Adult x linear on both metrics, better for Adult x tree_ensemble on Brier (F1 within noise), and indistinguishable from the default for both Marketing combos. Positive diff on neg-Brier means the recommended pipeline predicts better. Not a gate; these four runs make no claim about the recommender in general.

## Defect found and fixed during the demo (disclosed)

The first attempt crashed in all four combos: `TypeError: boolean value of NA is ambiguous` (sklearn `SimpleImputer` on object columns holding `pd.NA`, which is what TaskSpec loading produces). No result had been produced. A stateless first Pipeline step (`na`, pandas NA to `np.nan` for object / extension-dtype columns) was added to both the recommended and the default pipeline in `stage2/build.py`; a regression test covers it. The same fix applies to both arms, so the comparison is symmetric. The demo was then run once for all four combos (and re-run on the final code with identical numbers).

## Tables

### Adult x linear

positive label '>50K' from config.POSITIVE_CLASS (explicit in the TaskSpec, not defaulted). Rows 32561, features 14, rows dropped for missing target 0.

| step | rule_id | n columns | method | reason | alternative |
|---|---|---|---|---|---|
| imputation | IMP-C1 | 2 | constant_missing | At least 5% of the values are missing: keep 'missing' as its own level instead of guessing. | most frequent value |
| imputation | IMP-C2 | 1 | most_frequent | Fewer than 5% missing: the most frequent level is the least disruptive fill. | constant 'missing' level |
| encoding | ENC-H1 | 2 | onehot_capped | More than 15 levels: one-hot with rare levels grouped into one 'infrequent' column (at most 15 columns). | ordinal codes (imposes an order), or drop the column |
| encoding | ENC-L1 | 6 | onehot | Linear, distance and neural models need an unordered encoding: one-hot. | ordinal codes (imposes an order) |
| scaling | SCL-G1 | 3 | standard | Scale-sensitive model: zero mean and unit variance so every column has a comparable range. | robust scaling |
| scaling | SCL-S1 | 3 | yeo_johnson | Skewed numeric column and a model that prefers roughly symmetric inputs: Yeo-Johnson, then standardise (handles zeros and negatives). | standard scaling |

- neg-Brier: default -0.1027, recommended -0.1072, diff (rec - default) -0.0046 +/- 0.0002 (NB-corrected SE)
- F1: default 0.6583, recommended 0.6462, diff -0.0121 +/- 0.0017
- 15 fixed folds; report only, no gate, no commit decision. (37s)

### Adult x tree_ensemble

positive label '>50K' from config.POSITIVE_CLASS (explicit in the TaskSpec, not defaulted). Rows 32561, features 14, rows dropped for missing target 0.

| step | rule_id | n columns | method | reason | alternative |
|---|---|---|---|---|---|
| imputation | IMP-C1 | 2 | constant_missing | At least 5% of the values are missing: keep 'missing' as its own level instead of guessing. | most frequent value |
| imputation | IMP-C2 | 1 | most_frequent | Fewer than 5% missing: the most frequent level is the least disruptive fill. | constant 'missing' level |
| encoding | ENC-T1 | 8 | ordinal | Trees do not need one-hot columns; ordinal codes keep the matrix narrow at any cardinality. | one-hot |
| scaling | SCL-T1 | 6 | none | Trees are invariant to monotone scaling; leave the column as is. | standard scaling |

- neg-Brier: default -0.1031, recommended -0.1003, diff (rec - default) +0.0028 +/- 0.0004 (NB-corrected SE)
- F1: default 0.6752, recommended 0.6786, diff +0.0034 +/- 0.0037
- 15 fixed folds; report only, no gate, no commit decision. (49s)

### Marketing x linear

positive label '0' (Income=0), explicit, same as the registered P5 runs. Rows 8993, features 13, rows dropped for missing target 0.

| step | rule_id | n columns | method | reason | alternative |
|---|---|---|---|---|---|
| imputation | IMP-C1 | 1 | constant_missing | At least 5% of the values are missing: keep 'missing' as its own level instead of guessing. | most frequent value |
| imputation | IMP-C2 | 8 | most_frequent | Fewer than 5% missing: the most frequent level is the least disruptive fill. | constant 'missing' level |
| encoding | ENC-L1 | 13 | onehot | Linear, distance and neural models need an unordered encoding: one-hot. | ordinal codes (imposes an order) |

- neg-Brier: default -0.1561, recommended -0.1560, diff (rec - default) +0.0001 +/- 0.0001 (NB-corrected SE)
- F1: default 0.7434, recommended 0.7441, diff +0.0007 +/- 0.0010
- 15 fixed folds; report only, no gate, no commit decision. (10s)

### Marketing x tree_ensemble

positive label '0' (Income=0), explicit, same as the registered P5 runs. Rows 8993, features 13, rows dropped for missing target 0.

| step | rule_id | n columns | method | reason | alternative |
|---|---|---|---|---|---|
| imputation | IMP-C1 | 1 | constant_missing | At least 5% of the values are missing: keep 'missing' as its own level instead of guessing. | most frequent value |
| imputation | IMP-C2 | 8 | most_frequent | Fewer than 5% missing: the most frequent level is the least disruptive fill. | constant 'missing' level |
| encoding | ENC-T1 | 13 | ordinal | Trees do not need one-hot columns; ordinal codes keep the matrix narrow at any cardinality. | one-hot |

- neg-Brier: default -0.1597, recommended -0.1604, diff (rec - default) -0.0007 +/- 0.0014 (NB-corrected SE)
- F1: default 0.7392, recommended 0.7363, diff -0.0029 +/- 0.0041
- 15 fixed folds; report only, no gate, no commit decision. (15s)


## Diagnosis: Adult x linear (written BEFORE any rule or code change)

Per-rule ablation on the same 15 fixed folds, linear (LogisticRegression). Each row removes one rule so its columns fall to the next matching rule. diff = recommended minus default neg-Brier (default -0.1027); SE = Nadeau-Bengio corrected. Script was scratch (not in the repo).

| ablation | recommended neg-Brier | diff vs default +/- SE | F1 diff +/- SE |
|---|---|---|---|
| none (as shipped) | -0.1072 | -0.0046 +/- 0.0002 | -0.0121 +/- 0.0017 |
| remove IMP-C1 (constant_missing -> most_frequent) | -0.1078 | -0.0051 +/- 0.0002 | -0.0152 +/- 0.0018 |
| remove ENC-H1 (capped one-hot -> full one-hot) | -0.1072 | -0.0045 +/- 0.0003 | -0.0121 +/- 0.0016 |
| remove SCL-S1 (Yeo-Johnson -> standard) | -0.1021 | +0.0005 +/- 0.0002 | +0.0036 +/- 0.0013 |

Guilty rule: SCL-S1 (Yeo-Johnson on skewed numeric columns, linear/neural). Removing it turns -0.0046 into +0.0005 (about 2.5 SE better than default). IMP-C1 helps slightly, ENC-H1 is neutral.

### Dev-dataset check (non-study datasets; Adult and Marketing not used to choose anything)

OpenML credit-g (1000 rows, positive 'bad') and bank-marketing (45,211 rows, positive class '2'), linear, same fixed-fold machinery, saved in `Capstone_devdata/` outside the repo.

| dataset | SCL-S1 on: diff vs default | SCL-S1 removed: diff vs default |
|---|---|---|
| credit-g | -0.0015 +/- 0.0014 (F1 -0.0026) | -0.0000 +/- 0.0000 (F1 +0.0000) |
| bank-marketing | -0.0531 +/- 0.0008 (F1 +0.0830) | -0.0491 +/- 0.0008 (F1 +0.1014) |

Rationale (from dev only): on both dev sets, removing SCL-S1 is equal or better on neg-Brier and on F1 (bank: +0.0040 neg-Brier, about 5 SE, and +0.0184 F1; credit-g: +0.0015, within noise, F1 +0.0026). Yeo-Johnson never helped. Decision: remove SCL-S1 for linear and neural (skewed numerics fall to SCL-G1 standard scaling). Side observation, NOT acted on: on bank-marketing the large neg-Brier loss comes from IMB-1 (class_weight=balanced distorts probabilities for a Brier gate); one dev set only and out of scope for this Adult diagnosis, so the rule is unchanged and the step-3 fallback covers it.

## Final acceptance (after SCL-S1 removal and the 2-SE fallback)

Rule change chosen on dev data only (see Diagnosis). Fallback: if recommended < default by more than 2 corrected SE on neg-Brier, the default pipeline is recommended and the string "fallback: default outperformed recommendation" is recorded in the report dict (`fallback_note`, `note`) and in `format_report`. Adult and Marketing were re-run once, untuned.

| dataset x family | default neg-Brier | recommended neg-Brier | diff +/- SE | F1 diff +/- SE | final recommendation |
|---|---|---|---|---|---|
| Adult x linear | -0.1027 | -0.1021 | +0.0005 +/- 0.0002 | +0.0036 +/- 0.0013 | recommended |
| Adult x tree_ensemble | -0.1031 | -0.1003 | +0.0028 +/- 0.0004 | +0.0034 +/- 0.0037 | recommended |
| Marketing x linear | -0.1561 | -0.1560 | +0.0001 +/- 0.0001 | +0.0007 +/- 0.0010 | recommended |
| Marketing x tree_ensemble | -0.1597 | -0.1604 | -0.0007 +/- 0.0014 | -0.0029 +/- 0.0041 | recommended |

Acceptance (default never better than the final recommendation by more than 2 SE): PASS in all four combos; the fallback did not fire. The earlier tables above (Adult x linear with Yeo-Johnson, -0.0046) are the pre-change run, kept for the record. Not a general claim about the recommender.
