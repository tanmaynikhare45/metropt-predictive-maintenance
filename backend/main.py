"""MetroPT API.

Run from the project root:
    uvicorn backend.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs

Notes
- The data is historic, so "the last N hours" is measured from the newest reading
  (or from the optional `end` parameter), not from the clock.
- Every endpoint that returns a time series downsamples in SQL and caps the rows.
"""
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Optional
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from psycopg import sql
from confluent_kafka.admin import AdminClient, NewTopic

from ml.inference import forecast_sensor, load_models

from .db import make_pool

load_dotenv()

MAX_ROWS = 5000
# A 10-minute bucket with fewer readings than this is treated as "machine off" (about half of normal).
MIN_ROWS_PER_WINDOW = int(os.getenv("MIN_ROWS_PER_WINDOW", "25"))
FORECAST_TTL_S = 600

ANALOG_COLS = ["tp2", "tp3", "h1", "dv_pressure", "reservoirs", "oil_temperature", "motor_current"]
DIGITAL_COLS = ["comp", "dv_eletric", "towers", "mpg", "lps", "pressure_switch", "oil_level", "caudal_impulses"]
ALL_COLS = ANALOG_COLS + DIGITAL_COLS
PRED_MODELS = {"iforest", "lstm_ae", "failure_risk"}

# newest reading unless the caller passes `end`
ANCHOR = "COALESCE(%(end)s::timestamptz, (SELECT max(time) FROM sensor_readings))"

_forecast_cache = {}
ROOT = Path(__file__).resolve().parents[1]
_simulation_lock = Lock()


class SimulationRequest(BaseModel):
    start: datetime
    end: datetime
    speed: float = Field(default=60, ge=1, le=1000)
    reset_interval: bool = False


def _local_simulation_request(request: Request):
    # Simulation launches a local producer process; keep this endpoint unavailable to remote callers.
    if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403, "simulation controls are available only from this machine")


def _consumer_group_active(admin, group_id):
    group = admin.describe_consumer_groups([group_id])[group_id].result(timeout=5)
    return str(group.state).split(".")[-1].lower() == "stable" and bool(group.members)


def _delete_simulation_topic(bootstrap: str, topic: str):
    try:
        admin = AdminClient({"bootstrap.servers": bootstrap})
        admin.delete_topics([topic], operation_timeout=5)[topic].result(timeout=7)
    except Exception:
        pass


