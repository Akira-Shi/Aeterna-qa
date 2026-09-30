p = '../Documents/Documentation.md'
s = open(p, encoding='utf-8').read()

marker = '### 2026-09-29 (night) -- RETRACTION: the CV-hardened "real accept" was a measurement artifact'
assert marker in s

new_entry = """### 2026-09-29 (later that night) -- SECOND RETRACTION: the fixed-fold "commit" was also wrong, two more real bugs found and fixed

The fixed-fold fix below was itself re-reviewed and two more real, confirmed bugs were found before it was trusted:

1. **Fill-type operations were applied globally before fold-splitting.** Confirmed by direct inspection: after applying fill_mode to `workclass` globally, the training portion of a fold had 0 nulls in that column while the test portion (drawn from raw, untouched data) still had 376. Training on "no missingness" and testing on "real missingness" is not an evaluation of mode imputation -- it's an incoherent comparison. **Fix:** `executor.fit_and_apply` now fits any needed statistic (mean/median/mode/clip-bounds) from a fold's TRAINING rows only, then applies that same value to both that fold's train and test rows -- matching real deployment (fit once, apply to new data as it arrives). `drop_rows` remains training-only, exactly as before; a test row still missing the value keeps it and falls to the model's own missingness handling (documented explicitly now, not left implicit).
2. **The SE was naive and too small.** k-fold (let alone repeated k-fold) training sets overlap heavily -- roughly 75% of rows shared between any two folds' training sets here -- so they are not independent samples, and `std(deltas)/sqrt(n)` understates real uncertainty. **Fix:** `evaluator.paired_delta_corrected` implements the Nadeau-Bengio (2003) corrected-resampled variance (~2.2x the naive SE for this project's 5-fold x 3-repeat setup), and `evaluator.commit_threshold` uses a t-distribution critical value (not z -- with ~14 degrees of freedom the gap matters) at a Bonferroni-corrected alpha. Both are documented in code as literature-grounded but approximate -- true sequential/optional-stopping control across a staged run (deciding to keep testing chains until one passes) is a further, unresolved refinement, correctly flagged as lower priority than the fit/apply bug above.

**A real run under the STILL-BROKEN version of fix #1 above (before this correction) committed a chain at delta=+0.0028 against a threshold of 0.0026 -- directly contradicting the "leave the data alone" conclusion from the previous retraction entry, in the same conversation, within the same evening.** That contradiction is exactly what exposed bugs #1 and #2 above -- a guide reading the doc and a run log together would have caught it immediately, and did, by way of external review before it reached that stage.

**Re-run results after both fixes, exhaustive search (the only one re-run so far -- the real Groq-driven pipeline still needs a live run to confirm agreement):** true as-is baseline (fixed-fold, fit-on-train) = 0.6733 +/- 0.0082. Across all 64 combinations, the best result is +0.0037 (workclass=fill_unknown, occupation=drop_rows, native.country=fill_unknown), against a threshold of 0.0292 for that specific combination's own corrected SE -- nowhere close. **Zero of the 64 combinations clear their corrected threshold** (the one technical "YES" in the ranked table is the baseline compared against itself, a trivial degenerate case). Do-nothing ranks 34th of 64, in the exact middle of a tight, noise-sized band. This is now a clean, internally consistent result -- not one more roughly-plausible number to be doubted further without new evidence.

**Still open, by design, not yet decided:** a positive control (a case with a known, real, sizeable effect the loop should commit to) does not exist yet. Whether to build one, and whether "the loop found nothing to fix on real data" is an acceptable headline result for the guide, is a question for Akira and Dr. Menaka, not something to resolve unilaterally in this document.

"""

s = s.replace(marker, new_entry + marker, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
