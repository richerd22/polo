# Working on Polo (for any agent: Claude, Muse, a digest bot, a person)

polo.cold.fyi is an independent, fully footnoted guide to how Coachella works, plus an archive of the billboards on the I-10. It is a static site: you edit `content/` and `data/`, run `build.py`, and commit the generated HTML. GitHub Pages serves `main` from the repo root.

Read `STYLE.md` before writing a sentence. The short version is below.

## The five rules that never bend

1. **Every fact gets a footnote from a source you opened.** If you only saw a search snippet, either open the page or don't state it flat. When sources disagree, say so in the text.
2. **Rights.** Host only:
   - Richard Lathrop's own photos and videos (`own`)
   - Creative Commons images that are BY, BY-SA or CC0, never NC or ND (`cc`)
   - brand or label press kits (`press-kit`)

   Everything else (fan posts, IG, X, news photos) is **linked with credit, never copied**. It goes in `data/still_needed.json` until a hostable image turns up.
3. **Style.**
   - No em or en dashes. Use a spaced hyphen " - ".
   - No hype words (amazing, iconic, legendary, insane, epic, game-changing, unforgettable, must-see).
   - Quotes under 25 words.
   - Digits for 10 and up.
4. **Privacy.** Never describe where Richard lives, his building, or where the Boston stream's camera is.
5. **Independent.** Never imply affiliation with Coachella, Goldenvoice or AEG. Don't use their logos or brand assets. The desert scene, palms and Ferris wheel on the site are original drawings.

No paywall workarounds (archives, mirrors, login tricks). A web.archive.org copy is fine only for a page that was free and has since died.

## Commands

```bash
python3 build.py              # regenerate the whole site from content/ and data/
python3 tools/check.py        # rules above, footnotes, images, rights, EXIF, calendar (0 errors to commit)
python3 tools/check.py --built  # what CI runs: also fails if the committed HTML is stale
python3 -m http.server 8000   # preview at http://localhost:8000
```

`build.py` stamps "updated" from the last commit that touched `content/`, `data/` or `build.py`, so rebuilding an unchanged tree changes nothing.

## Recipes

### Add billboard photos or video (any year)

