"""Lineup pages and machine-readable lineup files, from data/lineup/<year>.json.

Called by build.py. For each year file it writes:
  /lineup/<year>/index.html   the poster, re-set in the guide's own type, plus a searchable table of every act
  /lineup-<year>.json         the data file as-is (canonical)
  /lineup-<year>.csv          one row per act
  /lineup-<year>.txt          plain text, one act per line, for agents and quick copy-paste
and returns llms.txt lines and sitemap paths.

To add a year: copy data/lineup/2027.json, transcribe the poster line by line, keep names exactly as printed.
"""
import csv, html, io, json, pathlib

e = lambda s: html.escape(str(s), quote=True)
DAYNUM = {"Friday": 0, "Saturday": 1, "Sunday": 2}
SIZES = {1: "l1", 2: "l2", 3: "l3", 4: "l4", 5: "l5", 6: "l6", 7: "l7", 8: "l8"}

CSS = """
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.lu{max-width:76rem;margin:0 auto;padding:0 clamp(1rem,4vw,2.5rem) 3rem}
.lu h1.ch{margin-top:1.2rem}
.lu .lede{max-width:44rem;font-size:1.08rem}
.lu .tools{display:flex;flex-wrap:wrap;gap:.6rem 1rem;align-items:center;margin:1.2rem 0 .4rem;font:600 .78rem/1.3 var(--f-mono);letter-spacing:.04em}
.lu .tools a{color:var(--ink)}
.lu .tools input{font:400 1rem/1.2 var(--f-mono);padding:.55rem .7rem;border:1px solid var(--line);border-radius:10px;background:var(--paper);color:var(--ink);min-width:min(100%,18rem)}
.lu .tools .cnt{color:var(--muted)}
.lu-poster{border-radius:22px;padding:clamp(1.4rem,4.5vw,3.2rem) clamp(.9rem,3.5vw,2.8rem);background:radial-gradient(120% 80% at 50% 115%,color-mix(in srgb,var(--sunset) 34%,transparent),transparent 62%),radial-gradient(90% 60% at 0% -10%,color-mix(in srgb,var(--lilac) 30%,transparent),transparent 60%),var(--paper2);margin:1rem 0 2rem}
.lu-day{margin:0 0 2.2rem}
.lu-day:last-of-type{margin-bottom:1rem}
.lu-day .dh{display:inline-block;font:600 .74rem/1 var(--f-mono);letter-spacing:.18em;text-transform:uppercase;color:var(--paper);background:var(--ink);padding:.45rem .7rem;border-radius:999px;margin:0 0 .6rem}
.lu-day:nth-of-type(even){text-align:right}
.lu-line{margin:.18rem 0;line-height:1.06;display:flex;flex-wrap:wrap;gap:.05em .2em;justify-content:flex-start}
.lu-day:nth-of-type(even) .lu-line{justify-content:flex-end}
.lu-line .a{white-space:nowrap;color:var(--ink);text-decoration:none;border-radius:6px;padding:0 .08em;scroll-margin-top:5rem}
.lu-line .a:hover,.lu-line .a:target{background:color-mix(in srgb,var(--sun) 40%,transparent)}
.lu-line .a:not(:last-child)::after{content:"·";color:var(--pink);margin:0 .06em 0 .28em;font-weight:400;-webkit-text-fill-color:var(--pink)}
.lu-line .a .nt{display:block;font:600 .62rem/1 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.1em}
.lu-line.l1{font:900 clamp(2.6rem,9vw,6rem)/.95 var(--f-display);text-transform:none}
.lu-line.l1 .a{background:var(--dusk);-webkit-background-clip:text;background-clip:text;color:transparent}
.lu-line.l2{font:800 clamp(1.15rem,2.9vw,2.05rem)/1.12 var(--f-display)}
.lu-line.l3{font:800 clamp(1rem,2.4vw,1.6rem)/1.15 var(--f-display)}
.lu-line.l4{font:800 clamp(.95rem,2vw,1.35rem)/1.2 var(--f-display)}
.lu-line.l5{font:700 clamp(.9rem,1.8vw,1.15rem)/1.25 var(--f-display)}
.lu-line.l6{font:700 clamp(.85rem,1.6vw,1.05rem)/1.3 var(--f-display)}
.lu-line.l7,.lu-line.l8{font:700 clamp(.8rem,1.45vw,.98rem)/1.3 var(--f-display)}
.lu-line .a.hide{opacity:.12}
.lu-special{text-align:center;margin:1.6rem 0 .4rem}
.lu-special .sp{font:900 clamp(2rem,6vw,3.8rem)/1 var(--f-display);margin:.2rem 0}
.lu-special .k{font:600 .72rem/1.4 var(--f-mono);letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.lu-special .sm{font:800 clamp(1rem,2.4vw,1.5rem)/1.2 var(--f-display);margin:1.2rem 0 .2rem}
.lu .facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.8rem;margin:1.6rem 0}
.lu .facts div{background:var(--paper2);border-radius:14px;padding:.9rem 1rem}
.lu .facts b{display:block;font:900 1.9rem/1 var(--f-display)}
.lu .facts span{font:600 .72rem/1.35 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.lu table{width:100%;border-collapse:collapse;font-size:.95rem}
.lu .tbl{overflow-x:auto;margin:.6rem 0 1.4rem}
.lu th,.lu td{text-align:left;padding:.42rem .55rem;border-bottom:1px solid var(--line);vertical-align:top}
.lu th{font:600 .7rem/1.2 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.lu td.n{font-family:var(--f-mono);font-variant-numeric:tabular-nums}
.lu tr.hide{display:none}
.lu .src li{margin:.3rem 0}
@media (max-width:640px){.lu-day:nth-of-type(even){text-align:left}.lu-day:nth-of-type(even) .lu-line{justify-content:flex-start}}
"""

