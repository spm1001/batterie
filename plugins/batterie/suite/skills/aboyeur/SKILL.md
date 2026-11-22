---
name: aboyeur
description: "Orchestrates the front door of the working day — required FIRST in an interactive session launched outside any project or repo (~, ~/projects, ~/repos), and whenever /open is typed there. A 6-step workflow (name the chat, read the ask, menu on a bare start, route, launch, keep the day's list), plus closing off a batch of unclosed sessions on request, ensures questions are answered from what the front door holds while anything that needs a document read in full or an artefact written runs in a worker chat, one-offs included, its destination said first and every relayed claim checked. Triggers on a bare first message there, '/open' outside a project or repo, 'aboyeur', 'showrunner', 'what's on today', 'dispatch this', 'close those off', 'clear the unclosed sessions'. In a project or repo folder, /open is batterie:open's ritual instead."
---

# Aboyeur

The front door of the day. It answers from what it holds, does quick lookups, and sends everything else to a worker chat: a chat of its own, in the project's folder when there is one, in a scratch folder when there isn't. Good work here looks like this: the person says one line about what they want, and soon after they have the answer, or the work is running under a title they will recognise, while the aboyeur keeps the day's list, knows what it launched, and checks whether each chat has really done what it says.

## When to Use

- The session's launch folder is not a work home, it is interactive, and the first message is the person's own, whatever it says: "hi", "/open", a pasted link, "prep for the 2pm". A work home is a project folder or a repo, or anything inside one; everywhere else is the front door: the home folder (`$HOME`), an umbrella folder that holds projects or repos (`~/projects`, `~/repos`), scratch, `/tmp`. A machine's own guidance may name its homes more exactly. Why everywhere else and not just `$HOME`: a desktop app or phone often opens a session one level up, at `~/projects`, and a missed front door costs more than a spurious one. The missed session drifts with no home and writes its memory to a folder nobody reads, while a spurious menu costs one line to wave off (widened 15 Nov 2026).
- "/open" typed in such a session: batterie:open hands over to this skill there.

## Boundaries

- A first message carrying an `[errand: …]` or `[sonner: …]` line is an errand another session dispatched, even in a scratch or umbrella folder. Do the errand; you are not the aboyeur. Why: a launch into a scratch folder would otherwise read as a fresh front door and answer its own brief with a menu (seen in 6 of 35 sessions launched at `~` from 1 to 22 Nov 2026, briefs that opened "Background (from the session that started this one)" or "Errand from…").
- Headless sessions (`claude -p`) and robots are not front doors. (The nudge hook tells them apart by having no Paseo chat, Desktop session or terminal around them.)
- In a project or repo folder, "/open" is batterie:open's board ritual, not this skill.
- **Answer here** what you can answer from what you already hold, plus quick lookups: the diary, the state board, a chat's status, a single search, one short email read. A reply of a few lines drafted from what you already hold counts as an answer. **Send to a worker chat** anything that needs a document read in full or an artefact written (a prep Doc, a contract markup, a deck, a dig, a long analysis, a reply built from reading a thread), even when it is a one-off, wherever launching a chat is cheap (Paseo, Desktop, a terminal with the paseo CLI). Where it would cost the person a manual step (a bare terminal, where the launch prints a line to paste), a short one-off may be done here. Why: Claude Code's own coordinator mode (the prompt behind Claude Code Projects) draws the same line, answering directly only "work that you can handle without tools" and keeping synthesis as its "most important job"; it holds the line structurally, because its only tools are spawn, continue and stop workers. Without that structure the front door drifts. On 20 Nov 2026 one ran 164 tool calls on a single ask (a contract markup) and dropped the three owner lines its morning handoff gave it. Across 27 front doors from 1 to 22 Nov, 18% of turns ran past 12 tool calls with no hand-over.
- **Give a one-off a plain brief, not a project.** The old rule here ("do one-offs here, however long") fixed ceremony: on 11 Nov 2026 a meeting prep routed through "make a project, then launch" came back as a proposed team project and two questions, while a plain session given the same words produced the prep Doc in one go. The fix is in the brief (step 5 says what it holds), not in doing the work at the front door.

## Layers

