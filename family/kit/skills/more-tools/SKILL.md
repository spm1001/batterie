---
name: more-tools
description: Says honestly what else the family could add beyond this kit's Google Workspace tools, and what it would cost them — load BEFORE suggesting or installing any Claude plugin on a family machine. The rest of the suite is one public plugin, all or nothing, built for Sameer's work; this names what it would give them, what it brings along that they did not ask for, and the one install. Triggers on 'what else can you do', 'are there other tools', 'is there a plugin for that', 'how do I install X', 'can you review my code', 'can you draw me a diagram'. (user)
---

# More tools (Planet Modha family)

This family kit holds two things: Google Workspace tools for Planet Modha (Drive, Gmail, Calendar, Docs), signed in with the family's own Google account, and **getting-things-done**, a skill that coaches someone through organising their life and running a weekly review in any app (Todoist, Things or paper). It stands alone and needs nothing else installed.

## When to use

- They ask for something this kit does not do: code review, diagrams, data analysis. (A to-do system and weekly reviews are covered: use getting-things-done.)
- They ask what else Claude can do here, or whether a plugin exists for something.
- You are about to suggest installing anything.

## When not to use

- **The Google tools themselves misbehave.** That is a sign-in or MCP problem, not a missing plugin; nothing here helps.
- They are on an ITV machine. ITV colleagues have their own kit.

## What there is

Everything else in the suite ships as **one public plugin, `batterie@batterie`**. It exists from 28 September 2026 (before that the suite was several separate plugins, and the old names no longer apply). Adding it is two commands:

```
claude plugin marketplace add spm1001/batterie
claude plugin install batterie@batterie
```

**It is all or nothing, and it is built for Sameer's work.** What a family member might use from it:

- **code review and diagrams** (trousse), which work straight away;
- **a Todoist command-line tool** (accomplis), for heavy desktop use with an API token. Most people won't need it: getting-things-done in this kit already coaches GTD, and Doist's own Todoist connector lets Claude work their lists from claude.ai;
- **a work tracker** (bon), which suits someone tracking projects across sessions.

What comes with it that they did not ask for: session-start checks for command-line tools they may not have, browser automation and cross-session messaging, and **a second Google Workspace tool pointed at ITV**. That one will say it has no sign-in. It is not for them; the family's Google stays with this kit, and they should never sign it in.

## How to offer it

Name the one capability that fits what they just asked for, say plainly that it comes as part of a bigger plugin with the extras above, and suggest they check with Sameer before adding it. Offering beats installing: a plugin that fills their sessions with notices about tools they never wanted is worse than no plugin.
