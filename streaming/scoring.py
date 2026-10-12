"""Score each closed window with the saved models, keeping a short history in memory."""
from dataclasses import dataclass, field

import pandas as pd

from ml.features import build_rolling_features
from ml.inference import predict_anomaly, predict_failure_risk, top_contributors

from . import config


@dataclass
class ScoreResult:
    time: pd.Timestamp
    rows: list = field(default_factory=list)        # (time, model, score, flag) ready for the predictions table
    summary: dict = field(default_factory=dict)     # everything an alert needs (Phase 6 hook)


class Scorer:
    def __init__(self, models, history_windows=config.HISTORY_WINDOWS):
        if models.anomaly_cfg is None:
            raise RuntimeError("anomaly models not loaded (run notebook 02 first)")
        self.models = models
        self.max_hist = history_windows
        self.history = pd.DataFrame()
        self.min_consec = models.anomaly_cfg["min_consecutive_windows"]
        seq_len = (models.lstm_meta or {}).get("seq_len", 12)
        self.tail_n = max(seq_len, self.min_consec) + 2

    def seed_history(self, feat):
        """Load already-computed window features (used at start-up)."""
        self.history = feat.tail(self.max_hist).copy()

    def score(self, feat):
        t = feat.index[0]
        h = pd.concat([self.history, feat])
        h = h[~h.index.duplicated(keep="last")].sort_index().tail(self.max_hist)
        self.history = h

        rows, summary = [], {"time": t}
        py_t = t.to_pydatetime()

        an = predict_anomaly(self.models, h.tail(self.tail_n)).loc[t]
        rows.append((py_t, "iforest", float(an["if_score"]), bool(an["if_flag"])))
        summary.update(if_score=float(an["if_score"]), if_flag=bool(an["if_flag"]), anomaly_alert=bool(an["alert"]))
        if pd.notna(an["lstm_score"]):
            rows.append((py_t, "lstm_ae", float(an["lstm_score"]), bool(an["lstm_flag"])))
            summary.update(lstm_score=float(an["lstm_score"]), lstm_flag=bool(an["lstm_flag"]))

        if self.models.failure is not None:
            rolling = build_rolling_features(h, drop_incomplete=False).tail(self.min_consec).dropna()
            if t in rolling.index:                       # needs enough history; otherwise no risk yet
                rf = predict_failure_risk(self.models, rolling).loc[t]
                rows.append((py_t, "failure_risk", float(rf["risk"]), bool(rf["flag"])))
                summary.update(risk=float(rf["risk"]), risk_flag=bool(rf["flag"]), risk_alert=bool(rf["alert"]))

        summary["top_features"] = top_contributors(self.models, h.tail(6), k=5).to_dict()
        return ScoreResult(time=t, rows=rows, summary=summary)
