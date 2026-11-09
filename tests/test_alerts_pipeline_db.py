"""End to end without Kafka: readings -> pipeline -> scoring -> alert service -> database."""
import pandas as pd
import pytest

from alerts.service import AlertService
from alerts.store import AlertStore
from ml.features import ANALOG, SENSORS
from streaming.pipeline import Pipeline
from streaming.schema import SENSOR_FIELDS, Reading
from streaming.scoring import Scorer
from streaming.sink import Sink
from streaming.windowing import WindowBuilder
from tests.db_helpers import alert_rows, alerts_ready, drop_schema, make_schema
from tests.helpers import make_raw
from tests.model_helpers import make_models

pytestmark = pytest.mark.skipif(not alerts_ready(), reason="database or alerts migration not available")

SCHEMA = "test_alerts_pipe"


class Capture:
    def __init__(self):
        self.sent, self.on_result = [], None

    def submit(self, alert_id, text):
        self.sent.append(text)
        if self.on_result:
            self.on_result(alert_id, True, "ok")
        return True

    def close(self, timeout=0):
        pass


def test_a_planted_fault_creates_one_incident_and_one_recovery(tmp_path):
    clean = make_raw(days=3, start="2030-01-01")
    # the models only know normal behaviour; the random-label risk model of the test fixture is silenced (threshold 0.99)
    models = make_models(tmp_path, clean, min_rows=5, failure_threshold=0.99)
    raw = clean.copy()
    fault = raw.loc["2030-01-02 12:00":"2030-01-02 17:59"].index    # 6 hours with a big shift in all analog sensors
    raw.loc[fault, ANALOG] += 30.0

    make_schema(SCHEMA, with_readings=True)
    try:
        sender = Capture()
        service = AlertService(AlertStore(schema=SCHEMA), sender, {"iforest_threshold": 0.5, "failure_threshold": 0.3})
        sender.on_result = service._on_delivery
        pipe = Pipeline(Sink(schema=SCHEMA), WindowBuilder(min_rows=5), Scorer(models))
        pipe.on_scored.append(service)

        for ts, vals in zip(raw.index, raw[SENSORS].to_numpy().tolist()):
            pipe.process(Reading.model_validate({"time": ts.isoformat(), **dict(zip(SENSOR_FIELDS, vals))}))
        pipe.flush()

        rows = alert_rows(SCHEMA)
        kinds = [r[1] for r in rows]
        assert 2 <= len(rows) <= 4, kinds                           # one incident, not one message per window
        first, last = rows[0], rows[-1]
        t_first = pd.Timestamp(first[0]).tz_convert(None)
        assert pd.Timestamp("2030-01-02 12:20") <= t_first <= pd.Timestamp("2030-01-02 12:40")   # after 3 flagged windows
        assert first[2] in ("warning", "critical")
        assert last[1] == "recovered"
        assert pd.Timestamp("2030-01-02 18:00") <= pd.Timestamp(last[0]).tz_convert(None) <= pd.Timestamp("2030-01-02 19:30")
        assert any("TP2" in m or "Oil_temperature" in m for m in sender.sent)       # the cause is named
        assert all(r[3] for r in rows)                                              # all delivered
    finally:
        drop_schema(SCHEMA)
