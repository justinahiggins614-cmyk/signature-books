#!/usr/bin/env python3
"""Assemble archive.html — the unified A-Z archive hub for all three wings.

Reuses index.html's theme <script>, <style> blocks, JAH-network nav and footer
verbatim, so the look never drifts. Body + JS are archive-specific:
  - hero with three stamped count chips (books / magazines / library artifacts)
  - wing tabs, search box, A-Z collapsible <details> lists
  - lazy per-wing gz index loads (data/index/archive-<wing>.json.gz)
  - deep links reuse the site's ?book= / magazines.html?mag= / library.html?lib= patterns

Counts come from the three api.json files (real numbers at build time);
code/stamp_counts.py re-stamps the chips after every drip.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://justinahiggins614-cmyk.github.io/signature-books/"

def _api(path, key):
    try:
        with open(os.path.join(ROOT, path)) as f:
            return int(json.load(f).get(key, 0))
    except Exception:
        return 0

WINGS = [
    ("books", "Books", "?book=", "JAH-BOOK"),
    ("mags", "Magazines", "magazines.html?mag=", "JAH-MAG"),
    ("libs", "Library Artifacts", "library.html?lib=", "JAH-LIB"),
]

def main():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        src = f.read()

    # --- lift the theme + shared chrome from index.html ---
    theme_script = '<script>try{if(localStorage.getItem("jah-theme")==="dark"){document.documentElement.dataset.theme="dark"}}catch(e){}</script>'
    styles = re.findall(r"<style>.*?</style>", src, flags=re.S)
    jahnet = re.search(r"<nav aria-label=\"JAH Network Global Ecosystem\".*?</nav>", src, flags=re.S).group(0)
    footer = re.search(r"<footer>.*?</footer>", src, flags=re.S).group(0)

    books = _api("data/index/api.json", "total_books")
    mags = _api("data/magazines/index/api.json", "total_issues")
    libs = _api("data/library/index/api.json", "total_artifacts")

    wing_tabs = "\n".join(
        '<button class="btn%s" data-wing="%s">%s</button>' % (" ghost" if i else "", w[0], w[1])
        for i, w in enumerate(WINGS))

    body = """
<div class="wingnav"><a href="./">Books</a><a href="magazines.html">Magazines</a><a href="library.html">Library</a><a href="archive.html" class="cur">A-Z Archive</a></div>

<header class="hero wrap">
<div class="jnkicker">SITE 11 OF 27 &middot; THE JAH NETWORK</div>
<h1>The Full Archive</h1>
<div class="sub">Every book, every magazine issue, every library artifact &mdash; the complete catalog from A to Z. Tap a letter, tap a record, start reading.</div>
<details class="statdrop" open><summary class="statsum">Shelf counts &mdash; tap to hide</summary>
<div class="stats" id="stats">
<div class="stat"><b data-stamp="archive_books">{books:,}</b><span>finished books</span></div>
<div class="stat"><b data-stamp="archive_mags">{mags:,}</b><span>magazine issues</span></div>
<div class="stat"><b data-stamp="archive_libs">{libs:,}</b><span>library artifacts</span></div>
</div>
<p class="loadline" id="loadline">Loading the A&ndash;Z shelves&hellip;</p>
</details>
</header>

<div class="controls"><div class="wrap">
<div class="row">
<input type="search" id="q" placeholder="Search titles across the whole archive&hellip;" aria-label="Search archive titles">
<div class="viewtoggle" role="tablist" aria-label="Archive wings">
{wing_tabs}
</div>
</div>
<div class="az" id="az" aria-label="Jump to a letter"></div>
</div></div>

<div class="wrap"><div id="results" aria-live="polite"></div></div>

<p class="honest wrap" style="margin-bottom:40px">Every record here is an original generated work by/for the Signature system &mdash; no real-world authors, no borrowed text, no trademarked characters. Derived records name the network record that seeded them. Full texts load only when you open a record; the archive itself stays light on any phone.</p>
""".format(books=books, mags=mags, libs=libs, wing_tabs=wing_tabs)

    js = r"""
<script>
"use strict";
/* The Full Archive: lazy per-wing A-Z index, deep links reuse ?book=/?mag=/?lib=. */
var WCFG={books:{file:"data/index/archive-books.json.gz",link:function(id){return "./?book="+id}},
          mags:{file:"data/index/archive-mags.json.gz",link:function(id){return "magazines.html?mag="+id}},
          libs:{file:"data/index/archive-libs.json.gz",link:function(id){return "library.html?lib="+id}}};
var CACHE={}, WING="books";
function $(id){return document.getElementById(id)}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function gunzip(buf){return new Response(buf).arrayBuffer().then(function(ab){
  var ds=new DecompressionStream("gzip");
  return new Response(new Blob([ab]).stream().pipeThrough(ds)).arrayBuffer()})}
function fetchGz(url){return fetch(url).then(function(r){if(!r.ok)throw new Error("fetch "+r.status);return r.arrayBuffer()})
  .then(gunzip).then(function(ab){return JSON.parse(new TextDecoder().decode(ab))})}
