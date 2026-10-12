"""API tests. They need the database running and loaded:

    cd infra && docker compose up -d
    python scripts/load_sensors.py
    pytest -q
They are skipped automatically if the database is not available.
"""
import os

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
URL = os.getenv("DATABASE_URL")


def _db_ready():
    if not URL:
        return False
    try:
        with psycopg.connect(URL, connect_timeout=3) as conn:
            return conn.execute("SELECT count(*) FROM sensor_readings").fetchone()[0] > 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_ready(), reason="database not running or sensor_readings is empty")


@pytest.fixture(scope="module")
def client():
    from backend.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sensors_default(client):
    r = client.get("/sensors")
    assert r.status_code == 200
    rows = r.json()
    assert 0 < len(rows) <= 5000
    assert {"time", "tp2", "oil_temperature"} <= set(rows[0])


def test_sensors_select_columns_and_bucket(client):
    r = client.get("/sensors", params={"hours": 24, "bucket_minutes": 10, "sensors": "tp2,motor_current"})
    assert r.status_code == 200
    rows = r.json()
    assert set(rows[0]) == {"time", "tp2", "motor_current"}
    assert len(rows) <= 24 * 6


def test_sensors_rejects_too_many_rows(client):
    assert client.get("/sensors", params={"hours": 168, "bucket_minutes": 1}).status_code == 422


def test_sensors_rejects_unknown_column(client):
    assert client.get("/sensors", params={"sensors": "tp2;DROP TABLE sensor_readings"}).status_code == 422


def test_predictions_validates_model(client):
    assert client.get("/predictions", params={"model": "nope"}).status_code == 422
    assert client.get("/predictions", params={"model": "iforest"}).status_code == 200


def test_failures_and_alerts(client):
    assert isinstance(client.get("/failures").json(), list)
    assert isinstance(client.get("/alerts").json(), list)


def test_latest(client):
    body = client.get("/latest").json()
    assert body["sensors"] is not None
    assert "predictions" in body


def test_forecast(client):
    pytest.importorskip("prophet")
    r = client.get("/forecast", params={"sensor": "TP2"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["forecast"]) == 36
    assert {"time", "yhat", "lower", "upper"} <= set(body["forecast"][0])
    assert client.get("/forecast", params={"sensor": "nope"}).status_code == 422
