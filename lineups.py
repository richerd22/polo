"""Lineup pages, the all-years archive and machine-readable files.

Inputs
  data/lineup/<year>.json    a poster transcribed line by line (2027 onward)
  data/history/<year>.json   past lineups by day and stage (transcribed from Wikipedia, see data/history/README.md)
  data/years.json, data/calendar.json  headliners by year

Outputs (written through build.py's write/shell)
  /lineup/<year>/                 poster re-set in the guide's own type, day filter, A-Z, search, table, FAQ
  /lineup/<year>/<day>/           one page per day
  /lineup/<year>/a/<slug>/        one page per act: day, dates, billing, Coachella history, searches to find them
  /lineup/<year>/history/         returning acts and likely debuts, with the stage and day of every past set
  /archive/  /archive/<year>/     every past lineup by day and stage; /archive/artists/ every act ever, A-Z
  /headliners/                    every headliner by year
  /lineup-<year>.json|.csv|.txt, /lineup-<year>-history.json, /coachella-<year>.ics, /archive.json, /headliners.json

Rules carried from AGENTS.md: names exactly as printed, nothing stated without a source, no official artwork,
and outbound "find them" links are searches (never a guessed profile URL). Matching across years is exact
on a normalized name (case, accents, "the", punctuation); anything looser is not counted.
"""
import csv, datetime, html, io, json, pathlib, re, unicodedata, urllib.parse

e = lambda s: html.escape(str(s), quote=True)
DAYS = ["Friday", "Saturday", "Sunday"]
SEARCH = [("Spotify", "https://open.spotify.com/search/{q}"), ("Apple Music", "https://music.apple.com/us/search?term={q}"),
          ("YouTube", "https://www.youtube.com/results?search_query={q}"), ("SoundCloud", "https://soundcloud.com/search?q={q}"),
          ("Bandcamp", "https://bandcamp.com/search?q={q}")]
WIKI = "https://en.wikipedia.org/wiki/Coachella_Festival_line-ups"

CSS = """
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.lu{max-width:76rem;margin:0 auto;padding:0 clamp(1rem,4vw,2.5rem) 3rem}
.lu h1.ch{margin-top:1.2rem}
.lu .lede{max-width:46rem;font-size:1.08rem}
.lu .bc{font:600 .74rem/1.4 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:1rem 0 0}
.lu .bc a{color:var(--muted)}
.lu .tools{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;gap:.5rem .8rem;align-items:center;margin:1.2rem 0 .4rem;padding:.6rem 0;background:var(--paper);font:600 .78rem/1.3 var(--f-mono);letter-spacing:.04em}
.lu .tools a{color:var(--ink)}
.lu .tools input{font:400 1rem/1.2 var(--f-mono);padding:.55rem .7rem;border:1px solid var(--line);border-radius:10px;background:var(--paper);color:var(--ink);min-width:min(100%,16rem)}
.lu .tools .cnt{color:var(--muted)}
.lu .chips{display:flex;flex-wrap:wrap;gap:.35rem;margin:.6rem 0}
.lu .chips a,.lu .chips button{font:600 .74rem/1 var(--f-mono);letter-spacing:.08em;text-transform:uppercase;padding:.5rem .7rem;border-radius:999px;border:1px solid var(--line);background:var(--paper2);color:var(--ink);text-decoration:none;cursor:pointer}
.lu .chips [aria-pressed="true"],.lu .chips a.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.lu .az{display:flex;flex-wrap:wrap;gap:.15rem;margin:.2rem 0 1rem;font:600 .78rem/1 var(--f-mono)}
.lu .az a,.lu .az span{padding:.35rem .42rem;border-radius:6px;text-decoration:none;color:var(--ink)}
.lu .az span{color:var(--muted);opacity:.45}
.lu .az a:hover{background:var(--paper2)}
.lu-poster{border-radius:22px;padding:clamp(1.4rem,4.5vw,3.2rem) clamp(.9rem,3.5vw,2.8rem);background:radial-gradient(120% 80% at 50% 115%,color-mix(in srgb,var(--sunset) 34%,transparent),transparent 62%),radial-gradient(90% 60% at 0% -10%,color-mix(in srgb,var(--lilac) 30%,transparent),transparent 60%),var(--paper2);margin:1rem 0 2rem}
.lu-day{margin:0 0 2.2rem}
.lu-day:last-of-type{margin-bottom:1rem}
.lu-day .dh{display:inline-block;font:600 .74rem/1 var(--f-mono);letter-spacing:.18em;text-transform:uppercase;color:var(--paper);background:var(--ink);padding:.45rem .7rem;border-radius:999px;margin:0 0 .6rem;text-decoration:none}
.lu-poster.multi .lu-day:nth-of-type(even){text-align:right}
.lu-line{margin:.18rem 0;line-height:1.06;display:flex;flex-wrap:wrap;gap:.05em .2em;justify-content:flex-start}
.lu-poster.multi .lu-day:nth-of-type(even) .lu-line{justify-content:flex-end}
.lu-line .a{white-space:nowrap;color:var(--ink);text-decoration:none;border-radius:6px;padding:0 .08em;scroll-margin-top:7rem}
.lu-line .a:hover,.lu-line .a:focus-visible{background:color-mix(in srgb,var(--sun) 40%,transparent)}
.lu-line .a:not(:last-child)::after{content:"·";color:var(--pink);margin:0 .06em 0 .28em;font-weight:400;-webkit-text-fill-color:var(--pink)}
.lu-line .a .nt{display:block;font:600 .62rem/1 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.1em}
.lu-line .a .rb{font:600 .5em/1 var(--f-mono);letter-spacing:.04em;vertical-align:super;color:var(--turf);-webkit-text-fill-color:var(--turf);margin-left:.15em}
.lu-line.l1{font:900 clamp(2.6rem,9vw,6rem)/.95 var(--f-display)}
.lu-line.l1 .a{background:var(--dusk);-webkit-background-clip:text;background-clip:text;color:transparent}
.lu-line.l2{font:800 clamp(1.15rem,2.9vw,2.05rem)/1.12 var(--f-display)}
.lu-line.l3{font:800 clamp(1rem,2.4vw,1.6rem)/1.15 var(--f-display)}
.lu-line.l4{font:800 clamp(.95rem,2vw,1.35rem)/1.2 var(--f-display)}
.lu-line.l5{font:700 clamp(.9rem,1.8vw,1.15rem)/1.25 var(--f-display)}
.lu-line.l6{font:700 clamp(.85rem,1.6vw,1.05rem)/1.3 var(--f-display)}
.lu-line.l7,.lu-line.l8{font:700 clamp(.8rem,1.45vw,.98rem)/1.3 var(--f-display)}
.lu-line .a.hide{opacity:.12}
.lu-day.off{display:none}
.lu-special{text-align:center;margin:1.6rem 0 .4rem}
.lu-special .sp{font:900 clamp(2rem,6vw,3.8rem)/1 var(--f-display);margin:.2rem 0}
.lu-special .sm{font:800 clamp(1rem,2.4vw,1.5rem)/1.2 var(--f-display);margin:1.2rem 0 .2rem}
.lu-special .k{font:600 .72rem/1.4 var(--f-mono);letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.lu-special a{color:inherit;text-decoration:none}
.lu .facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.8rem;margin:1.6rem 0}
.lu .facts div{background:var(--paper2);border-radius:14px;padding:.9rem 1rem}
.lu .facts b{display:block;font:900 1.9rem/1 var(--f-display)}
.lu .facts span{font:600 .72rem/1.35 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.lu .answer{background:var(--paper2);border-radius:18px;padding:1.2rem 1.3rem;margin:1.2rem 0;max-width:46rem}
.lu .answer .big{font:900 clamp(1.8rem,5vw,2.8rem)/1.02 var(--f-display);margin:0 0 .3rem}
.lu .answer dl{display:grid;grid-template-columns:max-content 1fr;gap:.35rem 1rem;margin:.8rem 0 0}
.lu .answer dt{font:600 .72rem/1.6 var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.lu .answer dd{margin:0}
.lu .find{display:flex;flex-wrap:wrap;gap:.4rem;margin:.5rem 0 1rem}
.lu .find a{font:600 .78rem/1 var(--f-mono);padding:.55rem .75rem;border-radius:10px;background:var(--paper2);color:var(--ink);text-decoration:none;border:1px solid var(--line)}
.lu .find a:hover{border-color:var(--ink)}
.lu .pn{display:flex;justify-content:space-between;gap:1rem;margin:2rem 0;font:600 .8rem/1.4 var(--f-mono)}
.lu .pn a{color:var(--ink)}
.lu table{width:100%;border-collapse:collapse;font-size:.95rem}
.lu .tbl{overflow-x:auto;margin:.6rem 0 1.4rem}
.lu th,.lu td{text-align:left;padding:.42rem .55rem;border-bottom:1px solid var(--line);vertical-align:top}
.lu th{font:600 .7rem/1.2 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.lu td.n{font-family:var(--f-mono);font-variant-numeric:tabular-nums}
.lu tr.hide,.lu li.hide{display:none}
.lu .faq dt{font-weight:600;margin-top:1rem}
.lu .faq dd{margin:.25rem 0 0}
.lu .src li{margin:.3rem 0}
.lu .stage{margin:0 0 1.2rem}
.lu .stage h3{font:600 .76rem/1.3 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:.8rem 0 .3rem}
.lu .stage p{margin:0;line-height:1.55}
.lu .stage p a{color:var(--ink)}
.lu .yrs{display:flex;flex-wrap:wrap;gap:.3rem;margin:1rem 0}
.lu .yrs a{font:700 .9rem/1 var(--f-mono);padding:.5rem .6rem;border-radius:8px;background:var(--paper2);color:var(--ink);text-decoration:none}
.lu .yrs a.on{background:var(--ink);color:var(--paper)}
.lu .ix{columns:16rem;column-gap:2rem;list-style:none;padding:0;font-size:.95rem}
.lu .ix li{break-inside:avoid;margin:0 0 .3rem}
.lu .ix li span{font:400 .78rem/1 var(--f-mono);color:var(--muted)}
.lu .callout{border-left:4px solid var(--sunset);background:var(--paper2);border-radius:0 14px 14px 0;padding:1rem 1.2rem;margin:1.4rem 0;max-width:46rem}
.lu .callout h3{margin:0 0 .4rem;font:800 1.25rem/1.15 var(--f-display)}
.lu .callout p{margin:.4rem 0 0}
@media (max-width:640px){.lu-poster.multi .lu-day:nth-of-type(even){text-align:left}.lu-poster.multi .lu-day:nth-of-type(even) .lu-line{justify-content:flex-start}.lu .tools{position:static}}
"""

