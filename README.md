# Network Monitoring Lab

A small FastAPI service that registers network targets, runs **TCP connection** and **DNS resolution** checks on them, stores the results in SQLite, and shows a simple dashboard.

## Status
A working MVP. Checks run **only when you trigger them** (there is no scheduler or alerting yet). Verified locally: 5 passing tests.

## Features
- Register a target as a TCP check (host + port) or a DNS check (host only); input is validated (no URLs, valid ports).
- Run a check on demand and record up/down status and timing in SQLite.
- Summary counts (total, up, down, unchecked) and recent check history.
- Interactive API docs at `/docs` and a dashboard at `/dashboard`.

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service health |
| GET | `/api/v1/summary` | Counts of targets by state |
| GET / POST | `/api/v1/targets` | List or register targets |
| POST | `/api/v1/targets/{id}/check` | Run a check now |
| GET | `/api/v1/checks?limit=25` | Recent check results |

## Run it
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
uvicorn network_monitor.main:app --reload
```
Open http://127.0.0.1:8000/dashboard. The database defaults to `data/network_monitor.db`; set `NETWORK_MONITOR_DB_PATH` to change it.

## Test
```bash
python -m pytest -q
```

## Stack
Python 3.11+, FastAPI, Pydantic, SQLite, pytest.

## Possible next steps
Scheduled checks, alert notifications, and a Docker image.
