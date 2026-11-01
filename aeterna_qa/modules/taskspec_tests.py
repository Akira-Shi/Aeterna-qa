"""TaskSpec + sandbox runner tests (P4). Run from aeterna_qa/:  python -m modules.taskspec_tests"""
import contextlib
import io
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, taskspec
from .taskspec import TaskSpec, SpecError


def _csv(tmp, df, name="t.csv"):
    p = Path(tmp) / name
    df.to_csv(p, index=False)
    return str(p)


def _toy(n=300, seed=0):
    r = np.random.RandomState(seed)
    x = r.normal(size=n)
    return pd.DataFrame({"row_id": np.arange(n), "x": x.round(3), "grp": r.choice(["a", "b", "c"], n),
                         "y": np.where(x + r.normal(size=n) > 0, "pos", "neg")})


def main():
    with tempfile.TemporaryDirectory() as tmp:
        df = _toy()
        p = _csv(tmp, df)
        # enums
        for bad in (dict(task_type="ranking"), dict(model_family="svm")):
            try:
                TaskSpec(path=p, target="y", **bad)
                raise AssertionError("bad enum accepted")
            except SpecError:
                pass
        s = TaskSpec(path=p, target="y", id_columns=["row_id"])
        assert TaskSpec.from_dict(s.to_dict()) == s
        # validation: ok + id-like warning when not excluded
        v = taskspec.validate(TaskSpec(path=p, target="y"))
        assert v.ok and any("row_id" in w and "ID" in w for w in v.warnings), v
        assert not any("row_id" in w for w in taskspec.validate(s).warnings)
        # missing target column / missing file
        assert not taskspec.validate(TaskSpec(path=p, target="nope")).ok
        assert not taskspec.validate(TaskSpec(path=p + ".x", target="y")).ok
        # binary needs exactly 2 classes
        assert not taskspec.validate(TaskSpec(path=p, target="grp")).ok
        assert taskspec.validate(TaskSpec(path=p, target="grp", task_type="multiclass")).ok
        assert not taskspec.validate(TaskSpec(path=p, target="y", positive_label="zzz")).ok
        # >40% missing warning; high-cardinality text is an error
        d2 = df.copy()
        d2.loc[:200, "grp"] = np.nan
        v = taskspec.validate(TaskSpec(path=_csv(tmp, d2, "m.csv"), target="y", id_columns=["row_id"]))
        assert any("grp" in w and "missing" in w for w in v.warnings)
        d3 = df.copy()
        d3 = pd.concat([d3] * 2, ignore_index=True); d3["txt"] = [f"u{i}" for i in range(len(d3))]
        assert not taskspec.validate(TaskSpec(path=_csv(tmp, d3, "h.csv"), target="y", id_columns=["row_id"])).ok
        # load: id dropped, target text, '?' and blanks become real NA (never the string 'nan')
        d4 = df.copy()
        d4.loc[:4, "grp"] = "?"
        d4.loc[5:9, "grp"] = " "
        out, prep = taskspec.load_dataset(TaskSpec(path=_csv(tmp, d4, "q.csv"), target="y", id_columns=["row_id"]))
        assert "row_id" not in out.columns and out["grp"].isna().sum() == 10, out["grp"].isna().sum()
        assert "nan" not in set(out["grp"].dropna())
        # numeric NaN: coded column -> categorical; wide continuous -> clear error instead of an evaluator crash
        d5 = df.copy()
        d5["code"] = np.random.RandomState(1).choice([1.0, 2.0, 3.0], len(d5))
        d5.loc[:20, "code"] = np.nan
        out, prep = taskspec.load_dataset(TaskSpec(path=_csv(tmp, d5, "c.csv"), target="y", id_columns=["row_id"]))
        assert prep["coerced_to_categorical"] == ["code"] and set(out["code"].dropna()) == {"1", "2", "3"}
        d6 = df.copy()
        d6.loc[:20, "x"] = np.nan
        try:
            taskspec.load_dataset(TaskSpec(path=_csv(tmp, d6, "n.csv"), target="y", id_columns=["row_id"]))
            raise AssertionError("numeric NaN column accepted")
        except SpecError as e:
            assert "numeric" in str(e)
        # missing-target rows dropped
        d7 = df.copy()
        d7.loc[:3, "y"] = np.nan
        out, prep = taskspec.load_dataset(TaskSpec(path=_csv(tmp, d7, "y.csv"), target="y", id_columns=["row_id"]))
        assert prep["rows_dropped_missing_target"] == 4 and len(out) == len(df) - 4
        # positive label: explicit wins, else minority
        assert taskspec.resolve_positive_label(TaskSpec(path=p, target="y", positive_label="neg"), df) == "neg"
        d8 = df.copy(); d8["y"] = np.where(np.arange(len(d8)) < 30, "rare", "common")
        assert taskspec.resolve_positive_label(TaskSpec(path=p, target="y"), d8) == "rare"
        # applied(): sets and RESTORES config
        before = (config.TARGET_COLUMN, config.POSITIVE_CLASS, config.DATA_PATH, list(config.KNOWN_MISSING_COLUMNS))
        with taskspec.applied(s, positive_label="pos"):
            assert config.TARGET_COLUMN == "y" and config.POSITIVE_CLASS == "pos"
        assert before == (config.TARGET_COLUMN, config.POSITIVE_CLASS, config.DATA_PATH, list(config.KNOWN_MISSING_COLUMNS))
        try:
            with taskspec.applied(s):
                raise RuntimeError
        except RuntimeError:
            pass
        assert config.TARGET_COLUMN == before[0]
        # Adult spec reproduces the v1 loader exactly
        if config.DATA_PATH.exists():
            from .evaluator import load_raw_dataset
            a_df, _ = taskspec.load_dataset(taskspec.adult_spec())
            ref = load_raw_dataset()
            assert list(a_df.columns) == list(ref.columns) and len(a_df) == len(ref)
            assert (a_df.astype(object).fillna('<NA>').astype(str).values == ref.astype(object).fillna('<NA>').astype(str).values).all(), "Adult via TaskSpec differs from load_raw_dataset"
        # runner: gated run writes exploratory_ files and an 'exploratory' audit; regression = detection only
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import run as runner
        old_log, old_root = config.LOG_DIR, config.AETERNA_ROOT
        try:
            config.LOG_DIR = Path(tmp) / "logs"
            config.AETERNA_ROOT = Path(tmp) / "root"
            config.EXPLAIN_ENABLED, was = False, config.EXPLAIN_ENABLED
            r = np.random.RandomState(3)
            big = pd.DataFrame({"a": r.normal(size=400), "b": r.choice(["u", "v"], 400)})
            big["t"] = np.where(big["a"] + r.normal(size=400) * 0.5 > 0, "1", "0")
            bp = _csv(tmp, big, "g.csv")
            with contextlib.redirect_stdout(io.StringIO()):
                res = runner.run_spec(TaskSpec(path=bp, target="t"), explain=False)
                reg = runner.run_spec(TaskSpec(path=bp, target="a", task_type="regression"))
            assert res["mode"] == "gated"
            lg = Path(res["log_path"])
            assert lg.name.startswith("exploratory_run_") and json.loads(lg.read_text())["meta"]["scenario"] == "exploratory"
            assert Path(res["clean_path"]).name.startswith("exploratory_")
            assert reg["mode"] == "detection_only" and reg["gate"] == "gate not supported"
            assert Path(reg["detect_path"]).name.startswith("exploratory_")
            assert config.TARGET_COLUMN == before[0], "runner leaked config state"
        finally:
            config.LOG_DIR, config.AETERNA_ROOT = old_log, old_root
            config.EXPLAIN_ENABLED = was
    print("taskspec_tests: all passed")


if __name__ == "__main__":
    main()