JS = """(function(){var q=document.getElementById('lu-q');if(!q)return;var as=[].slice.call(document.querySelectorAll('.lu-line .a')),rs=[].slice.call(document.querySelectorAll('#lu-rows tr')),c=document.getElementById('lu-cnt');
function n(s){return s.normalize('NFKD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}
function go(){var t=n(q.value.trim()),k=0;as.forEach(function(a){var m=!t||n(a.dataset.n).indexOf(t)>-1;a.classList.toggle('hide',!m)});
rs.forEach(function(r){var m=!t||n(r.dataset.n).indexOf(t)>-1;r.classList.toggle('hide',!m);if(m)k++});c.textContent=t?(k+' match'+(k==1?'':'es')):(rs.length+' acts');}
q.addEventListener('input',go);go();})();"""


def _fmt_dates(ds):
    import datetime
    a, b = (datetime.date.fromisoformat(x) for x in ds)
    return f"{a.strftime('%B')} {a.day} and {b.day}" if a.month == b.month else f"{a.strftime('%B')} {a.day} and {b.strftime('%B')} {b.day}"


def rows(L):
    for d in L["days"]:
        for a in d["acts"]:
            yield {"name": a["name"], "slug": a["slug"], "day": d["day"], "weekend1": d["dates"][0], "weekend2": d["dates"][1],
                   "line": a["line"], "position": a["position"], "headliner": a["headliner"], "note": a.get("note", ""),
                   "members": " + ".join(a.get("members", []))}
    for s in L.get("special_billings", []):
        yield {"name": s["name"], "slug": s["slug"], "day": "", "weekend1": "", "weekend2": "", "line": "", "position": "",
               "headliner": s.get("headliner", False), "note": s["billing"], "members": ""}