1. Put the originals in `incoming/billboards/<year>/`. This folder is gitignored, so originals with GPS never get committed.
2. Identify each board:
   - who it's for and what it says, word for word
   - where it stands (road, direction, nearest town; never anyone's home)
   - the date from EXIF (`tools/add_media.py` reads it)

   Search the press for it and open what you find.
3. Run one command per file:
   ```bash
   # attach to a board that's already in the archive
   python3 tools/add_media.py incoming/billboards/2027/IMG_0001.JPG --board 2027 "Artist" \
     --alt "What the picture shows" --caption "Eastbound I-10 east of Cabazon, April 15, 2027."
   # a board that isn't in the archive yet
   python3 tools/add_media.py incoming/billboards/2027/IMG_0002.JPG --new --year 2027 --artist "Artist" \
     --title "Short name for the board" --says "Every word on it" --where "I-10 eastbound, ... (photo location)" \
     --promoted "Their Saturday set at the Mojave" --crop 0 .3 1 .8 --blur .07 .49 .14 .52 \
     --alt "..." --caption "..."
   ```
   - `--crop L T R B` cuts out the dashboard (fractions of the frame).
   - `--blur L T R B` hides a licence plate or face, and can be repeated.
   - Videos (`.mov`, `.mp4`) come out 720px wide and muted, with a poster frame.
   - The tool strips all metadata, makes the 1600px and 800px copies, adds the photo as a source, and removes the board from `still_needed.json` if it was there.
4. Add press sources to the board's `sources` in `data/billboards.raw.json` (`publication`, `url`, `date`). Set `confidence`:
   - `high`: a press report plus a photo showing the copy
   - `medium`: one solid source or one dated photo
   - `low`: social posts only. Low boards are listed but not featured.
5. Run `python3 build.py && python3 tools/check.py`, then commit.

### Add a board you can't host (seen in press, IG, X)

Append to `data/still_needed.json` → `boards`:

```json
{"year": 2027, "artist": "Artist", "title": "Short name", "said": "What it says, if reported",
 "where": "Where it stood, if reported", "sources": [{"publication": "Outlet (Author)", "date": "2027-04-10", "url": "https://..."}],
 "official_post": {"url": "https://instagram.com/p/...", "credit": "@artist on Instagram, April 9, 2027"},
 "in_archive": false, "confidence": "medium"}
```

It renders under "Still needed" on /billboards/ with links and credit. Leads you haven't opened yet go in `research/billboards/still-needed-leads.json`, not on the site.

### A new festival year (2027, 2028, ...)

- **Dates announced** (usually the Monday after weekend two):
  ```bash
  python3 tools/add_year.py 2028 --w1 2028-04-14 --source-url <url you opened> --publication "Outlet (Author)" --title "Headline" --date 2027-04-19
  ```
  The home-page festival clock reads `data/calendar.json` in the browser. It counts down, says when a weekend is on, and once the last known edition is over it says the next dates aren't announced yet. It never shows a stale year, even if nobody touches the repo.
- **Lineup announced:**
  ```bash
  python3 tools/add_year.py 2028 --headliners "A" "B" "C" --source-url ... --publication ... --date ...
  ```
- **After the festival:**
  - Add the year to `data/years.json` (copy the shape of the 2026 entry: dates, headliners, attendance, prices, moments, firsts, sources).
  - Add the new boards (recipes above).
  - Add any big moments to `content/07-moments.md`.
  - `tools/check.py` warns if a past year is missing from `years.json`.
- Billboard years, still-needed years and the "Every year" table all sort themselves. Nothing in `build.py` needs a year changed.

### Add or fix a fact in a chapter

- Chapters are `content/NN-slug.md`. Write the sentence, then add a footnote: `[^xx-short]: Publication - "Title" - YYYY-MM-DD - URL`. Ids are unique within the chapter.
- Boxes:
  - `:::lore Title` for legends told as legends
  - `:::field Richard` for Richard's first-person asides, only what he supplied
  - `:::numbers Title` for small fact panels
- Images in a chapter use `:::figure img/path.jpg WxH | alt text`, then caption lines, then `:::`. CC images need `Photo: [Author](page) · [CC BY 2.0](licence url)` in the caption.
- If you fix a factual error, log it in `data/corrections.json` (`date`, `chapter`, `what`). It shows on /corrections/.

### CC photos for chapters

Flickr and Wikimedia Commons only. Read the licence on the file page itself; no NC or ND. Process it with `tools/add_media.py --dir img/cc --rights cc ...` or the same steps by hand, and log it in `research/images/cc-manifest.json`.

## Where things live

| Path | What |
|---|---|
| `content/*.md` | the 16 chapters (front matter `n`, `slug`, `title`, `short`) |
| `data/billboards.raw.json` | every board: year, artist, title, shows_says, location, promoted, aftermath, sources, image_sources (links only), media (hosted), confidence |
| `data/still_needed.json` | boards known from press or posts with no hostable image |
| `data/calendar.json` | festival dates and headliners per year, for the festival clock |
| `data/years.json` | one record per edition, for the "Every year" chapter |
| `data/corrections.json` | dated corrections log |
| `img/billboards/`, `img/cc/` | published, metadata-free web copies |
| `incoming/` | originals, gitignored |
| `research/` | notes, leads, audits; nothing here is published |
| `build.py` | the generator; CSS and the desert scene live in it |
| `tools/` | `add_media.py`, `add_year.py`, `check.py` |
| `/billboards.json`, `/calendar.json`, `/chapters.json`, `/sources.json`, `/years.json`, `/llms.txt` | generated, machine-readable copies for other agents |

## Git

- Work on a branch and open a PR.
- CI (`.github/workflows/check.yml`) runs `tools/check.py --built` and has to pass.
- Commit the regenerated HTML along with your source change.
