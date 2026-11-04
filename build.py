#!/usr/bin/env python3
"""Build polo.cold.fyi from content/*.md and data/*.json. No dependencies.

    python3 build.py

Writes: index.html, <slug>/index.html for every chapter, all/, sources/, corrections/,
404.html, chapters.json, years.json, billboards.json, sources.json, llms.txt, sitemap.xml, robots.txt.
/play/ is a hand-built page and is left alone (only linked).
"""
import datetime, html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent
SITE = "https://polo.cold.fyi"
NAME = "Polo"
LONGNAME = "Polo: how Coachella actually works"
TODAY = datetime.date.today()
UPDATED = TODAY.strftime("%B %Y")
e = lambda s: html.escape(str(s), quote=True)


# ---------------------------------------------------------------- markdown (small, strict)

def inline(s, refs):
    """Escape, then apply inline markup. refs(id) -> footnote number."""
    out, i = [], 0
    # protect code spans first
    parts = re.split(r"(`[^`]+`)", s)
    res = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            res.append("<code>" + e(p[1:-1]) + "</code>")
            continue
        t = e(p)
        t = re.sub(r"\[\^([A-Za-z0-9_.:-]+)\]", lambda m: refs(m.group(1)), t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)",
                   lambda m: f'<a href="{m.group(2)}"' + (' rel="noopener" target="_blank"' if m.group(2).startswith("http") else "") + f'>{m.group(1)}</a>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
        res.append(t)
    return "".join(res)


def blocks(md, refs, anchors):
    """Markdown body -> HTML. Supports ## ###, paragraphs, - and 1. lists, > quotes,
    :::lore/:::field/:::numbers boxes. Footnote definitions are removed beforehand."""
    lines = md.split("\n")
    html_out, i = [], 0
    def para(buf):
        if buf:
            html_out.append("<p>" + inline(" ".join(x.strip() for x in buf), refs) + "</p>")
    buf = []
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            para(buf); buf = []; i += 1; continue
        m = re.match(r"^:::figure\s+(\S+)\s+(\d+)x(\d+)\s*\|\s*(.*)$", s)
        if m:
            para(buf); buf = []
            src, w, h, alt = m.group(1), m.group(2), m.group(3), m.group(4).strip()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i].strip()); i += 1
            i += 1
            full = "/" + src.lstrip("/")
            sm = re.sub(r"\.(jpe?g|png|webp)$", r"-sm.\1", full)
            cap = "<br>".join(inline(x, refs) for x in inner if x)
            html_out.append(f'<figure class="shot"><a href="{e(full)}"><img src="{e(sm)}" alt="{e(alt)}" width="{w}" height="{h}" loading="lazy" decoding="async"></a>'
                            + (f"<figcaption>{cap}</figcaption>" if cap else "") + "</figure>")
            continue
        m = re.match(r"^:::(lore|field|numbers)\s*(.*)$", s)
        if m:
            para(buf); buf = []
            kind, title = m.group(1), m.group(2).strip()
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i]); i += 1
            i += 1
            label = {"lore": "The lore", "field": "From the field", "numbers": "By the numbers"}[kind]
            head = f'<p class="box-k">{e(label)}' + (f' · <span>{e(title)}</span>' if title else "") + "</p>"
            html_out.append(f'<aside class="box box-{kind}">{head}{blocks(chr(10).join(inner), refs, anchors)}</aside>')
            continue
        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if m:
            para(buf); buf = []
            lvl = len(m.group(1)); text = m.group(2).strip()
            aid = re.sub(r"[^a-z0-9]+", "-", re.sub(r"\[\^[^\]]+\]", "", text).lower()).strip("-")[:60] or "s"
            n = 2
            base = aid
            while aid in anchors:
                aid = f"{base}-{n}"; n += 1
            anchors.add(aid)
            html_out.append(f'<h{lvl} id="{aid}">{inline(text, refs)}</h{lvl}>')
            i += 1; continue
        if s.startswith(">"):
            para(buf); buf = []
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip()); i += 1
            html_out.append("<blockquote><p>" + inline(" ".join(q), refs) + "</p></blockquote>")
            continue
        if re.match(r"^(-|\*|\d+\.)\s+", s):
            para(buf); buf = []
            ordered = bool(re.match(r"^\d+\.", s))
            items = []
            while i < len(lines) and lines[i].strip():
                t = lines[i]
                if re.match(r"^\s*(-|\*|\d+\.)\s+", t) and not t.startswith("    "):
                    items.append(re.sub(r"^\s*(-|\*|\d+\.)\s+", "", t))
                elif items:
                    items[-1] += " " + t.strip()
                i += 1
            tag = "ol" if ordered else "ul"
            html_out.append(f"<{tag}>" + "".join(f"<li>{inline(x.strip(), refs)}</li>" for x in items) + f"</{tag}>")
            continue
        buf.append(ln); i += 1
    para(buf)
    return "\n".join(html_out)


# ---------------------------------------------------------------- content

def parse(path):
    raw = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"{path.name}: missing front matter")
    meta = {}
    for ln in m.group(1).split("\n"):
        if ":" in ln:
            k, v = ln.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    body = m.group(2)
    defs = {}
    def take(mm):
        defs[mm.group(1)] = mm.group(2).strip()
        return ""
    body = re.sub(r"^\[\^([A-Za-z0-9_.:-]+)\]:\s*(.+)$", take, body, flags=re.M)
    meta["n"] = int(meta.get("n", 99))
    meta["body"] = body.strip()
    meta["defs"] = defs
    meta["words"] = len(re.findall(r"[A-Za-z0-9']+", re.sub(r"\[\^[^\]]+\]", "", body)))
    return meta


