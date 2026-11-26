"""Offline tests: no network calls. Run with `pytest -q`."""
import json
import os
from datetime import date, datetime, timezone

import pytest

from digest import config
from digest.build import build
from digest.dedupe import State, merge, normalize_url
from digest.models import Item
from digest.notify import format_message
from digest.rank import score, tags
from digest.sources import (algolia_url, parse_algolia, parse_feed, parse_hf_papers,
                            parse_hn_bestcomments, parse_hn_list)
from digest.summarize import html_to_text

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)

HN_HTML = """
<table>
<tr class="athing" id="111"><td><span class="titleline"><a href="https://example.com/mcp?utm_source=hn">MCP Explained</a></span></td></tr>
<tr><td class="subtext"><span class="score" id="score_111">348 points</span>
<a href="item?id=111">136&nbsp;comments</a></td></tr>
<tr class="athing" id="222"><td><span class="titleline"><a href="item?id=222">Ask HN: How do you test LLM features?</a></span></td></tr>
<tr><td class="subtext"><span class="score" id="score_222">12 points</span><a href="item?id=222">discuss</a></td></tr>
</table>"""

BEST_COMMENTS_HTML = """
<span class="onstory"> | on: <a href="item?id=333" title="How the Claude Code team thinks about verification">How the Claude Code...</a></span>
<span class="onstory"> | on: <a href="item?id=333" title="How the Claude Code team thinks about verification">dup</a></span>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>releases</title>
<entry><title>Nightly</title><link href="https://github.com/x/nightly"/><updated>2026-11-26T00:00:00Z</updated></entry>
<entry><title>v1.65.2</title><link href="https://github.com/x/v1.65.2"/><updated>2026-11-14T00:00:00Z</updated>
<content type="html">&lt;p&gt;Fixes a breaking change in locator handling.&lt;/p&gt;</content></entry>
<entry><title>v1.10.0</title><link href="https://github.com/x/v1.10.0"/><updated>2025-01-01T00:00:00Z</updated></entry>
</feed>"""

ALGOLIA = {"hits": [
    {"objectID": "444", "title": "Rustwright: Playwright rewritten in Rust", "url": "https://github.com/x/rw",
     "points": 12, "num_comments": 4, "created_at": "2026-11-25T10:00:00Z"},
    {"objectID": "445", "title": "Tom Stoppard, award-winning playwright, dies at 88",
     "url": "https://nyt.example/stoppard", "points": 10, "num_comments": 1},
]}
LONG = ("Playwright 1.65 adds failure-only reports for pytest users. " * 30).strip()


def run(tmp_path, groups, day=26, status=None, ask=None):
    summary = build(tmp_path / "site", tmp_path / "seen.json", now=NOW.replace(day=day), groups=groups,
                    status=status or [], ask=ask, offline=True)
    return summary, json.loads((tmp_path / "site" / "data.json").read_text())


# ----------------------------------------------------------------- parsers
def test_hn_list_parses_ids_points_comments_and_relative_links():
    items = parse_hn_list(HN_HTML, "Front page")
    assert [i.key for i in items] == ["hn:111", "hn:222"]
    assert items[0].points == 348 and items[0].comments == 136
    assert items[1].url == "https://news.ycombinator.com/item?id=222"
    assert items[1].comments is None


def test_bestcomments_returns_each_story_once_with_full_title():
    items = parse_hn_bestcomments(BEST_COMMENTS_HTML)
    assert [i.title for i in items] == ["How the Claude Code team thinks about verification"]


def test_release_feed_skips_nightly_and_old_versions_and_keeps_notes():
    items = parse_feed(ATOM, "Playwright (Python)", skip=r"(?i)nightly", kind="release",
                       max_age_days=45, now=NOW)
    assert [i.title for i in items] == ["Playwright (Python) v1.65.2"]
    assert items[0].key == "rel:Playwright (Python):v1.65.2"
    assert items[0].body == "Fixes a breaking change in locator handling."


def test_rss_body_and_date():
    rss = ("<rss><channel><item><title>Post</title><link>https://b/1</link>"
           "<pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate>"
           "<description>&lt;p&gt;Hello &lt;b&gt;QA&lt;/b&gt; world&lt;/p&gt;</description></item></channel></rss>")
    item = parse_feed(rss, "Blog", now=NOW)[0]
    assert item.body == "Hello QA world" and item.published == "2026-11-24"


def test_algolia_excludes_theatre_playwright():
    exclude = {t[0]: t[3] for t in config.TOPICS}["Playwright"]
    items = parse_algolia(ALGOLIA, "Playwright", exclude=exclude)
    assert [i.key for i in items] == ["hn:444"]


def test_algolia_url_has_time_and_points_filters():
    url = algolia_url("pytest", 1795000000, 5)
    assert "created_at_i%3E1795000000" in url and "points%3E%3D5" in url


