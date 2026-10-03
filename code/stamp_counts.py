#!/usr/bin/env python3
"""Stamp last-known real shelf counts into index.html's raw stat chips.

Universal loading pattern: counters/chips must NEVER boot as bare "loading...".
This stamps the authoritative api.json counts into the raw HTML as initial
content; the page's JS overwrites them live once api.json arrives.
Idempotent: re-run after every book drip (drip_books.py calls it after
save_state). Markers: data-stamp="books|words|genres|origins".
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "data", "index", "api.json")
HTML = os.path.join(ROOT, "index.html")

def fmt_words(n):
    return f"{n/1e6:.1f}M"

def main():
    with open(API) as f:
        api = json.load(f)
    vals = {
        "books": f"{int(api['total_books']):,}",
        "words": fmt_words(int(api['total_words'])),
        "genres": str(len(api.get("genres", {}))),
        "origins": str(len(api.get("origins", {}))),
    }
    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    # 1) replace the original unstamped chips (first run)
    html, n1 = re.subn(
        r'<div class="stat"><b>loading(?:\.\.\.|\u2026)</b><span>(finished books|words of prose|genres|source streams)</span></div>',
        lambda m: '<div class="stat"><b data-stamp="%s">%s</b><span>%s</span></div>' % (
            {"finished books": "books", "words of prose": "words",
             "genres": "genres", "source streams": "origins"}[m.group(1)],
            vals[{"finished books": "books", "words of prose": "words",
                  "genres": "genres", "source streams": "origins"}[m.group(1)]],
            m.group(1)),
        html)
    # 2) refresh already-stamped chips (every drip)
    def repl(m):
        key = m.group(1)
        return '<b data-stamp="%s">%s</b>' % (key, vals[key])
    html, n2 = re.subn(r'<b data-stamp="(books|words|genres|origins)">.*?</b>', repl, html)
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"stamp_counts: stamped {n1 + n2} chips -> {vals}")

if __name__ == "__main__":
    main()
