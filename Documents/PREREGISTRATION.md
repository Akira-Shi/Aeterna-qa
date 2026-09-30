# AETERNA-QA — Pre-registration of the controlled-corruption study

**Status: SIGNED v1, 2026-09-30 (Akira). Nothing in sections 3–9 has been run on the evaluation partition. Amendments in section 12 override the text above where they conflict.**
**Rule once signed:** this file is frozen. Any change is a dated entry in section 12 (Amendments), never an edit above it. Results go in a separate file (`RESULTS.md`), not here.

Confidence tags: (Certain) measured or verified; (Likely) strong inference; (Guessing) unverified.

---

## 1. What this study can and cannot claim

- **Can claim:** on real Adult data with *known, injected* damage, the agent (a) detects the damage, (b) commits the repair that undoes it when the model-based gate says it helps, (c) rejects plausible-looking wrong repairs and harmless damage, and (d) the repair restores the true values to a stated accuracy.
- **Cannot claim:** that the agent works on arbitrary real dirty tables. One dataset, synthetic damage that we designed. We designed both the damage and the repair menu; sections 6 and 7 exist to limit how much that can flatter the result.
- **Synthetic is labelled synthetic everywhere** (banner, audit log `scenario`, file names, report titles).

## 2. Data

| Item | Value |
|---|---|
| Base | Adult, rows with no `?` in any column (Certain: 30,162 rows, 24.89% positive) |
| Real quirks kept in the base (Certain, verified) | 23 exact duplicate rows; 1 feature-group with two different income labels; `capital.gain = 99999` on 148 rows; `hours.per.week = 99` on 78; `age = 90` on 35; `hours.per.week <= 1` on 7; `Husband`+`Female` 1 row, `Wife`+`Male` 1 row; `education` vs `education.num` mismatches 0 |
| Naming rule | `99999`, `99`, `90` are **censored / top-coded values** ("this much or more"), not placeholders. They are real decoys. The write-up must not call them errors. The detector's current label "sentinel" for `capital.gain=99999` is a hypothesis label only (see amendment slot 12). |
| Split | One split, before anything else: 20% **pilot** / 80% **eval**. Stratified on income; fixed seed `20261001`. Rows are assigned as **groups** keyed on the full feature vector, so the 23 duplicate rows and the one conflicting pair never straddle the split. |
| Folds | 5-fold × 3-repeat fixed folds, computed on the **eval** partition only, after the split. Pilot uses its own folds on the pilot partition. |
| Real `?` condition | Kept as a separate, already-observed condition on the full 32,561 rows (see section 11). It is exempt from the split because its results were seen before this document. |

## 3. Evaluators and gate

- **Models (both, every scenario, never pooled):** RandomForest (as currently coded) and StandardScaler+LogisticRegression (frozen; both leak tests pass — Certain).
- **Gate metric (proposed, needs sign-off): Brier score** on each held-out fold's predicted probabilities, sign-flipped so a positive delta means improvement. Reasons: proper scoring rule; bounded; finite at p=0 or 1. (Certain, checked) 22.6% of RF test probabilities are exactly 0 or 1 on the base data, so RF log-loss would be governed by an arbitrary clip constant; RF Brier 0.1025 vs LR Brier 0.1032, comparable. **Log-loss with ε=1e-6 clipping is declared as the fallback** only if Brier is rejected at sign-off.
- **F1 is reported next to every decision** so earlier numbers stay comparable. It is not the gate.
- **Commit rule:** unchanged machinery — Nadeau-Bengio corrected paired SE, t-critical at Bonferroni α = 0.05 / (number of candidate ops in that run), and `delta > 0 and delta >= bar` (`clears_bar`). Greedy chain: an op joins the chain only if it improves the chain's cumulative delta.
- **Whose decision:** the metric switch is Akira's, not the guide's (the guide accepts any metric — corrected from an earlier misstatement).

## 4. Corruption types (declared before any eval-partition result)

Each scenario: one injected defect on the eval partition, ground truth recorded in a manifest the agent never sees.

| ID | Defect | Column | Mechanism | Severity ladder (fraction of rows) | Truth recorded |
|---|---|---|---|---|---|
| C1 | Category fragmentation | `occupation` | re-spell: case change, hyphen→space, upper-case; a second variant adds one-character typos | 10%, 30%, 60% | original label per row |
| C2 | Mixed units | `age` | fraction of rows multiplied by 12 (years → months) | 5%, 15%, 30% | original value per row |
| C3 | Missing-value code | `age` | fraction overwritten with `999` (never occurs naturally — Certain: 0 rows, max age 90) | 3%, 8%, 15% | original value per row |
| C4 | Harmless decoy | `native.country` | fragmentation as C1 (US = 91% of rows, little signal) | 30% | original label per row |

- Injected sentinel/unit values must never coincide with a value that occurs naturally, so injected rows are always separable from real censored rows when grading.
- Duplicates are **not** injected (duplicates straddling CV folds inflate scores; measured separately).
- C2 requires a new repair op (`rescale_units`). If it is not built and tested before the pilot, C2 is dropped and that is recorded in section 12, not silently omitted.

