"""QA suite: unit, negative and edge-case tests (offline). Each test names the risk it covers."""
import json
import random
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import pytest

from digest import config
from digest.dedupe import State, merge, normalize_url, same_story
from digest.models import Item
from digest.notify import format_message, send_telegram
from digest.rank import score, tags
from digest.sources import parse_algolia, parse_feed, parse_hf_papers, parse_hn_list
from digest.summarize import SKIP_FETCH, cap_words, excerpt, html_to_text, summarise

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)


def it(title, key=None, url=None, **kw):
    return Item(key=key or title, title=title, url=url or f"https://e/{abs(hash(title))}", source="s", **kw)


# =========================================================== feed parser (negative/edge)
def test_malformed_feed_raises_so_the_source_is_reported_failed():
    with pytest.raises(ET.ParseError):
        parse_feed("<rss><channel><item><title>broken", "X", now=NOW)


def test_html_page_instead_of_feed_raises():
    with pytest.raises(ET.ParseError):
        parse_feed("<!doctype html><html><body><p>Not a feed<br></body></html>", "X", now=NOW)


def test_empty_feed_returns_nothing():
    assert parse_feed("<rss><channel></channel></rss>", "X", now=NOW) == []


def test_entries_without_title_or_link_are_skipped():
    rss = ("<rss><channel><item><title></title><link>https://a</link></item>"
           "<item><title>No link</title></item>"
           "<item><title>Good</title><link>https://b</link></item></channel></rss>")
    assert [i.title for i in parse_feed(rss, "X", now=NOW)] == ["Good"]


def test_unicode_and_entities_survive():
    rss = ("<rss><channel><item><title>Ünïcödé &amp; emojis 🚀 — “quotes”</title>"
           "<link>https://a</link></item></channel></rss>")
    assert parse_feed(rss, "X", now=NOW)[0].title == "Ünïcödé & emojis 🚀 — “quotes”"


def test_unparseable_date_keeps_item_without_date():
    rss = "<rss><channel><item><title>T</title><link>https://a</link><pubDate>not a date</pubDate></item></channel></rss>"
    item = parse_feed(rss, "X", now=NOW)[0]
    assert item.published is None


def test_limit_and_only_filters_are_respected():
    entries = "".join(f"<item><title>pytest tip {n}</title><link>https://a/{n}</link></item>" for n in range(10))
    entries += "<item><title>Cooking pasta</title><link>https://a/x</link></item>"
    items = parse_feed(f"<rss><channel>{entries}</channel></rss>", "X", only="pytest", limit=3, now=NOW)
    assert len(items) == 3 and all("pytest" in i.title for i in items)


def test_atom_prefers_alternate_link_over_self_and_replies():
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title>'
            '<link rel="replies" href="https://x/replies"/><link rel="self" href="https://x/self"/>'
            '<link rel="alternate" href="https://x/post"/><updated>2026-11-25T00:00:00Z</updated></entry></feed>')
    assert parse_feed(atom, "X", now=NOW)[0].url == "https://x/post"


def test_script_in_feed_body_is_not_kept_as_markup():
    rss = ("<rss><channel><item><title>T</title><link>https://a</link>"
           "<description>&lt;script&gt;alert(1)&lt;/script&gt;&lt;p&gt;Hi&lt;/p&gt;</description></item></channel></rss>")
    body = parse_feed(rss, "X", now=NOW)[0].body
    assert "<script>" not in body and "Hi" in body


# ============================================================ HN / Algolia / HF parsers
def test_hn_list_handles_empty_page_jobs_rows_and_big_numbers():
    assert parse_hn_list("", "Front page") == []
    html = ('<table><tr class="athing" id="9"><td><span class="titleline"><a href="https://j">YC startup is hiring</a></span></td></tr>'
            '<tr><td class="subtext"><span class="age">1 hour ago</span></td></tr>'
            '<tr class="athing" id="10"><td><span class="titleline"><a href="https://k">Big</a></span></td></tr>'
            '<tr><td class="subtext"><span class="score" id="score_10">1,234 points</span><a href="item?id=10">2,345&nbsp;comments</a></td></tr></table>')
    items = parse_hn_list(html, "Front page")
    assert items[0].points is None and items[0].comments is None
    assert items[1].points == 1234 and items[1].comments == 2345


