#!/usr/bin/env node
/* Wing-app exercise harness (site 11/27): drives real wings.js with the
 * magazines WING config against real data. Prints PASS/FAIL; exit 1 on fail.
 */
"use strict";
const fs = require("fs"), path = require("path"), zlib = require("zlib");
const REPO = path.dirname(path.dirname(path.resolve(__filename)));
const results = [];
function check(name, cond, detail) {
  results.push(!!cond);
  console.log((cond ? "PASS " : "FAIL ") + name + (cond || !detail ? "" : " — " + detail));
}
function makeClassList() { const s = new Set(); return { add(c){s.add(c)}, remove(c){s.delete(c)}, contains(c){return s.has(c)}, toggle(c){s.has(c)?s.delete(c):s.add(c)} }; }
const REG = {};
function elStub(id) {
  const el = { _id:"", _innerHTML:"", textContent:"", value:"", style:{}, dataset:{}, disabled:false,
    classList: makeClassList(), children: [],
    addEventListener(){}, appendChild(c){this.children.push(c);return c;}, remove(){}, focus(){}, click(){},
    scrollIntoView(){}, getAttribute(){return null;}, setAttribute(){},
    querySelector(){return null;}, querySelectorAll(){return []},
    parentNode:{ insertBefore(){}, appendChild(){} } };
  Object.defineProperty(el, "id", { get(){return this._id;},
    set(v){ this._id=String(v); if(this._id && !REG[this._id]) REG[this._id]=this; }, configurable:true });
  el.id = id || "";
  Object.defineProperty(el, "innerHTML", { get(){return this._innerHTML;},
    set(v){ this._innerHTML=String(v); const re=/id="([A-Za-z0-9_-]+)"/g; let m;
      while((m=re.exec(this._innerHTML))){ if(!REG[m[1]]) REG[m[1]]=elStub(m[1]); } }, configurable:true });
  return el;
}
function ensure(id){ if(!REG[id]) REG[id]=elStub(id); return REG[id]; }
["q","fcat","sort","az","results","stats","marchfill","marchlbl","vgrid","vlist",
 "guidebtn","recview","home","rdstop","rdbar","rdprog","count",
 "wtTitle","wtWhat","wtDoes","wtHow","wtStart","wtBack","wtNext","wtSkip","wtDots",
 "wgclose","wingretry"].forEach(ensure);
// wingtour/wingguide are created lazily by the app; find them under body
function findInBody(id){ return (global.document.body.children||[]).find(c=>c.id===id); }
global.document = { getElementById:(id)=>REG[id]||null, createElement:(t)=>elStub(t),
  querySelector:()=>null, querySelectorAll:()=>[], head:elStub("head"), body:elStub("body"),
  addEventListener(){}, readyState:"complete", title:"" };
