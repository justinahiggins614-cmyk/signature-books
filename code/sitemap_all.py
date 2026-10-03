#!/usr/bin/env python3
"""Unified sitemap.xml for The Signature Book Depository (all three wings).

Aggregates: books (?book=JAH-BOOK-######), magazines (?mag=JAH-MAG-######),
library artifacts (?lib=JAH-LIB-######), plus static browse pages.
Called by every drip (books, magazines, library) so the sitemap never
goes stale for any wing.
"""
import gzip, json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://justinahiggins614-cmyk.github.io/signature-books/"

GENRES = ["Science Fiction", "Fantasy", "Mystery", "Romance", "Horror",
          "Mathematics", "Physics", "Chemistry", "Biology", "History",
          "Computer Science", "Children's", "Poetry", "Technical Manual",
          "Philosophy", "Business"]


def _gslug(g):
    return g.lower().replace(" ", "-").replace("'", "")

def _book_total():
    p = os.path.join(ROOT, "data", "state.json")
    if os.path.exists(p):
        with open(p) as f:
            return int(json.load(f).get("next_index", 1)) - 1
    return 0

def _wing_total(kind):
    # kind: "magazines" | "library"
    p = os.path.join(ROOT, "data", kind, "state.json")
    if os.path.exists(p):
        with open(p) as f:
            return int(json.load(f).get("next_index", 1)) - 1
    return 0

def write_sitemap():
    books = _book_total()
    mags = _wing_total("magazines")
    libs = _wing_total("library")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             f"<url><loc>{BASE}</loc></url>",
             f"<url><loc>{BASE}magazines.html</loc></url>",
             f"<url><loc>{BASE}library.html</loc></url>"]
    for i in range(1, books + 1):
        lines.append(f"<url><loc>{BASE}?book=JAH-BOOK-{i:06d}</loc></url>")
    for i in range(1, mags + 1):
        lines.append(f"<url><loc>{BASE}magazines.html?mag=JAH-MAG-{i:06d}</loc></url>")
    for i in range(1, libs + 1):
        lines.append(f"<url><loc>{BASE}library.html?lib=JAH-LIB-{i:06d}</loc></url>")
    # static crawlable browse pages (sub-indexes: shards + genre hubs)
    lines.append(f"<url><loc>{BASE}browse/</loc></url>")
    lines.append(f"<url><loc>{BASE}browse/genres.html</loc></url>")
    for g in GENRES:
        lines.append(f"<url><loc>{BASE}browse/genre-{_gslug(g)}.html</loc></url>")
    # standardized machine-readable catalog feed
    lines.append(f"<url><loc>{BASE}data/index/books-catalog.json</loc></url>")
    for s in range(1, math.ceil(books / 1000) + 1):
        lines.append(f"<url><loc>{BASE}browse/books-{s:03d}.html</loc></url>")
    if mags:
        lines.append(f"<url><loc>{BASE}browse/mags-index.html</loc></url>")
        for s in range(1, math.ceil(mags / 1000) + 1):
            lines.append(f"<url><loc>{BASE}browse/mags-{s:03d}.html</loc></url>")
    if libs:
        lines.append(f"<url><loc>{BASE}browse/libs-index.html</loc></url>")
        for s in range(1, math.ceil(libs / 1000) + 1):
            lines.append(f"<url><loc>{BASE}browse/libs-{s:03d}.html</loc></url>")
    lines.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write("\n".join(lines))
    print(f"sitemap: {books} books + {mags} mags + {libs} libs = {len(lines)-3} urls")

if __name__ == "__main__":
    write_sitemap()
