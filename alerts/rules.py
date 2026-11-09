"""When does an incident start, escalate, repeat and end? Pure logic: no Slack, no database.

The scorer already reports `anomaly_alert` / `risk_alert`: true after 3 flagged 10-minute
windows in a row. This module turns that stream into a small number of messages.

    start       first alert of an incident
    escalation  warning -> critical (both models flag)
    reminder    the incident is still going after REMINDER_HOURS (data time)
    recovered   RECOVER_AFTER clean windows in a row
"""
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

RANK = {"warning": 1, "critical": 2}


def _naive(ts):
    ts = pd.Timestamp(ts)
    return ts.tz_convert(None) if ts.tzinfo is not None else ts


def severity_of(summary) -> Optional[str]:
    """warning: one model flags (sustained). critical: both flag."""
    anomaly = bool(summary.get("anomaly_alert"))
    risk = bool(summary.get("risk_alert"))
    if anomaly and risk:
        return "critical"
    if anomaly or risk:
        return "warning"
    return None


def alert_kind(summary) -> str:
    """Value for the alerts.kind column."""
    return "failure_risk" if summary.get("risk_alert") else "anomaly"


@dataclass
class Decision:
    action: str                       # start | escalation | reminder | recovered
    severity: str                     # warning | critical | info
    time: pd.Timestamp
    since: Optional[pd.Timestamp] = None   # when the incident started


class IncidentTracker:
    def __init__(self, recover_after=6, reminder_hours=6.0, max_reminders=4):
        self.recover_after = recover_after
        self.reminder = pd.Timedelta(hours=reminder_hours)
        self.max_reminders = max_reminders
        self._reset()

    def _reset(self):
        self.in_incident = False
        self.top_severity = None
        self.last_alert_time = None
        self.incident_start = None
        self.clean_streak = 0
        self.reminders_sent = 0

    def restore(self, rows):
        """Rebuild the state from stored alerts (newest first), so a restart does not repeat messages.

        rows: dicts with time, kind, severity. Only alerts BEFORE the first new window may be passed.
        """
        incident = []
        for r in rows:
            if r["kind"] == "recovered":
                break
            incident.append(r)
        self._reset()
        if not incident:
            return
        self.in_incident = True
        self.last_alert_time = _naive(incident[0]["time"])
        self.incident_start = _naive(incident[-1]["time"])
        self.top_severity = max((r["severity"] for r in incident), key=lambda s: RANK.get(s, 0))
        self.reminders_sent = max(0, len(incident) - 1)       # approximation: every later message counts

    def step(self, time, severity: Optional[str]) -> List[Decision]:
        """Feed one scored window (in time order). Returns the messages to send (usually none)."""
        t = _naive(time)

        if severity is None:
            if not self.in_incident:
                return []
            self.clean_streak += 1
            if self.clean_streak >= self.recover_after:
                since = self.incident_start
                self._reset()
                return [Decision("recovered", "info", t, since)]
            return []

        self.clean_streak = 0
        if not self.in_incident:
            self.in_incident = True
            self.top_severity = severity
            self.last_alert_time = t
            self.incident_start = t
            self.reminders_sent = 0
            return [Decision("start", severity, t, t)]

        if RANK[severity] > RANK[self.top_severity]:
            self.top_severity = severity
            self.last_alert_time = t
            return [Decision("escalation", severity, t, self.incident_start)]

        if t - self.last_alert_time >= self.reminder and self.reminders_sent < self.max_reminders:
            self.last_alert_time = t
            self.reminders_sent += 1
            return [Decision("reminder", severity, t, self.incident_start)]
        return []