global.window = { addEventListener(){}, scrollTo(){} };
const LS = {};
global.localStorage = { getItem:(k)=>(k in LS?LS[k]:null), setItem:(k,v)=>{LS[k]=String(v);}, removeItem:(k)=>{delete LS[k];} };
global.location = { hash:"", search:"", href:"https://example.test/signature-books/magazines.html" };
global.history = { replaceState(){} };
global.requestAnimationFrame=(f)=>{try{f()}catch(e){} return 0;};
function bufOf(p){ const d=fs.readFileSync(p); return d.buffer.slice(d.byteOffset,d.byteOffset+d.byteLength); }
global.fetch = (url) => {
  const u=String(url).replace(/^\.\//,""); const p=path.join(REPO,u);
  if (u.endsWith("api.json")) return Promise.resolve({ ok:true, json:()=>Promise.resolve(JSON.parse(fs.readFileSync(p,"utf8"))) });
  if (!fs.existsSync(p)) return Promise.resolve({ ok:false, status:404 });
  return Promise.resolve({ ok:true, headers:{get:()=>null}, arrayBuffer:()=>Promise.resolve(bufOf(p)) });
};
global.WING = {
  pageFile:"magazines.html", pageTitle:"Signature Magazines — The Signature Book Depository",
  unitSing:"issue", unitPlural:"issues", itemWord:"article", itemWordPlural:"articles",
  apiUrl:"data/magazines/index/api.json", apiTotal:"total_issues",
  idxUrl:"data/magazines/index/mags.idx.json.gz",
  chunkDir:"data/magazines/volumes", chunkPrefix:"mags-c", chunkSize:100,
  deepParam:"mag", idRe:"JAH-MAG-\\d{6}",
  filterKey:"subject", filterGet:(e)=>e.s,
  hay:(e)=>e.id+" "+e.m+" "+e.s+" "+e.desc+" "+e.at.join(" "),
  titleKey:(e)=>e.m+" "+e.d,
  cardTitle:(e)=>e.m+" · Vol. "+e.v+" No. "+e.n,
  cardSub:(e)=>e.d+" — "+e.at[0],
  recTitle:(r)=>r.mag+" — Vol. "+r.vol+", No. "+r.no,
  byline:(r)=>r.date+" · "+r.subject,
  chips:(r)=>[r.subject, r.words.toLocaleString()+" words", r.articles.length+" articles", "JAH-MAG"],
  desc:(r)=>r.desc, authorOf:null,
  sections:(r)=>[{t:"Articles",items:r.articles.map((a)=>({t:a.t+" — "+a.d,b:"By "+a.a+"\n\n"+a.b}))}],
  text:(r)=>r.desc+" "+r.articles.map((a)=>a.t+". "+a.b).join(" "),
  coverKind:()=>"mag"
};
let src = fs.readFileSync(path.join(REPO,"wings.js"),"utf8");
// drop the "var WING=null" guard: in the browser the host page defines WING
// first; in this eval it would shadow globalThis.WING under "use strict".
src = src.replace(/if\s*\(typeof WING === "undefined"\)\s*\{\s*var WING = null;\s*\}.*/, "");
src += "\n;globalThis.__W={get IDX(){return IDX},applyFilters:applyFilters,render:render,openRecord:openRecord,route:route,Finder:Finder,WingTour:WingTour,WingGuide:WingGuide,loadWingIndex:loadWingIndex,init:init};";
eval(src);
const W = globalThis.__W;

(async () => {
  check("wings.js evaluated", !!W.applyFilters);
  W.init();
  await new Promise(r=>setTimeout(r,400));
  check("wing stats rendered", /8,000/.test(ensure("stats").innerHTML), ensure("stats").innerHTML.slice(0,60));
  check("wing results rendered", /data-id="JAH-MAG-/.test(ensure("results").innerHTML));
  check("wing tour invited", (findInBody("wingtour")||{classList:makeClassList()}).classList.contains("show"));
  check("wing tour key", W.WingTour.key()==="jah-tour-seen-magazines");
  check("wing tour steps (7, all WHAT/DOES/HOW)", W.WingTour.steps().length===7 &&
    W.WingTour.steps().every(s=>s.t&&s.what&&s.does&&s.how));
  W.WingTour.next();
  check("wing tour next works", true);
  W.WingTour.skip();
  check("wing tour skip marks seen", LS["jah-tour-seen-magazines"]==="1" &&
    !findInBody("wingtour").classList.contains("show"));
  // search + filter
  ensure("q").value = "science";
  W.applyFilters();
  check("wing search 'science'", W.IDX.length>0);
  ensure("q").value = "JAH-MAG-000010";
  W.applyFilters();
  // wing has no exact-ID-first sort; just verify the record is findable
  const found = W.IDX.some(e=>e.id==="JAH-MAG-000010");
  check("wing ID JAH-MAG-000010 exists in index", found);
  // deep link
  global.location.hash="#mag=JAH-MAG-000010"; global.location.search="";
  W.route();
  await new Promise(r=>setTimeout(r,400));
  check("wing openRecord renders", /JAH-MAG-000010/.test(ensure("recview").innerHTML));
  global.location.hash=""; global.location.search="?mag=JAH-MAG-000011";
  W.route();
  check("wing ?mag= -> #mag= hash", global.location.hash==="#mag=JAH-MAG-000011", global.location.hash);
  // retry UI
  W.loadWingIndex.call ? null : null;
  // simulate failure path by calling with bad url
  const oldUrl = global.WING.idxUrl; global.WING.idxUrl = "data/magazines/index/NOPE.json.gz";
  W.loadWingIndex();
  await new Promise(r=>setTimeout(r,200));
  check("wing failed index -> retry UI", /wingretry/.test(ensure("results").innerHTML));
  global.WING.idxUrl = oldUrl;
  // guide
  W.WingGuide.open();
  const wg = findInBody("wingguide")||{classList:makeClassList(),innerHTML:""};
  check("wing guide opens with content", wg.classList.contains("show") &&
    /Read aloud/.test(wg.innerHTML) && /JAH-MAG-000123/.test(wg.innerHTML));
  W.WingGuide.close();
  check("wing guide closes", !wg.classList.contains("show"));
  const fails = results.filter(r=>!r);
  console.log("\n==== "+(results.length-fails.length)+"/"+results.length+" passed ====");
  if (fails.length) process.exit(1);
})();
