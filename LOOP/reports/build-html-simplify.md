# build-html-simplify

## Before
Report opened with a jargon headline ("2 of 3 chain(s) committed (col=op...). neg-Brier -0.1171 -> -0.1062"), five stat tiles, then one big table per chain with planner quotes, delta/bar gauges, "COMMIT - delta +0.0005 cleared the bar 0.0006, 2.5 SE" verdicts.

## After (render_html in aeterna_qa/modules/explain.py only)
1. Synthetic banner (label kept) + one-line note that problems were planted on purpose.
2. Plain headline: "We checked 4 possible fixes to your data. 3 were kept, the rest were undone because they did not clearly help." + overall sentence ("somewhat cleaner ... This is evidence, not proof.").
3. "What was fixed": one card per kept fix, e.g. "Replaced placeholder values in capital.gain with the typical value / Effect: prediction accuracy improved noticeably" (noticeably = delta >= 3x bar; else slightly).
4. "What was tried but undone (N)": collapsed list, plain reason per line.
5. "How to read this" glossary (Brier/F1 per run metric, keep, undo, bar, synthetic).
6. ONE collapsed "Technical details": stats, ops, planner quotes, gauges, verdict text, LLM tallies, model.
Groq notes (guard unchanged) appear as "Assistant's note". Old logs: card reads "A group of 5 fixes was kept ... not recorded in this older log". Not changed: verdicts, guard, evaluator, audit schema, console.

## Verification
Regenerated offline: run_20260930T113058Z (3 cards, 1 undone: dedupe_rows), run_20260930T112347Z (1 card, 15 undone), run_20260929T042640Z (old log, renders). Main-view text read from HTML source; op names/neg-Brier appear only inside Technical details.
Note: report_run_20260930T112347Z.html (untracked) was overwritten by the new format; the throwaway old-log report was deleted; tracked report_run_20260930T113058Z.html overwritten intentionally.

Tests (all pass): frozen_check exit 0 ("clean (baseline 2dae093)"); ops_tests "all passed"; evaluator_tests "ALL PASS - LR evaluator may be frozen"; explain_tests "all passed"; demo_tests "all passed".
