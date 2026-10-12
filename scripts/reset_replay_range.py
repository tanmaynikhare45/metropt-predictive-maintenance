"""Delete readings, predictions and alerts from a date onwards so you can replay that range live.

    python scripts/reset_replay_range.py --from 2020-06-05                  # asks for confirmation
    python scripts/reset_replay_range.py --from 2020-06-05 --to 2020-06-09 --yes

The history BEFORE --from stays, because the consumer rebuilds its 24 h of context from it.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--to", dest="end", default=None, help="exclusive; default = everything after --from")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    start = pd.Timestamp(args.start).to_pydatetime()
    end = pd.Timestamp(args.end).to_pydatetime() if args.end else pd.Timestamp("2100-01-01").to_pydatetime()

    with psycopg.connect(os.environ["DATABASE_URL"], options="-c timezone=UTC") as conn:
        counts = {}
        for table in ("sensor_readings", "predictions", "alerts"):
            counts[table] = conn.execute(f"SELECT count(*) FROM {table} WHERE time >= %s AND time < %s",
                                         (start, end)).fetchone()[0]
        print(f"Range {start} -> {args.end or 'end'}:", counts)
        if not args.yes and input("Delete these rows? type yes: ").strip().lower() != "yes":
            sys.exit("Cancelled.")
        for table in counts:
            conn.execute(f"DELETE FROM {table} WHERE time >= %s AND time < %s", (start, end))
        conn.commit()
        print("Deleted.")


if __name__ == "__main__":
    main()
