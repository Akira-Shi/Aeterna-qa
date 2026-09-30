p = '../Documents/Documentation.md'
s = open(p, encoding='utf-8').read()

# --- Fix stale module table cells the review caught ---
old_eval_row = "| Evaluator | `evaluator.py` | Working | 2026-09-29 | F1 baseline on real `?` columns, random_state=42. Single-split only -- CV hardening still pending. |"
new_eval_row = "| Evaluator | `evaluator.py` | Working | 2026-09-29 (3rd revision) | Fixed row-ID folds computed once from raw data (make_fixed_folds), paired per-fold delta (paired_delta) vs. a naive re-CV'd comparison -- see changelog, a real test-set leakage bug was found and fixed here. |"
assert old_eval_row in s
s = s.replace(old_eval_row, new_eval_row)

old_orch_row = "| Orchestrator | `pipeline.py` | Working | 2026-09-29 | Runs up to MAX_ITERATIONS=6 detect->plan->execute->verify->rollback iterations; real end-to-end run confirmed (see changelog) |"
new_orch_row = "| Orchestrator | `pipeline.py` | Working | 2026-09-29 (3rd revision) | Runs up to MAX_ITERATIONS=12 detect->plan->execute->verify->stage->commit/discard iterations against FIXED folds; a real committed result was later found to be a measurement artifact and the evaluator was rebuilt -- see changelog. |"
assert old_orch_row in s
s = s.replace(old_orch_row, new_orch_row)

# --- Insert the correction as the new top changelog entry ---
old_changelog_head = "### 2026-09-29 (evening) -- CV-hardening + multi-op combination fix, real accept confirmed"
new_entry = """### 2026-09-29 (night) -- RETRACTION: the CV-hardened "real accept" was a measurement artifact

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

"""
assert old_changelog_head in s
s = s.replace(old_changelog_head, new_entry + old_changelog_head, 1)

open(p, 'w', encoding='utf-8').write(s)
print('ok')
