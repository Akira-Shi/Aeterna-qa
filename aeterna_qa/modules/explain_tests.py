"""Tests for Explain's handling of older logs (2026-09-30, T1).
Run: python -m modules.explain_tests"""
import json
from pathlib import Path
from .explain import build_facts, headline, render_html, plain_fix, guard_note, _SYSTEM, add_notes


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
    assert "synthetic" not in h.lower() and "banner" not in h and "planted on purpose" not in h
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


def _guard_tests():
    """Semantic guard (2026-11-01): sign, verdict consistency, prompt wording.
    Texts are the false passes recorded in LOOP/reports/build-T2.md."""
    def mk(n, status, delta, thr, ops):
        it = _it(n, 0, status, delta, chain_ops=ops, committed_ops={})
        it["threshold"], it["se"] = thr, 0.0002
        f = build_facts({"baseline_f1": 0.2, "final_f1": 0.2, "iterations": [it]})
        return f["iterations"][0], f
    # 1) sign blindness (run 060306Z iter 6/8/9): negative delta "equals" a positive bar
    for n, d, b in ((6, -0.0006, 0.0006), (8, -0.0007, 0.0007), (9, -0.0001, 0.0001)):
        it, f = mk(n, "discarded", d, b, {"age": "rescale_units"})
        bad = guard_note(f"Delta {d:.4f} equals bar {b:.4f}, no improvement.", it, f)
        assert bad, ("sign blindness not rejected", n)
        ok = guard_note(f"Delta {d:.4f} is below the bar {b:.4f}, no improvement.", it, f)
        assert not ok, ok
    it, f = mk(7, "discarded", -0.0010, 0.0006, {"age": "rescale_units"})
    assert guard_note("Delta +0.0010 is below the bar 0.0006.", it, f), "wrong explicit sign passed"
    assert not guard_note("Delta -0.0010 is below the bar 0.0006.", it, f)
    # 1b) negation exemption (112347Z iter 2, 7, 10): "does not exceed" is correct, must pass
    for n, d, b, se in ((2, -0.0011, 0.0007, "5.5"), (7, -0.0011, 0.0007, "5.5"), (10, -0.0011, 0.0007, "5.5")):
        it, f = mk(n, "discarded", d, b, {"age": "rescale_units"})
        it["se"] = 0.0002
        ok = guard_note(f"Delta {d:.4f} does not exceed the {b:.4f} bar, so operation rolled back.", it, f)
        assert not any("reaches" in p for p in ok), ok
    it, f = mk(6, "discarded", -0.0006, 0.0006, {"age": "rescale_units"})
    assert guard_note("Delta -0.0006 equals bar 0.0006", it, f)
    # negation outside the 3-token window plus a false reach claim is still rejected
    assert any("reaches" in p for p in guard_note(
        "Not helpful overall, and one two three delta -0.0006 equals bar 0.0006.", it, f))
    # 2) context omission (run 141619Z iter 1): staged then committed with its chain
    it, f = mk(1, "committed", 0.0005, 0.0006, {"age": "rescale_units"})
    assert it["verdict"]["code"] == "commit_with_chain"
    bad = guard_note("Normalization of occupation categories produced a 0.0005 increase, below the 0.0006 "
                     "threshold, so no measurable improvement.", it, f)
    assert any("COMMIT" in p for p in bad), bad
    assert not guard_note("Alone this gave a 0.0005 increase, below the 0.0006 bar; the chain cleared it later.", it, f)
    # rolled-back note must not claim improvement
    it, f = mk(2, "discarded", 0.0003, 0.0006, {"age": "rescale_units"})
    assert guard_note("The fix improved Brier by 0.0003.", it, f)
    assert guard_note("It reduced Brier by 0.0003.", it, f)
    assert not guard_note("It did not improve anything: 0.0003 is below the 0.0006 bar.", it, f)
    # 3) unjustified "Contradicts:" (run 093717Z iter 1): numbers/sign/verdict are all consistent
    #    now rejected by the "Contradicts" guard (option c, Akira 2026-11-01)
    it, f = mk(1, "discarded", 0.0011, 0.0011, {"age": "sentinel_to_median"})
    it["se"] = 0.0003
    bad = guard_note("Contradicts: delta +0.0011 equals bar, 3.7 SE, not distinguishable from noise.", it, f)
    assert any("Contradicts" in p for p in bad), bad
    assert not guard_note("Delta +0.0011 equals the bar, not distinguishable from noise.", it, f)
    assert "contradicts" not in _SYSTEM.lower().replace("never use the word 'contradicts'", "")
    assert "sign" in _SYSTEM and "do not say the operation had no effect" in _SYSTEM
    # add_notes: a rejected note falls back (no note attached) and is listed
    it, f = mk(1, "committed", 0.0005, 0.0006, {"age": "rescale_units"})
    st = add_notes(f, lambda p: {"summary": "", "iterations": [{"iteration": 1, "note": "no measurable improvement, 0.0005"}]})
    assert st["verified"] == 0 and len(st["rejected"]) == 1 and not f["iterations"][0].get("note")


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
    _guard_tests()
    print("explain_tests: all passed")


if __name__ == "__main__":
    main()