JS = """(function(){var q=document.getElementById('lu-q');if(!q)return;var as=[].slice.call(document.querySelectorAll('.lu-line .a,.lu-special .a')),rs=[].slice.call(document.querySelectorAll('#lu-rows tr,#lu-rows li')),c=document.getElementById('lu-cnt'),
ds=[].slice.call(document.querySelectorAll('.lu-day')),bs=[].slice.call(document.querySelectorAll('[data-day-btn]')),day='';
function n(s){return (s||'').normalize('NFKD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}
function go(){var t=n(q.value.trim()),k=0;as.forEach(function(a){var m=!t||n(a.dataset.n).indexOf(t)>-1;a.classList.toggle('hide',!m)});
ds.forEach(function(d){d.classList.toggle('off',!!day&&d.dataset.day!==day)});
rs.forEach(function(r){var m=(!t||n(r.dataset.n).indexOf(t)>-1)&&(!day||r.dataset.day===day);r.classList.toggle('hide',!m);if(m)k++});if(c)c.textContent=(t||day)?(k+' match'+(k==1?'':'es')):(rs.length+' '+(c.dataset.unit||'acts'));}
bs.forEach(function(b){b.addEventListener('click',function(){day=b.dataset.dayBtn;bs.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});go()})});
q.addEventListener('input',go);q.addEventListener('keydown',function(ev){if(ev.key==='Enter'){var v=as.filter(function(a){return !a.classList.contains('hide')});if(v.length===1)location.href=v[0].href}});go();})();"""


# ------------------------------------------------------------ helpers

def _d(s):
    return datetime.date.fromisoformat(s)


def nice(s):
    d = _d(s)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def two_dates(ds):
    a, b = (_d(x) for x in ds)
    return f"{a.strftime('%B')} {a.day} and {b.day}, {a.year}" if a.month == b.month else f"{a.strftime('%B')} {a.day} and {b.strftime('%B')} {b.day}, {a.year}"


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((dj set|live|b2b[^)]*|w1|w2|weekend [12][^)]*)\)", "", s)
    s = re.sub(r"^the\s+", "", s.strip())
    s = s.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).strip("-") or "x"


def split_pair(name):
    parts = re.split(r"\s+(?:x|b2b|B2B|X|vs\.?)\s+", name)
    return parts if len(parts) > 1 else []


def acts(L):
    out = []
    for d in L["days"]:
        nl = max(a["line"] for a in d["acts"])
        for a in d["acts"]:
            out.append(dict(a, day=d["day"], dates=d["dates"], lines_in_day=nl))
    for s in L.get("special_billings", []):
        out.append(dict(s, day=None, dates=None, line=None, position=None, lines_in_day=None, special=True))
    return out


# ------------------------------------------------------------ archive

def load_archive(root):
    out = {}
    for p in sorted((pathlib.Path(root) / "data/history").glob("*.json")):
        try:
            y = json.loads(p.read_text())
        except Exception:
            continue
        out[int(y["year"])] = y
    return out


def appearances(A):
    """normalized name -> list of {year, day, stage, as} for festivals that happened."""
    idx = {}
    for y, Y in sorted(A.items()):
        if Y.get("status") != "happened":
            continue
        for d in Y.get("days", []):
            for st in d.get("stages", []):
                for act in st.get("acts", []):
                    rec = {"year": y, "day": d["day"], "stage": st["stage"], "as": act}
                    keys = {norm(act)} | {norm(p) for p in split_pair(act)}
                    for k in keys:
                        if k:
                            lst = idx.setdefault(k, [])
                            if not any(r["year"] == y for r in lst):
                                lst.append(rec)
    return idx


def history_for(L, A):
    if not A:
        return None
    idx = appearances(A)
    yrs = sorted(y for y, Y in A.items() if Y.get("status") == "happened")
    H = {"range": f"{yrs[0]}-{yrs[-1]}, every edition that happened", "years_checked": yrs,
         "method": ("Each act's name was matched against every earlier Coachella lineup on Wikipedia's \"Coachella Festival line-ups\" page, transcribed by day and stage into this site's archive. "
                    "Matching is exact after ignoring case, accents, a leading \"the\" and punctuation, so a renamed act or a one-off alias will not match, and a different act with the same name would. "
                    "Pairings billed with \"x\" are checked member by member. Wikipedia's lists can miss late additions and small stages, so a \"debut\" here means no earlier appearance in that archive."),
         "source": {"name": "Wikipedia - Coachella Festival line-ups", "url": WIKI}, "acts": {}}
    for a in acts(L):
        hits = {}
        for k in [norm(a["name"])] + [norm(m) for m in a.get("members", [])]:
            for r in idx.get(k, []):
                hits.setdefault(r["year"], r)
        H["acts"][a["slug"]] = {"name": a["name"], "years": sorted(hits), "sets": [hits[y] for y in sorted(hits)]}
    return H


def hist_line(a, H):
    if not H:
        return None
    h = H["acts"].get(a["slug"])
    if h is None:
        return None
    if h["years"]:
        return "Played Coachella before: " + "; ".join(f"{s['year']} ({s['day']}, {s['stage']}" + (f", as {s['as']}" if norm(s['as']) != norm(a['name']) else "") + ")" for s in h["sets"]) + "."
    return f"No earlier Coachella appearance in the archive ({H['range']}). Likely a debut."


# ------------------------------------------------------------ JSON-LD

def loc():
    return {"@type": "Place", "name": "Empire Polo Club", "address": {"@type": "PostalAddress", "streetAddress": "81800 Avenue 51",
            "addressLocality": "Indio", "addressRegion": "CA", "postalCode": "92201", "addressCountry": "US"}}


def crumbs_ld(site, items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": site + p} for i, (n, p) in enumerate(items, 1)]}


def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}


def faq_html(qas):
    return '<h2>Questions</h2><dl class="faq">' + "".join(f"<dt>{e(q)}</dt><dd>{e(a)}</dd>" for q, a in qas) + "</dl>"


