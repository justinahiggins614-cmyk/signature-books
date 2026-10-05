#!/usr/bin/env python3
"""Static crawlable browse pages for The Signature Book Depository (AI/crawler accessibility).

Generates:
  browse/books-NNN.html (1,000 books per shard, plain <a href> ?book= deep links,
      each entry with a one-line summary, prev/next)
  browse/genres.html (16 genres, sections link to per-genre hub pages)
  browse/genre-<slug>.html (per-genre hub: every book in that genre)
  browse/index.html (master index)
  browse/text/JAH-BOOK-######.txt (plaintext summary fallback per book —
      INCREMENTAL: only missing files are written, never rewritten)

Re-run any time the catalog changes; code/drip_books.py calls main() after
every drip run, and sitemap.xml includes the hub + shard pages.
Purely additive — does not touch index.html's look or behavior.
"""
import gzip, json, os, html, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://justinahiggins614-cmyk.github.io/signature-books/"
OUT = os.path.join(ROOT, "browse")
TXT = os.path.join(OUT, "text")
PER = 1000

CSS = """body{font-family:Georgia,'Times New Roman',serif;background:#141009;color:#f0e6cf;margin:0;line-height:1.6}
.wrap{max-width:900px;margin:0 auto;padding:28px 18px}
h1{color:#f2d47e;font-size:1.5em}h2{color:#d9a441;margin-top:1.6em}
a{color:#9fc2ff}.meta{color:#a89e86;font-size:.9em}
.nav{display:flex;justify-content:space-between;margin:18px 0;flex-wrap:wrap;gap:8px}
ul{list-style:none;padding:0}li{margin:.35em 0}
.top{border-bottom:1px solid #4a3d24;padding-bottom:10px;margin-bottom:16px}
.sum{color:#c9bda0;font-size:.92em}"""


def slug(g):
    return g.lower().replace(" ", "-").replace("'", "")


def page(title, desc, body, canon):
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<script src='../js/signin.js'></script><script>/* JAHProfile storage: signed-out behavior is byte-identical to before; signed-in profiles get per-profile namespaced storage. */var PS = (typeof JAHProfile !== 'undefined') ? JAHProfile.store : localStorage;</script><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n"
            f"<meta name=\"description\" content=\"{html.escape(desc)}\">\n"
            f"<link rel=\"canonical\" href=\"{canon}\">\n"
            f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n{body}\n</div>\n<script>(function () {{  var mount = document.querySelector('header .booksearch') ||              document.querySelector('nav.jtabbar') ||              document.querySelector('header nav') ||              document.querySelector('header') ||              document.body;  if (window.JAHProfile && JAHProfile.ui) JAHProfile.ui.renderButton(mount);}})();</script><script>(function () {{ if (window.JAHProfile && JAHProfile.ui) {{ var mount = document.querySelector('header') || document.body; JAHProfile.ui.renderGreeting(mount); }} }})();</script></body>\n</html>\n")


def summary(r):
    d = str(r.get("d", "") or "")
    return d if len(d) <= 170 else d[:167].rsplit(" ", 1)[0] + "\u2026"


def entry_li(r):
    return (f'<li><a href="../?book={r["id"]}">{html.escape(r["t"])}</a> '
            f'<span class="meta">{html.escape(r["g"])} &middot; {r["w"]:,} words &middot; {r["id"]} '
            f'&middot; <a href="text/{r["id"]}.txt">plain text</a></span><br>'
            f'<span class="sum">{html.escape(summary(r))}</span></li>')


