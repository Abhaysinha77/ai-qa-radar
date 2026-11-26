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
    summary: str = ""             # plain-English summary shown on the page
    summary_kind: str = ""        # "ai" or "excerpt"
    body: str = ""                # raw source text used for summarising (never stored)

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("body", None)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)
