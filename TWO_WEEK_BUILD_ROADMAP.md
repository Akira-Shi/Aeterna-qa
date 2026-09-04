# AETERNA-QA — 2-Week Build Roadmap (40-50% Demo)

Built against a real constraint: 10-14 working days, 2-3 hrs/day = **20-35 hours total**, basic Python background, first time building an agent loop. That budget does not fit the original 4-month plan's Month 1+2 scope. This roadmap cuts to what actually proves the verification loop works, and defers everything else on purpose.

## What "40-50%" means here

Not 40-50% of all 7 modules. It means: **the core detect → plan → execute → verify → rollback loop runs end-to-end on one dataset, with real numbers**, plus a basic audit log. Everything else from the original Month 3-4 scope (multi-table schema, PyOD, RL convergence, human-in-the-loop, DuckDB, Docker, FastAPI) is explicitly out and should be named to the guide as "deferred to Month 2+", not hidden.

## Cuts from the original plan, and why

- **Drop LangChain.** Direct API calls with structured/JSON output do the same job with far less setup and far fewer debugging dead-ends. LangChain buys nothing at this scope.
- **Drop GPT-3.5 Turbo.** (Certain) OpenAI is retiring it by October 2026 — it will likely stop working mid-project. Use a current cheap model (e.g. gpt-4o-mini or a current Claude Haiku) instead.
- **Constrain the LLM to a fixed menu of operations**, not freeform Python generation. Freeform `exec()` on LLM output is a real code-injection risk and a debugging time-sink chasing hallucinated syntax. A fixed menu (fill_mean, fill_median, fill_mode, drop_rows, clip_outliers) is fast to implement, fast to test, and still lets the LLM "reason" about which one to pick and why.
- **Streamlit is optional, not Phase 1.** A working terminal script with printed before/after F1 numbers is a stronger demo than a half-built UI. Only wrap it in Streamlit if days 1-9 finish early.
- **Fix the random seed on every train/test split.** Without it, F1 varies more than your 1% threshold just from noise, and the demo could show a false rollback live in front of the guide.
- **Synthetically corrupt the dataset on purpose.** Adult Census is fairly clean already (aside from `?` nulls) — inject additional missing values / outliers yourself so the "before" state is visibly bad and the "after" improvement is visible and controllable, not left to chance.

## Day-by-day (10 working days across the 2 weeks — 4 days of slack built in on purpose)

**Day 1 (2-3h) — Environment + baseline evaluator**
- `pip install pandas scikit-learn python-dotenv` (skip LangChain, Great Expectations, PyOD, Streamlit for now)
- Load `adult.csv`, confirm it opens, check target column and class balance
- Write `evaluator.py`: `calculate_baseline_f1(df, target_col)` using `train_test_split(..., random_state=42)` and `RandomForestClassifier(random_state=42)`
- Run it once on the raw data, record the F1 number. This is your baseline — write it down, you'll need it for the demo.

**Day 2 (2-3h) — Make the dirty dataset**
- Write a small script that copies `adult.csv`, injects nulls into 2-3 columns (~10-15% of rows) and a few outliers into a numeric column, saves as `adult_dirty.csv`
- Run `evaluator.py` on the dirty version — confirm F1 drops. If it doesn't drop meaningfully, inject more corruption. You need a visible gap to close.

**Day 3 (2-3h) — Profiler**
- `profiler.py`: for each column, null count/%, dtype, and for numeric columns a simple outlier flag (IQR rule is enough — skip PyOD/Isolation Forest for now)
- Output as a plain dict/JSON. Test it against `adult_dirty.csv` and confirm it correctly flags the columns you corrupted.

**Day 4 (2-3h) — Planner (constrained choice, not freeform)**
- Define your fixed operation menu as a Python enum or list of strings: `["fill_mean", "fill_median", "fill_mode", "drop_rows", "clip_outliers"]`
- One API call: send the profiler's JSON output, ask the model to return structured JSON — `{"column": ..., "operation": ..., "reason": ...}` — picking from that menu only. Use the provider's structured-output / JSON-mode feature rather than parsing free text; free-text parsing is where most of your debugging time will go otherwise.
- Test with 2-3 manual profile inputs before trusting it on the real data.

**Day 5 (2-3h) — Executor**
- `executor.py`: takes the planner's JSON, maps `operation` to an actual pandas call on a **copy** of the dataframe, wrapped in `try/except`
- No `exec()`, no arbitrary code — just a dict mapping operation names to functions. This is deliberately boring; boring is fast and safe here.

**Day 6 (2-3h) — Wire it together, one full pass**
- Orchestration script: `original_f1 = evaluate(dirty_df)` → `profile = profile(dirty_df)` → `plan = plan(profile)` → `cleaned_df = execute(dirty_df, plan)` → `new_f1 = evaluate(cleaned_df)` → if `new_f1 - original_f1 >= 0.01: keep, else: rollback`
- Get ONE operation running end to end with a printed before/after. This is your minimum viable demo — if the two weeks ran out today, you'd still have something to show.

**Day 7 — Buffer.** Debugging day. Something in days 1-6 will not have worked cleanly — LLM returning malformed JSON, a column type mismatch, an operation that errors on edge-case data. Budget this day for that, don't schedule new work into it.

**Day 8 (2-3h) — Loop it (2-3 iterations)**
- Extend the orchestration script to run the detect→plan→execute→verify cycle 2-3 times in sequence on the same dataframe, each time re-profiling the current state
- Log each iteration's decision (accepted/rejected) to a list

**Day 9 (2-3h) — Minimal audit trail**
- Dump the iteration log to a JSON file or print a clean table: operation, column, F1 before/after, delta, accepted/rejected
- This is your stand-in for the "Audit & Explainability" module — it's honest about being basic, and it's real

**Day 10 — Buffer / demo prep**
- If everything above is solid: wrap the orchestration script in a 20-line Streamlit app (file upload → run → show before/after table). Only attempt this if days 1-9 finished with time to spare.
- If not: a terminal run with clean printed output is a legitimate, defensible demo. Screenshot or record it.
- Update your slides' Month 1/2 status to reflect what's actually built, and prepare to state plainly what's deferred (multi-table, PyOD, RL, Docker, FastAPI, DuckDB) and when it lands.

## What to tell the guide

Lead with the same line as before — the verification loop is the novel part, and it runs. Then be specific about scope: one dataset, one operation type per iteration, a fixed operation menu instead of freeform code generation (name this as a deliberate safety/reliability choice, not a shortcut — it is one), and a basic audit log. Everything else is Month 2+ per the original plan, now compressed into a 2-week checkpoint by request.

## Risk notes

- (Likely) The LLM planner step is where a first Python project run into API/parsing friction most often — the JSON-mode requirement in Day 4 exists specifically to reduce that.
- (Certain) If gpt-3.5-turbo is used anyway, confirm API access still works before Day 4 — it may already be blocked given the October 2026 retirement window.
- (Guessing) 20-35 hours is tight even with this cut scope for a first agent-loop build. If Day 7's buffer isn't enough, cut Days 8-9 (multi-iteration + audit log) and demo a single clean iteration instead — one real, working cycle beats three flaky ones.
