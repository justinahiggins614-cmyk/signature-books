#!/usr/bin/env python3
"""Standardized machine-readable catalog feed for The Signature Book Depository.

Writes data/index/books-catalog.json: site totals, per-genre counts with hub
pages, static browse shard pages, per-volume chunk ranges with direct URLs,
and the book URL pattern. Rebuilt by code/drip_books.py after every drip run
so the feed never goes stale. Purely additive — no look/behavior changes.
"""
import gzip, json, os, datetime, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://justinahiggins614-cmyk.github.io/signature-books/"
CHUNK = 100
PER_PAGE = 1000


def _slug(g):
    return g.lower().replace(" ", "-").replace("'", "")


def build_feed():
    with gzip.open(os.path.join(ROOT, "data", "index", "books.idx.json.gz"), "rt") as f:
        idx = json.load(f)
    n = len(idx)
    api_p = os.path.join(ROOT, "data", "index", "api.json")
    api = json.load(open(api_p)) if os.path.exists(api_p) else {}
    per_genre = {}
    for r in idx:
        per_genre[r["g"]] = per_genre.get(r["g"], 0) + 1
    chunk_n = math.ceil(n / CHUNK)
    volumes = []
    for c in range(1, chunk_n + 1):
        first = (c - 1) * CHUNK + 1
        last = min(c * CHUNK, n)
        volumes.append({
            "first": f"JAH-BOOK-{first:06d}",
            "last": f"JAH-BOOK-{last:06d}",
            "records": last - first + 1,
            "url": BASE + f"data/volumes/books-c{c:05d}.json.gz",
        })
    browse_shards = math.ceil(n / PER_PAGE)
    feed = {
        "site": "The Signature Book Depository",
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_books": n,
        "total_words": api.get("total_words"),
        "chunk_size": CHUNK,
        "index": BASE + "data/index/books.idx.json.gz",
        "book_url_pattern": BASE + "?book=JAH-BOOK-######",
        "genres": [
            {"name": g, "count": c,
             "page": BASE + f"browse/genre-{_slug(g)}.html"}
            for g, c in sorted(per_genre.items())
        ],
        "browse_pages": [BASE + f"browse/books-{s + 1:03d}.html"
                         for s in range(browse_shards)],
        "genre_index": BASE + "browse/genres.html",
        "volumes": volumes,
        "note": ("All books are original generated works by/for the Signature "
                 "system, by Justin Addam Higgins. Derived books carry "
                 "source-lineage links to the network record that seeded them."),
    }
    out = os.path.join(ROOT, "data", "index", "books-catalog.json")
    with open(out, "w") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"feed: {n} books, {chunk_n} volumes -> {out}")


if __name__ == "__main__":
    build_feed()
