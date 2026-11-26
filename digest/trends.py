"""Find the terms, tools and models that are NEW or RISING across everything collected.

Terms come from two places: the hand-written glossary (known concepts like "prompt injection")
and automatic detection of acronyms, CamelCase names and versioned names ("GPT-6.2", "Fable 5.2",
"OpenTelemetry"). Daily counts are kept for 60 days, so "new" means "not seen before this week".
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from . import config

ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,6}(?:-[A-Z0-9]{1,4})?\b")
CAMEL = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b")
VERSIONED = re.compile(r"\b[A-Z][A-Za-z]{1,15}[- ]\d+(?:\.\d+)?(?:[- ][A-Z][a-z]+)?\b")
_GLOSS = [(g["term"], re.compile(g["match"], re.I)) for g in config.GLOSSARY]


def extract_terms(title: str, text: str = "") -> list[str]:
    """Terms in one item. Glossary terms match title+summary; auto terms come from the title."""
    full = f"{title} {text}"
    found = [term for term, rx in _GLOSS if rx.search(full)]
    auto = ACRONYM.findall(title) + CAMEL.findall(title) + VERSIONED.findall(title)
    for t in auto:
        t = t.strip()
        if t in config.TREND_STOPLIST or t.upper() in config.TREND_STOPLIST or len(t) < 2:
            continue
        if re.fullmatch(r"[A-Z]{2,}\d*", t) and t in {"HN", "API"}:
            continue
        if t not in found:
            found.append(t)
    return found[:12]


def update_history(history: dict, items: list[dict], today: date) -> dict:
    """history = {"YYYY-MM-DD": {term: count}}. Today's counts are recomputed each run."""
    day = today.isoformat()
    counts: dict[str, int] = {}
    for it in items:
        if it.get("first_seen") == day:
            for t in it.get("terms") or []:
                counts[t] = counts.get(t, 0) + 1
    history = {d: c for d, c in history.items()
               if d >= (today - timedelta(days=config.TRENDS_HISTORY_DAYS)).isoformat()}
    history[day] = counts
    return history


def trending(history: dict, items: list[dict], today: date, limit: int = 24) -> list[dict]:
    win_start = (today - timedelta(days=config.TRENDS_WINDOW_DAYS - 1)).isoformat()
    recent: dict[str, int] = {}
    before: dict[str, int] = {}
    prior_days = [d for d in history if d < win_start]
    for d, counts in history.items():
        bucket = recent if d >= win_start else before
        for t, n in counts.items():
            bucket[t] = bucket.get(t, 0) + n
    gloss = {g["term"]: g for g in config.GLOSSARY}
    out = []
    for term, n in recent.items():
        if n < 2 and term not in gloss:
            continue
        prev = before.get(term, 0)
        weeks_before = max(1.0, len(prior_days) / 7)
        if prior_days and prev == 0:
            status = "new"
        elif prev and n / (prev / weeks_before) >= 2:
            status = "rising"
        else:
            status = "active"
        examples = [it["key"] for it in items if term in (it.get("terms") or [])][:5]
        out.append({"term": term, "count": n, "status": status, "examples": examples,
                    "definition": gloss.get(term, {}).get("def", ""),
                    "tags": gloss.get(term, {}).get("tags", [])})
    rank = {"new": 0, "rising": 1, "active": 2}
    out.sort(key=lambda t: (rank[t["status"]], -t["count"], t["term"]))
    return out[:limit]
