"""Pipeline tests against a real database (skipped if DATABASE_URL is not reachable).
They only touch temporary schemas (test_stream_*) and drop them afterwards."""
import os

import pandas as pd
import psycopg
import pytest
from dotenv import load_dotenv

from ml.features import SENSORS
from streaming.pipeline import Pipeline
from streaming.schema import Reading, SENSOR_FIELDS
from streaming.scoring import Scorer
from streaming.sink import Sink
from streaming.windowing import WindowBuilder
from tests.helpers import make_raw
from tests.model_helpers import make_models

load_dotenv()
URL = os.getenv("DATABASE_URL")
MIN_ROWS = 5


def _db_ready():
    if not URL:
        return False
    try:
        with psycopg.connect(URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1 FROM sensor_readings LIMIT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_ready(), reason="database not available")


def make_schema(name):
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")
        conn.execute(f"CREATE SCHEMA {name}")
        conn.execute(f"CREATE TABLE {name}.sensor_readings (LIKE public.sensor_readings INCLUDING DEFAULTS)")
        conn.execute(f"CREATE UNIQUE INDEX ON {name}.sensor_readings (time)")
        conn.execute(f"CREATE TABLE {name}.predictions (LIKE public.predictions INCLUDING DEFAULTS)")
        conn.execute(f"CREATE UNIQUE INDEX ON {name}.predictions (model, time)")


def drop_schema(name):
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")


def table(name, what):
    with psycopg.connect(URL, options="-c timezone=UTC") as conn:
        if what == "predictions":
            return conn.execute(f"SELECT time, model, score, flag FROM {name}.predictions ORDER BY model, time").fetchall()
        return conn.execute(f"SELECT count(*), min(time), max(time) FROM {name}.sensor_readings").fetchall()


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    raw = make_raw(days=3, start="2030-01-01")                # year 2030: cannot clash with real data
    models = make_models(tmp_path_factory.mktemp("m"), raw, min_rows=MIN_ROWS)
    readings = [Reading.model_validate({"time": ts.isoformat(), **dict(zip(SENSOR_FIELDS, vals))})
                for ts, vals in zip(raw.index, raw[SENSORS].to_numpy().tolist())]
    names = ["test_stream_a", "test_stream_b", "test_stream_c"]
    for n in names:
        make_schema(n)
    yield models, readings
    for n in names:
        drop_schema(n)


def run(readings, schema, models, flush_every=300, final_flush=True):
    pipe = Pipeline(Sink(schema=schema), WindowBuilder(min_rows=MIN_ROWS), Scorer(models))
    for i, r in enumerate(readings):
        pipe.process(r)
        if (i + 1) % flush_every == 0:
            pipe.flush()
    if final_flush:
        pipe.flush()
    return pipe


def test_full_run_writes_raw_and_predictions(setup):
    models, readings = setup
    run(readings, "test_stream_a", models)
    n, lo, hi = table("test_stream_a", "raw")[0]
    assert n == len(readings)
    preds = table("test_stream_a", "predictions")
    assert {p[1] for p in preds} == {"iforest", "failure_risk"}


def test_replaying_the_same_data_creates_no_duplicates(setup):
    models, readings = setup
    before_raw = table("test_stream_a", "raw")
    before_pred = table("test_stream_a", "predictions")
    run(readings, "test_stream_a", models)                    # replay everything again
    assert table("test_stream_a", "raw") == before_raw
    assert table("test_stream_a", "predictions") == before_pred


def test_crash_and_restart_gives_the_same_result_as_an_uninterrupted_run(setup):
    models, readings = setup
    full = table("test_stream_a", "predictions")

    # run 1 "crashes": its last flush was at reading 1800; everything after is lost from memory
    run(readings[:2005], "test_stream_b", models, flush_every=300, final_flush=False)
    # Kafka redelivers from the last committed offset (reading 1800) to a NEW process
    run(readings[1800:], "test_stream_b", models, flush_every=300)

    assert table("test_stream_b", "raw")[0][0] == len(readings)
    restarted = table("test_stream_b", "predictions")
    assert len(restarted) == len(full)
    for a, b in zip(full, restarted):
        assert a[0] == b[0] and a[1] == b[1] and a[3] == b[3]
        assert abs(a[2] - b[2]) < 1e-9