def fest_ld(L, site, path, days=None):
    days = days or L["days"]
    subs = []
    for d in days:
        perf = [{"@type": "PerformingGroup", "name": a["name"], "url": f"{site}/lineup/{L['year']}/a/{a['slug']}/"} for a in d["acts"]]
        for i, dt in enumerate(d["dates"], 1):
            subs.append({"@type": "MusicEvent", "name": f"Coachella {L['year']}: {d['day']}, weekend {i}", "startDate": dt, "endDate": dt,
                         "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                         "location": loc(), "organizer": {"@type": "Organization", "name": "Goldenvoice"}, "performer": perf,
                         "url": f"{site}/lineup/{L['year']}/{d['day'].lower()}/"})
    return {"@context": "https://schema.org", "@type": "Festival", "name": f"Coachella Valley Music and Arts Festival {L['year']}",
            "startDate": L["weekends"][0][0], "endDate": L["weekends"][-1][1], "location": loc(),
            "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "organizer": {"@type": "Organization", "name": "Goldenvoice"}, "subEvent": subs, "url": site + path,
            "description": f"Lineup as announced {L['announced']}. Page by an independent guide, not affiliated with Coachella, Goldenvoice or AEG."}


def dataset_ld(L, site, path):
    y = L["year"]
    return {"@context": "https://schema.org", "@type": "Dataset", "name": f"Coachella {y} lineup, structured",
            "description": f"Every act on the official Coachella {y} lineup poster, by day, poster line and position, spelled as printed, with each act's earlier Coachella appearances. Independent; not affiliated with Coachella, Goldenvoice or AEG.",
            "url": site + path, "dateModified": L["updated"], "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
            "distribution": [{"@type": "DataDownload", "encodingFormat": f, "contentUrl": f"{site}/{fn}"}
                             for fn, f in ((f"lineup-{y}.json", "application/json"), (f"lineup-{y}.csv", "text/csv"), (f"lineup-{y}.txt", "text/plain"), (f"lineup-{y}-history.json", "application/json"))]}


# ------------------------------------------------------------ page parts

def poster_html(L, days, H=None, multi=True):
    y = L["year"]
    out = ""
    for d in days:
        lines = {}
        for a in d["acts"]:
            lines.setdefault(a["line"], []).append(a)
        body = ""
        for ln in sorted(lines):
            items = ""
            for a in lines[ln]:
                nt = f'<span class="nt">{e(a["note"])}</span>' if a.get("note") else ""
                rb = ""
                if H and H["acts"].get(a["slug"], {}).get("years"):
                    k = len(H["acts"][a["slug"]]["years"])
                    rb = f'<span class="rb" title="Played Coachella {k} time{"s" if k > 1 else ""} before">{k}x</span>'
                items += f'<a class="a" id="a-{e(a["slug"])}" href="/lineup/{y}/a/{e(a["slug"])}/" data-n="{e(a["name"])}">{nt}{e(a["name"])}{rb}</a>'
            body += f'<p class="lu-line l{min(ln, 8)}">{items}</p>'
        out += (f'<section class="lu-day" data-day="{d["day"]}" aria-label="{e(d["day"])}">'
                f'<a class="dh" href="/lineup/{y}/{d["day"].lower()}/">{e(d["day"])} · {e(two_dates(d["dates"]).rsplit(",", 1)[0])}</a>{body}</section>')
    return f'<div class="lu-poster{" multi" if multi else ""}">{out}' + "{SPECIAL}</div>"


def special_html(L, H=None):
    y = L["year"]
    s = ""
    for x in L.get("special_billings", []):
        cls = "sp" if x.get("headliner") else "sm"
        s += (f'<p class="{cls}"><a class="a" href="/lineup/{y}/a/{e(x["slug"])}/" data-n="{e(x["name"])}">{e(x["name"])}</a></p>'
              f'<p class="k">{e(x["billing"])} · day not announced</p>')
    return f'<div class="lu-special">{s}</div>'


def table_html(L, H=None):
    y = L["year"]
    trs = ""
    for a in acts(L):
        h = ""
        if H:
            hh = H["acts"].get(a["slug"])
            h = (", ".join(str(v) for v in hh["years"]) if hh and hh["years"] else "debut*")
        note = a.get("billing") if a.get("special") else a.get("note", "")
        mem = (" (" + " + ".join(a["members"]) + ")") if a.get("members") else ""
        trs += (f'<tr data-n="{e(a["name"])} {e(note or "")}" data-day="{a["day"] or ""}"><td><a href="/lineup/{y}/a/{e(a["slug"])}/">{e(a["name"])}</a></td>'
                f'<td>{e(a["day"] or "TBA")}</td><td class="n">{e(a["line"] or "")}</td>'
                + (f'<td class="n">{e(h)}</td>' if H else "") + f'<td>{e(note or "")}{e(mem)}</td></tr>')
    hh = '<th>At Coachella before</th>' if H else ""
    return f'<div class="tbl"><table><thead><tr><th>Act</th><th>Day</th><th>Line</th>{hh}<th>Note</th></tr></thead><tbody id="lu-rows">{trs}</tbody></table></div>'


def az_html(L):
    y = L["year"]
    first = {}
    for a in sorted(acts(L), key=lambda a: norm(a["name"])):
        k = norm(a["name"])[:1].upper()
        k = k if k.isalpha() else "#"
        first.setdefault(k, a["slug"])
    keys = ["#"] + [chr(c) for c in range(65, 91)]
    return '<nav class="az" aria-label="Acts A to Z">' + "".join(
        f'<a href="/lineup/{y}/a/{first[k]}/" title="First act under {k}">{k}</a>' if k in first else f"<span>{k}</span>" for k in keys) + "</nav>"


def tools_html(L, show_days=True):
    y = L["year"]
    chips = ""
    if show_days:
        chips = '<div class="chips" role="group" aria-label="Show a day" style="margin:0"><button type="button" data-day-btn="" aria-pressed="true">All</button>' + "".join(
            f'<button type="button" data-day-btn="{d}" aria-pressed="false">{d[:3]}</button>' for d in DAYS) + "</div>"
    return (f'<div class="tools"><label for="lu-q" class="sr">Find an act</label><input id="lu-q" type="search" placeholder="Find an act" autocomplete="off">'
            f'{chips}<span class="cnt" id="lu-cnt"></span><span>Data: <a href="/lineup-{y}.json">JSON</a> · <a href="/lineup-{y}.csv">CSV</a> · '
            f'<a href="/lineup-{y}.txt">text</a> · <a href="/coachella-{y}.ics">calendar</a></span></div>')


def src_html(L):
    return '<ol class="src">' + "".join(
        f'<li>{e(s["publication"])} - "{e(s["title"])}" - {e(s["date"])}' + (f' - <a href="{e(s["url"])}" rel="noopener" target="_blank">link</a>' if s.get("url") else " (the poster itself, not hosted here)") + "</li>"
        for s in L["sources"]) + "</ol>"


def angles(L, H, A):
    """The 2027-specific stories worth a callout, each built only from sourced data in this repo."""
    out = []
    if not H:
        return out
    mad = H["acts"].get("madonna", {})
    if mad.get("years"):
        s = mad["sets"][0]
        out.append(("Madonna, back in the dance tent",
                    f"The poster prints \"In the Dance Tent\" over Madonna's name, the only stage named for any act on the 2027 sheet. Her first Coachella set was in {s['year']}, in the {s['stage']}, Coachella's dance tent, on a {s['day']}. "
                    "When she joined Sabrina Carpenter on weekend two in 2026, she told the crowd it had been \"20 years ago today\" that she played the dance tent and called it \"a full circle moment\" (Billboard). "
                    "Now the tent is the billing. The moments chapter has the 2026 night."))
    ju = H["acts"].get("justice", {})
    out.append(("The Bunker, round two",
                "In 2026 the last line of the poster read \"The Bunker Debut of Radiohead Kid A Mnesia.\" It was not a set: it was an underground cinema under the polo fields, open to anyone with a wristband (FLOOD, Stereogum). "
                "The 2027 poster ends the same way, with \"The Bunker Debut Of JUSTICE - Blinded By The Lights\" and no day. If it works like 2026, it is a piece you visit, not a one-night show. That is a reading of last year, not an announcement."
                + (f" Justice have played Coachella {len(ju['years'])} times before ({', '.join(str(x) for x in ju['years'])})." if ju.get("years") else "")))
    climb = []
    for a in acts(L):
        if not a.get("headliner"):
            continue
        hh = H["acts"].get(a["slug"], {})
        if hh.get("sets"):
            climb.append(f"{a['name']}: " + ", then ".join(f"{s['stage']} in {s['year']}" for s in hh["sets"]) + ", now " + (f"headlining {a['day']}" if a.get("day") else f"\"{a.get('billing')}\""))
        else:
            climb.append(f"{a['name']}: no earlier Coachella set in the archive")
    out.append(("How the headliners got here", ". ".join(climb) + "."))
    by_day = {}
    for d in L["days"]:
        r = [a for a in d["acts"] if H["acts"].get(a["slug"], {}).get("years")]
        by_day[d["day"]] = (len(r), len(d["acts"]))
    best = max(by_day, key=lambda k: by_day[k][0] / by_day[k][1])
    out.append(("Which day is the reunion day",
                "Share of each day's acts that have played Coachella before: " + ", ".join(f"{k} {v[0]} of {v[1]} ({round(100 * v[0] / v[1])}%)" for k, v in by_day.items())
                + f". {best} leans most on returning acts."))
    return out


