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
    # The JAH NETWORK nav block lives at the BOTTOM of index.html (below all
    # content, directly above the footer, one instance per page). Lift the bare
    # .jahnet div wherever it sits and re-wrap it for the archive page.
    jahnet_inner = re.search(r'<div class="jahnet">.*?</div>', src, flags=re.S).group(0)
    jahnet = ('<nav aria-label="JAH Network Global Ecosystem" role="navigation">\n'
              + jahnet_inner + '\n</nav>')
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
<div class="jnkicker">SITE 11 OF 31 &middot; THE JAH NETWORK</div>
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
<!-- JAH TAB BAR — Manon's 2026-10-04 order (calculator screenshot as spec).
     Paste right after </header> (or after the hero/title block) on index.html AND on the archive page.
     On index.html: "Front Door" carries class "on". On the archive page: "1 Million Archive" carries "on".
     Replace <a class="jtab" href="library.html">Library</a>
<a class="jtab" href="magazines.html">Magazines</a> with <a class="jtab" href="...">Label</a> items (may be empty). -->
<style>
.jtabbar{{display:flex;gap:8px;overflow-x:auto;padding:10px 12px;-webkit-overflow-scrolling:touch;scrollbar-width:thin;border-bottom:1px solid rgba(128,128,128,.25);align-items:center}}
.jtabbar a.jtab{{flex:0 0 auto;text-decoration:none;border:1px solid rgba(160,160,160,.45);border-radius:999px;padding:9px 16px;font-size:.92em;color:inherit;background:rgba(127,127,127,.08);white-space:nowrap;font-family:inherit;transition:background .15s ease,border-color .15s ease,box-shadow .15s ease}}
.jtabbar a.jtab:hover{{border-color:#f5c518;background:rgba(245,197,24,.16);box-shadow:0 1px 6px rgba(0,0,0,.18)}}
.jtabbar a.jtab:focus-visible{{outline:2px solid #f5c518;outline-offset:2px}}
.jtabbar a.jtab.on{{background:#f5c518;border-color:#f5c518;color:#191919;font-weight:700}}
.jtabbar a.jtab.on:hover{{background:#f5c518;box-shadow:0 1px 6px rgba(0,0,0,.25)}}
</style>
<nav class="jtabbar" aria-label="Site sections">
<a class="jtab" href="index.html">🏠 Front Door</a>
<a class="jtab on" href="archive.html">📚 1 Million Archive</a>
<a class="jtab" href="library.html">Library</a>
<a class="jtab" href="magazines.html">Magazines</a>
</nav>


<div class="controls"><div class="wrap">
<div class="row">
<input type="search" id="q" placeholder="Search titles across the whole archive&hellip;" aria-label="Search archive titles">
<div class="viewtoggle" role="tablist" aria-label="Archive wings">
{wing_tabs}
</div>
</div>
<div class="az" id="az" aria-label="Jump to a letter"></div>
</div></div>
<!-- ASK THE AI — Manon's 2026-10-04 order. Paste on the archive page, directly under the
     search/filter area (or at the top of the archive section if there is no search box).
     It FINDS records by scanning the page's own archive list, and ANSWERS with his real
     Signature Llama (same loader as the phone book). Never fake: if the Llama can't load,
     the found records are still shown honestly. Replace The Signature Book Depository and the finished-book archive. -->
<div class="jah-askai" id="jah-askai">
<style>
.jah-askai{{border:1px solid rgba(160,160,160,.4);border-radius:14px;padding:18px;margin:16px 0;background:rgba(127,127,127,.06);box-shadow:0 2px 10px rgba(0,0,0,.08)}}
.jah-askai h2{{margin:0 0 4px;font-size:1.15em}}
.jah-askai .jah-askai-sub{{margin:0 0 12px;font-size:.9em;opacity:.85}}
.jah-askai .jah-askai-row{{display:flex;gap:10px;align-items:stretch}}
.jah-askai input#jah-askai-q{{flex:1;min-width:0;padding:12px 14px;border-radius:10px;border:1px solid rgba(160,160,160,.55);font-size:1em;background:#fff;color:#111;font-family:inherit}}
.jah-askai input#jah-askai-q:focus{{outline:2px solid #f5c518;outline-offset:1px;border-color:#f5c518}}
.jah-askai button#jah-askai-go{{padding:12px 22px;border-radius:10px;border:1px solid #ddad00;background:#f5c518;color:#191919;font-weight:700;font-size:1em;cursor:pointer;font-family:inherit;transition:box-shadow .15s ease,transform .06s ease}}
.jah-askai button#jah-askai-go:hover{{box-shadow:0 2px 8px rgba(0,0,0,.28)}}
.jah-askai button#jah-askai-go:active{{transform:translateY(1px)}}
.jah-askai #jah-askai-out{{margin-top:12px;font-size:.95em}}
.jah-askai #jah-askai-out ul{{margin:8px 0;padding-left:22px;line-height:1.7}}
.jah-askai #jah-askai-out a{{word-break:break-word}}
.jah-askai .jah-askai-ans{{border-left:3px solid #f5c518;padding:10px 12px;margin-top:10px;background:rgba(245,197,24,.08);border-radius:0 8px 8px 0;line-height:1.6}}
.jah-askai .jah-askai-thinking{{opacity:.7;font-style:italic}}
@media(max-width:520px){{.jah-askai .jah-askai-row{{flex-direction:column}}.jah-askai button#jah-askai-go{{width:100%}}}}
</style>
<h2>🤖 Ask the AI</h2>
<p class="jah-askai-sub">Ask about anything in this archive — the AI searches the records and answers.</p>
<div class="jah-askai-row">
<input id="jah-askai-q" type="text" autocomplete="off" placeholder="Ask about this archive…" aria-label="Ask about this archive">
<button id="jah-askai-go" type="button">Ask</button>
</div>
<div id="jah-askai-out" aria-live="polite"></div>
<script>
(function(){{
var SITE="The Signature Book Depository", DESC="the finished-book archive";
function esc(s){{return String(s==null?"":s).replace(/[&<>"']/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c];}});}}
/* Real Signature Llama loader — same pattern as the phone book. */
var LLAMA_BASE="https://justinahiggins614-cmyk.github.io/signature-backend/sigllama/";
var LLAMA_VOCAB="vocab2.json", LLAMA_BIN="sigllama-v2.bin";
var net={{loading:null,ready:false}};
function llamaEnsure(){{
  if(net.ready) return Promise.resolve(true);
  if(net.loading) return net.loading;
  net.loading=new Promise(function(resolve){{
    function fin(ok){{net.ready=!!ok;resolve(net.ready);}}
    function boot(){{try{{
      if(typeof SigLlama==="undefined"){{fin(false);return;}}
      SigLlama.load(LLAMA_BASE,LLAMA_VOCAB,LLAMA_BIN).then(function(){{fin(true);}},function(){{fin(false);}});
    }}catch(e){{fin(false);}}}}
    if(typeof SigLlama!=="undefined"){{boot();return;}}
    var s=document.createElement("script");s.src=LLAMA_BASE+"sigllama.js";s.async=true;
    s.onload=boot;s.onerror=function(){{fin(false);}};document.head.appendChild(s);
  }});
  return net.loading;
}}
/* FIND: keyword scan over the page's own archive list links. */
function findRecords(q){{
  var words=String(q).toLowerCase().split(/[^a-z0-9]+/).filter(function(w){{return w.length>2;}});
  if(!words.length) return [];
  var scope=document.getElementById("jah-askai-scope")||document.querySelector("main")||document.body;
  var links=scope.getElementsByTagName("a"),out=[],seen={{}};
  for(var i=0;i<links.length;i++){{
    var a=links[i];
    if(a.closest("nav")||a.closest("header")||a.closest("footer")||a.closest(".jah-askai")) continue;
    var t=(a.textContent||"").replace(/\\s+/g," ").trim();
    if(t.length<3||t.length>160) continue;
    var tl=t.toLowerCase(),score=0;
    for(var j=0;j<words.length;j++) if(tl.indexOf(words[j])>=0) score++;
    if(score>0&&!seen[a.href]){{seen[a.href]=1;out.push({{t:t,h:a.href,s:score}});}}
    if(out.length>=60) break;
  }}
  out.sort(function(x,y){{return y.s-x.s;}});
  return out.slice(0,5);
}}
function ask(){{
  var q=document.getElementById("jah-askai-q").value.trim();
  var out=document.getElementById("jah-askai-out");
  if(!q){{out.innerHTML="<p>Please type a question first.</p>";return;}}
  var found=findRecords(q),html="";
  if(found.length){{
    html+="<p><b>📎 I found "+found.length+" record"+(found.length>1?"s":"")+" matching your words:</b></p><ul>"+
      found.map(function(f){{return '<li><a href="'+esc(f.h)+'">'+esc(f.t)+"</a></li>";}}).join("")+"</ul>";
  }}else{{
    html+="<p>No record titles matched those words — asking the AI anyway.</p>";
  }}
  html+='<p class="jah-askai-thinking">🤖 thinking…</p>';
  out.innerHTML=html;
  var think=out.querySelector(".jah-askai-thinking");
  llamaEnsure().then(function(ok){{
    if(!ok||typeof SigLlama==="undefined"||!SigLlama.loaded||!SigLlama.loaded()){{
      think.textContent="The AI voice could not load right now — the records above are what matched your words.";return;}}
    var ctx="You are the "+SITE+" archive helper. "+DESC+".\\n"+
      (found.length?("Records matching the question: "+found.map(function(f){{return f.t;}}).join(" | ")+"\\n"):"")+
      "User: "+q.slice(0,300)+"\\nHelper (one to three sentences, plain words):";
    var done=false;
    function show(t){{
      if(done) return; done=true;
      t=String(t||"").trim().replace(/^Helper\\s*:\\s*/i,"");
      if(t.length<8||/User\\s*:/.test(t)) t="I searched the archive for you — the matching records are listed above.";
      think.outerHTML='<p class="jah-askai-ans">🤖 '+esc(t)+"</p>";
    }}
    try{{
      SigLlama.generate(ctx,{{maxTokens:90,temperature:0.5,topK:40}}).then(show,function(){{show("");}});
      setTimeout(function(){{show("");}},25000);
    }}catch(e){{show("");}}
  }});
}}
document.getElementById("jah-askai-go").addEventListener("click",ask);
document.getElementById("jah-askai-q").addEventListener("keydown",function(e){{if(e.key==="Enter")ask();}});
}})();
</script>
</div>


<div class="wrap" id="jah-askai-scope"><div id="results" aria-live="polite"></div></div>

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

    head = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n' + "<script src='js/signin.js'></script><script>/* JAHProfile storage: signed-out behavior is byte-identical to before; signed-in profiles get per-profile namespaced storage. */var PS = (typeof JAHProfile !== 'undefined') ? JAHProfile.store : localStorage;</script>" + '\n' + theme_script +
            '\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">' +
            '\n<title>The Full Archive A&ndash;Z &mdash; The Signature Book Depository</title>' +
            '\n<meta name="description" content="The full A-to-Z archive of The Signature Book Depository: every finished book, magazine issue and library artifact, browsable by letter. Free, no login.">' +
            '\n<link rel="canonical" href="' + BASE + 'archive.html">' +
            '\n<meta property="og:type" content="website">' +
            '\n<meta property="og:title" content="The Full Archive A-Z \u2014 The Signature Book Depository">' +
            '\n<meta property="og:url" content="' + BASE + 'archive.html">' +
            '\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage","name":"The Full Archive A-Z","url":"' + BASE + 'archive.html","isPartOf":{"@type":"WebSite","name":"The Signature Book Depository","url":"' + BASE + '"},"creator":{"@type":"Person","name":"Justin Addam Higgins"}}</script>' +
            "\n" + styles[0] + "\n" + styles[1] + "\n" + extra_css + "\n</head>\n<body>\n")

    # JAH NETWORK nav sits at the BOTTOM: below all content, directly above the
    # footer, one instance per page (Manon's standing order).
    page = head + body + "\n" + jahnet + "\n" + footer + "\n" + js + "\n" + "<script>(function () {  var mount = document.querySelector('header .booksearch') ||              document.querySelector('nav.jtabbar') ||              document.querySelector('header nav') ||              document.querySelector('header') ||              document.body;  if (window.JAHProfile && JAHProfile.ui) JAHProfile.ui.renderButton(mount);})();</script>" + "</body>\n</html>\n"
    with open(os.path.join(ROOT, "archive.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("archive.html written: books=%d mags=%d libs=%d" % (books, mags, libs))

if __name__ == "__main__":
    main()
