"""Backend server tests over real HTTP on a local port (collector replaced by a fast fake)."""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from digest.dedupe import atomic_write
from server.app import Radar, Settings, make_handler


class Fake:
    def __init__(self, site: Path, delay=0.0, fail=False):
        self.site, self.delay, self.fail, self.calls = site, delay, fail, 0

    def __call__(self):
        self.calls += 1
        time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("all sources down")
        atomic_write(self.site / "data.json", json.dumps({"items": [], "n": self.calls}))  # like the collector
        return {"new_today": 0, "headlines": ["x"]}


def start(tmp_path, delay=0.0, fail=False, with_data=True, **env):
    settings = Settings({"SITE_DIR": str(tmp_path / "site"), "STATE_PATH": str(tmp_path / "state/seen.json"),
                         "MIN_REFRESH_SECONDS": env.get("min_refresh", "300"), "STALE_MINUTES": env.get("stale", "10")})
    fake = Fake(settings.site, delay, fail)
    radar = Radar(settings, build_fn=fake)
    radar.prepare()
    if with_data:
        (settings.site / "data.json").write_text('{"items": [], "n": 0}')
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(radar))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    return base, radar, fake, httpd


def req(url, method="GET"):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def wait_idle(radar, timeout=5):
    end = time.time() + timeout
    while radar.building and time.time() < end:
        time.sleep(0.02)


def test_serves_app_with_correct_types_and_security_headers(tmp_path):
    base, radar, _, httpd = start(tmp_path)
    try:
        code, h, body = req(base + "/")
        assert code == 200 and b"AI + QA Radar" in body and h["Content-Type"].startswith("text/html")
        assert "default-src 'self'" in h["Content-Security-Policy"] and h["X-Content-Type-Options"] == "nosniff"
        assert req(base + "/app.js")[1]["Content-Type"].startswith("text/javascript")
        assert req(base + "/manifest.webmanifest")[1]["Content-Type"].startswith("application/manifest+json")
        assert req(base + "/icon-192.png")[1]["Content-Type"] == "image/png"
        code, h, _ = req(base + "/", method="HEAD")
        assert code == 200 and int(h["Content-Length"]) > 0
    finally:
        httpd.shutdown()


def test_path_traversal_and_unknown_paths_are_404(tmp_path):
    base, _, _, httpd = start(tmp_path)
    (tmp_path / "secret.txt").write_text("top secret")
    try:
        for path in ["/../secret.txt", "/..%2fsecret.txt", "/%2e%2e/secret.txt", "/nope.html", "/api/nope",
                     "/../../etc/passwd", "//etc/passwd"]:
            code, _, body = req(base + path)
            assert code == 404 and b"top secret" not in body and b"root:" not in body, path
    finally:
        httpd.shutdown()


def test_health_and_status(tmp_path):
    base, radar, _, httpd = start(tmp_path)
    try:
        code, _, body = req(base + "/api/health")
        assert code == 200 and json.loads(body)["ok"] is True
        status = json.loads(req(base + "/api/status")[2])
        assert status["data_age_minutes"] is not None and status["building"] is False
    finally:
        httpd.shutdown()


def test_first_start_without_data_returns_503_and_builds(tmp_path):
    base, radar, fake, httpd = start(tmp_path, with_data=False)
    try:
        code, h, _ = req(base + "/data.json")
        assert code == 503 and h["Retry-After"] == "30"
        wait_idle(radar)
        code, _, body = req(base + "/data.json")
        assert code == 200 and json.loads(body)["n"] == 1 and fake.calls == 1
    finally:
        httpd.shutdown()


def test_reader_never_sees_a_half_written_file(tmp_path):
    """Hammer /data.json while refreshes rewrite it: every response must be valid JSON."""
    base, radar, fake, httpd = start(tmp_path, min_refresh="0")
    big = json.dumps({"items": ["x" * 200] * 5000})
    fake_writes = threading.Event()

    def writer():
        while not fake_writes.is_set():
            atomic_write(radar.s.site / "data.json", big)
    t = threading.Thread(target=writer, daemon=True)
    t.start()
    try:
        for _ in range(60):
            code, _, body = req(base + "/data.json")
            assert code == 200
            json.loads(body)
    finally:
        fake_writes.set()
        t.join()
        httpd.shutdown()


