# polo.cold.fyi

How Coachella actually works: the grounds, the roads, the buses, the rituals, the money, the moments, and a living archive of the billboards on the way in. Named for Empire Polo Club, the grounds the festival takes over.

Independent. Not affiliated with Coachella, Goldenvoice or AEG.

## Layout

- `research/` - raw, cited research notes. Every fact carries its source (URL, publication, date). Social posts are "reported by attendees" until confirmed elsewhere.
  - `research/billboards/` - billboard research by year range, plus `context.md` (the ritual, the roads, who owns the boards, image rights)
  - `research/chapters/` - one file per chapter cluster
- `incoming/billboards/` - Richard Lathrop's original photos and videos (full resolution, with EXIF and GPS). Gitignored, so they are never committed or published.
- `img/billboards/` - the published copies: resized (1600px and an 800px `-sm`), EXIF and GPS stripped, plates blurred, videos muted. Logged in `research/billboards/richard-2024-2026.md`.
- `data/still_needed.json` - boards reported in the press or posted officially, with no image yet (rendered at the bottom of /billboards/). Unverified leads wait in `research/billboards/still-needed-leads.json`.
- `data/billboards.raw.json` - every billboard found so far, merged, unreviewed. Fields: year, artist, title, shows_says, location, promoted, aftermath, sources, image_sources, confidence, entry_type, notes
- The site itself lands here once the outline is approved (GitHub Pages, `main`, root)

## Rules

- No claim without a source. Conflicting sources: record both.
- Images: host only Richard's own photos, Creative Commons images (Wikimedia/Flickr, with author and license) and brand or label press kits. Everything else: link or embed the original post with credit, never copy it. Fan photos only with written permission and credit. Street View by link (coordinates + imagery date), never screenshots.
- A board's `media` entries carry `license_kind`: `own`, `cc` or `press-kit`.
- Project guide: Notion, "Polo - polo.cold.fyi (READ FIRST)".
