#!/usr/bin/env python3
"""Put a festival year on the calendar, or update its lineup. Drives the home-page festival clock.

  # dates announced (give the Friday of weekend one; weekend two is assumed a week later - override with --w2)
  python3 tools/add_year.py 2028 --w1 2028-04-14 --source-url https://... --publication "Pollstar (Name)" --title "Headline" --date 2027-04-19

  # lineup announced
  python3 tools/add_year.py 2028 --headliners "Artist A" "Artist B" "Artist C" --source-url https://... --publication "Billboard" --date 2027-09-17

Only use a source you opened. After the festival happens, also add the year to data/years.json
(the "Every year" chapter) - tools/check.py reminds you.
"""
import argparse, datetime, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAL = ROOT / "data/calendar.json"

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("year", type=int)
ap.add_argument("--w1", help="Friday of weekend one, YYYY-MM-DD")
ap.add_argument("--w2", help="Friday of weekend two (default: a week after --w1)")
ap.add_argument("--headliners", nargs="+")
ap.add_argument("--on-sale")
ap.add_argument("--source-url", required=True)
ap.add_argument("--publication", required=True)
ap.add_argument("--title", default="")
ap.add_argument("--date", default=datetime.date.today().isoformat(), help="publication date of the source")
a = ap.parse_args()

cal = json.loads(CAL.read_text())
ed = next((x for x in cal["editions"] if x["year"] == a.year), None)
if ed is None:
    if not a.w1:
        sys.exit(f"{a.year} isn't on the calendar yet - pass --w1")
    ed = {"year": a.year, "weekends": [], "lineup": {"headliners": []}, "sources": []}
    cal["editions"].append(ed)
if a.w1:
    f1 = datetime.date.fromisoformat(a.w1)
    f2 = datetime.date.fromisoformat(a.w2) if a.w2 else f1 + datetime.timedelta(days=7)
    if f1.weekday() != 4 or f2.weekday() != 4:
        print("warning: weekends usually start on a Friday")
    ed["weekends"] = [[f1.isoformat(), (f1 + datetime.timedelta(days=2)).isoformat()], [f2.isoformat(), (f2 + datetime.timedelta(days=2)).isoformat()]]
if a.headliners:
    ed["lineup"] = {"headliners": a.headliners, "announced": a.date}
if a.on_sale:
    ed["on_sale"] = a.on_sale
src = {"publication": a.publication, "title": a.title, "date": a.date, "url": a.source_url}
if src not in ed["sources"]:
    ed["sources"].append(src)
cal["editions"].sort(key=lambda x: x["year"])
CAL.write_text(json.dumps(cal, indent=1, ensure_ascii=False) + "\n")
print(json.dumps(ed, indent=1, ensure_ascii=False))
print("next: python3 build.py && python3 tools/check.py")
