"""Backend server: serves the web app and its data, and keeps the data fresh.

    python -m server                  # http://localhost:8000

Uses only the Python standard library (plus the collector's own deps), so it runs on any
free host: Render, Hugging Face Spaces, Koyeb, a Raspberry Pi, or your laptop.

Endpoints
  GET  /                 the app (web/)
  GET  /data.json        latest data; if older than STALE_MINUTES a refresh starts in the
                         background (you get the current data instantly, fresh data next load)
  POST /api/refresh      start a refresh now (rate-limited, returns 202 or 429)
  GET  /api/status       last refresh: when, how long, counts, failed sources, error
  GET  /api/health       liveness check for the host
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
import shutil
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from digest import build as collector

log = logging.getLogger("radar")
ROOT = Path(__file__).resolve().parent.parent

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self' https://hn.algolia.com; manifest-src 'self'; frame-ancestors 'none'"
    ),
}
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")


class Settings:
    def __init__(self, env=os.environ):
        self.port = int(env.get("PORT", "8000"))
        self.site = Path(env.get("SITE_DIR", ROOT / "site"))
        self.state = Path(env.get("STATE_PATH", ROOT / "state" / "seen.json"))
        self.refresh_minutes = float(env.get("REFRESH_MINUTES", "30"))
        self.stale_minutes = float(env.get("STALE_MINUTES", "10"))
        self.min_refresh_seconds = float(env.get("MIN_REFRESH_SECONDS", "300"))
        # optional: start from the memory the GitHub Actions collector saved (public repo),
        # so a fresh server (free hosts wipe disks on restart) doesn't repeat old stories
        self.seed_state_url = env.get("SEED_STATE_URL", "")


class Radar:
    """Owns the data on disk and makes sure only one refresh runs at a time."""

    def __init__(self, settings: Settings, build_fn=None):
        self.s = settings
        self.build_fn = build_fn or (lambda: collector.build(self.s.site, self.s.state))
        self.lock = threading.Lock()
        self.building = False
        self.last_started = 0.0
        self.status: dict = {"last_ok": None, "last_error": None, "duration_s": None, "summary": None}

    # ------------------------------------------------------------- setup
    def prepare(self) -> None:
        self.s.site.mkdir(parents=True, exist_ok=True)
        if collector.WEB_DIR.exists():
            shutil.copytree(collector.WEB_DIR, self.s.site, dirs_exist_ok=True)
        if not self.s.state.exists() and self.s.seed_state_url.startswith("https://"):
            try:
                with urllib.request.urlopen(self.s.seed_state_url, timeout=20) as resp:  # noqa: S310
                    raw = resp.read()
                json.loads(raw)  # only accept valid JSON
                self.s.state.parent.mkdir(parents=True, exist_ok=True)
                self.s.state.write_bytes(raw)
                log.info("seeded state from %s", self.s.seed_state_url)
            except Exception as exc:  # seeding is best-effort
                log.warning("could not seed state: %s", exc)

    # ----------------------------------------------------------- refresh
    def data_age_minutes(self) -> float | None:
        path = self.s.site / "data.json"
        return (time.time() - path.stat().st_mtime) / 60 if path.exists() else None

    def refresh(self, force: bool = False) -> tuple[bool, float]:
        """Start a background refresh. Returns (started, seconds_until_allowed)."""
        with self.lock:
            if self.building:
                return False, 0.0
            wait = self.s.min_refresh_seconds - (time.time() - self.last_started)
            if not force and wait > 0:
                return False, wait
            self.building, self.last_started = True, time.time()
        threading.Thread(target=self._run, daemon=True).start()
        return True, 0.0

    def _run(self) -> None:
        started = time.time()
        try:
            summary = self.build_fn()
            self.status.update(last_ok=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               last_error=None, summary={k: v for k, v in (summary or {}).items() if k != "headlines"})
        except Exception as exc:  # a failed refresh must never take the server down
            log.exception("refresh failed")
            self.status["last_error"] = f"{type(exc).__name__}: {exc}"[:300]
        finally:
            self.status["duration_s"] = round(time.time() - started, 1)
            with self.lock:
                self.building = False

    def schedule_forever(self, stop: threading.Event) -> None:
        while not stop.wait(self.s.refresh_minutes * 60):
            self.refresh(force=True)


def make_handler(radar: Radar):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Radar/1.0"
        sys_version = ""

        def log_message(self, fmt, *args):  # quieter logs
            log.info("%s %s", self.address_string(), fmt % args)

        # ------------------------------------------------------- helpers
        def _send(self, code: int, body: bytes, ctype: str, cache: str = "no-store", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            for k, v in {**SECURITY_HEADERS, **(extra or {})}.items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code: int, obj, extra=None):
            self._send(code, json.dumps(obj).encode(), "application/json; charset=utf-8", extra=extra)

        def _static(self, rel: str):
            site = radar.s.site.resolve()
            target = (site / rel.lstrip("/")).resolve()
            if target.is_dir():
                target = target / "index.html"
            if site not in target.parents and target != site or not target.is_file():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith(("json", "javascript")):
                ctype += "; charset=utf-8"
            cache = "no-cache" if target.suffix in {".html", ".js", ".css", ".json"} else "public, max-age=86400"
            self._send(200, target.read_bytes(), ctype, cache=cache)

        # -------------------------------------------------------- routes
        def do_GET(self):  # noqa: N802
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            if path == "/api/health":
                return self._json(200, {"ok": True, "building": radar.building})
            if path == "/api/status":
                age = radar.data_age_minutes()
                return self._json(200, {**radar.status, "building": radar.building,
                                        "data_age_minutes": None if age is None else round(age, 1)})
            if path == "/data.json":
                age = radar.data_age_minutes()
                if age is None or age > radar.s.stale_minutes:
                    radar.refresh()  # stale-while-revalidate: answer now, refresh in background
                if age is None:
                    return self._json(503, {"error": "first refresh in progress, try again in a minute"},
                                      extra={"Retry-After": "30"})
            if path.startswith("/api/"):
                return self._json(404, {"error": "not found"})
            return self._static(path)

        do_HEAD = do_GET

        def do_POST(self):  # noqa: N802
            if self.path.split("?", 1)[0] != "/api/refresh":
                return self._json(404, {"error": "not found"})
            started, wait = radar.refresh()
            if started:
                return self._json(202, {"started": True})
            if radar.building:
                return self._json(202, {"started": False, "building": True})
            return self._json(429, {"started": False, "retry_after_s": int(wait) + 1},
                              extra={"Retry-After": str(int(wait) + 1)})

    return Handler


def serve(settings: Settings | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = settings or Settings()
    radar = Radar(s)
    radar.prepare()
    if not (s.site / "data.json").exists():
        radar.refresh(force=True)
    stop = threading.Event()
    threading.Thread(target=radar.schedule_forever, args=(stop,), daemon=True).start()
    httpd = ThreadingHTTPServer(("0.0.0.0", s.port), make_handler(radar))
    log.info("AI + QA Radar on http://localhost:%s", s.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        httpd.server_close()
