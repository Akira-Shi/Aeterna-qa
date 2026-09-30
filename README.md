# AETERNA-QA

A data-cleaning agent that has to **prove** a fix helps before it keeps it.

Most cleaning tools apply a fix and move on. AETERNA-QA treats every fix as a hypothesis. It looks for suspicious values, picks one repair from a short approved list, tries it, and measures whether a prediction model gets better. If the improvement is big enough to trust, the fix is kept. If not, it is undone. Every step is written to a log, and a plain-English report explains what happened.

The dataset is the classic Adult census table (predict whether income is above 50K).

## A tiny worked example

Imagine the column `capital.gain` contains the value `9999999` in a few rows. That is not real money, it is a placeholder someone typed in when the value was unknown.

1. **Detect.** A detector notices that one extreme value shows up far more often than it should.
2. **Plan.** The planner proposes: "replace `9999999` with the typical value of the column".
3. **Try.** The agent applies that fix on a copy of the data.
4. **Verify.** It trains a prediction model with and without the fix, on the same rotating train/test splits, and checks the predictions.
5. **Decide.** If the predictions improved by more than a minimum bar, the fix is **committed** (kept). If not, it is **rolled back** (undone) and the data stays as it was.

Nothing is kept on faith.

## The loop

```
  data ──> DETECT ──> PLAN ──> TRY the fix ──> VERIFY ──┬─ improved enough ──> KEEP (commit)
          (finds      (picks   (on a copy,    (same     │
          suspects)   one fix   fitted on     rotating  └─ not enough ───────> UNDO (rollback)
                      from a    training      test                │
                      fixed     rows only)    splits)             ▼
                      menu)                              AUDIT LOG ──> plain-English REPORT
```

The loop repeats: after each keep or undo, the planner proposes the next fix, up to a fixed number of tries per run (`MAX_ITERATIONS = 16`).

## Key ideas in plain words

**Cross-validation and folds (5x3).** Imagine a class exam where you never let students see the questions they will be graded on. We split the rows into 5 slices ("folds"). The model learns from 4 slices and is graded on the fifth, then the slices rotate so each one gets a turn as the exam. We do that whole rotation 3 times with different shuffles. That gives 15 exam scores for every candidate fix. The slices are drawn once and reused, so before and after are compared on exactly the same exams.

**Evaluator.** The model used to grade fixes: logistic regression with the numeric columns rescaled. The rescaling is learned inside each fold from training rows only. It is **frozen**: it is not adjusted after seeing results, and a set of leak tests must pass before its numbers are trusted. (A random forest was also tried early on and is kept only to reproduce old numbers. It barely reacts to the damage we inject, so it is not used to decide anything.)

**Gate / commit rule.** The gatekeeper. A fix is kept only if its measured gain is positive **and** at least a minimum improvement bar. The bar is computed from how noisy the measurement is, not guessed.

**Brier score (the gate) vs F1 (reported beside it).** Brier score measures how far the model's predicted probabilities are from what actually happened. Saying "90% sure" about something that did not happen costs more than saying "60% sure". Lower Brier is better. We use the negative, so **higher is better** and a positive change means improvement. F1 is a more familiar accuracy-style number. It is always printed next to each decision, but it does not decide anything.

**Nadeau-Bengio corrected standard error.** A standard error says how much a measurement wobbles by chance. Plain cross-validation error bars are too optimistic, because the 15 exams reuse mostly the same rows and are not independent. The Nadeau-Bengio correction widens the error bar to account for that overlap. Wider bars mean the agent is harder to fool.

**Bonferroni correction.** If you try many fixes, one of them will look good by luck. Bonferroni raises the bar in proportion to how many fixes are tried in a run, so a lucky win is much less likely to be kept.

**Commit and rollback.** Commit means the fix becomes part of the cleaned data. Rollback means the fix is discarded. A fix that helps only a little, below the bar, is treated as noise and rolled back. The report labels these separately from fixes that clearly hurt.

**Staged chain.** Sometimes two fixes only help together. A fix that improves the current chain by a meaningful amount (at least a quarter of its own bar) can be staged and held while the agent tests what comes next. If the chain clears the bar, all of it is committed. If the run ends first, it is discarded.

**Data leakage.** Cheating by accident, when information from the exam leaks into the studying. For example, computing a "typical value" from all rows, including the test rows. So every repair learns what it needs (medians, spellings, factors) from **training rows only** and then applies it to the test rows.

**Fixed operation menu.** The planner cannot write code. It can only choose from a short approved list: `fill_mean`, `fill_median`, `fill_mode`, `fill_unknown`, `drop_rows`, `clip_outliers`, `normalize_categories`, `sentinel_to_median`, `rescale_units`, `dedupe_rows`. This keeps the agent predictable and auditable.

**Planner.** The part that picks which fix to try next. Two versions exist: an LLM planner (Groq, model `openai/gpt-oss-20b`), which only sees the detectors' findings and must answer from the menu, and a rule-based planner that needs no API key. The planner only proposes. The gate decides.

**Pre-registration.** Before the study ran, the rules were written down and signed: scenarios, metric, how a result would be labelled. Later changes are only allowed as dated, append-only amendments. This stops us from picking the story after seeing the numbers. See `Documents/PREREGISTRATION.md`.

**Synthetic injection and the manifest.** To know whether the agent is right, we damage a clean copy on purpose (for example, re-spell some job titles, or overwrite some values with a placeholder) and keep an answer key, the **manifest**, listing exactly what we broke. The planner never sees the manifest. It is only used afterwards to grade the agent. Every result from this is labelled **synthetic**.

