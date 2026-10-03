/* Shared catalog app for the Book Depository wings (Magazines, Library).
   Generic over WING config set by the host page. Parchment/gold look matching index.html. */
"use strict";
if (typeof WING === "undefined") { var WING = null; } // set by host page before this script runs
function $(id){return document.getElementById(id)}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function hashStr(s){var h=2166136261;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=(h*16777619)>>>0}return h}
function numOf(id){var m=/(\d+)$/.exec(id);return m?parseInt(m[1],10):0}
function gunzip(buf){return new Response(buf).arrayBuffer().then(function(ab){
  if(typeof DecompressionStream==="undefined")throw new Error("no gzip");
  var ds=new DecompressionStream("gzip");
  return new Response(new Blob([ab]).stream().pipeThrough(ds)).arrayBuffer()})}
function fetchJSONgz(url){return fetch(url).then(function(r){if(!r.ok)throw new Error("fetch "+r.status);return r.arrayBuffer()}).then(gunzip).then(function(ab){
  return JSON.parse(new TextDecoder().decode(ab))})}

var IDX=[], FILTERED=[], SHOWN=0, PAGE=60, VIEW="grid", CUR=null, CURTEXT="";
var PALS=[["#7a1f1f","#e8c860","#f3ead2"],["#1f3a5f","#9fc2ff","#eef3ff"],["#1e5c38","#cfe8a0","#f2f7e6"],
          ["#5b2a6e","#d9a7e8","#f6ecfa"],["#8a5a17","#ffd98a","#fdf3dd"],["#0f4c4c","#8ad8d8","#eafafa"]];

