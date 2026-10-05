#!/usr/bin/env python3
"""Static crawlable browse pages for the Magazines + Library wings
(AI/crawler accessibility, mirroring code/build_browse.py for books).

Generates browse/mags-NNN.html and browse/libs-NNN.html (1,000 records per
shard, plain <a href> deep links, prev/next) + mags-index.html +
libs-index.html. Re-run any time the wings change; the unified sitemap
(code/sitemap_all.py) includes these pages.
Purely additive — does not touch any page's look or behavior.
"""
import gzip, json, os, html, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://justinahiggins614-cmyk.github.io/signature-books/"
OUT = os.path.join(ROOT, "browse")
PER = 1000

CSS = """body{font-family:Georgia,'Times New Roman',serif;background:#141009;color:#f0e6cf;margin:0;line-height:1.6}
.wrap{max-width:900px;margin:0 auto;padding:28px 18px}
h1{color:#f2d47e;font-size:1.5em}h2{color:#d9a441;margin-top:1.6em}
a{color:#9fc2ff}.meta{color:#a89e86;font-size:.9em}
.nav{display:flex;justify-content:space-between;margin:18px 0;flex-wrap:wrap;gap:8px}
ul{list-style:none;padding:0}li{margin:.35em 0}
.top{border-bottom:1px solid #4a3d24;padding-bottom:10px;margin-bottom:16px}"""

def page(title, desc, body, canon):
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<script src='../js/signin.js'></script><script src='../js/godmode.js'></script><script>/* JAHProfile storage: signed-out behavior is byte-identical to before; signed-in profiles get per-profile namespaced storage. */var PS = (typeof JAHProfile !== 'undefined') ? JAHProfile.store : localStorage;</script><meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n"
            f"<meta name=\"description\" content=\"{html.escape(desc)}\">\n"
            f"<link rel=\"canonical\" href=\"{canon}\">\n"
            f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n{body}\n</div>\n<script>(function () {{  var mount = document.querySelector('header .booksearch') ||              document.querySelector('nav.jtabbar') ||              document.querySelector('header nav') ||              document.querySelector('header') ||              document.body;  if (window.JAHProfile && JAHProfile.ui) JAHProfile.ui.renderButton(mount);}})();</script><script>(function () {{ if (window.JAHProfile && JAHProfile.ui) {{ var mount = document.querySelector('header') || document.body; JAHProfile.ui.renderGreeting(mount); }} }})();</script></body>\n</html>\n")

def build(wing, idx_name, idkey, linkfn, linefn, title, desc_tmpl, home, prefix):
    with gzip.open(os.path.join(ROOT, "data", wing, "index", idx_name), "rt") as f:
        idx = json.load(f)
    n = len(idx)
    if not n:
        print(f"no {wing} records yet"); return
    shards = math.ceil(n / PER)
    for s in range(shards):
        chunk = idx[s*PER:(s+1)*PER]
        first, last = chunk[0]["id"], chunk[-1]["id"]
        items = "\n".join(
            f'<li><a href="{linkfn(r)}">{html.escape(r[idkey])}</a> '
            f'<span class="meta">{linefn(r)}</span></li>' for r in chunk)
        prev_ = (f'<a href="{prefix}-{s:03d}.html">&larr; Previous 1,000</a>' if s > 0
                 else '<span class="meta">First page</span>')
        next_ = (f'<a href="{prefix}-{s+2:03d}.html">Next 1,000 &rarr;</a>' if s < shards-1
                 else '<span class="meta">Last page</span>')
        body = (f'<div class="top"><p class="meta"><a href="../{home}">{html.escape(title)}</a> &middot; '
                f'<a href="{prefix}-index.html">Browse index</a></p>\n'
                f"<h1>{html.escape(title)} \u2014 page {s+1} of {shards}</h1>\n"
                f"<p>{first} through {last}.</p></div>\n"
                f'<div class="nav">{prev_}{next_}</div>\n<ul>\n{items}\n</ul>\n'
                f'<div class="nav">{prev_}{next_}</div>')
        t = f"{title} {first}\u2013{last}"
        with open(os.path.join(OUT, f"{prefix}-{s+1:03d}.html"), "w") as f:
            f.write(page(t, desc_tmpl.format(n=len(chunk), first=first, last=last),
                         body, BASE+f"browse/{prefix}-{s+1:03d}.html"))
    links = "\n".join(
        f'<li><a href="{prefix}-{s+1:03d}.html">Page {s+1}</a> <span class="meta">{idx[s*PER]["id"]} \u2013 {idx[min((s+1)*PER,n)-1]["id"]}</span></li>'
        for s in range(shards))
    with open(os.path.join(OUT, f"{prefix}-index.html"), "w") as f:
        f.write(page(f"{title} \u2014 browse index",
                     f"Browse all {n} {title.lower()} by page.",
                     f'<div class="top"><p class="meta"><a href="../{home}">{html.escape(title)}</a></p>\n'
                     f"<h1>{html.escape(title)} \u2014 browse index</h1>\n<p>{n} records in {shards} pages.</p></div>\n<ul>\n{links}\n</ul>",
                     BASE+f"browse/{prefix}-index.html"))
    print(f"{wing}: {n} records, {shards} shard pages")

def main():
    os.makedirs(OUT, exist_ok=True)
    build("magazines", "mags.idx.json.gz", "m",
          lambda r: f'../magazines.html?mag={r["id"]}',
          lambda r: f'{html.escape(r["s"])} &middot; Vol. {r["v"]} No. {r["n"]} &middot; {html.escape(r["d"])} &middot; {r["id"]}',
          "Signature Magazines",
          "{n} original Signature magazine issues, {first} to {last}, each with a permanent issue page.",
          "magazines.html", "mags")
    build("library", "libs.idx.json.gz", "t",
          lambda r: f'../library.html?lib={r["id"]}',
          lambda r: f'{html.escape(r["k"])} &middot; {r["w"]:,} words &middot; {r["id"]}',
          "The Signature Library",
          "{n} Signature library artifacts, {first} to {last}, each with a permanent artifact page.",
          "library.html", "libs")

if __name__ == "__main__":
    main()