**Audit log.** A JSON file for each run recording every fix tried, the numbers, and the decision. The plain-English report is built from it.

## Repo map

```
CLAUDE.md                  project state and working rules
README.md                  this file
Dataset/adult.csv          original data
aeterna_qa/                the code
  modules/
    config.py              settings (models, gate metric, fold counts, operation menu)
    evaluator.py           FROZEN: cross-validation, corrected SE, commit bar
    evaluator_tests.py     leak tests for the evaluator
    detectors.py           finds suspects: missing codes, duplicates, unit mixups, spelling variants
    planner.py             picks the next fix (Groq LLM or rule-based)
    executor.py            applies the ten menu operations, fitted on training rows only
    pipeline.py            the whole loop, plus the command-line entry point
    audit.py               writes the run log
    explain.py             turns a log into a console summary and an HTML report
    injection.py           plants declared damage and records the manifest (synthetic)
    study.py               the pre-registered study runner (pilot, eval, confirm)
    demo.py                D1, a labelled synthetic demo scenario
    ops_tests.py, explain_tests.py, demo_tests.py   other tests
  data/adult.csv           the data the pipeline reads
  outputs/                 cleaned CSVs plus manifests
  logs/                    run logs, HTML reports, and logs/study/ for the study
  requirements.txt
  _archive/, _scratch/     old experiments and throwaway scripts, not part of the pipeline
Documents/                 Documentation.md (changelog), PREREGISTRATION.md, RESULTS.md, BUILD_PLAN.md, decks
Resources/                 reference papers
tools/frozen_check.py      checks that frozen files and the signed pre-registration are unchanged
```

`Documents/README.md` is older and out of date. This file replaces it.

## How to run

**Setup** (Python 3.10 or newer):

```
cd aeterna_qa
pip install -r requirements.txt
```

The Groq planner needs an API key. Create a file named `.env` in the repo root (next to this README, not inside `aeterna_qa/`) containing one line, `GROQ_API_KEY=` followed by your key. Never commit this file. You can skip this entirely by using the offline planner.

**Run from inside `aeterna_qa/`:**

```
# Windows only: avoids a crash on non-ASCII characters in LLM text
set PYTHONIOENCODING=utf-8          (PowerShell: $env:PYTHONIOENCODING="utf-8")

# Rule planner, declared synthetic damage, no API key needed
python -m modules.pipeline --inject --offline-planner

# The labelled synthetic demo (four defects at once, Groq planner)
python -m modules.pipeline --scenario D1 --seed 201

# Add --offline-planner to run the demo without a key
# Real Adult data, no injected damage: run with no flags
python -m modules.pipeline

# Explain a finished run (newest log if no path given); --offline avoids any LLM call
python -m modules.explain logs/run_<timestamp>.json
```

The pipeline also writes an explanation and an `report_*.html` file at the end of each run (when `EXPLAIN_ENABLED` is on, the default).

**Tests** (from `aeterna_qa/`, except the first, from the repo root):

```
python tools/frozen_check.py            # repo root; exit 0 means nothing frozen has changed
python -m modules.ops_tests
python -m modules.evaluator_tests
python -m modules.explain_tests
python -m modules.demo_tests
```

## What the results say

Everything below is on damage **we injected into one dataset** (Adult), so all of it is **synthetic**. The full tables are in `Documents/RESULTS.md`.

The study had 5 scenarios (C1 to C5), each run with 3 seeds (201 to 203) on 24,128 evaluation rows, so 15 runs. Against the outcomes the pilot predicted, using the pre-registered labels:

- **4 hit** (a fix was expected and committed): 1 of 3 for C1, 3 of 3 for C5.
- **2 miss** (a fix was expected but nothing committed): 2 of 3 for C1.
- **2 correct rollback** (nothing expected, nothing committed): 1 of 3 for C3, 1 of 3 for C4.
- **7 false commit** (nothing expected, but something was committed): 3 of 3 for C2, 2 of 3 for C3, 2 of 3 for C4.

Positive and negative scenarios are reported separately and never pooled into one accuracy figure.

The 7 false commits need context. The "expected" outcomes came from a small pilot, and they were wrong for several scenarios. In all 11 commits the agent applied the correct repair for a real injected defect: 0 wrong-operation commits, 0 collateral cells changed, 0 rows dropped. Nothing was re-tuned after seeing this. We report the labels as registered.

The rule planner and the Groq planner gave identical outcomes in 15 of 15 runs. Groq reached the correct commit on evaluation 1.0 on average against 1.55 for the rule planner. That is an efficiency finding only, on a small sample.

On the **real Adult data** (its own `?` missing values, no injection), nothing commits. That matches what we believe is the truth: those gaps are harmless to the model.

## Limitations

- Every positive result is on damage we planted ourselves in one dataset. There is no result yet on genuinely dirty real data, and no second dataset.
- The real-data run committing nothing is a correct "no", not a demonstration that cleaning helps.
- **D1** (`--scenario D1`) is a labelled synthetic **demo**. It is not a study result, not pre-registered, and never pooled with C1 to C5.
- Sentinel repairs replace a placeholder with the training median. They remove the bad code but cannot recover the true value.
- Only the rule planner and Groq planner were compared, on 15 runs. No claim is made that the LLM changes what gets committed.
- Sizes of gains are small (fourth decimal place of Brier score for most scenarios), and the statistical bars are approximate and conservative, not exact p-values.

## Where to read more

`Documents/Documentation.md` is the changelog and source of truth. `Documents/PREREGISTRATION.md` holds the signed plan and amendments. `Documents/RESULTS.md` holds every table.