/* ---------------- covers ---------------- */
function coverSVG(kind, seedStr, line1, line2, line3){
  var h=hashStr(seedStr), pal=PALS[h%PALS.length], W=300, H=420, s="";
  function R(n){h=(h*1103515245+12345)>>>0;return h%n}
  s+='<svg viewBox="0 0 '+W+' '+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="'+esc(line1)+' cover">';
  s+='<rect width="'+W+'" height="'+H+'" fill="'+pal[0]+'"/>';
  s+='<rect x="10" y="10" width="'+(W-20)+'" height="'+(H-20)+'" fill="none" stroke="'+pal[1]+'" stroke-width="3"/>';
  if(kind==="mag"){
    s+='<rect x="10" y="10" width="'+(W-20)+'" height="86" fill="'+pal[1]+'"/>';
    s+='<text x="'+(W/2)+'" y="48" text-anchor="middle" font-family="Georgia,serif" font-weight="bold" font-size="21" fill="'+pal[0]+'">'+esc(line1).slice(0,26)+'</text>';
    s+='<text x="'+(W/2)+'" y="72" text-anchor="middle" font-family="Georgia,serif" font-size="13" fill="'+pal[0]+'">'+esc(line2).slice(0,34)+'</text>';
    for(var i=0;i<5;i++){var y=130+i*46;R(3);
      s+='<rect x="28" y="'+y+'" width="'+(190-R(60))+'" height="10" fill="'+pal[1]+'" opacity="0.85"/>';
      s+='<rect x="28" y="'+(y+16)+'" width="'+(150-R(60))+'" height="7" fill="'+pal[2]+'" opacity="0.5"/>'}
    s+='<text x="'+(W/2)+'" y="'+(H-40)+'" text-anchor="middle" font-family="Georgia,serif" font-size="15" fill="'+pal[2]+'">'+esc(line3).slice(0,30)+'</text>';
    for(var b=0;b<24;b++){s+='<rect x="'+(24+b*10)+'" y="'+(H-26)+'" width="'+(3+R(5))+'" height="14" fill="'+pal[2]+'"/>'}
  }else{
    var cx=W/2, cy=190;
    if(kind==="microfilm"){
      s+='<circle cx="'+cx+'" cy="'+cy+'" r="95" fill="#0c0c10" stroke="'+pal[1]+'" stroke-width="5"/>';
      s+='<circle cx="'+cx+'" cy="'+cy+'" r="22" fill="'+pal[1]+'"/>';
      for(var k=0;k<6;k++){var a=k*Math.PI/3;s+='<circle cx="'+(cx+60*Math.cos(a))+'" cy="'+(cy+60*Math.sin(a))+'" r="16" fill="'+pal[0]+'" stroke="'+pal[1]+'" stroke-width="3"/>'}
    }else if(kind==="atlas"){
      s+='<path d="M40,120 Q110,90 150,150 T260,140 T250,260 T120,270 T50,210 Z" fill="'+pal[1]+'" opacity="0.85"/>';
      s+='<circle cx="215" cy="235" r="26" fill="none" stroke="'+pal[2]+'" stroke-width="3"/>';
      s+='<path d="M215,215 L215,255 M195,235 L235,235" stroke="'+pal[2]+'" stroke-width="3"/>';
      s+='<path d="M40,300 Q150,285 260,305" stroke="'+pal[2]+'" stroke-width="2" fill="none" opacity="0.6"/>';
    }else if(kind==="manuscript"){
      s+='<rect x="70" y="90" width="160" height="220" rx="8" fill="'+pal[2]+'"/>';
      s+='<rect x="60" y="80" width="160" height="220" rx="8" fill="#fbf6e6" stroke="'+pal[1]+'" stroke-width="2"/>';
      for(var l=0;l<9;l++){s+='<rect x="80" y="'+(120+l*20)+'" width="'+(120-R(30))+'" height="6" fill="'+pal[0]+'" opacity="0.55"/>'}
    }else if(kind==="reference"){
      for(var bk=0;bk<4;bk++){var bx=70+bk*42;s+='<rect x="'+bx+'" y="'+(140-bk*8)+'" width="34" height="180" fill="'+pal[1]+'" opacity="'+(0.65+bk*0.1)+'"/>'}
      s+='<rect x="60" y="310" width="180" height="10" fill="'+pal[1]+'"/>';
    }else{
      s+='<rect x="80" y="170" width="140" height="100" rx="10" fill="'+pal[1]+'"/>';
      s+='<rect x="80" y="150" width="140" height="40" rx="10" fill="'+pal[0]+'" stroke="'+pal[1]+'" stroke-width="3"/>';
      s+='<circle cx="'+cx+'" cy="170" r="10" fill="'+pal[2]+'"/>';
      s+='<path d="M'+cx+',180 L'+cx+',240 M100,190 L200,190" stroke="'+pal[0]+'" stroke-width="4"/>';
    }
    var words=String(line1).split(/\s+/), lines=[], cur="";
    words.forEach(function(w){if((cur+" "+w).trim().length>18){if(cur)lines.push(cur);cur=w}else cur=(cur+" "+w).trim()});
    if(cur)lines.push(cur); lines=lines.slice(0,3);
    lines.forEach(function(ln,i){s+='<text x="'+cx+'" y="'+(330+i*30)+'" text-anchor="middle" font-family="Georgia,serif" font-weight="bold" font-size="22" fill="'+pal[2]+'">'+esc(ln)+'</text>'});
    s+='<text x="'+cx+'" y="'+(H-30)+'" text-anchor="middle" font-family="Georgia,serif" font-size="14" fill="'+pal[1]+'">'+esc(line3).slice(0,34)+'</text>';
  }
  return s+"</svg>";
}

