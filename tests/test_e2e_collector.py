"""End-to-end: run the REAL collector (all jobs, threads, merge, state, ranking, output) against a
fake internet. Covers happy path, broken sources, reruns, new versions next day, and volume."""
import json
import time
from datetime import datetime, timedelta, timezone
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from digest import build as build_mod
from digest import config

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)


def atom(entries):
    body = "".join(f'<entry><title>{t}</title><link href="{u}"/><updated>{d}</updated>'
                   f'<content type="html">{c}</content></entry>' for t, u, d, c in entries)
    return f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{body}</feed>'


def rss(entries):
    body = "".join(f"<item><title>{t}</title><link>{u}</link><pubDate>{d}</pubDate>"
                   f"<description>{c}</description></item>" for t, u, d, c in entries)
    return f"<rss><channel>{body}</channel></rss>"


def hn_page(rows):
    out = ["<table>"]
    for i, title, url, pts, com in rows:
        out.append(f'<tr class="athing" id="{i}"><td><span class="titleline"><a href="{url}">{title}</a></span></td></tr>'
                   f'<tr><td class="subtext"><span class="score" id="score_{i}">{pts} points</span>'
                   f'<a href="item?id={i}">{com}&nbsp;comments</a></td></tr>')
    return "".join(out) + "</table>"


class FakeInternet:
    """Routes every URL the collector asks for. Unknown URLs raise like a 404."""

    def __init__(self, day=26, extra_release=False, volume=0):
        self.day, self.extra_release, self.volume = day, extra_release, volume
        self.calls = []

    def __call__(self, url, *a, **k):
        self.calls.append(url)
        d = f"2026-11-{self.day:02d}T01:00:00Z"
        if "openai-python/releases.atom" in url:
            entries = [("v3.59.0", "https://github.com/openai/openai-python/releases/v3.59.0", d,
                        "Removed deprecated client.beta endpoints (breaking change).")]
            if self.extra_release:
                entries.insert(0, ("v3.60.0", "https://github.com/openai/openai-python/releases/v3.60.0", d, "New features."))
            return atom(entries)
        if "playwright-python/releases.atom" in url:
            return atom([("v1.65.2", "https://github.com/microsoft/playwright-python/releases/v1.65.2", d, "Bug fixes."),
                         ("v1.65.1", "https://github.com/microsoft/playwright-python/releases/v1.65.1", d, "Bug fixes.")])
        if "SeleniumHQ/selenium/releases.atom" in url:
            return atom([("Nightly", "https://github.com/SeleniumHQ/selenium/releases/nightly", d, "nightly"),
                         ("Selenium 4.51.0", "https://github.com/SeleniumHQ/selenium/releases/4.51.0", d, "Java changes")])
        if url.endswith(".atom") and "github.com" in url:
            return atom([])                                   # other repos: nothing new
        if "pypi.org/rss/project/pytest" in url:
            return rss([("9.2.0", "https://pypi.org/project/pytest/9.2.0/", "Tue, 25 Nov 2026 10:00:00 GMT", ""),
                        ("10.0.0rc1", "https://pypi.org/project/pytest/10.0.0rc1/", "Wed, 26 Nov 2026 01:00:00 GMT", "")])
        if "interconnects.ai" in url:
            return "<html>Cloudflare challenge</html><p>"         # malformed: must be reported, not crash
        if "simonwillison.net" in url:
            raise RuntimeError("Timeout")
        if any(h in url for h in ("hamel.dev", "eugeneyan.com", "martinfowler.com", "testing.googleblog.com",
                                  "sebastianraschka", "pythoninsider", "realpython", "openai.com/news",
                                  "modelcontextprotocol.io", "github.blog", "pypi.org/feed", "devblogs.microsoft",
                                  "huggingface.co/blog", "arxiv.org")):
            host = urlsplit(url).netloc
            posts = [(f"{host} post about pytest and agents {n}", f"https://{host}/p{n}",
                      "Tue, 25 Nov 2026 10:00:00 GMT", "&lt;p&gt;" + "A useful paragraph about testing AI agents. " * 12 + "&lt;/p&gt;")
                     for n in range(3)]
            return rss(posts)
        if "huggingface.co/api/daily_papers" in url:
            return json.dumps([{"paper": {"id": "2611.1", "title": "Agents that write tests", "summary": "We study.", "upvotes": 9}}])
        if "hn.algolia.com" in url:
            q = parse_qs(urlsplit(url).query)["query"][0]
            hits = []
            if q == "MCP":
                hits.append({"objectID": "777", "title": "Security incident: malicious MCP server steals tokens",
                             "url": "https://blog.example/mcp-incident", "points": 420, "num_comments": 200,
                             "created_at": "2026-11-26T02:00:00Z"})
            if q == "playwright":
                hits.append({"objectID": "888", "title": "Tom Stoppard, playwright, dies at 88", "url": "https://n/s",
                             "points": 50, "num_comments": 3})
            for n in range(self.volume):
                hits.append({"objectID": f"{q}-{n}", "title": f"{q} story number {n} about AI agents",
                             "url": f"https://v.example/{q}/{n}", "points": 100 + n, "num_comments": n})
            return json.dumps({"hits": hits})
        if "news.ycombinator.com/active" in url:
            return "<html><body>Sorry.</body></html>"            # layout change → must be flagged
        if "news.ycombinator.com/bestcomments" in url:
            return '<span class="onstory"> | on: <a href="item?id=999" title="How the Claude Code team thinks about verification">x</a></span>'
        if "news.ycombinator.com" in url:
            return hn_page([(777, "Security incident: malicious MCP server steals tokens", "https://blog.example/mcp-incident?utm_source=hn", 430, 210),
                            (555, "Macrohistory in Six Facts", "https://m.example", 160, 80),
                            (556, "Show HN: pytest-tia runs only affected tests", "https://p.example", 40, 9)])
        raise RuntimeError(f"404 {url}")


