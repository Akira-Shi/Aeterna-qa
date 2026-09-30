"""
Orchestrator for AETERNA-QA. The only module that imports the others.

Runs up to config.MAX_ITERATIONS rounds of:
  profile -> plan (Groq) -> evaluate candidate -> commit / stage / discard
against the real '?' missingness in adult.csv, logging every round via
audit.py.

Staged/commit/replace model, sixth revision (2026-09-29, second review of
the night):

Prior revisions, in order: (v1) profiling the staged dataframe blocked
retrying a column's other operation; (v2) fixed that with a replaceable
chain, found a real compounding accept; (v3) found the comparison itself
leaked (drop_rows tested by training AND evaluating on cleaned data;
independently-reshuffled CV runs), fixed with fixed row-ID folds and
paired deltas -- an exhaustive 64-combination ground truth then showed
v3's own "confirmed" accept was itself a leakage artifact; (v4) found two
more bugs -- fill-type operations applied before fold-splitting (a
train/test mismatch, not an evaluation) and a naive, uncorrected SE.
Fixed with executor.fit_and_apply and evaluator.paired_delta_corrected +
commit_threshold; (v5) found a THIRD leak -- committed operations were
still materialized into one global `committed_df`, so a committed
drop_rows permanently shrank every later TEST fold too. Fixed: no more
materialized dataframe used for scoring; `committed_ops` is a plain dict
replayed fresh, per fold, alongside the candidate, via
evaluator.calculate_f1_candidate. Confirmed by a from-scratch exhaustive
re-run: same conclusion (0/64 clear, do-nothing ranks 34th/64).

v6 (this version) fixes a real-run inefficiency found by review of the
first full real (Groq) run under v5: iterations 11-12 of that run
re-proposed and re-evaluated the EXACT SAME chain as iterations 1-2
(same columns, same operations, same numbers -- inevitable, since the
folds and model seed are fixed, so evaluating the same full combination
twice can only ever give the same answer). Root cause: `tried_in_chain`
resets to empty whenever a chain is discarded, and discarded pairs never
get added to `permanently_rejected` (only individually-erroring
proposals did) -- so once a chain resets, the planner is free to walk
into a start-of-chain state it already fully explored in an earlier
attempt THIS SAME RUN. Two costs: wasted iteration budget (this project
only gets MAX_ITERATIONS=12 per run), and each repeat still "spends" one
of the comparisons the Bonferroni correction is sized for, without adding
any information.

Fixed: `evaluated_states` is a set of frozenset({**committed_ops, **chain
at time of evaluation}.items()) recorded after every REAL evaluation this
run (never reset when a chain resets -- it persists for the whole run).
Before each planner call, every dtype-valid, not-yet-tried-in-this-chain
(column, operation) pair is checked: if choosing it would recreate a
FULL combined state (committed_ops + this chain + that pair) already in
evaluated_states, it's added to the exclude list passed to the planner
for that call, on top of the existing tried_in_chain/permanently_rejected
exclusions. This only blocks recreating an identical full combination --
the same pair combined with a DIFFERENT chain context (or once something
different has actually committed, changing committed_ops) is still a
genuinely new state and remains available. A `chain_eval_cache` also maps
the same state key to its already-computed result, so if a duplicate ever
slips through anyway, it's served from cache rather than recomputed.

One clarification (not a bug): this pipeline's commit_threshold uses a
Bonferroni correction sized to config.MAX_ITERATIONS (12 look-backs per
run); exhaustive_search.py uses one sized to its own 64 comparisons. The
two scripts' printed threshold values are correctly on different scales
for that reason -- compare outcomes (does anything commit / clear), not
the raw threshold numbers, across the two scripts.

Usage: python -m modules.pipeline [--inject] [--offline-planner]
"""
from . import config
from .evaluator import (
    load_raw_dataset, make_fixed_folds, calculate_f1_candidate, materialize,
    paired_delta_corrected, commit_threshold, clears_bar,
)
from .detectors import detect
from .planner import plan, plan_offline, remaining_options
from .injection import inject, DECLARED_SPEC
from . import audit