def source_html(text):
    """'Publication - "Title" - date - URL' -> HTML with the URL linked to its host."""
    t = e(text)
    def link(m):
        url = html.unescape(m.group(0))
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        return f'<a href="{e(url)}" rel="noopener" target="_blank">{e(host)}</a>'
    return re.sub(r"https?://[^\s<]+[^\s<.,;)]", link, t)


def load():
    chapters = sorted((parse(p) for p in (ROOT / "content").glob("*.md")), key=lambda c: c["n"])
    numbers, sources = {}, []   # source key -> number; list of dicts
    def key_of(text):
        u = re.search(r"https?://\S+", text)
        return u.group(0).rstrip(".,;)") if u else re.sub(r"\s+", " ", text.lower())
    for c in chapters:
        c["fn"] = {}
        for fid in re.findall(r"\[\^([A-Za-z0-9_.:-]+)\]", c["body"]):
            if fid in c["fn"]:
                continue
            d = c["defs"].get(fid)
            if d is None:
                raise SystemExit(f"{c['slug']}: footnote [^{fid}] has no definition")
            k = key_of(d)
            if k not in numbers:
                numbers[k] = len(sources) + 1
                sources.append({"n": numbers[k], "text": d, "url": (re.search(r"https?://\S+", d) or [None])[0], "chapters": []})
            c["fn"][fid] = numbers[k]
            s = sources[numbers[k] - 1]
            if c["slug"] not in s["chapters"]:
                s["chapters"].append(c["slug"])
        unused = set(c["defs"]) - set(c["fn"])
        if unused:
            print(f"  note: {c['slug']} has unused footnotes: {', '.join(sorted(unused))}")
    return chapters, sources


# ---------------------------------------------------------------- page shell

FONTS = """@font-face{font-family:'Stencil';font-weight:800;font-display:swap;src:url(/fonts/big-shoulders-stencil-display-latin-800-normal.woff2) format('woff2')}
@font-face{font-family:'Stencil';font-weight:900;font-display:swap;src:url(/fonts/big-shoulders-stencil-display-latin-900-normal.woff2) format('woff2')}
@font-face{font-family:'Serif4';font-weight:400;font-display:swap;src:url(/fonts/source-serif-4-latin-400-normal.woff2) format('woff2')}
@font-face{font-family:'Serif4';font-style:italic;font-weight:400;font-display:swap;src:url(/fonts/source-serif-4-latin-400-italic.woff2) format('woff2')}
@font-face{font-family:'Serif4';font-weight:600;font-display:swap;src:url(/fonts/source-serif-4-latin-600-normal.woff2) format('woff2')}
@font-face{font-family:'Mono';font-weight:400;font-display:swap;src:url(/fonts/jetbrains-mono-latin-400-normal.woff2) format('woff2')}
@font-face{font-family:'Mono';font-weight:600;font-display:swap;src:url(/fonts/jetbrains-mono-latin-600-normal.woff2) format('woff2')}"""

