"""Post to a Slack incoming webhook: retries, timeout, and a background sender.

The webhook URL is a secret. It is never printed, logged or put into an error message here.
"""
import json
import queue
import threading
import time
import urllib.error
import urllib.request


class SlackClient:
    def __init__(self, webhook_url, timeout=5.0, retries=3, sleep=time.sleep):
        self._url = webhook_url
        self.timeout = timeout
        self.retries = max(1, retries)
        self._sleep = sleep

    def __repr__(self):
        return "SlackClient(webhook=<hidden>)"

    def post(self, text):
        """Returns (ok, detail). Retries network errors, 5xx and 429. A 4xx (bad URL/payload) is final."""
        body = json.dumps({"text": text}).encode("utf-8")
        detail = ""
        for attempt in range(1, self.retries + 1):
            wait = 2 ** (attempt - 1)
            try:
                req = urllib.request.Request(self._url, data=body, method="POST",
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    reply = resp.read().decode("utf-8", "replace").strip()
                    if resp.status == 200:
                        return True, reply or "ok"
                    detail = f"HTTP {resp.status}"
            except urllib.error.HTTPError as exc:          # must come before URLError
                detail = f"HTTP {exc.code}"
                if exc.code == 429:
                    try:
                        wait = min(float(exc.headers.get("Retry-After", wait)), 10.0)
                    except (TypeError, ValueError):
                        pass
                elif 400 <= exc.code < 500:
                    return False, detail                    # wrong URL / payload: retrying will not help
            except ValueError:
                return False, "invalid webhook URL"
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                detail = exc.__class__.__name__
            if attempt < self.retries:
                self._sleep(wait)
        return False, detail


class AsyncSender:
    """Sends in a background thread, so a slow or broken Slack can never block the Kafka consumer."""

    def __init__(self, client, on_result=None, maxsize=1000):
        self.client = client
        self.on_result = on_result
        self._q = queue.Queue(maxsize=maxsize)
        self._thread = threading.Thread(target=self._run, name="slack-sender", daemon=True)
        self._thread.start()

    def submit(self, alert_id, text) -> bool:
        try:
            self._q.put_nowait((alert_id, text))
            return True
        except queue.Full:
            return False

    def _run(self):
        while True:
            item = self._q.get()
            if item is None:
                return
            alert_id, text = item
            try:
                ok, detail = self.client.post(text)
            except Exception as exc:                        # never let the worker die
                ok, detail = False, exc.__class__.__name__
            if self.on_result:
                try:
                    self.on_result(alert_id, ok, detail)
                except Exception as exc:
                    print(f"[alerts] result handler failed: {exc.__class__.__name__}")

    def close(self, timeout=10.0):
        """Send what is queued (up to `timeout` seconds), then stop."""
        self._q.put(None)
        self._thread.join(timeout)
