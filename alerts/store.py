"""Read and write the `alerts` table. Writes are idempotent: (kind, time) is unique."""
import os
import threading

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class AlertStore:
    def __init__(self, url=None, schema=None):
        self.url = url or os.environ["DATABASE_URL"]
        self.options = "-c timezone=UTC" + (f" -c search_path={schema}" if schema else "")
        self._conn = None
        self._lock = threading.Lock()           # the service thread and the Slack thread share this store

    def _connect(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.url, options=self.options, connect_timeout=5, row_factory=dict_row)
        return self._conn

    def _run(self, fn):
        with self._lock:
            conn = self._connect()
            try:
                result = fn(conn)
                conn.commit()
                return result
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                self._conn = None
                raise

    def insert(self, time, kind, severity, message, top_sensors):
        """Returns the new id, or None if an alert with the same (kind, time) already exists."""
        def fn(conn):
            row = conn.execute(
                "INSERT INTO alerts (time, kind, severity, message, top_sensors) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (kind, time) DO NOTHING RETURNING id",
                (pd.Timestamp(time).to_pydatetime(), kind, severity, message, Jsonb(top_sensors)),
            ).fetchone()
            return row["id"] if row else None
        return self._run(fn)

    def mark_delivered(self, alert_id):
        self._run(lambda conn: conn.execute(
            "UPDATE alerts SET delivered = TRUE, delivered_at = now() WHERE id = %s", (alert_id,)))

    def history_before(self, time, limit=50):
        """Alerts older than `time`, newest first (used to rebuild the incident state after a restart)."""
        def fn(conn):
            return conn.execute(
                "SELECT time, kind, severity FROM alerts WHERE time < %s ORDER BY time DESC LIMIT %s",
                (pd.Timestamp(time).to_pydatetime(), limit)).fetchall()
        return self._run(fn)

    def undelivered(self, since, until=None, limit=5):
        """Stored alerts that never reached Slack, oldest first."""
        def fn(conn):
            return conn.execute(
                "SELECT id, time, kind, severity, message FROM alerts "
                "WHERE delivered = FALSE AND time >= %s AND time < COALESCE(%s::timestamptz, 'infinity') "
                "ORDER BY time LIMIT %s",
                (pd.Timestamp(since).to_pydatetime(),
                 pd.Timestamp(until).to_pydatetime() if until is not None else None, limit)).fetchall()
        return self._run(fn)

    def close(self):
        with self._lock:
            if self._conn is not None and not self._conn.closed:
                self._conn.close()
