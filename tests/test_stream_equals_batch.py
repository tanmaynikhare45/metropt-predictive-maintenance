"""The most important streaming test: feeding readings one by one must give EXACTLY the same
features and scores as the batch code used for training. If this fails, the live system is
silently scoring different numbers than the models were trained on."""
import numpy as np
import pandas as pd

from ml.features import SENSORS, build_rolling_features, build_window_features
from ml.inference import predict_anomaly, predict_failure_risk
from streaming.scoring import Scorer
from streaming.windowing import WindowBuilder
from tests.helpers import make_raw
from tests.model_helpers import make_models

MIN_ROWS = 5


def stream_windows(raw):
    b = WindowBuilder(min_rows=MIN_ROWS)
    out = []
    for ts, vals in zip(raw.index, raw[SENSORS].to_numpy()):
        out += b.add(ts, tuple(vals))
    out += b.close_all()
    return out


def test_streamed_window_features_equal_batch_features():
    raw = make_raw(days=3)
    batch = build_window_features(raw, min_rows=MIN_ROWS)
    streamed = pd.concat(stream_windows(raw))
    assert len(streamed) == len(batch)
    pd.testing.assert_frame_equal(streamed, batch, check_dtype=False, check_freq=False, check_names=False)


def test_streamed_window_features_equal_batch_with_machine_off_gap():
    raw = make_raw(days=3)
    raw = raw.drop(raw.loc["2020-03-01 20:00":"2020-03-02 03:00"].index)
    batch = build_window_features(raw, min_rows=MIN_ROWS)
    streamed = pd.concat(stream_windows(raw))
    pd.testing.assert_frame_equal(streamed, batch, check_dtype=False, check_freq=False, check_names=False)


def test_streamed_scores_equal_batch_scores(tmp_path):
    raw = make_raw(days=5)
    models = make_models(tmp_path, raw, min_rows=MIN_ROWS)

    feat_b = build_window_features(raw, min_rows=MIN_ROWS)
    an_b = predict_anomaly(models, feat_b)
    risk_b = predict_failure_risk(models, build_rolling_features(feat_b))

    scorer = Scorer(models)
    got_if, got_risk = {}, {}
    for feat in stream_windows(raw):
        res = scorer.score(feat)
        for t, model, score, flag in res.rows:
            if model == "iforest":
                got_if[pd.Timestamp(t)] = score
            elif model == "failure_risk":
                got_risk[pd.Timestamp(t)] = score

    assert len(got_if) == len(feat_b)
    for t, s in got_if.items():
        assert np.isclose(s, an_b.loc[t, "if_score"])

    common = [t for t in got_risk if t in risk_b.index]
    assert len(common) > 200                                  # risk exists once 12+ h of history is there
    for t in common:
        assert np.isclose(got_risk[t], risk_b.loc[t, "risk"])
