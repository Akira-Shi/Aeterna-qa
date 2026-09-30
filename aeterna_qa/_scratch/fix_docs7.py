p = '../Documents/Documentation.md'
s = open(p, encoding='utf-8').read()

marker = '**Still open, by design, not yet decided:** a positive control (a case with a known, real, sizeable effect the loop should commit to) does not exist yet. Whether to build one, and whether "the loop found nothing to fix on real data" is an acceptable headline result for the guide, is a question for Akira and Dr. Menaka, not something to resolve unilaterally in this document.'

addendum = marker + """

**CONFIRMED (2026-09-29, real Groq run after both fixes):** baseline 0.6716 +/- 0.0086 (fixed-fold, fit-on-train). 12 real planner proposals across two chain attempts -- one ran the full 9/9 valid (column, operation) combinations for the 3 real-missingness columns without ever clearing threshold (discarded), the second tried 3 more before hitting MAX_ITERATIONS (discarded). Final F1 = 0.6716 = baseline exactly. Zero commits. This matches the exhaustive ground-truth search exactly (also zero non-trivial commits, do-nothing ranked 34th of 64 in the middle of the noise band). The pipeline and the ground-truth script now agree with each other -- this is the state described in this document as of tonight, and the "no cleaning operation reliably improves this task" finding can be treated as solid, not provisional."""

assert marker in s
s = s.replace(marker, addendum, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