/* ---------------- catalog home ---------------- */
function init(){
  fetch(WING.apiUrl).then(function(r){return r.json()}).then(function(api){
    var st=$("stats"); if(!st)return;
    st.innerHTML='<div class="stat"><b>'+Number(api[WING.apiTotal]).toLocaleString()+'</b><span>'+WING.unitPlural+' on shelf</span></div>'+
      '<div class="stat"><b>'+Number(api.total_words).toLocaleString()+'</b><span>words</span></div>'+
      '<div class="stat"><b>1,000,000</b><span>march goal</span></div>';
    var pct=Math.min(100, 100*api[WING.apiTotal]/1000000);
    $("marchfill").style.width=pct+"%";
    $("marchlbl").textContent=Number(api[WING.apiTotal]).toLocaleString()+" of 1,000,000 "+WING.unitPlural+" ("+pct.toFixed(2)+"%)";
  }).catch(function(){});
  Finder.setup();fetchJSONgz(WING.idxUrl).then(function(idx){IDX=idx;buildFilters();buildAZ();route();})
    .catch(function(){$("results").innerHTML='<div class="loading">Could not load the catalog index. Check your connection and reload.</div>'});
  var q=$("q"); if(q)q.addEventListener("input",function(){applyFilters()});
  var fs=$("fcat"); if(fs)fs.addEventListener("change",applyFilters);
  var so=$("sort"); if(so)so.addEventListener("change",applyFilters);
  if($("vgrid"))$("vgrid").onclick=function(){VIEW="grid";render()};
  if($("vlist"))$("vlist").onclick=function(){VIEW="list";render()};
  window.addEventListener("hashchange",route);
}
function buildFilters(){
  var fs=$("fcat"); if(!fs||!WING.filterKey)return;
  var vals={}; IDX.forEach(function(e){vals[WING.filterGet(e)]=1});
  Object.keys(vals).sort().forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;fs.appendChild(o)});
}
function buildAZ(){
  var box=$("az"); if(!box)return; box.innerHTML="";
  var mk=function(lbl,val){var b=document.createElement("button");b.textContent=lbl;b.dataset.v=val;
    b.onclick=function(){box.querySelectorAll("button").forEach(function(x){x.classList.remove("on")});b.classList.add("on");applyFilters()};box.appendChild(b)};
  mk("#",""); "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach(function(l){mk(l,l)});
}
function azVal(){var b=$("az").querySelector("button.on");return b?b.dataset.v:""}
function applyFilters(){
  var q=$("q").value.trim().toLowerCase(), fc=$("fcat")?$("fcat").value:"", L=azVal(), s=$("sort").value;
  FILTERED=IDX.filter(function(e){
    if(fc&&WING.filterGet(e)!==fc)return false;
    if(L&&WING.titleKey(e).toUpperCase().charAt(0)!==L)return false;
    if(q){var hay=WING.hay(e).toLowerCase();if(hay.indexOf(q)<0)return false}
    return true});
  if(s==="title")FILTERED.sort(function(a,b){return WING.titleKey(a).localeCompare(WING.titleKey(b))});
  else if(s==="long")FILTERED.sort(function(a,b){return b.w-a.w});
  else FILTERED.sort(function(a,b){return b.id<a.id?-1:1});
  SHOWN=0;render();
  $("count").textContent=FILTERED.length.toLocaleString()+" "+WING.unitPlural;
}
function cardHTML(e){
  var cov=coverSVG(WING.coverKind(e), e.id, WING.cardTitle(e), WING.cardSub(e), e.id);
  if(VIEW==="grid")return '<div class="card" data-id="'+e.id+'">'+cov+'<div class="meta"><div class="t">'+esc(WING.cardTitle(e))+'</div><div class="a">'+esc(WING.cardSub(e))+'</div><div class="g">'+esc(e.id)+'</div><div style="margin-top:4px"><span class="stbadge">SIGNATURE ORIGINAL</span></div></div></div>';
  return '<div class="listrow" data-id="'+e.id+'">'+cov+'<div><div class="t">'+esc(WING.cardTitle(e))+'</div><div class="a">'+esc(WING.cardSub(e))+'</div><div class="g">'+esc(e.id)+'</div><div style="margin-top:3px"><span class="stbadge">SIGNATURE ORIGINAL</span></div></div></div>';
}
function render(){
  var box=$("results");
  var slice=FILTERED.slice(0,SHOWN+PAGE); SHOWN+=PAGE;
  box.innerHTML='<div class="'+(VIEW==="grid"?"grid":"")+'">'+slice.map(cardHTML).join("")+"</div>"+
    (FILTERED.length>SHOWN?'<button class="btn more" id="morebtn">Show more ('+(FILTERED.length-SHOWN).toLocaleString()+' left)</button>':"");
  box.querySelectorAll("[data-id]").forEach(function(el){el.onclick=function(){location.hash="#"+WING.deepParam+"="+el.dataset.id}});
  var mb=$("morebtn"); if(mb)mb.onclick=function(){render();window.scrollTo(0,document.body.scrollHeight)};
}
function route(){
  var m=new RegExp("^#"+WING.deepParam+"=("+WING.idRe+")").exec(location.hash||"");
  if(!m){var qp=null;try{qp=new URLSearchParams(location.search).get(WING.deepParam)}catch(e){}
    if(qp&&new RegExp("^"+WING.idRe+"$").test(qp)){try{history.replaceState(null,"","./"+WING.pageFile)}catch(e2){}location.hash="#"+WING.deepParam+"="+qp;return}}
  else{openRecord(m[1]);return}
  rdStop();$("recview").style.display="none";$("home").style.display="block";document.title=WING.pageTitle;applyFilters();
}
function findIdx(id){for(var i=0;i<IDX.length;i++)if(IDX[i].id===id)return IDX[i];return null}
function openRecord(id){
  rdStop();$("home").style.display="none";var rv=$("recview");rv.style.display="block";
  rv.innerHTML='<div class="loading">Opening '+esc(id)+'…</div>';window.scrollTo(0,0);
  var n=Math.ceil(numOf(id)/WING.chunkSize);
  fetchJSONgz(WING.chunkDir+"/"+WING.chunkPrefix+String(n).padStart(5,"0")+".json.gz").then(function(recs){
    var rec=null;for(var i=0;i<recs.length;i++)if(recs[i].id===id)rec=recs[i];
    if(!rec)throw new Error("not in chunk");
    CUR=rec;CURTEXT=WING.text(rec);renderRecord(rec);
    document.title=WING.recTitle(rec)+" — "+WING.pageTitle;
  }).catch(function(){rv.innerHTML='<div class="loading">Could not open '+esc(id)+'. <a href="#">Back</a></div>'});
}

