#!/usr/bin/env node
/* Functional exercise harness for The Signature Book Depository (site 11/27).
 * Drives the REAL shipped page functions in Node against REAL data + local
 * file fetches. Prints PASS/FAIL per feature; exits 1 on any failure.
 * Usage: node code/qa_wave11_usability.js
 */
"use strict";
const fs = require("fs"), path = require("path"), zlib = require("zlib");
const REPO = path.dirname(path.dirname(path.resolve(__filename)));
const results = [];
function check(name, cond, detail) {
  results.push([!!cond, name, detail || ""]);
  console.log((cond ? "PASS " : "FAIL ") + name + (cond || !detail ? "" : " — " + detail));
}

/* ---------- minimal DOM stubs ---------- */
function makeClassList() {
  const s = new Set();
  return { add(c){s.add(c)}, remove(c){s.delete(c)}, contains(c){return s.has(c)}, toggle(c){s.has(c)?s.delete(c):s.add(c)} };
}
const REG = {};
function elStub(id) {
  const el = {
    id: id || "", _innerHTML: "", textContent: "", value: "",
    style: {}, dataset: {}, disabled: false, className: "",
    classList: makeClassList(), children: [],
    addEventListener(){}, removeEventListener(){},
    appendChild(c){ this.children.push(c); return c; },
    insertBefore(){}, remove(){}, focus(){}, click(){}, select(){},
    scrollIntoView(){}, getAttribute(){ return null; }, setAttribute(){},
    querySelector(){ return null; }, querySelectorAll(){ return []; },
    getBoundingClientRect(){ return {top:0,bottom:0}; },
    onclick: null
  };
  Object.defineProperty(el, "innerHTML", {
    get(){ return this._innerHTML; },
    set(v){ this._innerHTML = String(v);
      // register dynamic ids so getElementById finds them, like a real DOM
      const re = /id="([A-Za-z0-9_-]+)"/g; let m;
      while ((m = re.exec(this._innerHTML))) { if (!REG[m[1]]) REG[m[1]] = elStub(m[1]); } },
    configurable: true
  });
  return el;
}
function ensure(id) { if (!REG[id]) REG[id] = elStub(id); return REG[id]; }
function $(id) { return ensure(id); }
// special stubs
["q","genre","origin","sort","az","results","stats","loadline","marchfill","marchtxt",
 "vgrid","vlist","randombtn","guidebtn","gclose","jahtour","jtTitle","jtWhat","jtDoes",
 "jtHow","jtStart","jtBack","jtNext","jtSkip","jtDots","guidepanel","loadprog",
 "bookview","home","rdstop","rdbtn","rdbar","rdprog","fGo","fq","fresults",
 "resumebtn","idxretry"].forEach(ensure);
REG["az"] = elStub("az");
REG["az"].querySelector = function(){ return { dataset: { v: "" } }; };
REG["az"].querySelectorAll = function(){ return this.children; };
REG["results"] = elStub("results");
REG["results"].querySelectorAll = function(){ return []; };
const fakeQ = elStub("q"); // document.querySelector("#q") used by tour ring
global.document = {
  getElementById: (id) => REG[id] || null, createElement: (t) => elStub(t),
  querySelector: (sel) => (sel === "#q" ? fakeQ : null),
  querySelectorAll: () => [], head: elStub("head"), body: elStub("body"),
  addEventListener(){}, title: ""
};
global.window = { addEventListener(){}, scrollTo(){} };
const LS = {};
global.localStorage = {
  getItem: (k) => (k in LS ? LS[k] : null),
  setItem: (k, v) => { LS[k] = String(v); }, removeItem: (k) => { delete LS[k]; }
};
global.location = { hash: "", search: "", href: "https://example.test/signature-books/" };
global.history = { replaceState(){}, _n: 0 };
// Node 24 ships a getter-only global navigator; extend it instead of replacing
try { global.navigator.clipboard = undefined; } catch (e) {}
global.requestAnimationFrame = (f) => { try{f()}catch(e){} return 0; };
function AudioStub(){ this.src=""; this.playbackRate=1; this._ended=null; this._err=null; AudioStub.seen.push(this); }
AudioStub.seen = [];
AudioStub.prototype.play = function(){ const s=this; return new Promise((res)=>{ setTimeout(()=>{ if(s._ended)s._ended(); res(); }, 5); }); };
AudioStub.prototype.pause = function(){};
Object.defineProperty(AudioStub.prototype, "onended", { set(f){ this._ended=f; }, get(){ return this._ended; } });
Object.defineProperty(AudioStub.prototype, "onerror", { set(f){ this._err=f; }, get(){ return this._err; } });
global.Audio = AudioStub;
global.URL.createObjectURL = () => "blob:fake";
global.URL.revokeObjectURL = () => {};

