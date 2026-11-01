# build-guard (Explain guard: reach-verb + 3-token negation, sign, verdict, "Contradicts")

Live Groq (`openai/gpt-oss-20b`) via `explain.explain_run`, config path only, `.env` not read, no HTML written.

## Per-log counts
| Log | Requested | Passed | Rejected |
|---|---|---|---|
| run_20260930T060306Z | 15 | 12 | 3 |
| run_20260930T093717Z | 9 | 9 | 0 |
| run_20260930T112347Z | 15 | 15 | 0 |
| run_20261004T141619Z | 4 | 3 | 1 |
| Total | 43 | 39 | 4 |

Summaries: 4/4 passed. Fallback rate: 4/43 = 9.3% (limit 10%).

## Rejections (verbatim)
1. 060306Z iter 6 [reach rule]: "Filling workclass with mode lowered neg-Brier by -0.0006, equal to the 0.0006 bar, indicating no improvement." Verdict: CORRECT (delta -0.0006 is below the +0.0006 bar, not equal; same class as known false pass 1). Arguable reading: magnitude equals bar, but wording is misleading.
2. 060306Z iter 8 [reach rule]: "Dropping rows with missing workclass decreased neg-Brier by -0.0007, equal to the 0.0007 bar, indicating no improvement." Verdict: CORRECT (same).
3. 060306Z iter 9 [reach rule]: "Filling native.country with mode lowered neg-Brier by -0.0001, equal to the 0.0001 bar, showing no benefit." Verdict: CORRECT (same).
4. 141619Z iter 1 [verdict rule]: "The operation produced a +0.0005 delta, below the 0.0006 bar, indicating no significant improvement." Verdict: CORRECT (already judged: op was committed with its chain).

False rejections: 0. The "Contradicts" guard did not fire live (prompt change worked; 093717Z 9/9 passed).
Note: the 112347Z "does not exceed" notes passed this run (negation exemption), but Groq is nondeterministic.

## Tests
frozen_check exit 0; ops_tests, evaluator_tests, explain_tests all pass. Known false pass 3 (093717Z iter 1) rejected by test.
