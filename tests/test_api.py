"""P7 API tests (FastAPI TestClient). Exploratory only; nothing here is a cited result.

  python tests/test_api.py        (or: pytest tests/test_api.py)
"""
import io
import json
import os
import sys
import tempfile
import time
import uuid
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

from api import jobs, main as api_main, recipe, store    # noqa: E402
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
    assert avail == {"cleaned.csv": True, "cleaning_recipe.json": True, "pipeline.joblib": False, "report.html": True,
                     "audit.json": True}, avail
    assert a["note"] == recipe.NOTE and aud["note"] == recipe.NOTE and aud["cleaning"]["note"] == recipe.NOTE
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
    # the written CSV is exactly what replaying the saved recipe (no refit) gives
    rec = json.loads(client.get(f"/jobs/{job_id}/artifacts/cleaning_recipe.json").content)
    assert rec["note"] == recipe.NOTE and all(o["fitted_on"] == "full_upload" for o in rec["ops"])
    import api.jobs as jobs
    fr = jobs._load_frames(job_id)
    again, _ = recipe.apply_recipe(fr["before"], rec["ops"], fit=False)
    pd.testing.assert_frame_equal(pd.read_csv(io.BytesIO(csv.content)), pd.read_csv(io.StringIO(again.to_csv(index=False))))
    print("  PASS: Stage 1 -> Stage 2 (edit logged as user_override) -> artifacts on an Adult sample "
          f"(committed: {aud['committed_ops'] or 'none'})")


def test_recipe_replay_reproduces_cleaning_exactly():
    rng = np.random.default_rng(3)
    n = 200
    x = rng.normal(size=n).round(3)
    x[:60] = np.nan
    df = pd.DataFrame({"x": x, "g": rng.choice(["a", "b", "A "], n), "y": rng.choice(["a", "b"], n)})
    df.loc[[150, 151], "x"] = np.nan
    ops = recipe.recipe_from_ops({"g": "normalize_categories", "x": "fill_mean"})
    cleaned, fitted = recipe.apply_recipe(df, ops, fit=True)
    filled = cleaned.loc[df["x"].isna(), "x"]
    assert (filled == df["x"].mean()).all()                       # fitted on the full upload
    assert fitted[1]["params"] == float(df["x"].mean()) and fitted[1]["fitted_on"] == "full_upload"
    saved = json.loads(json.dumps(fitted))                        # as written to cleaning_recipe.json
    other = pd.DataFrame({"x": [np.nan, 1.0], "g": ["a", "b"], "y": ["a", "b"]})
    assert recipe.apply_recipe(df, saved, fit=False)[0].equals(cleaned)       # exact reproduction, no refit
    assert recipe.apply_recipe(other, saved, fit=False)[0]["x"].iloc[0] == df["x"].mean()   # params, not other's mean
    # drop_rows removes all affected rows
    c2, _ = recipe.apply_recipe(df, [{"op": "drop_rows", "column": "x"}], fit=True)
    assert len(c2) == int(df["x"].notna().sum()) and c2["x"].notna().all()
    print("  PASS: apply_recipe(fit=False) with saved params reproduces the fitted cleaning exactly")


def _synthetic_sentinel_csv(n=3000, seed=11):
    """LABELLED SYNTHETIC fixture (generated, not real): churn-like table, 12% of `satisfaction` replaced by -999."""
    rng = np.random.default_rng(seed)
    sat = rng.uniform(1, 5, n).round(1)
    tenure = rng.normal(40, 12, n).round(1)
    spend = rng.gamma(2.0, 1.0, n).round(2)
    p = 1 / (1 + np.exp(-(1.2 * (3 - sat) + 0.02 * (30 - tenure))))
    df = pd.DataFrame({"cust_id": np.arange(n), "tenure": tenure, "spend": spend,
                       "region": rng.choice(["east", "west", "north"], n), "satisfaction": sat,
                       "churn": np.where(rng.random(n) < p, "yes", "no")})
    df.loc[rng.choice(n, int(0.12 * n), replace=False), "satisfaction"] = -999
    return df