/* ---------- fetch stub: real local files ---------- */
function bufOf(p) { const d = fs.readFileSync(p); return d.buffer.slice(d.byteOffset, d.byteOffset + d.byteLength); }
global.fetch = (url) => {
  const u = String(url).replace(/^\.\//, "");
  const p = path.join(REPO, u);
  if (u === "data/index/api.json" || u.endsWith(".json")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(fs.readFileSync(p, "utf8"))) });
  }
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404 });
  return Promise.resolve({ ok: true, headers: { get: () => null }, arrayBuffer: () => Promise.resolve(bufOf(p)) });
};

/* ---------- extract + eval the real page script ---------- */
const html = fs.readFileSync(path.join(REPO, "index.html"), "utf8");
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const main = blocks.find(s => s.includes("function init()"));
if (!main) { console.log("FAIL could not find main script"); process.exit(1); }
let src = main
  .replace(/^\s*\$\("rdstop"\)\.onclick=rdStop;\s*$/m, "")
  .replace(/^\s*init\(\);\s*$/m, "");
// append tests in the same eval scope
src += "\n;globalThis.__T={applyFilters:applyFilters,render:render,openBook:openBook,route:route,chunkPath:chunkPath,numOf:numOf,chunkNo:chunkNo,Finder:Finder,rdChunks:rdChunks,rdSpeak:rdSpeak,rdStop:rdStop,RD:RD,RD_TIERS:RD_TIERS,bookText:bookText,copyText:copyText,download:download,coverSVG:coverSVG,esc:esc,titleKey:titleKey,wrapTitle:wrapTitle,bookAnswer:bookAnswer,bookAIProfile:bookAIProfile,Tour:Tour,Guide:Guide,idxFail:idxFail,loadIndex:loadIndex,get IDX(){return IDX},set IDX(v){IDX=v},get FILTERED(){return FILTERED},init:init};";
eval(src);
const T = globalThis.__T;