def test_fresh_data_does_not_trigger_refresh_but_stale_data_does(tmp_path):
    base, radar, fake, httpd = start(tmp_path, stale="10", delay=0.3)
    try:
        req(base + "/data.json")
        wait_idle(radar)
        assert fake.calls == 0
        old = time.time() - 3600
        os.utime(radar.s.site / "data.json", (old, old))
        code, _, body = req(base + "/data.json")
        assert code == 200 and json.loads(body)["n"] == 0        # you get current data instantly…
        wait_idle(radar)
        assert fake.calls == 1                                    # …and a refresh ran in the background
    finally:
        httpd.shutdown()


def test_manual_refresh_is_rate_limited(tmp_path):
    base, radar, fake, httpd = start(tmp_path, min_refresh="300")
    try:
        code, _, body = req(base + "/api/refresh", method="POST")
        assert code == 202 and json.loads(body)["started"] is True
        wait_idle(radar)
        code, h, body = req(base + "/api/refresh", method="POST")
        assert code == 429 and int(h["Retry-After"]) > 0 and fake.calls == 1
        assert req(base + "/api/refresh")[0] == 404              # GET is not allowed to trigger work
        assert req(base + "/api/other", method="POST")[0] == 404
    finally:
        httpd.shutdown()


def test_concurrent_refreshes_run_only_one_build(tmp_path):
    base, radar, fake, httpd = start(tmp_path, delay=2.0, min_refresh="300")
    try:
        results = []
        threads = [threading.Thread(target=lambda: results.append(req(base + "/api/refresh", method="POST")[0]))
                   for _ in range(10)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        wait_idle(radar)
        assert fake.calls == 1 and results.count(202) == 10       # one started, the rest told "already building"
    finally:
        httpd.shutdown()


def test_failed_refresh_keeps_server_up_and_reports_error(tmp_path):
    base, radar, fake, httpd = start(tmp_path, fail=True, min_refresh="0")
    try:
        req(base + "/api/refresh", method="POST")
        wait_idle(radar)
        status = json.loads(req(base + "/api/status")[2])
        assert "all sources down" in status["last_error"] and status["building"] is False
        assert req(base + "/")[0] == 200 and req(base + "/data.json")[0] == 200   # old data still served
    finally:
        httpd.shutdown()


def test_full_stack_real_collector_behind_real_server(tmp_path):
    """Frontend + backend together: real server, real collector, simulated internet."""
    from unittest import mock

    from digest import build as collector
    from tests.test_e2e_collector import FakeInternet

    settings = Settings({"SITE_DIR": str(tmp_path / "site"), "STATE_PATH": str(tmp_path / "state/seen.json")})
    radar = Radar(settings, build_fn=lambda: collector.build(settings.site, settings.state, offline=True))
    radar.prepare()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(radar))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        with mock.patch.object(collector, "fetch", FakeInternet()):
            assert req(base + "/data.json")[0] == 503          # first open: collecting
            wait_idle(radar, timeout=60)
        code, _, body = req(base + "/data.json")
        data = json.loads(body)
        assert code == 200 and data["items"] and data["sources"] and data["learning"]["courses"]
        assert any(i["quadrant"] == "Act now" for i in data["items"])
        status = json.loads(req(base + "/api/status")[2])
        assert status["last_error"] is None and status["summary"]["new_today"] == len(data["items"])
        assert b"app.js" in req(base + "/")[2]
    finally:
        httpd.shutdown()


def test_bad_seed_url_is_ignored(tmp_path):
    settings = Settings({"SITE_DIR": str(tmp_path / "site"), "STATE_PATH": str(tmp_path / "s/seen.json"),
                         "SEED_STATE_URL": "https://127.0.0.1:9/nothing.json"})
    Radar(settings, build_fn=lambda: {}).prepare()      # must not raise
    assert not settings.state.exists()
