"""P7 API tests (FastAPI TestClient). Exploratory only; nothing here is a cited result.

  python tests/test_api.py        (or: pytest tests/test_api.py)
"""
import io
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "aeterna_qa"))

_TMP = tempfile.TemporaryDirectory()
os.environ["AETERNA_API_DATA"] = str(Path(_TMP.name) / "api_data")

from fastapi.testclient import TestClient            # noqa: E402

from api import cleaning, main as api_main, store    # noqa: E402
from modules import config, planner                  # noqa: E402

client = TestClient(api_main.app)
_CACHE = {}


def adult_sample(n=500):
    df = pd.read_csv(ROOT / "Dataset" / "adult.csv").sample(n, random_state=1).reset_index(drop=True)
    return df.to_csv(index=False).encode()


def upload(data=None, name="adult_small.csv"):
    r = client.post("/datasets", files={"file": (name, data or adult_sample(), "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()


def spec_body(ds, **kw):
    b = {"dataset_id": ds["dataset_id"], "target": "income", "positive_label": ">50K", "planner": "rule",
         "id_columns": ["fnlwgt"]}
    b.update(kw)
    return b


def test_upload_profile():
    ds = upload()
    assert ds["rows"] == 500 and ds["n_columns"] == 15
    cols = {c["name"]: c for c in ds["columns"]}
    assert set(cols["workclass"]) == {"name", "dtype", "missing", "distinct"}
    assert cols["workclass"]["missing"] > 0          # '?' normalised to missing
    assert cols["income"]["distinct"] == 2
    print("  PASS: upload returns columns, dtypes, missing and distinct counts")


def test_oversize_and_non_csv():
    old = api_main.MAX_UPLOAD_BYTES
    api_main.MAX_UPLOAD_BYTES = 2048
    try:
        r = client.post("/datasets", files={"file": ("big.csv", adult_sample(), "text/csv")})
        assert r.status_code == 413, r.status_code
    finally:
        api_main.MAX_UPLOAD_BYTES = old
    assert client.post("/datasets", files={"file": ("x.txt", b"a,b\n1,2\n", "text/plain")}).status_code == 415
    assert client.post("/datasets", files={"file": ("e.csv", b"", "text/csv")}).status_code == 422
    assert api_main.MAX_UPLOAD_MB == 25
    print("  PASS: oversize -> 413, non-CSV -> 415, empty -> 422")


def test_invalid_taskspec():
    ds = upload()
    bads = [spec_body(ds, target="nope"),                        # target not in CSV
            spec_body(ds, positive_label="maybe"),               # not a class
            spec_body(ds, task_type="ranking"),                  # bad enum
            spec_body(ds, model_family="svm"),
            spec_body(ds, planner="gpt"),
            spec_body(ds, id_columns=["income"]),                # target as id column
            {**spec_body(ds), "gate_metric": "f1"}]              # unknown field (also: f1 is not exposed)
    for b in bads:
        r = client.post("/jobs/stage1", json=b)
        assert r.status_code == 422, (b, r.status_code, r.text)
    assert client.post("/jobs/stage1", json=spec_body({"dataset_id": "0" * 32})).status_code == 404
    print("  PASS: invalid TaskSpec -> 422, unknown dataset -> 404")


def _run_flow():
    if "flow" in _CACHE:
        return _CACHE["flow"]
    ds = upload()
    r = client.post("/jobs/stage1", json=spec_body(ds))
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    st = client.get(f"/jobs/{job_id}").json()          # TestClient runs the background task before returning
    assert st["status"] == "done", st
    assert st["progress"]["of"] == config.MAX_ITERATIONS == 16 and st["progress"]["iteration"] >= 1
    _CACHE["flow"] = (ds, job_id)
    return _CACHE["flow"]


def test_full_flow():
    ds, job_id = _run_flow()
    s1 = client.get(f"/jobs/{job_id}/stage1").json()
    assert s1["scenario"] == "exploratory" and s1["metric"] == "neg-Brier" and s1["repairs"]
    r0 = s1["repairs"][0]
    for k in ("iteration", "column", "operation", "reason", "delta", "se", "threshold", "status", "verdict", "plain_fix"):
        assert k in r0, k
    aud = json.loads(client.get(f"/jobs/{job_id}/artifacts/audit.json").content)
    assert aud["scenario"] == "exploratory" and aud["stage1_log"]["meta"]["scenario"] == "exploratory"

    # artifacts before Stage 2: no pipeline yet
    a = client.get(f"/jobs/{job_id}/artifacts").json()
    avail = {f["name"]: f["available"] for f in a["files"]}
    assert avail == {"cleaned.csv": True, "pipeline.joblib": False, "report.html": True, "audit.json": True}, avail
    assert len(a["preview"]["before"]) == len(a["preview"]["after"]) <= 20

    # Stage 2
    assert client.post(f"/jobs/{job_id}/stage2/approve", json={"decisions": []}).status_code == 422   # before suggest
    sg = client.post(f"/jobs/{job_id}/stage2/suggest")
    assert sg.status_code == 200, sg.text
    sg = sg.json()
    assert sg["steps"] and sg["compare"]["metric"].startswith("neg_brier")
    assert "gate_metric" not in json.dumps(sg)
    steps = {s["index"]: s for s in sg["steps"]}
    edit_i = next(i for i, s in steps.items() if s["editable"] and s["stage"] == "scaling")
    new = next(m for m in steps[edit_i]["allowed_methods"] if m != steps[edit_i]["method"])
    bad = client.post(f"/jobs/{job_id}/stage2/approve", json={"decisions": [{"step": edit_i, "action": "edit", "method": "bogus"}]})
    assert bad.status_code == 422
    ok = client.post(f"/jobs/{job_id}/stage2/approve",
                     json={"decisions": [{"step": edit_i, "action": "edit", "method": new}]})
    assert ok.status_code == 200, ok.text
    aud = json.loads(client.get(f"/jobs/{job_id}/artifacts/audit.json").content)
    log = aud["stage2"]["steps"]
    assert len(log) == len(steps)
    for e in log:
        assert {"decided_by", "rule_id", "user_edit"} <= set(e)
        if e["index"] == edit_i:
            assert e["decided_by"] == "user_override" and e["user_edit"] == {"from": steps[edit_i]["method"], "to": new}
            assert e["rule_id"] == steps[edit_i]["rule_id"]
        else:
            assert e["decided_by"] == "rule" and e["user_edit"] is None

    # artifacts after approve
    a = client.get(f"/jobs/{job_id}/artifacts").json()
    assert all(f["available"] for f in a["files"]), a["files"]
    csv = client.get(f"/jobs/{job_id}/artifacts/cleaned.csv")
    assert csv.status_code == 200 and b"\r\n" not in csv.content
    import joblib
    pipe = joblib.load(io.BytesIO(client.get(f"/jobs/{job_id}/artifacts/pipeline.joblib").content))
    assert hasattr(pipe, "predict_proba")
    assert "<html" in client.get(f"/jobs/{job_id}/artifacts/report.html").text.lower()
    assert client.get(f"/jobs/{job_id}/artifacts/../../x").status_code in (404, 405)
    assert client.get(f"/jobs/{job_id}/artifacts/secret.txt").status_code == 404
    # the written CSV is exactly what the train-fitted writer gives for the committed ops
    import api.jobs as jobs
    fr = jobs._load_frames(job_id)
    again, _ = cleaning.clean_with_train_fit(fr["before"], aud["committed_ops"], fr["train_index"])
    pd.testing.assert_frame_equal(pd.read_csv(io.BytesIO(csv.content)), pd.read_csv(io.StringIO(again.to_csv(index=False))))
    print("  PASS: Stage 1 -> Stage 2 (edit logged as user_override) -> artifacts on an Adult sample "
          f"(committed: {aud['committed_ops'] or 'none'})")


def test_cleaned_csv_uses_training_fitted_values():
    rng = np.random.default_rng(3)
    n = 200
    x = rng.normal(size=n).round(3)
    x[:60] = np.nan                                   # missing rows
    df = pd.DataFrame({"x": x, "y": rng.choice(["a", "b"], n)})
    train = list(range(100, 200))                      # training rows: no missing at all in x[:60]? (rows 100..199)
    train_vals = df.loc[train, "x"]
    mean_train, mean_full = train_vals.mean(), df["x"].mean()
    assert abs(mean_train - mean_full) > 1e-6
    cleaned, fitted = cleaning.clean_with_train_fit(df, {"x": "fill_mean"}, train)
    filled = cleaned.loc[df["x"].isna(), "x"]
    assert len(filled) == 60 and (filled == mean_train).all()          # equals the training-fitted value ...
    assert not np.isclose(filled.iloc[0], mean_full)                   # ... not the full-file value
    assert fitted[0]["params"] == float(mean_train) and fitted[0]["fitted_on"] == "training rows only"
    csv = pd.read_csv(io.StringIO(cleaned.to_csv(index=False)))
    assert np.isclose(csv.loc[df["x"].isna().to_numpy(), "x"].iloc[0], mean_train)
    # the writer touches only the committed op: other columns and observed cells are unchanged
    pd.testing.assert_series_equal(cleaned["y"], df["y"])
    obs = df["x"].notna()
    assert (cleaned.loc[obs, "x"] == df.loc[obs, "x"]).all()
    # drop_rows removes TRAINING rows only
    d2 = df.copy()
    d2.loc[[5, 150], "x"] = np.nan
    c2, _ = cleaning.clean_with_train_fit(d2.assign(x=d2["x"]), {"x": "drop_rows"}, train)
    assert 5 in c2.index and 150 not in c2.index
    print("  PASS: cleaned CSV fill value == value fitted on training rows (not the full-file value)")


def test_groq_failure_path():
    ds = upload()
    orig = planner.plan

    def boom(findings, rejected=None):
        raise RuntimeError("503 service unavailable (mock)")
    planner.plan = boom
    try:
        r = client.post("/jobs/stage1", json=spec_body(ds, planner="groq"))
        assert r.status_code == 202, r.text
        job_id = r.json()["job_id"]
    finally:
        planner.plan = orig
    st = client.get(f"/jobs/{job_id}").json()
    assert st["status"] == "planner_unavailable" and st["can_rerun_with_rule"] is True, st
    assert "rule planner" in st["message"]
    assert client.get(f"/jobs/{job_id}/stage1").status_code == 409
    assert client.post(f"/jobs/{job_id}/stage2/suggest").status_code == 409
    rr = client.post(f"/jobs/{job_id}/rerun", json={"planner": "rule"})
    assert rr.status_code == 202, rr.text
    new_id = rr.json()["job_id"]
    assert new_id != job_id and client.get(f"/jobs/{new_id}").json()["status"] == "done"
    assert client.post(f"/jobs/{new_id}/rerun", json={}).status_code == 409   # only for planner_unavailable jobs
    print("  PASS: Groq API error -> planner_unavailable, rule-planner rerun completes")


def test_store_and_labels():
    ds, job_id = _run_flow()
    j = store.get_job(job_id)
    assert j["planner"] == "rule" and j["spec"]["target"] == "income"
    assert client.get("/jobs/" + "f" * 32).status_code == 404
    print("  PASS: SQLite job store round-trip")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("api tests: all passed")