def main_faq(L, H):
    y = L["year"]
    q = [
        (f"When is Coachella {y}?", f"Two weekends: April 9-11 and April 16-18, {y}, at the Empire Polo Club in Indio, California."),
        (f"Who is headlining Coachella {y}?", "Dua Lipa headlines Friday, Tame Impala Saturday and SZA Sunday. Daddy Yankee is billed \"In the Desert\" with no day; Yahoo called him a fourth headliner in a \"special production.\""),
        (f"Is the Coachella {y} lineup the same both weekends?", "As printed, yes: each day block on the poster carries both dates (Friday April 9 & 16, Saturday April 10 & 17, Sunday April 11 & 18). Changes between weekends usually only show once the festival is on."),
        (f"When do Coachella {y} tickets go on sale?", "General passes go on sale Friday, Nov. 13, 2026, at noon PT, per GV Wire. Yahoo reported an American Express presale the day before. The sources gathered here did not list prices."),
        (f"What day is Madonna playing Coachella {y}?", "Friday, both weekends (April 9 and 16), on the second line with \"In the Dance Tent\" printed over her name."),
        ("What is the Bunker at Coachella?", "An underground room built under the polo fields for Radiohead's KID A MNESIA cinema in 2026. The 2027 poster ends with \"The Bunker Debut Of JUSTICE - Blinded By The Lights\"; what that is had not been announced as of Nov. 11, 2026."),
        (f"Are Coachella {y} set times out?", f"Not as of {nice(L['updated'])}. Set times and stages usually come out shortly before the festival; this page will add them when they do."),
    ]
    if H:
        th = H["acts"].get("tame-impala", {})
        if th.get("years"):
            q.append(("Has Tame Impala played Coachella before?", f"Yes, in {', '.join(str(x) for x in th['years'])}, including a 2019 headline set alongside Childish Gambino and Ariana Grande."))
        ret = sum(1 for v in H["acts"].values() if v["years"])
        q.append((f"How many Coachella {y} acts have played Coachella before?", f"{ret} of {len(H['acts'])}, matched against every earlier lineup in the archive ({H['range']}). The rest have no earlier appearance there."))
    return q


# ------------------------------------------------------------ pages

def page_main(L, site, H=None, A=None):
    y = L["year"]
    n_acts = len(acts(L))
    qas = main_faq(L, H)
    ret = sum(1 for v in (H or {}).get("acts", {}).values() if v["years"]) if H else None
    callouts = "".join(f'<div class="callout"><h3>{e(t)}</h3><p>{e(b)}</p></div>' for t, b in angles(L, H, A))
    body = f"""<main class="lu" id="main">
<p class="readmeta">Lineup · announced {e(nice(L['announced']))} · updated {e(nice(L['updated']))}</p>
<h1 class="ch">Coachella {y}: the full lineup</h1>
<p class="lede">Every act on the official {y} poster, re-set line by line in this guide's own type, spelled exactly as printed. Tap any name for its day, both dates, billing, every earlier Coachella set and where to find them. The same lineup plays both weekends, April 9-11 and April 16-18, {y}, at the Empire Polo Club in Indio. Poster order is billing, not set order; stages and set times come later.</p>
<div class="facts"><div><b>{n_acts}</b><span>acts on the poster</span></div><div><b>3 + 1</b><span>day headliners Dua Lipa, Tame Impala, SZA, plus Daddy Yankee "In the Desert"</span></div>{f'<div><b>{ret}</b><span>have played Coachella before</span></div>' if H else ''}<div><b>Nov. 13</b><span>passes on sale, noon PT</span></div></div>
<nav class="chips" aria-label="More"><a href="/lineup/{y}/friday/">Friday</a><a href="/lineup/{y}/saturday/">Saturday</a><a href="/lineup/{y}/sunday/">Sunday</a>{f'<a href="/lineup/{y}/history/">Returning and debuts</a>' if H else ''}<a href="/archive/">Every past lineup</a><a href="/headliners/">Every headliner</a></nav>
{tools_html(L)}
{az_html(L)}
{poster_html(L, L['days'], H).replace('{SPECIAL}', special_html(L, H))}
{('<p class="note">Small green numbers: how many earlier Coachellas that act has played. <a href="/lineup/' + str(y) + '/history/">Full history</a>.</p>') if H else ''}
<h2>What's new on this poster</h2>
{callouts}
<h2>How to read the poster</h2>
<p>Each day is a block. The first line is that day's headliner; every line after it is set smaller, and the size is billing, not fee and not set time. Within a line, names run left to right in the order printed. Daddy Yankee sits on his own line under Sunday with "In the Desert" and no day. For what billing size means and who fights over it, see <a href="/lineup/">the lineup chapter</a>.</p>
<h2>Every act</h2>
<p class="note">Line 1 is the headliner row; higher numbers are smaller type. Names joining two acts with "x" are one billing; both members are noted.{' "debut*" means no earlier appearance in the archive; see the history page for what that covers.' if H else ''}</p>
{table_html(L, H)}
<h2>Tickets and stream</h2>
<p>General passes go on sale Friday, Nov. 13, 2026, at noon PT, per <a href="https://gvwire.com/2026/11/10/dua-lipa-tame-impala-and-sza-to-headline-coachella-2027/" rel="noopener" target="_blank">GV Wire</a>; Yahoo reported an American Express presale the day before, at noon PT. None of the sources gathered here listed prices. YouTube is the livestream partner for a 15th year, per GV Wire. Daddy Yankee's "fourth headliner" and "special production" wording is <a href="https://www.yahoo.com/entertainment/music/festivals/articles/coachella-2027-sets-dua-lipa-064237129.html" rel="noopener" target="_blank">Yahoo's</a>. Madonna's 2026 quote is from <a href="https://ca.billboard.com/music/concerts/madonna-sabrina-carpenter-coachella-2026-1236226082/" rel="noopener" target="_blank">Billboard</a>; the 2026 Bunker from <a href="https://floodmagazine.com/220098/radiohead-kid-a-mnesia-motion-picture-house-coachella" rel="noopener" target="_blank">FLOOD</a>. Add both weekends to your calendar with <a href="/coachella-{y}.ics">this .ics file</a>.</p>
{faq_html(qas)}
<h2>Sources</h2>
{src_html(L)}
{f'<p class="note">Earlier appearances: <a href="{WIKI}" rel="noopener" target="_blank">Wikipedia, Coachella Festival line-ups</a>, transcribed by day and stage in <a href="/archive/">the archive</a>.</p>' if H else ''}
<p class="note">Independent transcription. Not affiliated with Coachella, Goldenvoice or AEG. Spot a misspelling or a change? <a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20lineup%20{y}">Tell us</a> and it will be logged on <a href="/corrections/">corrections</a>.</p>
</main>"""
    ld = [fest_ld(L, site, f"/lineup/{y}/"), dataset_ld(L, site, f"/lineup/{y}/"), faq_ld(qas),
          crumbs_ld(site, [("Polo", "/"), ("The lineup", "/lineup/"), (f"{y}", f"/lineup/{y}/")])]
    return body, ld


