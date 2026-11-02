"""SQLite dataset/job store (stdlib sqlite3; no Redis/Celery). Data lives under AETERNA_API_DATA
(default aeterna_qa/api_data/, git-ignored)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()


def data_dir() -> Path:
    d = Path(os.environ.get("AETERNA_API_DATA") or Path(__file__).resolve().parents[1] / "api_data")
    d.mkdir(parents=True, exist_ok=True)
    return d


def job_dir(job_id: str) -> Path:
    d = data_dir() / "jobs" / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _conn():
    c = sqlite3.connect(str(data_dir() / "store.sqlite"), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS datasets (id TEXT PRIMARY KEY, filename TEXT, path TEXT, profile TEXT, created REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, dataset_id TEXT, status TEXT, iteration INTEGER, "
              "total INTEGER, planner TEXT, spec TEXT, message TEXT, warnings TEXT, stage2 TEXT, "
              "created REAL, updated REAL)")
    return c


def _run(sql, args=()):
    with _LOCK:
        c = _conn()
        try:
            cur = c.execute(sql, args)
            c.commit()
            return [dict(r) for r in cur.fetchall()]
        finally:
            c.close()


def add_dataset(ds_id, filename, path, profile):
    _run("INSERT INTO datasets VALUES (?,?,?,?,?)", (ds_id, filename, str(path), json.dumps(profile), time.time()))


def get_dataset(ds_id):
    r = _run("SELECT * FROM datasets WHERE id=?", (ds_id,))
    return r[0] if r else None


def add_job(job_id, dataset_id, planner, spec: dict, total: int, warnings: list):
    now = time.time()
    _run("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
         (job_id, dataset_id, "queued", 0, total, planner, json.dumps(spec), None, json.dumps(warnings), None, now, now))


def update_job(job_id, **kw):
    if "stage2" in kw and not isinstance(kw["stage2"], (str, type(None))):
        kw["stage2"] = json.dumps(kw["stage2"], default=str)
    kw["updated"] = time.time()
    sets = ", ".join(f"{k}=?" for k in kw)
    _run(f"UPDATE jobs SET {sets} WHERE id=?", (*kw.values(), job_id))


def get_job(job_id):
    r = _run("SELECT * FROM jobs WHERE id=?", (job_id,))
    if not r:
        return None
    j = r[0]
    j["spec"] = json.loads(j["spec"])
    j["warnings"] = json.loads(j["warnings"] or "[]")
    j["stage2"] = json.loads(j["stage2"]) if j["stage2"] else None
    return j


def mark_interrupted():
    _run("UPDATE jobs SET status='failed', message='interrupted by a server restart' WHERE status IN ('queued','running')")
