-- Runs automatically the FIRST time the database volume is created.
-- To re-run it from scratch:  docker compose down -v   then   docker compose up -d

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------- raw sensor data
CREATE TABLE IF NOT EXISTS sensor_readings (
    time            TIMESTAMPTZ NOT NULL,
    tp2             DOUBLE PRECISION,
    tp3             DOUBLE PRECISION,
    h1              DOUBLE PRECISION,
    dv_pressure     DOUBLE PRECISION,
    reservoirs      DOUBLE PRECISION,
    oil_temperature DOUBLE PRECISION,
    motor_current   DOUBLE PRECISION,
    comp            DOUBLE PRECISION,
    dv_eletric      DOUBLE PRECISION,
    towers          DOUBLE PRECISION,
    mpg             DOUBLE PRECISION,
    lps             DOUBLE PRECISION,
    pressure_switch DOUBLE PRECISION,
    oil_level       DOUBLE PRECISION,
    caudal_impulses DOUBLE PRECISION
);
SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);
-- unique time: replaying the same data twice must not create duplicates
CREATE UNIQUE INDEX IF NOT EXISTS sensor_readings_time_uq ON sensor_readings (time);

-- ---------------------------------------------------------------- model outputs (one row per 10-min window per model)
CREATE TABLE IF NOT EXISTS predictions (
    time    TIMESTAMPTZ NOT NULL,          -- start of the 10-minute window
    model   TEXT NOT NULL,                 -- 'iforest' | 'lstm_ae' | 'failure_risk'
    score   DOUBLE PRECISION NOT NULL,
    flag    BOOLEAN
);
SELECT create_hypertable('predictions', 'time', if_not_exists => TRUE);
CREATE UNIQUE INDEX IF NOT EXISTS predictions_model_time_uq ON predictions (model, time);

-- ---------------------------------------------------------------- cached forecasts
CREATE TABLE IF NOT EXISTS forecasts (
    made_at TIMESTAMPTZ NOT NULL,
    sensor  TEXT NOT NULL,
    ts      TIMESTAMPTZ NOT NULL,
    yhat    DOUBLE PRECISION,
    lower   DOUBLE PRECISION,
    upper   DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS forecasts_sensor_made_idx ON forecasts (sensor, made_at DESC);

-- ---------------------------------------------------------------- alerts (filled in Phase 6)
CREATE TABLE IF NOT EXISTS alerts (
    id          BIGSERIAL PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,
    kind        TEXT NOT NULL,             -- 'anomaly' | 'failure_risk'
    severity    TEXT NOT NULL,             -- 'warning' | 'critical'
    message     TEXT,
    top_sensors JSONB
);
CREATE INDEX IF NOT EXISTS alerts_time_idx ON alerts (time DESC);

-- ---------------------------------------------------------------- the 4 known failures
CREATE TABLE IF NOT EXISTS failure_events (
    id         SERIAL PRIMARY KEY,
    start_time TIMESTAMPTZ NOT NULL,
    end_time   TIMESTAMPTZ NOT NULL
);

-- ---------------------------------------------------------------- model bookkeeping
CREATE TABLE IF NOT EXISTS model_metadata (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    version    TEXT NOT NULL,
    trained_at TIMESTAMPTZ DEFAULT now(),
    metrics    JSONB
);
