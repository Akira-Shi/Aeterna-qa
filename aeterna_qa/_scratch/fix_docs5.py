p = '../Documents/Documentation.md'
s = open(p, encoding='utf-8').read()

old = """- IQR outlier_count is unreliable on skewed columns (carried forward from prior build, still true, still unsolved). `clip_outliers` stays in the op menu but isn't the planner's primary lever this milestone.
- RESOLVED (2026-09-29 evening): F1_DELTA_THRESHOLD is no longer a fixed guess -- it's computed each iteration as 2.0x the measured standard error of the current baseline's 5-fold CV scores (config.THRESHOLD_SE_MULTIPLIER). The old fixed 0.005 threshold was shown to be wrong on a real case: it accepted native.country/drop_rows at a measured +0.0067 under a single split, which CV showed was actually -0.0006 (noise).
- Absolute F1 (~0.688 final) is a middling score for Adult Census Income by published benchmarks (untuned RF typically ~0.65-0.70 on the >50K class) -- this is expected and intentional (classifier is deliberately untuned so it's a stable measuring instrument), but flag it proactively to the guide rather than waiting to be asked why it isn't higher.
- RESOLVED (2026-09-29 evening): verification now uses 5-fold CV (calculate_f1_cv) instead of a single train/test split for every accept/commit decision."""

new = """- IQR outlier_count is unreliable on skewed columns (carried forward from prior build, still true, still unsolved). `clip_outliers` stays in the op menu but isn't the planner's primary lever this milestone.
- SUPERSEDED (see the retraction entries in the changelog above, dated 2026-09-29 night): the "2.0x measured SE" threshold and `calculate_f1_cv` were both found to be flawed (test-set leakage, fold reshuffling, naive/uncorrected SE) and have been replaced by `calculate_f1_candidate` (fit-on-train/apply-to-test) with `paired_delta_corrected` (Nadeau-Bengio corrected SE) and `commit_threshold` (t-distribution, Bonferroni-corrected). Do not cite "2.0x SE" or "calculate_f1_cv is used for decisions" as current -- both are retracted.
- Absolute F1 number: do not cite ~0.688 as current -- that number came from the leaky evaluator. The corrected, fit-on-train baseline (fixed-fold) is ~0.673, and the exhaustive ground-truth search (exhaustive_search.py) found NO combination of available operations clears a properly corrected significance bar against that baseline (best: +0.0037, needs to clear a threshold around 0.013-0.04 depending on the combination's own variance). If nothing commits, final F1 is expected to equal the baseline (~0.673), not a higher number -- and that is the correct, honest outcome on this dataset, not a bug.
- OPEN, UNRESOLVED, genuinely undecided: no positive control exists yet -- a case with a known, real, sizeable effect where the loop is expected TO commit (e.g. deliberately corrupting a strong feature like education.num or age). Without one, "the loop commits nothing on real Adult data" cannot be distinguished from "the loop is broken and can never commit." Whether this is a nice-to-have or the centerpiece of the demo depends on whether the guide will accept "the loop correctly found nothing to fix" as a result -- Akira needs to ask the guide before this is built, not after."""

assert old in s, "old block not found"
s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
