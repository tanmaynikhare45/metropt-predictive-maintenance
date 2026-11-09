"""The alert service: plug it into the consumer with  pipeline.on_scored.append(service).

For every scored window it
  1. decides whether a message is due (rules.IncidentTracker),
  2. stores the alert in the database (idempotent: no duplicates after a restart or replay),
  3. hands the Slack text to a background sender, and marks the alert delivered when Slack says ok.

Nothing in here may stop the stream: every failure is caught, counted and retried later.
"""
from collections import Counter

import pandas as pd

from . import config, messages
from .recommendations import load_rules
from .rules import IncidentTracker, alert_kind, severity_of
from .slack import AsyncSender, SlackClient
from .store import AlertStore


class AlertService:
    def __init__(self, store, sender=None, thresholds=None, rules=None, tracker=None):
        self.store = store
        self.sender = sender
        self.thresholds = thresholds or {}
        self.rules = rules or load_rules()
        self.tracker = tracker or IncidentTracker(config.RECOVER_AFTER_WINDOWS, config.REMINDER_HOURS, config.MAX_REMINDERS)
        self.stats = Counter()
        self._ready = False
        self._queue = []          # scored windows waiting to be evaluated (only fills up while the database is down)
        self._unsaved = []        # alerts decided but not stored yet

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_env(cls, models, store=None):
        thresholds = {
            "iforest_threshold": (models.anomaly_cfg or {}).get("isolation_forest_threshold"),
            "failure_threshold": (models.failure_cfg or {}).get("threshold"),
        }
        service = cls(store or AlertStore(), None, thresholds)
        if config.SLACK_WEBHOOK_URL:
            client = SlackClient(config.SLACK_WEBHOOK_URL, config.SLACK_TIMEOUT_S, config.SLACK_RETRIES)
            service.sender = AsyncSender(client, on_result=service._on_delivery)
        return service

    def describe(self) -> str:
        slack = "Slack: ON" if self.sender else "Slack: OFF (SLACK_WEBHOOK_URL not set, alerts are only stored)"
        return (f"[alerts] {slack} | reminder every {config.REMINDER_HOURS:g} h, recovered after "
                f"{config.RECOVER_AFTER_WINDOWS} clean windows | dashboard link {config.DASHBOARD_URL}")

    # ------------------------------------------------------------------ the hook
    def __call__(self, result):
        """pipeline.on_scored hook. Never raises."""
        try:
            self._queue.append(result)
            self._drain()
        except Exception as exc:
            self.stats["errors"] += 1
            print(f"[alerts] unexpected error, continuing: {exc.__class__.__name__}: {exc}")

    def _drain(self):
        if not self._ready:
            try:
                self._bootstrap(self._queue[0].time)
            except Exception as exc:
                self.stats["bootstrap_retries"] += 1
                print(f"[alerts] database not ready, will retry: {exc.__class__.__name__}")
                return
        self._flush_unsaved()
        while self._queue:
            result = self._queue.pop(0)                    # the tracker moves on exactly once per window
            for decision in self.tracker.step(result.time, severity_of(result.summary)):
                self._unsaved.append(self._payload(decision, result.summary))
            self._flush_unsaved()

    def _bootstrap(self, first_time):
        first = pd.Timestamp(first_time)
        self.tracker.restore(self.store.history_before(first))
        if self.sender is not None:
            since = first - pd.Timedelta(hours=config.RESEND_RECENT_HOURS)
            for row in self.store.undelivered(since, first, config.RESEND_LIMIT):
                if self.sender.submit(row["id"], row["message"] or ""):
                    self.stats["resent"] += 1
        self._ready = True

    # ------------------------------------------------------------------ building and storing alerts
    def _payload(self, decision, summary):
        recovered = decision.action == "recovered"
        kind = "recovered" if recovered else alert_kind(summary)
        text = messages.build_slack_text(decision, kind, summary, self.thresholds, self.rules)
        top = {} if recovered else {k: round(float(v), 2) for k, v in (summary.get("top_features") or {}).items()}
        return {"time": decision.time, "kind": kind, "severity": decision.severity, "message": text, "top": top}

    def _flush_unsaved(self):
        while self._unsaved:
            p = self._unsaved[0]
            try:
                alert_id = self.store.insert(p["time"], p["kind"], p["severity"], p["message"], p["top"])
            except Exception as exc:
                self.stats["store_errors"] += 1
                print(f"[alerts] could not store an alert yet, will retry: {exc.__class__.__name__}")
                return False
            self._unsaved.pop(0)
            if alert_id is None:
                self.stats["duplicates"] += 1                # already stored: it was sent before
                continue
            self.stats["created"] += 1
            print(f"[alerts] {p['severity'].upper()} {p['kind']} at {messages.fmt_time(p['time'])} -> {messages.preview(p['message'])}")
            if self.sender is not None and not self.sender.submit(alert_id, p["message"]):
                self.stats["queue_full"] += 1
        return True

    def _on_delivery(self, alert_id, ok, detail):
        """Called from the Slack thread."""
        if ok:
            try:
                self.store.mark_delivered(alert_id)
                self.stats["delivered"] += 1
            except Exception as exc:
                print(f"[alerts] sent to Slack but could not mark alert {alert_id}: {exc.__class__.__name__}")
        else:
            self.stats["delivery_failed"] += 1
            print(f"[alerts] Slack delivery failed for alert {alert_id} ({detail}); it stays stored with delivered = false")

    def close(self):
        try:
            self._flush_unsaved()
        except Exception:
            pass
        if self.sender is not None:
            self.sender.close()
        self.store.close()
