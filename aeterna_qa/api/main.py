"""FastAPI app (P7). Local only: bind 127.0.0.1 (see __main__.py). Every run is EXPLORATORY, never a cited result."""
from __future__ import annotations

import io
import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # aeterna_qa/
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import pandas as pd                                                        # noqa: E402
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile    # noqa: E402
from fastapi.middleware.cors import CORSMiddleware                         # noqa: E402
from fastapi.responses import FileResponse                                 # noqa: E402

from modules import config, taskspec                                       # noqa: E402
from modules.taskspec import SpecError, TaskSpec                           # noqa: E402

from . import jobs, store                                                  # noqa: E402
from .schemas import ApproveRequest, RerunRequest, Stage1Request          # noqa: E402

MAX_UPLOAD_MB = 25                                  # below taskspec.MAX_FILE_MB (50), whose runs get slow
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MEDIA = {"cleaned.csv": "text/csv", "pipeline.joblib": "application/octet-stream", "report.html": "text/html",
         "audit.json": "application/json", "cleaning_recipe.json": "application/json", "preview.json": "application/json"}

app = FastAPI(title="AETERNA-QA API", version="0.1",
              description="Exploratory runs only: nothing produced here is a cited result.")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    store.mark_interrupted()


def _profile(df: pd.DataFrame) -> dict:
    return {"rows": int(len(df)), "n_columns": int(df.shape[1]),
            "columns": [{"name": str(c), "dtype": str(df[c].dtype), "missing": int(df[c].isna().sum()),
                         "distinct": int(df[c].nunique(dropna=True))} for c in df.columns]}


def _job_or_404(job_id: str) -> dict:
    j = store.get_job(job_id)
    if j is None:
        raise HTTPException(404, "unknown job")
    return j


def _done_or_409(job_id: str) -> dict:
    j = _job_or_404(job_id)
    if j["status"] != "done":
        raise HTTPException(409, f"job is {j['status']!r}, not 'done'")
    return j


@app.post("/datasets", status_code=201)
async def upload_dataset(file: UploadFile):
    name = file.filename or ""
    if not name.lower().endswith(".csv"):
        raise HTTPException(415, "CSV files only (.csv)")
    buf, size = io.BytesIO(), 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"file is larger than the {MAX_UPLOAD_MB} MB limit")
        buf.write(chunk)
    if size == 0:
        raise HTTPException(422, "empty file")
    ds_id = uuid.uuid4().hex
    path = store.data_dir() / "datasets" / f"{ds_id}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.getvalue())
    try:
        df = taskspec._normalise(taskspec._read_csv(path))
        if df.shape[1] < 2 or len(df) == 0:
            raise ValueError("need at least 2 columns and 1 row")
    except Exception as e:                                                    # noqa: BLE001
        path.unlink(missing_ok=True)
        raise HTTPException(422, f"not a readable CSV: {type(e).__name__}: {str(e)[:200]}")
    prof = _profile(df)
    store.add_dataset(ds_id, Path(name).name, path, prof)
    return {"dataset_id": ds_id, "filename": Path(name).name, **prof}


def _start(spec_body: dict, dataset: dict, planner: str, bg: BackgroundTasks) -> dict:
    try:
        spec = TaskSpec(path=dataset["path"], target=spec_body["target"], task_type=spec_body["task_type"],
                        positive_label=None if spec_body["positive_label"] is None else str(spec_body["positive_label"]),
                        model_family=spec_body["model_family"], id_columns=spec_body["id_columns"],
                        drop_columns=spec_body["drop_columns"])
        v = taskspec.validate(spec)
    except SpecError as e:
        raise HTTPException(422, {"errors": [str(e)]})
    if not v.ok:
        raise HTTPException(422, {"errors": v.errors, "warnings": v.warnings})
    job_id = uuid.uuid4().hex
    store.add_job(job_id, dataset["id"], planner, spec.to_dict(), config.MAX_ITERATIONS, v.warnings)
    bg.add_task(jobs.run_stage1, job_id)
    return {"job_id": job_id, "status": "queued", "planner": planner, "warnings": v.warnings,
            "scenario": "exploratory"}


@app.post("/jobs/stage1", status_code=202)
def start_stage1(body: Stage1Request, bg: BackgroundTasks):
    ds = store.get_dataset(body.dataset_id)
    if ds is None:
        raise HTTPException(404, "unknown dataset_id")
    return _start(body.model_dump(exclude={"dataset_id", "planner"}), ds, body.planner, bg)


@app.post("/jobs/{job_id}/rerun", status_code=202)
def rerun_with_rule_planner(job_id: str, body: RerunRequest, bg: BackgroundTasks):
    j = _job_or_404(job_id)
    if j["status"] != "planner_unavailable":
        raise HTTPException(409, "rerun is offered only for a job whose planner was unavailable")
    ds = store.get_dataset(j["dataset_id"])
    spec = dict(j["spec"])
    spec = {k: spec[k] for k in ("target", "task_type", "positive_label", "model_family", "id_columns", "drop_columns")}
    return _start(spec, ds, "rule", bg)


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    j = _job_or_404(job_id)
    return {"job_id": j["id"], "status": j["status"], "progress": {"iteration": j["iteration"], "of": j["total"]},
            "planner": j["planner"], "message": j["message"], "warnings": j["warnings"], "scenario": "exploratory",
            "can_rerun_with_rule": j["status"] == "planner_unavailable",
            "stage2": {"suggested": bool(j["stage2"]), "approved": bool(j["stage2"] and j["stage2"].get("approved"))}}


@app.get("/jobs/{job_id}/stage1")
def stage1(job_id: str):
    _done_or_409(job_id)
    return jobs.stage1_results(job_id)


@app.post("/jobs/{job_id}/stage2/suggest")
def stage2_suggest(job_id: str):
    _done_or_409(job_id)
    return jobs.suggest(job_id)


@app.post("/jobs/{job_id}/stage2/approve")
def stage2_approve(job_id: str, body: ApproveRequest):
    _done_or_409(job_id)
    try:
        return jobs.approve(job_id, body.decisions)
    except jobs.Stage2Error as e:
        raise HTTPException(422, str(e))


@app.get("/jobs/{job_id}/artifacts")
def artifacts(job_id: str):
    _done_or_409(job_id)
    jd = store.job_dir(job_id)
    files = [{"name": n, "available": (jd / n).is_file(), "url": f"/jobs/{job_id}/artifacts/{n}",
              "media_type": MEDIA[n]} for n in jobs.ARTIFACTS if n != "preview.json"]
    return {"files": files, "preview": json.loads((jd / "preview.json").read_text(encoding="utf-8")),
            "note": jobs.recipe_mod.NOTE, "pipeline_note": "pipeline.joblib exists only after /stage2/approve"}


@app.get("/jobs/{job_id}/artifacts/{name}")
def artifact_file(job_id: str, name: str):
    _done_or_409(job_id)
    if name not in MEDIA:
        raise HTTPException(404, "unknown artifact")
    p = store.job_dir(job_id) / name
    if not p.is_file():
        raise HTTPException(404, f"{name} not available yet")
    return FileResponse(p, media_type=MEDIA[name], filename=name)
