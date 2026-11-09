import pandas as pd

from alerts.rules import IncidentTracker, alert_kind, severity_of

T0 = pd.Timestamp("2020-06-05 10:00")


def t(i):
    return T0 + pd.Timedelta(minutes=10 * i)


def run(tracker, severities, start=0):
    """Feed one severity per 10-minute window; return [(window index, action, severity)]."""
    out = []
    for i, sev in enumerate(severities, start):
        for d in tracker.step(t(i), sev):
            out.append((i, d.action, d.severity))
    return out


def new(**kw):
    return IncidentTracker(recover_after=kw.get("recover_after", 3), reminder_hours=kw.get("reminder_hours", 6),
                           max_reminders=kw.get("max_reminders", 2))


def test_severity_and_kind_mapping():
    assert severity_of({}) is None
    assert severity_of({"anomaly_alert": True}) == "warning"
    assert severity_of({"risk_alert": True}) == "warning"
    assert severity_of({"anomaly_alert": True, "risk_alert": True}) == "critical"
    assert alert_kind({"anomaly_alert": True}) == "anomaly"
    assert alert_kind({"risk_alert": True}) == "failure_risk"
    assert alert_kind({"anomaly_alert": True, "risk_alert": True}) == "failure_risk"


def test_one_message_at_the_start_not_one_per_window():
    events = run(new(), [None] * 3 + ["warning"] * 20)
    assert events == [(3, "start", "warning")]


def test_escalation_is_sent_once_and_de_escalation_is_silent():
    events = run(new(), ["warning", "warning", "critical", "critical", "critical", "warning", "warning"])
    assert events == [(0, "start", "warning"), (2, "escalation", "critical")]


def test_reminder_after_six_hours_of_data_time_and_a_cap():
    events = run(new(max_reminders=2), ["warning"] * 200)          # 200 windows = 33 hours
    assert [(i, a) for i, a, _ in events] == [(0, "start"), (36, "reminder"), (72, "reminder")]


def test_recovery_needs_consecutive_clean_windows():
    events = run(new(recover_after=3), ["warning", None, None, "warning", None, None, None])
    # a flagged window in between resets the clean streak: no recovery after 2 clean windows
    assert events == [(0, "start", "warning"), (6, "recovered", "info")]


def test_a_new_incident_after_recovery_starts_again():
    events = run(new(recover_after=2), ["warning", None, None, "critical"])
    assert [(i, a) for i, a, _ in events] == [(0, "start"), (2, "recovered"), (3, "start")]


def test_recovered_decision_knows_when_the_incident_started():
    tracker = new(recover_after=2)
    decisions = []
    for i, sev in enumerate(["warning", "warning", None, None]):
        decisions += tracker.step(t(i), sev)
    assert decisions[-1].action == "recovered" and decisions[-1].since == t(0)


def test_restore_continues_an_open_incident_without_repeating_the_start():
    rows = [  # newest first, as the database returns them
        {"time": t(5).tz_localize("UTC"), "kind": "failure_risk", "severity": "critical"},
        {"time": t(0).tz_localize("UTC"), "kind": "anomaly", "severity": "warning"},
        {"time": t(-50), "kind": "recovered", "severity": "info"},
    ]
    tracker = new()
    tracker.restore(rows)
    assert tracker.in_incident and tracker.top_severity == "critical" and tracker.incident_start == t(0)
    assert run(tracker, ["critical"] * 5, start=6) == []                    # same incident, within 6 h: silent
    assert [a for _, a, _ in run(tracker, [None] * 3, start=11)] == ["recovered"]


def test_restore_after_recovery_means_no_open_incident():
    tracker = new()
    tracker.restore([{"time": t(0), "kind": "recovered", "severity": "info"}])
    assert not tracker.in_incident
    assert run(tracker, ["warning"], start=1) == [(1, "start", "warning")]


def test_restore_with_no_history_is_a_fresh_start():
    tracker = new()
    tracker.restore([])
    assert not tracker.in_incident
