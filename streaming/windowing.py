"""Collect readings into 10-minute windows (pure logic, no Kafka, no database).

A window is CLOSED when a reading from a LATER window arrives (event time, not wall-clock
time), so the replay speed never changes the results. A closed window is turned into
features by the same ml.features code that the training notebooks use.
"""
from collections import Counter

import numpy as np
import pandas as pd

from ml.features import SENSORS, WINDOW, build_window_features


class WindowBuilder:
    def __init__(self, min_rows, window=WINDOW):
        self.window = pd.Timedelta(window)
        self.window_str = window
        self.min_rows = min_rows
        self.open = {}                 # window start -> {reading time: tuple of 15 values}
        self.last_closed = None        # newest window start that was closed
        self.stats = Counter()

    def _floor(self, t):
        return pd.Timestamp(t).floor(self.window)

    def add(self, t, values):
        """Add one reading. Returns a list of feature DataFrames (one row each) for windows that just closed."""
        t = pd.Timestamp(t)
        ws = self._floor(t)
        if self.last_closed is not None and ws <= self.last_closed:
            self.stats["late_dropped"] += 1          # belongs to a window that is already closed
            return []

        closed = []
        for old in sorted(k for k in self.open if k < ws):
            feat = self._close(old)
            if feat is not None:
                closed.append(feat)

        bucket = self.open.setdefault(ws, {})
        if t in bucket:
            self.stats["duplicates"] += 1            # same timestamp again (e.g. replay): ignore
        else:
            bucket[t] = tuple(values)
        return closed

    def _close(self, ws):
        rows = self.open.pop(ws)
        self.last_closed = ws if self.last_closed is None else max(self.last_closed, ws)
        if len(rows) < self.min_rows:
            self.stats["sparse_windows"] += 1        # machine off / data gap
            return None
        times = sorted(rows)
        df = pd.DataFrame(np.array([rows[t] for t in times], dtype=float),
                          index=pd.DatetimeIndex(times), columns=SENSORS)
        feat = build_window_features(df, window=self.window_str, min_rows=self.min_rows)
        if len(feat) == 0:
            return None
        self.stats["windows_closed"] += 1
        return feat

    def close_all(self):
        """Close every open window (end of a finite stream, used in tests)."""
        out = []
        for ws in sorted(self.open):
            feat = self._close(ws)
            if feat is not None:
                out.append(feat)
        return out