def test_synthetic_sentinel_commit_flow():
    df = _synthetic_sentinel_csv()
    ds = upload(df.to_csv(index=False).encode(), "synthetic_sentinel.csv")
    r = client.post("/jobs/stage1", json={"dataset_id": ds["dataset_id"], "target": "churn", "positive_label": "yes",
                                          "id_columns": ["cust_id"], "planner": "rule"})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    s1 = client.get(f"/jobs/{job_id}/stage1").json()
    assert s1["committed_ops"] == {"satisfaction": "sentinel_to_median"}, s1["committed_ops"]
    a = client.get(f"/jobs/{job_id}/artifacts").json()
    assert a["note"] == recipe.NOTE and any(f["name"] == "cleaning_recipe.json" and f["available"] for f in a["files"])
    csv = pd.read_csv(io.BytesIO(client.get(f"/jobs/{job_id}/artifacts/cleaned.csv").content))
    rec = json.loads(client.get(f"/jobs/{job_id}/artifacts/cleaning_recipe.json").content)
    assert rec["ops"][0]["op"] == "sentinel_to_median" and rec["ops"][0]["fitted_on"] == "full_upload"
    sv, med = rec["ops"][0]["params"]
    assert sv == -999 and med == float(df.loc[df["satisfaction"] != -999, "satisfaction"].median())
    assert not (csv["satisfaction"] == -999).any() and (csv.loc[df["satisfaction"] == -999, "satisfaction"] == med).all()
    d2 = df.drop(columns=["cust_id"])
    again, _ = recipe.apply_recipe(d2, rec["ops"], fit=False)
    pd.testing.assert_frame_equal(csv, pd.read_csv(io.StringIO(again.to_csv(index=False))))
    aud = json.loads(client.get(f"/jobs/{job_id}/artifacts/audit.json").content)
    assert aud["scenario"] == "exploratory" and aud["note"] == recipe.NOTE
    print("  PASS: synthetic sentinel CSV: stage1 commits sentinel_to_median, cleaned CSV == recipe replay")


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


def test_queue_position_and_cancel():
    ds = upload()
    spec = {"target": "income", "task_type": "binary", "positive_label": ">50K", "model_family": "linear",
            "id_columns": ["fnlwgt"], "drop_columns": []}
    ids = [uuid.uuid4().hex for _ in range(3)]
    for i, jid in enumerate(ids):                       # TestClient runs background tasks inline, so queue directly
        store.add_job(jid, ds["dataset_id"], "rule", spec, config.MAX_ITERATIONS, [])
        time.sleep(0.01)
    store.update_job(ids[0], status="running")
    pos = [client.get(f"/jobs/{j}").json()["queue_position"] for j in ids]
    assert pos == [0, 1, 2], pos                         # running job counts as one job ahead
    assert client.delete(f"/jobs/{ids[0]}").status_code == 409          # running: refused
    assert store.get_job(ids[0])["status"] == "running"
    assert client.delete("/jobs/" + "f" * 32).status_code == 404
    r = client.delete(f"/jobs/{ids[1]}")
    assert r.status_code == 200 and r.json()["cancelled"] is True
    assert client.get(f"/jobs/{ids[1]}").status_code == 404 and store.get_job(ids[1]) is None
    assert client.get(f"/jobs/{ids[2]}").json()["queue_position"] == 1  # moved up
    assert not (store.data_dir() / "jobs" / ids[1]).exists()
    assert jobs.run_stage1(ids[1]) is None                              # a late worker for a cancelled job is a no-op
    store.update_job(ids[0], status="done")
    assert client.delete(f"/jobs/{ids[0]}").status_code == 409          # finished: refused
    print("  PASS: queue_position (1 job ahead), cancel queued only (409 running/finished, 404 unknown)")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("api tests: all passed")
