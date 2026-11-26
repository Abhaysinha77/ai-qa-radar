"""Download the Geist fonts once (open-source, SIL Open Font License) so the app never calls
Google Fonts. Files are pinned to an exact version and checked against SHA-256 hashes.

    python scripts/fetch_fonts.py        # writes web/fonts/*.woff2 (commit them)
"""
from __future__ import annotations

import base64
import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://cdn.jsdelivr.net/npm/@fontsource-variable"
FONTS = {
    # file in web/fonts         package@version / path                                   sha256 (base64, from jsDelivr)
    "geist.woff2": ("geist@5.2.8/files/geist-latin-wght-normal.woff2", "DLvmKGoA81bpiYB4PMlQqbaTdR4Ert+5fZUm/23CsxY="),
    "geist-mono.woff2": ("geist-mono@5.2.8/files/geist-mono-latin-wght-normal.woff2", "r2G5aef5mZafavV25YTuhdyjAaAIp2vhJR0XLVa5kEw="),
}
OUT = Path(__file__).resolve().parent.parent / "web" / "fonts"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (path, sha) in FONTS.items():
        target = OUT / name
        if target.exists() and base64.b64encode(hashlib.sha256(target.read_bytes()).digest()).decode() == sha:
            print(f"ok      {name}")
            continue
        with urllib.request.urlopen(f"{BASE}/{path}", timeout=30) as resp:  # noqa: S310
            data = resp.read()
        got = base64.b64encode(hashlib.sha256(data).digest()).decode()
        if got != sha:
            print(f"FAILED  {name}: checksum mismatch, not saved", file=sys.stderr)
            return 1
        target.write_bytes(data)
        print(f"saved   {name} ({len(data) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
