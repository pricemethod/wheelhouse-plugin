#!/usr/bin/env python3
"""Render a single-market event demand report from report.json.

Usage: python3 build_report.py report.json out.html

report.json = Block A's result, with overview.groups extended by Block B's
results, plus these keys Claude adds by hand:
  market_name      e.g. "Denver, CO"
  overview.summary 2-3 sentences on the next six months (whole market)
  sources_events   one line on where event dates came from
  caveats          list of short strings for "Read with care"
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

JS = r"""
(function(){
  var D = JSON.parse(document.getElementById('ovdata').textContent);
  var box = document.getElementById('months'), note = document.getElementById('grpnote');
  var cur = D.currency_symbol, ly = D.ly_short, MINUS = '\u2212', paceColor = D.basis === 'stly';
  function pct(v){return v==null?'\u2013':Math.round(v*100)+'%';}
  function money(v){return v==null?'\u2013':cur+Math.round(v).toLocaleString('en-US');}
  function sgn(v,u){if(v==null)return '\u2013';var r=Math.round(v);if(r===0)return '\u00b10'+u;return (r>0?'+':MINUS)+Math.abs(r)+u;}
  function cl(v,c){if(v==null||Math.abs(v)<c)return 'flat';return v>0?'pos':'neg';}
  function rel(a,b){return (a!=null&&b)?(a/b-1)*100:null;}
  function render(key){
    var g = D.groups[key]; if(!g){return;}
    if(g.error){box.innerHTML='<div class="mt">No data for this group.</div>';note.textContent='';return;}
    var h='';
    g.months.forEach(function(m){
      var d = (m.occ!=null&&m.occ_ly!=null)?(m.occ-m.occ_ly)*100:null;
      var fw = m.occ==null?0:Math.min(100,m.occ*100), bw = m.occ_ly==null?null:Math.min(100,m.occ_ly*100);
      var ra=rel(m.adr,m.adr_ly), rk=rel(m.ask,m.ask_ly);
      h+='<div class="mt"><div class="mn">'+m.label+'</div>'+
        '<div class="big">'+pct(m.occ)+'<span> on the books</span></div>'+
        '<span class="bar" role="img" aria-label="'+pct(m.occ)+' on the books, '+ly+' '+pct(m.occ_ly)+'"><span class="fill" style="width:'+fw+'%"></span>'+(bw==null?'':'<span class="base" style="left:'+bw+'%"></span>')+'</span>'+
        '<div class="kv"><span>'+ly+'</span><b>'+pct(m.occ_ly)+'<small class="'+(paceColor?cl(d,4):'flat')+'">'+sgn(d,' pts')+'</small></b></div>'+
        '<div class="kv"><span>ADR</span><b>'+money(m.adr)+'<small class="'+cl(ra,5)+'">'+sgn(ra,'%')+'</small></b></div>'+
        '<div class="kv"><span>Asking rate</span><b>'+money(m.ask)+'<small class="'+cl(rk,5)+'">'+sgn(rk,'%')+'</small></b></div>'+
        '<div class="kv"><span>Listings / night</span><b>'+(m.listings==null?'\u2013':m.listings.toLocaleString('en-US'))+'</b></div></div>';
    });
    box.innerHTML=h;
    note.textContent = g.thin ? 'Thin group: about '+g.market_listings+' listings in this bedroom group, so single bookings move these figures.' : '';
    note.hidden = !g.thin;
  }
  var btns = document.querySelectorAll('.chips button');
  btns.forEach(function(b){b.addEventListener('click',function(){
    btns.forEach(function(x){x.setAttribute('aria-pressed','false');});
    b.setAttribute('aria-pressed','true'); render(b.dataset.g);});});
  render('all');
})();
"""

def build(rep):
    cur = rep.get("currency") or "USD"
    sym = SYM.get(cur, cur + " ")
    market = rep.get("market_name") or ("Market " + str(rep.get("market_id")))
    ov = rep["overview"]
    stly = ov.get("basis") == "stly"
    ly_short = "STLY" if stly else "LY final"
    gen = datetime.date.fromisoformat(rep["generated"])
    gen_label = MON[gen.month - 1] + " " + str(gen.day) + ", " + str(gen.year)
    end_year = gen.year + 1
    ref = rep.get("reference") or {}

    # overview groups: add month labels, thin flags, ordering
    groups = {}
    order = ["all"] + sorted([k for k in ov["groups"] if k != "all"],
                             key=lambda k: (int(k.rstrip("+")) if k.rstrip("+").isdigit() else 99, k))
    for k in order:
        g = dict(ov["groups"][k])
        if "months" in g:
            g["months"] = [dict(m, label=mlabel(m["month"])) for m in g["months"]]
        ml = g.get("market_listings")
        g["thin"] = bool(ml is not None and ml < 100)
        groups[k] = g
    chips = "".join('<button type="button" data-g="{0}" aria-pressed="{1}">{2}</button>'.format(
        esc(k), "true" if k == "all" else "false", esc(groups[k].get("label", k))) for k in order)
    first_m = groups["all"]["months"][0]["label"]; last_m = groups["all"]["months"][-1]["label"]

    ref_line = ""
    if ref:
        ref_line = ('Last 12 months: <b>{0}</b> average adjusted occupancy · peak <b>{1} · {2}</b> · '
                    'softest <b>{3} · {4}</b> · about <b>{5:,}</b> listings bookable per night').format(
            pct(ref["avg_occ"]), MON[int(ref["peak"]["month"][5:]) - 1], pct(ref["peak"]["occ"]),
            MON[int(ref["soft"]["month"][5:]) - 1], pct(ref["soft"]["occ"]), ref["listings"])
    ly_expl = ("Ticks and comparisons show the same stay dates as they stood at this time last year (STLY)."
               if stly else
               "Ticks and comparisons show last year\u2019s final results for the same month (LY final), not where last year stood at this point. "
               "Bookings are still arriving for future months, so nearer months will usually read behind LY final; that gap is not a pace signal.")

    ovdata = json.dumps({"currency_symbol": sym, "ly_short": ly_short, "basis": ov.get("basis"), "groups": groups}).replace("</", "<\\/")

    # event tiers
    tiers_html = []
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
        tiers_html.append(
            '<section class="card t-{k}"><header class="th"><span class="pill">{n}</span>'
            '<span class="count">{c} event{s}</span><span class="tdesc">{d}</span></header>'
            '<div class="tw"><table><thead><tr><th>{y1}\u2013{y2} dates</th><th>Event</th>'
            '<th class="num">Market<span class="sub">listings / night</span></th>'
            '<th>Market occupancy<span class="sub">event nights, past 2 editions</span></th>'
            '<th class="num">vs. same<br>weekdays</th><th class="num">Market ADR<span class="sub">incl. fees</span></th>'
            '<th class="num">ADR premium<span class="sub">vs. same weekdays</span></th></tr></thead>'
            '<tbody>{rows}</tbody></table></div></section>'.format(
                k=key, n=name, c=len(rows), s="" if len(rows) == 1 else "s", d=desc,
                y1=gen.year, y2=str(end_year)[2:], rows="".join(trs)))
    unr = rep.get("unrated") or []
    if unr:
        items = "".join('<div><b>{0}</b> · {1} <span>· {2}</span></div>'.format(
            esc(u["name"]), esc(u.get("dates_label")), esc(u.get("reason"))) for u in unr)
        tiers_html.append('<section class="card t-none"><header class="th"><span class="pill">Not rated</span>'
                          '<span class="tdesc">Upcoming, but no past edition to measure.</span></header>'
                          '<div class="unr">{0}</div></section>'.format(items))

    caveats = rep.get("caveats") or []
    cav = " ".join(esc(c) for c in caveats)
    upd = esc((rep.get("data_updated_at") or "")[:10])

    return """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{market} market report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@600;700;800&family=Inter:wght@400;500;600;700&family=Space+Mono:wght@700&display=swap">
