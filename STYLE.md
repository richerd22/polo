# polo.cold.fyi - writing style

The house format of the cold.fyi deep dives (showfile, tickets, works), with its own voice: the smart friend who has been four times, read everything, and still thinks it's funny that the festival happens at a polo club that stopped playing polo.

## Voice

- Entertaining first, accurate always. Specific beats general: a number, a name, a date, a quote.
- Dry, warm, a little amused. Never snarky about fans, never cynical about the festival. Let it have its wins.
- Short sentences. Plain words. Explain any jargon the first time in a clause, not a footnote.
- Second person sparingly ("you've stood in this line"). Never "we" for the festival.
- No hype words: amazing, iconic, legendary, insane, epic, game-changing, unforgettable, must-see. Show it instead.
- No filler openers ("When it comes to...", "In today's world..."). Start with the most interesting true thing.
- Spaced hyphens " - " for breaks. Never em dashes or en dashes.
- Numbers: digits for 10 and up, money as $350K / $114.6M, years as numerals.
- Independent: never imply affiliation with Coachella, Goldenvoice or AEG. "The festival", "Goldenvoice" - not "we" or "our".

## Truth rules

- Every factual claim gets a footnote. A paragraph with three facts from two sources gets two footnotes.
- Only cite sources that were actually opened (by you now, or marked as read in the research files). If a research note says "headline only", "search-only", "not opened", "Wikipedia only" or "unconfirmed", either open the source yourself with WebFetch and confirm it, find a better source, or attribute and soften it ("Wikipedia's figures put it at..."). Never state it flat.
- Where sources disagree, say so in the text ("$300K, according to the 2015 documentary; $350K plus travel, according to Goldenvoice's own film").
- Lore: the legends stay in, told as legends, in a lore box (below). "The legend goes..." with who says it. Then the documented version, without sneering. Only call something wrong if it's a date or number error that matters.
- "Reported by attendees" for Reddit / TikTok / X claims not confirmed elsewhere.
- Never describe where Richard lives, and never mention his building or the Boston stream's location.
- Quotes: under 25 words each, attributed, footnoted. No long passages from articles.

## Format (content/NN-slug.md)

```
---
n: 6
slug: pyramid
title: Daft Punk and the pyramid
short: One paragraph, 2-4 sentences, the whole chapter in miniature. Shown in a box at the top and in the index.
---

Opening paragraph, no heading. Hook with the best true thing.

## Subhead in sentence case

Paragraphs. Lists only when the content is a list.

> A short attributed quote.[^dp-ringer]

:::lore The 40,000
The legend goes that 40,000 people tried to get into a 10,000-capacity tent. That number comes from their manager, in the 2015 documentary.[^dp-unchained] Nobody counted at the gate. Nobody had to.
:::

:::field Richard
First-person aside from Richard, only where he supplied it.
:::

[^dp-ringer]: The Ringer - "Title of the piece" - 2021-04-29 - https://...
[^dp-unchained]: Daft Punk Unchained (documentary, dir. Hervé Martin-Delpierre) - 2015
```

- Footnote ids: a short chapter prefix plus a word (`dp-ringer`, `vmt-kesq22`). Unique within the chapter. The build numbers them globally.
- Footnote definition format: `Publication - "Title" - YYYY-MM-DD (or YYYY) - URL`. URL required unless it's a film, book or print source.
- Headings: `##` only (and `###` sparingly). Sentence case.
- Inline: `**bold**` rarely, `*italics*` for titles of films, albums and books, `[text](url)` for links in the text (rare - prefer footnotes).
- Boxes: `:::lore Title` ... `:::` and `:::field Richard` ... `:::`, and `:::numbers Title` ... `:::` for a small fact panel (a bulleted list of key figures, each footnoted).
- Length: 1,500-3,000 words per chapter. Long is fine if every paragraph earns it.
- End each chapter with a `## Still open` section only if there are real open questions worth inviting readers on (1-4 bullets).