def test_hf_papers_parser_filters_and_links():
    data = [{"paper": {"id": "2611.1", "title": "Agents that write tests", "summary": "We study...", "upvotes": 40},
             "publishedAt": "2026-11-25T00:00:00Z"},
            {"paper": {"id": "2611.2", "title": "Protein folding at scale", "upvotes": 90}}]
    items = parse_hf_papers(data, only=config.HF_FILTER)
    assert [i.url for i in items] == ["https://huggingface.co/papers/2611.1"]
    assert items[0].body == "We study..."


# ------------------------------------------------------------------ dedupe
def test_normalize_url_drops_tracking_and_www():
    assert normalize_url("http://www.Example.com/a/?utm_source=x&id=2#top") == \
        normalize_url("https://example.com/a?id=2")


def test_merge_keeps_first_group_and_records_other_sources():
    topic = Item(key="hn:111", title="MCP Explained", url="https://example.com/mcp", source="HN · MCP")
    merged = merge([("Topic · MCP", [topic]), ("HN · Front page", parse_hn_list(HN_HTML, "Front page"))])
    mcp = next(i for i in merged if i.key == "hn:111")
    assert mcp.group == "Topic · MCP" and "Front page" in mcp.also_in and mcp.points == 348
    assert len(merged) == 2


def test_merge_joins_near_identical_titles_from_different_sites():
    a = Item(key="a", title="Show HN: Rustwright – Playwright rewritten in Rust", url="https://x/1", source="Show HN")
    b = Item(key="b", title="Rustwright - Playwright rewritten in Rust", url="https://y/2", source="Blog")
    assert len(merge([("g1", [a]), ("g2", [b])])) == 1


# ------------------------------------------------------------------- state
def test_item_is_never_new_twice(tmp_path):
    path = tmp_path / "seen.json"
    item = Item(key="hn:1", title="Python's experimental JIT to be removed", url="https://lwn.net/x", source="HN")
    s1 = State(path)
    s1.stamp([item], date(2026, 11, 26))
    s1.save()
    again = Item(key="hn:1", title=item.title, url=item.url, source="HN", points=600)
    s2 = State(path)
    s2.stamp([again], date(2026, 11, 27))
    assert again.first_seen == "2026-11-26" and s2.items["hn:1"]["points"] == 600


def test_same_story_with_new_url_next_day_is_not_new(tmp_path):
    s = State(tmp_path / "seen.json")
    s.stamp([Item(key="hn:1", title="Claude Fable 5.2 and Mythos 5.2", url="https://a/x", source="HN")], date(2026, 11, 9))
    dup = Item(key="hn:2", title="Claude Fable 5.2 and Mythos 5.2", url="https://b/y", source="HN")
    s.stamp([dup], date(2026, 11, 10))
    assert dup.first_seen == "2026-11-09" and "hn:2" not in s.items


def test_prune_forgets_old_entries(tmp_path):
    s = State(tmp_path / "seen.json")
    s.seen = {"old": "2026-01-01", "new": "2026-11-20"}
    s.prune(date(2026, 11, 26), seen_days=120, item_days=7)
    assert s.seen == {"new": "2026-11-20"}


# ----------------------------------------------------------------- ranking
@pytest.mark.parametrize("title,group,points,quadrant", [
    ("pytest 9.2 removes deprecated fixture API (breaking change)", "Releases", None, "Act now"),
    ("Security incident: malicious MCP server steals tokens", "Topic · MCP", 300, "Act now"),
    ("Deterministic Simulation Testing Is for Everyone with pytest", "Topic · Testing & QA", 90, "Plan"),
    ("Quad9 pulled their DNS service from France after outage", "HN · Best (24h)", 375, "Watch"),
    ("Macrohistory in Six Facts", "HN · Active", 160, "FYI"),
])
def test_quadrants(title, group, points, quadrant):
    item = Item(key="k", title=title, url="https://e/k", source="x", group=group, points=points,
                published="2026-11-26T03:00:00Z")
    assert score(item, now=NOW)["quadrant"] == quadrant


def test_scores_are_bounded_and_tagged():
    item = Item(key="k", title="Claude Code + Playwright MCP + pytest security breaking change",
                url="https://e", source="x", group="Releases", points=5000, also_in=["a", "b", "c"],
                published="2026-11-26T05:00:00Z")
    result = score(item, now=NOW)
    assert 0 <= result["importance"] <= 100 and 0 <= result["urgency"] <= 100
    assert {"Playwright", "pytest", "MCP", "Coding agents", "Security"} <= set(tags(item))


# --------------------------------------------------------------- summaries
def test_ai_summary_is_capped_at_400_words_and_made_once(tmp_path):
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return "word " * 500

    item = lambda: Item(key="k1", title="Playwright 1.65", url="https://e/1", source="Blog", body=LONG)  # noqa: E731
    _, data = run(tmp_path, [("Practitioner blogs", [item()])], ask=fake_llm)
    stored = data["items"][0]
    assert stored["summary_kind"] == "ai" and len(stored["summary"].split()) <= 400
    assert "body" not in stored and data["summaries"] == "ai"
    run(tmp_path, [("Practitioner blogs", [item()])], day=27, ask=fake_llm)
    assert len(calls) == 1


