"""Load the raw sensor data and the failure windows into the database.

Run from the project root:
    python scripts/load_sensors.py                 # first load
    python scripts/load_sensors.py --truncate      # wipe the tables and load again

Uses the UNLABELED parquet on purpose: the live path must never see the answers.
"""
import argparse
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import psycopg
from dotenv import load_dotenv

from ml.features import SENSORS

load_dotenv(ROOT / ".env")
CHUNK = 200_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default=str(ROOT / "data/processed/metropt3.parquet"))
    ap.add_argument("--failures", default=str(ROOT / "data/processed/failures.json"))
    ap.add_argument("--truncate", action="store_true", help="empty sensor_readings and failure_events first")
    args = ap.parse_args()

    df = pd.read_parquet(args.parquet)
    cols = [c.lower() for c in SENSORS]
    missing = [c for c in SENSORS if c not in df.columns]
    if missing:
        sys.exit(f"parquet is missing sensor columns: {missing}")
    df = df[SENSORS].astype(float)
    df.columns = cols
    df.index.name = "time"
    df = df[~df.index.duplicated(keep="first")].sort_index()
    print(f"Read {len(df):,} rows from {args.parquet} ({df.index.min()} -> {df.index.max()})")

    with psycopg.connect(os.environ["DATABASE_URL"], options="-c timezone=UTC") as conn:
        with conn.cursor() as cur:
            if args.truncate:
                cur.execute("TRUNCATE sensor_readings")
                cur.execute("TRUNCATE failure_events RESTART IDENTITY")
                print("Tables truncated.")
            else:
                n = cur.execute("SELECT count(*) FROM sensor_readings").fetchone()[0]
                if n:
                    sys.exit(f"sensor_readings already has {n:,} rows. Use --truncate to reload.")

            col_sql = ", ".join(["time"] + cols)
            with cur.copy(f"COPY sensor_readings ({col_sql}) FROM STDIN WITH (FORMAT csv)") as cp:
                for start in range(0, len(df), CHUNK):
                    buf = io.StringIO()
                    df.iloc[start:start + CHUNK].to_csv(buf, header=False, index=True, na_rep="")
                    cp.write(buf.getvalue())
                    print(f"  loaded {min(start + CHUNK, len(df)):,} / {len(df):,}")

            fpath = Path(args.failures)
            if fpath.exists():
                events = json.loads(fpath.read_text())
                cur.execute("DELETE FROM failure_events")
                for ev in events:
                    cur.execute("INSERT INTO failure_events (start_time, end_time) VALUES (%s, %s)",
                                (pd.Timestamp(ev["start"]).to_pydatetime(), pd.Timestamp(ev["end"]).to_pydatetime()))
                print(f"Loaded {len(events)} failure events.")

            n, lo, hi = cur.execute("SELECT count(*), min(time), max(time) FROM sensor_readings").fetchone()
            print(f"Done. sensor_readings: {n:,} rows, {lo} -> {hi}")


if __name__ == "__main__":
    main()
