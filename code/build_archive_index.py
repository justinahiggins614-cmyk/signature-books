#!/usr/bin/env python3
"""Build per-wing A-Z compact archive indexes for archive.html.

Reads each wing's compact idx gz, buckets records by first letter of title
(sorted by title), and writes three lazy-loadable gz files:
  data/index/archive-books.json.gz  {"letters": {"A": [[id, title], ...], "#": [...]}, "count": N}
  data/index/archive-mags.json.gz
  data/index/archive-libs.json.gz

Wings load only their own file on demand; no wing ever loads a full text chunk.
Called by every drip (books, magazines, library) after the index flush.
"""
import gzip, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "data", "index")

WINGS = {
    "books": {"idx": os.path.join(ROOT, "data", "index", "books.idx.json.gz"),
              "title": lambda e: e.get("t", "")},
    "mags": {"idx": os.path.join(ROOT, "data", "magazines", "index", "mags.idx.json.gz"),
             "title": lambda e: "%s \u00b7 Vol. %s No. %s" % (e.get("m", ""), e.get("v", ""), e.get("n", ""))},
    "libs": {"idx": os.path.join(ROOT, "data", "library", "index", "libs.idx.json.gz"),
             "title": lambda e: e.get("t", "")},
}

def letter_of(title):
    m = re.search(r"[A-Za-z]", title or "")
    return m.group(0).upper() if m else "#"

def build():
    for wing, cfg in WINGS.items():
        with gzip.open(cfg["idx"], "rt", encoding="utf-8") as f:
            entries = json.load(f)
        buckets = {}
        for e in entries:
            t = (cfg["title"](e) or "").strip()
            rid = e.get("id", "")
            if not rid:
                continue
            buckets.setdefault(letter_of(t), []).append([rid, t])
        for L in buckets:
            buckets[L].sort(key=lambda r: r[1].lower())
        out = {"letters": buckets, "count": len(entries)}
        op = os.path.join(OUTDIR, "archive-%s.json.gz" % wing)
        with gzip.open(op, "wt", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        print("archive-%s: %d records -> %s (%d bytes)" %
              (wing, len(entries), op, os.path.getsize(op)))

if __name__ == "__main__":
    build()
