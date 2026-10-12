"""Kafka consumer: validate -> window -> score -> store.

    python -m streaming.consumer            # Isolation Forest + failure risk
    python -m streaming.consumer --lstm     # also the LSTM autoencoder (needs torch)

Delivery is AT-LEAST-ONCE: Kafka offsets are committed only AFTER the database write succeeded.
Because every write is idempotent (ON CONFLICT DO NOTHING), a crash or restart never loses data
and never creates duplicates.
"""
import argparse
import json
import signal
import sys
import time

import psycopg
from confluent_kafka import Consumer, KafkaError, Producer

from ml.inference import load_models

from . import config
from .pipeline import Pipeline
from .schema import parse_reading
from .scoring import Scorer
from .sink import Sink
from .windowing import WindowBuilder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default=config.BOOTSTRAP)
    ap.add_argument("--group", default=config.GROUP_ID)
    ap.add_argument("--lstm", action="store_true", help="also load and run the LSTM autoencoder")
    ap.add_argument("--idle-exit", type=float, default=0, help="exit after this many idle seconds (0 = never)")
    args = ap.parse_args()

    models = load_models(load_lstm=args.lstm)
    if models.anomaly_cfg is None:
        sys.exit("No saved models found in ml/models/. Run notebook 02 first.")

    sink = Sink()
    builder = WindowBuilder(min_rows=config.MIN_ROWS_PER_WINDOW)
    pipeline = Pipeline(sink, builder, Scorer(models))
    print(f"Models: anomaly={models.iso is not None}, lstm={models.lstm is not None}, failure={models.failure is not None}"
          f" | min readings per window = {config.MIN_ROWS_PER_WINDOW}")

    consumer = Consumer({
        "bootstrap.servers": args.bootstrap,
        "group.id": args.group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,                 # we commit manually, after the database write
    })
    consumer.subscribe([config.TOPIC_RAW])
    dlq = Producer({"bootstrap.servers": args.bootstrap})

    state = {"running": True, "bad": 0, "msgs": 0}

    def stop(*_):
        state["running"] = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    def flush_and_commit(last_msg):
        """Write buffered data, then commit offsets. Retries while the database is down."""
        while True:
            try:
                pipeline.flush()
                break
            except psycopg.Error as exc:
                print(f"[consumer] database error, retrying in 2 s: {exc.__class__.__name__}")
                if not state["running"]:
                    return False                      # shutting down: leave offsets uncommitted, Kafka will redeliver
                time.sleep(2)
        dlq.flush(5)
        if last_msg is not None:
            consumer.commit(message=last_msg, asynchronous=False)
        return True

    print(f"Listening on {config.TOPIC_RAW} ... (Ctrl+C to stop)")
    last_msg = None
    last_flush = last_report = last_data = time.monotonic()
    report_msgs = 0

    while state["running"]:
        msg = consumer.poll(1.0)
        now = time.monotonic()

        if msg is None:
            if pipeline.pending() or last_msg is not None:
                if now - last_flush >= config.FLUSH_EVERY_SECONDS:
                    if flush_and_commit(last_msg):
                        last_msg = None
                    last_flush = now
            if args.idle_exit and state["msgs"] and now - last_data > args.idle_exit:
                print("Idle, exiting.")
                break
        elif msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                print("[consumer] Kafka error:", msg.error())
        else:
            last_data = now
            state["msgs"] += 1
            report_msgs += 1
            last_msg = msg
            reading, err = parse_reading(msg.value())
            if reading is None:
                state["bad"] += 1
                dlq.produce(config.TOPIC_DLQ, json.dumps({
                    "error": err,
                    "offset": msg.offset(),
                    "raw": (msg.value() or b"")[:500].decode("utf-8", errors="replace"),
                }).encode("utf-8"))
                dlq.poll(0)
            else:
                while True:
                    try:
                        pipeline.process(reading)
                        break
                    except psycopg.Error as exc:       # only possible while rebuilding state at start-up
                        print(f"[consumer] database error at start-up, retrying in 2 s: {exc.__class__.__name__}")
                        if not state["running"]:
                            break
                        time.sleep(2)

            if pipeline.pending() >= config.FLUSH_EVERY_MSGS or now - last_flush >= config.FLUSH_EVERY_SECONDS:
                if flush_and_commit(last_msg):
                    last_msg = None
                last_flush = now

        if now - last_report >= 10 and report_msgs:
            scored = pipeline.stats["windows_scored"]
            avg_ms = pipeline.stats["score_ms"] / scored if scored else 0
            print(f"[consumer] {report_msgs / (now - last_report):6.1f} msg/s | total {state['msgs']:,} | "
                  f"bad {state['bad']} | windows scored {scored} | avg scoring {avg_ms:.0f} ms | "
                  f"late {builder.stats['late_dropped']} dup {builder.stats['duplicates']} sparse {builder.stats['sparse_windows']}")
            last_report, report_msgs = now, 0

    print("Shutting down: flushing ...")
    flush_and_commit(last_msg)
    consumer.close()
    sink.close()
    print(f"Done. messages={state['msgs']:,} bad={state['bad']} windows scored={pipeline.stats['windows_scored']}")


if __name__ == "__main__":
    main()
