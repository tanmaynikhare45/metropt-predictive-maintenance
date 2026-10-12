"""Replay the dataset into Kafka like a live train.

    python -m streaming.producer --start 2020-06-05 --end 2020-06-08 --speed 200

--speed 200   200x faster than real time (use 0 to send as fast as possible)
--bad-every N send a malformed message every N readings, to demo the dead-letter topic
"""
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from confluent_kafka import Producer

from ml.features import SENSORS

from . import config

ROOT = Path(__file__).resolve().parents[1]
MAX_GAP_SECONDS = 2.0        # long gaps (machine off) are shortened to this many wall-clock seconds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default=str(ROOT / "data/processed/metropt3.parquet"))
    ap.add_argument("--start", default=None, help="first timestamp to replay, e.g. 2020-06-05")
    ap.add_argument("--end", default=None, help="last timestamp to replay, e.g. 2020-06-08")
    ap.add_argument("--speed", type=float, default=100.0)
    ap.add_argument("--limit", type=int, default=None, help="stop after this many readings")
    ap.add_argument("--bad-every", type=int, default=0)
    ap.add_argument("--bootstrap", default=config.BOOTSTRAP)
    args = ap.parse_args()

    df = pd.read_parquet(args.parquet).sort_index()          # the UNLABELED file: no failure labels
    df = df[~df.index.duplicated(keep="first")]
    df = df.loc[args.start:args.end]
    if args.limit:
        df = df.iloc[: args.limit]
    if len(df) == 0:
        sys.exit("No readings in that range.")

    cols = [c.lower() for c in SENSORS]
    values = df[SENSORS].astype(float).to_numpy()
    index = df.index
    print(f"Replaying {len(df):,} readings from {index[0]} to {index[-1]} at speed x{args.speed:g} -> {config.TOPIC_RAW}")

    failed = []

    def on_delivery(err, msg):
        if err is not None:
            failed.append(str(err))

    producer = Producer({"bootstrap.servers": args.bootstrap, "linger.ms": 20})
    t_data0 = index[0]
    wall0 = time.monotonic()
    sent = 0
    try:
        for i in range(len(df)):
            if args.speed > 0:
                target = wall0 + (index[i] - t_data0).total_seconds() / args.speed
                delay = target - time.monotonic()
                if delay > MAX_GAP_SECONDS:
                    wall0 -= delay - MAX_GAP_SECONDS          # skip the long gap, keep the schedule consistent
                    delay = MAX_GAP_SECONDS
                if delay > 0:
                    time.sleep(delay)

            if args.bad_every and i > 0 and i % args.bad_every == 0:
                payload = json.dumps({"time": "not-a-time", "tp2": "abc"})
            else:
                payload = json.dumps({"time": index[i].isoformat(), **dict(zip(cols, values[i].tolist()))})

            while True:
                try:
                    producer.produce(config.TOPIC_RAW, payload.encode("utf-8"), on_delivery=on_delivery)
                    break
                except BufferError:                           # local queue full: wait for deliveries
                    producer.poll(0.5)
            producer.poll(0)
            sent += 1
            if sent % 5000 == 0:
                print(f"  sent {sent:,} / {len(df):,}   (data time {index[i]})")
    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        producer.flush(10)
    print(f"Done. Sent {sent:,} messages. Delivery errors: {len(failed)}")
    if failed:
        print("First error:", failed[0])


if __name__ == "__main__":
    main()