def collect_with(tmp_path, net, now=NOW):
    with mock.patch.object(build_mod, "fetch", net):
        summary = build_mod.build(tmp_path / "site", tmp_path / "seen.json", now=now, offline=True)
    data = json.loads((tmp_path / "site" / "data.json").read_text())
    return summary, data


def test_e2e_happy_path_and_broken_sources(tmp_path):
    summary, data = collect_with(tmp_path, FakeInternet())
    items = data["items"]
    keys = [i["key"] for i in items]
    titles = [i["title"] for i in items]

    # every story appears exactly once
    assert len(keys) == len(set(keys))
    # the incident found in 3 places is one card, in its most specific group, with the others noted
    incident = [i for i in items if "malicious MCP" in i["title"]]
    assert len(incident) == 1 and incident[0]["group"] == "Topic · MCP" and incident[0]["also_in"]
    assert incident[0]["quadrant"] == "Act now" and "Security" in incident[0]["reasons"]
    # filters: nightly, rc builds, theatre "playwright", off-topic HN stories are out
    assert not any("Nightly" in t or "rc1" in t or "Stoppard" in t or "Macrohistory" in t for t in titles)
    # all releases from all repos survive (no per-group cap starving them)
    assert {"OpenAI Python SDK v3.59.0", "Playwright (Python) v1.65.2", "Playwright (Python) v1.65.1",
            "Selenium 4.51.0", "pytest 9.2.0"} <= set(titles)
    breaking = next(i for i in items if i["title"] == "OpenAI Python SDK v3.59.0")
    assert "Breaking change" in breaking["reasons"]
    # every blog feed gets a fair chance (no feed starved by the cap)
    blog_sources = {i["source"] for i in items if i["group"] == "Practitioner blogs"}
    working_blogs = {n for n, *_ in config.BLOG_FEEDS} - {"Interconnects", "Simon Willison"}
    assert blog_sources == working_blogs
    # excerpts were made from feed text, all within limits
    assert all(len(i["summary"].split()) <= 200 for i in items)
    # failures are reported with a reason, and do not stop the build
    failed = {s["name"]: s["error"] for s in data["sources"] if not s["ok"]}
    assert "Interconnects" in failed and "Simon Willison" in failed and "HN Active" in failed
    assert "layout may have changed" in failed["HN Active"]
    assert set(summary["failures"]) == set(failed)
    # the app shell was copied next to the data
    for f in ("index.html", "app.js", "app.css", "sw.js", "manifest.webmanifest", "icon-192.png"):
        assert (tmp_path / "site" / f).exists(), f


def test_e2e_rerun_same_day_and_next_day_never_repeats(tmp_path):
    first, data1 = collect_with(tmp_path, FakeInternet())
    again, data2 = collect_with(tmp_path, FakeInternet(), now=NOW + timedelta(minutes=30))
    assert again["new_today"] == first["new_today"]          # same day: same set, no duplicates
    assert len(data2["items"]) == len(data1["items"])
    nxt, data3 = collect_with(tmp_path, FakeInternet(day=27), now=NOW + timedelta(days=1))
    assert nxt["new_today"] == 0                              # nothing new tomorrow
    assert len(data3["items"]) == len(data1["items"])         # still listed under "last 7 days"


def test_e2e_new_version_next_day_is_shown(tmp_path):
    collect_with(tmp_path, FakeInternet())
    nxt, data = collect_with(tmp_path, FakeInternet(day=27, extra_release=True), now=NOW + timedelta(days=1))
    new_titles = [i["title"] for i in data["items"] if i["first_seen"] == "2026-11-27"]
    assert new_titles == ["OpenAI Python SDK v3.60.0"]


def test_e2e_items_expire_after_archive_window(tmp_path):
    collect_with(tmp_path, FakeInternet())
    later = NOW + timedelta(days=config.ARCHIVE_DAYS + 1)
    _, data = collect_with(tmp_path, FakeInternet(day=26), now=later)
    assert data["items"] == []                                 # old items gone from the page…
    state = json.loads((tmp_path / "seen.json").read_text())
    assert state["seen"]                                       # …but still remembered, so never re-shown


def test_e2e_total_outage_still_builds_a_page(tmp_path):
    def down(url, *a, **k):
        raise RuntimeError("network down")
    summary, data = collect_with(tmp_path, down)
    assert data["items"] == [] and all(not s["ok"] for s in data["sources"])
    assert (tmp_path / "site" / "index.html").exists()


def test_e2e_volume_and_speed(tmp_path):
    net = FakeInternet(volume=40)                              # ~40 hits × 30 queries ≈ 1,200 candidates
    start = time.perf_counter()
    summary, data = collect_with(tmp_path, net)
    first = time.perf_counter() - start
    start = time.perf_counter()
    collect_with(tmp_path, FakeInternet(volume=40), now=NOW + timedelta(minutes=30))
    second = time.perf_counter() - start
    print(f"\nperf: fetched={summary['fetched']} shown={len(data['items'])} first={first:.1f}s rerun={second:.1f}s")
    assert first < 60 and second < 60
    per_group = {}
    for i in data["items"]:
        if i["group"].startswith(("HN ·", "Topic ·")):
            per_group[i["group"]] = per_group.get(i["group"], 0) + 1
    assert max(per_group.values()) <= config.MAX_PER_GROUP     # HN groups stay capped