CSS = FONTS + """
:root{--paper:#f3ead8;--paper2:#e9dcc2;--ink:#1d1a16;--muted:#6b6152;--turf:#2f5d3a;--sunset:#d9572b;--dust:#b98d4c;--line:rgba(29,26,22,.14);
--f-display:'Stencil',Impact,'Arial Narrow',sans-serif;--f-body:'Serif4',Georgia,serif;--f-mono:'Mono',ui-monospace,Menlo,monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--paper:#14110d;--paper2:#1f1a14;--ink:#efe6d4;--muted:#a89c86;--turf:#6fa57c;--sunset:#ef7a4c;--dust:#c9a46a;--line:rgba(239,230,212,.14);color-scheme:dark}}
:root[data-theme=dark]{--paper:#14110d;--paper2:#1f1a14;--ink:#efe6d4;--muted:#a89c86;--turf:#6fa57c;--sunset:#ef7a4c;--dust:#c9a46a;--line:rgba(239,230,212,.14);color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:400 1.125rem/1.62 var(--f-body);-webkit-font-smoothing:antialiased}
a{color:var(--turf);text-decoration-thickness:1px;text-underline-offset:.18em}a:hover{color:var(--sunset)}
:focus-visible{outline:2px solid var(--sunset);outline-offset:3px}
.skip{position:absolute;left:-9999px}.skip:focus{left:1rem;top:1rem;background:var(--ink);color:var(--paper);padding:.4rem .8rem;z-index:9}
.progress{position:fixed;top:0;left:0;height:3px;background:var(--sunset);width:0;z-index:5}
.mast{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1rem clamp(1rem,4vw,2.5rem);font:400 .8rem/1.3 var(--f-mono);letter-spacing:.02em;border-bottom:1px solid var(--line);position:relative}
.mast::after{content:"";position:absolute;left:0;right:0;bottom:-5px;height:3px;background:linear-gradient(90deg,var(--turf) 0 50%,var(--sunset) 50% 100%);opacity:.85}
.mast a{color:var(--ink);text-decoration:none}.mast a:hover{color:var(--sunset)}.mast .sep{color:var(--muted);margin:0 .35rem}
.theme-btn{font:inherit;background:none;border:1px solid var(--line);color:var(--ink);padding:.3rem .6rem;border-radius:999px;cursor:pointer}
.layout{display:grid;grid-template-columns:minmax(0,16rem) minmax(0,1fr);gap:clamp(1.5rem,4vw,3.5rem);max-width:76rem;margin:0 auto;padding:2rem clamp(1rem,4vw,2.5rem) 4rem}
.rail{position:sticky;top:1rem;align-self:start;max-height:calc(100vh - 2rem);overflow:auto;font:400 .82rem/1.35 var(--f-mono);padding-right:.5rem}
.rail h2{font:900 1.5rem/1 var(--f-display);text-transform:uppercase;letter-spacing:.02em;margin:0 0 .8rem}
.rail a{display:flex;gap:.6rem;padding:.32rem 0;color:var(--muted);text-decoration:none;border-bottom:1px dashed var(--line)}
.rail a:hover,.rail a.on{color:var(--ink)}.rail a.on{font-weight:600}.rail .n{color:var(--sunset);min-width:1.6rem}
.col{max-width:42rem;min-width:0}
.readmeta{font:400 .78rem/1.4 var(--f-mono);color:var(--muted);margin:0 0 1rem;text-transform:uppercase;letter-spacing:.04em}
h1.ch{font:900 clamp(2.6rem,8vw,4.6rem)/.92 var(--f-display);text-transform:uppercase;letter-spacing:.01em;margin:0 0 1.2rem;overflow-wrap:break-word}
h1.ch .num{display:block;font-size:.42em;color:var(--sunset);letter-spacing:.08em;margin-bottom:.4rem}
.col h2{font:800 clamp(1.5rem,4vw,2rem)/1.05 var(--f-display);text-transform:uppercase;letter-spacing:.015em;margin:2.6rem 0 .7rem}
.col h3{font:600 1.15rem/1.3 var(--f-body);margin:1.8rem 0 .4rem}
.col p,.col li{overflow-wrap:break-word}.col ul,.col ol{padding-left:1.25rem}.col li{margin:.3rem 0}
.short{background:var(--paper2);border-top:3px solid var(--turf);padding:1rem 1.2rem;margin:0 0 2rem;font-size:1.05rem}
.short strong{font:600 .75rem/1 var(--f-mono);text-transform:uppercase;letter-spacing:.08em;display:block;margin-bottom:.45rem;color:var(--turf)}
blockquote{margin:1.6rem 0;padding:0 0 0 1.1rem;border-left:3px solid var(--sunset);font-style:italic;font-size:1.2rem;line-height:1.45}
blockquote p{margin:0}
.box{margin:1.8rem 0;padding:1rem 1.2rem;background:var(--paper2);border-left:4px solid var(--dust)}
.box p:last-child,.box ul:last-child{margin-bottom:0}.box-field{border-left-color:var(--turf)}.box-numbers{border-left-color:var(--sunset)}
.box-k{font:600 .72rem/1.2 var(--f-mono);text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 .5rem}.box-k span{color:var(--ink)}
sup.fn{font:600 .62em/0 var(--f-mono);margin-left:.08em}sup.fn a{text-decoration:none;color:var(--sunset);padding:0 .08em}
.pager{display:flex;justify-content:space-between;gap:1rem;margin:3rem 0 2rem;border-top:1px solid var(--line);padding-top:1rem;font:400 .85rem/1.35 var(--f-mono)}
.pager a{text-decoration:none;color:var(--ink);max-width:48%}.pager a span{display:block;color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.06em}
.pager a.next{text-align:right;margin-left:auto}
.refs h2{margin-top:1rem}.refs ol{font-size:.86rem;line-height:1.45;padding-left:2.6rem}.refs li{margin:.35rem 0;color:var(--muted)}.refs li a{word-break:break-all}
.refs .note{font:400 .8rem/1.4 var(--f-mono);color:var(--muted)}
.foot{border-top:1px solid var(--line);padding:1.5rem clamp(1rem,4vw,2.5rem) 3rem;font:400 .78rem/1.6 var(--f-mono);color:var(--muted);text-align:center}
.foot a{color:var(--muted)}
/* hub */
.hero{max-width:76rem;margin:0 auto;padding:clamp(2rem,7vw,5rem) clamp(1rem,4vw,2.5rem) 1rem}
.hero h1{font:900 clamp(4rem,17vw,11rem)/.82 var(--f-display);text-transform:uppercase;margin:0;letter-spacing:-.005em}
.hero .dek{font-size:clamp(1.15rem,2.6vw,1.5rem);max-width:40rem;margin:1.2rem 0 1rem;line-height:1.4}
.hero .stats{font:400 .8rem/1.6 var(--f-mono);color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.hero .stats b{color:var(--ink)}
.cta{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.4rem 0 0}
.cta a{font:600 .82rem/1 var(--f-mono);text-transform:uppercase;letter-spacing:.06em;text-decoration:none;padding:.75rem 1rem;border:1.5px solid var(--ink);color:var(--ink)}
.cta a.primary{background:var(--ink);color:var(--paper)}.cta a:hover{border-color:var(--sunset);color:var(--sunset)}.cta a.primary:hover{background:var(--sunset);color:var(--paper)}
.toc{max-width:76rem;margin:0 auto;padding:1rem clamp(1rem,4vw,2.5rem) 4rem;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,21rem),1fr));gap:0 2.5rem}
.toc a{display:grid;grid-template-columns:3.2rem 1fr;gap:.2rem .8rem;padding:1.1rem 0;border-top:1px solid var(--line);text-decoration:none;color:var(--ink)}
.toc .n{font:900 2.4rem/1 var(--f-display);color:var(--sunset);grid-row:span 2}
.toc .t{font:800 1.35rem/1.05 var(--f-display);text-transform:uppercase}.toc .s{font-size:.92rem;line-height:1.4;color:var(--muted)}
.toc a:hover .t{color:var(--turf)}
/* tables and archive */
.tbl{width:100%;border-collapse:collapse;font-size:.9rem;margin:1.5rem 0}
.tbl th{font:600 .7rem/1.2 var(--f-mono);text-transform:uppercase;letter-spacing:.06em;text-align:left;color:var(--muted);border-bottom:2px solid var(--ink);padding:.4rem .5rem .4rem 0}
.tbl td{border-bottom:1px solid var(--line);padding:.55rem .5rem .55rem 0;vertical-align:top}
.tbl td.y{font:900 1.3rem/1 var(--f-display);color:var(--sunset)}
.yr{border-top:2px solid var(--ink);margin:2.4rem 0 0;padding-top:.6rem}
.yr>h3{font:900 2.2rem/1 var(--f-display);color:var(--sunset);margin:0 0 .4rem}
.yr dl{display:grid;grid-template-columns:7.5rem 1fr;gap:.25rem 1rem;margin:.4rem 0;font-size:.95rem}
.yr dt{font:600 .7rem/1.6 var(--f-mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}.yr dd{margin:0}
.board{border-top:1px solid var(--line);padding:1rem 0}
.board h4{font:800 1.2rem/1.1 var(--f-display);text-transform:uppercase;margin:0 0 .3rem}
.board .who{font:600 .75rem/1.3 var(--f-mono);text-transform:uppercase;letter-spacing:.05em;color:var(--turf)}
.board p{margin:.35rem 0;font-size:.97rem}.board .meta{font:400 .78rem/1.5 var(--f-mono);color:var(--muted)}
.conf{display:inline-block;font:600 .62rem/1 var(--f-mono);text-transform:uppercase;letter-spacing:.07em;padding:.25rem .4rem;border:1px solid currentColor;margin-left:.4rem;vertical-align:middle}
.conf-high{color:var(--turf)}.conf-medium{color:var(--dust)}.conf-low{color:var(--muted)}
.shot{margin:1.6rem 0}.shot img,.shot video{display:block;width:100%;height:auto;background:var(--paper2);border:1px solid var(--line)}
.shot figcaption{font:400 .78rem/1.5 var(--f-mono);color:var(--muted);margin-top:.4rem}
.board .shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,13rem),1fr));gap:.6rem;margin:.7rem 0}
.board .shots .shot{margin:0}.board .shots video{max-height:26rem;object-fit:cover}
.own{font:600 .62rem/1 var(--f-mono);text-transform:uppercase;letter-spacing:.07em;padding:.25rem .4rem;background:var(--turf);color:var(--paper);margin-left:.4rem;vertical-align:middle}
.needed{list-style:none;padding-left:0!important}.needed li{border-top:1px solid var(--line);padding:.5rem 0;margin:0!important}.needed .meta{font:400 .78rem/1.5 var(--f-mono);color:var(--muted)}
.boardyear{font:900 2.4rem/1 var(--f-display);color:var(--sunset);margin:2.6rem 0 .2rem;border-top:2px solid var(--ink);padding-top:.6rem}
@media (max-width:900px){.layout{grid-template-columns:1fr}.rail{position:static;max-height:none;border:1px solid var(--line);padding:.8rem;order:2}.rail details summary{cursor:pointer}}
@media (max-width:520px){body{font-size:1.06rem}.yr dl{grid-template-columns:1fr}.yr dt{margin-top:.4rem}}
@media print{.rail,.mast,.pager,.foot,.progress,.theme-btn{display:none}.layout{display:block}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""

JS = """(function(){var r=document.documentElement,b=document.getElementById('theme-btn');
function cur(){return r.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}
function lab(){if(b)b.textContent=cur()==='dark'?'Day polo':'Night polo'}
try{var s=localStorage.getItem('polo-theme');if(s)r.setAttribute('data-theme',s)}catch(e){}
lab();if(b)b.addEventListener('click',function(){var n=cur()==='dark'?'light':'dark';r.setAttribute('data-theme',n);try{localStorage.setItem('polo-theme',n)}catch(e){}lab()});
var p=document.getElementById('progress');if(p){var f=function(){var h=document.documentElement,m=h.scrollHeight-h.clientHeight;p.style.width=(m>0?h.scrollTop/m*100:0)+'%'};addEventListener('scroll',f,{passive:true});f()}})();"""


def shell(title, desc, path, body, crumbs="", rail="", article=None):
    canon = SITE + path
    ld = {"@context": "https://schema.org", "@type": "Article" if article else "WebSite", "headline": title, "name": title,
          "description": desc, "url": canon, "inLanguage": "en", "dateModified": TODAY.isoformat(),
          "author": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
          "publisher": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"}}
    if article:
        ld["isPartOf"] = {"@type": "CreativeWork", "name": LONGNAME, "url": SITE + "/"}
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#14110d">
<meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="cold.fyi">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canon}"><meta property="og:image" content="{SITE}/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">
<link rel="preload" href="/fonts/big-shoulders-stencil-display-latin-900-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/source-serif-4-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<script type="application/ld+json">{json.dumps(ld)}</script>
<style>{CSS}</style>
</head>
<body><a class="skip" href="#main">Skip to the text</a><div class="progress" id="progress" aria-hidden="true"></div>
<header class="mast"><span><a href="https://cold.fyi">cold.fyi</a><span class="sep">/</span><a href="/">{NAME}</a>{crumbs}</span><button class="theme-btn" id="theme-btn" type="button">Night polo</button></header>
{body}
<footer class="foot"><p>made with &lt;3 in boston · <a href="https://thirdpolararch.com">Third Polar Arch</a> · <a href="https://map.cold.fyi">the full galaxy: map.cold.fyi</a></p>
<p>Independent. Not affiliated with Coachella, Goldenvoice or AEG. Corrections and takedowns: <a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi">hello@thirdpolararch.com</a> · <a href="/corrections/">corrections</a> · <a href="/sources/">all sources</a> · <a href="/llms.txt">llms.txt</a></p></footer>
<script>{JS}</script>
</body></html>
"""