def page_day(L, site, d, H=None):
    y = L["year"]
    head = [a["name"] for a in d["acts"] if a["line"] == 1]
    qas = [(f"Who is playing Coachella {y} on {d['day']}?", f"{', '.join(head)} headlines, with {len(d['acts']) - len(head)} more acts on the {d['day']} poster: " + ", ".join(a['name'] for a in d['acts'] if a['line'] == 2) + " on the second line, and the rest below."),
           (f"When is {d['day']} at Coachella {y}?", f"{d['day']} runs on both weekends: {two_dates(d['dates'])}. Set times and stages had not been published as of {nice(L['updated'])}.")]
    if H:
        r = [a for a in d["acts"] if H["acts"].get(a["slug"], {}).get("years")]
        qas.append((f"Which {d['day']} acts have played Coachella before?", f"{len(r)} of {len(d['acts'])}: " + ", ".join(a["name"] for a in r) + "."))
    others = " · ".join(f'<a href="/lineup/{y}/{x["day"].lower()}/">{x["day"]}</a>' for x in L["days"] if x is not d)
    body = f"""<main class="lu" id="main">
<p class="bc"><a href="/lineup/{y}/">Coachella {y} lineup</a> / {d['day']}</p>
<h1 class="ch">Coachella {y}: {d['day']} lineup</h1>
<p class="lede">{e(head[0])} headlines {d['day']}, {two_dates(d['dates'])}. {len(d['acts'])} acts, line by line as printed. Tap a name for its page. Other days: {others}.</p>
{tools_html(L, show_days=False)}
{poster_html(L, [d], H, multi=False).replace('{SPECIAL}', '')}
{table_html({**L, 'days': [d], 'special_billings': []}, H)}
{faq_html(qas)}
<p class="note">Independent. Not affiliated with Coachella, Goldenvoice or AEG. <a href="/lineup/{y}/">The full lineup and sources</a>.</p>
</main>"""
    ld = [fest_ld(L, site, f"/lineup/{y}/{d['day'].lower()}/", [d]), faq_ld(qas),
          crumbs_ld(site, [("Polo", "/"), ("The lineup", "/lineup/"), (f"{y}", f"/lineup/{y}/"), (d["day"], f"/lineup/{y}/{d['day'].lower()}/")])]
    return body, ld


def page_act(L, site, a, prev_a, next_a, H=None):
    y = L["year"]
    name = a["name"]
    find = lambda q: "".join(f'<a href="{u.format(q=urllib.parse.quote(q))}" rel="noopener nofollow" target="_blank">{lab}</a>' for lab, u in SEARCH)
    findh = ("".join(f'<p class="note">{e(m)}</p><div class="find">{find(m)}</div>' for m in a["members"]) if a.get("members")
             else f'<div class="find">{find(name)}</div>')
    hl = hist_line(a, H)
    if a.get("special"):
        when = "Day not announced"
        billing = f'"{a["billing"]}", printed on its own line, outside the day blocks'
        same = ""
        q_day = (f"What day is {name} playing Coachella {y}?", f"Not announced as of {nice(L['updated'])}. The poster bills {name} as \"{a['billing']}\" with no day. {a.get('note', '')}")
        ev = []
    else:
        d = next(x for x in L["days"] if x["day"] == a["day"])
        when = f"{a['day']} · {two_dates(a['dates'])}"
        billing = ("Headliner, top line of " if a["line"] == 1 else f"Line {a['line']} of {a['lines_in_day']} on ") + f"{a['day']}'s poster" + (f', printed with "{a["note"]}"' if a.get("note") else "")
        mates = [x for x in d["acts"] if x["line"] == a["line"] and x["slug"] != a["slug"]]
        same = ("<h2>On the same line</h2><p>" + " · ".join(f'<a href="/lineup/{y}/a/{x["slug"]}/">{e(x["name"])}</a>' for x in mates) + "</p>") if mates else ""
        q_day = (f"What day is {name} playing Coachella {y}?", f"{a['day']}, on both weekends: {two_dates(a['dates'])}." + (f" Billed \"{a['note']}\"." if a.get("note") else ""))
        ev = [{"@context": "https://schema.org", "@type": "MusicEvent", "name": f"{name} at Coachella {y} ({a['day']}, weekend {i})", "startDate": dt, "endDate": dt,
               "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "location": loc(),
               "performer": {"@type": "PerformingGroup", "name": name}, "organizer": {"@type": "Organization", "name": "Goldenvoice"},
               "superEvent": {"@type": "Festival", "name": f"Coachella Valley Music and Arts Festival {y}", "url": f"{site}/lineup/{y}/"},
               "url": f"{site}/lineup/{y}/a/{a['slug']}/"} for i, dt in enumerate(a["dates"], 1)]
    qas = [q_day,
           (f"Is {name} playing both weekends of Coachella {y}?", "As printed on the poster, yes: every day block carries both weekend dates." if not a.get("special") else "The poster gives no day or weekend for this billing."),
           (f"What time does {name} play at Coachella {y}?", f"Set times and stages had not been published as of {nice(L['updated'])}.")]
    if hl:
        qas.append((f"Has {name} played Coachella before?", hl))
    past = ""
    if H and H["acts"].get(a["slug"], {}).get("sets"):
        past = "<h2>Every earlier Coachella set</h2><div class=\"tbl\"><table><thead><tr><th>Year</th><th>Day</th><th>Stage</th><th>Billed as</th></tr></thead><tbody>" + "".join(
            f'<tr><td class="n"><a href="/archive/{s["year"]}/">{s["year"]}</a></td><td>{e(s["day"])}</td><td>{e(s["stage"])}</td><td>{e(s["as"])}</td></tr>' for s in H["acts"][a["slug"]]["sets"]) + "</tbody></table></div>"
    dl = f"<dt>When</dt><dd>{e(when)}</dd><dt>Billing</dt><dd>{e(billing)}</dd><dt>Set time</dt><dd>Not announced yet</dd>"
    if a.get("members"):
        dl += f"<dt>Who</dt><dd>{e(' and '.join(a['members']))}, billed together</dd>"
    if H:
        hh = H["acts"].get(a["slug"], {})
        dl += (f'<dt>Coachella before</dt><dd>{len(hh["years"])} time{"s" if len(hh["years"]) > 1 else ""}: {", ".join(str(x) for x in hh["years"])}</dd>' if hh.get("years")
               else f'<dt>Coachella before</dt><dd>None in the archive. Likely a debut. <a href="/lineup/{y}/history/">How this was checked</a></dd>')
    pn = '<nav class="pn">' + (f'<a href="/lineup/{y}/a/{prev_a["slug"]}/">← {e(prev_a["name"])}</a>' if prev_a else "<span></span>") + \
         (f'<a href="/lineup/{y}/a/{next_a["slug"]}/">{e(next_a["name"])} →</a>' if next_a else "<span></span>") + "</nav>"
    day_crumb = f' / <a href="/lineup/{y}/{a["day"].lower()}/">{a["day"]}</a>' if a.get("day") else ""
    body = f"""<main class="lu" id="main">
<p class="bc"><a href="/lineup/{y}/">Coachella {y} lineup</a>{day_crumb} / {e(name)}</p>
<h1 class="ch">{e(name)} at Coachella {y}</h1>
<div class="answer"><p class="big">{e(when)}</p><dl>{dl}</dl></div>
<p class="lede">The Empire Polo Club in Indio, California. Name spelled as printed on the official poster, released {e(nice(L['announced']))}.</p>
{past}
<h2>Find {e(name)}</h2>
<p class="note">These are searches, not official profiles: each opens that service's search for the name as printed.</p>
{findh}
{same}
{faq_html(qas)}
{pn}
<p class="note">Independent. Not affiliated with Coachella, Goldenvoice or AEG. <a href="/lineup/{y}/">The full {y} lineup and its sources</a>. Something wrong? <a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20{urllib.parse.quote(name)}">Tell us</a>.</p>
</main>"""
    crumbs = [("Polo", "/"), ("The lineup", "/lineup/"), (f"{y}", f"/lineup/{y}/")] + ([(a["day"], f"/lineup/{y}/{a['day'].lower()}/")] if a.get("day") else []) + [(name, f"/lineup/{y}/a/{a['slug']}/")]
    ld = ev + [faq_ld(qas), crumbs_ld(site, crumbs)]
    desc = (f"{name} plays Coachella {y} on {a['day']}, {two_dates(a['dates'])}. Billing, set-time status, every earlier Coachella set and where to find them."
            if not a.get("special") else f"{name} at Coachella {y}: billed \"{a['billing']}\", day not announced.")
    return body, ld, desc


