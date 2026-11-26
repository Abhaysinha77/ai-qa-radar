"""Read an article page: its sections (heading + text), its diagrams/architecture images and its
cover image. Everything returned is taken from the page itself — nothing is invented."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# images whose alt text, caption or file name says they explain something
DIAGRAM = re.compile(
    r"diagram|architecture|flow ?chart|flowchart|workflow|pipeline|sequence|schema|overview|"
    r"how it works|data ?flow|system design|lifecycle|framework|chart|graph|illustrat", re.I)
JUNK_IMG = re.compile(
    r"avatar|logo|icon|emoji|badge|pixel|tracking|gravatar|sprite|spinner|placeholder|"
    r"/ads?/|doubleclick|share|button|profile|headshot|author", re.I)
BOILERPLATE = re.compile(
    r"cookie|subscribe|sign up|sign in|log in|newsletter|all rights reserved|©|click here|"
    r"share this|follow us|advertisement|read more|related posts|leave a comment", re.I)


def _img_src(img) -> str:
    for attr in ("src", "data-src", "data-original", "data-lazy-src"):
        if img.get(attr):
            return img[attr]
    srcset = img.get("srcset") or img.get("data-srcset") or ""
    return srcset.split(",")[0].strip().split(" ")[0] if srcset else ""


def _too_small(img) -> bool:
    for attr in ("width", "height"):
        val = re.match(r"\d+", str(img.get(attr) or ""))
        if val and int(val.group()) < 200:
            return True
    return False


def parse(html: str, base_url: str = "") -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    cover = ""
    meta = soup.find("meta", attrs={"property": "og:image"}) or soup.find("meta", attrs={"name": "twitter:image"})
    if meta and meta.get("content"):
        cover = urljoin(base_url, meta["content"])
    for tag in soup(["script", "style", "noscript", "nav", "footer", "aside", "form", "header", "svg", "iframe"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup

    # ---- sections: walk headings and paragraphs in document order
    sections: list[dict] = [{"heading": "", "paras": []}]
    for el in root.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name in ("h1", "h2", "h3"):
            if el.name == "h1" and not sections[-1]["paras"]:
                continue  # page title, not a section
            if len(text) <= 120 and not BOILERPLATE.search(text):
                sections.append({"heading": text, "paras": []})
            continue
        if el.name == "li" and el.find_parent(["nav", "footer"]):
            continue
        if el.find_parent("li") and el.name == "p":
            continue  # avoid counting text twice
        if len(text) < 25 or BOILERPLATE.search(text[:80]):
            continue
        sections[-1]["paras"].append(text)
    sections = [s for s in sections if s["paras"]]
    if not sections:  # plain text without <p> tags (some feeds, release notes)
        loose = root.get_text(" ", strip=True)
        if len(loose) >= 20:
            sections = [{"heading": "", "paras": [loose]}]

    # ---- images: only real diagrams/architecture pictures from the article body
    images, seen = [], set()
    for img in root.find_all("img"):
        src = urljoin(base_url, _img_src(img))
        if not src.startswith("https://") or src in seen or _too_small(img) or JUNK_IMG.search(src + " " + (img.get("alt") or "")):
            continue
        fig = img.find_parent("figure")
        caption = fig.find("figcaption").get_text(" ", strip=True) if fig and fig.find("figcaption") else ""
        label = " ".join([img.get("alt") or "", img.get("title") or "", caption, src.rsplit("/", 1)[-1]])
        if DIAGRAM.search(label):
            seen.add(src)
            images.append({"src": src, "alt": (caption or img.get("alt") or "Diagram from the article")[:200]})
        if len(images) >= 3:
            break
    if cover and (not cover.startswith("https://") or JUNK_IMG.search(cover)):
        cover = ""

    words = sum(len(p.split()) for s in sections for p in s["paras"])
    return {"sections": sections, "images": images, "cover": cover, "words": words,
            "text": " ".join(p for s in sections for p in s["paras"])}