def rail_html(chapters, active=None):
    links = "".join(f'<a href="/{c["slug"]}/"' + (' class="on" aria-current="page"' if c["slug"] == active else "")
                    + f'><span class="n">{c["n"]:02d}</span>{e(c["title"])}</a>' for c in chapters)
    extra = (f'<a href="/play/"><span class="n">▶</span>Play polo</a>'
             f'<a href="/all/"' + (' class="on"' if active == "all" else "") + '><span class="n">··</span>Everything on one page</a>'
             f'<a href="/sources/"' + (' class="on"' if active == "sources" else "") + '><span class="n">§</span>All sources</a>')
    return f'<nav class="rail" aria-label="Chapters"><h2><a href="/" style="color:inherit;text-decoration:none">Polo</a></h2>{links}{extra}</nav>'


def refs_html(c, sources, title="Sources for this chapter"):
    nums = sorted(set(c["fn"].values()))
    if not nums:
        return ""
    items = "".join(f'<li id="src-{n}" value="{n}">{source_html(sources[n-1]["text"])}</li>' for n in nums)
    return (f'<section class="refs" id="refs"><h2>{e(title)}</h2><p class="note">{len(nums)} of the guide\'s {len(sources)} sources. '
            f'Numbers match the <a href="/sources/">full list</a>.</p><ol>{items}</ol></section>')


