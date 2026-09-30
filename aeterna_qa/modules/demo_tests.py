"""Tests for the D1 demo wiring (no Groq, no gate): spec, labelling, blindness."""
import pathlib
import re

from .demo import D1_SPEC, D1_SCENARIO
from .injection import inject
from .study import base_and_split


def main():
    assert D1_SCENARIO.startswith("synthetic") and "D1" in D1_SCENARIO
    assert len({s["column"] for s in D1_SPEC}) == 4
    _, ev = base_and_split()
    df, man = inject(ev, D1_SPEC, seed=201)
    assert len(df) == len(ev) and list(df.index) == list(ev.index)
    for m in man:
        assert len(m["rows"]) > 0, m["id"]
    assert (df["capital.gain"] == 9999999).sum() == round(0.02 * len(ev))
    assert (df["hours.per.week"] > 99).sum() > 0
    # answer key must not leak into pipeline decisions or the planner
    here = pathlib.Path(__file__).parent
    assert not re.search(r"\bdemo\b|D1_SPEC", (here / "planner.py").read_text(encoding="utf-8"))
    body = (here / "pipeline.py").read_text(encoding="utf-8")
    loop = body[body.index("for i in range(1, config.MAX_ITERATIONS + 1):"):body.index("path = audit.save(")]
    assert "manifest" not in loop and "D1" not in loop
    print("demo_tests: all passed")


if __name__ == "__main__":
    main()
