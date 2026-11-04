# polo.cold.fyi - design tokens

Mood (Nov 2026 refresh): golden hour on the polo field. A pastel desert sunset (sky blue to lilac to pink to orange), mountains, fan palms and a Ferris wheel that turns very slowly, stencil numerals like a scoreboard, a lineup-poster chapter list, and wristband stripes for Richard's road photos. Night mode is the field after dark: indigo sky, stars, the wheel's cars glowing. All of it is drawn in code (build.py, scene_svg) - never the festival's logo, fonts or artwork, and the 'not affiliated' line stays in the footer.

Palette and scene colours are CSS variables at the top of CSS in build.py (--sunset, --pink, --lilac, --sun, --sky, --turf, sky stops --s0..--s4, --mtn1/2, --ground, --palm, --wheel). --dusk is the signature gradient. The table below is the original 2026 palette, kept for reference.

Light (default)            Dark ("Night polo")
--paper  #f3ead8           #14110d
--paper2 #e9dcc2           #1f1a14
--ink    #1d1a16           #efe6d4
--muted  #6b6152           #a89c86
--turf   #2f5d3a           #6fa57c
--sunset #d9572b           #ef7a4c
--dust   #c9a46a           #c9a46a
--line   rgba(29,26,22,.14)   rgba(239,230,212,.14)

Fonts (self-hosted in /fonts, SIL OFL): Big Shoulders Stencil Display 800/900 (display, chapter numbers, scoreboard), Source Serif 4 400/600/italic (body), JetBrains Mono 400/600 (data, labels, footnote numbers).
Signature details: a thin sunset/turf double rule under the masthead (like a polo-club ribbon), chapter numbers as stencil "chukker" numerals, lore boxes on paper2 with a dust-colored left rule, field boxes (Richard) with a turf left rule and mono label.
Footer: "made with <3 in boston" + "Independent. Not affiliated with Coachella, Goldenvoice or AEG." + Third Polar Arch link.
