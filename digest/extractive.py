"""Accurate summaries without an AI model: every sentence is QUOTED from the article (no new
words are written), chosen so the summary + key points + outline cover the whole piece.

    summary     the most informative sentences, in the article's own order (≤ ~250 words)
    key_points  the best sentence from each section, labelled with that section's heading
    outline     the article's section headings — what it covers, in order
"""
from __future__ import annotations

import math
import re
from collections import Counter

STOP = set("""a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its itself just me more most my no nor not now of off
on once only or other our out over own same she should so some such than that the their them then there
these they this those through to too under until up very was we were what when where which while who whom
why will with would you your yours also may might must one two new like get got use used using make made
via per its it's i'm we're you're they're don't can't won't etc""".split())

SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]?\s+(?=[A-Z0-9\"'(\[])")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]*[A-Za-z0-9+#]|[A-Za-z]")


def sentences(text: str) -> list[str]:
    out = []
    for raw in SENT_SPLIT.split(re.sub(r"\s+", " ", text or "").strip()):
        s = raw.strip()
        n = len(s.split())
        if 6 <= n <= 70 and not re.search(r"https?://\S{40,}", s):
            out.append(s)
    return out


def _tokens(s: str) -> list[str]:
    return [w.lower().strip(".-") for w in WORD.findall(s) if w.lower() not in STOP and len(w) > 2]


def _rank(sents: list[str], title: str) -> list[float]:
    freq = Counter(t for s in sents for t in set(_tokens(s)))
    if not freq:
        return [0.0] * len(sents)
    top = max(freq.values())
    title_words = set(_tokens(title))
    scores = []
    for i, s in enumerate(sents):
        toks = _tokens(s)
        if not toks:
            scores.append(0.0)
            continue
        base = sum(freq[t] / top for t in toks) / math.sqrt(len(toks))
        base += 0.6 * len(title_words & set(toks)) / (len(title_words) or 1)
        base += 0.35 if i < 3 else 0.0                      # intros carry the thesis
        base += 0.15 if re.search(r"\d", s) else 0.0        # concrete numbers/versions
        scores.append(base)
    return scores


def _dedupe(sents: list[str]) -> list[str]:
    seen, out = set(), []
    for s in sents:
        key = re.sub(r"\W+", " ", s.lower()).strip()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def summarize(sections: list[dict], title: str = "", max_words: int = 250) -> dict:
    all_sents: list[str] = _dedupe([s for sec in sections for p in sec["paras"] for s in sentences(p)])
    if not all_sents:
        return {"summary": "", "key_points": [], "outline": []}
    scores = _rank(all_sents, title)
    order = sorted(range(len(all_sents)), key=lambda i: -scores[i])
    total = sum(len(x.split()) for x in all_sents)
    max_words = min(max_words, max(45, int(total * 0.45)))  # short articles: leave room for key points
    chosen, words = [], 0
    for i in order:
        n = len(all_sents[i].split())
        if words + n > max_words and chosen:
            continue
        chosen.append(i)
        words += n
        if words >= max_words * 0.85:
            break
    summary = " ".join(all_sents[i] for i in sorted(chosen))
    used = {all_sents[i] for i in chosen}

    # one key point per titled section, so the whole article is covered
    index = {s: i for i, s in enumerate(all_sents)}
    key_points = []
    for sec in sections:
        if not sec["heading"]:
            continue
        sec_sents = [s for p in sec["paras"] for s in sentences(p) if s in index]
        cands = [s for s in sec_sents if s not in used] or sec_sents  # reuse if the summary took them all
        if not cands:
            continue
        best = max(cands, key=lambda s: scores[index[s]])
        key_points.append({"heading": sec["heading"], "point": best})
        used.add(best)
        if len(key_points) >= 8:
            break
    if len(key_points) < 3:  # short or flat articles: add the next best sentences
        for i in order:
            if all_sents[i] not in used:
                key_points.append({"heading": "", "point": all_sents[i]})
                used.add(all_sents[i])
            if len(key_points) >= 4:
                break
    outline = [sec["heading"] for sec in sections if sec["heading"]][:12]
    return {"summary": summary, "key_points": key_points, "outline": outline}