## 5. Repair menu and plausible wrong fixes

Menu is the current `OPERATION_MENU` plus `rescale_units` (planned). The agent never sees which op is "right". Wrong-but-plausible repairs that must appear in every scenario's candidate list:

| Scenario | Correct repair | Plausible wrong repairs the gate should not commit |
|---|---|---|
| C1 | `normalize_categories` | `fill_mode`, `drop_rows` on the same column |
| C2 | `rescale_units` | `clip_outliers`, `sentinel_to_median` |
| C3 | `sentinel_to_median` | `clip_outliers` on `age`; `sentinel_to_median` on `capital.gain` (measured harmful on F1: −0.004, Certain) |
| C4 | none needed | `normalize_categories` on `native.country` (should be rolled back) |

Real decoys present in every scenario (untouched base): `dedupe_rows`, clip/sentinel ops on `capital.gain`, `hours.per.week`, `age` top-coding.

## 6. Pilot and severity rule (pilot partition only)

1. For each scenario and each ladder level, inject on the **pilot** partition with **3 injection seeds** (`101, 102, 103`), run each model, and record the best-correct-repair's mean gain (Brier) and its paired SE.
2. **Scale the noise to the eval partition.** SE shrinks about with √n, so `bar_eval_est = bar_pilot × √(n_pilot / n_eval)` (≈ ×0.5 for a 20/80 split); the same factor is applied to the SE inside `MDE_eval_est = bar_eval_est + 0.84 × SE_pilot × √(n_pilot / n_eval)`. Effect size is *not* scaled (it is a property of the damage). Declared choice: **scaled, not conservative-unscaled**; the unscaled figure is reported alongside.
3. **Severity chosen** = the smallest ladder level whose mean pilot effect across the 3 seeds is ≥ `MDE_eval_est`. If no level reaches it, the scenario is run at the top level and is designated **not detectable at this gate** for that model. The ladder is **not** extended after seeing results.
4. **Designation rule (per scenario × model):** *positive* (a commit is expected) if the pilot effect at the chosen level ≥ `MDE_eval_est`; otherwise *negative* (a rollback is expected). Expected outcomes are therefore set by the pilot, not by hope, and are written into `RESULTS.md` before the eval runs.
5. One gain measurement at one severity does not show a curve shape (paired SE ≈ 0.0025–0.0027, so a 0.0005 difference is noise — see section 10). At least 3 levels × 3 seeds are used for exactly that reason.

## 7. Agent blindness and grading

- **Manifest isolation:** the manifest, the truth column and injection parameters never enter `detectors`, `planner`, `pipeline` decision code or the audit log's planner-visible fields. A test (to be added before the pilot) asserts the planner payload contains only detector findings and the committed/rejected op list.
- **Repair grading (per type, after the agent has finished):**

| Type | Score |
|---|---|
| C1/C4 | exact restoration rate on injected rows; collateral = rows changed that were **not** injected |
| C3 | mean absolute error to the true value on injected rows, vs. a "median-of-column" reference; collateral count |
| C2 | share of injected rows restored within ±0.5 of the true value; collateral count |

## 8. Outcomes and failure conditions (fixed in advance)

- **Primary:** per model, in *positive* scenarios: correct repair committed (yes/no) over the eval seeds; in *negative* scenarios and decoys: nothing committed. Counts reported as k/n, no pooling across models.
- **Secondary:** Brier and F1 change; restoration accuracy; collateral changes.
- A decoy that commits is reported as a **false commit**; a positive scenario that does not commit is reported as a **miss**. Neither is re-run with a changed severity, gate or seed set.
- Eval injection seeds: `201, 202, 203` (disjoint from the pilot seeds).

## 9. Cleaned-file output

When any op commits, write `adult_clean_<scenario>.csv` and a manifest JSON (ops, fitted statistics, rows changed). Fit statistics on the full eval partition, then run a **confirmation** on the pilot partition, corrupted with a fresh seed (`301`) and repaired with the committed, already-fitted ops. This confirmation partition took no part in choosing which repair to commit (it only set severity).

## 10. Disclosure — what has already been seen (not to be used as pilot)

All on the full 32,561-row data, F1 gate unless stated (Certain, logged in `Documentation.md`):

- Real `?` data, RF: 64-combination sweep and pipeline runs — nothing commits; best +0.0022 vs bars ≈ 0.013+.
- Injected spec v1 (occupation 30%, age-999 5%), RF single-op sweep: 0/16 clear. Injected baseline F1 0.6737 vs clean 0.6716.
- Injected spec v1, LR single-op sweep: `age: sentinel_to_median` +0.0074 (SE 0.0027, bar 0.0087); `occupation: normalize_categories` +0.0004.
- Injected spec v2 (age-999 at 8%), LR pipeline, run once: best op +0.0069; nothing committed.
- **Retraction of an earlier claim:** the statement that the linear-in-rate assumption "was wrong (Certain, measured)" is withdrawn. +0.0074 → +0.0069 is a difference of 0.0005 against an SE ≈ 0.0027, i.e. noise. What is actually known: 8% did not reach the +0.0109 that linear extrapolation predicted; whether the curve is flat or the extrapolation was just noisy is **not established** (Likely-flat, not proven).
- A bug where three no-op `fill_unknown` ops "cleared" a zero bar under LR was found and fixed (`clears_bar`).

