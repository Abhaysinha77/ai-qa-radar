"""Importance × urgency scoring. The same rules are re-implemented in web/app.js (they are
exported in data.json), so keep the two in sync if you change the maths here."""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from . import config
from .models import Item

OFFICIAL_GROUPS = {"Releases", "Official updates"}


def _text(item: Item) -> str:
    return f"{item.title} {item.summary}"


def tags(item: Item) -> list[str]:
    text = _text(item)
    return [name for name, pattern in config.TAGS.items()
            if re.search(pattern, text, re.I)
            and not (name in config.TAG_EXCLUDE and re.search(config.TAG_EXCLUDE[name], text, re.I))]


def _age_hours(item: Item, now: datetime) -> float:
    stamp = item.published or item.first_seen
    if not stamp:
        return 12.0
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return 12.0
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(1.0, (now - when).total_seconds() / 3600)


def score(item: Item, now: datetime | None = None, rules: dict | None = None) -> dict:
    rules = rules or config.RANKING
    now = now or datetime.now(timezone.utc)
    text = _text(item)
    official = item.group in OFFICIAL_GROUPS

    stack = sum(r["weight"] for r in rules["stack"] if re.search(r["pattern"], text, re.I))
    velocity = 0.0
    if item.points:
        velocity = min(25.0, 12 * math.log10(1 + item.points / _age_hours(item, now)))
    importance = min(60, stack) + velocity + min(16, 8 * len(item.also_in))
    importance += rules["official_boost"] if official else 0

    # news/community items: only the title can make something urgent (summaries mention lots)
    urgent_text = item.title if rules.get("urgency_title_only_for_news") and not official else text
    reasons = [r["label"] for r in rules["urgency"] if re.search(r["pattern"], urgent_text, re.I)]
    urgency = max([r["weight"] for r in rules["urgency"] if r["label"] in reasons], default=0)
    if item.group == "Releases":
        urgency = max(urgency, rules["release_urgency"])
        reasons = reasons or ["New release"]
    if _age_hours(item, now) <= rules["fresh_hours"]:
        urgency += rules["fresh_boost"]
    urgency += rules["official_boost"] if official and urgency else 0

    importance, urgency = round(min(100, importance)), round(min(100, urgency))
    if urgency >= rules["act_urgency"] and importance >= rules["act_importance"]:
        quadrant = "Act now"
    elif importance >= rules["act_importance"]:
        quadrant = "Plan"
    elif urgency >= rules["act_urgency"]:
        quadrant = "Watch"
    else:
        quadrant = "FYI"
    return {"importance": importance, "urgency": urgency, "quadrant": quadrant,
            "hot": round(0.55 * importance + 0.45 * urgency), "reasons": reasons}
