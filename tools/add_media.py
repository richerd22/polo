#!/usr/bin/env python3
"""Add a photo or video to the billboard archive (or any chapter) in one step.

Processes the original (orientation, optional crop and plate blur, resize to
1600px + 800px "-sm", every bit of EXIF/GPS stripped; videos 720px wide, muted,
metadata stripped, with a poster frame), writes it under img/, and attaches it
to a board in data/billboards.raw.json - or creates the board.

Originals go in incoming/ (gitignored). Only the web copies are published.

Rights rule (enforced): only --rights own (the photographer gave it to the
site), cc (Creative Commons BY / BY-SA / CC0 - never NC or ND) or press-kit
(a brand/label press kit that allows editorial use). Anything else: don't
host it - add it to data/still_needed.json with a link instead.

Examples
  # Richard's photo of an existing board
  python3 tools/add_media.py incoming/billboards/2027/IMG_1234.JPG \\
      --board 2027 "Sabrina Carpenter" --name 2027-sabrina-whatever \\
      --alt "Pink billboard reading ..." --caption "Eastbound I-10 east of Cabazon, April 15, 2027."

  # a new board, with a crop (left top right bottom, fractions) and a plate blurred
  python3 tools/add_media.py incoming/billboards/2027/IMG_1300.JPG --new \\
      --year 2027 --artist "Someone" --title "What it says" --says "Full copy of the board" \\
      --where "I-10 eastbound east of Cabazon (photo location)" --promoted "Their Saturday set" \\
      --crop 0 .3 1 .8 --blur .07 .49 .14 .52 --alt "..." --caption "..."

  # a CC photo from Flickr
  python3 tools/add_media.py ~/Downloads/x.jpg --board 2027 "Someone" --rights cc \\
      --credit "Jane Doe (Flickr)" --license "CC BY 2.0" \\
      --license-url https://creativecommons.org/licenses/by/2.0/ \\
      --source-url https://www.flickr.com/photos/... --alt "..." --caption "..."

Then: python3 build.py && python3 tools/check.py
"""
import argparse, datetime, json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/billboards.raw.json"
NEEDED = ROOT / "data/still_needed.json"
SITE = "https://polo.cold.fyi/"
OWN_CREDIT = "Richard Lathrop"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def exif_date(path):
    try:
        from PIL import Image
        ex = Image.open(path).getexif()
        v = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        if v:
            return datetime.datetime.strptime(v[:19], "%Y:%m:%d %H:%M:%S").date().isoformat()
    except Exception:
        pass
    try:  # videos
        out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)], capture_output=True, text=True).stdout
        t = json.loads(out)["format"]["tags"].get("creation_time") or json.loads(out)["format"]["tags"].get("com.apple.quicktime.creationdate")
        return t[:10] if t else None
    except Exception:
        return None


def do_photo(src, dest, crop, blurs):
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    W, H = im.size
    for a, b, c, d in blurs:
        box = (int(a * W), int(b * H), int(c * W), int(d * H))
        im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(18)), box)
    if crop:
        im = im.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))
    im = ImageOps.autocontrast(im, cutoff=0.3)
    im = ImageEnhance.Contrast(im).enhance(1.04)
    size = None
    for suffix, edge in (("", 1600), ("-sm", 800)):
        x = im.copy(); x.thumbnail((edge, edge), Image.LANCZOS)
        if suffix:
            x = x.filter(ImageFilter.UnsharpMask(1, 40, 2))
        else:
            size = x.size
        x.save(dest.with_name(dest.stem + suffix + ".jpg"), "JPEG", quality=80, optimize=True, progressive=True)  # no exif= -> stripped
    return size


