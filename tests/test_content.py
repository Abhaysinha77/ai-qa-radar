"""Article reading, quoted (extractive) summaries, diagrams and trends — offline."""
import json
from datetime import date, datetime, timezone

from digest import config
from digest.article import parse
from digest.build import build
from digest.extractive import sentences, summarize
from digest.models import Item
from digest.summarize import summarise
from digest.trends import extract_terms, trending, update_history

ARTICLE = """<html><head><meta property="og:image" content="https://cdn.example/cover.png"></head><body>
<nav><p>Home Blog About Contact Subscribe to our newsletter today</p></nav>
<article><h1>How we test our MCP server with pytest</h1>
<p>Our team builds an MCP server that exposes 14 tools to coding agents, and we needed a reliable way to test it.</p>
<h2>Why classic tests were not enough</h2>
<p>Unit tests checked each tool in isolation, but agents called the tools in unexpected orders. Flaky failures appeared in CI about twice a week.</p>
<figure><img src="/img/architecture-diagram.png" alt="Architecture of the test harness" width="900"><figcaption>Test harness architecture</figcaption></figure>
<img src="https://cdn.example/author-avatar.png" alt="author avatar" width="64">
<img src="http://insecure.example/flow-diagram.png" alt="flow diagram">
<h2>The harness</h2>
<p>We wrote a pytest plugin that replays recorded agent sessions against the server. Each session is a JSON file with the tool calls and expected results.</p>
<p>The plugin runs 300 recorded sessions in under two minutes on GitHub Actions.</p>
<h2>Results</h2>
<p>Flaky failures dropped from two a week to zero over three months. We also caught a prompt injection bug where a tool result contained hidden instructions.</p>
<p>Subscribe to our newsletter for more posts like this.</p>
</article><footer><p>© 2026 Example Inc. All rights reserved.</p></footer></body></html>"""


def test_parse_sections_images_cover_and_boilerplate():
    got = parse(ARTICLE, "https://blog.example/post")
    headings = [s["heading"] for s in got["sections"]]
    assert headings == ["", "Why classic tests were not enough", "The harness", "Results"]
    assert got["cover"] == "https://cdn.example/cover.png"
    # only the real https diagram, with its caption; avatar and http image are rejected
    assert got["images"] == [{"src": "https://blog.example/img/architecture-diagram.png", "alt": "Test harness architecture"}]
    assert "newsletter" not in got["text"] and "rights reserved" not in got["text"]
    assert got["words"] > 80


def test_extractive_summary_is_quoted_word_for_word_and_covers_every_section():
    got = parse(ARTICLE, "https://blog.example/post")
    out = summarize(got["sections"], "How we test our MCP server with pytest")
    for s in sentences(out["summary"]):
        assert s in got["text"], f"invented sentence: {s}"           # nothing is rewritten
    for kp in out["key_points"]:
        assert kp["point"] in got["text"]
    assert [k["heading"] for k in out["key_points"]] == ["Why classic tests were not enough", "The harness", "Results"]
    assert out["outline"] == ["Why classic tests were not enough", "The harness", "Results"]
    assert len(out["summary"].split()) <= 260
    assert "14 tools" in out["summary"]                                 # keeps exact numbers


def test_extractive_handles_empty_and_repeated_text():
    assert summarize([], "x") == {"summary": "", "key_points": [], "outline": []}
    rep = [{"heading": "", "paras": ["The same sentence about pytest fixtures is here. " * 30]}]
    out = summarize(rep, "x")
    assert out["summary"].count("The same sentence") == 1


def test_summarise_fills_everything_from_html():
    item = Item(key="k", title="How we test our MCP server with pytest", url="https://blog.example/post", source="Blog")
    summarise(item, ask=None, get_html=lambda i: [ARTICLE])
    assert item.summary_kind == "extractive" and item.summary
    assert len(item.key_points) == 3 and item.outline and item.images and item.read_minutes >= 1


def test_ai_summary_used_when_available_but_points_stay_quoted():
    item = Item(key="k", title="T", url="https://blog.example/post", source="Blog")
    summarise(item, ask=lambda p: "A careful AI summary. Why it matters for QA: yes.", get_html=lambda i: [ARTICLE])
    assert item.summary_kind == "ai" and item.summary.startswith("A careful AI summary")
    parsed_text = parse(ARTICLE, "https://blog.example/post")["text"]
    assert all(k["point"] in parsed_text for k in item.key_points)


def test_extract_terms_glossary_acronyms_versions_and_stoplist():
    terms = extract_terms("OpenAI ships GPT-6.2 with A2A support and OpenTelemetry tracing for AI agents",
                          "Prompt injection remains the main risk.")
    assert "A2A (Agent2Agent)" in terms and "Prompt injection" in terms and "AI agent" in terms
    assert "GPT-6.2" in terms and "OpenTelemetry" in terms
    assert "AI" not in terms and "API" not in terms


