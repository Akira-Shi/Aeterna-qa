# AETERNA-QA — Build Documentation

Living log of what's built, what changed, and why. Update this after every work session — a 2-line changelog entry, not a rewrite. This is the guide-facing reference: it should always reflect what's actually working, not what's planned.

## Current state (2026-09-30) -- read this first

The sections below "Restart note" and "Key decisions" are kept as history and some are superseded. What is true now:

- **What it is:** an LLM-planned data-cleaning agent. Deterministic detectors find suspected defects; a planner (Groq `openai/gpt-oss-20b`, or a rule-based twin) picks one fix from a fixed menu; the evaluator scores it on 15 fixed train/test folds; a fix is committed only if the paired gain in **Brier score** beats a Nadeau-Bengio + Bonferroni bar, otherwise it is rolled back. Every step is logged and explained.
- **Evaluator:** Logistic Regression (StandardScaler + LR) only. RandomForest was dropped (it does not react to the injected defects). Gate = negative Brier; F1 is reported alongside. Leak tests pass (`python -m modules.evaluator_tests`).
- **Ops menu:** fill_mean, fill_median, fill_mode, fill_unknown, drop_rows, clip_outliers, normalize_categories, sentinel_to_median, rescale_units, dedupe_rows. All fitted on training rows only.
- **Real Adult:** nothing commits (declared check, passed 2026-09-30). The real `?` missingness is harmless.
- **Controlled-corruption study** (`PREREGISTRATION.md`, signed v1 with dated amendments; results in `RESULTS.md`): 5 scenarios x 3 seeds on a 24,128-row eval partition. Rule planner and Groq planner gave **identical outcomes in 15/15 runs**: 4 hit, 2 miss, 2 correct rollback, 7 "false commit" by the registered label. All 11 commits were the correct repair of a real injected defect; 0 wrong-op commits, 0 collateral cells, 0 rows dropped; recovery 0.89-1.00.
- **Planner comparison:** same final outcomes, but Groq reached the correct commit in 1 evaluation on average vs 1.55 for the rule (11 runs that committed under both), because the rule always tries the real `capital.gain = 99999` value first. Efficiency only, small sample.
- **Cleaned data:** `aeterna_qa/outputs/adult_clean_<scenario>_<seed>.csv` (+ manifest); Groq-run copies carry a `_groq` tag when written.
- **Not done / not shown:** any result on genuinely dirty real data; a second dataset; UI (`app.py`); LLM notes tested live after the token-limit fix; recovery of true values for sentinel repairs (median fill cannot).

## Restart note (2026-09-29, historical)

The prior build (evaluator.py, config.py, profiler.py, synthetic `adult_dirty.csv` v2) was wiped and rebuilt from scratch. Reason: three rounds of tuning synthetic corruption produced an F1 gap too small to defensibly demo (0.00485), and it wasn't real data corruption in the first place. `adult.csv` already contains real, naturally-occurring missing values (`?` in `workclass`, `occupation`, `native.country` — 2,399 of 32,561 rows, 7.4%) — this is now the dirty signal, not synthetic injection. See "Key decisions" below for the full reasoning and the numbers that back it.

## Module status (updated 2026-09-30)

| Module | File | Status | Notes |
|---|---|---|---|
| Config | `config.py` | Working | Op menu (10 ops), `EVALUATOR="lr"`, `GATE_METRIC="brier"`, `MAX_ITERATIONS=16`, `MIN_STAGE_GAIN_FRAC=0.25`, Groq key from `.env` |
| Detectors | `detectors.py` | Working | missing, duplicates, sentinel, top_coded, category_variants, mixed_units. Plain pandas, no LLM. `find_sentinel_value` and `find_unit_shift` are shared with the executor |
| Planner | `planner.py` | Working | Groq strict-JSON planner over `remaining_options`; `plan_offline` rule twin (ablation baseline). Never sees the answer key |
| Executor | `executor.py` | Working | Dict-mapped ops, no `exec()`; `fit_and_apply` fits on train only; `execute` finalizes decided ops |
| Evaluator | `evaluator.py` | Working, frozen | Fixed folds, fold-local replay, LR/RF factory, Brier gate, corrected paired SE, `clears_bar`. Tests: `evaluator_tests.py` |
| Orchestrator | `pipeline.py` | Working | Greedy chain (staging needs >=25% of the bar), commit/rollback, answer-key check, `run()` accepts an injected dataframe and returns a result dict |
| Audit | `audit.py` | Working | Iteration log to JSON |
| Explain | `explain.py` | Working | Console + HTML report, Groq notes with number/identifier guards; token-limit fix untested live |
| Injection | `injection.py` | Working | category_variants, sentinel, mixed_units injectors + manifest (answer key) |
| Study | `study.py` | Working | `pilot`, `ceilings`, `eval [--planner groq]`, `confirm`; 20/80 grouped split; grading; cleaned CSV |
| Tests | `evaluator_tests.py`, `ops_tests.py` | Passing | Leak tests; detector/op tests; answer key never reaches planner/detectors/executor/evaluator |
| Archived | `_archive/` | Not used | profiler, positive_control, exhaustive_search, diagnose, single_op_sweep |
| UI | `app.py` | Deferred | Stretch only |

Status values: Not started / In progress / Working / Blocked / Deferred

## Key decisions (with reasoning, so nobody re-litigates these later)

