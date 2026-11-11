# Brief: Coachella past lineups (for "played before / debut" on polo.cold.fyi)

Goal: for each Coachella edition in your assigned years, collect the FULL list of performing acts (not just headliners) from the most complete reliable source you can open, so we can tell which 2027 acts have played Coachella before and which are debuts.

Sources, in order of preference:
1. Wikipedia pages that list a year's full lineup (search e.g. "Coachella 2014 lineup wikipedia", "List of Coachella Valley Music and Arts Festival lineups").
2. setlist.fm festival pages for that Coachella year (they list every artist with a setlist).
3. Clashfinder (clashfinder.com) Coachella year pages, or contemporaneous press that prints the full poster text (Pitchfork, Billboard, Consequence, Stereogum, Rolling Stone, LA Times, Desert Sun).
Prefer one complete source per year; add a second for cross-checking where cheap. Note what each source covers (full poster? only acts with setlists? both weekends?).

FETCH RULE: only WebFetch URLs that appeared in your own WebSearch results or inside a page you already fetched. Never fetch a URL typed from memory - it triggers a permission prompt for a sleeping user. Search first.
Budget: at most 25 WebSearch calls. If a page fails, try one alternative, then move on and record the gap.

Output: write /home/claude/polo/research/lineups/past-<TAG>.json as
{"years": {"2014": {"sources": [{"name": "...", "url": "...", "covers": "full poster | setlist.fm only | partial"}], "acts": ["Act as printed", ...], "notes": "..."}, ...}, "gaps": ["..."]}
- acts: every performing act you found for that year, one string each, spelled as the source prints it. Keep b2b/x pairings as printed. Do not invent or fill from memory - only names you saw on the page you opened.
- If a year had no festival (2020, 2021) record that in notes with acts [].
Validate the JSON with python3. Final message: 2 lines - years covered with act counts, and gaps.