def ld(L, site, path):
    loc = {"@type": "Place", "name": "Empire Polo Club", "address": {"@type": "PostalAddress", "addressLocality": "Indio", "addressRegion": "CA", "addressCountry": "US"}}
    subs = []
    for d in L["days"]:
        perf = [{"@type": "PerformingGroup", "name": a["name"]} for a in d["acts"]]
        for i, dt in enumerate(d["dates"], 1):
            subs.append({"@type": "MusicEvent", "name": f"Coachella {L['year']} - {d['day']}, weekend {i}", "startDate": dt, "endDate": dt,
                         "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                         "location": loc, "performer": perf})
    fest = {"@context": "https://schema.org", "@type": "Festival", "name": f"Coachella Valley Music and Arts Festival {L['year']}",
            "startDate": L["weekends"][0][0], "endDate": L["weekends"][-1][1], "location": loc,
            "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "organizer": {"@type": "Organization", "name": "Goldenvoice"}, "subEvent": subs,
            "performer": [{"@type": "PerformingGroup", "name": s["name"]} for s in L.get("special_billings", [])],
            "description": f"Lineup as announced {L['announced']}. Transcribed by an independent guide, not affiliated with Coachella, Goldenvoice or AEG.",
            "url": site + path}
    ds = {"@context": "https://schema.org", "@type": "Dataset", "name": f"Coachella {L['year']} lineup, structured",
          "description": f"Every act on the official Coachella {L['year']} lineup poster, by day, poster line and position, with spellings as printed. Independent; not affiliated with Coachella, Goldenvoice or AEG.",
          "url": site + path, "dateModified": L["updated"], "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
          "creator": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
          "distribution": [{"@type": "DataDownload", "encodingFormat": f, "contentUrl": f"{site}/lineup-{L['year']}.{x}"}
                           for x, f in (("json", "application/json"), ("csv", "text/csv"), ("txt", "text/plain"))]}
    return [fest, ds]


def page(L, site):
    y = L["year"]
    n_acts = sum(len(d["acts"]) for d in L["days"]) + len(L.get("special_billings", []))
    days_html = ""
    for d in L["days"]:
        lines = {}
        for a in d["acts"]:
            lines.setdefault(a["line"], []).append(a)
        body = ""
        for ln in sorted(lines):
            items = ""
            for a in lines[ln]:
                nt = f'<span class="nt">{e(a["note"])}</span>' if a.get("note") else ""
                items += f'<a class="a" id="a-{e(a["slug"])}" href="#a-{e(a["slug"])}" data-n="{e(a["name"])}">{nt}{e(a["name"])}</a>'
            body += f'<p class="lu-line {SIZES.get(ln, "l8")}">{items}</p>'
        days_html += f'<section class="lu-day" aria-label="{e(d["day"])}"><p class="dh">{e(d["day"])} · {e(_fmt_dates(d["dates"]))}</p>{body}</section>'
    sp = L.get("special_billings", [])
    spec = ""
    for s in sp:
        cls = "sp" if s.get("headliner") else "sm"
        spec += (f'<p class="{cls}"><a class="a" id="a-{e(s["slug"])}" href="#a-{e(s["slug"])}" data-n="{e(s["name"])}" style="color:inherit;text-decoration:none">{e(s["name"])}</a></p>'
                 f'<p class="k">{e(s["billing"])} · day not announced</p>')
    trs = "".join(f'<tr data-n="{e(r["name"])} {e(r["day"])} {e(r["note"])}"><td><a href="#a-{e(r["slug"])}">{e(r["name"])}</a></td><td>{e(r["day"] or "TBA")}</td>'
                  f'<td class="n">{e(r["line"])}</td><td class="n">{e(r["position"])}</td><td>{e(r["note"])}{(" (" + e(r["members"]) + ")") if r["members"] else ""}</td></tr>'
                  for r in rows(L))
    per_day = " · ".join(f'{d["day"]} {len(d["acts"])}' for d in L["days"])
    srcs = "".join(f'<li>{e(s["publication"])} - "{e(s["title"])}" - {e(s["date"])}' + (f' - <a href="{e(s["url"])}" rel="noopener" target="_blank">link</a>' if s.get("url") else " (the poster itself)") + "</li>" for s in L["sources"])
    t = L.get("tickets", {})
    return f"""<main class="lu" id="main">
<p class="readmeta">Lineup · announced {e(L['announced'])} · updated {e(L['updated'])}</p>
<h1 class="ch">Coachella {y}: the full lineup</h1>
<p class="lede">Every act on the official {y} poster, re-set line by line in this guide's own type, with spellings exactly as printed. The same lineup plays both weekends, April 9-11 and April 16-18, {y}, at the Empire Polo Club in Indio. Poster order is billing, not set order; stages and set times come later.</p>
<div class="facts"><div><b>{n_acts}</b><span>acts on the poster</span></div><div><b>3 + 1</b><span>day headliners Dua Lipa, Tame Impala, SZA, plus Daddy Yankee "In the Desert"</span></div><div><b>{"/".join(str(len(d["acts"])) for d in L["days"])}</b><span>acts Fri / Sat / Sun</span></div><div><b>Nov. 13</b><span>passes on sale, noon PT</span></div></div>
<div class="tools"><label for="lu-q" class="sr">Find an act</label><input id="lu-q" type="search" placeholder="Find an act" autocomplete="off"><span class="cnt" id="lu-cnt"></span>
<span>Data: <a href="/lineup-{y}.json">JSON</a> · <a href="/lineup-{y}.csv">CSV</a> · <a href="/lineup-{y}.txt">plain text</a> · <a href="/llms.txt">llms.txt</a></span></div>
<div class="lu-poster">{days_html}<div class="lu-special">{spec}</div></div>
<h2>How to read the poster</h2>
<p>Each day is a block. The first line is that day's headliner; every line after it is set smaller, and the size is billing, not fee and not set time. Within a line, names run left to right in the order printed. Madonna is billed on Friday's second line with "In the Dance Tent" above her name. Daddy Yankee sits on his own line under Sunday with "In the Desert" and no day, and was reported as a fourth headliner in a "special production." Justice is printed at the very bottom as "The Bunker Debut Of JUSTICE - Blinded By The Lights," also with no day. For what billing size means and who fights over it, see <a href="/lineup/">the lineup chapter</a>.</p>
<h2>Every act</h2>
<p class="note">Line 1 is the headliner row; higher numbers are smaller type. Names that join two acts with "x" are listed as one billing with both members noted.</p>
<div class="tbl"><table><thead><tr><th>Act</th><th>Day</th><th>Line</th><th>Pos.</th><th>Note</th></tr></thead><tbody id="lu-rows">{trs}</tbody></table></div>
<h2>Tickets and stream</h2>
<p>General passes go on sale Friday, Nov. 13, 2026, at noon PT, per <a href="https://gvwire.com/2026/11/10/dua-lipa-tame-impala-and-sza-to-headline-coachella-2027/" rel="noopener" target="_blank">GV Wire</a>; Yahoo reported an American Express presale the day before, at noon PT. None of the sources gathered here listed prices. YouTube is the livestream partner for a 15th year, per GV Wire. Daddy Yankee's "fourth headliner" and "special production" wording is <a href="https://www.yahoo.com/entertainment/music/festivals/articles/coachella-2027-sets-dua-lipa-064237129.html" rel="noopener" target="_blank">Yahoo's</a>.</p>
<h2>Sources</h2>
<ol class="src">{srcs}</ol>
<p class="note">Independent transcription. Not affiliated with Coachella, Goldenvoice or AEG. Spot a misspelling or a change? <a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20lineup%20{y}">Tell us</a> and it will be logged on <a href="/corrections/">corrections</a>.</p>
</main>"""


def files(L):
    y = L["year"]
    out = {f"lineup-{y}.json": json.dumps(L, indent=1, ensure_ascii=False) + "\n"}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["name", "slug", "day", "weekend1", "weekend2", "line", "position", "headliner", "note", "members"])
    w.writeheader()
    for r in rows(L):
        w.writerow(r)
    out[f"lineup-{y}.csv"] = buf.getvalue()
    txt = [f"Coachella {y} lineup - as announced {L['announced']}, transcribed from the official poster by polo.cold.fyi (independent).",
           f"Weekends: {L['weekends'][0][0]} to {L['weekends'][0][1]} and {L['weekends'][1][0]} to {L['weekends'][1][1]}, Empire Polo Club, Indio, California. Same lineup both weekends.",
           "Format: day | poster line (1 = headliner) | act as printed | note", ""]
    for r in rows(L):
        txt.append(" | ".join([r["day"] or "Day TBA", str(r["line"] or "-"), r["name"], r["note"]]).rstrip(" |"))
    out[f"lineup-{y}.txt"] = "\n".join(txt) + "\n"
    return out


def llms_lines(L, site):
    y = L["year"]
    out = ["", f"## Coachella {y} lineup (announced {L['announced']})",
           f"- Page: {site}/lineup/{y}/ - data: {site}/lineup-{y}.json, {site}/lineup-{y}.csv, {site}/lineup-{y}.txt",
           f"- Weekends {L['weekends'][0][0]}-{L['weekends'][0][1][-2:]} and {L['weekends'][1][0]}-{L['weekends'][1][1][-2:]}; the same lineup plays both."]
    for d in L["days"]:
        h = [a["name"] for a in d["acts"] if a["line"] == 1]
        rest = [a["name"] + (f" ({a['note']})" if a.get("note") else "") for a in d["acts"] if a["line"] != 1]
        out.append(f"- {d['day']} ({', '.join(d['dates'])}): headliner {', '.join(h)}; then {', '.join(rest)}")
    for s in L.get("special_billings", []):
        out.append(f"- {s['name']}: billed \"{s['billing']}\", no day announced. {s.get('note','')}")
    return out
