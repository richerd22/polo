#!/usr/bin/env python3
"""Check the guide before you commit. No dependencies except Pillow (for image checks).

    python3 tools/check.py           # content, data, images, rights
    python3 tools/check.py --built   # also rebuild and fail if the committed site is stale (CI runs this)

Errors fail (exit 1). Warnings print but pass. Every rule here comes from STYLE.md / AGENTS.md.
"""
import datetime, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors, warnings = [], []
err = lambda where, msg: errors.append(f"{where}: {msg}")
warn = lambda where, msg: warnings.append(f"{where}: {msg}")

DASHES = re.compile("[–—]")
HYPE = re.compile(r"\b(amazing|iconic|legendary|insane|epic|game-changing|unforgettable|must-see)\b", re.I)
REF = re.compile(r"\[\^([A-Za-z0-9_.:-]+)\](?!:)")
DEF = re.compile(r"^\[\^([A-Za-z0-9_.:-]+)\]:\s*(.+)$", re.M)
FIG = re.compile(r"^:::figure\s+(\S+)\s+(\d+)x(\d+)\s*\|\s*(.*)$", re.M)
BAD_LIC = re.compile(r"\b(NC|ND)\b|non-?commercial|no ?deriv", re.I)


def img_size(rel):
    try:
        from PIL import Image
        with Image.open(ROOT / rel) as im:
            return im.size, im.getexif()
    except ImportError:
        return None, None


def check_image(where, rel, w=None, h=None, need_sm=True):
    p = ROOT / rel.lstrip("/")
    if not p.exists():
        return err(where, f"missing file {rel}")
    if p.suffix.lower() in (".jpg", ".jpeg"):
        size, exif = img_size(rel.lstrip("/"))
        if size and w and (size[0], size[1]) != (int(w), int(h)):
            err(where, f"{rel} is {size[0]}x{size[1]}, not {w}x{h}")
        if exif and (0x8825 in exif or len(exif)):
            err(where, f"{rel} still has EXIF metadata (GPS/camera) - reprocess with tools/add_media.py")
        if need_sm:
            sm = p.with_name(p.stem + "-sm" + p.suffix)
            if not sm.exists():
                err(where, f"missing small copy {sm.relative_to(ROOT)}")
    if p.stat().st_size > 15 * 1024 * 1024:
        err(where, f"{rel} is over 15 MB")


def check_content():
    ids_seen = {}
    for f in sorted((ROOT / "content").glob("*.md")):
        t = f.read_text(); name = f"content/{f.name}"
        if not t.startswith("---\n"):
            err(name, "missing front matter")
        for i, ln in enumerate(t.split("\n"), 1):
            if DASHES.search(ln):
                err(f"{name}:{i}", "em or en dash - use a spaced hyphen ' - '")
            if not ln.startswith("[^") and not ln.startswith(">"):
                body = re.sub(r'"[^"]*"', "", ln)  # hype words inside quotes are someone else's words
                m = HYPE.search(body)
                if m:
                    warn(f"{name}:{i}", f"hype word {m.group(0)!r}")
            if ln.startswith(">"):
                q = re.sub(r"\[\^[^\]]+\]", "", ln.lstrip("> "))
                if len(q.split()) > 25:
                    err(f"{name}:{i}", f"block quote is {len(q.split())} words (max 25)")
            for q in re.findall(r'"([^"]*)"', ln if not ln.startswith("[^") else ""):
                if len(q.split()) > 25:
                    warn(f"{name}:{i}", f"quote of {len(q.split())} words (max 25)")
        defs = {m.group(1): m.group(2) for m in DEF.finditer(t)}
        refs = set(REF.findall(DEF.sub("", t)))
        for r in sorted(refs - set(defs)):
            err(name, f"footnote [^{r}] has no definition")
        for d in sorted(set(defs) - refs):
            warn(name, f"footnote [^{d}] is defined but never used")
        for k, v in defs.items():
            if k in ids_seen and ids_seen[k] != v:
                warn(name, f"footnote id [^{k}] also used in {ids_seen[k][:0] or 'another chapter'} with different text")
            ids_seen.setdefault(k, v)
            if " - " not in v:
                warn(name, f"[^{k}] doesn't follow 'Publication - \"Title\" - date - URL'")
            if not re.search(r"https?://", v) and not re.search(r"\b(film|documentary|book|print|interview|dir\.|photographed)\b", v, re.I):
                warn(name, f"[^{k}] has no URL (fine only for films, books and print)")
        for m in FIG.finditer(t):
            check_image(name, m.group(1), m.group(2), m.group(3))
            if not m.group(4).strip():
                err(name, f"figure {m.group(1)} has no alt text")
            after = t[m.end():t.find(":::", m.end())]
            if "img/cc/" in m.group(1) and not re.search(r"creativecommons\.org|CC0|public domain", after, re.I):
                err(name, f"CC figure {m.group(1)} has no licence link in its caption")


