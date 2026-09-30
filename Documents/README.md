> **Outdated (mentions RandomForest and profiler.py). See ../README.md.**

# AETERNA-QA

An autonomous data-quality agent: detect real data errors, plan a fix with an LLM, execute it safely (fixed operation menu, no freeform code generation), verify the fix actually improved a downstream ML model, and roll back if it didn't.

## Status (2026-09-29)

Full rebuild in progress after a restart — see `Documentation.md` for the complete decision log, including why the dataset changed from synthetic corruption to the real missing-value gap already present in `adult.csv`.

## Structure

```
aeterna_qa/
  data/          adult.csv (real data, real ? missingness — no synthetic corruption)
  modules/       config.py, evaluator.py, profiler.py, planner.py, executor.py, pipeline.py, audit.py
  logs/          audit output from pipeline runs
```

## Setup

1. Python 3.11+, then from `aeterna_qa/`: `pip install -r requirements.txt`
2. Create `.env` in the Capstone root (not inside `aeterna_qa/`) with:
   ```
   GROQ_API_KEY=your_key_here
   ```
3. Run `python modules/pipeline.py` to execute one full detect→plan→execute→verify cycle.

## Core loop

profiler.py reads the dataset and reports null percentages per column. planner.py sends that report to Groq (`llama-3.3-70b-versatile`) and gets back a JSON decision: which column, which operation, why — picking only from a fixed menu (`fill_mean`, `fill_median`, `fill_mode`, `drop_rows`, `clip_outliers`). executor.py applies that operation via a plain dict-to-function map. evaluator.py fits a RandomForest and measures F1 before and after. pipeline.py compares the two and accepts or rolls back based on the delta, logging every iteration to `audit.py`'s output.

## Why this dataset

`adult.csv` (US Census / Adult Income) already contains real, naturally-occurring missing values — `?` in `workclass`, `occupation`, `native.country`, roughly 7.4% of rows — because that's genuinely how the census was collected, not injected. Dropping those rows vs. leaving them in produces a confirmed 0.0175 F1 gap, and naively filling the mode (a plausible first move) actually makes F1 worse by 0.0062 — a real case for the verification loop to catch. Full reasoning in `Documentation.md`.

## Research context

See `Resources/` for the three core reference papers (DeepPrep, "Exploring LLM Agents for Cleaning Tabular ML Datasets," "Iterative Cleaning with Verification Loops"). A full module-by-module literature list lives in the project's status doc.
