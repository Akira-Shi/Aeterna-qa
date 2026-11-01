# NOVELTY.md - AETERNA-QA vs prior work (phase 2, 2026-11-01)

Scope and honesty note. This is a limited comparison of 7 named systems plus the 3 papers in `Resources/`. Most prior systems were verified from the arXiv abstract page only, not the full paper. Any cell or claim not confirmed from the paper itself is marked "(unverified)". Absence of a feature in an abstract is NOT evidence that the paper lacks it, so those cells say "(unverified)", not "no". No retracted numbers are cited.

## Corrections to the brief
- **Du et al., arXiv:2305.14325** is "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (Du, Li, Torralba, Tenenbaum, Mordatch). It is not a data-cleaning system. It is kept only as prior art for multi-LLM critique (section 4), and its table row is N/A. If a different Du et al. paper was intended, the ID is needed.
- "CPClean" was verified through its source paper, Karlas et al., "Nearest Neighbor Classifiers over Incomplete Information: From Certain Answers to Certain Predictions" (arXiv:2005.05117). The abstract names CPClean but the page gives no venue.

## 1. Comparison table

Legend: yes = confirmed in the source read; no = confirmed absent by the nature of the method; (unverified) = not confirmed from the paper itself.

| System | Statistical commit gate? | Multiple-comparison correction? | Rollback? | LLM planner? | Constrained op menu? | Audit log? | Real-data eval? |
|---|---|---|---|---|---|---|---|
| ActiveClean (2016) [1] | no commit gate. Abstract claims an accuracy guarantee on partially cleaned data; its form is (unverified) | (unverified) | (unverified) | no | (unverified) | (unverified) | yes (5 real datasets incl. UCI Adult; real and synthetic errors) |
| BoostClean (2017) [2] | partial: checks improvement against clean test labels; no statistical test stated in abstract (unverified) | (unverified) | (unverified) | no (Word2Vec-based detector, not an LLM) | yes: ensemble chosen from an extensible library of detector/repair pairs | (unverified) | yes (12 datasets: Kaggle, UCI, production) |
| Learn2Clean (2019) [3] | (unverified) | (unverified) | (unverified) | no (Q-learning) | partial: picks a sequence from a fixed set of preprocessing tasks (unverified in detail) | (unverified) | yes, "preliminary" on real-world data (from search snippet) |
| CPClean (Karlas et al.) [4] | no: uses a "certain prediction" criterion, not a statistical test | (unverified) | (unverified) | no | (unverified) | (unverified) | (unverified) |
| DiffPrep (SIGMOD 2023) [5] | no: bi-level optimisation, not a commit test (unverified beyond abstract) | (unverified) | (unverified) | no | yes: searches a defined space of preprocessing pipelines | (unverified) | yes (18 real datasets) |
| CleanAgent (2024) [6] | (unverified) | (unverified) | (unverified) | yes (LLM agents) | yes: LLM writes code against declarative Dataprep.Clean column-type APIs | (unverified) | demo web app on real datasets; no evaluation described on the abstract page |
| Du et al. 2305.14325 [7] | N/A (not data cleaning) | N/A | N/A | N/A | N/A | N/A | N/A |
| DeepPrep (2026, Resources) [8] | no (no commit test found in text searched) | no (none found) | yes in a different sense: tree-based search can revert to an earlier node and revise; this is search backtracking, not undoing a committed data change | yes (trained LLM agent) | partial: 31 operators plus a free-form program-synthesis operator | (unverified) | yes (real ADP benchmarks) |
| Bendinelli et al. 2025 (Resources) [9] | no statistical test. LLM submits datasets for a held-out score, keeps the best-scoring one, stops on a token budget | none found | partial: all versions stored, best kept (selection, not a gate) | yes (free-form Python via IPython) | no (free code) | none described beyond stored dataset versions (unverified) | Kaggle datasets with intentionally injected errors (synthetic damage) |
| IterClean (Ni et al., Resources) [10] | no: LLM "verifier" checks detector rationales; no statistical test | none found | none found | yes (detector, verifier, repairer roles) | no (free LLM output) | (unverified) | yes (Hospital, Flights, Beers, plus a synthetic-error set); scored by cell-level F1 against ground truth, not a downstream-model gate |
| **AETERNA-QA** | yes: fixed 5x3 CV folds, Nadeau-Bengio corrected SE, Brier gate, F1 reported beside it | yes: Bonferroni-corrected commit bar | yes: verify then rollback if gate fails | yes: Groq `openai/gpt-oss-20b`, but see note | yes: planner picks only from a fixed op menu | yes: JSON run log plus HTML report | synthetic scenarios C1-C5 (labelled synthetic) plus real Adult `?` values, where nothing commits (matches ground truth) |

Note on the LLM cell for AETERNA-QA: in the registered study the rule planner and the Groq planner gave identical outcomes in 15/15 runs. The LLM planner shows an efficiency difference only (correct commit on evaluation 1.0 vs 1.55). It gives no accuracy advantage.

