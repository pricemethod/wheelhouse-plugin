#!/usr/bin/env python3
"""Render the 12-month market event timeline from report.json.

Usage: python3 build_timeline.py report.json out.html

report.json = the timeline block's result, plus these keys Claude adds by hand:
  market_name     e.g. "Denver, CO"
  sources_events  one line on where event dates came from
  caveats         list of short strings for "Read with care"
"""
import json, sys, html, datetime

SYM = {"USD": "$", "CAD": "CA$", "AUD": "A$", "NZD": "NZ$", "EUR": "\u20ac",
       "GBP": "\u00a3", "MXN": "MX$", "JPY": "\u00a5"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MINUS = "\u2212"

def esc(s): return html.escape(str(s or ""), quote=True)
def money(v, cur):
    if v is None: return "\u2013"
    return SYM.get(cur, (cur or "") + " ") + "{:,.0f}".format(v)
def pct(v):
    return "\u2013" if v is None else "{:.0f}%".format(v * 100)
def signed(v, unit=""):
    if v is None: return "\u2013"
    r = round(v)
    if r == 0: return "\u00b10" + unit
    return ("+" if r > 0 else MINUS) + str(abs(r)) + unit
def cls(v, cut):
    if v is None or abs(v) < cut: return "flat"
    return "pos" if v > 0 else "neg"
def mlabel(ym):
    y, m = ym.split("-"); return MON[int(m) - 1] + " " + y
def short_k(n):
    if n is None: return "\u2013"
    return "{:.1f}k".format(n / 1000) if n >= 1000 else str(int(n))

TIERS = [("high", "High demand", "Market fills well above the weeks around it, and rates rise."),
         ("mid", "Mid demand", "A clear but moderate bump, often on top of an already busy season."),
         ("low", "Low demand", "Little or no change in market occupancy or rate.")]

CSS = r"""
:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);
  --page:#f5f5f4;--card:#ffffff;--ink:#1a1a1a;--body:#2b2b2b;--muted:#666666;--line:#e5e4e4;--line2:#dcdbdb;
  --brand:#bd08b6;--brand-deep:#82087d;--brand-wash:#fce0fa;--brand-mid:#fa8ff6;
  --pos:#0f7a52;--neg:#c23a3f;--flat:#666666;--track:#eeeeee;--low-wash:#eeeeee;
  --display:"Hanken Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;
  --ui:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"Space Mono",ui-monospace,"SF Mono",Menlo,monospace;color-scheme:light}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --page:#1a1a1a;--card:#222222;--ink:#ffffff;--body:rgba(255,255,255,.9);--muted:#a6a6a6;--line:rgba(255,255,255,.08);--line2:rgba(255,255,255,.14);
  --brand:#fd25f5;--brand-deep:#fa8ff6;--brand-wash:#3a0a37;--brand-mid:#bd08b6;
  --pos:#2bc78f;--neg:#f07479;--flat:#a6a6a6;--track:#2e2e2e;--low-wash:#2e2e2e;color-scheme:dark}}
:root[data-theme="dark"]{
  --page:#1a1a1a;--card:#222222;--ink:#ffffff;--body:rgba(255,255,255,.9);--muted:#a6a6a6;--line:rgba(255,255,255,.08);--line2:rgba(255,255,255,.14);
  --brand:#fd25f5;--brand-deep:#fa8ff6;--brand-wash:#3a0a37;--brand-mid:#bd08b6;
  --pos:#2bc78f;--neg:#f07479;--flat:#a6a6a6;--track:#2e2e2e;--low-wash:#2e2e2e;color-scheme:dark}
body{margin:0;background:var(--page);color:var(--body);font-family:var(--ui);font-size:12.5px;line-height:1.4}
.wrap{max-width:1180px;margin:0 auto;padding-block:28px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:20px}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:12px 24px}
.eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);font-weight:700}
h1{font-family:var(--display);font-weight:800;font-size:34px;line-height:1.05;color:var(--ink);margin:4px 0 0;letter-spacing:-.01em;text-wrap:balance}
h2{font-family:var(--display);font-weight:800;font-size:20px;color:var(--ink);margin:0}
.lede{max-width:62ch;color:var(--muted);margin:6px 0 0}
.legend{display:grid;gap:4px;font-size:11px;color:var(--muted);min-width:0}
.legend .lg{display:flex;align-items:center;gap:8px}
.legend .sw{display:inline-block;width:28px;height:8px;border-radius:999px;background:var(--track);position:relative;flex:none}
.legend .sw::before{content:"";position:absolute;inset:0 40% 0 0;border-radius:999px;background:var(--brand)}
.legend .sw::after{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;width:2px;background:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.ovh{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px 16px;padding:14px 16px;border-bottom:1px solid var(--line)}
.ovh .ref{font-size:11.5px;color:var(--muted);margin-top:3px}
.ovh .ref b{color:var(--ink);font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chips button{font:inherit;font-size:11px;padding:4px 10px;border-radius:999px;border:1px solid var(--line2);background:transparent;color:var(--body);cursor:pointer}
.chips button[aria-pressed="true"]{background:var(--brand);border-color:var(--brand);color:#fff}
.chips button:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
.summary{padding:12px 16px 0;max-width:90ch;color:var(--body);font-size:13px}
.months{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;padding:14px 16px 16px}
.mt{border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:grid;gap:6px}
.mt .mn{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}
.mt .big{font-family:var(--display);font-weight:800;font-size:24px;color:var(--ink);line-height:1}
.mt .big span{font-family:var(--ui);font-size:11px;font-weight:500;color:var(--muted)}
.kv{display:flex;justify-content:space-between;gap:6px;font-size:11.5px;border-top:1px solid var(--line);padding-top:5px}
.kv span{color:var(--muted)} .kv b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums;text-align:right}
.kv small{display:block;font-weight:600;font-size:10.5px}
.ovnote{padding:0 16px 14px;font-size:11px;color:var(--muted)}
.slabel{display:inline-block;font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;color:var(--muted);margin-right:8px}
.thin{margin:10px 16px 0;padding:6px 10px;border-radius:8px;background:var(--brand-wash);color:var(--brand-deep);font-size:11.5px;font-weight:500}
.th{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:12px 16px;border-bottom:1px solid var(--line)}
.pill{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;padding:4px 10px;border-radius:999px}
.t-high .pill{background:var(--brand);color:#fff}
.t-mid .pill{background:var(--brand-wash);color:var(--brand-deep)}
.t-low .pill,.t-none .pill{background:var(--low-wash);color:var(--muted)}
.count{font-weight:600;color:var(--ink)} .tdesc{color:var(--muted)}
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:820px}
th{font-size:10.5px;font-weight:600;color:var(--muted);text-align:left;padding:8px 10px;border-bottom:1px solid var(--line2);vertical-align:bottom;white-space:nowrap}
th .sub,td .sub{display:block;font-weight:400;font-size:10px;color:var(--muted)}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.num{font-weight:600;color:var(--ink)}
.dt{white-space:nowrap;font-variant-numeric:tabular-nums;width:138px}
.ev strong{color:var(--ink);font-weight:600}
.note{font-size:10.5px;color:var(--muted);margin-top:2px}
.occ{width:200px}
.occrow{display:flex;align-items:center;gap:8px}
.occrow b{color:var(--ink);font-variant-numeric:tabular-nums;min-width:30px;text-align:right}
.bar{position:relative;flex:1;height:8px;border-radius:999px;background:var(--track);display:block}
.bar .fill{position:absolute;inset:0 auto 0 0;border-radius:999px;background:var(--brand)}
.t-mid .bar .fill{background:var(--brand-mid)}
.t-low .bar .fill{background:var(--muted)}
.bar .base{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink);border-radius:1px}
.yrs{display:flex;gap:10px;margin-top:3px;font-size:10.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.yrs i{font-style:normal;margin-right:3px}
.pos{color:var(--pos)!important} .neg{color:var(--neg)!important} .flat{color:var(--flat)!important}
.prem{font-size:13px}
.unr{padding:10px 16px;display:grid;gap:4px;font-size:12px}
.unr span{color:var(--muted)}
.foot{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;font-size:11px;color:var(--muted);border-top:1px solid var(--line2);padding-top:12px}
.foot b{color:var(--body);font-weight:600}
@media (max-width:960px){.months{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:860px){.foot{grid-template-columns:1fr}}
@media (max-width:520px){.months{grid-template-columns:repeat(2,minmax(0,1fr))} h1{font-size:28px}}
@media print{@page{size:landscape;margin:10mm}body{font-size:10.5px;background:#fff}.wrap{padding:0;gap:10px}.card{break-inside:avoid}table{min-width:0}td,th{padding:4px 6px}.chips{display:none}}
"""

TL_CSS = r"""
:root{--ly:#57534e;--ly-soft:#a8a29e}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ly:#d6d3d1;--ly-soft:#78716c}}
:root[data-theme="dark"]{--ly:#d6d3d1;--ly-soft:#78716c}
.chartcard{padding:14px 0 10px}
.chartcard .ovh{border-bottom:0;padding-top:0}
.cscroll{overflow-x:auto;padding:0 16px}
#chart{min-width:980px;position:relative}
#chart svg{display:block;overflow:visible}
#chart:focus-visible{outline:2px solid var(--brand);outline-offset:4px;border-radius:6px}
.grid{stroke:var(--line);stroke-width:1}
.axis{stroke:var(--line2);stroke-width:1}
.ytick,.mlab{fill:var(--muted);font-size:11px;font-family:var(--ui)}
.mlab.yr{fill:var(--ink);font-weight:600}
.mstat{font-size:10.5px;font-family:var(--ui);font-variant-numeric:tabular-nums}
.mstat .l{fill:var(--muted)} .mstat .c{fill:var(--brand);font-weight:700}
.ly-area{fill:var(--ly-soft);opacity:.16}
.ly-line{fill:none;stroke:var(--ly);stroke-width:2;stroke-linejoin:round}
.cur-line{fill:none;stroke:var(--brand);stroke-width:2.5;stroke-linejoin:round}
.band{stroke:none}
.band.high{fill:var(--brand);opacity:.16}
.band.mid{fill:var(--brand-mid);opacity:.18}
.band.low{fill:var(--muted);opacity:.12}
.band.none{fill:none;stroke:var(--muted);stroke-dasharray:3 3;opacity:.7}
.band.tba{stroke:var(--muted);stroke-dasharray:2 3;stroke-width:1}
.lead{stroke:var(--line2);stroke-width:1}
.lab rect{rx:7;ry:7}
.lab.high rect{fill:var(--brand)} .lab.high text{fill:#fff}
.lab.mid rect{fill:var(--brand-wash)} .lab.mid text{fill:var(--brand-deep)}
.lab.low rect{fill:var(--low-wash)} .lab.low text{fill:var(--body)}
.lab.none rect{fill:var(--card);stroke:var(--muted);stroke-dasharray:3 2} .lab.none text{fill:var(--body)}
.lab .n{font-size:11px;font-weight:600;font-family:var(--ui)}
.lab .s{font-size:10px;font-family:var(--ui);opacity:.85}
.ctx rect{fill:var(--ink);opacity:.55}
.ctx text{fill:var(--muted);font-size:10px;font-family:var(--ui)}
.hol line{stroke:var(--muted);stroke-width:1;stroke-dasharray:1 2}
.hol text{fill:var(--muted);font-size:9.5px;font-family:var(--ui)}
.xhair{stroke:var(--ink);stroke-width:1;opacity:.5}
.tip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--line2);border-radius:8px;padding:8px 10px;font-size:11.5px;box-shadow:0 4px 14px rgba(0,0,0,.12);min-width:200px;display:none;z-index:2}
.tip b{color:var(--ink)} .tip .r{display:flex;justify-content:space-between;gap:12px} .tip .r span{color:var(--muted)}
.tip .ev{margin-top:4px;padding-top:4px;border-top:1px solid var(--line);color:var(--brand-deep);font-weight:600}
.legend .ln{display:inline-block;width:24px;height:0;border-top:2.5px solid var(--brand);flex:none}
.legend .ln.ly{border-top:2px solid var(--ly)}
.legend .bd{display:inline-block;width:14px;height:12px;border-radius:3px;background:var(--brand);opacity:.35;flex:none}
.summary{padding:0 16px 10px}

.band.ly{fill:url(#lyhatch);opacity:.9}
.hatch-bg{fill:var(--card);opacity:0}
.hatch-ln{stroke:var(--ly);stroke-width:2;opacity:.55}
.band.on{opacity:.3}
.band.ly.on{opacity:1}
.hit{fill:transparent;cursor:pointer}
.hit:hover{fill:var(--ink);opacity:.06}
.lab{cursor:pointer}
.lab.ly rect{fill:var(--card);stroke:var(--ly);stroke-dasharray:4 2;stroke-width:1.2} .lab.ly text{fill:var(--ly)}
.lab.ly .n{font-style:italic}
.lead.lylead{stroke:var(--ly);stroke-dasharray:2 2}
.tip .ev.lyev{color:var(--ly);font-style:italic}
.tip .hint{margin-top:4px;font-size:10.5px;color:var(--muted)}
.ctrls{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.ctrls .hintline{font-size:11px;color:var(--muted)}
.tbtn{font:inherit;font-size:11.5px;padding:5px 11px;border-radius:999px;border:1px solid var(--line2);background:transparent;color:var(--body);cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.tbtn:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
.tbtn[aria-pressed="true"]{border-color:var(--ly);background:var(--low-wash);color:var(--ink)}
.tbtn .sw2{display:inline-block;width:12px;height:12px;border-radius:2px;border:1px solid var(--ly);background:repeating-linear-gradient(45deg,var(--ly) 0 1.5px,transparent 1.5px 4px);opacity:.8}
.legend .hb{display:inline-block;width:14px;height:12px;border-radius:3px;border:1px dashed var(--ly);background:repeating-linear-gradient(45deg,var(--ly) 0 1.5px,transparent 1.5px 4px);opacity:.7;flex:none}
"""

TL_JS = r"""
(function(){
  var D = JSON.parse(document.getElementById('tldata').textContent);
  var host = document.getElementById('chart'), tip = document.getElementById('tip');
  var btnLY = document.getElementById('btn-ly'), btnReset = document.getElementById('btn-reset');
  var MS = 864e5, MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var WD = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'], MINUS = '\u2212';
  function P(s){var a=s.split('-');return Date.UTC(+a[0],+a[1]-1,+a[2]);}
  var t0 = P(D.series.start), N = D.series.occ.length;
  function idx(s){return Math.round((P(s)-t0)/MS);}
  function dstr(i,shift){var d=new Date(t0+(i-(shift||0))*MS);return WD[d.getUTCDay()]+', '+MON[d.getUTCMonth()]+' '+d.getUTCDate()+', '+d.getUTCFullYear();}
  function rng(s,e){var a=new Date(P(s)),b=new Date(P(e)),y=a.getUTCFullYear();
    if(s===e) return MON[a.getUTCMonth()]+' '+a.getUTCDate()+', '+y;
    return MON[a.getUTCMonth()]+' '+a.getUTCDate()+'\u2013'+(a.getUTCMonth()===b.getUTCMonth()?'':MON[b.getUTCMonth()]+' ')+b.getUTCDate()+', '+y;}
  function pct(v){return v==null?'\u2013':Math.round(v*100)+'%';}
  function sgn(v,u){if(v==null)return '\u2013';var r=Math.round(v);return (r>0?'+':r<0?MINUS:'\u00b1')+Math.abs(r)+u;}
  function avg7(a){var o=[];for(var i=0;i<a.length;i++){var s=0,n=0;for(var k=i-3;k<=i+3;k++){if(k>=0&&k<a.length&&a[k]!=null){s+=a[k];n++;}}o.push(n?s/n:null);}return o;}

  // stop the on-the-books line where bookable inventory falls below 30% of normal (calendars not open yet)
  var bks = D.series.bookable.filter(function(v){return v!=null;}).slice().sort(function(a,b){return a-b;});
  var med = bks.length ? bks[Math.floor(bks.length/2)] : 0;
  var curM = D.series.occ.map(function(v,i){var b=D.series.bookable[i];return (b==null||b<0.3*med)?null:v;});
  var cutoff = null; for(var ci=0; ci<curM.length; ci++){ if(curM[ci]==null && D.series.occ[ci]!=null){cutoff=ci;break;} }
  var ly7 = avg7(D.series.occ_ly), cur7 = avg7(curM); if(cutoff!=null) for(var cj=cutoff; cj<cur7.length; cj++) cur7[cj]=null;
  var ymax = 0; D.series.occ_ly.concat(D.series.occ).forEach(function(v){if(v!=null&&v>ymax)ymax=v;});
  ymax = Math.min(1, Math.ceil((ymax+0.04)*10)/10);

  // items: this year's events on their next dates, and last year's editions placed 364 days forward
  // so they sit on the last-year line. Event nights: night before day one to the night before the last day.
  var items = [];
  D.events.concat(D.unrated).forEach(function(e,k){
    var rated = e.tier != null, a = idx(e.next_start)-1, b = idx(e.next_end||e.next_start)-1; if(b<a) b=a;
    if(b>=0 && a<N) items.push({key:'t'+k, ly:false, e:e, tier: rated?e.tier:'none', a:a, b:b, score: rated?e.score:-999,
      l1: e.name+(e.tba?' (TBA)':''), l2: rated ? sgn(e.lift_pts,' pts')+' \u00b7 '+sgn(e.adr_prem,'% ADR') : 'New \u00b7 no past edition'});
    (e.editions||[]).forEach(function(ed){ if(!ed.start) return;
      var la = idx(ed.start)-1+364, lb = idx(ed.end)-1+364; if(lb<la) lb=la;
      if(lb<0 || la>=N) return;
      items.push({key:'l'+k+ed.label, ly:true, e:e, ed:ed, tier:'ly', a:la, b:lb, score:-1,
        l1: 'Last year ' + ed.label + ' \u00b7 ' + e.name,
        l2: rng(ed.start, ed.end) + ' \u00b7 ' + pct(ed.occ) + ' occ \u00b7 ' + sgn(ed.lift_pts,' pts') + ' \u00b7 ' + sgn(ed.adr_prem,'% ADR')});
    });
  });
  items.sort(function(x,y){return x.a-y.a;});
  var byKey = {}; items.forEach(function(o){byKey[o.key]=o;});
  var state = {shown:null, order:[], defaults:[], showLY:false, i:null};

  function nthWd(y,m,wd,n){var d=new Date(Date.UTC(y,m,1));while(d.getUTCDay()!==wd)d=new Date(+d+MS);return +d+7*(n-1)*MS;}
  function lastWd(y,m,wd){var d=new Date(Date.UTC(y,m+1,0));while(d.getUTCDay()!==wd)d=new Date(+d-MS);return +d;}
  var hols=[]; [new Date(t0).getUTCFullYear(), new Date(t0).getUTCFullYear()+1].forEach(function(y){
    hols.push(['Thanksgiving', nthWd(y,10,4,4)]); hols.push(['Christmas', Date.UTC(y,11,25)]);
    hols.push(['New Year', Date.UTC(y,0,1)]); hols.push(['July 4', Date.UTC(y,6,4)]);
    hols.push(['Memorial Day', lastWd(y,4,1)]); hols.push(['Labor Day', nthWd(y,8,1,1)]); });
  function el(n,a,txt){var e=document.createElementNS('http://www.w3.org/2000/svg',n);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;}
  function lw(o){return Math.max(o.l1.length*6.3, o.l2.length*5.6)+16;}

  // find a spot for a label in one lane: centered over its band, or slid sideways (at most MAXS px)
  // default row may slide further so events sharing dates (e.g. two on July 4th weekend) both fit
  var MAXS = 150, MAXS_DEFAULT = 230;
  function fit(lane, cx, w, L, Wr, maxs){ maxs = maxs || MAXS;
    var want = Math.min(Math.max(cx-w/2, L), Wr-w), cands=[want];
    lane.forEach(function(iv){cands.push(iv[1]+6); cands.push(iv[0]-6-w);});
    var best=null;
    cands.forEach(function(x){ if(x<L||x+w>Wr) return; if(Math.abs(x-want)>maxs) return;
      if(lane.some(function(iv){return x < iv[1]+6 && x+w > iv[0]-6;})) return;
      if(best==null || Math.abs(x-want)<Math.abs(best-want)) best=x; });
    return best;
  }

  // lay out one row: keep date order, push overlapping labels apart, pull back from the right edge.
  // Returns {key: x} or null if any label would sit more than maxs px from its band.
  function layoutRow(list, X, L, Wr, maxs){
    var g = list.map(function(o){var w=lw(o), cx=X((o.a+o.b+1)/2); return {k:o.key, w:w, want:Math.min(Math.max(cx-w/2,L),Wr-w)};})
      .sort(function(p,q){return p.want-q.want;});
    var i; for(i=0;i<g.length;i++){ g[i].x = i ? Math.max(g[i].want, g[i-1].x+g[i-1].w+6) : g[i].want; }
    for(i=g.length-1;i>=0;i--){ var lim = (i===g.length-1) ? Wr-g[i].w : g[i+1].x-6-g[i].w; if(g[i].x>lim) g[i].x=lim; }
    var out={};
    for(i=0;i<g.length;i++){ if(g[i].x<L || Math.abs(g[i].x-g[i].want)>maxs) return null; if(i && g[i].x < g[i-1].x+g[i-1].w+6-0.5) return null; out[g[i].k]=g[i].x; }
    return out;
  }
  function draw(){
    host.innerHTML='';
    var W = Math.max(980, host.clientWidth), L=44, R=12, Wr = W-R;
    var pw = W-L-R, xw = pw/N;
    function X(i){return L+i*xw;}
    // first draw: the default row is the highest-scoring High and Mid events that fit on one line
    if(state.shown==null){
      state.shown={}; var pick=[];
      items.filter(function(o){return !o.ly && (o.tier==='high'||o.tier==='mid');})
        .sort(function(x,y){return y.score-x.score;})
        .forEach(function(o){ if(layoutRow(pick.concat([o]), X, L, Wr, MAXS_DEFAULT)){ pick.push(o); state.shown[o.key]=true; state.defaults.push(o.key); } });
    }
    // place labels: the default row first, then everything clicked on, in click order, stacking upward
    var lanes=[[]], placed=[];
    var defs0 = state.defaults.filter(function(k){return state.shown[k];}).map(function(k){return byKey[k];});
    var pos0 = layoutRow(defs0, X, L, Wr, MAXS_DEFAULT) || {};
    defs0.forEach(function(o){ var x=pos0[o.key]; if(x==null) return; var w=lw(o);
      lanes[0].push([x,x+w]); placed.push({o:o,x:x,w:w,cx:X((o.a+o.b+1)/2),lane:0}); });
    var queue = state.order.filter(function(k){return state.shown[k] && state.defaults.indexOf(k)<0;})
      .filter(function(k){return state.showLY || !byKey[k].ly;});
    queue.forEach(function(k){
      var o=byKey[k], w=lw(o), cx=X((o.a+o.b+1)/2), x=null, li=0;
      for(li=0; li<12; li++){ lanes[li]=lanes[li]||[]; x=fit(lanes[li], cx, w, L, Wr, MAXS); if(x!=null) break; }
      if(x==null){ li=lanes.length; lanes[li]=[]; x=Math.min(Math.max(cx-w/2,L),Wr-w); }
      lanes[li].push([x,x+w]); placed.push({o:o,x:x,w:w,cx:cx,lane:li});
    });
    var LH=37, nl=Math.max(1,lanes.length), TOP = nl*LH+12, PH=300, ctxH = D.context.length?16:0;
    var PT = TOP+ctxH, PB = PT+PH, H = PB+74;
    function Y(v){return PB-(v/ymax)*PH;}
    var s = el('svg',{width:W,height:H,viewBox:'0 0 '+W+' '+H,role:'img','aria-label':'Market occupancy over the next 12 months with events'});
    var defs = el('defs',{}), pat = el('pattern',{id:'lyhatch',width:6,height:6,patternUnits:'userSpaceOnUse',patternTransform:'rotate(45)'});
    pat.appendChild(el('rect',{width:6,height:6,'class':'hatch-bg'})); pat.appendChild(el('line',{x1:0,y1:0,x2:0,y2:6,'class':'hatch-ln'}));
    defs.appendChild(pat); s.appendChild(defs);
    for(var g=0; g<=ymax+1e-9; g+=0.2){ s.appendChild(el('line',{x1:L,x2:Wr,y1:Y(g),y2:Y(g),'class':'grid'})); s.appendChild(el('text',{x:L-8,y:Y(g)+4,'text-anchor':'end','class':'ytick'},Math.round(g*100)+'%')); }
    // bands
    var vis = items.filter(function(o){return state.showLY || !o.ly;});
    vis.forEach(function(o){
      var cls='band '+o.tier+(o.e.tba&&!o.ly?' tba':'')+(state.shown[o.key]?' on':'');
      s.appendChild(el('rect',{x:X(o.a),y:PT,width:Math.max(3,(o.b-o.a+1)*xw),height:PH,'class':cls}));
    });
    // month grid + labels
    D.months.forEach(function(m,k){
      var a=m.month.split('-'), i=Math.max(0, Math.round((Date.UTC(+a[0],+a[1]-1,1)-t0)/MS));
      if(k>0) s.appendChild(el('line',{x1:X(i),x2:X(i),y1:PT,y2:PB+8,'class':'grid'}));
      if(m.days>=10){
        var mid = X(i + m.days/2), isY = (+a[1]===1)||k===0||(k===1&&D.months[0].days<10);
        s.appendChild(el('text',{x:mid,y:PB+20,'text-anchor':'middle','class':'mlab'+(isY?' yr':'')}, MON[+a[1]-1]+(isY?' '+a[0]:'')));
        var t=el('text',{x:mid,y:PB+35,'text-anchor':'middle','class':'mstat'});
        t.appendChild(el('tspan',{'class':'l'},'LY '+pct(m.occ_ly)+' \u00b7 ')); t.appendChild(el('tspan',{'class':'c'},pct(m.occ)));
        s.appendChild(t);
      }
    });
    s.appendChild(el('line',{x1:L,x2:Wr,y1:PB,y2:PB,'class':'axis'}));
    function path(arr){var d='',pen=false;for(var i=0;i<N;i++){var v=arr[i];if(v==null){pen=false;continue;}d+=(pen?'L':'M')+X(i+.5).toFixed(1)+' '+Y(v).toFixed(1);pen=true;}return d;}
    var ad='M'+X(.5)+' '+PB; for(var i=0;i<N;i++){var v=D.series.occ_ly[i]; ad+='L'+X(i+.5).toFixed(1)+' '+Y(v==null?0:v).toFixed(1);} ad+='L'+X(N-.5)+' '+PB+'Z';
    s.appendChild(el('path',{d:ad,'class':'ly-area'}));
    s.appendChild(el('path',{d:path(ly7),'class':'ly-line'}));
    s.appendChild(el('path',{d:path(cur7),'class':'cur-line'}));
    if(cutoff!=null) s.appendChild(el('text',{x:X(cutoff)-4,y:PB-8,'text-anchor':'end','class':'ytick'},'Too few listings open to read bookings \u2192'));
    D.context.forEach(function(c){var a=Math.max(0,idx(c.next_start)), b=Math.min(N-1,idx(c.next_end)); if(b<0||a>=N)return;
      var g=el('g',{'class':'ctx'}); g.appendChild(el('rect',{x:X(a),y:TOP+3,width:(b-a+1)*xw,height:4,rx:2}));
      g.appendChild(el('text',{x:X(b+1)+4,y:TOP+9},c.name+' \u00b7 season-long, not rated')); s.appendChild(g);});
    var lastHx=-1e9, hrow=0;
    hols.slice().sort(function(p,q){return p[1]-q[1];}).forEach(function(h){var i=Math.round((h[1]-t0)/MS); if(i<0||i>=N)return; var g=el('g',{'class':'hol'});
      var hx=X(i+.5); hrow = (hx-lastHx<80) ? 1-hrow : 0; lastHx=hx;
      g.appendChild(el('line',{x1:hx,x2:hx,y1:PB,y2:PB+46+hrow*11})); g.appendChild(el('text',{x:hx+3,y:PB+55+hrow*11},h[0])); s.appendChild(g);});
    var xh = el('line',{y1:PT,y2:PB,'class':'xhair',visibility:'hidden'}); s.appendChild(xh);
    // click targets over the bands (at least 14px wide so short events are easy to hit)
    vis.forEach(function(o){
      var bx=X(o.a), bw=Math.max(3,(o.b-o.a+1)*xw), hw=Math.max(14,bw);
      var hit=el('rect',{x:bx+bw/2-hw/2,y:PT,width:hw,height:PH,'class':'hit'});
      hit.appendChild(el('title',{},(state.shown[o.key]?'Hide':'Show')+' details: '+o.l1));
      hit.addEventListener('click',function(ev){ev.stopPropagation(); toggle(o.key);});
      s.appendChild(hit);
    });
    // labels + leaders (lane 0 sits right above the chart; clicked labels stack upward)
    placed.forEach(function(p){   // all leaders first, so no leader crosses a label
      var y = TOP - 8 - (p.lane+1)*LH + 6, tx = Math.min(Math.max(p.cx, p.x+8), p.x+p.w-8);
      s.appendChild(el('line',{x1:p.cx,x2:tx,y1:PT,y2:y+28,'class':'lead'+(p.o.ly?' lylead':'')}));
    });
    placed.forEach(function(p){
      var o=p.o, y = TOP - 8 - (p.lane+1)*LH + 6;
      var g=el('g',{'class':'lab '+o.tier}); g.appendChild(el('rect',{x:p.x,y:y,width:p.w,height:28}));
      g.appendChild(el('text',{x:p.x+8,y:y+12,'class':'n'},o.l1)); g.appendChild(el('text',{x:p.x+8,y:y+24,'class':'s'},o.l2));
      g.appendChild(el('title',{},'Click to hide'));
      g.addEventListener('click',function(){toggle(o.key);});
      s.appendChild(g);
    });
    host.appendChild(s); host.appendChild(tip);

    function at(i){return vis.filter(function(o){return i>=o.a-1&&i<=o.b+1;});}
    function show(i){
      state.i=i; if(i==null){xh.setAttribute('visibility','hidden');tip.style.display='none';return;}
      var x=X(i+.5); xh.setAttribute('x1',x); xh.setAttribute('x2',x); xh.setAttribute('visibility','visible');
      var on = vis.filter(function(o){return i>=o.a&&i<=o.b;}).map(function(o){
        return '<div class="ev'+(o.ly?' lyev':'')+'">'+(o.ly?'Last year '+o.ed.label+': ':'')+o.e.name+'</div>';}).join('');
      var bk = D.series.bookable[i];
      tip.innerHTML='<b>'+dstr(i)+'</b>'+
        '<div class="r"><span>On the books</span><b>'+pct(D.series.occ[i])+'</b></div>'+
        '<div class="r"><span>Last year ('+dstr(i,364).slice(0,-6)+')</span><b>'+pct(D.series.occ_ly[i])+'</b></div>'+
        '<div class="r"><span>Last year ADR</span><b>'+(D.series.adr_ly[i]==null?'\u2013':D.currency_symbol+D.series.adr_ly[i].toLocaleString('en-US'))+'</b></div>'+
        '<div class="r"><span>Listings bookable</span><b>'+(bk==null?'\u2013':bk.toLocaleString('en-US'))+'</b></div>'+on+
        (on?'<div class="hint">Click to show or hide details</div>':'');
      tip.style.display='block';
      var left = x+14; if(left+240>W) left = x-14-tip.offsetWidth; tip.style.left=left+'px'; tip.style.top=(PT+8)+'px';
    }
    s.addEventListener('mousemove',function(ev){var r=s.getBoundingClientRect(), x=ev.clientX-r.left; var i=Math.floor((x-L)/xw); show(i>=0&&i<N?i:null);});
    s.addEventListener('mouseleave',function(){show(null);});
    host.onkeydown=function(ev){
      if(ev.key==='Enter' && state.i!=null){ var hits=at(state.i); if(hits.length){ev.preventDefault(); toggle(hits[0].key);} return; }
      if(ev.key!=='ArrowRight'&&ev.key!=='ArrowLeft'&&ev.key!=='Escape')return; ev.preventDefault();
      if(ev.key==='Escape'){show(null);return;} var i=state.i==null?0:state.i+(ev.key==='ArrowRight'?1:-1); show(Math.max(0,Math.min(N-1,i)));};
    if(state.i!=null) show(state.i);
  }
  function toggle(k){
    if(state.shown[k]) delete state.shown[k]; else { state.shown[k]=true; state.order=state.order.filter(function(x){return x!==k;}); state.order.push(k); }
    draw();
  }
  btnLY.addEventListener('click',function(){ state.showLY=!state.showLY; btnLY.setAttribute('aria-pressed', state.showLY?'true':'false'); draw(); });
  btnReset.addEventListener('click',function(){ state.shown={}; state.defaults.forEach(function(k){state.shown[k]=true;}); state.order=[]; draw(); });
  draw(); var rt; window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(draw,120);});
})();
"""


def tier_tables(rep, cur, gen):
    out = []
    for key, name, desc in TIERS:
        rows = [e for e in rep.get("events", []) if e["tier"] == key]
        if not rows: continue
        trs = []
        for e in rows:
            fw = min(100, (e["occ"] or 0) * 100); bw = min(100, (e["base_occ"] or 0) * 100)
            yrs = "".join('<span><i>{0}</i>{1}</span>'.format(esc(x["label"]), pct(x["occ"])) for x in e["editions"])
            note = '<div class="note">{0}</div>'.format(esc(e["note"])) if e.get("note") else ""
            trs.append(
                '<tr><td class="dt">{dt}</td><td class="ev"><strong>{nm}</strong>{note}</td>'
                '<td class="num">{lst}</td>'
                '<td class="occ"><div class="occrow"><span class="bar" role="img" aria-label="Event nights {o}, same weekdays {bo}">'
                '<span class="fill" style="width:{fw:.0f}%"></span><span class="base" style="left:{bw:.0f}%"></span></span><b>{o}</b></div>'
                '<div class="yrs">{yrs}</div></td>'
                '<td class="num {lc}">{lift}<span class="sub">pts</span></td>'
                '<td class="num">{adr}</td><td class="num prem {pc}">{prem}</td></tr>'.format(
                    dt=esc(e["dates_label"]), nm=esc(e["name"]), note=note, lst=short_k(e.get("listings")),
                    o=pct(e["occ"]), bo=pct(e["base_occ"]), fw=fw, bw=bw, yrs=yrs,
                    lc=cls(e["lift_pts"], 4), lift=signed(e["lift_pts"]), adr=money(e["adr"], cur),
                    pc=cls(e["adr_prem"], 5), prem=signed(e["adr_prem"], "%")))
        out.append(
            '<section class="card t-{k}"><header class="th"><span class="pill">{n}</span>'
            '<span class="count">{c} event{s}</span><span class="tdesc">{d}</span></header>'
            '<div class="tw"><table><thead><tr><th>Next dates</th><th>Event</th>'
            '<th class="num">Market<span class="sub">listings / night</span></th>'
            '<th>Market occupancy<span class="sub">event nights, past 2 editions</span></th>'
            '<th class="num">vs. same<br>weekdays</th><th class="num">Market ADR<span class="sub">incl. fees</span></th>'
            '<th class="num">ADR premium<span class="sub">vs. same weekdays</span></th></tr></thead>'
            '<tbody>{rows}</tbody></table></div></section>'.format(
                k=key, n=name, c=len(rows), s="" if len(rows) == 1 else "s", d=desc, rows="".join(trs)))
    extra = []
    for u in rep.get("unrated") or []:
        extra.append('<div><b>{0}</b> \u00b7 {1} <span>\u00b7 {2}</span></div>'.format(
            esc(u["name"]), esc(u.get("dates_label")), esc(u.get("reason"))))
    for c in rep.get("context") or []:
        extra.append('<div><b>{0}</b> \u00b7 {1} <span>\u00b7 Season-long; shown on the chart for context, not rated</span></div>'.format(
            esc(c["name"]), esc(c.get("dates_label"))))
    if extra:
        out.append('<section class="card t-none"><header class="th"><span class="pill">Not rated</span>'
                   '<span class="tdesc">New events, or season-long ones that can\u2019t be measured against the weeks around them.</span></header>'
                   '<div class="unr">{0}</div></section>'.format("".join(extra)))
    return "\n  ".join(out)


def build(rep):
    cur = rep.get("currency") or "USD"
    sym = SYM.get(cur, cur + " ")
    market = rep.get("market_name") or ("Market " + str(rep.get("market_id")))
    gen = datetime.date.fromisoformat(rep["generated"])
    gen_label = MON[gen.month - 1] + " " + str(gen.day) + ", " + str(gen.year)
    s0 = datetime.date.fromisoformat(rep["series"]["start"]); s1 = datetime.date.fromisoformat(rep["series"]["end"])
    span = "{0} {1}, {2} to {3} {4}, {5}".format(MON[s0.month-1], s0.day, s0.year, MON[s1.month-1], s1.day, s1.year)
    ref = rep.get("reference") or {}
    ref_line = ""
    if ref:
        ref_line = ('Last 12 months: <b>{0}</b> average adjusted occupancy \u00b7 peak <b>{1} \u00b7 {2}</b> \u00b7 '
                    'softest <b>{3} \u00b7 {4}</b> \u00b7 about <b>{5:,}</b> listings bookable per night').format(
            pct(ref["avg_occ"]), MON[int(ref["peak"]["month"][5:]) - 1], pct(ref["peak"]["occ"]),
            MON[int(ref["soft"]["month"][5:]) - 1], pct(ref["soft"]["occ"]), ref["listings"])
    data = {"currency_symbol": sym, "series": rep["series"], "months": rep["months"],
            "events": rep.get("events", []), "unrated": rep.get("unrated", []), "context": rep.get("context", [])}
    tldata = json.dumps(data).replace("</", "<\\/")
    cav = " ".join(esc(c) for c in rep.get("caveats") or [])
    upd = esc((rep.get("data_updated_at") or "")[:10])
    return """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{market} event timeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@600;700;800&family=Inter:wght@400;500;600;700&family=Space+Mono:wght@700&display=swap">
<style>{css}{tlcss}</style></head><body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="eyebrow">{market} \u00b7 Event timeline \u00b7 {gen_label}</div>
      <h1>The year ahead: last year\u2019s demand, this year\u2019s bookings, and the events that move the market</h1>
      <p class="lede">Market adjusted occupancy for all Wheelhouse-tracked listings in {market}, day by day for the next 12 months. Each event is placed on its next dates and rated on how its two most recent past editions filled the market against the same weekdays around them.</p>
    </div>
    <div class="legend">
      <div class="lg"><span class="ln ly"></span>Last year, same weekday 52 weeks earlier (7-day average; shading = daily)</div>
      <div class="lg"><span class="ln"></span>On the books today (7-day average)</div>
      <div class="lg"><span class="bd"></span>Event nights this year \u00b7 darker = higher demand tier \u00b7 dashed = new or TBA</div>
      <div class="lg"><span class="hb"></span>Last year\u2019s edition, placed on the last-year line (toggle above the chart)</div>
    </div>
  </div>

  <section class="card chartcard">
    <header class="ovh">
      <div><h2>Next 12 months \u00b7 {span}</h2><div class="ref">{ref_line}</div></div>
      <div class="ctrls"><span class="hintline">Click any event band to add or remove its details</span>
        <button type="button" class="tbtn" id="btn-ly" aria-pressed="false"><span class="sw2"></span>Last year\u2019s events</button>
        <button type="button" class="tbtn" id="btn-reset">Reset</button></div>
    </header>
    <div class="cscroll"><div id="chart" tabindex="0" aria-label="Timeline chart. Use left and right arrow keys to read each night."></div></div>
    <div class="tip" id="tip"></div>
    <div class="ovnote" style="padding-top:8px">Under each month: last year\u2019s final occupancy, then what is on the books today. Bookings are still arriving, so the gap between the lines narrows as dates approach; it is not a pace signal. Far-out dates have few bookable listings, so the right end of the magenta line is thin data. Hover or use arrow keys for any night.</div>
  </section>

  {tiers}

  <div class="foot">
    <div><b>Sources.</b> Wheelhouse RM API market report: daily adjusted occupancy and ADR (incl. fees) for {market}, {dfrom} to {dto}; data updated {upd}. {src_ev}</div>
    <div><b>Method.</b> Last year\u2019s line uses the date 364 days earlier so weekdays line up. Event nights run from the night before day one to the night before the last day. Baselines use the same weekdays within 4 weeks either side, leaving out other listed events and holiday weekends. Tiers come from a score combining the occupancy lift, ADR premium and event-night occupancy against the market\u2019s 12-month average.</div>
    <div><b>Read with care.</b> Figures are market-wide, so events concentrated near one venue can look smaller here than on nearby streets. The on-the-books line is not a forecast. {cav} Data pulled {gen_label}.</div>
  </div>
</div>
<script type="application/json" id="tldata">{tldata}</script>
<script>{js}</script>
</body></html>""".format(
        market=esc(market), css=CSS, tlcss=TL_CSS, gen_label=gen_label, span=span, ref_line=ref_line,
        tiers=tier_tables(rep, cur, gen),
        dfrom=esc(rep.get("data_from")), dto=esc(rep.get("data_to")), upd=upd,
        src_ev=esc(rep.get("sources_events", "Event dates researched from organizers and press.")),
        cav=cav, tldata=tldata, js=TL_JS)

if __name__ == "__main__":
    rep = json.load(open(sys.argv[1]))
    out = build(rep)
    open(sys.argv[2], "w").write(out)
    print("wrote", sys.argv[2], len(out), "bytes")