def _ensure_simulation_consumer(request: Request, bootstrap: str, group_id: str, topic: str):
    admin = AdminClient({"bootstrap.servers": bootstrap})
    try:
        admin.list_topics(timeout=5)
    except Exception as exc:
        raise HTTPException(503, f"Kafka broker is not reachable at {bootstrap}; start Kafka with docker compose -f infra/docker-compose.yml up -d kafka ({exc.__class__.__name__})")
    try:
        admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)])[topic].result(timeout=10)
    except Exception as exc:
        raise HTTPException(503, f"could not create an isolated Kafka topic for this replay ({exc.__class__.__name__})")

    process = subprocess.Popen(
        [sys.executable, "-m", "streaming.consumer", "--bootstrap", bootstrap,
         "--group", group_id, "--topic", topic, "--idle-exit", "15"],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    request.app.state.simulation_consumer = process

    deadline = time.monotonic() + 30
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise HTTPException(503, "the streaming consumer exited during startup; check the database, models, and Kafka settings")
        try:
            if _consumer_group_active(admin, group_id):
                return process
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    reason = f" ({last_error.__class__.__name__})" if last_error else ""
    raise HTTPException(503, f"Kafka is running, but consumer group {group_id} did not become active within 30 seconds{reason}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = make_pool()
    app.state.pool.open()
    app.state.models = load_models(load_lstm=False)     # the API does not need torch
    app.state.simulation = None
    app.state.simulation_consumer = None
    yield
    for process in (app.state.simulation, app.state.simulation_consumer):
        if process and process.poll() is None:
            process.terminate()
    app.state.pool.close()


app = FastAPI(title="MetroPT Predictive Maintenance API", version="0.1.0", lifespan=lifespan)
# In development the browser origin can be http://localhost:5173 or http://127.0.0.1:5173 (or another
# Vite port). Set CORS_ALLOW_LOCALHOST=0 in production and list the real origins in CORS_ORIGINS.
LOCALHOST_REGEX = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_origin_regex=LOCALHOST_REGEX if os.getenv("CORS_ALLOW_LOCALHOST", "1") == "1" else None,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    return JSONResponse(
        status_code=500,
        content={"detail": f"{exc.__class__.__name__}: {str(exc)}"},
    )


@app.post("/simulation/start")
def start_simulation(body: SimulationRequest, request: Request):
    """Replay a historical interval into Kafka for the running consumer to score and alert on."""
    _local_simulation_request(request)
    start = body.start if body.start.tzinfo else body.start.replace(tzinfo=timezone.utc)
    end = body.end if body.end.tzinfo else body.end.replace(tzinfo=timezone.utc)
    if end <= start:
        raise HTTPException(422, "end must be later than start")
    if end - start > timedelta(days=8):
        raise HTTPException(422, "a simulation can cover at most 8 days")
    parquet = ROOT / "data" / "processed" / "metropt3.parquet"
    if not parquet.is_file():
        raise HTTPException(503, "processed sensor data is missing: data/processed/metropt3.parquet")
    from alerts import config as alert_config
    from streaming import config as streaming_config
    if not alert_config.SLACK_WEBHOOK_URL:
        raise HTTPException(503, "set SLACK_WEBHOOK_URL in .env before starting a Slack simulation")
    if not body.reset_interval:
        raise HTTPException(422, "confirm reset_interval to replace stored readings, predictions, and alerts in this simulation range")
    with _simulation_lock:
        process = request.app.state.simulation
        if process and process.poll() is None:
            info = getattr(request.app.state, "simulation_info", {})
            same_range = (info.get("start") and info.get("end") and
                          datetime.fromisoformat(info["start"]) == start and
                          datetime.fromisoformat(info["end"]) == end)
            if same_range:
                return {"status": "already_running", **info}
            raise HTTPException(409, "another simulation is running; stop it or reload the dashboard to reconnect")
        run_id = uuid4().hex[:12]
        topic = f"sensors.simulation.{run_id}"
        group_id = f"metropt-simulation-{run_id}"
        consumer = _ensure_simulation_consumer(request, streaming_config.BOOTSTRAP, group_id, topic)
        reset = subprocess.run(
            [sys.executable, "scripts/reset_replay_range.py", "--from",
             start.astimezone(timezone.utc).replace(tzinfo=None).date().isoformat() + " " +
             start.astimezone(timezone.utc).replace(tzinfo=None).time().isoformat(timespec="seconds"),
             "--to", end.astimezone(timezone.utc).replace(tzinfo=None).date().isoformat() + " " +
             end.astimezone(timezone.utc).replace(tzinfo=None).time().isoformat(timespec="seconds"),
             "--yes"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        if reset.returncode:
            if consumer and consumer.poll() is None:
                consumer.terminate()
            _delete_simulation_topic(streaming_config.BOOTSTRAP, topic)
            raise HTTPException(503, f"could not prepare the simulation range ({reset.stderr.strip()[-300:]})")
        process = subprocess.Popen(
            [sys.executable, "-m", "streaming.producer", "--bootstrap", streaming_config.BOOTSTRAP,
             "--topic", topic, "--start",
             start.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" "),
             "--end", end.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" "),
             "--speed", str(body.speed)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        request.app.state.simulation = process
        request.app.state.simulation_consumer = consumer
        request.app.state.simulation_info = {
            "start": start.isoformat(), "end": end.isoformat(), "speed": body.speed,
            "process_id": process.pid, "consumer_process_id": consumer.pid if consumer else None, "topic": topic,
        }
    return {"status": "started", "reset_rows": reset.stdout.strip().splitlines()[:1], **request.app.state.simulation_info}


@app.get("/simulation/status")
def simulation_status(request: Request):
    _local_simulation_request(request)
    process = request.app.state.simulation
    info = getattr(request.app.state, "simulation_info", {})
    if not process:
        return {"status": "idle"}
    code = process.poll()
    consumer = request.app.state.simulation_consumer
    consumer_code = consumer.poll() if consumer else None
    sensor_time = None
    if info.get("start") and info.get("end"):
        try:
            rows = run(request,
                       "SELECT max(time) AS time FROM sensor_readings WHERE time >= %(start)s AND time < %(end)s",
                       {"start": datetime.fromisoformat(info["start"]),
                        "end": datetime.fromisoformat(info["end"])})
            sensor_time = rows[0]["time"]
        except Exception:
            pass
    drained = False
    if code == 0 and consumer_code == 0 and sensor_time is not None:
        finish = datetime.fromisoformat(info["end"])
        drained = sensor_time >= finish - timedelta(minutes=1)
    failed = (code is not None and code != 0) or (consumer_code is not None and consumer_code != 0)
    incomplete = code == 0 and consumer_code == 0 and not drained
    status = "failed" if failed else ("completed" if drained else ("incomplete" if incomplete else ("draining" if code == 0 else "running")))
    progress = 0.0
    if sensor_time is not None and info.get("start") and info.get("end"):
        start = datetime.fromisoformat(info["start"])
        finish = datetime.fromisoformat(info["end"])
        progress = max(0.0, min(100.0, (sensor_time - start).total_seconds() / (finish - start).total_seconds() * 100))
    if code is not None and consumer_code is not None and info.get("topic") and not info.get("topic_cleaned"):
        from streaming.config import BOOTSTRAP
        _delete_simulation_topic(BOOTSTRAP, info["topic"])
        info["topic_cleaned"] = True
    return {"status": status, "publisher": "running" if code is None else ("completed" if code == 0 else "failed"),
            "consumer": "running" if consumer_code is None else ("stopped" if consumer_code == 0 else "failed"),
            "progress": progress, "return_code": code,
            "consumer_return_code": consumer_code,
            "sensor_time": sensor_time.isoformat() if sensor_time else None, **info}


@app.post("/simulation/stop")
def stop_simulation(request: Request):
    _local_simulation_request(request)
    process = request.app.state.simulation
    consumer = request.app.state.simulation_consumer
    stopping = False
    if process and process.poll() is None:
        process.terminate()
        stopping = True
    if consumer and consumer.poll() is None:
        consumer.terminate()
        stopping = True
    for child in (process, consumer):
        if child and child.poll() is None:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
    if process and process.poll() is not None and consumer and consumer.poll() is not None:
        info = getattr(request.app.state, "simulation_info", {})
        if info.get("topic"):
            from streaming.config import BOOTSTRAP
            _delete_simulation_topic(BOOTSTRAP, info["topic"])
            info["topic_cleaned"] = True
    if process and process.poll() is not None and consumer and consumer.poll() is not None:
        request.app.state.simulation = None
        request.app.state.simulation_consumer = None
        request.app.state.simulation_info = {}
    return {"status": "stopping" if stopping else "idle"}


def run(request: Request, query, params=None):
    with request.app.state.pool.connection() as conn:
        return conn.execute(query, params or {}).fetchall()


def parse_sensors(text: str):
    cols = [c.strip().lower() for c in text.split(",") if c.strip()]
    bad = [c for c in cols if c not in ALL_COLS]
    if not cols or bad:
        raise HTTPException(422, f"unknown sensor(s) {bad or text!r}; choose from {ALL_COLS}")
    return cols


@app.get("/health")
def health(request: Request):
    try:
        run(request, "SELECT 1")
    except Exception as exc:
        raise HTTPException(503, f"database unavailable ({exc.__class__.__name__})")
    m = request.app.state.models
    return {
        "status": "ok",
        "database": True,
        "models": {
            "anomaly": m.iso is not None and m.scaler is not None,
            "failure": m.failure is not None,
            "forecast_config": m.forecast_cfg is not None,
        },
    }


@app.get("/config")
def config(request: Request):
    """Thresholds and settings the dashboard needs to draw its charts."""
    m = request.app.state.models
    a, f, fc = m.anomaly_cfg or {}, m.failure_cfg or {}, m.forecast_cfg or {}
    return {
        "iforest_threshold": a.get("isolation_forest_threshold"),
        "lstm_threshold": a.get("lstm_threshold"),
        "failure_threshold": f.get("threshold"),
        "failure_horizon_hours": f.get("horizon_hours"),
        "min_consecutive_windows": a.get("min_consecutive_windows"),
        "window": a.get("window", "10min"),
        "forecast_sensors": fc.get("sensors", ["TP2", "Oil_temperature"]),
        "forecast_steps": fc.get("steps", 36),
        "forecast_interval": fc.get("interval_width", 0.9),
    }


@app.get("/sensors")
def sensors(
    request: Request,
    hours: int = Query(6, ge=1, le=168),
    bucket_minutes: int = Query(1, ge=1, le=60),
    sensors: str = Query(",".join(ANALOG_COLS), description="comma-separated column names"),
    end: Optional[datetime] = None,
):
    cols = parse_sensors(sensors)
    if hours * 60 / bucket_minutes > MAX_ROWS:
        raise HTTPException(422, f"too many rows (> {MAX_ROWS}); use a larger bucket_minutes or fewer hours")
    select_cols = sql.SQL(", ").join(
        sql.SQL("avg({c}) AS {c}").format(c=sql.Identifier(c)) for c in cols
    )
    query = sql.SQL(
        "SELECT time_bucket(make_interval(mins => %(b)s), time) AS time, {cols} "
        "FROM sensor_readings "
        "WHERE time > " + ANCHOR + " - make_interval(hours => %(h)s) AND time <= " + ANCHOR + " "
        "GROUP BY 1 ORDER BY 1 LIMIT %(lim)s"
    ).format(cols=select_cols)
    return run(request, query, {"b": bucket_minutes, "h": hours, "end": end, "lim": MAX_ROWS})


@app.get("/predictions")
def predictions(
    request: Request,
    model: str = Query("iforest"),
    hours: int = Query(24, ge=1, le=168),
    end: Optional[datetime] = None,
):
    if model not in PRED_MODELS:
        raise HTTPException(422, f"model must be one of {sorted(PRED_MODELS)}")
    pred_anchor = "%(end)s::timestamptz" if end else "COALESCE((SELECT max(time) FROM predictions WHERE model = %(m)s), (SELECT max(time) FROM sensor_readings))"
    query = (
        "SELECT time, score, flag FROM predictions "
        "WHERE model = %(m)s AND time > " + pred_anchor + " - make_interval(hours => %(h)s) AND time <= " + pred_anchor + " "
        "ORDER BY time LIMIT %(lim)s"
    )
    return run(request, query, {"m": model, "h": hours, "end": end, "lim": MAX_ROWS})


@app.get("/failures")
def failures(request: Request):
    return run(request, "SELECT id, start_time, end_time FROM failure_events ORDER BY start_time")


@app.get("/alerts")
def alerts(request: Request, limit: int = Query(50, ge=1, le=500)):
    return run(request, "SELECT id, time, kind, severity, message, top_sensors FROM alerts ORDER BY time DESC LIMIT %(n)s",
               {"n": limit})


@app.get("/latest")
def latest(request: Request, end: Optional[datetime] = None):
    row = run(request, "SELECT * FROM sensor_readings WHERE time <= " + ANCHOR + " ORDER BY time DESC LIMIT 1",
              {"end": end})
    preds = run(request,
                "SELECT DISTINCT ON (model) model, time, score, flag FROM predictions "
                "WHERE time <= " + ANCHOR + " ORDER BY model, time DESC", {"end": end})
    return {
        "sensors": row[0] if row else None,
        "predictions": {p["model"]: {"time": p["time"], "score": p["score"], "flag": p["flag"]} for p in preds},
    }


@app.get("/forecast")
def forecast(request: Request, sensor: str = Query("TP2"), end: Optional[datetime] = None):
    models = request.app.state.models
    allowed = (models.forecast_cfg or {}).get("sensors", ["TP2", "Oil_temperature"])
    by_lower = {s.lower(): s for s in allowed}
    if sensor.lower() not in by_lower:
        raise HTTPException(422, f"sensor must be one of {allowed}")
    name = by_lower[sensor.lower()]
    col = name.lower()

    query = sql.SQL(
        "SELECT time_bucket('10 minutes', time) AS t, avg({c}) AS v FROM sensor_readings "
        "WHERE time > " + ANCHOR + " - interval '14 days' AND time <= " + ANCHOR + " "
        "GROUP BY 1 HAVING count(*) >= %(minrows)s ORDER BY 1"
    ).format(c=sql.Identifier(col))
    rows = run(request, query, {"end": end, "minrows": MIN_ROWS_PER_WINDOW})
    if len(rows) < 144:
        raise HTTPException(404, "not enough history before this time to fit a forecast (need about 1 day)")

    idx = pd.DatetimeIndex([r["t"] for r in rows]).tz_convert(None)    # models use naive UTC timestamps
    series = pd.Series([r["v"] for r in rows], index=idx).dropna()

    key = (name, series.index[-1])
    cached = _forecast_cache.get(key)
    if cached and cached[0] > time.time():
        return cached[1]

    try:
        fc = forecast_sensor(models, series, name)
    except ImportError:
        raise HTTPException(503, "prophet is not installed (pip install prophet)")

    payload = {
        "sensor": name,
        "history": [{"time": t.isoformat(), "value": float(v)} for t, v in series.iloc[-144:].items()],
        "forecast": [{"time": t.isoformat(), "yhat": float(r.yhat), "lower": float(r.lower), "upper": float(r.upper)}
                     for t, r in fc.iterrows()],
        "method": (models.forecast_cfg or {}).get("best_method", {}).get(name, "prophet_level"),
    }
    _forecast_cache[key] = (time.time() + FORECAST_TTL_S, payload)
    return payload