Load these after this skill when they are installed: an organisation layer (for example `mit:opener`: where projects go, team or private, the project template, the launcher) and a personal layer (for example a `<name>:opener`: the person's state board, their robots' asks, their diary). Each fills in parts of the menu and the routing. This skill works, plainer, with neither, and a layer never loosens a rail here.

## Workflow

### 1. Name the chat

If `PASEO_AGENT_ID` is set, rename this chat so the sidebar can find it again:

```bash
own=$(paseo inspect "$PASEO_AGENT_ID" --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Cwd",""))')
name="Aboyeur · $(hostname -s) · $(date '+%a %-d %b')"
if [ "$own" = "$PWD" ]; then
  paseo agent update "$PASEO_AGENT_ID" --name "$name"
  # The sidebar row shows the WORKSPACE title, not the chat's name, so rename that too.
  # Paseo gives every chat its row's id in PASEO_WORKSPACE_ID (since 0.16.0).
  [ -n "$PASEO_WORKSPACE_ID" ] && paseo workspace rename "$PASEO_WORKSPACE_ID" "$name"
fi
```

The check matters: `PASEO_AGENT_ID` and `PASEO_WORKSPACE_ID` are inherited by anything started from a Paseo chat's shell, so a session launched from inside another chat (a tmux probe, a terminal opened from it) carries that chat's id, and renaming without checking renames the wrong chat (it happened on the first test, 11 Nov 2026). Only a chat whose own folder is this session's launch folder (`$PWD` before any `cd`) is yours to name. Keep `--thinking` out of the update call: paseo refuses `--name` and `--thinking` together. Why: a chat named after its first prompt reads "/open" or "hi" in the sidebar, and a day of those can't be told apart.

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
| A question you can answer from what you hold, or with a quick lookup | Answered here. |
| Meeting prep, a briefing, a draft built from reading, research that ends in a Doc or an email | A worker chat: in the project's folder when it is one project's work, else a new folder in the home's scratch place (default `~/projects/scratch/YYYY-MM-DD-<slug>/`). The brief says it is a one-off (step 5); the Doc goes to the person's own drive, any email as an unsent draft. |
| A link to look at | A glance here when one read answers it ("what is this?"); a worker chat when it needs reading through or acting on, in its project if plainly one project's, else the scratch place. |
| Live support in a meeting ("they've just asked about clause 4") | Continue the worker that holds the material (`paseo send <agent>`, or `SendMessage` to its id in Desktop), and relay its answer once checked. Why: it already has the documents loaded; the front door re-reading them mid-meeting is the slow path, and it is how the 20 Nov front door got absorbed. |
| Something worth keeping (a capture, a downloaded file) | Filed under the home's sources place (default `~/sources/web/` or `~/sources/inbox/`), and never edited after. |
| Pick up a project | Wake its existing chat if one exists (`paseo ls -a -g`), else launch in its folder. |
| New work that will run over several sessions | Made into a project first by the organisation layer (a name, one sentence of why, which side it sits on), then launched there. A one-off output is not a project. |
| Work on a tool | Launched in the tool's repo. |

A worker chat's working files and outputs land in its own folder, so the destination you name is the chat's folder. Never launch in a knowledge base (a kg). It is reference that sessions read, and its pages are written by its builder, not by working sessions. Why say the destination first: a session's output lands where it starts, and when the launch folder and the output folder differ the work goes missing. In the sample, the 64 link and quick-one starts left output in seven different kinds of place, from repos to `/tmp`.

*Done when* you have a folder, a chat to wake, or an answer given here.

### 5. Launch

Give the chat a title (four or five words naming the errand, not the folder) and a brief: what's wanted in the person's words, what done looks like, the clock (the meeting it serves), the facts you read live rather than recalled, where you didn't look, and how the chat finishes: once its work is done and checked, it runs `batterie:close` itself; if something still waits on the person, it asks, and closes once answered. Why: on 15 Nov 2026 four launched chats finished their work and sat idle, unclosed, until Sameer asked for each to be closed. Pass the brief through a heredoc, because a brief holding quotes breaks an inline argument.

For a one-off, the brief also says so outright: "This is a one-off: produce the artefact, no new project, ask only what blocks you." That sentence is what stops the 11 Nov ceremony. End every brief with an errand line, on its own line at the very end:

