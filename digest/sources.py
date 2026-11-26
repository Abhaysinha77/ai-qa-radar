"""Parsers for each kind of source. Network calls live in fetch(); parsers are pure
functions so they can be unit-tested offline."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from . import config
from .models import Item

HN = "https://news.ycombinator.com/"
_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT


def fetch(url: str, retries: int = 2, timeout: int = 25) -> str:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = _session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:  # pragma: no cover - network
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


# ------------------------------------------------------------------ feeds
def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            when = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _entries(text: str) -> list[dict]:
    """Minimal RSS 2.0 / Atom reader (stdlib only)."""
    root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    for el in root.iter():  # drop namespaces: {http://www.w3.org/2005/Atom}entry -> entry
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    out = []
    for node in [*root.iter("entry"), *root.iter("item")]:
        link = ""
        for ln in node.findall("link"):
            href = ln.get("href") or (ln.text or "").strip()
            if href and ln.get("rel", "alternate") == "alternate":
                link = href
                break
        date_text = next((node.findtext(t) for t in ("published", "updated", "pubDate", "date")
                          if node.findtext(t)), None)
        raw = next((node.findtext(t) for t in ("content", "encoded", "summary", "description")
                    if node.findtext(t)), "") or ""
        body = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True) if raw else ""
        out.append({"title": (node.findtext("title") or "").strip(), "link": link,
                    "date": _parse_date(date_text), "body": body})
    return out


def parse_feed(text: str, name: str, *, skip: str | None = None, only: str | None = None,
               limit: int = 3, max_age_days: int = 14, kind: str = "post",
               now: datetime | None = None) -> list[Item]:
    now = now or datetime.now(timezone.utc)
    items: list[Item] = []
    for entry in _entries(text):
        title = entry["title"]
        link = entry["link"]
        if not title or not link:
            continue
        if skip and re.search(skip, title):
            continue
        if only and not re.search(only, title):
            continue
        when = entry["date"]
        if when and now - when > timedelta(days=max_age_days):
            continue
        if kind == "release":
            key = f"rel:{name}:{title}"
            shown = f"{name} {title}" if name.lower() not in title.lower() else title
        else:
            key = link
            shown = title
        items.append(Item(key=key, title=shown, url=link, source=name,
                          published=when.date().isoformat() if when else None,
                          body=entry["body"]))
        if len(items) >= limit:
            break
    return items


# ------------------------------------------------------------ hacker news
def _int(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"\d+", text.replace(",", ""))
    return int(match.group()) if match else None


def parse_hn_list(html: str, section: str) -> list[Item]:
    """Parse a news.ycombinator.com listing page (news, best, show, ask, active...)."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[Item] = []
    for row in soup.select("tr.athing"):
        item_id = row.get("id")
        link = row.select_one("span.titleline > a")
        if not item_id or link is None:
            continue
        sub = row.find_next_sibling("tr")
        points = comments = None
        if sub is not None:
            score = sub.select_one(f"#score_{item_id}")
            points = _int(score.get_text()) if score else None
            for a in sub.find_all("a"):
                txt = a.get_text(" ", strip=True)
                if "comment" in txt:
                    comments = _int(txt)
        discussion = urljoin(HN, f"item?id={item_id}")
        url = urljoin(HN, link.get("href", ""))
        items.append(Item(key=f"hn:{item_id}", title=link.get_text(" ", strip=True), url=url,
                          source=section, points=points, comments=comments,
                          discussion_url=discussion))
    return items


def parse_hn_bestcomments(html: str) -> list[Item]:
    """Return the stories that the most-upvoted comments were posted on."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    items: list[Item] = []
    for a in soup.select("span.onstory a"):
        match = re.search(r"item\?id=(\d+)", a.get("href", ""))
        if not match or match.group(1) in seen:
            continue
        story_id = match.group(1)
        seen.add(story_id)
        title = a.get("title") or a.get_text(" ", strip=True)
        url = urljoin(HN, f"item?id={story_id}")
        items.append(Item(key=f"hn:{story_id}", title=title, url=url, source="Best comments",
                          discussion_url=url))
    return items


def parse_hf_papers(data, only: str | None = None, limit: int = 4) -> list[Item]:
    """Hugging Face Daily Papers JSON (tolerant of small format changes)."""
    items: list[Item] = []
    for row in data if isinstance(data, list) else data.get("papers", []):
        paper = row.get("paper", row)
        title = (paper.get("title") or "").strip()
        pid = paper.get("id")
        if not title or not pid or (only and not re.search(only, title)):
            continue
        items.append(Item(key=f"hf:{pid}", title=title, url=f"https://huggingface.co/papers/{pid}",
                          source="HF Daily Papers", points=paper.get("upvotes"),
                          published=(row.get("publishedAt") or "")[:10] or None,
                          body=paper.get("summary") or ""))
        if len(items) >= limit:
            break
    return items


def algolia_url(query: str, since_ts: int, min_points: int, hits: int = 10) -> str:
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{since_ts},points>={min_points}",
        "hitsPerPage": hits,
        "attributesToRetrieve": "title,url,points,num_comments,created_at",
    }
    return "https://hn.algolia.com/api/v1/search?" + urlencode(params)


def parse_algolia(data: dict, topic: str, exclude: str | None = None) -> list[Item]:
    items: list[Item] = []
    for hit in data.get("hits", []):
        title = hit.get("title") or ""
        object_id = hit.get("objectID")
        if not title or not object_id:
            continue
        if exclude and re.search(exclude, title):
            continue
        discussion = urljoin(HN, f"item?id={object_id}")
        items.append(Item(key=f"hn:{object_id}", title=title, url=hit.get("url") or discussion,
                          source=f"HN · {topic}", points=hit.get("points"),
                          comments=hit.get("num_comments"), discussion_url=discussion,
                          published=(hit.get("created_at") or "")[:10] or None))
    return items