def text_fallback(r):
    """Plaintext summary fallback for one book (from the catalog index row)."""
    chs = r.get("ch", []) or []
    lines = [
        f"{r['t']}",
        f"by {r.get('a', 'Justin Addam Higgins')} \u00b7 {r['id']}",
        f"Genre: {r['g']} \u00b7 {r['w']:,} words",
        "",
        "Summary:",
        str(r.get("d", "") or ""),
        "",
        "Chapters:",
    ]
    lines += [f"  {i + 1}. {c}" for i, c in enumerate(chs)]
    lines += ["",
              f"Read the full volume (cover, chapters, read-aloud) at:",
              BASE + "?book=" + r["id"],
              "",
              "An original generated work created by the Signature system. "
              "All names, places, and events are invented."]
    return "\n".join(lines) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TXT, exist_ok=True)
    with gzip.open(os.path.join(ROOT, "data", "index", "books.idx.json.gz"), "rt") as f:
        idx = json.load(f)
    n = len(idx)
    shards = math.ceil(n / PER)

    for s in range(shards):
        chunk = idx[s * PER:(s + 1) * PER]
        first, last = chunk[0]["id"], chunk[-1]["id"]
        items = "\n".join(entry_li(r) for r in chunk)
        prev_ = (f'<a href="books-{s:03d}.html">&larr; Previous 1,000</a>' if s > 0
                 else '<span class="meta">First page</span>')
        next_ = (f'<a href="books-{s + 2:03d}.html">Next 1,000 &rarr;</a>' if s < shards - 1
                 else '<span class="meta">Last page</span>')
        body = (f'<div class="top"><p class="meta"><a href="../">The Signature Book Depository</a> &middot; '
                f'<a href="index.html">Browse index</a> &middot; <a href="genres.html">Genres</a></p>\n'
                f"<h1>Book catalog \u2014 page {s + 1} of {shards}</h1>\n"
                f"<p>{first} through {last}: every book below opens its full finished volume "
                f"(cover, chapters, read-aloud) at its permanent link. Each entry also links "
                f"a plain-text summary fallback.</p></div>\n"
                f'<div class="nav">{prev_}{next_}</div>\n<ul>\n{items}\n</ul>\n'
                f'<div class="nav">{prev_}{next_}</div>')
        t = f"Signature books {first}\u2013{last}"
        with open(os.path.join(OUT, f"books-{s + 1:03d}.html"), "w") as f:
            f.write(page(t, f"{len(chunk)} finished Signature books, {first} to {last}, each with a permanent book page.",
                         body, BASE + f"browse/books-{s + 1:03d}.html"))

    # per-genre hub pages (sub-indexes for crawlers + humans)
    genres = {}
    for r in idx:
        genres.setdefault(r["g"], []).append(r)
    for g in sorted(genres):
        gs = slug(g)
        items = "\n".join(entry_li(r) for r in genres[g])
        gbody = (f'<div class="top"><p class="meta"><a href="../">The Signature Book Depository</a> &middot; '
                 f'<a href="index.html">Browse index</a> &middot; <a href="genres.html">All genres</a></p>\n'
                 f"<h1>{html.escape(g)}</h1>\n"
                 f"<p>{len(genres[g]):,} finished books. Every link is a permanent book URL; "
                 f"each entry also links a plain-text summary fallback.</p></div>\n"
                 f"<ul>\n{items}\n</ul>")
        with open(os.path.join(OUT, f"genre-{gs}.html"), "w") as f:
            f.write(page(f"Signature books \u2014 {g}",
                         f"All {len(genres[g]):,} finished Signature {g} books, each with a permanent book page.",
                         gbody, BASE + f"browse/genre-{gs}.html"))

    # genres page (sections link to the per-genre hub pages)
    secs = []
    for g in sorted(genres):
        gs = slug(g)
        items = "\n".join(
            f'<li><a href="../?book={r["id"]}">{html.escape(r["t"])}</a> '
            f'<span class="meta">{r["w"]:,} words &middot; {r["id"]}</span></li>'
            for r in genres[g][:50])
        more = (f'<p class="meta"><a href="genre-{gs}.html">All {len(genres[g]):,} {html.escape(g)} books &rarr;</a></p>'
                if len(genres[g]) > 50 else "")
        secs.append(f'<h2 id="{html.escape(gs)}"><a href="genre-{gs}.html" style="color:#d9a441">{html.escape(g)}</a> '
                    f'<span class="meta">({len(genres[g]):,} books)</span></h2>\n<ul>\n{items}\n</ul>\n{more}')
    gbody = (f'<div class="top"><p class="meta"><a href="../">The Signature Book Depository</a> &middot; '
             f'<a href="index.html">Browse index</a></p>\n'
             f"<h1>Browse by genre</h1>\n<p>{len(genres)} genres, {n:,} finished books.</p></div>\n"
             + "\n".join(secs))
    with open(os.path.join(OUT, "genres.html"), "w") as f:
        f.write(page("Signature books \u2014 browse by genre",
                     f"All {n:,} finished Signature books across {len(genres)} genres, each with a permanent book page.",
                     gbody, BASE + "browse/genres.html"))

    # plaintext fallbacks — INCREMENTAL: only write files that don't exist yet
    new_txt = 0
    for r in idx:
        p = os.path.join(TXT, r["id"] + ".txt")
        if not os.path.exists(p):
            with open(p, "w") as f:
                f.write(text_fallback(r))
            new_txt += 1

    shards_links = " ".join(f'<a href="books-{s + 1:03d}.html">{s + 1}</a>' for s in range(shards))
    genre_links = " ".join(f'<a href="genre-{slug(g)}.html">{html.escape(g)}</a>' for g in sorted(genres))
    ibody = (f'<div class="top"><p class="meta"><a href="../">The Signature Book Depository</a></p>\n'
             f"<h1>Browse the depository</h1>\n"
             f"<p>Static, crawler-friendly index of all {n:,} finished books. Every link is a permanent book URL.</p></div>\n"
             f"<h2>Book pages</h2><p>{shards_links}</p>\n"
             f"<h2>By genre</h2><p>{genre_links}</p>")
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(page("The Signature Book Depository \u2014 browse index",
                     f"Static browse index: all {n:,} finished Signature books and {len(genres)} genres.",
                     ibody, BASE + "browse/"))
    print(f"wrote {shards} book shards + {len(genres)} genre hubs + genres + index "
          f"({n} books), {new_txt} new plaintext fallbacks")


if __name__ == "__main__":
    main()
