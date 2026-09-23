<!-- Generated upstream: this file is authored in spm1001/batterie-de-savoir
     (marketplace/README.md, table from brigade.toml) and copied here by
     assemble.sh on every run. Edits made directly in spm1001/batterie are
     overwritten. -->

# Batterie de Savoir

*Kitchen tools for knowledge work with Claude Code — each named for a station in a professional kitchen [brigade](https://en.wikipedia.org/wiki/Brigade_de_cuisine).*

This repository is the suite's plugin marketplace. It is assembled daily from the tools' source repositories, and everything a plugin needs ships inside it.

## Install

```
claude plugin marketplace add spm1001/batterie
claude plugin install <plugin>@batterie
```

Most plugins install a small command-line tool on first run, using [uv](https://docs.astral.sh/uv/) — install uv first. Keep everything current with `/batterie:update`, which updates every plugin and its CLI in one go.

## The plugins

<!-- GENERATED:plugin-table:START -->
| Plugin | Station | What it does | Needs |
|--------|---------|--------------|-------|
| **bon** | The ticket | GTD-flavoured work tracking — outcomes, actions, tactical steps | — |
| **trousse** | The knife roll | Code review through three lenses, blank-slate Claudes, driving a real interactive session, skill authoring | — |
| **mise** | Mise en place | Content fetching and prep from Google Workspace and the web (MCP) | An ITV (itv.com) Google account |
| **passe** | The pass | Fast browser automation via Chrome DevTools Protocol — fetch pages, screenshots, forms, network capture | A Chrome running with remote debugging |
| **accomplis** | The commis | Todoist integration with GTD coaching — human-owned tasks and deadlines | A Todoist account and API token |
| **sonner** | The bell | Inter-session messaging — ring a repo and a Claude answers, spawning one if nobody's home | — |
| **arete** | The fishbone | Lists in and out of MindNode — a pasted list becomes a mind map, a map comes back as Markdown | macOS and MindNode |
| **batterie** | The pots and pans | Suite plumbing — update every plugin at once, show versions, publish a release | — |
<!-- GENERATED:plugin-table:END -->

Each plugin carries the one suite version; `/batterie:version` shows what you are on.
