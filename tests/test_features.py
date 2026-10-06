import numpy as np
import pandas as pd
import pytest

from ml.features import (ANALOG, DIGITAL, build_window_features, build_rolling_features,
                         make_sequences, window_feature_names)
from tests.helpers import make_raw


def test_window_features_shape_and_names():
    feat = build_window_features(make_raw(days=2))
    expected = window_feature_names()
    assert len(expected) == 7 * 4 + 8 == 36
    assert list(feat.columns) == expected + ["n_rows"]
    assert not feat.isna().any().any()
    assert len(feat) == 2 * 24 * 6          # one row per 10 minutes


def test_missing_sensor_column_is_rejected():
    raw = make_raw(days=1).drop(columns=["TP2"])
    with pytest.raises(ValueError):
        build_window_features(raw)


def test_machine_off_windows_are_dropped():
    raw = make_raw(days=2)
    raw = raw.drop(raw.loc["2020-03-01 06:00":"2020-03-01 08:00"].index)   # 2 h gap
    feat = build_window_features(raw)
    assert not ((feat.index >= "2020-03-01 06:00") & (feat.index < "2020-03-01 08:00")).any()


def test_rolling_features_shape():
    feat = build_window_features(make_raw(days=4))
    R = build_rolling_features(feat)
    assert R.shape[1] == 9 * 8                 # 9 base columns x (3 means + 3 stds + delta + dev)
    assert not R.isna().any().any()
    assert R.index.min() >= feat.index.min() + pd.Timedelta("11h")   # needs >= 50% of 24 h of history


def test_rolling_features_use_only_the_past():
    # Changing data AFTER a cutoff must not change features BEFORE the cutoff.
    raw = make_raw(days=5)
    cutoff = pd.Timestamp("2020-03-05 00:00")
    changed = raw.copy()
    changed.loc[cutoff:, :] = changed.loc[cutoff:, :] + 100.0

    R1 = build_rolling_features(build_window_features(raw, min_rows=5))
    R2 = build_rolling_features(build_window_features(changed, min_rows=5))
    before = R1.index[R1.index <= cutoff - pd.Timedelta("10min")]
    assert len(before) > 100
    np.testing.assert_allclose(R1.loc[before].values, R2.loc[before].values)


def test_make_sequences_skips_gaps():
    feat = build_window_features(make_raw(days=1))
    X = feat[window_feature_names()]
    seqs, ends = make_sequences(X, 12)
    assert seqs.shape == (len(X) - 11, 12, 36)
    gapped = X.drop(X.index[50:60])
    seqs2, ends2 = make_sequences(gapped, 12)
    assert len(seqs2) < len(gapped) - 11        # sequences across the gap are skipped
