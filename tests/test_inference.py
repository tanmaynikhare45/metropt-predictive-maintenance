import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from ml.features import build_window_features, build_rolling_features, window_feature_names
from ml.inference import (forecast, load_models, predict_anomaly, predict_failure_risk,
                          top_contributors)
from tests.helpers import make_raw


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    d = tmp_path_factory.mktemp("models")
    feat = build_window_features(make_raw(days=6))
    names = window_feature_names()
    scaler = StandardScaler().fit(feat[names])
    X = pd.DataFrame(scaler.transform(feat[names]), index=feat.index, columns=names)
    iso = IsolationForest(n_estimators=50, random_state=0).fit(X)
    scores = -iso.score_samples(X)

    R = build_rolling_features(feat)
    y = (np.arange(len(R)) % 50 == 0).astype(int)
    rf = RandomForestClassifier(n_estimators=30, random_state=0).fit(R, y)

    joblib.dump(scaler, d / "scaler.joblib")
    joblib.dump(iso, d / "isolation_forest.joblib")
    joblib.dump(rf, d / "failure_model.joblib")
    (d / "anomaly_config.json").write_text(json.dumps({
        "features": names, "window": "10min", "seq_len": 12,
        "isolation_forest_threshold": float(np.quantile(scores, 0.99)),
        "lstm_threshold": 1.0, "min_consecutive_windows": 3}))
    (d / "failure_config.json").write_text(json.dumps({
        "features": list(R.columns), "threshold": 0.5, "min_consecutive_windows": 3}))
    return load_models(d, load_lstm=False), feat, R


def test_predict_anomaly(setup):
    models, feat, _ = setup
    out = predict_anomaly(models, feat)
    assert list(out.columns) == ["if_score", "if_flag", "lstm_score", "lstm_flag", "alert"]
    assert len(out) == len(feat)
    assert out["if_score"].notna().all()
    assert out["lstm_score"].isna().all()        # LSTM not loaded in this test


def test_predict_failure_risk(setup):
    models, _, R = setup
    out = predict_failure_risk(models, R)
    assert len(out) == len(R)
    assert out["risk"].between(0, 1).all()


def test_failure_risk_needs_the_right_columns(setup):
    models, _, R = setup
    with pytest.raises(KeyError):
        predict_failure_risk(models, R.drop(columns=[R.columns[0]]))


def test_top_contributors(setup):
    models, feat, _ = setup
    tc = top_contributors(models, feat.tail(6), k=5)
    assert len(tc) == 5
    assert tc.is_monotonic_decreasing


def test_naive_forecast_shape():
    hist = pd.Series(np.random.default_rng(0).normal(5, 0.1, 300),
                     index=pd.date_range("2020-03-01", periods=300, freq="10min"))
    fc = forecast(hist, steps=36, method="naive")
    assert list(fc.columns) == ["yhat", "lower", "upper"]
    assert len(fc) == 36
    assert fc.index[0] == hist.index[-1] + pd.Timedelta("10min")
    assert (fc["lower"] <= fc["yhat"]).all() and (fc["yhat"] <= fc["upper"]).all()


def test_prophet_forecast_shape():
    pytest.importorskip("prophet")
    hist = pd.Series(np.random.default_rng(0).normal(5, 0.1, 1000),
                     index=pd.date_range("2020-03-01", periods=1000, freq="10min"))
    fc = forecast(hist, steps=12, method="prophet_level")
    assert len(fc) == 12
    assert fc.notna().all().all()