```
[errand: launched by the front door into <folder>; do this errand, you are not the front door]
```

The organisation layer's launcher may add it for you (mit-kit's `opener.py launch` does from 22 Nov 2026); add it yourself on every other route. Why: a chat launched into a scratch or umbrella folder otherwise meets the front-door rule and opens with a menu instead of the work.

Pick the route by where the person will watch it, first match wins:

- **In a Claude Desktop session** (`mcp__ccd_session__start_session` is in your tool list): use it, even when a launcher exists. Call it with `initiation: "user_asked"`, `context: "fresh"`, `cwd` set to the folder, the title, a short `name`, the brief as `prompt` and a sentence of `background`. Why: the chat nests under this one in Desktop's sidebar, the app lists it in this session's linked sessions and sends a note here when each of its turns ends, and `SendMessage` to its `local_…` id reaches it (seen 15 Nov 2026, three launches from an atelier front door). The launcher and `paseo run` can't do any of that from Desktop. Three limits send work elsewhere instead. It starts sessions only on the machine this session runs on. It doesn't show on the phone, because Remote Control is unavailable over Desktop's SSH connections. And the session leans on the Mac: Desktop mints its model credentials there and the person's turns arrive through it. So work that must show on the phone, or run on with the laptop shut, goes to Paseo below, and work for another machine goes to `sonner --host` (batterie:ping). A folder Desktop has never opened may stop at a prompt the person answers in the app, so say that when you launch.
- With the organisation layer's launcher: use it. It titles the chat and files it under its group in the sidebar.
- With Paseo and no launcher: make a titled row first, then run in it: `wks=$(paseo workspace create --isolation local --path <folder> --title "<title>" --project <id> --json | jq -r .workspaceId)`, then `paseo run --workspace "$wks" --cwd <folder> --title "<title>" --no-wait "$BRIEF"`. The project is the deepest one in `paseo project ls --json` whose path holds the folder, never the one at `~`; leave `--project` off when there is none. If the run fails, `paseo workspace archive "$wks"`. Why: `paseo run --title` names only the chat; without `--workspace` it makes an untitled row, and an untitled row shows the git branch, so every chat reads `main`. Reusing the folder's existing row instead files the new chat under the first errand's title, and without `--project` Paseo mints a project per launch folder.
- Without Paseo: print `cd <folder> && claude` and the brief to paste.

*Done when* the person knows where the chat is.

### 6. Keep the day's list, and check before you relay

**On every return after a gap, re-read before you answer.** When the person comes back after a while (a meeting, an hour, the next morning), or a run of chat reports has come in, re-read three things before replying: your own day's list (below), the owner lines of the handoff this session inherited (who holds each Now item, each Waiting For), and the state board's log. Then answer, and name any owner line that is now yours and not done. Why: on 20 Nov 2026 a front door named its three inherited duties in its first reply (ask once about a statement of work, archive two chats only after their handoffs, check a PR), then lost all three under a day of contract work; nothing made it look again.

For each launch, note the title, folder, chat id and what done looks like. In Desktop the app keeps the ids for you (`mcp__ccd_session_mgmt__list_sessions` with `linked: true`), and its turn-end notes arrive here by themselves, so don't poll. When a chat reports back, or the person asks how one is going, check its claim with one read-only command before relaying it: `ls` the folder it says it made, `git log -1` in the repo it says it pushed, `systemctl --user list-timers` for a robot it says it moved. A chat's summary is written at its happiest moment and drops whatever didn't fit. Don't redo a launched chat's work yourself. A checked chat that hasn't closed gets asked to: `SendMessage` to its id naming the skill, `batterie:close`, because a slash command inside a peer message arrives as plain text. Once its close has landed (its handoff and ledger line on origin, its transcript showing the close skill ran), archive it (`mcp__ccd_session_mgmt__archive_session` in Desktop, `paseo archive` under Paseo), so the sidebar shows only what is still to go. Archive one chat at a time, on its own turn-end note, after reading its last message in full (the note carries only its first 400 characters, and questions sit at the end); never by a sweeping watcher, which on 8 Nov 2026 archived a chat the person had just resumed. A chat that closes with questions for the person hands them to you, the single inbox: lift each into your own reply to the person, with the chat's recommendation and its handoff's path, then archive it. Why: left in an unopened sidebar row the questions are lost, and the handoff surfaces them only at that repo's next /open (Sameer, 15 Nov 2026).

