"""Send alerts again that are stored but were never delivered (Slack outage, crash).

    python scripts/resend_alerts.py                 # the 10 oldest undelivered alerts
    python scripts/resend_alerts.py --limit 50
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alerts import config
from alerts.messages import preview
from alerts.slack import SlackClient
from alerts.store import AlertStore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    if not config.SLACK_WEBHOOK_URL:
        sys.exit("SLACK_WEBHOOK_URL is not set in .env")
    store = AlertStore()
    client = SlackClient(config.SLACK_WEBHOOK_URL, config.SLACK_TIMEOUT_S, config.SLACK_RETRIES)
    rows = store.undelivered("1970-01-01", None, args.limit)
    print(f"{len(rows)} undelivered alert(s)")
    for row in rows:
        ok, detail = client.post(row["message"] or "")
        print(f"  #{row['id']} {row['time']:%Y-%m-%d %H:%M} {row['kind']}: {'sent' if ok else 'FAILED ' + detail}  ({preview(row['message'] or '')})")
        if ok:
            store.mark_delivered(row["id"])
    store.close()


if __name__ == "__main__":
    main()