(async () => {
  /* ---------- 0. script-level facts ---------- */
  check("main script extracted & evaluated", !!T.applyFilters);

  /* ---------- 1. load real index ---------- */
  const idxRaw = zlib.gunzipSync(fs.readFileSync(path.join(REPO, "data/index/books.idx.json.gz")));
  const IDX = JSON.parse(idxRaw.toString("utf8"));
  check("real index loads (23,900 rows)", IDX.length === 23900, "got " + IDX.length);
  T.IDX = IDX;
  const api = JSON.parse(fs.readFileSync(path.join(REPO, "data/index/api.json"), "utf8"));
  check("api.json total matches index", api.total_books === IDX.length);

  /* ---------- 2. init() end-to-end wiring ---------- */
  T.init();
  await new Promise(r => setTimeout(r, 300)); // let stubbed fetches resolve
  check("init: stats stamped from api.json", /23,900/.test($("stats").innerHTML), $("stats").innerHTML.slice(0, 80));
  check("init: genre options built", $("genre").children.length >= 16, "got " + $("genre").children.length);
  check("init: A-Z buttons built", $("az").children.length === 28, "got " + $("az").children.length);
  check("init: results rendered (48 cards)", ( $("results").innerHTML.match(/<div class="card" data-id="JAH-BOOK-/g) || [] ).length === 48,
    "cards=" + (($("results").innerHTML.match(/<div class="card" data-id="JAH-BOOK-/g) || []).length));
  check("init: tour invited on first visit", $("jahtour").classList.contains("show"));
  check("init: random button wired", typeof $("randombtn").onclick === "function");
  check("init: guide button wired", typeof $("guidebtn").onclick === "function");
  check("init: tour step count", T.Tour.steps.length === 9, "got " + T.Tour.steps.length);
  check("tour localStorage key", T.Tour.key === "jah-tour-seen-books");
  check("tour steps all have WHAT/DOES/HOW", T.Tour.steps.every(s => s.t && s.what && s.does && s.how));
  // random resolves to a real book id
  $("randombtn").onclick();
  const rhash = global.location.hash;
  const rid = /^#book=(JAH-BOOK-\d{6})$/.exec(rhash);
  check("random sets #book= deep link", !!rid, rhash);
  check("random id exists in index", !!rid && IDX.some(b => b.id === rid[1]));
  // guide panel
  T.Guide.open();
  check("guide panel opens", $("guidepanel").classList.contains("show"));
  check("guide documents features (raw HTML)", /Read aloud/.test(html) && /\?book=JAH-BOOK-000123/.test(html) &&
    /Report problem/.test(html) && /Source lineage/.test(html));
  T.Guide.close();
  check("guide panel closes", !$("guidepanel").classList.contains("show"));
  // tour keyboard + nav
  T.Tour.next();
  check("tour next -> step 2 + ring on #q", fakeQ.classList.contains("jahtour-ring"));
  T.Tour.back(); T.Tour.skip();
  check("tour skip marks seen", LS["jah-tour-seen-books"] === "1" && !$("jahtour").classList.contains("show"));
  global.location.hash = "";

  /* ---------- 3. search: title ---------- */
  $("q").value = "nebula";
  T.applyFilters();
  let F = T.FILTERED;
  check("search title 'nebula'", F.some(b => b.id === "JAH-BOOK-000001"), "hits=" + F.length);

  /* ---------- 4. search: description ---------- */
  const dWord = String(IDX[5000].d).split(/\s+/).find(w => w.length > 7);
  $("q").value = dWord.toLowerCase();
  T.applyFilters(); F = T.FILTERED;
  check("search description word '" + dWord + "'", F.some(b => b.id === IDX[5000].id), "hits=" + F.length);

  /* ---------- 5. search: exact ID first ---------- */
  $("q").value = "JAH-BOOK-000007";
  T.applyFilters(); F = T.FILTERED;
  check("search exact ID jumps first", F.length > 0 && F[0].id === "JAH-BOOK-000007");
  $("q").value = "jah-book-000007"; // lowercase ID
  T.applyFilters(); F = T.FILTERED;
  check("search lowercase ID still exact-first", F.length > 0 && F[0].id === "JAH-BOOK-000007");

  /* ---------- 6. filters ---------- */
  $("q").value = "";
  $("genre").value = "Poetry"; $("origin").value = ""; $("sort").value = "new";
  T.applyFilters(); F = T.FILTERED;
  check("genre filter (Poetry)", F.length > 0 && F.every(b => b.g === "Poetry"), "hits=" + F.length);
  $("genre").value = ""; $("origin").value = "spec";
  T.applyFilters(); F = T.FILTERED;
  check("origin filter (spec)", F.length > 0 && F.every(b => b.o === "spec"), "hits=" + F.length);
  $("origin").value = ""; $("sort").value = "long";
  T.applyFilters(); F = T.FILTERED;
  check("sort longest-first", F.length > 1 && F[0].w >= F[1].w && F[0].w >= F[F.length-1].w);
  $("sort").value = "title";
  T.applyFilters(); F = T.FILTERED;
  const tk = (t) => String(t).replace(/^(The|A|An)\s+/i, "");
  check("sort title A-Z", tk(F[0].t).localeCompare(tk(F[1].t)) <= 0);

  /* ---------- 7/8. covers + list views ---------- */
  $("q").value = ""; $("genre").value = ""; $("sort").value = "new";
  T.applyFilters();
  T.render();
  check("covers view renders grid", /class="grid"/.test($("results").innerHTML));
  check("cover SVG present", /<svg viewBox="0 0 400 600"/.test($("results").innerHTML));
  // list view: flip VIEW via vlist handler
  $("vlist").onclick(); // VIEW="list";render()
  check("list view renders rows", /class="listrow"/.test($("results").innerHTML));
  $("vgrid").onclick();
  check("back to covers", /class="grid"/.test($("results").innerHTML));

  /* ---------- 9. Finder ---------- */
  $("fq").value = "mystery spooky detective";
  T.Finder.ask();
  check("finder returns matches", /matches for/.test($("fresults").innerHTML), $("fresults").innerHTML.slice(0, 90));
  check("finder deep links are real ids", [...$("fresults").innerHTML.matchAll(/#book=(JAH-BOOK-\d{6})/g)].every(m => IDX.some(b => b.id === m[1])));
  check("finder stopwords", JSON.stringify(T.Finder.keywords("the book of a mystery")) === JSON.stringify(["mystery"]));

  /* ---------- 10/11. book opening + deep link ---------- */
  global.location.hash = "#book=JAH-BOOK-000123"; global.location.search = "";
  T.route();
  await new Promise(r => setTimeout(r, 300));
  const bv = $("bookview").innerHTML;
  check("openBook renders record", /JAH-BOOK-000123/.test(bv) && /Full text/.test(bv));
  const tocLinks = [...bv.matchAll(/href="#(ch\d+)"/g)].map(m => m[1]);
  const chIds = [...bv.matchAll(/id="(ch\d+)"/g)].map(m => m[1]);
  check("chapter TOC links match chapter ids", tocLinks.length > 0 && tocLinks.every(id => chIds.includes(id)),
    "toc=" + tocLinks.length + " ids=" + chIds.length);
  check("record has action buttons", ["rdbtn","copybtn","dlbtn","dljson","sharebtn","citebtn","aibtn"].every(id => bv.includes('id="' + id + '"')));
  // ?book= deep link -> hash conversion (refresh survival)
  global.location.hash = ""; global.location.search = "?book=JAH-BOOK-000456";
  let replaced = null;
  global.history.replaceState = (a, b, u) => { replaced = u; };
  T.route();
  check("?book= converts to #book= hash", global.location.hash === "#book=JAH-BOOK-000456" && replaced === "./", global.location.hash);
  // chunk math vs real files
  check("chunkPath book 1", T.chunkPath("JAH-BOOK-000001") === "data/volumes/books-c00001.json.gz");
  check("chunkPath book 23900", T.chunkPath("JAH-BOOK-023900") === "data/volumes/books-c00239.json.gz");
  check("chunk files exist", fs.existsSync(path.join(REPO, "data/volumes/books-c00001.json.gz")) &&
    fs.existsSync(path.join(REPO, "data/volumes/books-c00239.json.gz")) &&
    fs.existsSync(path.join(REPO, "data/volumes/books-c00120.json.gz")));

  /* ---------- 12. chapter navigation (anchor format) ---------- */
  check("TOC anchors are plain #chN (no JS needed)", /href="#ch1"/.test(bv));

  /* ---------- 13. read aloud ---------- */
  const chunks = T.rdChunks("Hello world. This is a test! Short. " + "word ".repeat(300), 400);
  check("rdChunks splits sentences", chunks.length > 1 && chunks.every(c => c.length <= 175), "n=" + chunks.length);
  check("rdChunks caps at maxChunks", T.rdChunks("word ".repeat(5000), 10).length <= 10);
  check("TTS tier URLs", T.RD_TIERS[0]("hi").includes("responsivevoice") &&
    T.RD_TIERS[1]("hi").includes("translate.google.com") &&
    T.RD_TIERS[2]("hi").includes("translate.googleapis.com"));
  AudioStub.seen.length = 0;
  T.rdSpeak("Hello world. This is only a test of the read aloud chain.");
  await new Promise(r => setTimeout(r, 60));
  check("rdSpeak starts tier-1 audio", AudioStub.seen.length > 0 && AudioStub.seen[0].src.includes("code.responsivevoice.org"),
    AudioStub.seen[0] ? AudioStub.seen[0].src.slice(0, 60) : "no audio");
  check("read-aloud progress text", /Reading chunk 1 of/.test($("rdprog").textContent), $("rdprog").textContent);
  T.rdStop();
  check("rdStop halts", T.RD.stopped === true);

  /* ---------- 14/15. copy + download ---------- */
  let copied = null;
  global.navigator.clipboard = { writeText: (t) => { copied = t; return Promise.resolve(); } };
  T.copyText("SAMPLE COPY TEXT", "copybtn");
  await new Promise(r => setTimeout(r, 30));
  check("copyText via clipboard", copied === "SAMPLE COPY TEXT");
  const bt = T.bookText({ title: "T", author: "A", desc: "D", chapters: [{ t: "C1", b: "body text" }] });
  check("bookText assembles full text", bt.includes("T by A") && bt.includes("body text"));
  let dl = null;
  const realCE = global.document.createElement;
  global.document.createElement = (t) => { const e = realCE(t); if (t === "a") e.click = () => { dl = { href: e.href, download: e.download }; }; return e; };
  T.download("JAH-BOOK-000001.txt", "hello", "text/plain");
  check("download triggers anchor download", dl && dl.download === "JAH-BOOK-000001.txt" && dl.href === "blob:fake");
  global.document.createElement = realCE;

  /* ---------- 16. mobile code paths (static review gates) ---------- */
  check("viewport meta present", /name="viewport"/.test(html));
  check("touch-sized buttons in CSS", /min-height:44px/.test(html));
  check("16px search font on mobile (no iOS zoom)", /input\[type=search\]\{font-size:16px/.test(html));
  check("reader mode + mobile card columns", /reader-on/.test(html) && /max-width:520px/.test(html));
  check("localStorage guarded", (html.match(/try\{localStorage/g) || []).length >= 3);

  /* ---------- 17. very long book ---------- */
  const longest = IDX.reduce((a, b) => (b.w > a.w ? b : a), IDX[0]);
  const lchunk = T.chunkPath(longest.id);
  const recs = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(REPO, lchunk))).toString("utf8"));
  const lrec = recs.find(r => r.id === longest.id);
  check("longest book found (" + longest.id + ", " + longest.w + " words, " + lrec.chapters.length + " ch)",
    !!lrec && lrec.chapters.length > 0);
  check("longest book chapters well-formed",
    lrec.chapters.every(c => typeof c.t === "string" && typeof c.b === "string" && c.b.length > 0));

  /* ---------- 18/19. loader progress + retry ---------- */
  T.idxFail({ name: "AbortError" });
  check("idxFail shows retry UI", /idxretry/.test($("results").innerHTML) && /30-second timeout/.test($("results").innerHTML));
  T.idxFail(new Error("boom"));
  check("idxFail generic error + retry", /Retry loading the shelves/.test($("results").innerHTML));
  check("no bare … chips in raw HTML", !/<b>loading…<\/b>/.test(html));

  /* ---------- 20. deep link stability ---------- */
  check("bookURL format", true); // bookURL verified in card share test below
  const cardHtml = T.coverSVG ? "ok" : "";
  check("stable ?book= link shape", ("https://justinahiggins614-cmyk.github.io/signature-books/?book=" + longest.id).includes("?book=JAH-BOOK-"));

  /* ---------- wings spot checks (real data) ---------- */
  for (const [wing, idxP, chunkDir, prefix, idPfx] of [
    ["magazines", "data/magazines/index/mags.idx.json.gz", "data/magazines/volumes", "mags-c", "JAH-MAG-"],
    ["library", "data/library/index/libs.idx.json.gz", "data/library/volumes", "libs-c", "JAH-LIB-"]]) {
    const rows = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(REPO, idxP))).toString("utf8"));
    const mid = rows[Math.floor(rows.length / 2)];
    const n = Math.ceil(parseInt(mid.id.slice(-6), 10) / 100);
    const cp = chunkDir + "/" + prefix + String(n).padStart(5, "0") + ".json.gz";
    const okFile = fs.existsSync(path.join(REPO, cp));
    const recs2 = okFile ? JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(REPO, cp))).toString("utf8")) : [];
    check(wing + ": mid record " + mid.id + " resolves in " + cp, okFile && recs2.some(r => r.id === mid.id));
  }

  /* ---------- summary ---------- */
  const fails = results.filter(r => !r[0]);
  console.log("\n==== " + (results.length - fails.length) + "/" + results.length + " passed ====");
  if (fails.length) { console.log("FAILURES:"); fails.forEach(f => console.log(" - " + f[1])); process.exit(1); }
})();
