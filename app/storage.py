"""Persistência dos lotes e das observações públicas de vídeos."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
import uuid

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
LOCK = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def connection():
    db = sqlite3.connect(DATA / "cortes.db", timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    return db


with connection() as db:
    db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, updated TEXT, data TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS observations (video_id TEXT, observed REAL, views INTEGER)")


def save(job):
    with LOCK, connection() as db:
        job["updated_at"] = now()
        db.execute("INSERT OR REPLACE INTO jobs VALUES (?, ?, ?)",
                   (job["id"], job["updated_at"], json.dumps(job, ensure_ascii=False)))


def get(identifier):
    with LOCK, connection() as db:
        row = db.execute("SELECT data FROM jobs WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise KeyError("Lote não encontrado")
    return json.loads(row[0])


def jobs():
    with LOCK, connection() as db:
        rows = db.execute("SELECT data FROM jobs ORDER BY updated DESC").fetchall()
    return [json.loads(row[0]) for row in rows]


def create(options):
    identifier = uuid.uuid4().hex[:16]
    job = {"id": identifier, "topic": options["topic"], "options": options,
           "created_at": now(), "status": "queued", "stage": "queued", "progress": 0,
           "message": "Aguardando processamento", "sources": [], "references": [],
           "clips": [], "events": [], "warnings": [], "error": None}
    (DATA / identifier).mkdir()
    save(job)
    return job


def update(identifier, **changes):
    with LOCK:
        job = get(identifier)
        job.update(changes)
        save(job)
    return job


def event(identifier, stage, progress, message):
    with LOCK:
        job = get(identifier)
        job.update(stage=stage, progress=progress, message=message)
        job["events"].append({"at": now(), "stage": stage, "message": message})
        save(job)


def observe(identifier, views, timestamp):
    if views is None:
        return None
    with LOCK, connection() as db:
        previous = db.execute("SELECT observed, views FROM observations WHERE video_id=? "
                              "AND observed<? ORDER BY observed DESC LIMIT 1",
                              (identifier, timestamp - 3600)).fetchone()
        db.execute("INSERT INTO observations VALUES (?, ?, ?)", (identifier, timestamp, int(views)))
    if previous and views >= previous[1]:
        return round((views - previous[1]) / ((timestamp - previous[0]) / 3600), 2)
    return None
