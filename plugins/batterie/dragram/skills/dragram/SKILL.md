---
name: dragram
description: Sets up and runs the dragram drag-to-edit diagram workbench — load BEFORE building a data-flow or box-and-arrow diagram a person will want to rearrange by hand, or when someone asks to edit, move boxes in, or comment on a dragram .html diagram. Four steps (copy the kit into the diagram's folder, serve it, the person drags in the browser while positions save to the file, Claude reads the file and checks it with shot.py) ensure the human and Claude edit one file instead of trading screenshots. Triggers on 'diagram I can drag', 'data flow diagram', 'DFD', 'move the boxes', 'dragram', 'rearrange this diagram'. For a one-off static chart or SVG, use the diagram skill instead.
---

# dragram — diagrams the person drags and Claude reads

Good work here looks like this: the person drags boxes in a browser, every drop lands in the `.html` file, and Claude reads that file to see exactly where things now sit. Neither side redraws what the other did. The `.html` file is the one shared artefact: placement in each block's inline `left/top`, topology in a JSON list of edges, arrows drawn from live box geometry so they follow every drag.

## When to Use

- Building a data-flow, architecture or process diagram that a person will rearrange: legal data flows, pipelines, who-sends-what-to-whom.
- Someone opens an existing dragram `.html` and asks for changes, or has left comments in it.

## Boundaries

- A static chart, a Venn diagram or a one-off SVG: the `diagram` skill.
- Data charts: the `dataviz` skill.

## Where the kit is

This skill's base directory is `<kit>/skills/dragram/`, so the kit is two levels up from it: `drag.js`, `grammar.css`, `serve.py`, `shot.py` and `example.html` sit there.

## Workflow

**1. Put the kit beside the diagram.** In the folder that will hold the diagrams (one folder per diagram set), copy `drag.js`, `grammar.css`, `serve.py`, `shot.py` and `example.html` from the kit. They work from their own folder, so a copy is a working workbench. A diagram loads `drag.js` by relative path, which is why the files have to sit together. Update by copying again when the plugin updates.

**2. Write the diagram.** Start from `example.html`. Each block is a `.node` with an `id` and inline `style="left:…px; top:…px; width:…px"`; arrows are `{ "from": id, "to": id }` entries in the `<script type="application/json" id="edges">` list. Coordinates sit on a 20px grid. When one block is meant to line up with another, write the tie instead of computing pixels: `data-align-x="center:<other-id>.center"` (x lines `left|center|right`, y lines `top|middle|bottom`).

**3. Serve it; the person drags.** `uv run serve.py` in that folder (port 8731, `DRAGRAM_PORT` to change it). The person opens `http://localhost:8731/<file>.html?edit`, drags boxes, drags an edge to resize, and presses `c` to point at a box and leave a comment for Claude. Every drop writes to the file. Without `?edit` the page is a clean render with no editor chrome.

**4. Read the file, then check it.** After the person's edits, read the `.html` for the new positions, then `uv run shot.py <file> --state`. It prints a verdict and invariants (every arrow drawn, ties hold, content fits its box, open comments) computed in a real browser, plus every block's computed box. `uv run shot.py <file> --png` writes a picture for a visual check. `uv run shot.py --comments` lists the person's open comments. To resolve one, make the change and delete that element's `data-comment` attribute; the edit is the answer.

Success: `shot.py --state` says PASS, and the person sees their moves still where they put them after a reload.

## Common Mistakes

| Symptom | Why | Do |
|---|---|---|
| Arrows missing, page renders bare | `drag.js` isn't beside the `.html` | Copy the kit into that folder (step 1) |
| Drags don't save | Page opened as a file, or without `?edit` | Open through `serve.py` with `?edit` |
| A box snaps back after Claude edited its `left`/`top` | It carries a `data-align-*` tie, and the tie wins over hand-written pixels | When Claude moves a box, change or delete the tie, not the pixels. Ties don't trap the person: a drag updates or clears them, so leave meant ties in |
| The open tab banner says the file changed on disk | Claude edited the file while the tab was open | Press `r` in the tab to reload, keeping zoom |
| `shot.py` and the person's screen disagree by a few px | Fonts differ between machines | Trust `shot.py --state` on the machine that renders the deliverable |

This covers the common cases, not every case; the repo's CLAUDE.md holds the full model (resize rules, regroup by dragging into a keyline, save versioning). Reason from the whys above.