def test_without_api_key_a_quoted_extractive_summary_is_used(tmp_path):
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(var, None)
    _, data = run(tmp_path, [("Practitioner blogs", [Item(key="k2", title="T", url="https://e/2", source="Blog", body=LONG)])])
    assert data["summaries"] == "extractive"
    item = data["items"][0]
    assert item["summary_kind"] == "extractive" and len(item["summary"].split()) <= 260
    assert item["summary"] in LONG  # quoted, never rewritten


def test_llm_failure_falls_back_to_quoted_summary(tmp_path):
    def broken(prompt):
        raise RuntimeError("API down")
    _, data = run(tmp_path, [("Practitioner blogs", [Item(key="k3", title="T", url="https://e/3", source="Blog", body=LONG)])],
                  ask=broken)
    assert data["items"][0]["summary_kind"] == "extractive"


def test_html_to_text_prefers_article_paragraphs():
    html = ("<html><nav><p>Menu menu menu menu menu menu menu menu menu menu</p></nav>"
            "<article><p>This is the real article paragraph about pytest fixtures and flaky tests.</p>"
            "</article><script>evil()</script></html>")
    text = html_to_text(html)
    assert "real article" in text and "Menu" not in text and "evil" not in text


# ------------------------------------------------------------------- build
def test_build_writes_app_and_ranked_data_and_never_repeats(tmp_path):
    groups = [
        ("Releases", parse_feed(ATOM, "Playwright (Python)", skip="(?i)nightly", kind="release", now=NOW)),
        ("Topic · Playwright", parse_algolia(ALGOLIA, "Playwright", exclude="(?i)dies")),
        ("HN · Front page", parse_hn_list(HN_HTML, "Front page")),
    ]
    status = [{"name": "HN Active", "group": "HN · Active", "ok": False, "count": 0, "error": "Timeout"}]
    summary, data = run(tmp_path, groups, status=status)
    assert summary["new_today"] == len(data["items"]) == 4
    assert summary["failures"] == ["HN Active"]
    assert (tmp_path / "site" / "index.html").exists() and (tmp_path / "site" / "app.js").exists()
    release = next(i for i in data["items"] if i["group"] == "Releases")
    assert release["quadrant"] in ("Act now", "Watch") and "Breaking change" in release["reasons"]
    assert set(data) >= {"ranking", "tags", "live", "sources", "check_pages", "generated"}
    second, _ = run(tmp_path, groups, day=27)
    assert second["new_today"] == 0


def test_state_changes_every_run_to_keep_schedule_alive(tmp_path):
    run(tmp_path, [])
    first = (tmp_path / "seen.json").read_text()
    run(tmp_path, [], day=27)
    assert (tmp_path / "seen.json").read_text() != first


def test_patterns_have_no_python_only_syntax():
    """The web app re-uses these regexes in JavaScript."""
    patterns = list(config.TAGS.values()) + [r["pattern"] for r in config.RANKING["stack"]]
    patterns += [r["pattern"] for r in config.RANKING["urgency"]]
    for p in patterns:
        assert "(?" not in p and "\\Z" not in p and "(?P" not in p


def test_learning_catalog_is_free_https_and_exported(tmp_path):
    _, data = run(tmp_path, [])
    courses = data["learning"]["courses"]
    assert len(courses) >= 10
    for c in courses:
        assert c["url"].startswith("https://")
        assert {"title", "provider", "topics", "cert", "hours", "why"} <= set(c)
        assert "paid" not in c["cert"].lower() or "exam is paid" in c["cert"].lower()


@pytest.mark.parametrize("title,expected", [
    ("Zapier offers free MCP tool calls until Jan. 5", True),
    ("Anthropic Academy launches 13 free courses with certificates", True),
    ("Google open-sourced its new eval harness for agents", True),
    ("Show HN: AI Engineer Notebooks – free RAG/agents/evals course on Colab", True),
    ("Free tier for Playwright cloud testing is back", True),
    ("A lock-free queue in Rust", False),
    ("Python 3.15 makes free-threading the default on macOS", False),
    ("Feel free to ignore this: notes on pytest fixtures", False),
    ("Hands-free voice control for your IDE", False),
])
def test_free_and_learning_tag_precision(title, expected):
    item = Item(key="k", title=title, url="https://e", source="HN")
    assert ("Free & learning" in tags(item)) is expected


def test_empty_scraped_hn_page_is_reported_as_failed():
    from digest.build import _scraped, collect
    groups, status = collect([("HN · Active", "HN Active", lambda: _scraped([], "Active"))])
    assert status[0]["ok"] is False and "layout may have changed" in status[0]["error"]
    assert groups == [("HN · Active", [])]


def test_telegram_message_lists_headlines():
    msg = format_message({"new_today": 3, "failures": ["x"], "headlines": ["A", "B", "C"]},
                         "https://me.github.io/ai-qa-digest/")
    assert msg.splitlines()[0] == "AI + QA Radar: 3 new today"
    assert "• A" in msg and "source(s) failed" in msg and msg.endswith("/ai-qa-digest/")
