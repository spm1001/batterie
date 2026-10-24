# Topic mode — `/open on X`

A topic open ends with the session standing where a subject lives, holding what was last known about it, with the board ritual run on the board that owns that subject. It does not start by running the ritual on whatever board the session happened to launch on.

**Why this exists (census, 28 Sep 2026, `docs/open-topic-orient-2026-09-28.md`).** Topic asks went from about 3 a month (December to June) to about 18 a month in September, from 2% of Sameer's `/open`s to 20%. The phrase "/open on X" was first used as a request on 10 Sep. Most topic asks are launched in stores that hold many strands (`~/notes`, mit-kg) or from `~`, so the launch directory no longer names the work. The words after `/open` do. In 10 of the 13 '/open on X' requests on tube, the Claude ran the whole board ritual first and hunted second, and at least twice the sweep went on handoffs unrelated to the topic.

## Telling a topic from a task

Syntax settles only two cases. Nothing after `/open` means the plain ritual. First words (minus a leading "on") that are a path or match exactly one repo mean roaming. Everything else is judged on meaning, because the usual form is `/open and <request>`, and the "and" is shared by tasks and topics alike. In the census, 37 of the 251 requests that open with a joining word ("and", "then", "please") or a dash were topics.

Ask one question: **does the request need material on a subject found first, beyond the board you launched on?** It usually does when the request:

- picks up a thread by what it was about ("the Tube work", "the budget story", "the work we were doing yesterday on X");
- says the thing is somewhere ("somewhere we did…", "dig it out", "can't find");
- asks to read up, limber up or warm up on something, or says "on X".

A task on material that is here or handed over (an email link, a file path, a pasted report), or a named card, is the plain ritual followed by the task, as before. The same reading applies when "/open" appears mid-sentence ("can you /open on the budget work please?"). That form never arrives as a slash command.

## The moves

1. **Find where it lives, cheapest index first, and stop when one home clearly wins.**
   1. The launch repo's own map: `rooms.md`, or mit-kg's `index.md`, whose "Holds … Not … →" lines are routing clauses.
   2. Board items across the machine (titles and briefs). `skills/bon-review/scripts/audit_survey.py` already reads every board.
   3. Handoff ledgers: each `handoffs/LEDGER.md` line carries a handoff's purpose and card IDs.
   4. Past sessions: `deglacer --search "X"`, ranked, across all history. Half the census's topic asks pointed back at earlier sessions. Read the scope line, because the index can be stale.
   5. Gmail and Drive through mise, when the ask names mail, a document or a person, or when the local results are thin.
   6. Todoist through accomplis, only when named.

   This list is a floor, not a fence. If the topic plainly lives somewhere else, go there.
2. **Show the candidates in a few lines.** Ask only when two homes tie. Guessing between homes is barred for the same reason guessing between repos is: orienting on the wrong board fails silently.
3. **Read in at the home:** the room's CLAUDE.md and understanding.md, and the handoffs, record pages and board items *that mention the topic*.
4. **Run the ritual on the home board, scoped to the topic.** Sweep the unticked handoffs that touch the topic. Name the rest in one line ("4 other unticked handoffs here, not about X, left for the next plain /open"). They stay unticked, so nothing is dropped, and the next plain `/open` processes them.
   **A home with its own rules wins wherever they differ from bon's ritual.** mit-kg is the live case, and its CLAUDE.md is the authority: there is no `understanding.md` there by design, so durable knowledge from a handoff lands on the room's own pages (a Record addendum, the register's State, a Decision page); a handoff is marked processed by stamping `swept: { by, at }` in its frontmatter and regenerating the ledger (`kg gen ledger`), never by hand-ticking `LEDGER.md`, which the next render would undo; and `kg brief <room>` is the on-entry read, before step 3's reading. A sweep with nowhere to write does not happen (the 6 Oct atelier session found eight gcp-estate handoffs unswept across three sessions for exactly that reason), so name where each handoff's knowledge went.
5. **Declare the orientation on the home** (the breadcrumb from SKILL.md's Present Hierarchy step), so `/close` files where the work was done. If the home is another repo, SKILL.md's roaming list applies to it.

## What to hand back

- **Where X lives:** the home, then the secondary places, each with its latest date.
- **Where we got to:** the newest state, from the latest handoff, record or session touching X, with dates.
- **Open threads:** matching board items, waiting-fors, and emails still waiting for a reply.
- **Searched and found nothing, or didn't search:** without this line, an empty result and an unlooked-at source read the same.
- Then the user's own request, if one came with the open.

This covers the shapes seen in the census, not every shape. Where it runs out, reason from the aim: stand where the subject lives, and run the ritual there.
