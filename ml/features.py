"""Feature engineering shared by the notebooks, the streaming consumer and the API.

Keep ALL feature logic here. If training and serving compute features differently
("training/serving skew"), the models silently get worse in production.
"""
import numpy as np
import pandas as pd

ANALOG = ["TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current"]
DIGITAL = ["COMP", "DV_eletric", "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses"]
SENSORS = ANALOG + DIGITAL

WINDOW = "10min"

# Columns the rolling (failure-prediction) features are built from.
BASE = [f"{c}_mean" for c in ANALOG] + ["Motor_current_std", "COMP_mean"]
ROLLING_HOURS = (1, 6, 24)
MIN_PERIODS = {1: 3, 6: 18, 24: 72}   # need at least ~50% of the windows in each span


def window_feature_names():
    """The 36 per-window features, in the order the anomaly models expect."""
    names = []
    for c in ANALOG:
        names += [f"{c}_{s}" for s in ("mean", "std", "min", "max")]
    names += [f"{c}_mean" for c in DIGITAL]
    return names


def build_window_features(raw, window=WINDOW, min_rows=None):
    """Aggregate raw sensor rows into fixed windows (default 10 minutes).

    raw      DataFrame with a DatetimeIndex and the 15 sensor columns.
    min_rows windows with fewer readings are dropped (machine off / data gap).
             If None, half of the median readings per window is used.
    Returns a DataFrame with the 36 window features plus the column 'n_rows'.
    """
    if not isinstance(raw.index, pd.DatetimeIndex):
        raise ValueError("raw must have a DatetimeIndex")
    missing = [c for c in SENSORS if c not in raw.columns]
    if missing:
        raise ValueError(f"missing sensor columns: {missing}")

    agg = {c: ["mean", "std", "min", "max"] for c in ANALOG}
    agg.update({c: ["mean"] for c in DIGITAL})
    feat = raw[SENSORS].resample(window).agg(agg)
    feat.columns = [f"{c}_{s}" for c, s in feat.columns]

    n_rows = raw[ANALOG[0]].resample(window).count()
    feat["n_rows"] = n_rows
    if min_rows is None:
        typical = n_rows[n_rows > 0].median()
        min_rows = 0.5 * typical
    feat = feat[feat["n_rows"] >= min_rows].fillna(0)
    return feat


def build_rolling_features(feat, window=WINDOW, base=BASE, drop_incomplete=True):
    """Past-only rolling features for failure prediction (72 features by default).

    Every feature at time t uses only windows up to and including t. Windows are put on
    a complete grid first, so "6 hours ago" always means exactly 36 windows.
    Rows without enough history (at least half of each span, and a window exactly 6 h earlier)
    are dropped when drop_incomplete is True.
    """
    steps_6h = int(pd.Timedelta("6h") / pd.Timedelta(window))
    grid = pd.date_range(feat.index.min(), feat.index.max(), freq=window)
    base_full = feat[base].reindex(grid)

    means, parts = {}, []
    for h in ROLLING_HOURS:
        r = base_full.rolling(f"{h}h", min_periods=MIN_PERIODS[h])
        means[h] = r.mean()
        parts.append(means[h].add_suffix(f"__mean{h}h"))
        parts.append(r.std().add_suffix(f"__std{h}h"))
    parts.append((base_full - base_full.shift(steps_6h)).add_suffix("__delta6h"))
    parts.append((means[1] - means[24]).add_suffix("__dev1h_vs_24h"))

    out = pd.concat(parts, axis=1).reindex(feat.index)
    if drop_incomplete:
        out = out.dropna()
    return out


def make_sequences(X, seq_len, window=WINDOW):
    """Sliding sequences of consecutive windows for the LSTM autoencoder.

    Sequences that span a time gap are skipped.
    Returns (array of shape [n, seq_len, n_features], DatetimeIndex of each sequence's last window).
    """
    vals = X.values.astype(np.float32)
    ts = X.index.values
    win = pd.Timedelta(window).to_timedelta64()
    n = len(vals) - seq_len + 1
    if n <= 0:
        return np.empty((0, seq_len, vals.shape[1]), dtype=np.float32), pd.DatetimeIndex([])
    starts = np.arange(n)
    contiguous = (ts[seq_len - 1:] - ts[:n]) == (seq_len - 1) * win
    starts = starts[contiguous]
    if len(starts) == 0:
        return np.empty((0, seq_len, vals.shape[1]), dtype=np.float32), pd.DatetimeIndex([])
    seqs = np.stack([vals[i:i + seq_len] for i in starts])
    return seqs, pd.DatetimeIndex(ts[starts + seq_len - 1])
