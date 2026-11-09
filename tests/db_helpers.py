"""Shared helpers for tests that need the database. They only ever touch temporary test_* schemas."""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("DATABASE_URL")


def alerts_ready():
    """True if the database is up AND the alerts table has the Phase 6 columns (delivered, ...)."""
    if not URL:
        return False
    try:
        with psycopg.connect(URL, connect_timeout=3) as conn:
            cols = {r[0] for r in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'alerts'").fetchall()}
        return {"delivered", "delivered_at"} <= cols
    except Exception:
        return False


def make_schema(name, with_readings=False):
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")
        conn.execute(f"CREATE SCHEMA {name}")
        conn.execute(f"CREATE TABLE {name}.alerts (LIKE public.alerts INCLUDING DEFAULTS)")
        conn.execute(f"CREATE UNIQUE INDEX ON {name}.alerts (kind, time)")
        if with_readings:
            conn.execute(f"CREATE TABLE {name}.sensor_readings (LIKE public.sensor_readings INCLUDING DEFAULTS)")
            conn.execute(f"CREATE UNIQUE INDEX ON {name}.sensor_readings (time)")
            conn.execute(f"CREATE TABLE {name}.predictions (LIKE public.predictions INCLUDING DEFAULTS)")
            conn.execute(f"CREATE UNIQUE INDEX ON {name}.predictions (model, time)")


def drop_schema(name):
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")


def alert_rows(name):
    with psycopg.connect(URL, options="-c timezone=UTC") as conn:
        return conn.execute(
            f"SELECT time, kind, severity, delivered, message FROM {name}.alerts ORDER BY time, kind").fetchall()
