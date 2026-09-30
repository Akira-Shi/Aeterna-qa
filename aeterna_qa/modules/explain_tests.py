"""Tests for Explain's handling of older logs (2026-09-30, T1).
Run: python -m modules.explain_tests"""
import json
from pathlib import Path
from .explain import build_facts, headline, render_html, plain_fix


def _it(n, chain, status, delta, chain_ops=None, committed_ops=None, col="age", op="rescale_units"):
    d = {"iteration": n, "column": col, "operation": op, "reason": "r", "f1_before": 0.2, "f1_after": 0.2 + delta,
         "delta": delta, "std_before": 0.01, "std_after": 0.01, "se": 0.01, "threshold": 0.02,
         "accepted": status == "committed", "error": None, "status": status, "chain_id": chain}
    if chain_ops is not None or committed_ops is not None:
        d["chain_ops"], d["committed_ops"] = chain_ops, committed_ops
    return d


def _render(run, scenario=None, label=None, metric=None):
    if scenario:
        run = dict(run, meta={"scenario": scenario, "label": label, "metric": metric})
    facts = build_facts(run)
    return render_html(facts, {"mode": "template-only", "verified": 0, "rejected": []}, Path("x.json"))


def _main_view(h):
    """HTML before the single Technical details section."""
    i = h.index("<summary><b>Technical details</b>")
    return h[:i]


def _html_tests():
    ops = {"capital.gain": "sentinel_to_median", "hours.per.week": "rescale_units"}
    run = {"baseline_f1": -0.12, "final_f1": -0.11, "iterations": [
        _it(1, 0, "committed", 0.01, chain_ops={"capital.gain": "sentinel_to_median"}, committed_ops={},
            col="capital.gain", op="sentinel_to_median"),
        _it(2, 1, "committed", 0.05, chain_ops={"hours.per.week": "rescale_units"}, committed_ops={},
            col="hours.per.week", op="rescale_units"),
        _it(3, 2, "discarded", -0.01, col="age", op="clip_outliers"),
        _it(4, 3, "discarded", 0.005, col="education", op="fill_mode")]}
    h = _render(run, "synthetic_D1_demo", "SYNTHETIC DEMO test", "brier")
    m = _main_view(h)
    assert "SYNTHETIC DEMO test" in m and "banner synth" in m and "planted on purpose" in m
    assert m.count("<div class='card'>") == 2, m.count("<div class='card'>")
    assert "We checked 4 possible fixes" in m and "2 were kept" in m
    assert "Replaced placeholder values in capital.gain" in m
    assert "not big enough to be sure it was real" in m
    for jargon in ("neg-Brier", "sentinel_to_median", "rescale_units", "clip_outliers", "fill_mode",
                   "delta", "Bonferroni", "fold", "evaluator", "0.0500"):
        assert jargon not in m, jargon
    assert "sentinel_to_median" in h  # kept, but only in technical details
    assert h.count("<summary><b>Technical details</b>") == 1
    for banned in ("+0.0175", "0.688", "2.0x SE", "calculate_f1_cv"):
        assert banned not in h, banned
    import re
    assert not re.search(r"bprov(e|es|ed|en)b", h)
    # unknown op falls back safely
    assert "clean-up" in plain_fix("zzz", "brand_new_op") and "brand_new_op" not in plain_fix("zzz", "brand_new_op")
    # nothing committed
    none = _render({"baseline_f1": -0.1, "final_f1": -0.1, "iterations": [_it(1, 0, "discarded", -0.01)]})
    assert "None were kept" in _main_view(none) and "banner synth" not in none
    # old log (no chain_ops keys) still renders, in plain words
    old = _render({"baseline_f1": 0.2, "final_f1": 0.25, "iterations": [_it(1, 0, "committed", 0.05)]})
    om = _main_view(old)
    assert "not recorded in this older log" in om and om.count("<div class='card'>") == 1
    # real logs, if present
    d = Path(__file__).resolve().parent.parent / "logs"
    for name in ("run_20260930T113058Z.json", "run_20260929T042640Z.json"):
        if (d / name).exists():
            hh = _render(json.loads((d / name).read_text()))
            assert "What was fixed" in hh and "Technical details" in hh


def main():
    # old log: committed chain, no chain_ops/committed_ops keys at all
    old = {"baseline_f1": 0.2, "final_f1": 0.25, "iterations": [_it(1, 0, "committed", 0.05)]}
    f = build_facts(old)
    assert f["committed_ops_recorded"] is False and f["n_committed"] == 1
    h = headline(f)
    assert "not recorded in this older log" in h and "(none)" not in h, h
    # new log: ops recorded, headline names them
    new = {"baseline_f1": 0.2, "final_f1": 0.25, "iterations": [
        _it(1, 0, "committed", 0.05, chain_ops={"age": "rescale_units"}, committed_ops={})]}
    f = build_facts(new)
    assert f["committed_ops_recorded"] is True and f["committed_ops"] == {"age": "rescale_units"}
    assert "age=rescale_units" in headline(f)
    # nothing committed: still reports the unchanged data, no "not recorded" text
    none = {"baseline_f1": 0.2, "final_f1": 0.2, "iterations": [_it(1, 0, "discarded", -0.01)]}
    assert "not recorded" not in headline(build_facts(none))
    _html_tests()
    print("explain_tests: all passed")


if __name__ == "__main__":
    main()