def test_hn_title_markup_is_text_only():
    html = '<tr class="athing" id="1"><td><span class="titleline"><a href="https://x">&lt;img src=x onerror=alert(1)&gt;</a></span></td></tr>'
    assert parse_hn_list(html, "S")[0].title == "<img src=x onerror=alert(1)>"  # raw text; the app escapes it


def test_algolia_skips_broken_hits_and_falls_back_to_discussion_url():
    data = {"hits": [{"objectID": "1"}, {"title": "No id"}, {"objectID": "2", "title": "Ask HN: x", "url": None}]}
    items = parse_algolia(data, "T")
    assert [i.key for i in items] == ["hn:2"] and items[0].url.endswith("item?id=2")
    assert parse_algolia({}, "T") == []


def test_hf_papers_accepts_dict_form_and_ignores_garbage():
    assert parse_hf_papers({"papers": [{"id": "1", "title": "Agent eval"}]})[0].key == "hf:1"
    assert parse_hf_papers({"unexpected": True}) == []
    assert parse_hf_papers([{"paper": {"title": "no id"}}]) == []


# ================================================================== dedupe
@pytest.mark.parametrize("a,b,same", [
    ("OpenAI Python SDK v3.59.0", "OpenAI Python SDK v3.58.0", False),   # different versions
    ("Claude Fable 5.2 and Mythos 5.2", "Claude Fable 5.1 and Mythos 5.1", False),
    ("Python 3.15.0 released", "Python 3.15.1 released", False),
    ("Show HN: Rustwright – Playwright in Rust", "Rustwright - Playwright in Rust", True),
    ("MCP Explained", "MCP explained!", True),
])
def test_same_story_never_merges_different_versions(a, b, same):
    assert same_story(it(a), it(b)) is same


def test_normalize_url_is_idempotent_and_keeps_meaningful_query():
    u = "HTTPS://WWW.Example.com/Path/?b=2&utm_medium=x&a=1"
    once = normalize_url(u)
    assert normalize_url(once) == once and "b=2" in once and "a=1" in once and "utm" not in once
    assert "/Path" in once  # path case is significant


def test_merge_handles_empty_and_single_inputs():
    assert merge([]) == [] and merge([("g", [])]) == []
    assert len(merge([("g", [it("Only one")])])) == 1


def test_merge_same_source_twice_does_not_add_self_to_also_in():
    a, b = it("Same", key="hn:1"), it("Same", key="hn:1")
    merged = merge([("g1", [a]), ("g2", [b])])
    assert merged[0].also_in == []