def check_media(where, m):
    kind = m.get("license_kind")
    if kind not in ("own", "cc", "press-kit"):
        err(where, f"license_kind {kind!r} - only own, cc or press-kit can be hosted; link anything else instead")
    if kind in ("cc", "press-kit") and not (m.get("license") and m.get("source_url")):
        err(where, "cc/press-kit media needs license and source_url")
    if kind == "cc" and (BAD_LIC.search(m.get("license", "")) or not m.get("license_url")):
        err(where, f"CC licence {m.get('license')!r} must be BY / BY-SA / CC0 with a license_url")
    for f in ("file", "alt", "caption", "credit", "w", "h"):
        if not m.get(f):
            err(where, f"media is missing {f}")
    if m.get("kind") == "video":
        check_image(where, m["file"], need_sm=False)
        if m.get("poster"):
            check_image(where, m["poster"], m.get("w"), m.get("h"), need_sm=False)
        else:
            err(where, "video has no poster")
    elif m.get("file"):
        check_image(where, m["file"], m.get("w"), m.get("h"))


def check_data():
    for f in sorted((ROOT / "data").glob("*.json")):
        try:
            json.loads(f.read_text())
        except Exception as x:
            err(f"data/{f.name}", f"invalid JSON: {x}")
        if DASHES.search(f.read_text()):
            warn(f"data/{f.name}", "contains an em or en dash (shown on the site - use ' - ')")
    raw = json.loads((ROOT / "data/billboards.raw.json").read_text())
    seen = set()
    for i, b in enumerate(raw):
        w = f"data/billboards.raw.json[{i}] {b.get('year')} {b.get('artist')}"
        if b.get("entry_type") == "year_note":
            continue
        if not isinstance(b.get("year"), int):
            warn(w, "year isn't a number, so the board is kept in the data but not shown on the site")
        for k in ("artist", "title"):
            if not b.get(k):
                err(w, f"missing {k}")
        if b.get("confidence") not in ("high", "medium", "low"):
            err(w, f"confidence must be high, medium or low (got {b.get('confidence')!r})")
        srcs = [s for s in b.get("sources") or [] if isinstance(s, dict) and s.get("url")]
        if not srcs:
            err(w, "no source with a url")
        key = (b.get("year"), (b.get("artist") or "").lower(), (b.get("title") or "").lower())
        if key in seen:
            err(w, "duplicate board (same year, artist and title)")
        seen.add(key)
        for m in b.get("media") or []:
            check_media(w, m)
    nd = json.loads((ROOT / "data/still_needed.json").read_text())
    hosted = {(b.get("year"), (b.get("artist") or "").lower()) for b in raw if b.get("media")}
    for i, b in enumerate(nd.get("boards", [])):
        w = f"data/still_needed.json[{i}] {b.get('year')} {b.get('artist')}"
        for k in ("year", "artist", "title"):
            if not b.get(k):
                err(w, f"missing {k}")
        if not any(s.get("url") for s in b.get("sources") or []) and not (b.get("official_post") or {}).get("url"):
            err(w, "needs at least one source or official_post url")
        if (b.get("year"), (b.get("artist") or "").lower()) in hosted and not b.get("in_archive"):
            warn(w, "this artist already has a hosted image for that year - still needed?")
    cal = json.loads((ROOT / "data/calendar.json").read_text())
    years = set()
    for ed in cal.get("editions", []):
        w = f"data/calendar.json {ed.get('year')}"
        if ed.get("year") in years:
            err(w, "duplicate year")
        years.add(ed.get("year"))
        try:
            (a1, a2), (b1, b2) = ([datetime.date.fromisoformat(x) for x in wk] for wk in ed["weekends"])
            if not (a1 <= a2 < b1 <= b2) or a1.year != ed["year"]:
                err(w, "weekends out of order or wrong year")
            if a1.weekday() != 4 or b1.weekday() != 4:
                warn(w, "a weekend doesn't start on a Friday - double check")
        except Exception as x:
            err(w, f"weekends must be [[start, end], [start, end]] in YYYY-MM-DD ({x})")
        if not any(s.get("url") for s in ed.get("sources", [])):
            err(w, "needs a source url for the dates")
    ys = [y["year"] for y in json.loads((ROOT / "data/years.json").read_text())]
    if len(ys) != len(set(ys)):
        err("data/years.json", "duplicate year")
    for y in years:
        if y not in ys and y <= datetime.date.today().year and any(
                datetime.date.fromisoformat(e["weekends"][1][1]) < datetime.date.today() for e in cal["editions"] if e["year"] == y):
            warn("data/years.json", f"{y} has happened but has no entry in years.json yet")


def check_repo():
    tracked = subprocess.run(["git", "ls-files", "incoming"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if tracked:
        err("incoming/", "originals are tracked by git - they must stay out of the repo (git rm --cached)")
    for p in (ROOT / "img").rglob("*"):
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg") and not p.stem.endswith("-poster"):
            size, exif = img_size(str(p.relative_to(ROOT)))
            if exif and len(exif):
                err(str(p.relative_to(ROOT)), "has EXIF metadata - strip it")


def check_built():
    before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    subprocess.run([sys.executable, "build.py"], cwd=ROOT, check=True, capture_output=True)
    after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    if after != before:
        err("build", "the committed HTML is out of date - run python3 build.py and commit the result:\n" + after)


if __name__ == "__main__":
    check_content(); check_data(); check_repo()
    if "--built" in sys.argv:
        check_built()
    for w in warnings:
        print("warn ", w)
    for x in errors:
        print("ERROR", x)
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)