## 11. Real-data conditions retained

- **Real `?` condition (full 32,561 rows):** must still commit nothing under the Brier gate for both models. This is a **declared check on the metric switch**: if anything commits, that is reported as a finding and investigated before the study proceeds; the gate is not loosened or re-tuned to make it pass.
- Leakage lesson retained: the retracted +0.0175 (drop-rows measured on a test set that shrank with the drops) stays in the write-up as the reason for fixed folds and train-only fitting.

## 12. Amendments (dated; append only)

| Date | Amendment | Reason |
|---|---|---|
| 2026-09-30 | Models: LogisticRegression (StandardScaler) only. RandomForest is dropped from the study; section 3 "both models" and "never pooled" now mean LR alone. | Akira's standing instruction: if LR is better than RF, go entirely with LR. Measured Brier RF 0.1025 vs LR 0.1032 (comparable), and RF was blind to the injected defects (0/16 single-op clears). |
| 2026-09-30 | Gate = Brier (signed off). Log-loss fallback is void. | Akira approved Brier. |
| 2026-09-30 | Build `rescale_units`; C2 stays in the study. | Akira approved. |
| 2026-09-30 | Seeds approved as listed: split 20261001; pilot 101,102,103; eval 201,202,203; confirmation 301. | Sign-off. |
| 2026-09-30 | Staging rule: an op joins the chain only if it improves the chain's delta by at least 25% of its own bar (`MIN_STAGE_GAIN_FRAC`). Commit rule unchanged. | Real-`?` run staged exact-zero no-ops (delta +0.0000, bar 0.0000); staging on noise lets a chain accumulate luck. Set after seeing that run, so it is post-hoc; not tuned further. |
| 2026-09-30 | Real `?` check (section 11), LR + Brier, offline planner, full 32,561 rows: committed nothing. Closest: hours.per.week clip and age clip, +0.0003 vs bar 0.0005. | Declared check passed. |
| 2026-09-30 | Reporting: the recovery fraction (fixed - injected)/(clean - injected) is reported per scenario, using a clean baseline on the same rows. | The 2026-09-30 trial gave about two thirds (0.0010 of 0.0015, one seed, rounded). Not a result. |
| 2026-09-30 | C1: the "second variant with one-character typos" is NOT implemented; C1 uses only case / hyphen / upper-case re-spelling. | No op on the menu can repair typos (`normalize_categories` merges case/space/punctuation only); including them would inject an unfixable defect. |
| 2026-09-30 | Pilot run (C1-C4, seeds 101-103, LR, Brier). Outcome: C1 positive at 10% (effect +0.0019 vs scaled MDE 0.0013); C2 (30%), C3 (15%), C4 (30%) designated NEGATIVE (effects ~+0.0009, below MDE ~0.0011-0.0012). Effects are flat across the whole ladder. | Pilot rule applied as written. |
| 2026-09-30 | Finding behind the flat ladders: `age` carries only 0.00096 Brier in total (destroying it costs that much), so no corruption of `age` can exceed roughly that, which is below the bar. Measured column headroom (pilot partition): capital.gain 0.0121, occupation 0.0030, capital.loss 0.0017, hours.per.week 0.0014, age 0.0010. Clean-data controls: each candidate op on the uncorrupted pilot partition gives delta exactly 0.0000. | Explains C2/C3 negatives; the earlier 'flat in severity' question is answered for age: saturated at the column's whole value. |
| 2026-09-30 | Added scenario **C5**: missing-value code `9999999` in `capital.gain`, ladder 1% / 3% / 6%, correct repair `sentinel_to_median`, plausible wrong repairs `clip_outliers` (refused, IQR 0), `fill_median`. Piloted with the same rule and seeds; C5 positive at 1% (effect +0.0120, MDE 0.0034). C1-C4 kept unchanged. Added after seeing the C1-C4 pilot, before any eval run; chosen because capital.gain is the only column with headroom. Disclosed as post-pilot. | Without C5 the study has one positive scenario and cannot test numeric detection. |

**Was open at sign-off (resolved above except item 4):** (1) Brier vs clipped log-loss as gate; (2) whether to build `rescale_units` (C2) or drop C2; (3) seed lists in sections 2, 6, 8, 9; (4) confirm the detector's `sentinel` label for `capital.gain = 99999` is reworded to "possible censored value" in output text (cosmetic, no behaviour change).

## 13. Threats to validity (stated, not solved)

- We authored both the damage and the repair menu. Mitigations: rules fixed before eval, wrong fixes and a harmless decoy in every run, expected outcomes set by the pilot, a real-data run that must commit nothing.
- One base dataset. Effects may not transfer.
- Multiple-comparison correction is approximate (per-run Bonferroni, not family-wide across scenarios and models).
- Pilot noise scaled by √n is an approximation; the unscaled figure is reported for comparison.
