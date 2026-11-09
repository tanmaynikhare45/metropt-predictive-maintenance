"""Alert settings. Override with environment variables or .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Slack incoming webhook. Treat it like a password: it lives in .env only, never in code or Git.
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()

# Where the Slack link points to (the React dashboard).
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5173").rstrip("/")

# An incident ends after this many clean 10-minute windows in a row (6 = 1 hour).
RECOVER_AFTER_WINDOWS = int(os.getenv("ALERT_RECOVER_WINDOWS", "6"))

# While an incident continues, remind every N hours of DATA time (not wall-clock time:
# a replay runs 200x faster than real time), at most MAX_REMINDERS times per incident.
REMINDER_HOURS = float(os.getenv("ALERT_REMINDER_HOURS", "6"))
MAX_REMINDERS = int(os.getenv("ALERT_MAX_REMINDERS", "4"))

SLACK_TIMEOUT_S = float(os.getenv("SLACK_TIMEOUT_S", "5"))
SLACK_RETRIES = int(os.getenv("SLACK_RETRIES", "3"))

# At start-up, alerts that were stored but never delivered (crash, Slack outage) and are
# newer than this many hours (data time) are sent again.
RESEND_RECENT_HOURS = 6
RESEND_LIMIT = 5

RECOMMENDATIONS_FILE = Path(__file__).with_name("recommendations.json")