# =================================================================== state
def test_corrupted_state_file_is_recovered_not_fatal(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{not json")
    s = State(path)
    assert s.seen == {} and s.items == {}
    assert (tmp_path / "seen.json.corrupt").exists()  # kept for inspection


def test_state_save_creates_missing_folders(tmp_path):
    s = State(tmp_path / "a" / "b" / "seen.json")
    s.save("x")
    assert json.loads((tmp_path / "a" / "b" / "seen.json").read_text())["last_build"] == "x"


def test_new_version_next_day_is_new_even_though_title_is_similar(tmp_path):
    s = State(tmp_path / "seen.json")
    s.stamp([Item(key="rel:SDK:v3.58.0", title="OpenAI Python SDK v3.58.0", url="https://g/1", source="SDK")],
            date(2026, 11, 25))
    nxt = Item(key="rel:SDK:v3.59.0", title="OpenAI Python SDK v3.59.0", url="https://g/2", source="SDK")
    assert s.is_new(nxt)


# ================================================================= ranking
def test_quadrant_boundaries_are_inclusive():
    r = dict(config.RANKING)
    # craft rules so the scores land exactly on the thresholds
    r = {**r, "stack": [{"pattern": "edge", "weight": r["act_importance"]}],
         "urgency": [{"label": "U", "pattern": "edge", "weight": r["act_urgency"]}],
         "fresh_boost": 0, "official_boost": 0}
    out = score(it("edge case"), now=NOW, rules=r)
    assert (out["importance"], out["urgency"], out["quadrant"]) == (r["act_importance"], r["act_urgency"], "Act now")
    r2 = {**r, "stack": [{"pattern": "edge", "weight": r["act_importance"] - 1}]}
    assert score(it("edge case"), now=NOW, rules=r2)["quadrant"] == "Watch"


@pytest.mark.parametrize("published", [None, "", "garbage", "2030-01-01T00:00:00Z", "2026-11-26"])
def test_bad_or_future_dates_do_not_crash_scoring(published):
    out = score(it("pytest breaking change", published=published, points=50), now=NOW)
    assert 0 <= out["importance"] <= 100 and 0 <= out["urgency"] <= 100


def test_fuzz_scores_always_bounded_and_quadrant_valid():
    rng = random.Random(7)
    words = ["pytest", "MCP", "security", "breaking", "agents", "free", "release", "outage", "lol", "", "🚀",
             "Claude", "<script>", "x" * 500]
    for _ in range(500):
        title = " ".join(rng.choice(words) for _ in range(rng.randint(0, 8)))
        item = Item(key="k", title=title, url="https://e", source="s",
                    group=rng.choice(["Releases", "Official updates", "HN · Active", "Topic · MCP", ""]),
                    points=rng.choice([None, 0, 1, 10, 10_000, 10**9]), also_in=["a"] * rng.randint(0, 5))
        out = score(item, now=NOW)
        assert 0 <= out["importance"] <= 100 and 0 <= out["urgency"] <= 100
        assert out["quadrant"] in {"Act now", "Plan", "Watch", "FYI"}


def test_tags_are_case_insensitive_and_empty_title_has_none():
    assert "pytest" in tags(it("PYTEST 9 IS OUT"))
    assert tags(it("")) == []


# ================================================================ summaries
def test_cap_words_boundaries():
    assert cap_words("w " * 200).endswith("w") and len(cap_words("w " * 200).split()) == 200
    capped = cap_words("w " * 201)
    assert capped.endswith("…") and len(capped.split()) == 200
    assert cap_words("") == ""


def test_excerpt_handles_no_punctuation_and_whitespace_only():
    assert len(excerpt("word " * 500, 80).split()) <= 80
    assert excerpt("   ") == ""


def test_html_to_text_on_empty_and_scriptonly_pages():
    assert html_to_text("") == ""
    assert "alert" not in html_to_text("<script>alert(1)</script>")


@pytest.mark.parametrize("url,skip", [
    ("https://www.dropbox.com/s/file", False),       # contains "x.com/" but is not x.com
    ("https://x.com/someone/status/1", True),
    ("https://twitter.com/a/status/1", True),
    ("https://example.com/paper.pdf", True),
    ("https://example.com/post", False),
])
def test_skip_fetch_only_matches_real_hosts(url, skip):
    assert bool(SKIP_FETCH.search(url)) is skip


def test_empty_ai_answer_falls_back_to_quoted_summary():
    item = it("T", body="Real article text about pytest fixtures. " * 20)
    summarise(item, ask=lambda p: "   ", get_text=lambda i: i.body)
    assert item.summary and item.summary_kind == "extractive"


def test_no_text_and_no_ai_leaves_summary_empty_not_crash():
    item = it("T")
    summarise(item, ask=None, get_text=lambda i: "")
    assert item.summary == ""


# ================================================================== notify
def test_telegram_only_sends_in_configured_half_hour(monkeypatch=None):
    import os
    os.environ.update({"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c", "NOTIFY_HOUR_UTC": "2"})
    try:
        summary = {"new_today": 1, "headlines": ["A"], "failures": []}
        assert send_telegram(summary, now=datetime(2026, 11, 26, 3, 0, tzinfo=timezone.utc)) is False
        assert send_telegram(summary, now=datetime(2026, 11, 26, 2, 45, tzinfo=timezone.utc)) is False
        assert send_telegram({**summary, "new_today": 0}, now=datetime(2026, 11, 26, 2, 5, tzinfo=timezone.utc)) is False
    finally:
        for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "NOTIFY_HOUR_UTC"):
            os.environ.pop(k, None)


def test_telegram_message_without_page_url_or_headlines():
    msg = format_message({"new_today": 0}, "")
    assert msg == "Kairoq: 0 new today"


# ================================================================== config
def test_config_sanity():
    names = [n for n, *_ in config.RELEASE_FEEDS + config.OFFICIAL_FEEDS + config.BLOG_FEEDS]
    assert len(names) == len(set(names)), "duplicate source names make the Sources table ambiguous"
    for _, url, *_ in config.RELEASE_FEEDS + config.OFFICIAL_FEEDS + config.BLOG_FEEDS + config.RESEARCH_FEEDS:
        assert url.startswith("https://")
    assert {t[0] for t in config.TOPICS}.isdisjoint({""})
    assert config.RANKING["act_urgency"] <= 100 and config.RANKING["act_importance"] <= 100
