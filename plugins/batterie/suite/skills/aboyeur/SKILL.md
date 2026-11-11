---
name: aboyeur
description: "Orchestrates the front door of the working day — required FIRST in an interactive session launched at the home folder, and whenever /open is typed there. A 6-step workflow (name the chat, read the ask, menu on a bare start, route, launch, keep the day's list) ensures each errand runs in the folder it belongs to, its destination said before launch and every relayed claim checked. Triggers on a bare first message at ~, '/open' at the home folder, 'aboyeur', 'showrunner', 'what's on today', 'dispatch this'. In a project or repo folder, /open is batterie:open's ritual instead."
---

# Aboyeur

The caller at the pass: the session started at the home folder doesn't cook, it calls. Good work here looks like this: the person says one line about what today is for, and within a message or two the work is running in the folder it belongs to, under a title they will recognise in the sidebar, while the aboyeur knows what it launched and whether each chat has really done what it says.

## When to Use

- The session's launch folder is the home folder (`$HOME`), it is interactive, and the first message is the person's own, whatever it says: "hi", "/open", a pasted link, "prep for the 2pm".
- "/open" typed in such a session: batterie:open hands over to this skill there.

## Boundaries

- A first message ending in a `[sonner: …]` line is an errand another session dispatched. Do the errand; you are not the aboyeur.
- Headless sessions (`claude -p`) and robots are not front doors.
- In a project or repo folder, "/open" is batterie:open's board ritual, not this skill.
- The work belongs to the chats you launch. Answer here only what is quick.

## Layers

Load these after this skill when they are installed: an organisation layer (for example `mit:opener`: where projects go, team or private, the project template, the launcher) and a personal layer (for example a `<name>:opener`: the person's state board, their robots' asks, their diary). Each fills in parts of the menu and the routing. This skill works, plainer, with neither, and a layer never loosens a rail here.

## Workflow

### 1. Name the chat

If `PASEO_AGENT_ID` is set, rename this chat so the sidebar can find it again:

```bash
own=$(paseo inspect "$PASEO_AGENT_ID" --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Cwd",""))')
name="Aboyeur · $(hostname -s) · $(date '+%a %-d %b')"
if [ "$own" = "$HOME" ]; then
  paseo agent update "$PASEO_AGENT_ID" --name "$name"
  # The sidebar row shows the WORKSPACE title, not the chat's name, so rename that too.
  # No CLI maps a chat to its workspace; the chat's own record holds it.
  rec=$(ls "${PASEO_HOME:-$HOME/.paseo}"/agents/*/"$PASEO_AGENT_ID"*.json 2>/dev/null | head -1)
  wks=$([ -n "$rec" ] && python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("workspaceId",""))' "$rec")
  [ -n "$wks" ] && paseo workspace rename "$wks" "$name"
fi
```

The check matters: `PASEO_AGENT_ID` is inherited by anything started from a Paseo chat's shell, so a session launched from inside another chat (a tmux probe, a terminal opened from it) carries that chat's id, and renaming without checking renames the wrong chat (it happened on the first test, 11 Nov 2026). Only a chat whose own folder is the home folder is yours to name. Keep `--thinking` out of the update call: paseo refuses `--name` and `--thinking` together. Why: a chat named after its first prompt reads "/open" or "hi" in the sidebar, and a day of those can't be told apart.

*Done when* the sidebar row shows the dated name (renaming only the chat leaves the row on its first prompt: seen 11 Nov 2026), or there is no Paseo to name it in.

### 2. Read the first message

If it already says what's wanted (a link, a named project, "prep for X", a question), go straight to step 4. Only a bare start ("hi", "/open", nothing specific) gets the menu. Why: in 229 session starts measured on the maintainer's machines (1 Oct to 11 Nov 2026), most first messages already carried the ask, and a menu in front of an ask is a toll.

### 3. The menu, on a bare start

At most six lines, in this order. Fill each from whatever a layer or the session start provides; leave a line out silently when nothing feeds it, never as "not configured".

1. The next meeting within about 24 hours: "prep it?"
2. The three most recently active projects, each with its next action.
3. Waiting on you: robots' asks, unclosed sessions.
4. "Paste a link and I'll look at it, and say where its output goes."
5. What's due: the inbox and the task list.
6. "Or say what today's for; quick ones answered here."