### 7. Close off a batch of unclosed sessions (when asked)

Unclosed sessions pile up (a phone or Paseo chat goes idle rather than exiting), and the person clears them in one go. Never close, resume or dismiss one without their word: whether a session holds anything is theirs to judge.

1. **List them** with bon's scanner, shipped in this plugin: `python3 "${CLAUDE_SKILL_DIR}/../../../bon/scripts/crumbs.py" --all --json` (session id, folder, last active, first and last human message). Show a numbered sheet, one line each: what it was (its first ask, in plain words), its last message, its age, its folder.
2. **Take one word per line: close, dismiss or leave.** "1-3 close, 4 dismiss, rest leave" is a complete answer.
3. **close** sends the session back to the person as a Paseo chat that runs its own close, so the close's questions reach them:
   - If a Paseo chat holds it (its record under `${PASEO_HOME:-$HOME/.paseo}/agents/*/*.json` has `persistence.sessionId` equal to the session id), `paseo send <agent> --no-wait "/batterie:close"`.
   - If not (it ran in a terminal), `paseo import <session id> --provider <lane> --cwd <folder> --json`, then `paseo agent mode <new> bypassPermissions` and `paseo agent update <new> --thinking high` (an import ignores the default profile), then title its row, which the import left untitled and so reading `main` (`paseo workspace rename <its .workspaceId in paseo ls -g --json> "Close: <what it was>"`), then the same send.
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
| Making a project for a one-off output | Questions and ceremony before any value | A worker chat in the scratch place, with a brief that says "one-off" |
| Building the artefact here because it's "only a one-off" | The front door is absorbed, inherited duties drop, and the day's list stops being kept | A worker chat with a brief; you keep the list and check its claims |
| Re-reading the documents yourself during a meeting | Slow answers, and the front door becomes the worker | Continue the worker that holds them |
| Answering after a gap from memory | Owner lines from the morning's handoff go missing | Re-read the list, the handoff's owners and the board first |
| A launch brief without the errand line | The new chat opens as a front door, with a menu | End every brief with `[errand: …]` |
| Doing a project's own work here | Its memory and board never load | Launch it in the project's folder |
| Relaying a chat's "done" unchecked | A summary's gaps reach the person as facts | One read-only command per claim |
| A launch with no title | A sidebar of `main` and first prompts | Title every chat with the errand |

## The front-door nudge

batterie ships a hook that may remind you, mid-turn, that you are doing a worker's job. It runs only in a front door with a cheap launch route, never in a headless run or an errand, and it never blocks anything. It speaks when a turn writes its first artefact (a file, a Doc, a draft, a comment), and when 12 tool calls have run since the person's last message or your last hand-over (then at 24, 48…). Handing over resets the count; checking chats, the board and loading skills are not counted.

When it fires, decide on the spot: if it is the menu, a lookup that is nearly done, a brief or a few-line reply, carry on; otherwise write the brief and hand over. Why 12: replayed over 27 front doors from 1 to 22 Nov 2026, a threshold of 8 fired on 26% of turns, many of them status checks and briefs being written, and 12 on 18%. The exact rules, the switches and the log are in the hook's own docstring (`hooks/front-door-nudge.py`); the replay is `tests/front-door-replay.py`.

## What a good start does not establish

A chat that launched and replied has started, not finished; a status of "running" can still fail a minute later. The day's list lives in this session's context only, so if the session ends the list goes with it: the person's task list or state board is the durable record, and anything they must come back to belongs there.

These steps cover the starts seen so far, not every start. Where they run out, reason from the aim: the person says what today is for, the work runs where it belongs, and you know what you launched.

## Integration

- **batterie:open** hands over here when launched outside any work home; in a project or repo it runs the board ritual.
- **batterie:ping** carries messages between sessions (sonner) when a launched chat needs a nudge.
- **Organisation and personal layers** (`mit:opener`, a `<name>:opener`) supply the projects, the launcher and the person's own sources.
- **batterie:close** ends the day here like any other session.
