from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Item:
    key: str                      # stable id used for "never show twice"
    title: str
    url: str
    source: str                   # e.g. "Show HN", "Simon Willison", "pytest"
    group: str = ""               # section on the page; set by the builder
    points: int | None = None
    comments: int | None = None
    discussion_url: str | None = None
    published: str | None = None  # ISO date if the source gives one
    also_in: list[str] = field(default_factory=list)
    first_seen: str = ""          # ISO date we first showed it
    found_at: str = ""            # exact ISO time it was first collected (for "new since last visit")
    action: bool = False
    tags: list[str] = field(default_factory=list)
    importance: int = 0           # 0-100: how much it matters to your stack
    urgency: int = 0              # 0-100: how time-sensitive it is
    quadrant: str = "FYI"         # Act now / Plan / Watch / FYI
    hot: int = 0                  # combined score used for the Hot list
    reasons: list[str] = field(default_factory=list)
    summary: str = ""             # summary shown on the page
    summary_kind: str = ""        # "ai", "extractive" (quoted sentences) or "excerpt"
    key_points: list[dict] = field(default_factory=list)   # [{"heading", "point"}] quoted
    outline: list[str] = field(default_factory=list)       # the article's section headings
    images: list[dict] = field(default_factory=list)       # diagrams found in the article
    cover: str = ""               # the article's own preview image (og:image)
    read_minutes: int = 0
    terms: list[str] = field(default_factory=list)          # glossary / trending terms in it
    discussion: list[str] = field(default_factory=list)     # quoted highlights from the HN thread
    enriched: bool = False        # True once the full reader (key points, outline...) has run
    no_text_reason: str = ""      # why there is no summary (blocked site, link-only post...)
    body: str = ""                # raw source text (never stored)
    html: str = ""                # raw source HTML (never stored)

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("body", None)
        data.pop("html", None)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)
