#!/usr/bin/env python3
"""
Stem - Meta pixel injector for the cold.fyi static sites.

Adds the Meta base pixel before </head> on every .html page in a site, plus a
one-line measurement note at the end of the footer. Idempotent: pages that
already carry the marker are skipped, so it is safe to re-run after a rebuild.

  python3 meta_pixel.py <site-dir> --pixel <id> [--check] [--quiet]

--check  reports what would change and writes nothing (exit 1 if work is pending).

AX: writes a machine-readable summary to <site-dir>/.stem-pixel.json
    {pixel, pages, injected, already, skipped, note_added, when}
"""
import argparse, json, os, re, sys, datetime

MARK = "tpa-meta-pixel"
NOTE_MARK = "px-note"
NOTE_TAG = '<span class="px-note"'

PIXEL = (
    '\n<!-- {m}: Meta base code. Measurement only - see the footer note. -->\n'
    "<script>!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?"
    "n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;"
    "n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;"
    "t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}"
    "(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');"
    "fbq('init','{p}');fbq('track','PageView');</script>\n"
    '<noscript><img height="1" width="1" style="display:none" alt=""'
    ' src="https://www.facebook.com/tr?id={p}&amp;ev=PageView&amp;noscript=1"/></noscript>\n'
)

NOTE = ('<span class="{n}">A Meta pixel counts visits from our ads - '
        '<a href="https://thirdpolararch.com/privacy">what we collect</a>.</span>')

NOTE_CSS = (
    '\n<style>.{n}{{display:block;margin-top:.6em;font-size:.82em;opacity:.72}}'
    '.{n} a{{color:inherit}}</style>'
)


def inject(html, pixel):
    """Return (new_html, did_pixel, did_note). Never touches a page twice."""
    did_px = did_note = False
    if MARK not in html:
        i = html.lower().rfind("</head>")
        if i == -1:
            return html, False, False
        block = PIXEL.format(m=MARK, p=pixel) + NOTE_CSS.format(n=NOTE_MARK).strip() + "\n"
        html = html[:i] + block + html[i:]
        did_px = True
    if NOTE_TAG not in html:
        j = html.lower().rfind("</footer>")
        if j != -1:
            # keep the note inside the footer's inner wrapper when there is one
            before = html[:j].rstrip()
            at = j
            if before.endswith("</div>"):
                at = len(before) - len("</div>")
            html = html[:at] + NOTE.format(n=NOTE_MARK) + html[at:]
            did_note = True
    return html, did_px, did_note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("--pixel", required=True)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"\d{10,20}", a.pixel):
        sys.exit("pixel id must be digits only")

    pages = injected = already = notes = nohead = 0
    for root, dirs, files in os.walk(a.site):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "fonts", "img")]
        for f in sorted(files):
            if not f.endswith(".html"):
                continue
            p = os.path.join(root, f)
            pages += 1
            src = open(p, encoding="utf-8").read()
            out, dpx, dn = inject(src, a.pixel)
            if dpx:
                injected += 1
            else:
                already += 1
            if dn:
                notes += 1
            if dpx and "</head>" not in src.lower():
                nohead += 1
            if out != src and not a.check:
                open(p, "w", encoding="utf-8").write(out)

    summary = {"pixel": a.pixel, "pages": pages, "injected": injected,
               "already": already, "notes_added": notes, "no_head": nohead,
               "when": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
               "mode": "check" if a.check else "write"}
    if not a.check:
        with open(os.path.join(a.site, ".stem-pixel.json"), "w") as fh:
            json.dump(summary, fh, indent=2)
            fh.write("\n")
    if not a.quiet:
        print(json.dumps(summary))
    if a.check and injected:
        sys.exit(1)


if __name__ == "__main__":
    main()