<style>{css}</style></head><body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="eyebrow">{market} · Market report · {gen_label}</div>
      <h1>The next six months, and how past events filled the market</h1>
      <p class="lede">Market occupancy and rates for all Wheelhouse-tracked listings in {market}: a month-by-month outlook, then each upcoming event measured on its two most recent past editions against the same weekdays in the four weeks before and after.</p>
    </div>
    <div class="legend">
      <div class="lg"><span class="sw"></span>Bar = occupancy · tick = comparison (last year above, same weekdays below)</div>
      <div class="lg"><b class="pos">+12%</b>&nbsp;premium · <b class="neg">{minus}8%</b>&nbsp;discount · grey = small change</div>
      <div class="lg">Rates include guest fees (market report basis)</div>
    </div>
  </div>

  <section class="card">
    <header class="ovh">
      <div><h2>Next six months · {first_m} to {last_m}</h2><div class="ref">{ref_line}</div></div>
      <div class="chips" role="group" aria-label="Bedroom group">{chips}</div>
    </header>
    <p class="summary"><span class="slabel">All bedrooms</span>{summary}</p>
    <p class="thin" id="grpnote" hidden></p>
    <div class="months" id="months"></div>
    <div class="ovnote">{ly_expl} Rates include guest fees; ADR is for booked nights, asking rate for open nights. Changes under ADR and asking rate compare with {ly_short}.</div>
  </section>

  {tiers}

  <div class="foot">
    <div><b>Sources.</b> Wheelhouse RM API market report: daily adjusted occupancy, ADR and asking rate (incl. fees) for {market}, {dfrom} to {dto}; data updated {upd}. {src_ev}</div>
    <div><b>Method.</b> Monthly figures weight each day by bookable nights; ADR by booked nights; asking rate by available nights. Event nights run from the night before day one to the night before the last day. Baselines use the same weekdays within 4 weeks either side, leaving out other listed events and holiday weekends. Tiers come from a score combining the occupancy lift, ADR premium and event-night occupancy against the market\u2019s 12-month average.</div>
    <div><b>Read with care.</b> Figures are market-wide, so events concentrated near one venue can look smaller here than on nearby streets. Future months are on the books, not a forecast. {cav} Data pulled {gen_label}.</div>
  </div>
</div>
<script type="application/json" id="ovdata">{ovdata}</script>
<script>{js}</script>
</body></html>""".format(
        market=esc(market), css=CSS, gen_label=gen_label, minus=MINUS, first_m=first_m, last_m=last_m,
        ref_line=ref_line, chips=chips, ly_short=ly_short, summary=esc(ov.get("summary", "")), ly_expl=ly_expl,
        tiers="\n  ".join(tiers_html), dfrom=esc(rep.get("data_from")), dto=esc(rep.get("data_to")),
        upd=upd, src_ev=esc(rep.get("sources_events", "Event dates researched from organizers and press.")),
        cav=cav, ovdata=ovdata, js=JS)

if __name__ == "__main__":
    rep = json.load(open(sys.argv[1]))
    out = build(rep)
    open(sys.argv[2], "w").write(out)
    print("wrote", sys.argv[2], len(out), "bytes")