function linkHref(id){return WCFG[WING].link(id)}
function entryRow(e){return '<div class="azrow"><a href="'+linkHref(e[0])+'" data-id="'+esc(e[0])+'">'+esc(e[1])+'</a><span class="azid">'+esc(e[0])+'</span></div>'}
function renderAz(payload){
  var L=payload.letters, keys=Object.keys(L).sort(), h="", i;
  for(i=0;i<keys.length;i++){var k=keys[i], rows=L[k];
    h+='<details class="azdet" id="det-'+esc(k)+'"><summary><b>'+esc(k)+'</b><span class="azcount">'+rows.length.toLocaleString()+' record'+(rows.length===1?"":"s")+'</span></summary><div class="azlist">';
    for(var j=0;j<rows.length;j++)h+=entryRow(rows[j]);
    h+='</div></details>'}
  $("results").innerHTML=h;
  var az=$("az");az.innerHTML="";
  keys.forEach(function(k){var b=document.createElement("button");b.textContent=k;
    b.setAttribute("aria-label","Open letter "+k);
    b.onclick=function(){var d=$("det-"+k);if(d){d.open=true;d.scrollIntoView({block:"start",behavior:"smooth"})}};
    az.appendChild(b)});
  var q=$("q").value.trim();
  if(q)doSearch(q); else $("loadline").textContent="Showing "+payload.count.toLocaleString()+" records, A to Z.";
}
function setStatus(msg){$("loadline").textContent=msg}
function loadWing(w){
  WING=w;
  document.querySelectorAll(".viewtoggle .btn").forEach(function(b){
    b.classList.toggle("ghost",b.getAttribute("data-wing")!==w)});
  $("results").innerHTML='<div class="loading"><div class="spin"></div>Loading the shelves&hellip;</div>';
  $("az").innerHTML="";$("q").value="";
  if(CACHE[w]){renderAz(CACHE[w]);return}
  setStatus("Loading the "+w+" shelf index\u2026");
  fetchGz(WCFG[w].file).then(function(p){CACHE[w]=p;renderAz(p)}).catch(function(e){
    $("results").innerHTML='<p class="honest">The shelf index could not be loaded ('+esc(e.message)+'). Check your connection and try again.</p>';
    setStatus("Index failed to load.")});
}
function doSearch(q){
  var p=CACHE[WING];if(!p)return; q=q.toLowerCase();
  var hits=[], keys=Object.keys(p.letters);
  for(var i=0;i<keys.length&&hits.length<500;i++){var rows=p.letters[keys[i]];
    for(var j=0;j<rows.length&&hits.length<500;j++){var r=rows[j];
      if(r[1].toLowerCase().indexOf(q)>=0||r[0].toLowerCase().indexOf(q)>=0)hits.push(r)}}
  var h='<p class="azhead">'+hits.length+(hits.length>=500?"+":"")+' match'+(hits.length===1?"":"es")+' for \u201c'+esc(q)+'\u201d</p><div class="azlist flat">';
  var cap=Math.min(hits.length,200);
  for(var k=0;k<cap;k++)h+=entryRow(hits[k]);
  h+='</div>';
  if(hits.length>cap)h+='<p class="azhead">Showing '+cap+' of '+hits.length+' &mdash; refine your search to narrow it.</p>';
  $("results").innerHTML=h;$("az").innerHTML="";
  setStatus(hits.length+" matches in this wing.");
}
document.querySelectorAll(".viewtoggle .btn").forEach(function(b){
  b.addEventListener("click",function(){loadWing(b.getAttribute("data-wing"))})});
var qt=null;
$("q").addEventListener("input",function(){var v=this.value;clearTimeout(qt);
  qt=setTimeout(function(){v=v.trim();if(!v){if(CACHE[WING])renderAz(CACHE[WING]);return}doSearch(v)},250)});
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",function(){loadWing("books")});
else loadWing("books");
</script>"""

    extra_css = """<style>
.azdet{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:0 0 10px;overflow:hidden}
.azdet summary{cursor:pointer;padding:12px 16px;display:flex;align-items:center;gap:12px;font-size:1.15em;list-style:none}
.azdet summary::-webkit-details-marker{display:none}
.azdet summary b{color:var(--gold2);font-size:1.3em;min-width:1.2em}
.azdet summary::after{content:"\\25B6";margin-left:auto;color:var(--mut);font-size:.8em}
.azdet[open] summary::after{content:"\\25BC"}
.azcount{color:var(--mut);font-size:.75em}
.azlist{padding:0 16px 14px}
.azrow{display:flex;justify-content:space-between;gap:10px;padding:7px 2px;border-top:1px dashed var(--line);font-size:.95em}
.azrow a{text-decoration:none}
.azrow a:hover{text-decoration:underline}
.azid{color:var(--mut);font-size:.78em;white-space:nowrap;align-self:center}
.azhead{color:var(--mut);font-size:.9em;margin:10px 0}
.azlist.flat .azrow{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:6px}
</style>"""

    head = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n' + theme_script +
            '\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">' +
            '\n<title>The Full Archive A&ndash;Z &mdash; The Signature Book Depository</title>' +
            '\n<meta name="description" content="The full A-to-Z archive of The Signature Book Depository: every finished book, magazine issue and library artifact, browsable by letter. Free, no login.">' +
            '\n<link rel="canonical" href="' + BASE + 'archive.html">' +
            '\n<meta property="og:type" content="website">' +
            '\n<meta property="og:title" content="The Full Archive A-Z \u2014 The Signature Book Depository">' +
            '\n<meta property="og:url" content="' + BASE + 'archive.html">' +
            '\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage","name":"The Full Archive A-Z","url":"' + BASE + 'archive.html","isPartOf":{"@type":"WebSite","name":"The Signature Book Depository","url":"' + BASE + '"},"creator":{"@type":"Person","name":"Justin Addam Higgins"}}</script>' +
            "\n" + styles[0] + "\n" + styles[1] + "\n" + extra_css + "\n</head>\n<body>\n")

    page = head + jahnet + "\n" + body + "\n" + footer + "\n" + js + "\n</body>\n</html>\n"
    with open(os.path.join(ROOT, "archive.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("archive.html written: books=%d mags=%d libs=%d" % (books, mags, libs))

if __name__ == "__main__":
    main()
