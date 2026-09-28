<!-- Generated upstream: this file is authored in spm1001/batterie-de-savoir
     (marketplace/README.md, table from brigade.toml) and copied here by
     assemble.sh on every run. Edits made directly in spm1001/batterie are
     overwritten. -->

# Batterie de Savoir

*Kitchen tools for knowledge work with Claude Code — each named for a station in a professional kitchen [brigade](https://en.wikipedia.org/wiki/Brigade_de_cuisine).*

This repository is the suite's plugin marketplace. It holds one plugin, `batterie`, assembled daily from the tools' source repositories, and everything the plugin needs ships inside it.

## Install

```
claude plugin marketplace add spm1001/batterie
claude plugin install batterie@batterie
```

Several tools install a small command-line tool on first run, using [uv](https://docs.astral.sh/uv/) — install uv first. Keep everything current with `/batterie:update`, which updates the plugin and its CLIs in one go. Skills answer to `/batterie:<name>`, or to the bare name when nothing else claims it: `/open`, `/close`, `/deep-review`, `/browse`.

## Moving from the eight plugins to one

Before the one-plugin release each tool was its own plugin (`bon@batterie`, `trousse@batterie`, `mise@batterie` and so on). Claude Code does not remove a plugin its marketplace stops listing, and an old one left beside `batterie@batterie` runs every hook twice and starts a second Google Workspace server. So move over once:

- **Claude Desktop and claude.ai:** in Customize → Plugins, uninstall each old batterie plugin and install **batterie**. A plugin installed through claude.ai syncs to your terminal sessions too, so do this even if you mostly use the terminal.
- **Claude Code in a terminal:** run `/batterie:update`; it removes the old plugins it finds and installs the new one. By hand: `claude plugin uninstall <name>@batterie` for each of bon, trousse, mise, accomplis, sonner, passe and arete, then `claude plugin install batterie@batterie`.
- **Permission rules** that name Google Workspace tools change prefix: `mcp__plugin_mise_mise__…` becomes `mcp__plugin_batterie_mise__…`.

Your Google sign-in carries over; nothing asks you to consent again.

## If the kit stops loading

The sign is a new session with none of the tools, and `claude plugin list` showing `batterie@batterie` with "failed to load — Marketplace batterie not found". Claude Code keeps two records of the marketplace, one in your `settings.json` and one in its own registry, and it refuses to load it when they name different sources (the same repo by git URL in one and as `spm1001/batterie` in the other, for example). `/batterie:update` can't help yet, because it ships inside the plugin that won't load. In a terminal:

```
claude plugin marketplace add spm1001/batterie
claude plugin update batterie@batterie
```

Then start a new session and run `/batterie:update`. Re-adding a marketplace switches off its auto-update, and the update turns it back on when it can tell it was on. If `/batterie:update` doesn't say it turned auto-update back on and you want it, open `/plugin` → Marketplaces → batterie and choose Enable auto-update.

## What's inside

<!-- GENERATED:plugin-table:START -->
| Tool | Station | What it does | Needs |
|--------|---------|--------------|-------|
| **bon** | The ticket | GTD-flavoured work tracking — outcomes, actions, tactical steps | — |
| **trousse** | The knife roll | Code review through three lenses, blank-slate Claudes, driving a real interactive session, skill authoring | — |
| **mise** | Mise en place | Content fetching and prep from Google Workspace and the web (MCP) | An ITV (itv.com) Google account |
| **passe** | The pass | Fast browser automation via Chrome DevTools Protocol — fetch pages, screenshots, forms, network capture | A Chrome running with remote debugging |
| **accomplis** | The commis | Todoist integration with GTD coaching — human-owned tasks and deadlines | A Todoist account and API token |
| **sonner** | The bell | Inter-session messaging — ring a repo and a Claude answers, spawning one if nobody's home | — |
| **batterie** | The pots and pans | Keeps the kit current — /batterie:update updates the plugin and its CLIs, /batterie:version shows what you are on | — |
<!-- GENERATED:plugin-table:END -->

The plugin carries the one suite version; `/batterie:version` shows what you are on.
