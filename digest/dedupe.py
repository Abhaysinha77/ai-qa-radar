"""Merging duplicates across sources and remembering what was already shown."""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Item

_TRACKING = re.compile(r"^(utm_|ref$|ref_|source$|via$|fbclid|gclid)")


def atomic_write(path: Path, text: str) -> None:
    """Write to a temp file then swap it in, so a reader (the web server, a phone) never sees
    a half-written file and a crash mid-write never corrupts the previous version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, query, ""))


def _norm_title(title: str) -> str:
    title = re.sub(r"^(show|ask|tell|launch) hn:\s*", "", title.lower())
    return re.sub(r"[^a-z0-9 ]+", "", title).strip()


_NUMBERS = re.compile(r"\d+(?:\.\d+)*")


def same_story(a: Item, b: Item, threshold: float = 0.9) -> bool:
    if a.key == b.key:
        return True
    if normalize_url(a.url) == normalize_url(b.url) and "news.ycombinator.com" not in a.url:
        return True
    # "SDK v3.59.0" vs "SDK v3.58.0", "Claude 5.2" vs "Claude 5.1": similar titles, different news
    na, nb = _NUMBERS.findall(a.title), _NUMBERS.findall(b.title)
    if na and nb and na != nb:
        return False
    ta, tb = _norm_title(a.title), _norm_title(b.title)
    if not ta or not tb or abs(len(ta) - len(tb)) > max(len(ta), len(tb)) * (1 - threshold) * 2:
        return False  # cheap length check before the (slow) fuzzy comparison
    return SequenceMatcher(None, ta, tb).ratio() >= threshold


def merge(groups: list[tuple[str, list[Item]]]) -> list[Item]:
    """Groups are in priority order; an item lands in the first group it appears in and
    later sightings are recorded in `also_in` instead of being shown again."""
    kept: list[Item] = []
    for group, items in groups:
        for item in items:
            match = next((k for k in kept if same_story(k, item)), None)
            if match is None:
                item.group = group
                kept.append(item)
                continue
            label = item.source
            if label != match.source and label not in match.also_in:
                match.also_in.append(label)
            # keep the richer numbers / discussion link
            if item.points and (match.points or 0) < item.points:
                match.points, match.comments = item.points, item.comments
            match.discussion_url = match.discussion_url or item.discussion_url
    return kept


class State:
    """state/seen.json  -> {"seen": {key: first_seen}, "items": {key: item-dict}}"""

    def __init__(self, path: Path):
        self.path = path
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if not isinstance(data, dict):
                    raise ValueError("state is not a JSON object")
            except (ValueError, OSError):
                # never let a damaged memory file take the whole app down: keep a copy, start fresh
                path.replace(path.with_name(path.name + ".corrupt"))
                data = {}
        self.seen: dict[str, str] = data.get("seen", {}) or {}
        self.items: dict[str, dict] = data.get("items", {}) or {}

    def _lookup(self, item: Item) -> tuple[str | None, Item | None]:
        """Earliest date this story was shown before (by key, URL or near-identical title)."""
        keys = {item.key, normalize_url(item.url)}
        dates = [self.seen[k] for k in keys if k in self.seen]
        twin = next((Item.from_dict(d) for d in self.items.values()
                     if d["key"] != item.key and same_story(Item.from_dict(d), item)), None)
        if twin is not None:
            dates.append(twin.first_seen)
        return (min(dates) if dates else None), twin

    def is_new(self, item: Item) -> bool:
        return self._lookup(item)[0] is None

    def stamp(self, items: list[Item], today: date, now_iso: str = "") -> None:
        """Give every item a first_seen date; previously shown items keep their old date
        (matched by key, by URL, or by a near-identical title of an archived item)."""
        for item in items:
            keys = {item.key, normalize_url(item.url)}
            earlier, twin = self._lookup(item)
            first = earlier or today.isoformat()
            item.first_seen = first
            for k in keys:
                self.seen.setdefault(k, first)
            stored = self.items.get(twin.key if twin else item.key)
            if stored is not None:
                # already on the page: only refresh the numbers, never re-add it
                if item.points and (stored.get("points") or 0) < item.points:
                    stored["points"], stored["comments"] = item.points, item.comments
            elif first == today.isoformat():
                item.found_at = now_iso or today.isoformat()
                self.items[item.key] = item.to_dict()

    def recent(self, today: date, days: int) -> list[Item]:
        cutoff = (today - timedelta(days=days)).isoformat()
        return [Item.from_dict(d) for d in self.items.values() if d.get("first_seen", "") >= cutoff]

    def prune(self, today: date, seen_days: int, item_days: int) -> None:
        seen_cut = (today - timedelta(days=seen_days)).isoformat()
        item_cut = (today - timedelta(days=item_days)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v >= seen_cut}
        self.items = {k: v for k, v in self.items.items() if v.get("first_seen", "") >= item_cut}

    def save(self, last_build: str = "") -> None:
        """`last_build` changes on every run, so the daily workflow always commits. That
        commit counts as repository activity and stops GitHub from switching off the
        schedule after 60 quiet days."""
        atomic_write(self.path, json.dumps({"last_build": last_build, "seen": self.seen,
                                            "items": self.items}, indent=1, sort_keys=True))