/* ---------------- record view + per-record AI ---------------- */
/* JAH NETWORK 10-FIX: record panel + provenance + AI identity card (additive) */
function wingSeedBase(id){return /^JAH-LIB-/.test(id)?20261003:/^JAH-MAG-/.test(id)?20261002:20261001}
function wingProvHTML(rec){
  var n=numOf(rec.id);
  return '<div class="prov">Provenance: made by the '+esc(WING.pageTitle.split(" — ")[0])+' generator · deterministic record seed '+wingSeedBase(rec.id)+'+'+n+' · record date not recorded per record (deterministic — the same seed regenerates the same record)</div>';
}
function wingPanelHTML(rec){
  return '<div class="recpanel" role="group" aria-label="Record actions"><span class="rpid">ID: '+esc(rec.id)+'</span><span class="rpver">VERSION v1.0</span>'+
  '<button data-rp="open">OPEN</button><button data-rp="src">SOURCE</button><button data-rp="share">SHARE</button>'+
  '<button data-rp="copy">COPY</button><button data-rp="dl">DOWNLOAD</button><button data-rp="read">READ ALOUD</button></div>';
}
function wingWirePanel(rec){
  var panel=document.querySelector("#recview .recpanel");if(!panel)return;
  var n=Math.ceil(numOf(rec.id)/WING.chunkSize);
  var chunk=WING.chunkDir+"/"+WING.chunkPrefix+String(n).padStart(5,"0")+".json.gz";
  var deep=location.href.split("#")[0]+WING.pageFile+"?"+WING.deepParam+"="+rec.id;
  panel.querySelectorAll("button").forEach(function(b){
    var a=b.getAttribute("data-rp");
    b.onclick=function(){
      if(a==="open"){location.hash="#"+WING.deepParam+"="+rec.id;}
      else if(a==="src"){if(!panel.querySelector(".srcnote")){var sn=document.createElement("span");sn.className="srcnote";sn.style.color="var(--mut)";sn.textContent="Source: "+WING.pageTitle+" catalog · "+chunk;panel.appendChild(sn);}}
      else if(a==="share"){copyText(deep,"sharebtn");}
      else if(a==="copy"){$("copybtn").click();}
      else if(a==="dl"){$("dljson").click();}
      else if(a==="read"){$("rdbtn").click();}
    };
  });
}
function wingAIProfile(){
  return {name:WING.unitSing.charAt(0).toUpperCase()+WING.unitSing.slice(1)+" Assistant",
    description:"A helper AI that answers questions from this "+WING.unitSing+"’s own text. It quotes the record, explains it in plain words, and says plainly when something is not covered.",
    abilities:["quote and explain passages from this "+WING.unitSing,"summarize its contents","tell you its title, kind and length"],
    domain:"books",kind:"helper"};
}
function wingAICardHTML(){
  var p=wingAIProfile(),duties=p.abilities.map(function(x){return esc(x)}).join("; ");
  return '<div class="jaicard"><b>🤖 AI IDENTITY</b><br><b>Name:</b> '+esc(p.name)+' — '+esc(p.description)+
   '<br><b>Duties:</b> '+duties+
   '<br><b>Engine:</b> Signature Llama (live where available) with the built-in JAHtalk on-device fallback — it always answers.</div>';
}
function renderRecord(rec){
  var secs=WING.sections(rec);
  var secHTML=secs.map(function(s){
    var items=s.items.map(function(it){
      return '<div class="ch"><h3>'+esc(it.t)+'</h3><p>'+esc(it.b).replace(/\n\n/g,"</p><p>").replace(/\n/g,"<br>")+"</p></div>"}).join("");
    return '<div class="chapters"><h2>'+esc(s.t)+"</h2>"+items+"</div>"}).join("");
  $("recview").innerHTML=
   '<div class="bookview"><p><a href="#">← Back to the shelves</a></p>'+
   '<div class="bv-top"><div class="bv-cover">'+coverSVG(WING.coverKind(rec),rec.id,WING.recTitle(rec),WING.byline(rec),rec.id)+"</div>"+
   '<div class="bv-info"><h1>'+esc(WING.recTitle(rec))+"</h1>"+
   '<div class="byline">'+esc(WING.byline(rec))+" · "+esc(rec.id)+"</div>"+
   '<div style="margin:6px 0"><span class="stbadge">SIGNATURE ORIGINAL</span></div>'+
   wingPanelHTML(rec)+wingProvHTML(rec)+
   '<div class="chips">'+WING.chips(rec).map(function(c){return '<span class="chip">'+esc(c)+"</span>"}).join("")+"</div>"+
   '<div class="actions"><button class="btn" id="rdbtn">🔊 Read aloud</button>'+
   '<button class="btn ghost" id="copybtn">⧉ Copy text</button>'+
   '<button class="btn ghost" id="dlbtn">⬇ Download .txt</button>'+
   '<button class="btn ghost" id="dljson">⬇ .json</button>'+
   '<button class="btn ghost" id="aibtn">💬 Ask about this '+WING.unitSing+"</button></div>"+
   '<div class="desc">'+esc(WING.desc(rec))+"</div>"+
   '<div class="honest">✦ '+esc(rec.note||"An original generated work created by the Signature system.")+"</div>"+
   '<div class="aipanel" id="aipanel" style="display:none"><h3>💬 Ask about this '+esc(WING.unitSing)+'</h3>'+
   wingAICardHTML()+
   '<p class="aimeta">Grounded in this '+esc(WING.unitSing)+'’s own text — it quotes and explains, and says plainly when something isn’t covered.</p>'+
   '<div class="airow"><input type="text" id="aiq" placeholder="Ask a question…" aria-label="Ask about this '+esc(WING.unitSing)+'"><button class="btn" id="aiask">Ask</button></div>'+
   '<div class="aians" id="aians"></div></div>'+
   "</div></div>"+secHTML+'<p><a href="#">← Back to the shelves</a></p></div>';
  $("rdbtn").onclick=function(){rdSpeak(CURTEXT)};
  $("copybtn").onclick=function(){copyText(CURTEXT,"copybtn")};
  $("dlbtn").onclick=function(){download(rec.id+".txt",CURTEXT,"text/plain")};
  $("dljson").onclick=function(){download(rec.id+".json",JSON.stringify(rec,null,1),"application/json")};
  $("aibtn").onclick=function(){var p=$("aipanel");p.style.display=p.style.display==="none"?"block":"none";if(p.style.display==="block")$("aiq").focus()};
  $("aiask").onclick=function(){askAI(rec)};
  $("aiq").addEventListener("keydown",function(e){if(e.key==="Enter")askAI(rec)});
  wingWirePanel(rec);
}
var AI_STOP={a:1,an:1,the:1,and:1,or:1,but:1,if:1,then:1,of:1,to:1,in:1,on:1,for:1,with:1,by:1,from:1,at:1,as:1,is:1,are:1,was:1,were:1,be:1,been:1,it:1,its:1,this:1,that:1,these:1,those:1,what:1,when:1,where:1,which:1,who:1,whom:1,how:1,why:1,does:1,do:1,did:1,can:1,could:1,would:1,should:1,will:1,about:1,into:1,over:1,under:1,again:1,there:1,their:1,them:1,they:1,you:1,your:1,tell:1,me:1,please:1,does:1};
function aiKeywords(q){
  return q.toLowerCase().split(/[^a-z0-9]+/).filter(function(w){return w.length>=3&&!AI_STOP[w]});
}
function askAI(rec){
  var q=$("aiq").value.trim(), box=$("aians");
  if(!q){box.innerHTML='<p class="ainone">Type a question first.</p>';return}
  box.innerHTML="<p class='ainone'>Thinking…</p>";
  setTimeout(function(){box.innerHTML=aiAnswer(rec,q)},60);
}
function aiAnswer(rec,q){
  var ql=q.toLowerCase(), secs=WING.sections(rec);
  var flat=[]; secs.forEach(function(s){s.items.forEach(function(it){flat.push({sec:s.t,t:it.t,b:it.b})})});
  // meta intents — answered from the record's own fields
  if(/who (wrote|made|created|author)/.test(ql)&&WING.authorOf)
    return "<p>"+esc(WING.authorOf(rec))+"</p>";
  if(/how (many|long)|word count|words\b/.test(ql))
    return "<p>This "+esc(WING.unitSing)+" runs <b>"+Number(rec.words).toLocaleString()+" words</b> across "+flat.length+" "+esc(WING.itemWord)+".</p>";
  if(/what (is|are) (this|it)|summar|about|describe/.test(ql))
    return "<p>"+esc(WING.desc(rec))+"</p>";
  if(/(when|date|published|issued)/.test(ql)&&rec.date)
    return "<p>Dated <b>"+esc(rec.date)+"</b>.</p>";
  if(/(list|all|every).*(article|chapter|entr|frame|item|section)/.test(ql)||/table of contents|contents/.test(ql)){
    var lis=flat.map(function(f){return "<li><b>"+esc(f.t)+"</b> <span class='aimeta'>("+esc(f.sec)+")</span></li>"}).join("");
    return "<p>It contains:</p><ul class='ailist'>"+lis+"</ul>";
  }
  // keyword match over the record's own text
  var kws=aiKeywords(q);
  if(!kws.length)
    return "<p class='ainone'>I couldn't pick out searchable words from that. Try asking about a topic, e.g. “what does it say about "+esc(flat[0]?flat[0].t.toLowerCase():"its contents")+"?”</p>";
  var scored=flat.map(function(f){
    var hay=(f.t+" "+f.b).toLowerCase(), sc=0;
    kws.forEach(function(k){var i=hay.indexOf(k);while(i>=0){sc+= (f.t.toLowerCase().indexOf(k)>=0?3:1);i=hay.indexOf(k,i+1)}});
    return {f:f,sc:sc}});
  scored.sort(function(a,b){return b.sc-a.sc});
  var best=scored[0];
  if(!best||best.sc===0){
    var tops=flat.slice(0,6).map(function(f){return esc(f.t)}).join("; ");
    return "<p class='ainone'>This "+esc(WING.unitSing)+" doesn't seem to cover “"+esc(q)+"”. Its "+esc(WING.itemWordPlural||"sections")+" include: "+tops+"… Try one of those topics.</p>";
  }
  // excerpt around first keyword hit
  var b=best.f.b, low=b.toLowerCase(), hit=-1;
  kws.forEach(function(k){var i=low.indexOf(k);if(i>=0&&(hit<0||i<hit))hit=i});
  var start=Math.max(0,hit-160), ex=b.slice(start,start+420);
  if(start>0)ex="…"+ex; if(start+420<b.length)ex=ex+"…";
  return "<p>From <b>“"+esc(best.f.t)+"”</b> <span class='aimeta'>("+esc(best.f.sec)+")</span>:</p>"+
    "<blockquote class='aiquote'>"+esc(ex)+"</blockquote>"+
    "<p class='aimeta'>Answered from this "+esc(WING.unitSing)+"’s own text.</p>";
}
function copyText(t,btnId){
  function done(ok){var b=$(btnId);if(b)b.textContent=ok?"✓ Copied":"Copy failed";setTimeout(function(){if(b)b.textContent="⧉ Copy text"},1800)}
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(function(){done(true)},function(){done(false)});
  else{var ta=document.createElement("textarea");ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand("copy");done(true)}catch(e){done(false)}ta.remove()}
}
function download(name,text,mime){
  var b=new Blob([text],{type:mime}),u=URL.createObjectURL(b),a=document.createElement("a");
  a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(u)},4000);
}

