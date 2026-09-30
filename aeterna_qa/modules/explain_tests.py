"""Tests for Explain's handling of older logs (2026-09-30, T1).
Run: python -m modules.explain_tests"""
from .explain import build_facts, headline


def _it(n, chain, status, delta, chain_ops=None, committed_ops=None, col="age", op="rescale_units"):
    d = {"iteration": n, "column": col, "operation": op, "reason": "r", "f1_before": 0.2, "f1_after": 0.2 + delta,
         "delta": delta, "std_before": 0.01, "std_after": 0.01, "se": 0.01, "threshold": 0.02,
         "accepted": status == "committed", "error": None, "status": status, "chain_id": chain}
    if chain_ops is not None or committed_ops is not None:
        d["chain_ops"], d["committed_ops"] = chain_ops, committed_ops
    return d


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
    print("explain_tests: all passed")


if __name__ == "__main__":
    main()