# ---------------------------------------------------------------- generated sections

def years_section():
    ys = json.loads((ROOT / "data/years.json").read_text())
    out = []
    for y in ys:
        rows = []
        def row(k, v):
            if v not in (None, "", [], "null"):
                rows.append(f"<dt>{e(k)}</dt><dd>{e(v) if not isinstance(v, list) else e(', '.join(v))}</dd>")
        row("Dates", y.get("dates")); row("Headliners", y.get("headliners"))
        row("Attendance", y.get("attendance")); row("GA ticket", y.get("ga_price")); row("VIP", y.get("vip_price"))
        row("Gross", y.get("gross"))
        moments = "".join(f"<li>{e(m)}</li>" for m in (y.get("moments") or []))
        firsts = "".join(f"<li>{e(f)}</li>" for f in (y.get("firsts") or []))
        srcs = " · ".join(f'<a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s.get("publication","source"))}</a>'
                          for s in (y.get("sources") or []) if s.get("url"))
        out.append(f'<section class="yr" id="y{e(y["year"])}"><h3>{e(y["year"])}</h3><dl>{"".join(rows)}</dl>'
                   + (f"<ul>{moments}</ul>" if moments else "")
                   + (f'<p class="box-k">Firsts</p><ul>{firsts}</ul>' if firsts else "")
                   + (f'<p class="meta" style="font:400 .78rem/1.5 var(--f-mono);color:var(--muted)">Sources: {srcs}</p>' if srcs else "")
                   + "</section>")
    return "<h2 id=\"the-record\">The record</h2>" + "".join(out)


def board_norm(b):
    return {
        "year": b.get("year"),
        "artist": b.get("artist") or "",
        "title": b.get("title") or "",
        "said": b.get("shows_says") or b.get("what_it_showed") or "",
        "where": b.get("location") or b.get("where") or "",
        "promoted": b.get("promoted") or "",
        "aftermath": b.get("aftermath") or "",
        "type": b.get("entry_type") or "artist_promo",
        "confidence": b.get("confidence") or "low",
        "sources": [s for s in (b.get("sources") or []) if isinstance(s, dict) and s.get("url")],
        "photos": [{"url": s.get("url") or s.get("page"), "credit": s.get("credit") or "", "kind": s.get("photo_type") or s.get("type") or ""}
                   for s in (b.get("image_sources") or []) if isinstance(s, dict) and (s.get("url") or s.get("page"))],
        "media": b.get("media") or [],
        "rights": rights_of(b.get("media") or []),
    }


def rights_of(media):
    """'own' = Richard Lathrop's photo, 'cc' = Creative Commons with attribution, 'press-kit' = brand/label press kit.
    Anything else is never rehosted, only linked or embedded with credit."""
    kinds = {m.get("license_kind") for m in media}
    for k in ("own", "cc", "press-kit"):
        if k in kinds:
            return k
    return "link-only"


