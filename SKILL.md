---
name: instagram-story-links
description: Use this skill whenever the user wants the outbound URLs hidden behind link stickers in Instagram Stories. Typical cases: an instagram.com/stories/... link is pasted with a request to get, grab, list, or open its links; they ask for "the links in this story/reel", "the URLs behind each sticker", or "the application links" from an account's stories; or they name an account and ask to pull its story links (job or internship postings, signups, products) to apply to, prefill, paste into a tracker, or catalog. It walks the whole reel in order and reports which stories have no link. Not for feed posts, reels, bios, highlights, captions, or downloading media. Requires Claude in Chrome (signed-in browser); the built-in browser hits a login wall.
---

# Instagram story reel link extractor

Link stickers are not in the page text. The real URL only appears in the accessibility tree
(`read_page`) after the sticker is clicked, as `https://l.instagram.com/?u=<encoded URL>&e=...`.
So the method is: open a story, click its sticker, `read_page`, decode `u=`, move on.

Speed comes from doing one fixed group of actions per story with no deliberation in between, and
from keeping the story **paused** while you click. Every wrong click in testing traced back to a story
that was still playing and auto-advanced (about every 5 seconds) between the screenshot and the click.

## Setup

1. Load the Chrome tools in a single ToolSearch:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__tabs_close_mcp`
2. `tabs_context_mcp` with `createIfEmpty: true`; use that tab ID for everything.
3. Navigate to the story URL, wait ~3s. If a "View story" gate appears, click its center. Tell the user
   this marks the story as viewed by the account owner.
4. Click pause immediately.

## Batch item shapes

Inside `browser_batch`, every item is `{"name": ..., "input": {..., "tabId": N}}`.
`read_page` is its own item name, not a `computer` action:

```
{"name":"computer","input":{"action":"left_click","coordinate":[744,550],"tabId":N,"action_summary":"Opens the link sticker"}}
{"name":"read_page","input":{"tabId":N,"filter":"interactive"}}
```

A `read_page` written as `{"name":"computer","input":{"action":"read_page"}}` fails, and that failure
made one test run do every read outside the batch. Likewise `wait` is a `computer` action
(`{"name":"computer","input":{"action":"wait","duration":1,"tabId":N}}`), not its own item name.

## Coordinates

Click coordinates use the frame the screenshot reports (a 0.5-scale screenshot reported `1492x812`
while the page viewport was 1728x941). Calibrate once from a screenshot:

| Control | Position (1492x812 frame) |
|---|---|
| Pause / play | (903, 60). (900, 60) sometimes hit the "..." menu |
| Next arrow | (988, 406) |
| Previous arrow | (502, 406) |
| Link sticker | x 744-760 (its center); y anywhere 418-655 and different per story |

Click the sticker's center, not its edge. Wide stickers overlap the next arrow's zone, and an edge
click advances the story.

The frame size can change mid-run (one run saw 1456x840, then 1492x812, with the viewport resizing),
and then the pause button and next arrow move. If a click misses or a story is skipped, take a fresh
screenshot and re-measure before continuing. Story IDs ascend in reel order, so a skipped story shows
up as a gap in the sequence; step back with the previous arrow and redo it.

## Per-story group

```
click sticker -> read_page (interactive) -> click next -> wait 1 -> click pause -> screenshot (scale 0.4)
```

The trailing screenshot shows the story you are now on, so it gives you the next sticker's y. One
group per `browser_batch` call is the reliable default: a sticker's y varies from 418 to 655, so each
story's aim comes from the screenshot of the one before. Measured first-click hit rate when aiming from a
paused 0.4 screenshot: 20 of 21. With a fixed guessed y it was about 1 in 3.

To batch more than one story per call, only chain groups when the stories look like the same template
(same job site or same page layout), aim each at the previous story's sticker y, and drop the screenshot
for all but the last group. Grow the batch while hits stay consistent; shrink it at the first miss or
skipped story ID. This is untested beyond 2-3 groups.

Every story gets a line in the output, including ones you did not click. Text-only stories, chat
screenshots, and Q&A or poll stickers are recorded as "no link", but you still advance through them. Two
test runs dropped chat-screenshot stories from the list and under-counted the reel.

## Attribute links to the right story

The tab URL in each batch result carries a story ID, but it is the ID *after* the batch's last click.
So the ID you saw at the end of the previous call is the story the next call's sticker click acts on.
Write down `ID -> link` as you go. If `read_page` returns a link that matches the previous story, the
click landed after an auto-advance: go back with the previous arrow, pause, and redo it.

## Misses

A miss is a `read_page` with no `l.instagram.com` link. First check the screenshot: if a link sticker
(link icon plus a domain) is visible, click its center once more and `read_page` again (the first click
on a freshly advanced story sometimes does nothing). If none is visible, it is "no link". Do not navigate back
to the story URL to redo a story, because the "View story" gate returns; use the previous arrow.

## Decode

Do not decode by hand; one test run silently dropped `utm_source`. Pass the raw hrefs through the
script, for example:

```
python3 -I scripts/decode_links.py <<'EOF'
<paste the l.instagram.com hrefs from read_page>
EOF
```

It URL-decodes `u=` and drops `fbclid`. Keep the destination's own parameters (`utm_source`,
`utm_id`, `gh_jid`, ...). Keep each link's original scheme (`http` or `https`).

## End of the reel and verification

The reel ends when the viewer closes to the home feed. The last story's first "next" click may do
nothing; a second click exits. Do not click again after that: a stray click on the home feed opened an
unrelated tab in one run. Check the count against the progress bar
(zoom on roughly x 500-960, y 20-50) or against the ID sequence, since the segments can be hard to count
when there are 30+.

## Output

One line per story, in reel order: `Story name: full URL` or `Story name: no link`. Close the tab you
opened when done.

## Pitfalls

- Do not click "Visit link" in the tooltip; it opens a new tab and the URL is already in `read_page`.
- Keep clicks inside the viewer; clicks outside close the reel.
- Arrow keys stop working after sticker clicks; use on-screen arrows.
- `find` and `get_page_text` do not expose sticker links. Page scripts for story data are blocked.
- Other agents may share the Chrome window; only use and close your own tab.
- Layout can change; if clicks miss, recalibrate from a screenshot.
