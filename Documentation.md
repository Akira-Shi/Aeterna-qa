# AETERNA-QA — Build Documentation

Living log of what's built, what changed, and why. Update this after every work session — a 2-line changelog entry, not a rewrite. This is the guide-facing reference: it should always reflect what's actually working, not what's planned.

## Module status

| Module | File | Status | Last updated | Notes |
|---|---|---|---|---|
| Config | `config.py` | Not started | — | Threshold, op menu, model name |
| Evaluator | `evaluator.py` | Not started | — | Fixed random_state |
| Profiler | `profiler.py` | Not started | — | IQR outliers, null %, dtype |
| Planner | `planner.py` | Not started | — | JSON-mode, fixed op menu only |
| Executor | `executor.py` | Not started | — | No exec(), dict-mapped ops |
| Orchestrator | `pipeline.py` | Not started | — | Only module that imports the others |
| Audit logger | `audit.py` | Not started | — | Iteration log → JSON |
| UI | `app.py` | Deferred | — | Only build if core loop finishes early |

Status values: Not started / In progress / Working / Blocked / Deferred

## Key decisions (with reasoning, so nobody re-litigates these later)

- **2026-09-04** — Cut LangChain in favor of direct API calls with JSON-mode structured output. Reason: no framework overhead justified at this scope; JSON-mode avoids free-text parsing failures, which was the expected biggest time-sink.
- **2026-09-04** — Cut gpt-3.5-turbo. Reason: OpenAI retiring it by October 2026 — would likely break mid-build. Using a current model instead.
- **2026-09-04** — Planner restricted to a fixed menu of 5 operations (fill_mean, fill_median, fill_mode, drop_rows, clip_outliers) instead of freeform LLM code generation. Reason: freeform `exec()` on LLM output is a real code-injection risk and a debugging sink from hallucinated syntax; fixed menu is faster to build, safer, and still demonstrates LLM reasoning (it's choosing among options, not writing code).
- **2026-09-04** — 2-week milestone scoped to ONE dataset (Adult Census, synthetically corrupted) with a single-iteration verification loop as the floor, multi-iteration + audit log as stretch. Reason: 20-35 available hours; original Month 1-2 scope (2 datasets, PyOD anomaly detection, temporal drift monitoring) doesn't fit. Deferred items named explicitly so the guide sees them as "next," not missing.
- **2026-09-04** — Random seed fixed (42) on every train/test split and model fit. Reason: F1 variance from an unfixed seed can exceed the 1% delta threshold, risking a wrong accept/rollback decision live in a demo.

## Changelog

### 2026-09-04
- Roadmap and module breakdown finalized. No code written yet.
- Documentation.md created.

<!-- Add new entries above this line, most recent on top. Format:
### YYYY-MM-DD
- What you built/changed
- Any numbers worth keeping (F1 before/after, time spent, what broke)
-->

## Known issues / open questions

- (none yet — first log this against a real run, not speculatively)

## Cost tracking

Track this from Day 4 onward (first planner API call) — you quoted ~$30 total in the original pitch; log actual spend here so you can answer "how much did this cost" with a real number instead of the estimate.

| Date | Calls made | Est. tokens | Est. cost |
|---|---|---|---|
| — | — | — | — |