/* ---------------- tiered TTS (same chain as the book site) ---------------- */
var RD={audio:null,queue:[],playing:false,stopped:true,timer:null,speed:1,total:0};
var RD_TIERS=[
 function(t){return "https://code.responsivevoice.org/getvoice.php?t="+encodeURIComponent(t)+"&tl=en-US&sv=g2&vn=&pitch=0.5&rate=0.95"},
 function(t){return "https://translate.google.com/translate_tts?ie=UTF-8&q="+encodeURIComponent(t)+"&tl=en&client=tw-ob"},
 function(t){return "https://translate.googleapis.com/translate_tts?ie=UTF-8&q="+encodeURIComponent(t)+"&tl=en&client=tw-ob"}];
function rdChunks(t,maxChunks){t=String(t).replace(/\s+/g," ").trim();var out=[],cur="";
  t.split(/(?<=[.!?])\s+/).forEach(function(s){if((cur+" "+s).length>170){if(cur)out.push(cur);cur=s}else cur=(cur?cur+" ":"")+s});
  if(cur)out.push(cur);return out.slice(0,maxChunks||400)}
function rdStop(){RD.stopped=true;RD.playing=false;RD.queue=[];if(RD.timer){clearTimeout(RD.timer);RD.timer=null}
  if(RD.audio){try{RD.audio.pause()}catch(e){}RD.audio=null}
  var b=$("rdbtn");if(b)b.textContent="🔊 Read aloud";var rb=$("rdbar");if(rb)rb.classList.remove("show")}
