"""Load the saved models and score new data. Used by the streaming consumer and the API.

    models = load_models()
    feat   = build_window_features(raw_rows)
    anomaly = predict_anomaly(models, feat)
    risk    = predict_failure_risk(models, build_rolling_features(feat))
    fc      = forecast_sensor(models, series_of_10min_means, "TP2")
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

from .features import WINDOW, make_sequences

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "models"


@dataclass
class Models:
    scaler: Any = None
    iso: Any = None
    lstm: Any = None
    lstm_meta: Optional[dict] = None
    failure: Any = None
    anomaly_cfg: Optional[dict] = None
    failure_cfg: Optional[dict] = None
    forecast_cfg: Optional[dict] = None


def _read_json(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def _load_lstm(path):
    import torch                      # imported lazily: the API can run without torch
    from .lstm_ae import LSTMAE
    ckpt = torch.load(path, map_location="cpu")
    net = LSTMAE(ckpt["n_features"], ckpt["hidden"], ckpt["latent"])
    net.load_state_dict(ckpt["state_dict"])
    net.eval()
    return net, {"seq_len": ckpt["seq_len"]}


def load_models(model_dir=None, load_lstm=True):
    """Load whatever artifacts exist in model_dir. Missing files stay None."""
    d = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    m = Models()
    if (d / "scaler.joblib").exists():
        m.scaler = joblib.load(d / "scaler.joblib")
    if (d / "isolation_forest.joblib").exists():
        m.iso = joblib.load(d / "isolation_forest.joblib")
    if (d / "failure_model.joblib").exists():
        m.failure = joblib.load(d / "failure_model.joblib")
    m.anomaly_cfg = _read_json(d / "anomaly_config.json")
    m.failure_cfg = _read_json(d / "failure_config.json")
    m.forecast_cfg = _read_json(d / "forecast_config.json")
    if load_lstm and (d / "lstm_autoencoder.pt").exists():
        m.lstm, m.lstm_meta = _load_lstm(d / "lstm_autoencoder.pt")
    return m


def sustained(flag, n):
    """True only where `flag` has been True for n consecutive windows."""
    return flag.astype(int).rolling(n).min().fillna(0).astype(bool)


def _scaled(models, feat):
    if models.scaler is None or models.anomaly_cfg is None:
        raise RuntimeError("scaler / anomaly_config.json not loaded")
    cols = models.anomaly_cfg["features"]
    return pd.DataFrame(models.scaler.transform(feat[cols]), index=feat.index, columns=cols)


def predict_anomaly(models, feat):
    """Anomaly scores for window features (output of build_window_features).

    Returns a DataFrame with: if_score, if_flag, lstm_score, lstm_flag, alert.
    'alert' is True after min_consecutive_windows flagged windows in a row.
    The LSTM columns are NaN where there is no full sequence (or the LSTM is not loaded).
    """
    cfg = models.anomaly_cfg
    X = _scaled(models, feat)
    out = pd.DataFrame(index=feat.index)

    out["if_score"] = np.nan
    if models.iso is not None:
        out["if_score"] = -models.iso.score_samples(X)
    out["if_flag"] = out["if_score"] > cfg["isolation_forest_threshold"]

    out["lstm_score"] = np.nan
    if models.lstm is not None:
        import torch
        seqs, end_times = make_sequences(X, models.lstm_meta["seq_len"], cfg.get("window", WINDOW))
        if len(seqs):
            with torch.no_grad():
                xb = torch.from_numpy(seqs)
                err = ((models.lstm(xb) - xb) ** 2).mean(dim=(1, 2)).numpy()
            out.loc[end_times, "lstm_score"] = err
    out["lstm_flag"] = out["lstm_score"] > cfg["lstm_threshold"]

    flag = out["lstm_flag"] if out["lstm_score"].notna().any() else out["if_flag"]
    out["alert"] = sustained(flag, cfg["min_consecutive_windows"])
    return out


def top_contributors(models, feat, k=5):
    """The k features that deviate most from normal (mean absolute z-score over the given rows).

    These become the "likely cause" in alerts. Pass the last few windows.
    """
    X = _scaled(models, feat)
    return X.abs().mean().sort_values(ascending=False).head(k).round(2)


def predict_failure_risk(models, rolling_feat):
    """Failure risk (0 to 1) for rolling features (output of build_rolling_features).

    Returns a DataFrame with: risk, flag, alert.
    """
    if models.failure is None or models.failure_cfg is None:
        raise RuntimeError("failure_model.joblib / failure_config.json not loaded")
    cfg = models.failure_cfg
    X = rolling_feat[cfg["features"]]
    out = pd.DataFrame(index=rolling_feat.index)
    out["risk"] = models.failure.predict_proba(X)[:, 1]
    out["flag"] = out["risk"] > cfg["threshold"]
    out["alert"] = sustained(out["flag"], cfg.get("min_consecutive_windows", 3))
    return out


def forecast(hist, steps=36, method="prophet_level", interval=0.9, decay=0.95, window=WINDOW):
    """Forecast a sensor from a Series of 10-minute means (no NaN, newest last).

    method: 'naive', 'prophet' or 'prophet_level'.
    Returns a DataFrame indexed by time with columns yhat, lower, upper.
    Prophet is refitted on every call (a few seconds): cache the result in the API.
    """
    hist = hist.dropna()
    step = pd.Timedelta(window)
    future_idx = pd.date_range(hist.index[-1] + step, periods=steps, freq=window)

    if method == "naive":
        sigma = float(hist.diff().dropna().std())              # random-walk band
        k = np.arange(1, steps + 1)
        half = 1.645 * sigma * np.sqrt(k)
        last = float(hist.iloc[-1])
        return pd.DataFrame({"yhat": last, "lower": last - half, "upper": last + half}, index=future_idx)

    import logging
    from prophet import Prophet
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    logging.getLogger("prophet").setLevel(logging.ERROR)

    d = pd.DataFrame({"ds": hist.index, "y": hist.values})
    m = Prophet(interval_width=interval, daily_seasonality=True, weekly_seasonality=True,
                yearly_seasonality=False, changepoint_prior_scale=0.05)
    m.fit(d)
    fc = m.predict(pd.DataFrame({"ds": future_idx}))
    out = pd.DataFrame({"yhat": fc["yhat"].values, "lower": fc["yhat_lower"].values,
                        "upper": fc["yhat_upper"].values}, index=future_idx)
    if method == "prophet_level":
        fitted_tail = m.predict(d[["ds"]].tail(6))["yhat"].values
        offset = float(np.mean(d["y"].tail(6).values - fitted_tail))
        out = out + offset * decay ** np.arange(1, steps + 1)[:, None]
    return out


def forecast_sensor(models, hist, sensor):
    """Forecast one sensor with the method chosen in notebook 04 (forecast_config.json)."""
    cfg = models.forecast_cfg or {}
    method = cfg.get("best_method", {}).get(sensor, "prophet_level")
    if method == "seasonal_naive":
        method = "naive"                  # not implemented for live use
    if method == "nbeats":
        method = "prophet_level"          # not available in the API
    hist = hist.iloc[-cfg.get("history_days", 14) * 144:]
    return forecast(hist, steps=cfg.get("steps", 36), method=method,
                    interval=cfg.get("interval_width", 0.9), decay=cfg.get("level_decay", 0.95))
