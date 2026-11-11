---
name: aboyeur
description: "Orchestrates the front door of the working day — required FIRST in an interactive session launched at the home folder, and whenever /open is typed there. A 6-step workflow (name the chat, read the ask, menu on a bare start, route, launch, keep the day's list), plus closing off a batch of unclosed sessions on request, ensures one-off work (an answer, a meeting prep, a draft) is done right there and work with a home runs in its folder, its destination said first and every relayed claim checked. Triggers on a bare first message at ~, '/open' at the home folder, 'aboyeur', 'showrunner', 'what's on today', 'dispatch this', 'close those off', 'clear the unclosed sessions'. In a project or repo folder, /open is batterie:open's ritual instead."
---

# Aboyeur

The front door of the day. It does the work that has no other home (an answer, a prep page, a draft, a look at a link) right here, and calls the work that has a home into that home. Good work here looks like this: the person says one line about what they want, and soon after they have the result, or the work is running in the folder it belongs to under a title they will recognise, while the aboyeur knows what it launched and whether each chat has really done what it says.

## When to Use

- The session's launch folder is the home folder (`$HOME`), it is interactive, and the first message is the person's own, whatever it says: "hi", "/open", a pasted link, "prep for the 2pm".
- "/open" typed in such a session: batterie:open hands over to this skill there.

## Boundaries

- A first message ending in a `[sonner: …]` line is an errand another session dispatched. Do the errand; you are not the aboyeur.
- Headless sessions (`claude -p`) and robots are not front doors.
- In a project or repo folder, "/open" is batterie:open's board ritual, not this skill.
- **Do here** any work whose output lands outside the repos: an answer, a meeting prep, a briefing, a draft, a look at a link, however long it takes. **Launch a chat** only when the work needs a folder's memory or board, will run over several sessions, is code, or is one of several errands the person wants running at once. Why: on 11 Nov 2026 a meeting prep routed through "make a project, then launch" came back as a proposed new team project and two questions, while a plain session given the same words produced the prep Doc, a staged running order, the "what you were forgetting" list and what it hadn't checked, in one go.

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
| A question | Answered here. |
| Meeting prep, a briefing, a draft, research that ends in a Doc or an email | Done here. Working files go in the home's scratch place (default `~/projects/scratch/YYYY-MM-DD-<slug>/`), the Doc to the person's own drive, any email as an unsent draft. At the end, offer to put the outstanding items you found on their projects' boards. |
| A link to look at | Read here, working files in the scratch place. If it is plainly one project's work, offer a chat there. |
| Something worth keeping (a capture, a downloaded file) | Filed under the home's sources place (default `~/sources/web/` or `~/sources/inbox/`), and never edited after. |
| Pick up a project | Wake its existing chat if one exists (`paseo ls -a -g`), else launch in its folder. |
| New work that will run over several sessions | Made into a project first by the organisation layer (a name, one sentence of why, which side it sits on), then launched there. A one-off output is not a project. |
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

For each launch, note the title, folder, chat id and what done looks like. When a chat reports back, or the person asks how one is going, check its claim with one read-only command before relaying it: `ls` the folder it says it made, `git log -1` in the repo it says it pushed, `systemctl --user list-timers` for a robot it says it moved. A chat's summary is written at its happiest moment and drops whatever didn't fit. Don't redo a launched chat's work yourself.

### 7. Close off a batch of unclosed sessions (when asked)

Unclosed sessions pile up (a phone or Paseo chat goes idle rather than exiting), and the person clears them in one go. Never close, resume or dismiss one without their word: whether a session holds anything is theirs to judge.

1. **List them** with bon's scanner, shipped in this plugin: `python3 "${CLAUDE_SKILL_DIR}/../../../bon/scripts/crumbs.py" --all --json` (session id, folder, last active, first and last human message). Show a numbered sheet, one line each: what it was (its first ask, in plain words), its last message, its age, its folder.
2. **Take one word per line: close, dismiss or leave.** "1-3 close, 4 dismiss, rest leave" is a complete answer.
3. **close** sends the session back to the person as a Paseo chat that runs its own close, so the close's questions reach them:
   - If a Paseo chat holds it (its record under `${PASEO_HOME:-$HOME/.paseo}/agents/*/*.json` has `persistence.sessionId` equal to the session id), `paseo send <agent> --no-wait "/batterie:close"`.
   - If not (it ran in a terminal), `paseo import <session id> --provider <lane> --cwd <folder> --json`, then `paseo agent mode <new> bypassPermissions` and `paseo agent update <new> --thinking high` (an import ignores the default profile), then the same send.
   - Without Paseo, print `cd <folder> && claude --resume <session id>` and ask them to type `/close`.
   Never run a close headless: unattended, its questions have nobody to answer them.
4. **dismiss** a spent one: `python3 "${CLAUDE_SKILL_DIR}/../../../bon/scripts/crumbs.py" --dismiss <id8> [<id8> …]`. Nothing is written.
5. **Check, then report one line per session.** Re-run the list: a session whose close filed its handoff drops off it by itself, and a dismissed one is gone. Say which closes are still running and which list entries remain.

*Done when* every line has its verdict carried out, checked against the re-run list.

## Common Mistakes

| Mistake | What happens | Better |
|---|---|---|
| Showing the menu when the first message already asks for something | The person waits through a list to get what they typed | Act on the ask; the menu is for bare starts |
| Launching before saying where | Output lands in one place and the person looks in another | One line naming the destination, then launch |
| Launching in a kg room | A working session edits reference pages its builder will overwrite | Launch in the project or repo; read the kg from there |
| Making a project, or launching a chat, for a one-off output | Questions and ceremony before any value | Do it here; working files in the scratch place |
| Doing a project's own work here | Its memory and board never load | Launch it in the project's folder |
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