def do_video(src, dest):
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed for video")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-an", "-map_metadata", "-1", "-vf", "scale='min(720,iw)':-2",
                    "-c:v", "libx264", "-crf", "26", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)], check=True)
    poster = dest.with_name(dest.stem + "-poster.jpg")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", str(dest), "-frames:v", "1", "-map_metadata", "-1", "-q:v", "4", str(poster)], check=True)
    from PIL import Image
    return Image.open(poster).size, poster


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=pathlib.Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--board", nargs=2, metavar=("YEAR", "ARTIST"), help="attach to the board for YEAR whose artist contains ARTIST")
    g.add_argument("--new", action="store_true", help="create a new board")
    ap.add_argument("--title-match", default="", help="with --board, also match this text in the board title")
    ap.add_argument("--name", help="file name without extension (default: YEAR-artist-title)")
    ap.add_argument("--dir", default="img/billboards")
    ap.add_argument("--alt", required=True, help="what's in the picture, for screen readers")
    ap.add_argument("--caption", required=True, help="where and when, e.g. 'Eastbound I-10 east of Cabazon, April 15, 2027.'")
    ap.add_argument("--rights", choices=["own", "cc", "press-kit"], default="own")
    ap.add_argument("--credit", default=OWN_CREDIT)
    ap.add_argument("--license", help="e.g. 'CC BY 2.0' (required for cc and press-kit)")
    ap.add_argument("--license-url")
    ap.add_argument("--source-url", help="original page (required for cc and press-kit)")
    ap.add_argument("--taken", help="YYYY-MM-DD (default: from EXIF)")
    ap.add_argument("--crop", nargs=4, type=float, metavar=("L", "T", "R", "B"))
    ap.add_argument("--blur", nargs=4, type=float, action="append", default=[], metavar=("L", "T", "R", "B"), help="blur a box (plates, faces); repeatable")
    for f in ("year", "artist", "title", "says", "where", "promoted"):
        ap.add_argument("--" + f)
    ap.add_argument("--type", default="artist_promo", help="artist_promo | brand | activation | label | unknown")
    ap.add_argument("--confidence", default="medium", choices=["high", "medium", "low"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.src.exists():
        sys.exit(f"no such file: {a.src}")
    lic_kind = a.rights
    if lic_kind != "own" and not (a.license and a.source_url):
        sys.exit("--license and --source-url are required for cc and press-kit")
    if lic_kind == "cc" and re.search(r"\b(NC|ND)\b", a.license or ""):
        sys.exit("NC and ND licences can't be hosted here - link it from data/still_needed.json instead")
    if lic_kind == "own" and a.credit != OWN_CREDIT:
        print(f"note: rights=own with credit {a.credit!r} - only use 'own' when that person gave the photo to the site")

    raw = json.loads(RAW.read_text())
    taken = a.taken or exif_date(a.src)
    if a.new:
        miss = [f for f in ("year", "artist", "title") if not getattr(a, f)]
        if miss:
            sys.exit("--new needs " + ", ".join("--" + m for m in miss))
        year = int(a.year)
        board = None
    else:
        year = int(a.board[0])
        hits = [b for b in raw if b.get("year") == year and a.board[1].lower() in (b.get("artist") or "").lower()
                and a.title_match.lower() in (b.get("title") or "").lower()]
        if len(hits) != 1:
            print(f"{len(hits)} boards match {year} / {a.board[1]!r}" + (f" / {a.title_match!r}" if a.title_match else "") + ":")
            for b in hits:
                print("   ", b.get("artist"), "|", b.get("title"))
            sys.exit("narrow it with --title-match, or use --new")
        board = hits[0]
    if taken and not str(taken).startswith(str(year)):
        print(f"warning: taken {taken} but board year {year} - check the date")

    is_video = a.src.suffix.lower() in (".mov", ".mp4", ".m4v")
    name = a.name or slug(f"{year} {a.artist if a.new else board['artist']} {a.title if a.new else board['title']}")[:60]
    outdir = ROOT / a.dir; outdir.mkdir(parents=True, exist_ok=True)
    rel = f"{a.dir.strip('/')}/{name}"
    if a.dry_run:
        print("would write", rel + (".mp4" if is_video else ".jpg")); return
    if is_video:
        (w, h), poster = do_video(a.src, outdir / f"{name}.mp4")
        media = {"kind": "video", "file": rel + ".mp4", "poster": rel + "-poster.jpg", "w": w, "h": h}
        url = SITE + rel + ".mp4"
    else:
        w, h = do_photo(a.src, outdir / f"{name}.jpg", a.crop, a.blur)
        media = {"kind": "photo", "file": rel + ".jpg", "w": w, "h": h}
        url = SITE + rel + ".jpg"
    media.update({"alt": a.alt, "caption": a.caption, "credit": a.credit,
                  "license": a.license or f"© {a.credit}, used with permission", "license_kind": lic_kind, "taken": taken})
    if a.license_url:
        media["license_url"] = a.license_url
    if a.source_url:
        media["source_url"] = a.source_url
    src_entry = {"publication": f"{a.credit} (photo, polo.cold.fyi)" if lic_kind == "own" else a.credit, "date": taken or str(year),
                 "url": url if lic_kind == "own" else a.source_url}

    if board is None:
        board = {"year": year, "artist": a.artist, "title": a.title, "shows_says": a.says or "", "location": a.where or "",
                 "promoted": a.promoted or "", "aftermath": None, "entry_type": a.type, "sources": [], "image_sources": [], "media": [],
                 "confidence": a.confidence,
                 "confidence_note": "One dated first-hand photo. Add a press source when one turns up." if lic_kind == "own" else "",
                 "notes": f"Added {datetime.date.today().isoformat()} with tools/add_media.py."}
        raw.append(board)
    board.setdefault("media", []).append(media)
    board.setdefault("sources", []).append(src_entry)
    RAW.write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {media['file']} ({w}x{h}) and attached it to {board['year']} {board['artist']} - {board['title']}")

    # a board that now has a hosted image no longer belongs on the still-needed list
    if NEEDED.exists():
        nd = json.loads(NEEDED.read_text())
        keep = [x for x in nd.get("boards", []) if not (x.get("year") == year and x.get("artist", "").lower() == board["artist"].lower())]
        if len(keep) != len(nd.get("boards", [])):
            nd["boards"] = keep; nd["updated"] = datetime.date.today().isoformat()
            NEEDED.write_text(json.dumps(nd, indent=1, ensure_ascii=False) + "\n")
            print("removed it from data/still_needed.json")
    print("next: python3 build.py && python3 tools/check.py")


if __name__ == "__main__":
    main()