def page_history(L, site, H):
    y = L["year"]
    al = acts(L)
    ret = [(a, H["acts"][a["slug"]]) for a in al if H["acts"][a["slug"]]["years"]]
    deb = [a for a in al if not H["acts"][a["slug"]]["years"]]
    ret.sort(key=lambda t: (-len(t[1]["years"]), norm(t[0]["name"])))
    most = ret[0] if ret else None
    rows_r = "".join(f'<tr><td><a href="/lineup/{y}/a/{a["slug"]}/">{e(a["name"])}</a></td><td>{e(a["day"] or "TBA")}</td><td class="n">{len(h["years"])}</td>'
                     f'<td>{", ".join(f"<a href=\"/archive/{s["year"]}/\">{s["year"]}</a> <span class=\"note\">{e(s["stage"])}</span>" for s in h["sets"])}</td></tr>' for a, h in ret)
    deb_html = " · ".join(f'<a href="/lineup/{y}/a/{a["slug"]}/">{e(a["name"])}</a>' for a in sorted(deb, key=lambda a: norm(a["name"])))
    hl = [a for a in al if a.get("headliner")]
    hl_html = "".join(f'<li><a href="/lineup/{y}/a/{a["slug"]}/">{e(a["name"])}</a>: ' + (", ".join(f'{s["year"]} ({e(s["stage"])})' for s in H["acts"][a["slug"]]["sets"]) or "no earlier Coachella set in the archive") + "</li>" for a in hl)
    qas = [(f"Which Coachella {y} acts have played Coachella before?", f"{len(ret)} of the {len(al)} acts on the {y} poster appear on at least one earlier Coachella lineup" + (f"; {most[0]['name']} has the most earlier appearances, {len(most[1]['years'])} ({', '.join(str(v) for v in most[1]['years'])})." if most else ".")),
           (f"How many Coachella {y} acts are making their Coachella debut?", f"{len(deb)} acts have no earlier appearance in the archive ({H['range']}). Archives miss small stages and late adds, so treat a debut as likely, not certain."),
           (f"Have the Coachella {y} headliners played Coachella before?", " ".join(f"{a['name']}: " + (", ".join(str(x) for x in H['acts'][a['slug']]['years']) if H['acts'][a['slug']]['years'] else "no earlier set in the archive") + "." for a in hl))]
    body = f"""<main class="lu" id="main">
<p class="bc"><a href="/lineup/{y}/">Coachella {y} lineup</a> / Returning and debuts</p>
<h1 class="ch">Coachella {y}: who has played before, and who is new</h1>
<p class="lede">Every act on the {y} poster checked against every earlier Coachella lineup, {e(H['range'])}, with the year and stage of each set. {len(ret)} have played before; {len(deb)} have no earlier appearance in the archive.</p>
<div class="facts"><div><b>{len(ret)}</b><span>returning acts</span></div><div><b>{len(deb)}</b><span>likely debuts</span></div>{f'<div><b>{len(most[1]["years"])}x</b><span>most returns: {e(most[0]["name"])}</span></div>' if most else ''}</div>
<h2>The headliners</h2><ul>{hl_html}</ul>
<h2>Returning, most appearances first</h2>
<div class="tbl"><table><thead><tr><th>Act</th><th>{y} day</th><th>Times</th><th>Earlier sets</th></tr></thead><tbody>{rows_r}</tbody></table></div>
<h2>Likely debuts</h2>
<p>{deb_html}</p>
<h2>How this was checked</h2>
<p>{e(H['method'])}</p>
<p class="note">Source: <a href="{WIKI}" rel="noopener" target="_blank">Wikipedia, "Coachella Festival line-ups"</a>, transcribed by day and stage in <a href="/archive/">the archive</a>. Data: <a href="/lineup-{y}-history.json">lineup-{y}-history.json</a>.</p>
{faq_html(qas)}
<p class="note">Independent. Not affiliated with Coachella, Goldenvoice or AEG. Know an appearance we missed? <a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20history%20{y}">Tell us</a>.</p>
</main>"""
    ld = [faq_ld(qas), crumbs_ld(site, [("Polo", "/"), ("The lineup", "/lineup/"), (f"{y}", f"/lineup/{y}/"), ("Returning and debuts", f"/lineup/{y}/history/")])]
    return body, ld


def page_archive_year(Y, A, site, current_slugs):
    y = Y["year"]
    yrs = sorted(A)
    nav = '<nav class="yrs" aria-label="Years">' + "".join(f'<a href="/archive/{x}/"' + (' class="on" aria-current="page"' if x == y else "") + f">{x}</a>" for x in yrs) + "</nav>"
    total = sum(len(st["acts"]) for d in Y.get("days", []) for st in d.get("stages", []))
    body = ""
    for d in Y.get("days", []):
        body += f"<h2>{e(d['day'])}</h2>"
        for st in d.get("stages", []):
            items = " · ".join((f'<a href="/lineup/2027/a/{current_slugs[norm(x)]}/" title="On the 2027 lineup">{e(x)}</a>' if norm(x) in current_slugs else e(x)) for x in st["acts"])
            body += f'<div class="stage"><h3>{e(st["stage"])} · {len(st["acts"])}</h3><p>{items}</p></div>'
    status = {"happened": "", "canceled": " This lineup was announced and then canceled; the festival did not happen.", "no festival": " There was no festival this year."}.get(Y.get("status"), "")
    notes = "".join(f"<li>{e(n)}</li>" for n in Y.get("notes", []))
    html_ = f"""<main class="lu" id="main">
<p class="bc"><a href="/archive/">Every Coachella lineup</a> / {y}</p>
<h1 class="ch">Coachella {y} lineup, by day and stage</h1>
<p class="lede">{total} acts as listed by day and stage.{status} Names linked in the text are also on the 2027 poster.</p>
{nav}
{body or '<p>No lineup.</p>'}
{('<h2>Notes</h2><ul>' + notes + '</ul>') if notes else ''}
<p class="note">Source: <a href="{e(Y['source']['url'])}" rel="noopener" target="_blank">{e(Y['source']['name'])}</a>, retrieved {e(Y['source'].get('retrieved', ''))}, transcribed here. Independent. Not affiliated with Coachella, Goldenvoice or AEG. Data: <a href="/archive.json">archive.json</a>. Something wrong? <a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20archive%20{y}">Tell us</a>.</p>
</main>"""
    return html_, total


def page_archive_index(A, idx, site):
    yrs = sorted(A)
    rows_ = ""
    for y in sorted(yrs, reverse=True):
        Y = A[y]
        n = sum(len(st["acts"]) for d in Y.get("days", []) for st in d.get("stages", []))
        stages = sorted({st["stage"] for d in Y.get("days", []) for st in d.get("stages", [])})
        rows_ += f'<tr><td class="n"><a href="/archive/{y}/">{y}</a></td><td>{e(Y.get("status"))}</td><td class="n">{n}</td><td>{e(", ".join(stages))}</td></tr>'
    SIDE = re.compile(r"do lab|heineken|desert sky|bassface|camp|matin|dome|unspecified|dj.?s between", re.I)
    main_idx = {k: [r for r in v if not SIDE.search(r["stage"])] for k, v in idx.items()}
    top = sorted(((v[0]["as"], v) for k, v in main_idx.items() if v), key=lambda t: (-len(t[1]), t[0].lower()))[:30]
    top_all = sorted(((v[0]["as"], v) for k, v in idx.items()), key=lambda t: (-len(t[1]), t[0].lower()))[:15]
    toph = "".join(f'<li><b>{e(n)}</b> <span>{len(v)} · {", ".join(str(r["year"]) for r in v)}</span></li>' for n, v in top)
    toph_all = "".join(f'<li><b>{e(n)}</b> <span>{len(v)} · {", ".join(str(r["year"]) for r in v)}</span></li>' for n, v in top_all)
    stage_count = {}
    for y, Y in A.items():
        for d in Y.get("days", []):
            for st in d.get("stages", []):
                base = re.sub(r"\s*\(weekend [12]\)|\s+tent$", "", st["stage"], flags=re.I).strip()
                stage_count.setdefault(base, set()).add(y)
    sth = "".join(f"<li><b>{e(s)}</b> <span>{min(v)}-{max(v)} · {len(v)} editions</span></li>" for s, v in sorted(stage_count.items(), key=lambda t: (-len(t[1]), t[0])) if s != "Unspecified")
    body = f"""<main class="lu" id="main">
<h1 class="ch">Every Coachella lineup, 1999 to now</h1>
<p class="lede">Every edition's lineup by day and stage, every act ever listed, who has played the most, and every stage name the festival has used. Transcribed from Wikipedia's "Coachella Festival line-ups" and linked to the 2027 poster.</p>
<nav class="chips" aria-label="More"><a href="/lineup/2027/">The 2027 lineup</a><a href="/archive/artists/">Every act, A-Z</a><a href="/headliners/">Every headliner</a></nav>
<div class="tbl"><table><thead><tr><th>Year</th><th>Status</th><th>Acts</th><th>Stages</th></tr></thead><tbody>{rows_}</tbody></table></div>
<h2>Most appearances on the main lineup</h2><p class="note">Every stage except the sponsor and partner stages (the Do LaB, Heineken House and Dome, Desert Sky, the camping stages).</p><ol class="ix">{toph}</ol>
<h2>Most appearances, every stage</h2><p class="note">The Do LaB and Heineken House residents play almost every year, so they lead here.</p><ol class="ix">{toph_all}</ol>
<h2>Every stage name</h2><ul class="ix">{sth}</ul>
<p class="note">Counts are per edition (an act playing both weekends counts once) and use exact name matches, so renamed acts count separately. Source: <a href="{WIKI}" rel="noopener" target="_blank">Wikipedia, "Coachella Festival line-ups"</a>. Data: <a href="/archive.json">archive.json</a>. Independent. Not affiliated with Coachella, Goldenvoice or AEG.</p>
</main>"""
    qas = [("Who has played Coachella the most?", "On the main lineup: " + "; ".join(f"{n}, {len(v)} times" for n, v in top[:5]) + ". Counting every edition in Wikipedia's lineup lists with exact name matches, and leaving out the Do LaB and other partner stages, whose residents play nearly every year."),
           ("How many stages does Coachella have?", "It changes by year; this page lists every stage name in the archive with the years it appears.")]
    return body + "", qas, top