def run(use_injection: bool = False, offline_planner: bool = False, raw_df=None, manifest=None,
        label: str | None = None, scenario_meta: dict | None = None, run_explain: bool = True,
        scenario_name: str | None = None) -> dict:
    """use_injection: corrupt the data with injection.DECLARED_SPEC first (SYNTHETIC,
    labelled as such everywhere). offline_planner: use the rule-based planner instead
    of Groq. Real-data runs use neither."""
    external = raw_df is not None   # study.py passes an already-injected partition + its manifest
    if external:
        use_injection = manifest is not None
    else:
        raw_df = load_raw_dataset()
        manifest = None
    if use_injection and not external:
        raw_df, manifest = inject(raw_df)
        print("*** SYNTHETIC RUN: declared corruption injected (see injection.DECLARED_SPEC). "
              "Not real data. ***")
        for m in (manifest if external else DECLARED_SPEC):
            print(f"    injected {m['id']}: {m['kind']} in '{m['column']}' at {m['rate']:.0%}")
        print()
    folds = make_fixed_folds(raw_df)
    print(f"Fixed {config.CV_FOLDS}-fold x {config.CV_REPEATS}-repeat evaluation folds computed "
          f"from the raw dataset ({len(folds)} total train/test splits, reused for every comparison "
          f"in this run). Bonferroni-corrected for up to {config.MAX_ITERATIONS} look-backs in this "
          f"run (exhaustive_search.py uses a different correction, sized to its own 64 comparisons "
          f"-- the two scripts' threshold numbers are not meant to match).\n")

    committed_ops: dict[str, str] = {}
    committed = calculate_f1_candidate(raw_df, folds, committed_ops)
    committed_f1, committed_scores = committed["mean"], committed["scores"]
    print(f"Evaluator: {config.EVALUATOR.upper()}")
    print(f"Baseline {config.METRIC_LABEL} ({'SYNTHETIC-injected' if use_injection else 'real data'}, as-is), fixed-fold: "
          f"{committed_f1:.4f} +/- {committed['std']:.4f}   [F1 {committed['f1_mean']:.4f}]\n")

    if use_injection:
        log_meta = {"scenario": scenario_name or "synthetic_injection",
                    "label": label or "SYNTHETIC INJECTION (declared corruption on Adult - not real data)",
                    "declared_spec": scenario_meta if external else DECLARED_SPEC}
    else:
        log_meta = {"scenario": "real_adult", "label": "REAL DATA (Adult Census, real '?' missingness)"}
    log_meta["evaluator"] = config.EVALUATOR
    log_meta["metric"] = config.GATE_METRIC   # NOTE: audit fields named f1_* hold the GATE score (neg-Brier) from 2026-09-30
    log_meta["planner"] = "offline_rule" if offline_planner else config.MODEL_NAME
    log = audit.new_run(meta=log_meta)

    chain: dict[str, str] = {}
    chain_delta = 0.0  # cumulative paired delta of the CURRENT chain vs the committed baseline
    tried_in_chain: set[tuple[str, str]] = set()
    permanently_rejected: list[tuple[str, str]] = []
    chain_id = 0

    # Persist for the WHOLE run (never reset on chain discard) -- this is
    # the v6 fix: prevents re-walking into an already-fully-evaluated
    # combination once a chain resets.
    evaluated_states: set[frozenset] = set()
    chain_eval_cache: dict[frozenset, dict] = {}

    for i in range(1, config.MAX_ITERATIONS + 1):
        print(f"--- Iteration {i} ---")
        findings = detect(materialize(raw_df, committed_ops))  # profiling-only view, never scored
        if not findings:
            if chain:
                print(f"No detectable defects left in the committed baseline, staged chain "
                      f"{list(chain.items())} never cleared threshold -- discarding.\n")
                audit.resolve_chain(log, chain_id, "discarded")
            else:
                print("No detectable defects left -- stopping.")
            break

        # v6: on top of tried_in_chain/permanently_rejected, exclude any
        # pair that would recreate a full (committed_ops + chain + pair)
        # combination already evaluated earlier THIS run.
        already_evaluated_pairs = [
            (c, op) for c, op, _ in remaining_options(findings)
            if (c, op) not in tried_in_chain
            and frozenset({**committed_ops, **chain, c: op}.items()) in evaluated_states
        ]
        exclude = list(tried_in_chain) + permanently_rejected + already_evaluated_pairs

        try:
            decision = (plan_offline if offline_planner else plan)(findings, rejected=exclude)
        except Exception as e:
            print(f"Planner failed or chain exhausted: {e}")
            audit.log_iteration(
                log, iteration=i, column=None, operation=None, reason=None,
                f1_before=committed_f1, f1_after=None, threshold=None,
                accepted=False, error=str(e), status="error", chain_id=chain_id,
                chain_ops=chain, committed_ops=committed_ops,
            )
            if chain:
                print(f"Discarding chain {list(chain.items())}.\n")
                audit.resolve_chain(log, chain_id, "discarded")
                chain = {}
                chain_delta = 0.0
                tried_in_chain = set()
                chain_id += 1
                continue
            break

        column, operation, reason = decision["column"], decision["operation"], decision["reason"]
        print(f"Planner: column={column!r} operation={operation!r} reason={reason!r}")
        tried_in_chain.add((column, operation))

        new_chain = dict(chain)
        new_chain[column] = operation
        state_key = frozenset({**committed_ops, **new_chain}.items())

        try:
            if state_key in chain_eval_cache:
                cached = chain_eval_cache[state_key]
                candidate, stats = cached["candidate"], cached["stats"]
                print(f"  (already evaluated this run -- reusing cached result instead of recomputing)")
            else:
                candidate = calculate_f1_candidate(raw_df, folds, committed_ops, candidate_ops=new_chain)
                stats = paired_delta_corrected(
                    committed_scores, candidate["scores"], candidate["n_train"], candidate["n_test"],
                )
                chain_eval_cache[state_key] = {"candidate": candidate, "stats": stats}
                evaluated_states.add(state_key)
        except Exception as e:
            print(f"Evaluation failed: {e}\n")
            audit.log_iteration(
                log, iteration=i, column=column, operation=operation, reason=reason,
                f1_before=committed_f1, f1_after=None, threshold=None,
                accepted=False, error=str(e), status="error", chain_id=chain_id,
                chain_ops=new_chain, committed_ops=committed_ops,
            )
            permanently_rejected.append((column, operation))
            continue

        delta = stats["mean_delta"]
        threshold = commit_threshold(stats["se_delta"], stats["dof"], config.MAX_ITERATIONS)
        chain_display = list(new_chain.items())

        stacks = delta > chain_delta + config.MIN_STAGE_GAIN_FRAC * max(threshold, 0.0)   # greedy: an op joins the chain only if it improves the chain
        audit.log_iteration(
            log, iteration=i, column=column, operation=operation, reason=reason,
            f1_before=committed_f1, f1_after=candidate["mean"], threshold=threshold,
            accepted=False, std_before=committed["std"], std_after=candidate["std"],
            se=stats["se_delta"], status="staged" if (stacks or clears_bar(delta, threshold)) else "discarded",
            chain_id=chain_id, chain_ops=new_chain if (stacks or clears_bar(delta, threshold)) else chain,
            committed_ops=committed_ops,
        )

        fmt = (f"Cumulative {config.METRIC_LABEL} (chain={chain_display}) before={committed_f1:.4f} "
               f"after={candidate['mean']:.4f} paired_delta={delta:+.4f} "
               f"(threshold={threshold:.4f}, corrected-SE + t-dist, Bonferroni over "
               f"{config.MAX_ITERATIONS} look-backs, n={len(folds)} folds)")
        if clears_bar(delta, threshold):
            print(f"{fmt} -> COMMITTED\n")
            audit.resolve_chain(log, chain_id, "committed")
            committed_ops.update(new_chain)  # no materialized dataframe -- just record what's confirmed
            committed = calculate_f1_candidate(raw_df, folds, committed_ops)
            committed_f1, committed_scores = committed["mean"], committed["scores"]
            chain = {}
            chain_delta = 0.0
            tried_in_chain = set()
            chain_id += 1
        elif stacks:
            print(f"{fmt} -> STAGED (improves the chain from {chain_delta:+.4f}), "
                  f"continuing to test for a compounding effect\n")
            chain = new_chain
            chain_delta = delta
        else:
            print(f"{fmt} -> DROPPED from chain (does not improve the chain's {chain_delta:+.4f}); "
                  f"chain stays {list(chain.items()) or '(empty)'}\n")
    else:
        if chain:
            print(f"Reached MAX_ITERATIONS with chain {list(chain.items())} still unproven -- discarding.\n")
            audit.resolve_chain(log, chain_id, "discarded")

    path = audit.save(
        log,
        baseline_f1=log["iterations"][0]["f1_before"] if log["iterations"] else committed_f1,
        final_f1=committed_f1,
    )
    print(f"Final {config.METRIC_LABEL}: {committed_f1:.4f}   [F1 {committed['f1_mean']:.4f}]")
    print(f"Committed operations: {committed_ops if committed_ops else '(none)'}")

    print(f"Distinct full (column -> operation) states evaluated this run (deduplicated): "
          f"{len(evaluated_states)}.")
    if manifest is not None:
        print("\nAnswer key check (SYNTHETIC run -- did the agent commit the fix that undoes each injected defect?)")
        for m in manifest:
            got = committed_ops.get(m["column"])
            if m.get("expected_commit", True):
                verdict = "YES" if got == m["expected_fix"] else (f"NO (committed: {got})" if got else "NO (not committed)")
                print(f"  {m['id']}: expected {m['expected_fix']} on '{m['column']}' -> {verdict}")
            else:
                verdict = "CORRECT (left alone)" if got is None else f"WRONG (committed {got})"
                print(f"  {m['id']}: negative control, harmless defect, agent should NOT fix -> {verdict}")
    print(f"Audit log written to: {path}")

    # Explain module (2026-09-30): turn the audit log into a demo-ready
    # report. Never allowed to break a run -- the audit JSON is already
    # saved by this point.
    if config.EXPLAIN_ENABLED and run_explain:
        try:
            from . import explain
            explain.explain_run(path)
        except Exception as ex:  # noqa: BLE001
            print(f"(Explain step skipped: {type(ex).__name__}: {ex})")

    return {"committed_ops": dict(committed_ops), "baseline": log["iterations"][0]["f1_before"] if log["iterations"] else committed_f1,
            "final": committed_f1, "final_f1": committed["f1_mean"], "log_path": str(path)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="AETERNA-QA pipeline")
    ap.add_argument("--inject", action="store_true",
                    help="run on Adult with the DECLARED synthetic corruption (labelled SYNTHETIC)")
    ap.add_argument("--scenario", choices=["D1"], default=None,
                    help="run a labelled SYNTHETIC DEMO scenario (D1) on the eval partition; use with --seed")
    ap.add_argument("--seed", type=int, default=201, help="injection seed for --scenario (default 201)")
    ap.add_argument("--evaluator", choices=config.EVALUATORS, default=config.EVALUATOR,
                    help="model used for every accept/commit decision (declared input)")
    ap.add_argument("--offline-planner", action="store_true",
                    help="use the rule-based planner instead of Groq (no API key needed)")
    a = ap.parse_args()
    config.EVALUATOR = a.evaluator
    if a.scenario:
        from . import demo
        demo.run_d1(seed=a.seed, offline_planner=a.offline_planner)
    else:
        run(use_injection=a.inject, offline_planner=a.offline_planner)
