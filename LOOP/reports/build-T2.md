# build-T2 (Explain guard check, report only)

No guard logic or code changed. Groq called via the existing path (`explain._groq_interpret`, config key; `.env` not read). HTML not written (`write_html=False`), no logs modified. Pre-field logs (29 Sep) skipped; SYNTHETIC_DRYRUN_TEST logs not used.

## Table (live Groq note, `openai/gpt-oss-20b`)
| Log | Scenario | Notes requested | Passed guard | Rejected | Summary note |
|---|---|---|---|---|---|
| run_20260930T060306Z | real_adult | 15 | 15 | none | passed |
| run_20260930T093717Z | synthetic_injection (study C3, 15% age sentinel, seed 203) | 9 | 9 | none | passed |
| run_20260930T112347Z | synthetic_injection (frag_occupation + sentinel_age) | 15 | 15 | none | passed |
| run_20261004T141619Z | synthetic_D1_demo (seed 201) | 4 | 4 | none | passed |

Total 43/43 notes and 4/4 summaries passed; 0 rejected. No API error.

## False rejections
None (nothing was rejected).

## False passes (guard passed a note that is wrong or misleading)
The guard checks magnitudes (`abs`) and identifiers only, so it cannot see sign or context. Four cases:

1. Sign blindness, run_20260930T060306Z, iterations 6, 8, 9. Log: delta -0.0006 / -0.0007 / -0.0001, bar +0.0006 / +0.0007 / +0.0001. Notes:
   - "Delta -0.0006 equals bar 0.0006, no improvement."
   - "Delta -0.0007 equals bar 0.0007, no improvement." (iter 8)
   - "Delta -0.0001 equals bar 0.0001, no improvement." (iter 9)
   "Equals bar" is false (a negative delta is far below the positive bar); passed because the guard compares abs values. Conclusion "no improvement" is right.
2. Context omission, run_20261004T141619Z, iteration 1: "Normalization of occupation categories produced a 0.0005 increase, below the 0.0006 threshold, so no measurable improvement." Log verdict: STAGED, then COMMITTED with its chain. The numbers are correct alone but the note reads as if the op did nothing; the run summary repeats it ("The first operation showed no measurable effect") although occupation=normalize_categories is in the final committed set.
3. Wording against the system rule, run_20260930T093717Z (iterations 1-5, 7-10 all begin "Contradicts:"), e.g. iteration 1: "Contradicts: delta +0.0011 equals bar, 3.7 SE, not distinguishable from noise." The system prompt allows "contradicts" only if the planner reason predicted an improvement; these reasons (e.g. iter 4 "14 rows are exact copies ... need removal") only describe a defect. Also "3.7 SE ... not distinguishable from noise" reads oddly: it quotes the log's verdict text (100% of the Bonferroni bar), where the bar is higher than 3.7 SE would suggest. Numbers all in the log, so the guard passes.
4. Iteration 7/8 in the same run: "Contradicts: delta -0.0010 is not better than baseline, 0.0006 bar." Numbers fine; same "Contradicts" over-claim as item 3.

## Takeaway (for Akira, no change made)
Guard works as designed on numbers and identifiers (no false rejections, no invented numbers or columns). Residual risk is semantic: sign, "equals", and chain-context. Options if wanted (need Akira's OK, not done): compare signed deltas for phrases like "equals/exceeds/below bar"; instruct the model to mention chain-commit status; ban "contradicts" unless the reason contains an improvement prediction. Sample is 4 runs, one seed per scenario; not a rate estimate.
