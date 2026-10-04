#!/usr/bin/env python3
"""
Cover-art coverage gate for the Signature Book Depository drip.

Every book cover composites AI-painted genre base art
(assets/covers/cover-<gkey>.jpg, genuinely generated per genre) with the
book's REAL title/author typeset in the browser (bookstore typography).
This gate runs at the end of every drip_books.py run: it verifies that
every genre the drip can emit has its cover file present and non-trivial,
so no book can ever ship without cover art. Deterministic: same book ->
same genre art + same typography -> same cover, forever.

New books need no manual work: their genre's art already exists, and the
browser composites the per-book typography client-side (lazy-loaded,
with a deterministic SVG fallback if the art file ever fails to load).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COVERS = os.path.join(ROOT, "assets", "covers")
MIN_BYTES = 20000  # sanity: a real 800x1200 painted JPEG is far larger


def genres():
    src = open(os.path.join(HERE, "drip_books.py")).read()
    m = re.search(r"GENRES\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        raise RuntimeError("GENRES block not found in drip_books.py")
    return re.findall(r'\(\s*"([^"]+)"\s*,\s*"[^"]+"\s*\)', m.group(1))


def main():
    gkeys = genres()
    if not gkeys:
        print("COVER GATE FAILED: no genres parsed")
        sys.exit(1)
    missing = [g for g in gkeys
               if not os.path.isfile(os.path.join(COVERS, f"cover-{g}.jpg"))]
    bad = [g for g in gkeys
           if os.path.isfile(os.path.join(COVERS, f"cover-{g}.jpg"))
           and os.path.getsize(os.path.join(COVERS, f"cover-{g}.jpg")) < MIN_BYTES]
    if missing or bad:
        print("COVER GATE FAILED:", {"missing": missing, "corrupt": bad})
        sys.exit(1)
    print(f"cover gate OK: {len(gkeys)} genre covers present")


if __name__ == "__main__":
    main()