function rdPlayTier(chunk,tier,done){
  if(tier>=RD_TIERS.length){done(false);return}
  var url=RD_TIERS[tier](chunk),a=new Audio();RD.audio=a;a.playbackRate=RD.speed;
  var finished=false;
  function next(ok){if(finished)return;finished=true;try{a.pause()}catch(e){}done(ok)}
  a.onended=function(){next(true)};a.onerror=function(){next(false)};
  RD.timer=setTimeout(function(){rdPlayTier(chunk,tier+1,done)},12000);
  a.src=url;var p=a.play();if(p&&p.catch)p.catch(function(){next(false)});
  var iv=setInterval(function(){if(finished){clearInterval(iv);return}if(!RD.timer){clearInterval(iv);return}},500);
  var oldNext=next;next=function(ok){if(RD.timer){clearTimeout(RD.timer);RD.timer=null}clearInterval(iv);oldNext(ok)};
}
function rdNext(){
  if(RD.stopped||!RD.queue.length){rdStop();return}
  RD.playing=true;var chunk=RD.queue.shift(),tier=0;
  $("rdprog").textContent="Reading chunk "+(RD.total-RD.queue.length)+" of "+RD.total+"…";
  (function attempt(){
    if(RD.stopped)return;
    rdPlayTier(chunk,tier,function(ok){
      if(RD.stopped)return;
      if(ok){setTimeout(rdNext,250)}else{tier++;if(tier<RD_TIERS.length)attempt();else setTimeout(rdNext,250)}
    });
  })();
}
function rdSpeak(text){
  if(RD.playing&&!RD.stopped){rdStop();return}
  rdStop();RD.queue=rdChunks(text,400);RD.total=RD.queue.length;
  if(!RD.queue.length)return;RD.stopped=false;
  var b=$("rdbtn");if(b)b.textContent="⏹ Stop";
  $("rdbar").classList.add("show");rdNext();
}