def page_artists(A, idx, site, current_slugs):
    items = []
    for k, v in idx.items():
        name = v[0]["as"]
        items.append((norm(name), name, v, k))
    items.sort(key=lambda t: (t[0], t[1]))
    lis = "".join(f'<li data-n="{e(n)}"><b>' + (f'<a href="/lineup/2027/a/{current_slugs[k]}/">{e(n)}</a>' if k in current_slugs else e(n)) + f'</b> <span>{", ".join(f"<a href=\"/archive/{r["year"]}/\">{r["year"]}</a>" for r in v)}</span></li>' for _, n, v, k in items)
    body = f"""<main class="lu" id="main">
<p class="bc"><a href="/archive/">Every Coachella lineup</a> / Every act</p>
<h1 class="ch">Every act that has played Coachella</h1>
<p class="lede">{len(items):,} acts, A to Z, with every year they played. Bold links are on the 2027 poster.</p>
<div class="tools"><label for="lu-q" class="sr">Find an act</label><input id="lu-q" type="search" placeholder="Find an act" autocomplete="off"><span class="cnt" id="lu-cnt" data-unit="acts"></span></div>
<ul class="ix" id="lu-rows">{lis}</ul>
<p class="note">Exact name matches only: an act that changed its name appears twice. Source: <a href="{WIKI}" rel="noopener" target="_blank">Wikipedia, "Coachella Festival line-ups"</a>. Independent. Not affiliated with Coachella, Goldenvoice or AEG.</p>
</main>"""
    return body, len(items)


# ------------------------------------------------------------ files

def rows(L, H=None):
    for a in acts(L):
        hh = (H or {}).get("acts", {}).get(a["slug"], {})
        yield {"name": a["name"], "slug": a["slug"], "day": a["day"] or "", "weekend1": (a["dates"] or ["", ""])[0], "weekend2": (a["dates"] or ["", ""])[1],
               "line": a["line"] or "", "position": a["position"] or "", "headliner": a.get("headliner", False),
               "note": a.get("note", "") if not a.get("special") else a.get("billing", ""), "members": " + ".join(a.get("members", [])),
               "coachella_before": " ".join(str(x) for x in hh.get("years", [])), "url": f"https://polo.cold.fyi/lineup/{L['year']}/a/{a['slug']}/"}


def ics(L):
    y = L["year"]
    stamp = L["updated"].replace("-", "") + "T000000Z"
    ev = []
    for i, (a, b) in enumerate(L["weekends"], 1):
        end = (_d(b) + datetime.timedelta(days=1)).strftime("%Y%m%d")
        ev += ["BEGIN:VEVENT", f"UID:coachella-{y}-w{i}@polo.cold.fyi", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{_d(a).strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{end}",
               f"SUMMARY:Coachella {y} - weekend {i}", "LOCATION:Empire Polo Club\\, 81800 Avenue 51\\, Indio\\, CA 92201",
               f"DESCRIPTION:Lineup by day: https://polo.cold.fyi/lineup/{y}/ (independent guide\\, not affiliated with Coachella)", f"URL:https://polo.cold.fyi/lineup/{y}/", "END:VEVENT"]
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//polo.cold.fyi//lineup//EN", "CALSCALE:GREGORIAN", f"X-WR-CALNAME:Coachella {y}"] + ev + ["END:VCALENDAR"]) + "\r\n"


def files(L, H=None):
    y = L["year"]
    out = {f"lineup-{y}.json": json.dumps(L, indent=1, ensure_ascii=False) + "\n", f"coachella-{y}.ics": ics(L)}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["name", "slug", "day", "weekend1", "weekend2", "line", "position", "headliner", "note", "members", "coachella_before", "url"])
    w.writeheader()
    for r in rows(L, H):
        w.writerow(r)
    out[f"lineup-{y}.csv"] = buf.getvalue()
    txt = [f"Coachella {y} lineup - as announced {L['announced']}, transcribed from the official poster by polo.cold.fyi (independent, not affiliated with Coachella).",
           f"Weekends: {L['weekends'][0][0]} to {L['weekends'][0][1]} and {L['weekends'][1][0]} to {L['weekends'][1][1]}, Empire Polo Club, Indio, California. Same lineup both weekends.",
           f"Per-act pages: https://polo.cold.fyi/lineup/{y}/a/<slug>/ (slugs in the JSON and CSV).",
           "Format: day | poster line (1 = headliner) | act as printed | note | earlier Coachella years", ""]
    for r in rows(L, H):
        txt.append(" | ".join([r["day"] or "Day TBA", str(r["line"] or "-"), r["name"], r["note"], r["coachella_before"]]).rstrip(" |"))
    out[f"lineup-{y}.txt"] = "\n".join(txt) + "\n"
    if H:
        out[f"lineup-{y}-history.json"] = json.dumps(H, indent=1, ensure_ascii=False) + "\n"
    return out


def llms_lines(L, site, H=None):
    y = L["year"]
    out = ["", f"## Coachella {y} lineup (announced {L['announced']})",
           f"- Page: {site}/lineup/{y}/ - days: {site}/lineup/{y}/friday/, /saturday/, /sunday/ - one page per act: {site}/lineup/{y}/a/<slug>/",
           f"- Data: {site}/lineup-{y}.json, {site}/lineup-{y}.csv, {site}/lineup-{y}.txt, calendar {site}/coachella-{y}.ics",
           f"- Weekends {L['weekends'][0][0]} to {L['weekends'][0][1]} and {L['weekends'][1][0]} to {L['weekends'][1][1]}; the same lineup plays both. Set times and stages not published as of {L['updated']}."]
    if H:
        out.append(f"- Who has played Coachella before (year, day, stage) and likely debuts: {site}/lineup/{y}/history/ (data {site}/lineup-{y}-history.json)")
    for d in L["days"]:
        h = [a["name"] for a in d["acts"] if a["line"] == 1]
        rest = [a["name"] + (f" ({a['note']})" if a.get("note") else "") for a in d["acts"] if a["line"] != 1]
        out.append(f"- {d['day']} ({', '.join(d['dates'])}): headliner {', '.join(h)}; then {', '.join(rest)}")
    for s in L.get("special_billings", []):
        out.append(f"- {s['name']}: billed \"{s['billing']}\", no day announced. {s.get('note','')}")
    return out


# ------------------------------------------------------------ entry points

def render(L, site, write, shell, root, NAME):
    y = L["year"]
    A = load_archive(root)
    A = {k: v for k, v in A.items() if k < y}
    H = history_for(L, A)
    urls = []
    body, ld = page_main(L, site, H, A)
    write(f"lineup/{y}/index.html", shell(f"Coachella {y} lineup: every act, by day | {NAME}",
          f"The full Coachella {y} lineup by day, transcribed from the official poster: all {len(acts(L))} acts with dates, billing, past Coachella sets and a page for each. JSON, CSV and calendar downloads. Independent.",
          f"/lineup/{y}/", body, crumbs=f'<span class="sep">/</span><a href="/lineup/">Lineup</a><span class="sep">/</span>{y}', extra_ld=ld, extra_css=CSS, extra_js=JS))
    urls.append(f"/lineup/{y}/")
    for d in L["days"]:
        body, ld = page_day(L, site, d, H)
        p = f"/lineup/{y}/{d['day'].lower()}/"
        head = [a["name"] for a in d["acts"] if a["line"] == 1][0]
        write(p.strip("/") + "/index.html", shell(f"Coachella {y} {d['day']} lineup: {head} and every act | {NAME}",
              f"Every act playing Coachella {y} on {d['day']}, {two_dates(d['dates'])}, line by line as printed on the official poster, headlined by {head}.",
              p, body, crumbs=f'<span class="sep">/</span><a href="/lineup/{y}/">{y}</a><span class="sep">/</span>{d["day"]}', extra_ld=ld, extra_css=CSS, extra_js=JS))
        urls.append(p)
    al = acts(L)
    for i, a in enumerate(al):
        body, ld, desc = page_act(L, site, a, al[i - 1] if i else None, al[i + 1] if i + 1 < len(al) else None, H)
        p = f"/lineup/{y}/a/{a['slug']}/"
        write(p.strip("/") + "/index.html", shell(f"{a['name']} at Coachella {y}: day, dates and history | {NAME}", desc, p, body,
              crumbs=f'<span class="sep">/</span><a href="/lineup/{y}/">{y}</a><span class="sep">/</span>{e(a["name"])}', extra_ld=ld, extra_css=CSS))
        urls.append(p)
    if H:
        body, ld = page_history(L, site, H)
        write(f"lineup/{y}/history/index.html", shell(f"Coachella {y}: who has played before, and the debuts | {NAME}",
              f"Every Coachella {y} act checked against every earlier Coachella lineup: who is returning, how many times, on which stages, and who looks like a debut.",
              f"/lineup/{y}/history/", body, crumbs=f'<span class="sep">/</span><a href="/lineup/{y}/">{y}</a><span class="sep">/</span>History', extra_ld=ld, extra_css=CSS))
        urls.append(f"/lineup/{y}/history/")
    for fn, txt in files(L, H).items():
        write(fn, txt)
    return llms_lines(L, site, H), urls


