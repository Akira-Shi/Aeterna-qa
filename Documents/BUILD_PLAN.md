# AETERNA-QA — Build Plan (written 2026-09-29, for tonight's 6pm session onward)

Demo date: **not yet confirmed** — fill in here: ______. Sequencing below assumes ≥ 5 working sessions before the demo.

## Guide decisions this plan is built on (2026-09-29)
- Synthetic positive control is OK for the demo if clearly labelled. Frame it as **reversible noise injection (DeepPrep §5.3)**.
- Evaluator model is a declared input: RF and LR, both always reported.
- F1 stays the gate; AUC reported as a secondary metric. A bigger gain comes from a stronger pre-declared corruption, not a metric switch.
- Retraction slide: not needed.
- Priorities: Explain module + demo-friendly output. Add one novel idea if possible.

## Evidence already in hand (don't redo)
- Real Adult `?` data: 0/64 combinations clear the gate; the Groq pipeline commits nothing (matches ground truth).
- `positive_control.py` (06:15 today): MCAR NaN on `education.num` at 10% → best repair +0.0013 vs threshold 0.0207. **Keep this as the negative example.** It fails for two reasons: MCAR destroys information, and `education` is a near-duplicate of `education.num`, so the model never loses the signal.

---

## TONIGHT (Phases 0–3; stop after Phase 3 even if energy remains)

### Phase 0 — Log what exists (15 min)
- [ ] Add a changelog entry to Documentation.md: MCAR `education.num` result as the negative example, with the two reasons above.
- [ ] Don't delete `positive_control.py`. Rename its role in the docstring to "negative control: information-destroying corruption".
- **Done when:** the doc states why MCAR failed, in two lines.

### Phase 1 — Choose the fragmentation target (30–45 min)
- [ ] New script `modules/feature_redundancy.py`. For each candidate categorical column (`relationship`, `marital.status`, `sex`, `education`, `race`), use the fixed folds to compute the F1 drop when **that column alone** is permuted, and the F1 drop when it **and its suspected twin** are permuted together.
- [ ] Known twins: relationship↔marital.status, education↔education.num.
- [ ] Skip `occupation`, `workclass` and `native.country`; they already hold real `?` values, and mixing the two error types muddies the control.
- **Done when:** a table of standalone drop vs pair drop exists. Pick either (a) the strongest column with no twin, or (b) a twin pair that you fragment together (then the demo needs two commits).

### Phase 2 — Reversible fragmentation + `normalize_categories` (60–90 min)
- [ ] `corrupt_fragment(df, column, rate, n_variants, seed)`: for `rate` of rows, replace the value with one of `n_variants` surface variants (case, surrounding whitespace, punctuation, one-character typo). Row IDs are preserved.
- [ ] `normalize_categories` goes in executor **through `fit_and_apply`**. It is NOT stateless: typo repair needs the canonical vocabulary, so fit that vocabulary (the most frequent surface form per normalized key, plus a difflib fuzzy match with a fixed cutoff) on **training rows only**, then apply it to train and test.
- [ ] **Reversibility assertion (DeepPrep §5.3):** `normalize_categories(corrupt_fragment(df)) == df` exactly on the full column. A scenario is only valid if this passes.
- [ ] Profiler gets a new field: `near_duplicate_categories` per column (the number of raw unique values minus the number of unique normalized keys). **Without it the planner has no signal to try `normalize_categories`**, and the demo commit would depend on luck.
- **Done when:** the reversibility test passes at 30% rate × 30 variants, and the profiler flags the corrupted column.

### Phase 3 — Model as a declared evaluator input, then FREEZE (60 min)
- [ ] `config.EVAL_MODELS = ["rf", "lr"]`, plus a model factory in the evaluator. LR runs as `Pipeline(StandardScaler, LogisticRegression(max_iter=...))`, fit inside each fold.
- [ ] Leak test 1: an in-code assertion that the scaler is fit only on training indices.
- [ ] Leak test 2: the LR as-is baseline equals sklearn `cross_val_score` on the same fixed folds (to within rounding).
- [ ] Leak test 3 (sanity only): as-is vs as-is gives a delta of exactly 0 for both models.
- [ ] Add AUC as a reported secondary metric only. It never gates.
- [ ] Freeze: record the evaluator.py SHA-256 in Documentation.md. Any later change requires a changelog entry.
- **Done when:** all 3 tests pass and the hash is recorded.

---

## NEXT SESSION(S)

### Phase 4 — Pilot, pre-declared rule, screen
- [ ] Pilot one scenario (the target from Phase 1, 20% rate, 15 variants, RF). **Record only the SE of the per-fold differences. Don't look at the mean delta.**
- [ ] Write `Documents/SELECTION_RULE.md` **before screening**, and timestamp it. Draft: *"Screen in the order rate {10,20,30}% × variants {5,15,30} × model {RF, LR}. Demo scenario = the first cell where the correct repair's gain ≥ max(pipeline threshold + 0.84·SE, 0.02 F1) AND at least one plausible wrong repair (fill_mode or drop_rows) has a delta ≤ 0. All cells are reported."*
- [ ] Screen fragmentation (both models). Screen mixed units (age in months for a fraction of rows) with **LR only**; label it as the model-dependence scenario.
- [ ] Correct the family for two models: report RF and LR as separate families.
- **Done when:** a results table + PNG exist for every cell, and the chosen cell is named under the rule.

### Phase 5 — Full Groq pipeline on the chosen scenario
- [ ] The planner must not be told about the corruption. It only sees profiler output.
- [ ] Expected: a wrong repair is tried → rolled back; `normalize_categories` → committed. Log real numbers.
- [ ] Re-run real Adult: still commits nothing (regression check).

### Phase 6 — Explain module + demo output (guide priority)
- [ ] `explain.py`: one Groq call per run that turns the audit JSON into a plain-English rationale for each iteration. It must quote the numbers from the audit log, never generate its own.
- [ ] Output: one per-iteration table (iteration · column · operation · planner reason · Δ ± SE · threshold · COMMIT/ROLLBACK · explanation), plus a one-line headline (baseline → final F1). Use console `rich` plus an HTML report.
- [ ] Three demo runs: synthetic control (commit + rollback), real Adult (correctly nothing), LR mixed-units (model dependence).

### Phase 7 — Novel add-on for the demo: planner-critic (if time)
- [ ] A second Groq call reviews each proposal before execution: approve, or veto with a reason.
- [ ] Pre-declared metric: the number of evaluator calls needed to reach the correct commit, with vs without the critic, on the synthetic scenario (several seeds).
- [ ] Check the literature before calling it novel (multi-agent debate: Du et al., arXiv:2305.14325).

---

## FINAL PRODUCT (after the demo)
1. **Ensemble error detection** (Raha rationale): replaces the IQR check, and feeds the planner real error signals, not just nulls.
2. **A real dataset where cleaning measurably helps.** The guide wants a meaningful real result; the synthetic control doesn't provide it.
3. Backtracking over committed ops (the cheap version of DeepPrep's tree idea: re-test an earlier commit after later ones).
4. Optional: contextual bandit trained on the screening-grid episodes and tested on held-out scenarios.
5. Metric switch (AUC/log-loss as the gate) only with a full re-run of the earlier results.

## Rules that stay on
- No scenario, metric or model is chosen after seeing its result without a written rule.
- Evaluator frozen after Phase 3; any change → changelog + re-run the leak tests.
- Every synthetic result is labelled "synthetic positive control" on screen.