def media_html(m):
    full = "/" + m["file"].lstrip("/")
    credit = m.get("credit", "")
    lic = m.get("license", "")
    lic_html = (f'<a href="{e(m["license_url"])}" rel="noopener" target="_blank">{e(lic)}</a>' if m.get("license_url") else e(lic))
    src_html = (f' · <a href="{e(m["source_url"])}" rel="noopener" target="_blank">original</a>' if m.get("source_url") else "")
    cap = (e(m.get("caption", "")) + " " if m.get("caption") else "") + f"Photo: {e(credit)}" + (f" ({lic_html})" if lic and m.get("license_kind") != "own" else "") + src_html
    if m.get("kind") == "video":
        poster = "/" + m["poster"].lstrip("/")
        body = (f'<video controls muted playsinline preload="none" poster="{e(poster)}" width="{m["w"]}" height="{m["h"]}" aria-label="{e(m.get("alt",""))}">'
                f'<source src="{e(full)}" type="video/mp4"></video>')
        cap = cap.replace("Photo:", "Video:", 1)
    else:
        sm = full.rsplit(".", 1)[0] + "-sm." + full.rsplit(".", 1)[1]
        body = f'<a href="{e(full)}"><img src="{e(sm)}" alt="{e(m.get("alt",""))}" width="{m["w"]}" height="{m["h"]}" loading="lazy" decoding="async"></a>'
    return f'<figure class="shot">{body}<figcaption>{cap}</figcaption></figure>'


def needed_section():
    path = ROOT / "data/still_needed.json"
    if not path.exists():
        return ""
    d = json.loads(path.read_text())
    items = d.get("boards", [])
    if not items:
        return ""
    out = ['<h2 id="still-needed">Still needed</h2>',
           f'<p>{len(items)} boards that were reported in the press or posted by the artist, label or fans, with no photo this archive can show yet. '
           "Where the original post exists, it's linked with credit. Nothing here is copied. "
           'Shot one of these from the road? <a href="mailto:hello@thirdpolararch.com?subject=Polo%20billboard%20sighting">Send it in</a>, with the road, direction and date.</p>']
    year = None
    for b in sorted(items, key=lambda b: (-b["year"], b["artist"].lower())):
        if b["year"] != year:
            if year is not None:
                out.append("</ul>")
            year = b["year"]; out.append(f'<p class="boardyear" id="need{year}">{year}</p><ul class="needed">')
        srcs = " · ".join(f'<a href="{e(x["url"])}" rel="noopener" target="_blank">{e(x.get("publication","source").split("(")[0].strip())}</a>' for x in b.get("sources", [])[:3])
        post = b.get("official_post")
        post_html = (f' · <a href="{e(post["url"])}" rel="noopener" target="_blank">original post</a> ({e(post.get("credit",""))})' if post and post.get("url") else "")
        out.append(f'<li><strong>{e(b["artist"])}</strong>: {e(b["title"])}'
                   + (f'<br><span class="meta">{e(b["said"])}</span>' if b.get("said") else "")
                   + (f'<br><span class="meta">Where: {e(b["where"])}</span>' if b.get("where") else "")
                   + (f'<br><span class="meta">Reported by: {srcs}{post_html}</span>' if srcs or post_html else "") + "</li>")
    out.append("</ul>")
    return "".join(out)


def boards():
    raw = json.loads((ROOT / "data/billboards.raw.json").read_text())
    out = []
    for b in raw:
        n = board_norm(b)
        if n["type"] == "year_note" or not isinstance(n["year"], int):
            continue
        out.append(n)
    out.sort(key=lambda b: (-b["year"], {"high": 0, "medium": 1, "low": 2}[b["confidence"]], b["artist"].lower()))
    return out


