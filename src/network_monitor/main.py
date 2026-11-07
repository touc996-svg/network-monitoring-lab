from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import initialize_database
from .schemas import TargetCreate
from .service import (
    create_target,
    list_targets,
    monitoring_summary,
    recent_checks,
    run_check,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Network Monitoring Lab",
    description=(
        "Local network availability monitoring for explicitly registered "
        "and authorized hosts. Supports TCP connectivity and DNS resolution checks."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health", tags=["Operations"])
def health():
    return {"status": "healthy", "service": "network-monitoring-lab"}


@app.get("/api/v1/summary", tags=["Monitoring"])
def summary():
    return monitoring_summary()


@app.get("/api/v1/targets", tags=["Targets"])
def targets():
    return list_targets()


@app.post("/api/v1/targets", status_code=201, tags=["Targets"])
def add_target(payload: TargetCreate):
    try:
        return create_target(payload)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="A target with this name or host/check combination already exists.",
        ) from exc


@app.post("/api/v1/targets/{target_id}/check", tags=["Monitoring"])
def check_target(target_id: int):
    result = run_check(target_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Target not found.")
    return result


@app.get("/api/v1/checks", tags=["Monitoring"])
def checks(limit: int = Query(default=25, ge=1, le=100)):
    return recent_checks(limit)


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    page = STATIC_DIR / "dashboard.html"
    return HTMLResponse(page.read_text(encoding="utf-8"))