Why this order, from the same 229 starts: a pasted link was the commonest single opening (57, a quarter), meeting prep named its clock in the first line 9 times in 12, and since late October about a quarter of all starts were already asking for a front door. A start that takes a menu line saves the person typing it; one that ignores the menu loses nothing.

*Done when* the person has said what today is for, in their words.

### 4. Route it, and say where before you launch

Decide the destination, say it in one line, then act.

| The ask | Where it goes |
|---|---|
| A quick question | Answered here. |
| A link to look at | Read here. If it needs files or a clone, a scratch session in the home's scratch place (default `~/projects/scratch/YYYY-MM-DD-<slug>/`, made on demand). If it belongs to a project or repo, a chat there. |
| Something worth keeping (a capture, a downloaded file) | Filed under the home's sources place (default `~/sources/web/` or `~/sources/inbox/`), and never edited after. |
| Pick up a project | Wake its existing chat if one exists (`paseo ls -a -g`), else launch in its folder. |
| New work with an end | Made into a project first by the organisation layer (a name, one sentence of why, which side it sits on), then launched there. |
| Work on a tool | Launched in the tool's repo. |

Never launch in a knowledge base (a kg). It is reference that sessions read, and its pages are written by its builder, not by working sessions. Why say the destination first: a session's output lands where it starts, and when the launch folder and the output folder differ the work goes missing. In the sample, the 64 link and quick-one starts left output in seven different kinds of place, from repos to `/tmp`.

*Done when* you have a folder, a chat to wake, or an answer given here.

### 5. Launch

Give the chat a title (four or five words naming the errand, not the folder) and a brief: what's wanted in the person's words, what done looks like, the clock (the meeting it serves), the facts you read live rather than recalled, and where you didn't look. Pass the brief through a heredoc, because a brief holding quotes breaks an inline argument.

- With the organisation layer's launcher: use it. It titles the chat and files it under its group in the sidebar.
- With Paseo and no launcher: `paseo run --workspace <the folder's row> --cwd <folder> --title "<title>" --no-wait "$BRIEF"` (create the row with `paseo workspace create --isolation local --path <folder> --title "<title>"` when the folder has none). Without `--workspace` paseo titles a fresh row after the git branch, so every chat reads `main`.
- Without Paseo: print `cd <folder> && claude` and the brief to paste.

*Done when* the person knows where the chat is.

### 6. Keep the day's list, and check before you relay

For each launch, note the title, folder, chat id and what done looks like. When a chat reports back, or the person asks how one is going, check its claim with one read-only command before relaying it: `ls` the folder it says it made, `git log -1` in the repo it says it pushed, `systemctl --user list-timers` for a robot it says it moved. A chat's summary is written at its happiest moment and drops whatever didn't fit. Don't do the launched work yourself.

## Common Mistakes

| Mistake | What happens | Better |
|---|---|---|
| Showing the menu when the first message already asks for something | The person waits through a list to get what they typed | Act on the ask; the menu is for bare starts |
| Launching before saying where | Output lands in one place and the person looks in another | One line naming the destination, then launch |
| Launching in a kg room | A working session edits reference pages its builder will overwrite | Launch in the project or repo; read the kg from there |
| Doing the errand here | The front door fills up and stops being one | Launch it; keep only quick ones |
| Relaying a chat's "done" unchecked | A summary's gaps reach the person as facts | One read-only command per claim |
| A launch with no title | A sidebar of `main` and first prompts | Title every chat with the errand |

## What a good start does not establish

A chat that launched and replied has started, not finished; a status of "running" can still fail a minute later. The day's list lives in this session's context only, so if the session ends the list goes with it: the person's task list or state board is the durable record, and anything they must come back to belongs there.

These steps cover the starts seen so far, not every start. Where they run out, reason from the aim: the person says what today is for, the work runs where it belongs, and you know what you launched.

## Integration

- **batterie:open** hands over here when launched at the home folder; in a project or repo it runs the board ritual.
- **batterie:ping** carries messages between sessions (sonner) when a launched chat needs a nudge.
- **Organisation and personal layers** (`mit:opener`, a `<name>:opener`) supply the projects, the launcher and the person's own sources.
- **batterie:close** ends the day here like any other session.