def boards_section(bs):
    shown = [b for b in bs if b["confidence"] in ("high", "medium")]
    held = [b for b in bs if b["confidence"] == "low"]
    shot = [b for b in shown if b["media"]]
    out, year = ["<h2 id=\"the-archive\">The archive</h2>",
                 f"<p>{len(shown)} boards with at least one solid source, newest first. Every photo link goes to the original post or article and its credit. "
                 f"{len(shot)} of them are shown in photos taken from the road by Richard Lathrop, marked <span class=\"own\">From the road</span>. "
                 f"{len(held)} more sightings rest on social posts alone - they're listed at the bottom until something firmer turns up.</p>"], None
    for b in shown:
        if b["year"] != year:
            year = b["year"]; out.append(f'<p class="boardyear" id="b{year}">{year}</p>')
        srcs = " · ".join(f'<a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s.get("publication","source").split("(")[0].strip())}</a>' for s in b["sources"][:4])
        photos = " · ".join(f'<a href="{e(p["url"])}" rel="noopener" target="_blank">photo</a>' + (f' ({e(p["credit"][:80])})' if p["credit"] else "") for p in b["photos"][:2])
        aid = re.sub(r"[^a-z0-9]+", "-", f'{b["year"]} {b["artist"]} {b["title"]}'.lower()).strip("-")[:70]
        own = any(m.get("license_kind") == "own" for m in b["media"])
        out.append(f'<article class="board" id="{aid}"><p class="who">{e(b["artist"])}<span class="conf conf-{b["confidence"]}">{e(b["confidence"])}</span>'
                   + ('<span class="own">From the road</span>' if own else "") + '</p>'
                   f'<h4>{e(b["title"])}</h4>'
                   + (f'<div class="shots">{"".join(media_html(m) for m in b["media"])}</div>' if b["media"] else "")
                   + (f'<p>{e(b["said"])}</p>' if b["said"] else "")
                   + (f'<p class="meta">Where: {e(b["where"])}</p>' if b["where"] and b["where"].lower() not in ("not specified", "not reported") else "")
                   + (f'<p class="meta">For: {e(b["promoted"])}</p>' if b["promoted"] else "")
                   + (f'<p class="meta">After: {e(b["aftermath"])}</p>' if b["aftermath"] else "")
                   + (f'<p class="meta">Sources: {srcs}</p>' if srcs else "")
                   + (f'<p class="meta">See it: {photos}</p>' if photos else "")
                   + "</article>")
    if held:
        out.append('<h2 id="unconfirmed-sightings">Unconfirmed sightings</h2><p>Reported once, mostly on social media. Seen one? Send it in.</p><ul>')
        for b in held:
            s = b["sources"][0]["url"] if b["sources"] else None
            out.append(f'<li><strong>{e(b["year"])}</strong> · {e(b["artist"])}: {e(b["title"])}'
                       + (f' (<a href="{e(s)}" rel="noopener" target="_blank">source</a>)' if s else "") + "</li>")
        out.append("</ul>")
    out.append(needed_section())
    return "".join(out)


# ---------------------------------------------------------------- build

