import numpy as np
import pandas as pd
from ml.features import ANALOG, DIGITAL


def make_raw(days=3, freq="60s", seed=0, start="2020-03-01"):
    """Synthetic raw sensor data with the same columns as MetroPT-3."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=int(days * 24 * 3600 / pd.Timedelta(freq).total_seconds()), freq=freq)
    df = pd.DataFrame(index=idx)
    cyc = np.sin(np.arange(len(idx)) / 30.0)
    for j, c in enumerate(ANALOG):
        df[c] = 5 + j + cyc * 0.5 + rng.normal(0, 0.1, len(idx))
    for c in DIGITAL:
        df[c] = (rng.random(len(idx)) > 0.5).astype(float)
    df.index.name = "timestamp"
    return df
