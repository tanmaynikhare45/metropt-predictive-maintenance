"""Tiny models fitted on synthetic data, so the streaming tests need no saved models."""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from ml.features import build_rolling_features, build_window_features, window_feature_names
from ml.inference import load_models


def make_models(directory, raw, min_rows=5):
    feat = build_window_features(raw, min_rows=min_rows)
    names = window_feature_names()
    scaler = StandardScaler().fit(feat[names])
    X = pd.DataFrame(scaler.transform(feat[names]), index=feat.index, columns=names)
    iso = IsolationForest(n_estimators=50, random_state=0).fit(X)

    R = build_rolling_features(feat)
    y = (np.arange(len(R)) % 40 == 0).astype(int)
    rf = RandomForestClassifier(n_estimators=30, random_state=0).fit(R, y)

    joblib.dump(scaler, directory / "scaler.joblib")
    joblib.dump(iso, directory / "isolation_forest.joblib")
    joblib.dump(rf, directory / "failure_model.joblib")
    (directory / "anomaly_config.json").write_text(json.dumps({
        "features": names, "window": "10min", "seq_len": 12,
        "isolation_forest_threshold": float(np.quantile(-iso.score_samples(X), 0.95)),
        "lstm_threshold": 1.0, "min_consecutive_windows": 3}))
    (directory / "failure_config.json").write_text(json.dumps({
        "features": list(R.columns), "threshold": 0.3, "min_consecutive_windows": 3}))
    return load_models(directory, load_lstm=False)