- **2026-09-28** — Full restart. Prior codebase wiped, not kept as a legacy reference, per explicit decision to rebuild clean rather than continue with unfamiliar in-progress code.
- **2026-09-28** — Dataset: use `adult.csv`'s real `?` missingness (workclass/occupation/native.country, 7.4% of rows) as the dirty signal, not synthetic corruption. Investigated external real-error benchmarks first (CleanML, REIN, Raha/HoloClean) — CleanML's data is behind a Dropbox link, REIN sources several datasets via Kaggle, and the build environment's network policy blocks Dropbox/Kaggle/UCI (archive.ics.uci.edu) — only GitHub-hosted repo files are reachable. Raha's real dirty/clean pairs (Hospital, Beers, Flights, Rayyan, Tax) are reachable but are entity-resolution benchmarks with no classification target — wrong shape for this project's F1-based evaluator. Resolution: use what's already real and already in hand.
- **2026-09-28** — Verified empirically before committing (RandomForest, `random_state=42`, held-out test set, one-hot with `dummy_na=True`): as-is (real `?` present) F1 = 0.6708; dropped `?` rows (canonical clean) F1 = 0.6883. **Delta = 0.0175** — real, meaningful, well above any sane rollback threshold, and roughly 3.6x the old synthetic v2's 0.00485.
- **2026-09-28** — Also tested `fill_mode` (the planner's most likely first pick from the fixed op menu) on the same real missingness: F1 = 0.6646, i.e. **worse than doing nothing** (Δ = −0.0062 vs. as-is). This is intentional demo material, not a bug to fix: it's the case that makes the verification/rollback loop earn its place — a plausible-looking fix that should be caught and rejected, not blindly applied.
- **2026-09-28** — Planner will therefore need to reason about *which* column-level operation to try per iteration, and the pipeline needs to actually reject `fill_mode` here when it's proposed — this is the single most important behavior to verify in task 7's first end-to-end pass.
- **2026-09-28** — LLM for planner.py: Groq, `llama-3.3-70b-versatile`, free tier. gpt-3.5-turbo was ruled out previously (OpenAI retiring it); Groq chosen for free tier + fast inference + solid JSON-mode support. API key lives in `.env` (`GROQ_API_KEY`), never in this repo's tracked files or in chat.
- **2026-09-28** — Carried forward from the old build, still true, not being re-solved this milestone: naive IQR outlier detection is unreliable on skewed columns (`hours.per.week`, `capital.loss`, `education.num`, `fnlwgt` all showed high false-positive-style counts on the old dataset despite being uncorrupted). `clip_outliers` stays in the op menu but the planner should be steered toward null-based column selection for now. Revisit with domain-calibrated or ensemble outlier detection as a documented future enhancement, not a blocker for this milestone.
- **2026-09-28** — Accepted post-demo enhancement, prioritized above new features: replace the single train/test split F1 comparison with 5-fold CV or repeated splits before accept/reject, since a single split's F1 has variance that could produce a false accept/rollback decision. Do this before calling the core loop "done," not after.
- **2026-09-28** — Novelty framing needs updating before the next guide meeting: CleanML and REIN are existing benchmark literature specifically about measuring downstream ML impact of cleaning, so "we verify against downstream F1, prior work doesn't" is narrower than the original pitch claimed. The actual differentiator is the closed-loop *agent* architecture (detect→plan→execute→verify→rollback, autonomous, per-dataset) — not the F1-verification idea by itself.

## Reference paper notes (DeepPrep)

Read the actual DeepPrep paper (Resources/DeepPrep-*.pdf) — note: `github.com/pBFSLab/DeepPrep` is an unrelated neuroimaging repo, do not cite it as related work.

What DeepPrep actually is: multi-table ADP (autonomous data preparation) — given source tables + a target schema in natural language, builds a pipeline of 31 operators (joins, pivots, aggregation, schema editing, cleaning, etc.) to produce a table matching that schema. Evaluated by exact-match accuracy / schema-content similarity against a ground-truth table. Trained via tree-based agentic reasoning with backtracking, cold-start SFT + multi-turn RL (GRPO) with a hybrid reward — a research training pipeline (16 A800 GPUs), not an inference-only prompting setup.

Confirms the novelty claim in its narrower form: DeepPrep's evaluation is exact-match/schema-similarity, not downstream ML model performance directly, and it doesn't have a rollback/verification loop. What's NOT adopted from it, on purpose: the 31-op multi-table taxonomy (out of scope, single-table this milestone) and the tree-search/RL training apparatus (out of budget and time entirely — this is what "let's build from the paper" would tempt toward, and what this project is explicitly not doing; see the bandit-policy future-scope idea below for a compute-cheap alternative).

## Future-scope research directions (post-demo, for literature review / possible extension)

- Contextual-bandit policy learning over the audit log — treat operation selection (given error type, column dtype, null%) as a contextual bandit that improves from accept/reject outcomes, as a compute-cheap alternative to DeepPrep's full RL (GRPO) training.
- Planner-critic pre-execution review — second LLM call critiques the planner's proposed fix before the executor runs it (adapts multi-agent debate).
- Ensemble error detection — replace the single-rule IQR outlier check with an ensemble of weak detectors (Raha's ensembling rationale).
- Cross-dataset transfer — test whether a learned operation-preference policy transfers to an unseen dataset.
- Restore the "Explain" module from the original 5-module pitch (profile/plan/execute/verify/explain) — one more Groq call turning the audit log into a plain-English rationale per iteration.

Full literature list with citations lives in the project's status doc (Claude project "Capstone - Aeterna" → `claude/aeterna-qa-status.md`), organized by module.

## Changelog

### 2026-09-29 (fourth pass -- committed-operations leak, found on review before the positive control)

- **RETRACTION (partial) of the third-pass fix.** The fit-on-train/apply-to-test
  redesign (previous entry) was correct for the CANDIDATE operation being
  tested, but it still materialized every CONFIRMED (committed) operation
  into one global `committed_df` via `executor.execute()` (a whole-dataset
  fit) and intersected each fold's row IDs against it. That reintroduces the
  exact leak this whole redesign exists to prevent, one level up: a
  committed `drop_rows` permanently removes those rows from every
  SUBSEQUENT comparison's TEST fold too, not just training, and committed
  fill-type operations were fit on the whole dataset (train+test pooled),
  leaking mildly. It did not corrupt any result reported so far because
  nothing has committed in any real run yet -- but it would have corrupted
  the first run designed to commit something, i.e. the positive control.
  Caught by review before that control was built.
- **Fix**: removed the `committed_df` dataframe entirely from evaluation.
  `evaluator.calculate_f1_candidate` now takes `(raw_df, folds,
  committed_ops=None, candidate_ops=None)` and, inside every fold, starts
  from `raw_df`'s original rows for that fold's train/test row IDs and
  replays `{**committed_ops, **candidate_ops}` together via
  `executor.fit_and_apply` -- nothing is ever pre-removed or pre-baked
  globally, for the whole run, no matter how many operations have
  committed. `pipeline.py` now tracks `committed_ops: dict[str, str]` (a
  plain record of what's confirmed) instead of a materialized dataframe.
  A new `evaluator.materialize(raw_df, committed_ops)` still produces a
  global dataframe, but only for `profiler.profile()` to read (which
  columns still show missingness) -- explicitly documented as never to be
  used for F1 scoring. `exhaustive_search.py` needed no logic change (it
  never had a "committed" concept), just an updated call to match the new
  signature.
- Re-ran the exhaustive 64-combination search from scratch against the
  fixed evaluator: same conclusion as the third-pass run -- 0/64 combos
  clear the corrected threshold, do-nothing ranks 34th of 64 (delta
  +0.0000 by definition), best combo
  (`workclass=fill_unknown, occupation=drop_rows, native.country=fill_unknown`)
  delta=+0.0037 vs. threshold=0.0292, does not clear. True as-is baseline:
  0.6733 +/- 0.0082 (5 folds x 1 repeat, ranking-sweep config). Confirms
  the leak fix did not change the substantive conclusion on this dataset
  (nothing had committed yet, so there was nothing for the bug to have
  been distorting) -- but the fix is required before any run that DOES
  commit something, starting with the positive control.
- Clarified, not a bug: the pipeline's Bonferroni correction is sized to
  `config.MAX_ITERATIONS` (12 look-backs per run); `exhaustive_search.py`'s
  is sized to its own 64 comparisons. The two scripts' printed threshold
  numbers are correctly on different scales for that reason -- compare
  outcomes (does anything commit / clear), not the raw threshold values,
  across the two scripts. One-line comment to this effect added in both
  scripts' docstrings and in `pipeline.py`'s startup print.
- Still open, unresolved, deliberately not started: the positive control
  (deliberately corrupting a strong feature to give the loop a case it
  should actually commit) and how to frame "the loop found nothing to fix
  on real Adult data, twice confirmed independently" to the guide. Ask
  the guide before building the control -- the answer decides whether
  it's a nice-to-have or the centre of the demo.

### 2026-09-29 (later that night) -- SECOND RETRACTION: the fixed-fold "commit" was also wrong, two more real bugs found and fixed

The fixed-fold fix below was itself re-reviewed and two more real, confirmed bugs were found before it was trusted:

1. **Fill-type operations were applied globally before fold-splitting.** Confirmed by direct inspection: after applying fill_mode to `workclass` globally, the training portion of a fold had 0 nulls in that column while the test portion (drawn from raw, untouched data) still had 376. Training on "no missingness" and testing on "real missingness" is not an evaluation of mode imputation -- it's an incoherent comparison. **Fix:** `executor.fit_and_apply` now fits any needed statistic (mean/median/mode/clip-bounds) from a fold's TRAINING rows only, then applies that same value to both that fold's train and test rows -- matching real deployment (fit once, apply to new data as it arrives). `drop_rows` remains training-only, exactly as before; a test row still missing the value keeps it and falls to the model's own missingness handling (documented explicitly now, not left implicit).
2. **The SE was naive and too small.** k-fold (let alone repeated k-fold) training sets overlap heavily -- roughly 75% of rows shared between any two folds' training sets here -- so they are not independent samples, and `std(deltas)/sqrt(n)` understates real uncertainty. **Fix:** `evaluator.paired_delta_corrected` implements the Nadeau-Bengio (2003) corrected-resampled variance (~2.2x the naive SE for this project's 5-fold x 3-repeat setup), and `evaluator.commit_threshold` uses a t-distribution critical value (not z -- with ~14 degrees of freedom the gap matters) at a Bonferroni-corrected alpha. Both are documented in code as literature-grounded but approximate -- true sequential/optional-stopping control across a staged run (deciding to keep testing chains until one passes) is a further, unresolved refinement, correctly flagged as lower priority than the fit/apply bug above.

**A real run under the STILL-BROKEN version of fix #1 above (before this correction) committed a chain at delta=+0.0028 against a threshold of 0.0026 -- directly contradicting the "leave the data alone" conclusion from the previous retraction entry, in the same conversation, within the same evening.** That contradiction is exactly what exposed bugs #1 and #2 above -- a guide reading the doc and a run log together would have caught it immediately, and did, by way of external review before it reached that stage.

**Re-run results after both fixes, exhaustive search (the only one re-run so far -- the real Groq-driven pipeline still needs a live run to confirm agreement):** true as-is baseline (fixed-fold, fit-on-train) = 0.6733 +/- 0.0082. Across all 64 combinations, the best result is +0.0037 (workclass=fill_unknown, occupation=drop_rows, native.country=fill_unknown), against a threshold of 0.0292 for that specific combination's own corrected SE -- nowhere close. **Zero of the 64 combinations clear their corrected threshold** (the one technical "YES" in the ranked table is the baseline compared against itself, a trivial degenerate case). Do-nothing ranks 34th of 64, in the exact middle of a tight, noise-sized band. This is now a clean, internally consistent result -- not one more roughly-plausible number to be doubted further without new evidence.

**Still open, by design, not yet decided:** a positive control (a case with a known, real, sizeable effect the loop should commit to) does not exist yet. Whether to build one, and whether "the loop found nothing to fix on real data" is an acceptable headline result for the guide, is a question for Akira and Dr. Menaka, not something to resolve unilaterally in this document.

**CONFIRMED (2026-09-29, real Groq run after both fixes):** baseline 0.6716 +/- 0.0086 (fixed-fold, fit-on-train). 12 real planner proposals across two chain attempts -- one ran the full 9/9 valid (column, operation) combinations for the 3 real-missingness columns without ever clearing threshold (discarded), the second tried 3 more before hitting MAX_ITERATIONS (discarded). Final F1 = 0.6716 = baseline exactly. Zero commits. This matches the exhaustive ground-truth search exactly (also zero non-trivial commits, do-nothing ranked 34th of 64 in the middle of the noise band). The pipeline and the ground-truth script now agree with each other -- this is the state described in this document as of tonight, and the "no cleaning operation reliably improves this task" finding can be treated as solid, not provisional.

### 2026-09-29 (night) -- RETRACTION: the CV-hardened "real accept" was a measurement artifact

External review of the CV-hardening entry below (credit: a detailed technical review, not caught internally) found two real bugs in that design, both confirmed by direct computation, not just argued:

1. **Test-set leakage.** calculate_f1_cv fit AND evaluated on the cleaned dataframe, so drop_rows was rewarded for deleting hard-to-predict rows from the TEST folds too, not just training. Confirmed concretely: after dropping native.country/workclass `?` rows, exactly 7 rows are still missing `occupation` -- all "Never-worked", a small idiosyncratic group. Two chains differing ONLY by whether those 7 rows were dropped or filled measured 0.0049 F1 apart, almost exactly the size of the threshold (0.0074) that decided the earlier "commit".
2. **Fold reshuffling.** Comparing two independently-computed StratifiedKFold(shuffle=True) runs means a row-count change (even 7 rows) produces a genuinely different fold partition, not the same partition minus 7 rows -- so most of a small observed delta between close configurations can be reshuffling noise, not a cleaning effect.
3. **Uncorrected multiple comparisons.** Raising MAX_ITERATIONS to 12 specifically because "only drop_rows compounds" was optimizing the search toward an expected result. Staging up to 12 chain attempts against a ~2.0x-SE (~95%-ish one-sided) bar without correcting for testing many chains inflates the real chance of at least one spurious commit well above the nominal per-test rate.

**Fix, implemented and verified:**
- evaluator.py: added `make_fixed_folds` (fold membership computed ONCE from the RAW dataset, by row ID, reused for every comparison in a run), `calculate_f1_fixed_folds` (training rows come from the cleaned dataframe; TEST rows always come from the raw, uncleaned dataframe for that fold's row IDs -- the model must predict every original test row, `?` and all, regardless of what was cleaned during training), and `paired_delta` (per-fold paired differences between two conditions on the SAME folds, the correct error bar for "is B better than A", instead of comparing two independently-noisy means/stds). CV_REPEATS=3 added (5 folds x 3 repeats = 15 paired comparisons per decision).
- executor.py: `_drop_rows` no longer calls `.reset_index(drop=True)` -- it was silently destroying the row-ID correspondence the fixed-fold method depends on. Also added `fill_unknown` (explicit missing-as-its-own-category op); confirmed to score ~identically to leaving a column as-is under this project's `dummy_na=True` one-hot encoding, which is itself a real, stated finding, not a wasted addition.
- config.py: THRESHOLD_SE_MULTIPLIER raised 2.0 -> 2.7, an approximate Bonferroni-style correction for up to MAX_ITERATIONS=12 look-backs per run (not an exact family-wise guarantee -- the per-iteration tests aren't fully independent).
- **exhaustive_search.py (new)**: a deterministic, non-LLM ground-truth script enumerating all 4^3=64 combinations of {none, fill_mode, drop_rows, fill_unknown} across the 3 real-missingness columns against the SAME fixed-fold, paired-delta evaluation. Result: the exact combination this pipeline had committed to in the CV-hardening run (native.country=drop_rows, workclass=drop_rows, occupation=fill_mode) ranks **60th of 64** under corrected measurement, at delta **-0.0013** -- confirming it was purely a leakage/reshuffling artifact. The best of all 64 combinations (+0.0038, workclass=none/occupation=drop_rows/native.country=fill_mode) does not clear a properly Bonferroni-corrected bar (needs ~3.16x SE for 64 comparisons; this is ~2.1x SE). "Do nothing" ranks 40th of 64, in the middle of a tight, mostly-noise-sized band.

**Real conclusion for this dataset/target/classifier, stated plainly: no cleaning operation in this project's menu reliably improves downstream F1 on Adult Census Income once measured without leakage and corrected for testing many combinations. "Leave the data as-is" is the defensible, correct answer here** -- not a failure of the agent, but the verification loop doing exactly its job: refusing to act on an effect that isn't real, even when an earlier, flawed measurement made it look like one. This changes how the capstone should be presented to the guide: the demo's strongest claim is no longer "look, it found and applied a real fix" but "the verification loop correctly resists committing to plausible-looking but statistically unsupported fixes, including ones a naive evaluation methodology itself got wrong." That is arguably a MORE interesting and more defensible research result, not a lesser one -- but it is a different story than the one being told as of the previous changelog entry below, and Akira and the guide need to agree on how to present it before the next demo.
- The "the accept/reject decisions are now trustworthy" line in the entry below is WRONG and is retracted by this entry, not edited in place, so the record shows the mistake was made and caught, not smoothed over.

### 2026-09-29 (evening) -- CV-hardening + multi-op combination fix, real accept confirmed
- Replaced the fixed F1_DELTA_THRESHOLD=0.005 guess with a measured one: evaluator.py now has calculate_f1_cv (5-fold StratifiedKFold), and every accept/commit decision compares against threshold = 2.0x the current baseline's measured standard error (std/sqrt(5)), config.THRESHOLD_SE_MULTIPLIER. This is a real methodological upgrade, not cosmetic -- under CV, native.country/drop_rows (accepted in the single-split demo run at +0.0067) actually measures as -0.0006, i.e. noise. The single-split number was wrong.
- That, in turn, exposed that NO single operation on this dataset individually clears a defensible noise bar -- but two of them compound: native.country/drop_rows alone is flat, yet combined with workclass/drop_rows the pair clears the threshold (+0.0075-0.0083 depending on what's done with occupation). A single-operation gate that rejects anything under the bar immediately can never let that compounding effect show up, since the first operation alone never survives to let the second build on it.
- Rebuilt pipeline.py around a staged/commit/discard/replace model: operations are evaluated cumulatively against the last CONFIRMED baseline (not the immediately preceding state), staged if they don't individually clear the bar, and the WHOLE chain commits together once the cumulative effect does. A column already staged with one operation can be REPLACED with its other valid operation later in the same chain attempt (fixed a bug in the first version of this design, where profiling the staged dataframe made a column's missingness vanish the moment any op was staged for it, permanently blocking the planner from trying that column's other operation). audit.py's log_iteration/resolve_chain retroactively rewrite "staged" entries to "committed" or "discarded" once a chain resolves.
- Real confirmed run (real Groq calls, openai/gpt-oss-20b): baseline 0.6733 +/- 0.0082 (5-fold CV). Planner proposed fill_mode for all three columns first (staged: -0.0026, -0.0003, -0.0016 cumulative -- correctly not committed), then revised native.country and workclass to drop_rows while leaving occupation on fill_mode -- that combined chain committed at delta=+0.0083 (threshold was 0.0074). Final F1 = 0.6816.
- MAX_ITERATIONS raised 6 -> 12 to give room for a first losing chain attempt plus a second attempt, since the planner has an observed bias toward proposing fill_mode over drop_rows and only drop_rows combinations have been seen to compound into a real accept.
- Honest scoring update: 0.6816 is still a middling absolute F1 for Adult Census Income (same caveat as before -- untuned RandomForest, no class_weight balancing, no hyperparameter search, deliberately left that way so the classifier stays a stable measuring instrument). The real result of today's work isn't a higher number -- it's that the accept/reject decisions are now trustworthy: they're measured against actual noise, not a guess, and they correctly account for operations whose effect only shows up in combination.

### 2026-09-29 (later same day) -- first real end-to-end pass, task 7 done
- Fixed a chain of real bugs to get a genuine run on the actual machine: Groq model deprecation (llama-3.3-70b-versatile -> openai/gpt-oss-20b), planner JSON-mode returning nulls (switched to strict json_schema with dynamic enums), a pandas dtype portability bug (str vs object breaking the '?' -> NaN replacement on pandas 2.3.3), and a planner heuristic (ban op after 2 failures) that could starve valid categorical combinations -- replaced with deterministic enumeration of untried, dtype-valid (column, operation) pairs each iteration.
- Real run, real Groq calls, on the actual dataset: baseline F1 = 0.6708. Accepted: native.country/drop_rows (+0.0067), workclass/drop_rows (+0.0101). Correctly rejected: native.country/fill_mode (-0.0127), workclass/fill_mode (-0.0032), occupation/fill_mode (+0.0003, below threshold), occupation/drop_rows (+0.0007, below threshold). Final F1 = 0.6877.
- Task 7 (first end-to-end pass) is done -- the loop demonstrably measures real F1 deltas and accepts/rejects correctly, including two genuine near-miss calls at +0.0003 and +0.0007 that a naive "any improvement" rule would have wrongly accepted.
- Honest scoring note (asked "is the F1 score good if we're doing an actual cleaning?"): 0.688 is a real, correctly-measured improvement, but it's a middling absolute F1 for this exact dataset -- untuned RandomForest on Adult Census Income typically lands ~0.65-0.70 F1 on the minority (>50K) class, and tuned/boosted models commonly reach 0.70+. The classifier is deliberately left untuned (fixed random_state=42, no class_weight balancing, no hyperparameter search) so it stays a stable measuring instrument rather than a second thing being optimized -- the capstone claim is "the verification loop correctly measures and acts on downstream impact," not "we built a strong income classifier." Say this proactively to the guide, don't wait to be asked.
- F1_DELTA_THRESHOLD=0.005 is still an unvalidated guess, not derived from measured variance -- it happened to draw the right line in this one run (rejected +0.0003/+0.0007, accepted +0.0067/+0.0101) but that's one run, not a calibration. This is exactly why CV-hardening (5-fold or repeated splits, already flagged as top-priority post-demo enhancement) matters: it would let the threshold be justified in terms of measured F1 variance instead of "it felt right."

### 2026-09-29
- Full restart. Wiped prior aeterna_qa/ (evaluator.py, config.py, profiler.py, adult_dirty.csv v2, make_dirty.py).
- Fixed `.env` filename (was saved as `.env.txt` — Windows hiding the real extension) and rewrote `.gitignore` (was UTF-16 encoded from Notepad, so `.env` wasn't actually being ignored by git before this).
- Rebuilt directory structure: `aeterna_qa/{modules,data,logs}`. Copied real `adult.csv` into `aeterna_qa/data/`.
- Confirmed real `?` missingness gap (0.0175 F1) and the `fill_mode`-makes-it-worse finding (see decisions above) as the dataset foundation for the rest of the build.

### 2026-09-04 to 2026-09-11 (prior build, wiped)
- Roadmap and module breakdown finalized, evaluator.py + profiler.py built against synthetic corruption. Superseded by the 2026-09-29 restart above — see that entry for why.

### 2026-09-30 -- Explain module (guide priority) + audit-log fix
- **Found first:** `audit.log_iteration` recorded only the last-added (column, operation), but `f1_after`/`delta` are measured on the WHOLE staged chain layered on the committed baseline. A reader of the old log would misattribute a delta (e.g. the +0.0034 on iteration 4 of run_20260929T062818Z is a chain result, not "occupation/fill_mode alone"). Fixed by logging `chain_ops` and `committed_ops` per iteration, plus `meta` (scenario label) per run. evaluator.py untouched.
- **New `modules/explain.py`.** Three visibly separate layers: (1) VERDICT -- deterministic COMMIT/ROLLBACK text derived from the logged delta/bar/SE by code; (2) PLANNER reason quoted verbatim, shown as a pre-measurement hypothesis; (3) NOTE -- one Groq call per run, one sentence per iteration, every number and every column/operation name machine-checked against the log; a failing note is dropped (listed in the HTML), never repaired.
- Output: rich console (grouped by chain, headline with closest-miss) + self-contained `logs/report_<run>.html`. Runs automatically at the end of `pipeline.run()` (config.EXPLAIN_ENABLED / EXPLAIN_USE_LLM); standalone: `python -m modules.explain [log] [--offline]`.
- Verified offline on run_20260929T062818Z (legacy format: chain contents flagged as unrecorded) and on a hand-built new-format log with a fake LLM: good notes pass; invented numbers, invented columns and a non-tested operation name are rejected. NOT yet tested: a live Groq call (needs the key on the Windows machine).
- Limits, stated plainly: the guard checks numbers and identifiers, not reasoning -- a note can still be a weak interpretation with correct numbers. That is why the verdict never comes from the LLM.

### 2026-09-30 -- Defect detectors + declared synthetic injection (diagnose stage)
- **Why:** the profiler only reported null_pct and a naive IQR count, so the planner had no evidence about WHAT was wrong and just walked the op menu. Also: low F1 (~0.67) is the task ceiling for Adult (24% positive class, RF at 0.5 threshold), NOT evidence of dirty data -- the dataset is nearly clean apart from `?`, which the 64-combination sweep showed is harmless to the RF.
- **New `modules/detectors.py`** (plain pandas, no LLM, deterministic): `missing`, `duplicates`, `sentinel` (missing-value code far outside the real range, e.g. 999 / 99999), `top_coded` (cap such as age 90, hours 99), `category_variants` (case/space/punctuation spellings). Each finding carries evidence, row count, and candidate fix ops. A finding is a hypothesis; only the F1 gate can commit a fix.
- **Real Adult, what the detectors report:** `?` in workclass/occupation/native.country; 24 duplicate rows; `capital.gain=99999` on 159 rows (sentinel); age=90 and hours.per.week=99 (top-coded caps); no category variants.
- **Bugs found and fixed in the first pass of the detectors:** zero-inflated columns (capital.gain==0, 92% of rows) were flagged as top-coded -> added MAX_SPIKE_SHARE=0.20; hours==99 was called a sentinel because it is all-nines -> a magic number is only a sentinel if it sits well outside the real range (99 has 98 beside it; 999 in age / 99999 in capital.gain do not).
- **New `modules/injection.py`:** DECLARED synthetic corruption with an answer key (manifest of exactly which rows were changed): 30% of occupation re-spelled (expected fix normalize_categories), 5% of age overwritten with 999 (expected fix sentinel_to_median). Spec is declared before any run and must NOT be tuned after seeing results. Always labelled SYNTHETIC. Injection bug fixed: re-spells that left the text unchanged were counted as corrupted (recall showed 0.971 for that reason, not detector error).
- **New `modules/diagnose.py`** (`python -m modules.diagnose`): prints findings on real and injected data and scores detections against the answer key. Result: both injected defects found, precision 1.000 / recall 1.000 on rows.
- **Limits, stated plainly:** detection was only verified on defects WE injected plus Adult's known quirks; recall on unknown defect types is untested. Duplicate injection was deliberately left out (duplicates that land in both train and test folds inflate CV F1, so dedupe may LOWER measured F1). Mixed units and outliers have no detector yet.

### 2026-09-30 -- Three new executor ops (fit on training rows only)
- Added to `executor.py` + `config.OPERATION_MENU`: `normalize_categories` (canonical spelling per normalised key = most frequent raw form in TRAINING; test values map through the same table, unseen spellings left alone), `sentinel_to_median` (sentinel value found by `detectors.find_sentinel_value` on TRAINING rows only, replaced by the training median of the remaining values; no-op if no sentinel in training), `dedupe_rows` (whole-row op, column key `"*"`, removes exact duplicates from TRAINING only -- test rows never touched, same policy as drop_rows).
- Renamed the planned `sentinel_to_nan` -> `sentinel_to_median` everywhere (detectors, injection). Reason: numeric NaN would have needed extra handling in the RF/one-hot path; median-replace keeps the evaluator unchanged.
- `config.MAX_ITERATIONS` 12 -> 16 because detector-driven planning offers ~14 (column, op) pairs on real Adult; the Bonferroni look-back count is re-sized automatically (commit_threshold takes MAX_ITERATIONS). Real-data thresholds will therefore be slightly stricter than in earlier runs -- do not compare threshold numbers across the two configurations.
- Verified (unit checks, no F1 involved): full-data normalize on the injected occupation recovers the original text 100%; sentinel_to_median changes exactly the 309 sentinel rows in a test slice (309/309) and clears real capital.gain=99999 (0 remain); no-sentinel column left untouched; dedupe drops train 26000->25985, test rows unchanged (6561); text-only/numeric-only dtype guards raise.
- NOT yet verified: any F1 effect of these ops (next entry).

### 2026-09-30 -- Detector-driven planner + pipeline wiring (`--inject`, `--offline-planner`)
- `planner.py`: `plan(findings, rejected)` now receives detector FINDINGS (defect, column, rows, evidence) and a deterministically enumerated `remaining_options` list (`remaining_options()`), and must cite the evidence in its reason; the prompt forbids predicting a score gain (gain is measured after, never predicted). New `plan_offline()` = rule-based twin (defect priority: sentinel, category_variants, duplicates, missing, top_coded; then row count) -- lets the pipeline run without a Groq key and serves as an LLM-vs-rule ablation baseline. NOT yet tested with a live Groq call on the new prompt.
- `pipeline.py`: profiles via `detectors.detect()` instead of `profiler.profile()`; new CLI: `python -m modules.pipeline [--inject] [--offline-planner]`. `--inject` runs on Adult with the DECLARED synthetic corruption, prints a SYNTHETIC banner, labels the audit log `scenario=synthetic_injection`, and at the end prints an ANSWER KEY CHECK (did the agent commit the fix that undoes each injected defect). The old "combinations evaluated out of 64" line was replaced by a plain count of distinct evaluated states (the 64-space only made sense for the 3 missingness columns).
- Verified: pipeline runs end to end offline on injected data (15 states evaluated, explain report generated, answer-key check prints). Baseline on the real data reproduces the user's own run exactly (0.6716 +/- 0.0086) in the test environment, so numbers here are comparable to earlier runs.

### 2026-09-30 -- FINDING: the RF evaluator is blind to the declared injected defects; two design flaws found and fixed on the way
- **Result (Certain, measured):** `python -m modules.single_op_sweep --inject` (new; every detector-justified op evaluated ALONE against the untouched baseline, same folds, Bonferroni over 16): 0 of 16 clear the bar. Injected baseline F1 0.6737 vs clean 0.6716 -- i.e. injecting the defects did not lower the RF's F1 at all. `normalize_categories` on the 30%-fragmented occupation: -0.0025; `sentinel_to_median` on age=999 (5%): -0.0001. Reason (Likely): trees isolate 999 as its own split bucket and one-hot spellings still each carry the occupation signal. So a RandomForest gate cannot show these fixes winning, however correct they are. This is exactly the guide-agreed reason to add LR (in-fold scaling) as a declared second evaluator; the injection spec must NOT be strengthened after seeing this (that would be tuning the answer).
- **Flaw 1 -- destructive op proposed:** `clip_outliers` on `capital.gain` (92% zeros -> IQR 0 -> bounds 0..0) flattened the feature: delta -0.0496. Fixes: detectors only propose clip when IQR > 0; `executor` now REFUSES clip_outliers when IQR == 0 (raises, so the pipeline logs it as an error instead of scoring it).
- **Flaw 2 -- chain poisoning (pre-existing design):** the chain staged every proposal whatever its delta, so one harmful op stayed in the chain and every later op was measured on top of it. In the first injected run normalize_categories was never evaluated on its own (its -0.049 was the capital.gain clip). Fix (greedy forward selection): an op joins the chain only if its cumulative delta beats the chain's current delta; otherwise it is logged as `discarded` ("DROPPED from chain"). Commit rule and Bonferroni bar unchanged. Consequence: the pipeline's per-op numbers now match the standalone sweep (e.g. -0.0001, -0.0046, -0.0025 in both).
- **Explain prompt fix:** the Groq note prompt asked whether the measurement "supports or contradicts the planner's reason", which produced the boilerplate "...contradicting the reason" on every rollback in the demo output even though the planner never predicted a gain. Now told the reason is a hypothesis about the defect, not a promise of a gain. Not yet re-run with a live Groq call.
- **Injected pipeline run after fixes (offline planner):** nothing committed; answer-key check prints NO for both injected defects (expected: the RF cannot see them). Closest miss 8% of bar.
- `single_op_sweep.py` added to modules/ (output: logs/single_op_sweep_{real,inject}.json).
- **Next (not done):** (1) LR evaluator with in-fold scaling + the two guide-agreed leak tests, frozen before any further look at gains; (2) run single_op_sweep under LR on the SAME declared spec; (3) efficiency ranking + apply step that writes adult_clean.csv and re-scores on a holdout not used in selection.

### 2026-09-30 -- LR evaluator added, leak-tested, frozen; commit-rule bug fixed
- **`evaluator.py`:** `make_model("rf"|"lr")`; `calculate_f1_candidate(..., model=None)` defaults to `config.EVALUATOR` (new; "rf" default, "lr" allowed; CLI `--evaluator` on `pipeline` and `single_op_sweep`). LR = `StandardScaler` + `LogisticRegression(max_iter=2000)` inside one sklearn Pipeline, so scaling is fitted on each fold's TRAINING rows only. Audit log meta now records `evaluator` and `planner`.
- **Leak tests (`python -m modules.evaluator_tests`), both PASS:** (1) `assert_scaler_fit_on_train_only` passes a train-only scaler and RAISES on a scaler deliberately fitted on train+test; it also runs inside every LR fold. (2) LR baseline per-fold F1 on the fixed folds equals sklearn's own `cross_val_score(Pipeline(StandardScaler, LR))` on the same folds: mean 0.6617 both, max per-fold difference 0.00e+00. LR evaluator considered frozen from here.
- **BUG FOUND AND FIXED -- commit rule could commit a no-op.** Under LR, `fill_unknown` on a missing categorical is exactly equivalent to the NaN-indicator column, so every fold gives an identical score; paired SE = 0; bar = 0; and `delta >= bar` (0 >= 0) reported "CLEARS" for three no-op fills. New single commit rule `evaluator.clears_bar(delta, bar)` = `delta > 0 and delta >= bar`, used by `pipeline.py` and `single_op_sweep.py`. Any earlier RF result was unaffected (RF randomness prevents exactly-zero deltas), but the rule was unsafe.
- **`--inject` answer key** now distinguishes commit-expected defects from a NEGATIVE CONTROL (`expected_commit: False`): correct behaviour there is to leave the data alone.

### 2026-09-30 -- Injected run under LR: the agent finds and ranks the right fix, but F1 cannot clear the bar (spec v2 run once, failed)
- **LR single-op sweep, spec v1 (sentinel_age 5%, frag 30%):** `age: sentinel_to_median` +0.0074 (SE 0.0027, bar 0.0087) = 85% of the bar; `age: clip_outliers` +0.0044; `occupation: normalize_categories` +0.0004 (LR does not see the fragmentation either). RF saw none of it.
- **Spec v2 set by the guide's rule, not by trial:** needed gain = bar + 0.84*SE = 0.0109; assuming gain ~linear in rate, rate = 5% * 0.0109/0.0074 = 7.4% -> declared 8%. v1 gains had already been seen; disclosed in `injection.py` SPEC HISTORY. Run ONCE.
- **Result of the single v2 run (LR, offline planner):** baseline 0.6548 +/- 0.0116; `age: sentinel_to_median` +0.0069 (STAGED, best single op, ranked first among everything tested); nothing else stacked meaningfully; NOTHING COMMITTED. Answer key: frag_occupation (negative control) correctly left alone; sentinel_age NOT committed.
- **CORRECTED 2026-09-30 (this bullet originally over-claimed):** 5% gave +0.0074 and 8% gave +0.0069. That 0.0005 difference is well inside the paired SE (~0.0027), so it is noise and does NOT show the gain is flat or nonlinear. What is established: 8% did not reach the +0.0109 that linear extrapolation predicted. A possible mechanism (999 outliers inflating the scaler's std for every row, so damage does not grow with row count) is a hypothesis, not a finding. One measurement per severity cannot show a curve shape; the pre-registration uses >= 3 levels x 3 seeds. Do not raise the v2 rate again on this evidence.
- **Why the gate is the bottleneck (Likely):** the bar is ~3.2 x the corrected SE (t-critical at Bonferroni alpha 0.05/16, ~14 dof, Nadeau-Bengio inflation); a single-column defect worth ~+0.007 F1 cannot clear a ~0.009 bar on F1 at a fixed 0.5 threshold. F1 at a fixed threshold is a high-variance metric.
- **Not a pipeline failure:** detection found the right defect, the planner (Groq, user's own run) chose normalize_categories then sentinel_to_median first, the greedy chain kept the only op that helped, and the answer key check works. What is missing is a corruption/metric combination whose true effect is larger than the bar.
- **Decision pending (Akira / guide):** (a) inject several independent numeric sentinels or a unit mix so cumulative chain gain exceeds the bar (stays inside the guide's "stronger pre-declared synthetic corruption, F1 stays the gate"), or (b) promote a lower-variance secondary metric (AUC/log-loss) to the gate for the synthetic demo (guide said no; would need re-blessing). Do not tune the spec further without deciding this first.

### 2026-09-30 -- Pre-registration drafted (`Documents/PREREGISTRATION.md`); review corrections adopted
- **Decision context:** guide confirmed synthetic data is acceptable as the end product. Plan agreed: corrupted REAL Adult (not generated data), base = Adult with `?` rows removed, ground truth known, agent never sees it, repairs graded against truth as well as by the model gate.
- **Verified facts about the 30,162-row base (Certain):** 24.89% positive; 23 exact duplicate rows (24 feature-duplicates; 1 feature group carries two different labels); `capital.gain=99999` 148 rows; `hours.per.week=99` 78; `age=90` 35; `hours<=1` 7; Husband+Female 1, Wife+Male 1; education/education.num mismatches 0; `age=999` occurs 0 times (safe to inject).
- **Relabel:** 99999 / 99 / 90 are CENSORED (top-coded) values, not placeholders. Injected sentinel/unit values must never coincide with natural values. The detector's "sentinel" label for capital.gain=99999 is only a hypothesis label; wording to be softened (cosmetic, pending).
- **Metric:** proposal is Brier score as the gate for BOTH models (proper, bounded, finite), F1 reported alongside; clipped log-loss (eps 1e-6) is the declared fallback. Checked: 22.6% of RF test probabilities are exactly 0 or 1, RF log-loss 0.353 vs LR 0.324 (sklearn clips, so it is finite, but governed by the clip constant); Brier RF 0.1025 vs LR 0.1032. Earlier idea "gate on LR only, report RF" is dropped (it removed RF from the model-dependence study). Metric switch is Akira's decision, not the guide's (an earlier statement that the guide "ruled against" it was wrong).
- **Design changes vs the first draft:** 20% pilot / 80% eval split BEFORE folds, grouped so duplicate rows never straddle it; >= 3 severities x 3 seeds per scenario; pilot noise scaled by sqrt(n_pilot/n_eval) (unscaled reported too); scenarios designated positive/negative by the pilot, not by expectation; four scenarios (fragmentation, mixed units, 999 code, harmless decoy) each with plausible wrong fixes; real `?` run must still commit nothing under Brier (declared check on the metric switch); cleaned CSV written on commit, confirmed on the pilot partition.
- **Status:** draft awaiting sign-off; nothing run on the eval partition. Open at sign-off: Brier vs log-loss, build `rescale_units` or drop mixed-units scenario, seed lists, softening the censored-value wording.

### 2026-09-30 -- Brier gate + LR as the study evaluator; module cleanup; FIRST COMMIT (trial, not the study result)
- **Sign-off (Akira):** Brier is the gate; build `rescale_units`; if LR is better than RF, use LR only. Interpretation recorded: RF is dropped from the study because it is BLIND to the injected defects (measured: RF single-op sweep 0/16, injected baseline not worse than clean). This is NOT the same as "LR is the better classifier": on the clean base RF Brier 0.1025 vs LR 0.1032 (about equal). LR is chosen because it is the evaluator that responds to data damage. Cost, stated plainly: results say nothing about tree-model pipelines, and the planned "sentinel is a decoy under RF" scenario is gone. RF stays in the code (`--evaluator rf`) only to reproduce old numbers.
- **Code:** `config.EVALUATOR = "lr"`, `config.GATE_METRIC = "brier"` (gate score = NEGATIVE Brier, so higher = better and a positive paired delta = improvement; labelled `neg-Brier` in output). `evaluator.calculate_f1_candidate` (name kept) now returns gate `scores` plus `f1_scores`, `brier_scores`, `f1_mean`. F1 is printed next to every baseline/final line. NOTE: audit-log fields named `f1_*` hold the GATE score from now on; `meta.metric` says which. `explain.py` headline/labels read the metric from meta.
- **Leak tests re-run and pass** with Brier included: LR Brier per fold equals sklearn `cross_val_score(neg_brier_score)` exactly (max diff 0.00e+00).
- **Module cleanup (fewer modules, none deleted):** moved to `aeterna_qa/_archive/`: profiler, positive_control, exhaustive_search, diagnose, single_op_sweep. Verified nothing on the pipeline path imports them. Active modules: audit, config, detectors, evaluator, evaluator_tests, executor, explain, injection, pipeline, planner. Old numbers in this file that cite exhaustive_search / positive_control / single_op_sweep remain valid history; the scripts are in `_archive/`.
- **FIRST COMMIT EVER (trial run, LR + Brier, offline planner, injected spec v2, full 32,561 rows, ~3 min):** baseline neg-Brier -0.1037 (F1 0.6548); `age: sentinel_to_median` COMMITTED, paired delta +0.0010 -> neg-Brier -0.1027 (F1 0.6617). `capital.gain: sentinel_to_median` (real censored value) DROPPED (-0.0011). `occupation: normalize_categories` +0.0003, not enough to commit; fragmentation left alone = the negative control behaving as intended. Answer-key check: sentinel_age YES; frag_occupation CORRECT (left alone).
- **Honest caveat on that commit:** this is a trial, NOT the pre-registered result. The Brier gate was chosen AFTER seeing that the F1 gate failed on this exact spec (v2) on this exact data, so it can't be presented as an unbiased test. The clean claim needs the pilot/eval split and the pre-declared severity rule (`PREREGISTRATION.md`) — still to run.

### 2026-09-30 -- Real-data check passed; pre-registration signed; staging rule tightened
- **Real `?` check (LR + Brier, offline planner, 32,561 rows): committed nothing.** Baseline -0.1022. Closest: `hours.per.week: clip_outliers` and `age: clip_outliers`, +0.0003 vs bar 0.0005 (60%). This was the declared check on the metric switch (PREREGISTRATION section 11). (Certain)
- **Injected trial reproduced on Akira's machine:** `age: sentinel_to_median` committed (+0.0010 vs bar 0.0007); occupation fragmentation correctly left alone. Injected -0.1037, repaired -0.1027, clean -0.1022: about two thirds recovered (0.0010 of 0.0015, rounded, one seed). A trial, not a result: Brier was chosen after F1 failed on this data. (Likely)
- **Staging rule changed** (`config.MIN_STAGE_GAIN_FRAC = 0.25`, `pipeline.py`): an op joins the chain only if it beats the chain's delta by >= 25% of its own bar. Before, exact-zero no-ops (`fill_unknown`, `dedupe_rows`) were "staged" at +0.0000. Post-hoc change, recorded as an amendment; not to be tuned further.
- **Explain module:** Groq call now sets `max_completion_tokens=4096` (16 iterations were truncated and violated the strict schema); payload key `delta_f1` renamed `delta` plus a `metric` field, so notes no longer say "F1" under the Brier gate. Not yet tested against live Groq. Verdicts were always code-derived.
- **PREREGISTRATION.md signed v1**, amendments table filled: LR only, Brier, `rescale_units` approved, seeds approved (split 20261001, pilot 101-103, eval 201-203, confirmation 301).
- Known cosmetic bug left: "Chain N: (chain contents not recorded)" for a chain whose only op was dropped.
- Next: `rescale_units` (detector + executor op), then `study.py` (20/80 grouped split, C1-C4, truth grading, cleaned CSV).

### 2026-09-30 -- `rescale_units`, `study.py`, pilot run, and the headroom finding
- **`rescale_units` built** (`detectors.find_unit_shift` / `detect_mixed_units`, `executor` op, `injection` kind `mixed_units`, planner priority). Fits a cut and a factor from {12, 100, 1000} on training rows only; needs a multiplicative gap, a multi-valued upper cluster, a median ratio near a declared factor, and upper/factor landing inside the lower range. Tests (`python -m modules.ops_tests`): no finding on real Adult; injected x12 at 5/15/30% detected exactly and restored 100% with 0 collateral; no-op on clean data; a 999 code is not read as a unit shift. The same file now also asserts the answer key never reaches planner/detectors/executor/evaluator or the pipeline decision loop.
- **`pipeline.run` refactored** to accept an injected dataframe + manifest and return `{committed_ops, baseline, final, ...}` (behaviour unchanged for the CLI).
- **`study.py`** (`pilot`, `ceilings`, `eval`, `confirm`): 20/80 split by feature-vector groups, stratified, seed 20261001 (pilot 6,034 rows / eval 24,128; zero feature-vector overlap, both 24.9% positive; complete-case Adult). Eval refuses to run without `pilot.json`. Per run it records commit/miss/false-commit, gate before/after/clean, paired delta with 95% CI, recovery fraction, a blind clean-everything baseline, restoration accuracy, collateral cells and dropped rows. Writes `adult_clean_<scenario>_<seed>.csv` + manifest to `aeterna_qa/outputs/` when something commits; `RESULTS.md` is append-only.
- **Pilot findings (Certain, measured):** clean-data controls give delta exactly 0.0000 for every new op. Effects are flat across each ladder. Cause: `age` carries only 0.00096 Brier in total, so no corruption of it can reach the bar (~0.001-0.0018). Headroom: capital.gain 0.0121, occupation 0.0030, capital.loss 0.0017, hours 0.0014, age 0.0010. C1 positive at 10%; C2, C3, C4 negative by the pilot rule.
- **Amendment:** added C5 (9999999 code in `capital.gain`), positive at 1% (+0.0120). Post-pilot, disclosed in PREREGISTRATION section 12. C1 typo variant dropped (no op can repair typos).
- **Eval running** (offline planner, 15 runs, ~4 min each). First two C1 runs: MISS (nothing committed); the damage on the eval partition was only ~0.0005 Brier, against a pilot estimate of 0.0019, i.e. the small pilot partition overstated the effect. Recorded as a miss, not re-run.
- Deviation to note: pilot SE is a within-partition fold SE; it does not capture partition-to-partition variation, so pilot-based expected outcomes can be optimistic.

### 2026-09-30 -- Study eval + confirmation run (rule planner, LR, Brier); full record in `Documents/RESULTS.md`
- Eval on the 24,128-row partition, seeds 201-203, five scenarios (C1-C5). **Registered labels:** HIT 4 (C1 1/3, C5 3/3), MISS 2 (C1 2/3), CORRECT ROLLBACK 2 (C3 1/3, C4 1/3), FALSE COMMIT 7 (C2 3/3, C3 2/3, C4 2/3). (Certain, from `logs/study/eval.json`.)
- **What the labels hide:** all 11 commits were the correct repair for a real injected defect; 0 wrong-op commits, 0 collateral cells, 0 rows dropped; gate recovery 0.89-1.00; gate after repair equals the clean score (-0.1046) or is within 0.0001-0.0002 of it. The pilot's expected outcomes were wrong for C2/C3/C4 (effects 0.0009-0.0012 sat just over the eval bar ~0.0009) and for C1 (eval damage 0.0005-0.0006 vs pilot 0.0019). Pilot SE ignores partition-to-partition variation. Nothing re-run or re-tuned.
- **Baselines:** blind "clean everything flagged" scored -0.1054 on C1-C4 (worse than doing nothing on C1); matched the agent only on C5.
- **Cleaned files:** `aeterna_qa/outputs/adult_clean_<scenario>_<seed>.csv` + `.manifest.json` for every run that committed (11). Confirmation on the pilot partition with fresh seed 301: C2 restored 100%, C4 100%, C3/C5 sentinel removed (median fill), 0 collateral.
- **Limits:** rule planner only (no Groq run yet, so no LLM-vs-rule ablation); sentinel repairs cannot recover true values (median fill); one dataset; synthetic damage authored by us; expected outcomes for C2-C4 were mis-set by the pilot.
- Ran in the cloud workspace (sklearn); files were committed back to the folder. `python -m modules.ops_tests` passes on the device.

### 2026-09-30 -- Groq planner eval finished: identical outcomes to the rule planner; docs brought up to date
- `python -m modules.study eval --planner groq` (run on Akira's machine, ~5-10 min per scenario) wrote `logs/study/eval_groq.json` and `eval_groq_<scenario>_<seed>.txt`. **Outcomes were identical to the rule planner in 15/15 runs** (same committed ops, same labels, final gate scores equal to 5 decimals). (Certain, compared programmatically.)
- **Efficiency difference (Likely, small sample):** among the 11 runs that committed under both planners, the correct commit came on evaluation 1.0 (Groq) vs 1.55 (rule) on average. The rule planner's fixed priority always tries `capital.gain: sentinel_to_median` first (the real 99999 value), which is rejected; Groq went straight to the defect the evidence pointed at in C1, C2, C4. On the 4 no-commit runs Groq used one more evaluation in 3 (C1 x2, C4 x1: 7 vs 6) and the same in 1 (C3: 9 vs 9). The final result never differs, because the gate decides, not the planner.
- Claim to make: the LLM planner is no worse and slightly more efficient; it does not change what gets committed. Do not claim it improves cleaning quality.
- `study.py` output files carry a `_groq` tag for non-rule planners so runs do not overwrite each other.
- Documentation.md restructured: added a "Current state" block, rewrote the module table, rewrote Known issues. Older sections are history.
- Rule-planner per-run logs for all 15 runs are now in `logs/study/`.

<!-- Add new entries above this line, most recent on top. Format:
### YYYY-MM-DD
- What you built/changed
- Any numbers worth keeping (F1 before/after, time spent, what broke)
-->

## Known issues / open questions (rewritten 2026-09-30)

- The study's "false commit" count (7/15) is a labelling artifact: the pilot set expected outcomes that the eval partition contradicted for C2/C3/C4, and the eval damage in C1 was smaller than the pilot estimated. The registered labels are kept; the reading is in `RESULTS.md`. Pilot SE ignores partition-to-partition variation.
- `age` carries only 0.00096 Brier; corruption of `age` cannot clear the bar by design headroom, so C2/C3 sit near the bar (0.0011-0.0012 vs ~0.0009). C5 (`capital.gain`) was added post-pilot to test a strongly detectable defect.
- Sentinel repairs replace a code with the training median; they cannot recover the true value (MAE equals the median-reference MAE).
- The detector labels `capital.gain = 99999` as "sentinel"; it is actually a censored/top-coded value. Wording only, no behaviour change.
- The staging-rule minimum gain (25% of the bar) was added after seeing the real-`?` run; recorded as a post-hoc amendment; not to be tuned further.
- Cosmetic: the explain report prints "Chain N: (chain contents not recorded)" for a chain whose only op was dropped.
- Groq explain notes: `max_completion_tokens` raised and metric wording fixed; not yet tested against live Groq with 16 iterations.
- `pipeline` CLI does not write a cleaned CSV (only `study.py` does). A `--write-clean` option is a possible add.
- One dataset, damage authored by us; no result yet on genuinely dirty real data.
- IQR outlier_count is unreliable on skewed columns (carried forward); `clip_outliers` is not the planner's primary lever.
- Superseded (history only): the F1-gate/RF-era issues, the "2.0x SE" threshold, the leaky ~0.688 F1, and the "no positive control yet" item. A positive control now exists (C5 and the age trial).

## Cost tracking

| Date | Calls made | Est. tokens | Est. cost |
|---|---|---|---|
| — | — | — | — |