/* ---------------- FINDER (additive): deterministic keyword finder over the wing's own index ---------------- */
var Finder={};
Finder.STOP={a:1,an:1,the:1,and:1,or:1,but:1,if:1,then:1,of:1,to:1,in:1,on:1,for:1,with:1,by:1,from:1,at:1,as:1,is:1,are:1,was:1,were:1,be:1,been:1,it:1,its:1,this:1,that:1,these:1,those:1,what:1,when:1,where:1,which:1,who:1,whom:1,how:1,why:1,does:1,do:1,did:1,can:1,could:1,would:1,should:1,will:1,about:1,into:1,over:1,under:1,again:1,there:1,their:1,them:1,they:1,you:1,your:1,tell:1,me:1,please:1,find:1,looking:1,look:1,show:1,want:1,need:1,get:1,some:1,any:1,all:1,both:1,more:1,most:1,very:1,just:1,like:1,such:1,than:1,one:1,thing:1,kind:1,type:1};
Finder.keywords=function(q){return String(q||"").toLowerCase().replace(/[^a-z0-9]+/g," ").split(" ").filter(function(w){return w.length>=3&&!Finder.STOP[w]})};
Finder.setup=function(){
  var az=$("az");if(!az||$("finder"))return;
  var st=document.createElement("style");
  st.textContent=".finder{margin:10px 0;border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:#0e0a05}"+
    ".finder .fhead{display:flex;gap:10px;align-items:center;margin-bottom:8px}"+
    ".finder .fhead b{color:var(--gold2);letter-spacing:.06em}"+
    ".finder .fhead span{display:block;font-size:.82em;color:var(--mut)}"+
    ".finder .frow{display:flex;gap:8px;flex-wrap:wrap}"+
    ".finder .frow input{flex:1;min-width:200px}"+
    ".finder .fcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:10px}"+
    ".finder .fcard{border:1px solid var(--line);border-radius:10px;padding:12px;background:#171107;cursor:pointer}"+
    ".finder .fcard h4{margin:2px 0 4px}"+
    ".finder .fcard .go{color:var(--gold2);font-weight:700;text-decoration:none}";
  document.head.appendChild(st);
  var d=document.createElement("div");d.className="finder";d.id="finder";
  d.innerHTML='<div class="fhead"><span aria-hidden="true">\uD83D\uDD0E</span><div><b>FINDER</b><span>describe the '+esc(WING.unitSing)+' you want in plain words — it searches this wing\u2019s own index</span></div></div>'+
    '<div class="frow"><input id="fq" maxlength="160" placeholder="Describe what you\u2019re looking for\u2026" aria-label="Describe the '+esc(WING.unitSing)+' you want"><button class="btn" id="fGo">Find</button></div>'+
    '<div id="fresults"></div>';
  az.parentNode.insertBefore(d,az);
  $("fGo").onclick=Finder.ask;
  $("fq").addEventListener("keydown",function(e){if(e.key==="Enter")Finder.ask()});
};
/* same hay rule as applyFilters — reuses the wing's own search, no second index */
Finder.ask=function(){
  var box=$("fresults"),kws=Finder.keywords($("fq").value);
  if(!kws.length){box.innerHTML='<p class="dim" style="margin-top:8px">Describe what you want — a topic, a subject, a mood — and I will match this wing\u2019s own records.</p>';return}
  if(!IDX.length){box.innerHTML='<p class="dim" style="margin-top:8px">The index is still loading — one moment.</p>';return}
  var scored=IDX.map(function(e){var hay=WING.hay(e).toLowerCase(),sc=0;kws.forEach(function(k){if(hay.indexOf(k)>=0)sc++});return{e:e,sc:sc}}).filter(function(x){return x.sc>0});
  scored.sort(function(a,b){return b.sc-a.sc});
  var top=scored.slice(0,5);
  if(!top.length){box.innerHTML='<p class="dim" style="margin-top:8px"><b>Nothing matched.</b> Try fewer, simpler words.</p>';return}
  box.innerHTML='<p class="dim" style="margin-top:8px">'+top.length+' of '+scored.length.toLocaleString()+' matches for \u201C'+esc(kws.join(" "))+'\u201D:</p>'+
    '<div class="fcards">'+top.map(function(x){var e=x.e;
      return '<div class="fcard" data-id="'+e.id+'" role="button" tabindex="0"><div class="g">'+esc(e.id)+'</div><h4>'+esc(WING.cardTitle(e))+'</h4><div class="a">'+esc(WING.cardSub(e))+'</div><p class="n"><a class="go" href="'+WING.pageFile+'#'+WING.deepParam+'='+e.id+'" data-dl="1">Take me there &rarr;</a></p></div>';
    }).join("")+'</div>';
  box.querySelectorAll(".fcard").forEach(function(el){
    el.addEventListener("click",function(e){if(e.target.getAttribute("data-dl"))return;location.hash="#"+WING.deepParam+"="+el.getAttribute("data-id")});
    el.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" ")location.hash="#"+WING.deepParam+"="+el.getAttribute("data-id")});
  });
};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