## 2. Where prior work already covers an item
- **LLM-driven cleaning agents:** covered (CleanAgent, DeepPrep, Bendinelli, IterClean).
- **Constrained or declarative operator spaces:** covered (BoostClean library, DiffPrep search space, CleanAgent APIs, DeepPrep operator set).
- **Evaluate a cleaning step by downstream model performance on held-out data:** covered at least by BoostClean and Bendinelli, and the idea of cleaning for ML accuracy goes back to ActiveClean.
- **Iterative detect/verify/repair loops with an LLM verifier:** covered (IterClean).
- **Keep-best / backtracking over candidate states:** partly covered (Bendinelli keeps the best dataset; DeepPrep reverts within its search tree).
- **Synthetic error injection for evaluation:** covered (Bendinelli, IterClean).

## 3. What looks different (and what does not)
- In the sources read, none of the papers uses an explicit **statistical decision rule** (corrected SE plus a family-wise correction) to decide whether to commit each repair, with rollback on failure. This is the only item where AETERNA-QA looks distinct. It rests on a limited sample of papers, and abstract-only reads cannot rule out that BoostClean, ActiveClean, CPClean, DiffPrep or Learn2Clean have something similar, so it is a "to our knowledge, among works reviewed" claim.
- The **audit log** is engineering, not a research contribution.
- The **menu constraint** is not new on its own (see section 2).
- The **LLM** adds efficiency only in our own study, so the LLM is not part of the novelty.
- Scope limits: one dataset (Adult), damage authored by us, 15 runs, no result yet on genuinely dirty real data. The false-commit labels come from mis-set pilot expectations, as recorded in `RESULTS.md`.

## 4. Conclusions

**(1) One-sentence novelty claim.** To our knowledge among the systems reviewed here, AETERNA-QA is a menu-constrained cleaning agent in which every repair commits only if a pre-registered, fixed-fold, corrected-SE cross-validated gate with a Bonferroni-corrected bar says it helps, and is otherwise rolled back and logged, which we test with labelled synthetic damage and a real-data negative check.

**(2) Is a planner-critic step novel? No.** Reasons:
- Generic LLM critique loops are established prior art: Self-Refine [11] (self-critique then revise), Reflexion [12] (verbal feedback memory), CRITIC [13] (tool-interactive critique then revise), and multiagent debate [7].
- In cleaning specifically, IterClean [10] already has an LLM verifier that filters the detector's findings by rationale, inside a detect-verify-repair loop. Bendinelli [9] already feeds held-out performance back to the LLM each iteration. DeepPrep [8] feeds execution feedback back and revises earlier decisions.
- AETERNA-QA already has a non-LLM verifier (the statistical gate), which is stronger than an LLM critic as a safety check. An LLM critic placed before the gate would be an incremental variant of IterClean's verifier.
- It could only count as a contribution if shown empirically (for example fewer wasted gate evaluations at equal commit quality), and as a narrow engineering claim, not a research-novelty claim. Since the planner is not the source of accuracy in our study (15/15 identical outcomes), expected benefit is small. Any such claim would be a new research claim and needs Akira's sign-off and a written rule before testing.

## 5. Items marked (unverified)
- All gate, correction, rollback and audit-log cells for ActiveClean, BoostClean, Learn2Clean, CPClean, DiffPrep, CleanAgent unless stated: only abstracts or search snippets were read.
- ActiveClean: form of its accuracy guarantee.
- Learn2Clean: the "fixed task set" detail and the real-data evaluation scope (search snippet only).
- CPClean: datasets, venue, rollback and real-data evaluation.
- CleanAgent: any evaluation.
- DeepPrep, IterClean, Bendinelli: audit-log cells. Their absence cells (no test, no correction) come from keyword search of the extracted text plus reading the method sections, not a full read.
- Whether any system outside this list covers the statistical-gate item.

## Sources
1. ActiveClean (Krishnan et al., 2016): https://arxiv.org/abs/1601.03797
2. BoostClean (Krishnan et al., 2017): https://arxiv.org/abs/1711.01299
3. Learn2Clean (Berti-Equille, WWW 2019): https://hal.archives-ouvertes.fr/hal-02197265 (also https://laureberti.github.io/website/pub/www19.pdf)
4. CPClean / Certain Predictions (Karlas et al., 2020): https://arxiv.org/abs/2005.05117
5. DiffPrep (Li, Chen, Chu, Rong, SIGMOD 2023): https://arxiv.org/abs/2308.10915
6. CleanAgent (Qi, Miao, Wang, 2024): https://arxiv.org/abs/2403.08291
7. Du et al., Multiagent Debate: https://arxiv.org/abs/2305.14325
8. DeepPrep (Fan et al., 2026): https://arxiv.org/abs/2602.07371 (local PDF in `Resources/`)
9. Bendinelli, Dox, Holz, Exploring LLM Agents for Cleaning Tabular ML Datasets (ICLR 2025 workshop): https://arxiv.org/abs/2503.06664 (local PDF in `Resources/`)
10. IterClean (Ni et al.): local `Resources/Iterative Cleaning with Verification Loops.pdf`; online URL not fetched (unverified)
11. Self-Refine: https://arxiv.org/abs/2303.17651
12. Reflexion: https://arxiv.org/abs/2303.11366
13. CRITIC: https://arxiv.org/abs/2305.11738
