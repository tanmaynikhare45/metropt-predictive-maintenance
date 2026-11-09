import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from alerts.slack import AsyncSender, SlackClient


class FakeSlack:
    """A local HTTP server that answers with a scripted list of status codes."""

    def __init__(self, statuses, retry_after=None):
        outer = self
        self.statuses = list(statuses)
        self.requests = []
        self.retry_after = retry_after

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                outer.requests.append(json.loads(body))
                status = outer.statuses.pop(0) if outer.statuses else 200
                self.send_response(status)
                if status == 429 and outer.retry_after is not None:
                    self.send_header("Retry-After", str(outer.retry_after))
                payload = b"ok" if status == 200 else b"nope"
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *a):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()


@pytest.fixture
def slack():
    made = []

    def make(statuses, **kw):
        s = FakeSlack(statuses, **kw)
        made.append(s)
        return s
    yield make
    for s in made:
        s.stop()


def client(url, **kw):
    return SlackClient(url, timeout=2, retries=kw.get("retries", 3), sleep=lambda s: None)


def test_success(slack):
    s = slack([200])
    ok, detail = client(s.url).post("hello <world>")
    assert ok and detail == "ok"
    assert s.requests == [{"text": "hello <world>"}]


def test_server_errors_are_retried_until_success(slack):
    s = slack([500, 502, 200])
    ok, _ = client(s.url).post("x")
    assert ok and len(s.requests) == 3


def test_gives_up_after_the_retries(slack):
    s = slack([500, 500, 500, 500])
    ok, detail = client(s.url, retries=3).post("x")
    assert not ok and detail == "HTTP 500" and len(s.requests) == 3


def test_client_errors_are_final(slack):
    s = slack([404, 200])
    ok, detail = client(s.url).post("x")
    assert not ok and detail == "HTTP 404" and len(s.requests) == 1


def test_rate_limit_is_retried(slack):
    s = slack([429, 200], retry_after=0)
    assert client(s.url).post("x")[0] and len(s.requests) == 2


def test_connection_refused_does_not_raise():
    ok, detail = SlackClient("http://127.0.0.1:1/hook", timeout=1, retries=2, sleep=lambda s: None).post("x")
    assert not ok and detail


def test_invalid_url_does_not_raise():
    assert SlackClient("not a url", sleep=lambda s: None).post("x") == (False, "invalid webhook URL")


def test_the_secret_is_never_shown():
    c = SlackClient("https://hooks.slack.com/services/SECRET", sleep=lambda s: None)
    assert "SECRET" not in repr(c)


def test_async_sender_delivers_and_reports_results(slack):
    s = slack([200, 404])
    results = []
    sender = AsyncSender(client(s.url), on_result=lambda i, ok, d: results.append((i, ok, d)))
    assert sender.submit(1, "a") and sender.submit(2, "b")
    sender.close(timeout=5)
    assert results == [(1, True, "ok"), (2, False, "HTTP 404")]


def test_async_sender_survives_a_crashing_client():
    class Boom:
        def post(self, text):
            raise RuntimeError("boom")
    results = []
    sender = AsyncSender(Boom(), on_result=lambda i, ok, d: results.append((i, ok)))
    sender.submit(1, "a")
    sender.submit(2, "b")
    sender.close(timeout=5)
    assert results == [(1, False), (2, False)]