def archive(root, site, write, shell, NAME, current=None):
    A = load_archive(root)
    if not A:
        return [], []
    idx = appearances(A)
    cur = {}
    if current:
        for a in acts(current):
            cur[norm(a["name"])] = a["slug"]
            for m in a.get("members", []):
                cur.setdefault(norm(m), a["slug"])
    urls = []
    for y, Y in sorted(A.items()):
        body, total = page_archive_year(Y, A, site, cur)
        write(f"archive/{y}/index.html", shell(f"Coachella {y} lineup by day and stage ({total} acts) | {NAME}",
              f"The full Coachella {y} lineup by day and stage, {total} acts, with links to acts returning in 2027. Independent, sourced.",
              f"/archive/{y}/", body, crumbs=f'<span class="sep">/</span><a href="/archive/">Archive</a><span class="sep">/</span>{y}',
              extra_ld=[crumbs_ld(site, [("Polo", "/"), ("Archive", "/archive/"), (str(y), f"/archive/{y}/")])], extra_css=CSS))
        urls.append(f"/archive/{y}/")
    body, qas, top = page_archive_index(A, idx, site)
    write("archive/index.html", shell(f"Every Coachella lineup, 1999 to 2026, by day and stage | {NAME}",
          "Every Coachella lineup by year, day and stage, the acts that have played the most, and every stage name. Sourced, independent.",
          "/archive/", body + "", crumbs='<span class="sep">/</span>Archive',
          extra_ld=[faq_ld(qas), crumbs_ld(site, [("Polo", "/"), ("Archive", "/archive/")])], extra_css=CSS))
    urls.append("/archive/")
    body, n = page_artists(A, idx, site, cur)
    write("archive/artists/index.html", shell(f"Every act that has played Coachella, A to Z | {NAME}",
          f"All {n:,} acts listed on Coachella lineups since 1999, A to Z, with every year each one played.", "/archive/artists/", body,
          crumbs='<span class="sep">/</span><a href="/archive/">Archive</a><span class="sep">/</span>Every act',
          extra_ld=[crumbs_ld(site, [("Polo", "/"), ("Archive", "/archive/"), ("Every act", "/archive/artists/")])], extra_css=CSS, extra_js=JS))
    urls.append("/archive/artists/")
    write("archive.json", json.dumps({"note": "Every Coachella lineup by day and stage, transcribed from Wikipedia's 'Coachella Festival line-ups' page (see each year's source). Independent; not affiliated with Coachella.",
                                      "years": [A[y] for y in sorted(A)],
                                      "acts": [{"name": v[0]["as"], "years": [r["year"] for r in v], "sets": v} for k, v in sorted(idx.items())]}, ensure_ascii=False) + "\n")
    llms = ["", "## Every past Coachella lineup", f"- {site}/archive/ - every edition by day and stage; {site}/archive/<year>/ per year; {site}/archive/artists/ every act A-Z with years",
            f"- Data: {site}/archive.json", "- Most appearances: " + "; ".join(f"{n} ({len(v)})" for n, v in top[:10])]
    return llms, urls


def _clean(h):
    return re.sub(r"\s*\(.*?\)\s*$", "", h).strip()


def headliners(root, site, write, shell, NAME):
    root = pathlib.Path(root)
    yrs = json.loads((root / "data/years.json").read_text())
    cal = json.loads((root / "data/calendar.json").read_text())
    known = {y["year"] for y in yrs}
    data = []
    for y in sorted(yrs, key=lambda x: x["year"]):
        data.append({"year": y["year"], "headliners": y.get("headliners") or [], "status": "canceled" if y["year"] == 2020 else ("no festival" if not y.get("headliners") else "happened"), "source": f"{site}/years/"})
    for ed in cal.get("editions", []):
        if ed["year"] not in known and ed.get("lineup", {}).get("headliners"):
            data.append({"year": ed["year"], "headliners": ed["lineup"]["headliners"], "status": "announced", "source": ed["sources"][-1]["url"]})
    count = {}
    for r in data:
        if r["status"] != "happened":
            continue
        for h in r["headliners"]:
            count.setdefault(_clean(h), []).append(r["year"])
    multi = sorted(((k, v) for k, v in count.items() if len(v) > 1), key=lambda t: (-len(t[1]), t[1][0]))
    rows_ = ""
    for r in sorted(data, key=lambda r: -r["year"]):
        link = (f'<a href="/lineup/{r["year"]}/">lineup</a>' if (root / f"data/lineup/{r['year']}.json").exists()
                else (f'<a href="/archive/{r["year"]}/">lineup</a>' if (root / f"data/history/{r['year']}.json").exists() else '<a href="/years/">details</a>'))
        hs = ", ".join(r["headliners"]) or "no festival"
        rows_ += f'<tr><td class="n">{r["year"]}</td><td>{e(hs)}</td><td>{e(r["status"])}</td><td>{link}</td></tr>'
    mh = "".join(f"<li><b>{e(k)}</b> <span>{len(v)} times · {', '.join(str(x) for x in v)}</span></li>" for k, v in multi)
    qas = [("Who has headlined Coachella the most?", "; ".join(f"{k}, {len(v)} times ({', '.join(str(x) for x in v)})" for k, v in multi[:5]) + ". Counted from this guide's year-by-year records; editions that were canceled are not counted."),
           ("Who headlines Coachella 2027?", "Dua Lipa (Friday), Tame Impala (Saturday) and SZA (Sunday), with Daddy Yankee billed \"In the Desert\" with no day.")]
    body = f"""<main class="lu" id="main">
<h1 class="ch">Every Coachella headliner, by year</h1>
<p class="lede">From Pearl Jam's polo-field show in 1993 to the 2027 poster. Names as recorded in <a href="/years/">the year-by-year chapter</a>, where every edition carries its sources; special slots and replacements are labeled the way the sources describe them.</p>
<nav class="chips" aria-label="More"><a href="/lineup/2027/">The 2027 lineup</a><a href="/archive/">Every past lineup</a></nav>
<div class="tbl"><table><thead><tr><th>Year</th><th>Headliners</th><th>Status</th><th></th></tr></thead><tbody>{rows_}</tbody></table></div>
<h2>Headlined more than once</h2><ul class="ix">{mh}</ul>
{faq_html(qas)}
<p class="note">Data: <a href="/headliners.json">headliners.json</a>. Independent. Not affiliated with Coachella, Goldenvoice or AEG.</p>
</main>"""
    write("headliners/index.html", shell(f"Every Coachella headliner, 1999-2027 | {NAME}", "Every Coachella headliner by year, from 1999 to the 2027 lineup, and who has headlined more than once. Sourced, independent.",
          "/headliners/", body, crumbs='<span class="sep">/</span>Headliners', extra_ld=[faq_ld(qas), crumbs_ld(site, [("Polo", "/"), ("Headliners", "/headliners/")])], extra_css=CSS))
    write("headliners.json", json.dumps({"note": "Headliners by year, as recorded in polo.cold.fyi/years/ (sources there) plus announced future editions.", "years": data,
                                         "repeat_headliners": [{"name": k, "years": v} for k, v in multi]}, indent=1, ensure_ascii=False) + "\n")
    return ["", "## Every Coachella headliner", f"- {site}/headliners/ - by year, and who has headlined more than once (data {site}/headliners.json)"], ["/headliners/"]
