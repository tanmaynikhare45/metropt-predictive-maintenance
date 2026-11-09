"""AlertService against a real database (temporary schemas). Slack is replaced by a fake sender."""
import pandas as pd
import pytest

from alerts.service import AlertService
from alerts.store import AlertStore
from streaming.scoring import ScoreResult
from tests.db_helpers import alert_rows, alerts_ready, drop_schema, make_schema

pytestmark = pytest.mark.skipif(
    not alerts_ready(), reason="database not available, or the alerts migration (delivered columns) was not applied")

T0 = pd.Timestamp("2030-01-01 00:00")
THRESHOLDS = {"failure_threshold": 0.5, "iforest_threshold": 0.55}


def win(i, anomaly=False, risk=False):
    t = T0 + pd.Timedelta(minutes=10 * i)
    return ScoreResult(time=t, rows=[], summary={
        "time": t, "anomaly_alert": anomaly, "risk_alert": risk,
        "risk": 0.9 if risk else 0.1, "if_score": 0.7 if anomaly else 0.3, "top_features": {"TP2_mean": 3.0}})


# windows 0-2 clean | 3-6 anomaly only | 7-9 both | 10-11 anomaly only | 12-19 clean
SCRIPT = [(False, False)] * 3 + [(True, False)] * 4 + [(True, True)] * 3 + [(True, False)] * 2 + [(False, False)] * 8
WINDOWS = [win(i, a, r) for i, (a, r) in enumerate(SCRIPT)]
EXPECTED = [  # (window index, kind, severity)
    (3, "anomaly", "warning"),
    (7, "failure_risk", "critical"),
    (17, "recovered", "info"),
]


class FakeSender:
    def __init__(self, ok=True):
        self.ok, self.sent, self.on_result = ok, [], None

    def submit(self, alert_id, text):
        self.sent.append((alert_id, text))
        if self.on_result:
            self.on_result(alert_id, self.ok, "ok" if self.ok else "HTTP 500")
        return True

    def close(self, timeout=0):
        pass


def make_service(schema, ok=True, store=None):
    sender = FakeSender(ok)
    service = AlertService(store or AlertStore(schema=schema), sender, THRESHOLDS)
    sender.on_result = service._on_delivery
    return service, sender


def summarize(schema):
    return [(r[0].tz_convert(None) if hasattr(r[0], "tz_convert") else pd.Timestamp(r[0]).tz_localize(None), r[1], r[2])
            for r in alert_rows(schema)]


def expected_rows():
    return [(T0 + pd.Timedelta(minutes=10 * i), k, s) for i, k, s in EXPECTED]


@pytest.fixture(autouse=True)
def schemas():
    names = ["test_alerts_a", "test_alerts_b", "test_alerts_c", "test_alerts_d", "test_alerts_e"]
    for n in names:
        make_schema(n)
    yield
    for n in names:
        drop_schema(n)


def feed(service, windows):
    for w in windows:
        service(w)


def test_incident_lifecycle_is_stored_and_delivered():
    service, sender = make_service("test_alerts_a")
    feed(service, WINDOWS)
    assert summarize("test_alerts_a") == expected_rows()
    rows = alert_rows("test_alerts_a")
    assert all(r[3] for r in rows)                                  # delivered = True for all
    assert len(sender.sent) == 3
    assert "WARNING" in sender.sent[0][1] and "ESCALATED to CRITICAL" in sender.sent[1][1]
    assert "Back to normal" in sender.sent[2][1]
    assert service.stats["created"] == 3 and service.stats["delivered"] == 3


def test_replaying_the_same_windows_sends_nothing_again():
    first, _ = make_service("test_alerts_b")
    feed(first, WINDOWS)
    again, sender = make_service("test_alerts_b")
    feed(again, WINDOWS)
    assert len(sender.sent) == 0 and again.stats["duplicates"] == 3
    assert summarize("test_alerts_b") == expected_rows()


def test_restart_in_the_middle_of_an_incident_changes_nothing():
    a, _ = make_service("test_alerts_c")
    feed(a, WINDOWS[:9])                                            # crash during the critical phase
    b, sender_b = make_service("test_alerts_c")
    feed(b, WINDOWS[9:])                                            # new process continues
    assert summarize("test_alerts_c") == expected_rows()
    assert ["Back to normal" in t for _, t in sender_b.sent] == [True]   # only the recovery is new


def test_slack_outage_keeps_alerts_stored_and_they_are_resent_later():
    down, sender_down = make_service("test_alerts_d", ok=False)
    feed(down, WINDOWS)                                             # must not raise, stream goes on
    assert summarize("test_alerts_d") == expected_rows()
    assert not any(r[3] for r in alert_rows("test_alerts_d"))       # none delivered
    assert down.stats["delivery_failed"] == 3

    later, sender_later = make_service("test_alerts_d")
    later(win(20))                                                  # start-up: resends the recent undelivered ones
    assert len(sender_later.sent) == 3
    assert all(r[3] for r in alert_rows("test_alerts_d"))


class FlakyStore(AlertStore):
    """Fails the first N calls of one method, like a database that is briefly unavailable."""

    def __init__(self, schema, fail_history=0, fail_insert=0):
        super().__init__(schema=schema)
        self.fail_history, self.fail_insert = fail_history, fail_insert

    def history_before(self, *a, **k):
        if self.fail_history:
            self.fail_history -= 1
            raise ConnectionError("database down")
        return super().history_before(*a, **k)

    def insert(self, *a, **k):
        if self.fail_insert:
            self.fail_insert -= 1
            raise ConnectionError("database down")
        return super().insert(*a, **k)


def test_database_down_at_start_up_loses_no_alert():
    service, sender = make_service("test_alerts_e", store=FlakyStore("test_alerts_e", fail_history=2))
    feed(service, WINDOWS)                                          # first 2 windows cannot even bootstrap
    assert summarize("test_alerts_e") == expected_rows()
    assert service.stats["bootstrap_retries"] == 2


def test_database_down_when_saving_loses_no_alert():
    service, sender = make_service("test_alerts_e", store=FlakyStore("test_alerts_e", fail_insert=2))
    feed(service, WINDOWS)                                          # the start alert fails twice, then succeeds
    assert summarize("test_alerts_e") == expected_rows()
    assert service.stats["store_errors"] == 2 and len(sender.sent) == 3