def test_trending_marks_new_rising_and_active():
    hist = {}
    for d, items in {
        date(2026, 10, 1): [{"key": "a", "first_seen": "2026-10-01", "terms": ["MCP (Model Context Protocol)"]}],
        date(2026, 10, 8): [{"key": "b", "first_seen": "2026-10-08", "terms": ["MCP (Model Context Protocol)"]}],
    }.items():
        hist = update_history(hist, items, d)
    today = date(2026, 11, 26)
    week = [{"key": f"n{i}", "first_seen": "2026-11-26", "terms": ["MCP (Model Context Protocol)", "Fable 5.2"]} for i in range(4)]
    hist = update_history(hist, week, today)
    out = {t["term"]: t for t in trending(hist, week, today)}
    assert out["Fable 5.2"]["status"] == "new" and out["Fable 5.2"]["count"] == 4
    assert out["MCP (Model Context Protocol)"]["status"] == "rising"
    assert out["MCP (Model Context Protocol)"]["definition"]          # glossary definition attached
    assert out["Fable 5.2"]["examples"][:2] == ["n0", "n1"]


def test_history_is_pruned_and_today_is_recomputed_not_double_counted():
    hist = {"2026-01-01": {"old": 9}}
    items = [{"key": "a", "first_seen": "2026-11-26", "terms": ["X1"]}]
    hist = update_history(hist, items, date(2026, 11, 26))
    hist = update_history(hist, items, date(2026, 11, 26))           # second run same day
    assert "2026-01-01" not in hist and hist["2026-11-26"] == {"X1": 1}


def test_build_exports_trends_glossary_resources_and_terms(tmp_path):
    item = Item(key="hn:1", title="Prompt injection found in a popular MCP server", url="https://e/1",
                source="HN", html=ARTICLE)
    build(tmp_path / "site", tmp_path / "seen.json", now=datetime(2026, 11, 26, 6, tzinfo=timezone.utc),
          groups=[("Topic · AI security", [item])], status=[], offline=True)
    data = json.loads((tmp_path / "site" / "data.json").read_text())
    assert data["glossary"] and data["resources"] and isinstance(data["trends"], list)
    it = data["items"][0]
    assert "Prompt injection" in it["terms"] and it["key_points"] and it["images"]
    assert "html" not in it and "body" not in it


def test_glossary_and_resources_are_well_formed():
    import re
    for g in config.GLOSSARY:
        assert g["term"] and len(g["def"]) > 20 and re.compile(g["match"], re.I)
        assert "(?" not in g["match"]
    names = [r["name"] for r in config.RESOURCES]
    assert len(names) == len(set(names))
    assert all(r["url"].startswith("https://") and r["about"] for r in config.RESOURCES)


def test_backfill_upgrades_stories_collected_before_the_full_reader(tmp_path):
    """Old archive items (no key points) get the full briefing on the next run, once."""
    import json as _json
    from digest.dedupe import State
    state_path = tmp_path / "seen.json"
    st = State(state_path)
    old = Item(key="hn:9", title="How we test our MCP server with pytest", url="https://blog.example/post",
               source="HN", summary="Short old excerpt.", summary_kind="excerpt", first_seen="2026-11-25",
               found_at="2026-11-25T08:00")
    st.seen = {"hn:9": "2026-11-25"}
    st.items = {"hn:9": old.to_dict()}
    st.save("x")
    pages = {"https://blog.example/post": ARTICLE}
    from unittest import mock
    from digest import summarize as summ
    with mock.patch.object(summ, "fetch", lambda url, *a, **k: pages.get(url) or (_ for _ in ()).throw(RuntimeError("404"))):
        build(tmp_path / "site", state_path, now=datetime(2026, 11, 26, 6, tzinfo=timezone.utc), groups=[], status=[])
    item = _json.loads((tmp_path / "site" / "data.json").read_text())["items"][0]
    assert item["enriched"] and item["key_points"] and item["outline"] and item["summary_kind"] == "extractive"


def test_discussion_highlights_are_quoted_substantive_and_capped():
    from digest.summarize import discussion_highlights
    thread = {"children": [{"text": "<p>Too short.</p>"},
                           {"text": "<p>" + "We tried this approach in production and the flaky tests dropped a lot. " * 3 + "</p>"},
                           {"text": "[dead]"},
                           {"text": "<p>" + "Another detailed comment explaining how the harness replays agent sessions reliably. " * 4 + "</p>"}]}
    out = discussion_highlights(thread)
    assert len(out) == 2 and all(len(q.split()) <= 91 for q in out)
    assert discussion_highlights(None) == []


def test_blocked_site_gets_a_clear_reason_and_keeps_old_summary():
    item = Item(key="hn:5", title="T", url="https://blocked.example/a", source="HN")
    from unittest import mock
    from digest import summarize as summ
    with mock.patch.object(summ, "fetch", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("403"))):
        summarise(item)
    assert item.summary == "" and "blocked" in item.no_text_reason
    kept = Item(key="hn:6", title="T", url="https://blocked.example/b", source="HN", summary="Old text.", summary_kind="excerpt")
    with mock.patch.object(summ, "fetch", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("403"))):
        summarise(kept)
    assert kept.summary == "Old text."
