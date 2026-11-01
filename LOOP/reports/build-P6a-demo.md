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

