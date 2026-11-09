"""A fake Slack on your own PC: prints every alert it receives, so you can test without posting to Slack.

    python scripts/mock_slack.py                    # listens on http://127.0.0.1:9000/hook
    python scripts/mock_slack.py --fail-first 3     # answers 500 to the first 3 requests (tests retries)
    python scripts/mock_slack.py --status 500       # always fails (simulates a Slack outage)

Then put   SLACK_WEBHOOK_URL=http://127.0.0.1:9000/hook   in .env and start the consumer.
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


def make_handler(args):
    state = {"count": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            state["count"] += 1
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", "replace")
            if args.delay:
                time.sleep(args.delay)
            failing = args.status != 200 or state["count"] <= args.fail_first
            status = (args.status if args.status != 200 else 500) if failing else 200
            try:
                text = json.loads(raw).get("text", raw)
            except ValueError:
                text = raw
            stamp = time.strftime("%H:%M:%S")
            if status == 200:
                print(f"\n=== [{stamp}] message #{state['count']} received ===\n{text}\n", flush=True)
                body = b"ok"
            else:
                print(f"[{stamp}] request #{state['count']} -> answering HTTP {status} (simulated failure)", flush=True)
                body = b"error"
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--status", type=int, default=200, help="HTTP status to answer with (200 = ok)")
    ap.add_argument("--fail-first", type=int, default=0, help="answer HTTP 500 to the first N requests")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds to wait before answering")
    a = ap.parse_args()
    print(f"Fake Slack listening on http://127.0.0.1:{a.port}/hook  (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", a.port), make_handler(a)).serve_forever()
