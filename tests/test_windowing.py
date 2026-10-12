import numpy as np
import pandas as pd

from ml.features import SENSORS, window_feature_names
from streaming.windowing import WindowBuilder

VALS = tuple(float(i) for i in range(15))


def feed(builder, times):
    out = []
    for t in times:
        out += builder.add(pd.Timestamp(t), VALS)
    return out


def minutes(start, n):
    return pd.date_range(start, periods=n, freq="60s")


def test_window_closes_only_when_a_later_window_arrives():
    b = WindowBuilder(min_rows=5)
    closed = feed(b, minutes("2020-06-05 08:00", 10))        # exactly the 08:00 window
    assert closed == []                                      # nothing later has arrived yet
    closed = b.add(pd.Timestamp("2020-06-05 08:10:00"), VALS)
    assert len(closed) == 1
    assert closed[0].index[0] == pd.Timestamp("2020-06-05 08:00")
    assert list(closed[0].columns) == window_feature_names() + ["n_rows"]
    assert closed[0]["n_rows"].iloc[0] == 10


def test_sparse_windows_are_dropped():
    b = WindowBuilder(min_rows=5)
    feed(b, minutes("2020-06-05 08:00", 3))                  # only 3 readings: machine off
    closed = b.add(pd.Timestamp("2020-06-05 08:30:00"), VALS)
    assert closed == []
    assert b.stats["sparse_windows"] == 1


def test_duplicates_are_ignored():
    b = WindowBuilder(min_rows=5)
    times = list(minutes("2020-06-05 08:00", 10))
    feed(b, times + times)                                   # same readings twice
    closed = b.add(pd.Timestamp("2020-06-05 08:10:00"), VALS)
    assert closed[0]["n_rows"].iloc[0] == 10
    assert b.stats["duplicates"] == 10


def test_late_readings_are_dropped():
    b = WindowBuilder(min_rows=5)
    feed(b, minutes("2020-06-05 08:00", 10))
    b.add(pd.Timestamp("2020-06-05 08:10:00"), VALS)         # closes the 08:00 window
    assert b.add(pd.Timestamp("2020-06-05 08:05:30"), VALS) == []
    assert b.stats["late_dropped"] == 1


def test_gap_closes_the_old_window():
    b = WindowBuilder(min_rows=5)
    feed(b, minutes("2020-06-05 08:00", 10))
    closed = b.add(pd.Timestamp("2020-06-05 14:00:00"), VALS)   # machine was off for hours
    assert len(closed) == 1 and closed[0].index[0] == pd.Timestamp("2020-06-05 08:00")


def test_close_all_flushes_the_open_window():
    b = WindowBuilder(min_rows=5)
    feed(b, minutes("2020-06-05 08:00", 10))
    out = b.close_all()
    assert len(out) == 1 and len(b.open) == 0