def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def main():
    chapters, sources = load()
    bs = boards()
    total_words = sum(c["words"] for c in chapters)
    for c in chapters:
        def refs(fid, c=c):
            n = c["fn"][fid]
            return f'<sup class="fn"><a href="#src-{n}" id="ref-{c["slug"]}-{fid}">{n}</a></sup>'
        c["refs"] = refs
        anchors = set()
        c["html"] = blocks(c["body"], refs, anchors)
        if c["slug"] == "years":
            c["html"] += years_section()
        if c["slug"] == "billboards":
            c["html"] += boards_section(bs)
        c["mins"] = max(1, round(c["words"] / 230))

    # chapter pages
    for i, c in enumerate(chapters):
        prev_c = chapters[i - 1] if i > 0 else None
        next_c = chapters[i + 1] if i + 1 < len(chapters) else None
        pager = '<nav class="pager">' + (f'<a href="/{prev_c["slug"]}/"><span>Back · {prev_c["n"]:02d}</span>{e(prev_c["title"])}</a>' if prev_c else '<span></span>') \
            + (f'<a class="next" href="/{next_c["slug"]}/"><span>Next · {next_c["n"]:02d}</span>{e(next_c["title"])}</a>' if next_c else '<a class="next" href="/play/"><span>Next</span>Play polo</a>') + "</nav>"
        body = f"""<div class="layout">{rail_html(chapters, c['slug'])}<main class="col" id="main">
<p class="readmeta">Chapter {c['n']:02d} of {max(x['n'] for x in chapters):02d} · about {c['mins']} min read · updated {UPDATED}</p>
<h1 class="ch"><span class="num">{c['n']:02d}</span>{e(c['title'])}</h1>
<div class="short"><strong>The short version</strong>{inline(c.get('short',''), lambda f: '')}</div>
{c['html']}
{pager}
{refs_html(c, sources)}
</main></div>"""
        write(f"{c['slug']}/index.html", shell(f"{c['title']} | {LONGNAME}", c.get("short", "")[:300], f"/{c['slug']}/", body,
                                              crumbs=f'<span class="sep">/</span>{e(c["title"])}', article=True))

    # hub
    toc = "".join(f'<a href="/{c["slug"]}/"><span class="n">{c["n"]:02d}</span><span class="t">{e(c["title"])}</span><span class="s">{e(c.get("short","")[:170].rsplit(" ",1)[0])}…</span></a>' for c in chapters)
    hub = f"""<main id="main"><section class="hero"><h1>Polo</h1>
<p class="dek">How Coachella actually works: the polo club that stopped playing polo, the roads, the buses, the tents named for deserts, the money, the moments, the pyramid, and every billboard on the drive in.</p>
<p class="stats"><b>{len(chapters)}</b> chapters · <b>{total_words:,}</b> words · <b>{len(sources)}</b> sources · <b>{len(json.loads((ROOT / 'data/years.json').read_text()))}</b> years · <b>{len([b for b in bs if b['confidence'] != 'low'])}</b> billboards · updated {UPDATED}</p>
<div class="cta"><a class="primary" href="/{chapters[0]['slug']}/">Start reading</a><a href="/pyramid/">The pyramid</a><a href="/billboards/">The billboards</a><a href="/play/">Play polo</a><a href="/all/">One page</a></div></section>
<section class="toc" aria-label="Chapters">{toc}</section></main>"""
    write("index.html", shell(LONGNAME, "A cited deep dive on how Coachella works - the polo club, the roads, the stages, the money, the moments, the pyramid and every billboard on the I-10. Independent.", "/", hub))

    # all
    allbody = "".join(f'<section id="{c["slug"]}"><p class="readmeta">Chapter {c["n"]:02d}</p><h1 class="ch"><span class="num">{c["n"]:02d}</span>{e(c["title"])}</h1>'
                      f'<div class="short"><strong>The short version</strong>{inline(c.get("short",""), lambda f: "")}</div>{c["html"]}</section>' for c in chapters)
    allrefs = "".join(f'<li id="src-{s["n"]}" value="{s["n"]}">{source_html(s["text"])}</li>' for s in sources)
    write("all/index.html", shell(f"Everything on one page | {LONGNAME}", "The whole guide on one page, with every source.", "/all/",
          f'<div class="layout">{rail_html(chapters, "all")}<main class="col" id="main">{allbody}<section class="refs" id="refs"><h2>All sources</h2><ol>{allrefs}</ol></section></main></div>',
          crumbs='<span class="sep">/</span>Everything'))

    # sources page
    srcbody = "".join(f'<li id="src-{s["n"]}" value="{s["n"]}">{source_html(s["text"])} <span class="note">· ' +
                      ", ".join(f'<a href="/{ch}/">{ch}</a>' for ch in s["chapters"]) + "</span></li>" for s in sources)
    write("sources/index.html", shell(f"All sources | {LONGNAME}", f"Every one of the {len(sources)} sources behind the guide.", "/sources/",
          f'<div class="layout">{rail_html(chapters, "sources")}<main class="col" id="main"><h1 class="ch">All sources</h1>'
          f'<p>{len(sources)} sources, numbered in the order they first appear. Each links to the chapters that cite it. Spot something wrong? '
          f'<a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20correction">Tell us</a>.</p><section class="refs"><ol>{srcbody}</ol></section></main></div>',
          crumbs='<span class="sep">/</span>Sources'))

    # corrections
    corr_path = ROOT / "data/corrections.json"
    corr = json.loads(corr_path.read_text()) if corr_path.exists() else []
    citems = "".join(f"<li><strong>{e(c['date'])}</strong> · <a href=\"/{e(c['chapter'])}/\">{e(c['chapter'])}</a>: {e(c['what'])}</li>" for c in corr) or "<li>None yet.</li>"
    write("corrections/index.html", shell(f"Corrections | {LONGNAME}", "Every correction and update, dated.", "/corrections/",
          f'<div class="layout">{rail_html(chapters)}<main class="col" id="main"><h1 class="ch">Corrections</h1>'
          f'<p>Every fix to a fact, dated. Typos and wording changes aren\'t listed. To report one: '
          f'<a href="mailto:hello@thirdpolararch.com?subject=polo.cold.fyi%20correction">hello@thirdpolararch.com</a>.</p><ul>{citems}</ul></main></div>',
          crumbs='<span class="sep">/</span>Corrections'))

    # 404
    write("404.html", shell(f"Not found | {LONGNAME}", "Page not found.", "/404.html",
          '<main class="col" id="main" style="margin:3rem auto;padding:0 1rem"><h1 class="ch">Wrong field</h1><p>This page isn\'t here. The polo club isn\'t playing polo either. <a href="/">Back to the guide</a>.</p></main>'))

    # data (AX)
    write("chapters.json", json.dumps([{"n": c["n"], "slug": c["slug"], "title": c["title"], "short": c.get("short", ""), "url": f"{SITE}/{c['slug']}/",
                                         "words": c["words"], "sources": sorted(set(c["fn"].values()))} for c in chapters], indent=1, ensure_ascii=False))
    write("sources.json", json.dumps([{"n": s["n"], "citation": s["text"], "url": s["url"], "chapters": s["chapters"]} for s in sources], indent=1, ensure_ascii=False))
    write("years.json", (ROOT / "data/years.json").read_text())
    write("billboards.json", json.dumps({"updated": TODAY.isoformat(), "note": "rights: own = photo by Richard Lathrop, hosted here; cc = Creative Commons, credited; press-kit = brand/label press kit; link-only = original post linked with credit, never copied. media lists hosted files.",
                                         "boards": bs}, indent=1, ensure_ascii=False))
    llms = [f"# {LONGNAME}", "", "> A cited, independent deep dive on how the Coachella festival works - the grounds (Empire Polo Club), polo itself, the stages, the 2006 Daft Punk pyramid, the moments, the transport system, camping rituals, the lineup, the build, the money, the desert season and an archive of artist billboards on the I-10.",
            "", f"About {total_words:,} words, {len(sources)} sources, updated {UPDATED}. Not affiliated with Coachella, Goldenvoice or AEG.", "", "## Chapters"]
    llms += [f"- [{c['title']}]({SITE}/{c['slug']}/): {c.get('short','')}" for c in chapters]
    llms += ["", "## Data", f"- {SITE}/chapters.json", f"- {SITE}/sources.json", f"- {SITE}/years.json - every edition 1999-2026 plus 1993", f"- {SITE}/billboards.json - the billboard archive", "",
             "## Other", f"- [Play polo]({SITE}/play/): a small browser polo game", f"- [Everything on one page]({SITE}/all/)", f"- [All sources]({SITE}/sources/)"]
    write("llms.txt", "\n".join(llms) + "\n")
    urls = ["/", "/all/", "/sources/", "/play/", "/corrections/"] + [f"/{c['slug']}/" for c in chapters]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    write("CNAME", "polo.cold.fyi\n")
    print(f"built {len(chapters)} chapters, {total_words:,} words, {len(sources)} sources, {len(bs)} boards")


if __name__ == "__main__":
    main()
