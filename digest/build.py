"""Collector: fetch every source, merge duplicates, rank, summarise, and write the web app's
data (site/data.json) next to the app files from web/.

    python -m digest                      # uses the network
    python -m digest --out site --state state/seen.json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config
from .dedupe import State, atomic_write, merge
from .models import Item
from .notify import send_telegram
from .rank import score, tags
from .sources import (algolia_url, fetch, parse_algolia, parse_feed, parse_hf_papers,
                      parse_hn_bestcomments, parse_hn_list)
from .summarize import provider, summarise_all

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _relevant(items: list[Item]) -> list[Item]:
    return [i for i in items if re.search(config.RELEVANT, i.title)]


def _scraped(items: list[Item], label: str) -> list[Item]:
    """A scraped HN page always lists stories. Zero rows means the page layout changed or we
    were blocked, so report the source as failed instead of silently showing nothing."""
    if not items:
        raise RuntimeError(f"0 stories parsed from {label} — page layout may have changed")
    return _relevant(items)


def _jobs(since_ts: int) -> list[tuple[str, str, object]]:
    """(group, source label, callable -> list[Item]) in page priority order."""
    jobs: list[tuple[str, str, object]] = []
    for name, url, skip in config.RELEASE_FEEDS:
        jobs.append(("Releases", name, lambda u=url, n=name, s=skip: parse_feed(
            fetch(u), n, skip=s, limit=config.RELEASES_PER_FEED,
            max_age_days=config.RELEASE_MAX_AGE_DAYS, kind="release")))
    for name, url, only in config.OFFICIAL_FEEDS:
        jobs.append(("Official updates", name, lambda u=url, n=name, o=only: parse_feed(
            fetch(u), n, only=o, limit=config.POSTS_PER_FEED, max_age_days=config.FEED_MAX_AGE_DAYS)))
    for name, url, only in config.BLOG_FEEDS:
        jobs.append(("Practitioner blogs", name, lambda u=url, n=name, o=only: parse_feed(
            fetch(u), n, only=o, limit=config.POSTS_PER_FEED, max_age_days=config.FEED_MAX_AGE_DAYS)))
    for name, url, only in config.RESEARCH_FEEDS:
        jobs.append(("Research", name, lambda u=url, n=name, o=only: parse_feed(
            fetch(u), n, only=o, limit=config.RESEARCH_PER_FEED, max_age_days=4)))
    jobs.append(("Research", "HF Daily Papers", lambda: parse_hf_papers(
        json.loads(fetch(config.HF_DAILY_PAPERS)), config.HF_FILTER, config.RESEARCH_PER_FEED)))
    # topic searches before HN sections so a story lands in its most specific place
    for topic, queries, min_points, exclude in config.TOPICS:
        for query in queries:
            jobs.append((f"Topic · {topic}", f"HN search “{query}”",
                         lambda q=query, t=topic, p=min_points, e=exclude: parse_algolia(
                             json.loads(fetch(algolia_url(q, since_ts, p))), t, e)))
    for section, url in config.HN_SECTIONS:
        jobs.append((f"HN · {section}", f"HN {section}",
                     lambda u=url, s=section: _scraped(parse_hn_list(fetch(u), s), s)))
    jobs.append(("HN · Best comments", "HN Best comments",
                 lambda: _scraped(parse_hn_bestcomments(fetch(config.HN_BEST_COMMENTS)), "Best comments")))
    return jobs


def group_order() -> list[str]:
    order = ["Releases", "Official updates", "Practitioner blogs", "Research"]
    order += [f"Topic · {t[0]}" for t in config.TOPICS]
    order += [f"HN · {s}" for s, _ in config.HN_SECTIONS] + ["HN · Best comments"]
    return order


def collect(jobs) -> tuple[list[tuple[str, list[Item]]], list[dict]]:
    def run(job):
        group, label, fn = job
        try:
            items = fn()
            return group, items, {"name": label, "group": group, "ok": True, "count": len(items)}
        except Exception as exc:  # one bad source must never break the build
            return group, [], {"name": label, "group": group, "ok": False, "count": 0,
                               "error": f"{type(exc).__name__}: {str(exc)[:120]}"}

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, jobs))  # map keeps priority order
    groups: dict[str, list[Item]] = {}
    status = []
    for group, items, info in results:
        groups.setdefault(group, []).extend(items)
        status.append(info)
    return list(groups.items()), status


def build(out_dir: Path, state_path: Path, now: datetime | None = None,
          groups: list[tuple[str, list[Item]]] | None = None,
          status: list[dict] | None = None, ask=None, offline: bool = False) -> dict:
    """`groups`/`status`/`ask` can be injected for offline tests (`ask` = fake LLM);
    `offline=True` summarises only from text already in the feeds."""
    tz = ZoneInfo(config.TIMEZONE)
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    today = now.date()
    if groups is None:
        since = int((now - timedelta(hours=config.HN_TOPIC_WINDOW_HOURS)).timestamp())
        groups, status = collect(_jobs(since))
    status = status or []

    items = merge(groups)
    state = State(state_path)
    # Hacker News groups show at most MAX_PER_GROUP new stories PER DAY (runs every 30 min must
    # not keep topping them up). Feeds are already limited per source, so they are never capped.
    fresh: dict[str, list[Item]] = {}
    for item in items:
        if state.is_new(item):
            fresh.setdefault(item.group, []).append(item)
    shown_today: dict[str, int] = {}
    for d in state.items.values():
        if d.get("first_seen") == today.isoformat():
            shown_today[d.get("group", "")] = shown_today.get(d.get("group", ""), 0) + 1
    chosen: list[Item] = []
    for group, group_items in fresh.items():
        group_items.sort(key=lambda x: x.points or 0, reverse=True)
        if group.startswith(("HN ·", "Topic ·")):
            group_items = group_items[:max(0, config.MAX_PER_GROUP - shown_today.get(group, 0))]
        chosen += group_items
    summarised = summarise_all(chosen, config.MAX_SUMMARIES_PER_RUN, ask=ask,
                               get_text=(lambda i: i.body) if offline else None)
    already = [i for i in items if not state.is_new(i)]
    state.stamp(chosen + already, today, now_iso=now.astimezone(timezone.utc).isoformat(timespec="minutes"))
    state.prune(today, config.SEEN_RETENTION_DAYS, config.ARCHIVE_DAYS)

    page_items = state.recent(today, config.ARCHIVE_DAYS)
    for item in page_items:  # re-score every run: votes and age change
        item.tags = tags(item)
        item.__dict__.update(score(item, now=now.astimezone(timezone.utc)))
        item.action = item.quadrant in ("Act now", "Watch")
        state.items[item.key] = item.to_dict()
    page_items.sort(key=lambda i: (i.first_seen, i.hot), reverse=True)

    data = {
        "generated": now.isoformat(timespec="minutes"),
        "today": today.isoformat(),
        "summaries": "ai" if (provider() or ask) else "excerpt",
        "groups": group_order(),
        "tags": config.TAGS,
        "tag_exclude": config.TAG_EXCLUDE,
        "ranking": config.RANKING,
        "live": {"topics": [{"topic": t, "queries": q, "min_points": p, "exclude": e}
                            for t, q, p, e in config.TOPICS],
                 "relevant": config.RELEVANT.replace("(?i)", "")},
        "check_pages": [{"name": n, "url": u} for n, u in config.CHECK_PAGES],
        "learning": {"courses": config.LEARNING, "checked": config.LEARNING_CHECKED},
        "sources": status,
        "items": [i.to_dict() for i in page_items],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    if WEB_DIR.exists():
        shutil.copytree(WEB_DIR, out_dir, dirs_exist_ok=True)
    atomic_write(out_dir / "data.json", json.dumps(data, ensure_ascii=False))
    state.save(last_build=now.isoformat(timespec="minutes"))

    new = [i for i in page_items if i.first_seen == today.isoformat()]
    failures = [s["name"] for s in status if not s["ok"]]
    return {"new_today": len(new), "on_page": len(page_items), "fetched": len(items),
            "summarised": summarised, "failures": failures,
            "headlines": [i.title for i in sorted(new, key=lambda x: -x.hot)]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect, rank and publish the AI + QA digest")
    parser.add_argument("--out", default="site", type=Path)
    parser.add_argument("--state", default="state/seen.json", type=Path)
    args = parser.parse_args(argv)
    summary = build(args.out, args.state)
    send_telegram(summary)  # no-op unless TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set
    print(json.dumps({k: v for k, v in summary.items() if k != "headlines"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
