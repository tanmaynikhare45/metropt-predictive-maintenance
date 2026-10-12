"""The Kafka-free heart of the consumer: reading -> raw buffer + windows -> scores -> prediction buffer.

The consumer (consumer.py) only adds Kafka around this class, so everything here is testable
without Kafka.
"""
import time
from collections import Counter

import pandas as pd

from ml.features import build_window_features

from . import config


class Pipeline:
    def __init__(self, sink, builder, scorer, bootstrap_hours=config.BOOTSTRAP_HOURS):
        self.sink = sink
        self.builder = builder
        self.scorer = scorer
        self.bootstrap_hours = bootstrap_hours
        self.on_scored = []                # hooks: callable(ScoreResult). Phase 6 adds Slack alerts here.
        self.stats = Counter()
        self._bootstrapped = False

    def _score_window(self, feat):
        """Score one closed window and buffer its predictions. Returns the ScoreResult or None on error."""
        started = time.perf_counter()
        try:
            res = self.scorer.score(feat)
        except Exception as exc:                       # one bad window must not stop the stream
            self.stats["score_errors"] += 1
            print(f"[pipeline] scoring failed for window {feat.index[0]}: {exc!r}")
            return None
        self.stats["score_ms"] += (time.perf_counter() - started) * 1000
        self.stats["windows_scored"] += 1
        self.sink.add_predictions(res.rows)
        for hook in self.on_scored:
            hook(res)
        return res

    def _bootstrap(self, first_time):
        """Rebuild state after a (re)start from the raw readings already in the database.

        - completed windows before the first message become the scoring history
        - completed windows that have NO stored score yet are scored now. Without this, the
          window that was still open when the process died would be lost: it only closes when
          the next reading arrives, and that reading had not been processed yet.
        - readings of the CURRENT window that were stored before a crash are put back into the builder
        """
        t0 = pd.Timestamp(first_time).floor(self.builder.window)
        raw = self.sink.fetch_raw(t0 - pd.Timedelta(hours=self.bootstrap_hours), first_time)
        last_scored = self.sink.last_prediction_time()
        pending = []
        if len(raw):
            completed = raw[raw.index < t0]
            if len(completed):
                feat = build_window_features(completed, window=self.builder.window_str, min_rows=self.builder.min_rows)
                if len(feat):
                    if last_scored is None:
                        self.scorer.seed_history(feat.iloc[:0])
                        pending = [feat.iloc[[i]] for i in range(len(feat))]
                    else:
                        self.scorer.seed_history(feat[feat.index <= last_scored])
                        pending = [feat.iloc[[i]] for i in range(len(feat)) if feat.index[i] > last_scored]
            partial = raw[raw.index >= t0]
            for ts, vals in zip(partial.index, partial.to_numpy()):
                self.builder.add(ts, tuple(vals))
        for feat_row in pending:
            self._score_window(feat_row)
        self._bootstrapped = True
        self.stats["bootstrap_rows"] = len(raw)
        self.stats["bootstrap_rescored"] = len(pending)

    def process(self, reading):
        """Handle one validated Reading. May raise a database error (only during bootstrap)."""
        if not self._bootstrapped:
            self._bootstrap(reading.time)
        row = reading.to_row()
        self.sink.add_raw(reading.time, row)
        self.stats["readings"] += 1

        results = []
        for feat in self.builder.add(reading.time, row):
            res = self._score_window(feat)
            if res is not None:
                results.append(res)
        return results

    def pending(self):
        return self.sink.pending()

    def flush(self):
        return self.sink.flush()
