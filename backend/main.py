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
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from psycopg import sql

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = make_pool()
    app.state.pool.open()
    app.state.models = load_models(load_lstm=False)     # the API does not need torch
    yield
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
    query = (
        "SELECT time, score, flag FROM predictions "
        "WHERE model = %(m)s AND time > " + ANCHOR + " - make_interval(hours => %(h)s) AND time <= " + ANCHOR + " "
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