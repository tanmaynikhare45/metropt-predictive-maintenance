"""Batched, idempotent writes to TimescaleDB (and the read used at start-up)."""
import os

import pandas as pd
import psycopg

from ml.features import SENSORS

DB_COLS = [c.lower() for c in SENSORS]


class Sink:
    def __init__(self, url=None, schema=None):
        self.url = url or os.environ["DATABASE_URL"]
        self.options = "-c timezone=UTC" + (f" -c search_path={schema}" if schema else "")
        self.conn = None
        self.raw = []
        self.preds = []

    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg.connect(self.url, options=self.options, connect_timeout=5)
        return self.conn

    def add_raw(self, t, row):
        self.raw.append((t, *row))

    def add_predictions(self, rows):
        self.preds.extend(rows)

    def pending(self):
        return len(self.raw)

    def flush(self):
        """Write everything buffered in ONE transaction. Raises on failure and keeps the buffers."""
        if not self.raw and not self.preds:
            return 0
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                if self.raw:
                    cur.execute("CREATE TEMP TABLE _raw_stage (LIKE sensor_readings INCLUDING DEFAULTS) ON COMMIT DROP")
                    with cur.copy(f"COPY _raw_stage (time, {', '.join(DB_COLS)}) FROM STDIN") as cp:
                        for r in self.raw:
                            cp.write_row(r)
                    cur.execute("INSERT INTO sensor_readings SELECT * FROM _raw_stage ON CONFLICT DO NOTHING")
                if self.preds:
                    cur.execute("CREATE TEMP TABLE _pred_stage (LIKE predictions INCLUDING DEFAULTS) ON COMMIT DROP")
                    with cur.copy("COPY _pred_stage (time, model, score, flag) FROM STDIN") as cp:
                        for r in self.preds:
                            cp.write_row(r)
                    cur.execute("INSERT INTO predictions SELECT * FROM _pred_stage ON CONFLICT DO NOTHING")
            conn.commit()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None                 # reconnect on the next attempt
            raise
        n = len(self.raw)
        self.raw, self.preds = [], []
        return n

    def fetch_raw(self, start, end):
        """Raw readings with start <= time < end as a DataFrame (canonical sensor names, naive UTC index)."""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT time, {', '.join(DB_COLS)} FROM sensor_readings WHERE time >= %s AND time < %s ORDER BY time",
                    (pd.Timestamp(start).to_pydatetime(), pd.Timestamp(end).to_pydatetime()),
                )
                rows = cur.fetchall()
            conn.rollback()                  # do not keep a read transaction open
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None
            raise
        df = pd.DataFrame(rows, columns=["time"] + SENSORS)
        df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(None)
        return df.set_index("time").astype(float)

    def last_prediction_time(self):
        """Newest window that already has a stored score (naive UTC), or None."""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                row = cur.execute("SELECT max(time) FROM predictions WHERE model = 'iforest'").fetchone()
            conn.rollback()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            self.conn = None
            raise
        return pd.Timestamp(row[0]).tz_convert(None) if row[0] is not None else None

    def close(self):
        if self.conn is not None and not self.conn.closed:
            self.conn.close()
