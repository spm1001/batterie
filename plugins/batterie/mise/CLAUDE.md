# CLAUDE.md

**mise-en-space** — Google Workspace MCP (Drive, Gmail) with mise-en-place philosophy: everything prepped, in its place, ready for Claude to cook with.

## Versioning & releasing (suite-managed)

mise ships as part of the **Batterie de Savoir** suite, which carries **one suite-wide version**. So:

- **Do NOT hand-bump `.claude-plugin/plugin.json` to release.** This repo's own `plugin.json` version is **local-dev-only** — the assembler stamps every published plugin to the suite version, overwriting it.
- **Release via `/ship`** from this working tree — it bumps the suite version centrally and ships the change (a 2-repo push: this repo + the central suite bump). Never hand-run the assemble.
- **mise is vendored full-source** — any source edit, plus `CLAUDE.md`, `instructions.md`, `skills/`, `hooks/` and **`scripts/`**, ships. **A push to `main` IS a release:** the assembler bumps unbumped drift and ships it on its next run, and any session's `/ship` or a manual 'Assemble plugins' dispatch reassembles everything — a push can be live within the hour. Before `/ship`, check the assembler hasn't already shipped it (`git -C ~/repos/spm1001/batterie fetch && git show origin/main:plugins/mise/.claude-plugin/plugin.json`) or you mint an empty version. Unshipped: the assembler's exclude list (`assemble.sh`, the rsync near L193) — `.bon/`, `handoffs/`, `tests/`, `docs/`, `fixtures/`, `bakeoff/`, `.github/`, `.claude/`, `CHANGELOG.md`; anything else ships. **Unshipped is not private:** shipped files land in the public `spm1001/batterie`, so never put colleagues', partners' or third parties' names, or quoted mail, into shipped files or into history (a 2026-09-22 slip forced a main rewrite, mise-tijeko). Detail: `docs/claude-md-detail.md`.

Full picture: `spm1001/batterie-de-savoir` → `CLAUDE.md` "Versioning convention" + `.bon/understanding.md`.

### Identity: one engine, two kits — distinct from build flavours

Since the one-plugin fold (suite 2.0.0, 27 Sep 2026, bds-jakemi and bds-cofico) this source serves **two Workspaces through two kits**, and no longer through a string-rewriting transform. This is a *different axis* from the full/slim build flavours (see Development → Build flavours).

- **ITV — the `mit@mit` kit** (ITV/mit-kit). batterie vendors this repo as its `mise/` component without `credentials.json` and runs no Google server itself (the `mcpServers.mise` line stays in this repo's `plugin.json` because its presence triggers full-source vendoring and templates family's). `hooks/ensure-mise.sh` syncs the engine's `.venv` and records it in `${XDG_DATA_HOME:-~/.local/share}/mise-en-space/engine`; mit's launcher execs that engine with the ITV client through the OAuth-client seam, token store `data/mit-mit` (the pre-switch `data/mise-batterie-de-savoir` token adopted by copy). Tools: `mcp__plugin_mit_mise__*`. `credentials.json` stays here for local dev, the CLI and Codex. Detail: `docs/claude-md-detail.md`.
- **Planet Modha — the `family@family` kit** (`spm1001/family-kit`). Ships the engine unmodified minus the ITV `credentials.json`, `hooks/`, `.claude-plugin/` and this `CLAUDE.md` (it names both kits' tool ids, which the family guard forbids), plus `mise/planetmodha-client.json`; the skill's tool ids are rewritten to the family prefix and pyproject's version is pinned (full delta list: the comment above the family block in batterie `assemble.sh`); wired through the seam to `data/family-family`. Its own hook writes `rules/family.md`. Tools: `mcp__plugin_family_mise__*`. Detail: `docs/claude-md-detail.md`.

`make-mise-flavour.sh` is deleted: hooks, `oauth_config.py`, `plugin.json` and the skill are **no longer rewritten per flavour** — this repo is what both kits run, except the family build's tool-id rewrite and version pin (see `assemble.sh`). `plugin.json`'s `identity` drives `ensure-mise.sh`'s no-token warning, which treats `data/family-family/token.json` as the sibling being authed. Pre-fold history: `.bon/understanding.md` → "Identity flavours". Detail: `docs/claude-md-detail.md`.

**The ITV kit's rules shard is REGENERATED EVERY SESSION START.** `hooks/ensure-mise.sh` rewrites `~/.claude/rules/mise.md` (a routing rule naming both kits' tool prefixes, then this repo's `instructions.md`) on every session, so **hand-editing `rules/mise*.md` silently lasts one session**; its mtime equals the session start. Fix it in `instructions.md` or the hook. Detail: `docs/claude-md-detail.md`.

## Architecture

```
extractors/     Pure functions, no MCP awareness (testable without APIs)
adapters/       Thin Google API wrappers (easily mocked)
tools/          MCP tool definitions + dispatch/remote orchestration (the wiring layer)
workspace/      File deposit management (.mise/ in cwd)
resources/      MCP resource text (mise://docs/*) + tool-doc registry
mise_en_space/  The blessed LIBRARY door (mise-dareti): one class (Mise), search/fetch/do, credentials selected in the constructor — the wheel-consumer contract (glaneur, Garni)
server.py       MCPServer registration shim (stdio default, --remote for StreamableHTTP) — ≤500 lines, enforced
apps-script/    Google Apps Script for email attachment extraction (runs in Google, not Python)
docs/           Design documents and references
```

**Shared utilities (root level)** — infrastructure that multiple layers need but doesn't belong in any single layer:

| File | Purpose | Used by |
|------|---------|---------|
| `html_convert.py` | HTML↔markdown: HTML→markdown via markitdown (needs tempfile — why it's not in extractors); markdown→HTML via python-markdown (`markdown_to_html`, for email draft bodies); Gmail body-selection policy (`select_body_text`, `has_data_table` — see the 'Gmail body selection' bullet in docs/tool-behaviours.md) | adapters, tools |
| `markdown_import.py` | Pre-import rewrite for Drive's markdown→Doc engine (`convert_fenced_blocks`) — fenced code blocks become per-line inline-code spans (see Gotchas) | tools |
| `filters.py` | Attachment filtering logic (`is_trivial_attachment`, `filter_attachments`) — holds two `lru_cache`s | adapters, tools |
| `validation.py` | ID/URL validation (`validate_drive_id`, `validate_gmail_id`, etc.) | tools, adapters |
| `retry.py` | Retry decorator with exponential backoff and jitter. `idempotent=` is REQUIRED (mise-covubi): True retries 5xx, 429 and httpx transport errors; False (a write that duplicates on repeat) retries only 429, and its final error says "This write may have landed" and is not retryable. A missing keyword fails at import; `tests/unit/test_retry_idempotent_declared.py` AST-scans every site | adapters |
| `logging_config.py` | Structured logging setup (`logger`, `log_retry`) | everywhere |
| `cues_util.py` | Identity cues (`with_identity`, `current_user_email`) — Protocol-typed, deliberately no adapter import | tools, models |

**Caches, enumerated** (no single authority — know all three): manual client singletons in `adapters/http_client.py` (`get_http_client`/`get_sync_client`, one per mode), two `lru_cache`s in `filters.py`, and a manual metadata cache in `adapters/drive.py` (~L579).

**Key references, with their age on the label:** `docs/information-flow.md` (last content 2026-02) and `docs/decisions.md` (2026-04) are *historical* — how things came to be, not how they are. The current picture is `.bon/understanding.md` and this file; `docs/tool-behaviours.md`, `docs/development-notes.md`, `docs/oauth.md` and `docs/claude-md-detail.md` carry the detail this file indexes. Detail: `docs/claude-md-detail.md`.

**Layer rules:**
- Extractors NEVER import from adapters or tools (no I/O, no tempfile, no os)
- Adapters NEVER import from tools
- Adapters MAY import parsing utilities from extractors
- Adapters use `convert_*` names, not `extract_*` (extract_* reserved for pure extractors/)
- Tools wire adapters → extractors → workspace. The do() machinery (`DISPATCH`, `REQUIRED_PARAMS`, `run_operation`) lives in `tools/dispatch.py`; remote orchestration in `tools/remote.py`
- `mise_en_space/` is the facade tier ABOVE everything: it imports downward freely and NOTHING may import it (enforced — it sits in every other tier's forbidden set). It is deliberately thin re-exports plus identity selection; logic belongs in the layers. Identity state lives in `token_store.configure_identity()` (in-process, never env mutation), and the frozen `http_client` pays only the three seams ambient already paid
- server.py registers tools/resources and holds the thin @mcp.tool wrappers — nothing else (capped at 500 lines)
- Shared utilities live at root level — they sit BELOW the layers and never import upward (retry.py's `adapters.http_client` import is the one documented exception)
- ALL of the above is mechanically enforced by `tests/unit/test_architecture.py` (`LAYER_RULES` for directories, `FILE_RULES` for server.py + root utilities). When adding a module tier, extend the rules — unpoliced tiers are where mass accumulates (server.py hit 1,318 lines before mise-jimohe)
- **Module size is policed repo-wide** (mise-nebewe): every `*.py` under `extractors/`, `adapters/`, `tools/`, `workspace/`, `resources/` is capped at **500 lines**; the modules already over are frozen in `_LEGACY_SIZE_BASELINE` — a **ratchet, not an exemption** (they may only shrink; a shrink over 50 lines fails until the number is lowered). If it trips on code you add, move it to a sibling; raising a baseline is a deliberate act argued in the commit message. Detail: `docs/claude-md-detail.md`.

### Adapter Specializations

| Adapter | Purpose |
|---------|---------|
| `drive.py` | File metadata, search, download, export, comments |
| `docs.py` | Google Docs API (multi-tab support) |
| `sheets.py` | Sheets API (batchGet for values) |
| `slides.py` | Slides API + thumbnail fetching |
| `gmail.py` | Gmail threads and messages |
| `gmail_ids.py` | Alternate Gmail identifiers → thread id (message ids, rfc822 Message-IDs) — fields-masked failure-path resolvers |
| `gmail_browser.py` | a-family (self-sent) URL resolution via a logged-in CDP Chrome — background tab, DOM harvest, fail-open. NB dead through the envelope on all of mcp 1.x (`asyncio.run` on the loop thread, swallowed by the fail-open) and repaired by 2.x's worker threads — first live production success 2026-08-23, three-arm verified (mise-wamoco) |
| `activity.py` | Drive Activity API v2 |
| `calendar.py` | Calendar events and meeting context; `get_event_by_ical_uid` for live invite state (`showDeleted=true` load-bearing); `respond_to_event` (patch replaces the whole attendees array); `insert_event`/`patch_event` (always send supportsAttachments + conferenceDataVersion — omitting either is accept-and-drop; insert stamps `mise:minted_by`/`minted_at`, patch merges that map per-key while replacing arrays wholesale); `freebusy_query` (needs calendar.readonly — NOT covered by calendar.events); `lookup_calendar_timezone` → `(zone, reason)`; `list_events(private_property='k=v')` keyed query (recurring instances inherit the master's properties). Detail: `docs/claude-md-detail.md`. |
| `forms.py` | Google Forms API v1 (structure: questions, sections, options) |
| `charts.py` | Sheets chart export via temporary Slides embed (Sheets API has no direct export) |
| `cdp.py` | Chrome DevTools Protocol cookie access (for genai.py; graceful fallback) |
| `conversion.py` | **Shared** Drive upload→convert→export→delete pattern |
| `pdf.py` | PDF text extraction (pdftotext -layout primary → markitdown only when poppler absent → Drive OCR fallback; mise-mitoki). The flattened-table detector judges ONLY markitdown output — it is calibrated on markitdown's failure shapes and false-fires on -layout's aligned columns (27/133 census slices) |
| `pdf_info.py` | The poppler subprocess seam: `count_pdf_pages` (pdfinfo) + `run_pdftotext` |
| `pdf_render.py` | PDF page-thumbnail rendering (CoreGraphics on macOS, pdf2image/poppler on Linux) — split from pdf.py 2026-08-18 |
| `office.py` | Office file conversion (DOCX/XLSX/PPTX via Drive) |
| `image.py` | Image files (raster + SVG→PNG rendering) |
| `genai.py` | Video summaries via internal GenAI API (requires chrome-debug) |

## Error Handling

Errors are `MiseError` (in `models.py`) with `ErrorKind`: `AUTH_EXPIRED`, `NOT_FOUND`, `PERMISSION_DENIED`, `RATE_LIMITED`, `NETWORK_ERROR`, `INVALID_INPUT`, `EXTRACTION_FAILED`. Each includes `retryable` hint.

**The conversion contract is deliberately two-tier** (mise-ceroru — don't "fix" the second tier into the first):

- **API-facing adapters convert at the adapter layer.** `drive.py` and `gmail.py` (plus thinner docs/sheets/slides call sites) map Google's HTTP taxonomy to `MiseError` kinds — the status code carries meaning (403→PERMISSION_DENIED, 404→NOT_FOUND, 429→RATE_LIMITED) and a `retryable` hint the tools layer couldn't reconstruct from a bare exception.
- **Processing adapters raise bare.** The conversion family (office, pdf, conversion, image, charts, forms, activity, genai, cdp) raises `ValueError`/`Exception` or returns None: their failures are local processing errors whose message IS the diagnostic — a MiseError wrapper would add ceremony, not information.
- **Every tools-layer funnel converts uniformly, so nothing reaches an MCP response raw:** fetch (`tools/fetch/router.py` — MiseError→its kind, ValueError→invalid_input, Exception→unknown), search (`tools/search.py` — per-source catch into `errors[]`; one source failing doesn't block the others), do() (`run_operation` in `tools/dispatch.py` — never raises; an exception escaping a handler becomes kind INTERNAL, since handlers format their own errors), and server.py's wrapper as backstop.

- **"No usable credential" is `token_store.CredentialsUnavailable`, never a bare `FileNotFoundError`** (mise-nodavu, 2026-10-24). The client raises that subclass for every designed token failure (missing, corrupt, revoked, foreign client, ambient); httpx's own constructor raises a plain `FileNotFoundError` for a missing `SSL_CERT_FILE` before any credential loads, and an essayeur caught the first cut telling that user to re-authenticate. `retry._convert_to_mise_error` converts only the subclass to `AUTH_EXPIRED` at every `@with_retry` site, adapters and tools alike (mise-lokowo); `adapters/credential_errors.credentials_as_auth` does the same for a call with no `with_retry` around it (calendar's `respond_to_event`). Client calls outside any `with_retry` still let it through raw.

New adapter rule: interprets Google API responses directly → convert with kinds; post-processes content → raise with a clear message and let the funnel catch.

## How to Add a New Content Type

1. **Adapter** — Create `adapters/{type}.py` with fetch function (API calls, returns data)
2. **Extractor** — Create `extractors/{type}.py` with pure extraction function (data in, markdown out)
3. **Wire in tools** — Add handler in `tools/fetch/` and route in `tools/fetch/router.py`
4. **Model** — Add data model in `models.py` if needed
5. **Fixture** — Add to `fixtures/{type}/`. **Build the smallest thing that exercises what you're testing, by hand** (worked examples: `fixtures/gmail/outlook_reply_url_dense_quote.txt` and siblings). For a real Google response, fetch that one document and sanitise with `scripts/sanitize_fixtures.py`. There is deliberately no bulk-capture script (mise-sowepo). Detail: `docs/claude-md-detail.md`.
6. **Tests** — Unit test for extractor (fixture → expected output), adapter mock test

## How to Add a New do() Operation

1. **Implementation** — Create `tools/{op}.py` with `do_{op}()` that validates its own params (accepts `str | None`) and returns `DoResult` on success or error dict on failure
2. **Dispatch** — Add handler to `DISPATCH` dict, required params to `REQUIRED_PARAMS`, and the params the lambda actually passes to `OP_PARAMS`, all in `tools/dispatch.py`. `OP_PARAMS` is what stops a param the op doesn't consume from being accepted and dropped in silence (mise-fumuda) — one flat param list serves all ops, so the schema can't do it. A test parses the lambdas and fails if the two disagree, in either direction: forget an entry and every caller passing that param gets refused; over-claim and the drop comes back. A **new param** also needs a `DO_PARAM_DEFAULTS` entry (same file) matching its `do()` signature default, or the gate cannot tell "the caller passed this" from "the default arrived"
3. **Register** — Add name to `OPERATIONS` in `tools/__init__.py`
4. **Export** — Add `do_{op}` to `tools/__init__.py` imports and `__all__`
5. **Resource docs** — Update `docs_do()` in `resources/docs.py` with new operation
6. **Advertise it, and check the budget** — add the op to `DO_DESCRIPTION_FULL` in `tools/dispatch.py`, then **measure**: that description is hard-capped at **2048 chars**, and over the line the API drops schema properties *silently* (`do()` has 26). Adding `copy` took it to 2036 — twelve characters — and only a manual measurement caught it. `tests/unit/test_tool_description_budget.py` now fails below 100 chars of headroom; when it does, move detail into `mise://docs/*` rather than trimming meaning. Also update the op **count** in CLAUDE.md, README.md and the SKILL.md table — those three drift silently (see `.bon/understanding.md`)
7. **Decide remote mode deliberately** — `REMOTE_ALLOWED_OPS` in `tools/remote.py` is a whitelist audited Mar 2026. New ops are excluded by default; adding one is a security decision, not a wiring step. Assert the choice in a test either way
8. **Tests** — Unit test for the implementation + `test_dispatch.py` verifies OPERATIONS/DISPATCH sync automatically

## Gotchas

| Gotcha | Detail |
|--------|--------|
| **Overwrite uses Drive import** | Google Doc overwrite uses `files().update()` with `text/markdown` media type — same import engine as create. All markdown formatting (headings, bold, tables) renders automatically. No Docs API involved. |
| **Fenced code blocks are rewritten before Doc import** | Drive's markdown import mangles every code block into per-word code runs; inline code imports clean. So `convert_fenced_blocks` (markdown_import.py) rewrites fenced blocks into per-line inline-code spans with hard breaks before `create`/`overwrite` upload (`\v` line breaks, rendered back by the extractor). prepend/append use raw `insertText` and are untouched (mise-sejule). Detail: `docs/claude-md-detail.md`. |
| **Google Docs eats `\f` and `\x00` on every write path — and `\f` is mise's own page marker** | The markdown import (`create`, `overwrite`) deletes form feeds and **truncates the document at the first NUL** under an HTTP 200; insertText paths delete both but keep the rest; `\t`/`\v` survive (`convert_fenced_blocks` needs `\v`). pdftotext's page separator is `\f`, so `tools/doc_control_chars.py` turns each into a `---` line (imports as a real horizontal rule), strips NULs, and cues `page_breaks_marked`/`nuls_removed` with a warning. A byte upload preserves both and is the lossless route; Sheets CSV is unmeasured (mise-melaso). Detail: `docs/claude-md-detail.md`. |
| **Gmail web IDs ≠ API IDs, and the token is the LAST fragment segment** | `FMfcgz…` web ids need conversion: `thread-f:` converts, self-sent `thread-a:` (and `QgrcJHs…` search-view tokens) does not. The token is the **last** `/`-separated fragment segment — `gmail_fragment_segments()` splits; widening the old regex instead silently re-breaks 3+ segment URLs. `diagnose_gmail_url()` gives per-class teaching (Chat link, draft link, thread-a → the `rfc822msgid:` route). See `validation.py` (mise-jujoti). Detail: `docs/claude-md-detail.md`. |
| **No search snippets** | Drive API v3 has no `contentSnippet` field. `fullText` search finds files but doesn't explain why they matched. |
| **Pre-exfil detection** | User runs background extractor to Drive. Value is that Drive fullText indexes PDF *content*. Check "Email Attachments" folder. |
| **Overwrite destroys content** | `overwrite` is a full replacement — images, tables, formatting lost; use `prepend`/`append`/`replace_text` when existing content matters. A pre-edit restore point is captured (`cues.restore_point` + an `[agent]` comment) but is no licence to overwrite casually. Sheets: `range=` scopes the blast radius, un-ranged overwrite on a multi-tab sheet refuses. **Multi-tab Docs refuse** (the import would destroy every tab but the first) and teach `append tab=`; on multi-tab docs `prepend`/`append` hit the first tab only and `replace_text` hits ALL tabs (mise-wisuzu). Detail: `docs/claude-md-detail.md`. |
| **No purpose parameter** | This MCP always prepares for LLM consumption. No archival/editing modes. |
| **Image size skip vs format skip asymmetry** | `att.size > 4.5MB` no longer causes a pre-download skip — oversized images are downloaded and resized. Unsupported MIME types (not in `SUPPORTED_IMAGE_MIME_TYPES`) still skip pre-download. Reason: size is fixable by resizing; unsupported format is not. Don't restore the size check without also removing the resize logic. |
| **get_deposit_folder wipes on re-fetch** | Every call to `get_deposit_folder` deletes existing files in that folder before returning it. This prevents stale files from previous fetches. Do NOT call `get_deposit_folder` twice for the same folder mid-operation (e.g. inside a retry loop) — the second call will wipe files the first call's writes produced. |
| **A working-tree edit is NOT reachable from the MCP envelope — and restarting does not help** | The plugin runs the **published** engine under `~/.claude/plugins/cache/batterie/batterie/<version>/mise/`, never this repo, so `mcp__*` calls can't see a working-tree change however often the session restarts. Exercise the envelope with `scripts/smoke_stdio.py` (spawns the working tree's `server.py` over real stdio MCP); after publishing, re-verify against the installed artefact. A long-running session keeps the version it started with (bds-sawalu). Detail: `docs/claude-md-detail.md`. |
| **Share requires confirm gate** | `do(share)` without `confirm=True` returns a preview (`Share 'NAME' as ROLE with:` then recipients on 74-column lines) and does not execute: preview, show the user, call again with `confirm=True`. Non-Google addresses (iCloud, Outlook) get Google's required notification email; `cues.notified` says who. Detail: `docs/claude-md-detail.md`. |
| **A confirm dialog shows 4 lines of 74 columns (an 80-column terminal), so mise only asks when the message fits** — re-read unchanged for mise on CC 2.1.303 and 2.1.310 (2.1.310 allows 16 lines to one built-in server only); re-read on every CC bump, recipe in `docs/research/2026-10-24-pukiri-wave2/` | share, attendee-bearing `create_event` and structural `update_event` ride MCP elicitation through one gate (do()'s `confirm_gate`, resolvers in `tools/confirm_gate.py`); the dialog text IS the preview's `message`. Claude Code clips lines and shows only 3 lines plus `… (+N more)`, so `tools/elicit.py::fits_dialog` gates every ask on 4×74 and a longer preview takes the confirm= round-trip. For the calendar ops `settle_gate` writes on accept only if the re-read state still renders to the same words, and never on an ORPHANED answer; share writes on any accept. When adding a fact to a preview, keep the common case in budget and let a warning push to confirm= rather than trimming. The resolvers run on EVERY do() call before the body, so `gate_question` checks capability before any API read; they run before the body's refusals too, so a refused call can still raise a dialog (mise-kelira). The event can change while a dialog waits. Detail: `docs/claude-md-detail.md`. |
| **`_REMOTE_MODE` is early** | Set at module load, not in `__main__`. Required because `@mcp.tool(description=...)` fires at decoration time. Don't "clean up" by moving to argparse — breaks conditional tool descriptions. For containers, use `MISE_REMOTE=1` env var (not `--remote` flag) — `sys.argv` is fragile under process managers. |
| **Remote fetch retry risk** | `get_deposit_folder` wipes on re-call (see above). In remote mode, HTTP client retries or Kube probes can trigger double-wipe. Don't add automatic retry at the HTTP level for fetch operations. |
| **Remote is single-user** | One `token.json`, one `lru_cache(maxsize=1)` per service. Multi-tenancy would require per-request credential injection — architecturally significant. This is a confirmed design choice. |
| **`search` query is `""` not `None` when omitted** | `query` defaults to `""`. Empty string and absent query are indistinguishable inside `do_search` — both skip the `fullText` clause. If you add a source that needs to distinguish "no query given" from "empty query", use a sentinel (e.g. `query: str \| None = None` and check `is None`). Don't assume `""` means "give me everything" — the type/folder_id validation gate catches the all-empty case. |
| **Image embedding needs public sharing** | `do(create)` with local image refs uses Docs API `insertInlineImage`, which requires a publicly accessible URL. Images are uploaded to Drive, shared publicly for seconds, then permissions revoked and temp files deleted. Enterprise Workspace accounts with DLP policies may block the `permissions.create` call — images will be skipped with `cues.image_errors`, doc is still created. |
| **`file_path` is stdio-only (gated)** | `file_path` on `do(create)` and `do(overwrite)` reads the server's disk. Remote mode rejects it outright in server.py's do() wrapper (the boundary). In stdio it's deliberately unrestricted — any readable path works, including `/tmp` and `~/scratch` (mise-jebude: the old cwd-containment rail rejected natural staging spots while guarding nothing, since the same Claude can Read any file and pass `content=`). |
| **Checkbox tick-state is export-only** | Google Docs checkbox checked-state is NOT in the Docs API (`documents.get` returns identical bullet dicts for checked/unchecked). `adapters/docs.py::_apply_checkbox_states` fetches the `text/markdown` export as an oracle — a **2nd API call, only when a checkbox list is present** (`is_checkbox_list` gate) — parses `[ ]`/`[x]` in document order, and tags each paragraph. Count-mismatch → plain bullets + a warning cue (never a wrong tick). The `~~` on checked rows in the export is synthesised by Google's renderer from the checked bit, NOT `textStyle.strikethrough` — don't try to read it from the API. |
| **`comments.md` locates comments — all three surfaces, from two different planes** | Docs correlate on content (anchor text → nearest heading); Slides/Sheets on ids via a second GET with `commentsViewMode=COMMENTS_VIEW_MODE_INCLUDED` (`adapters/comment_anchors.py`) → `slide N (title)` / `Tab!B12`, rendered in document order with `↳`, orphans flagged `⚠`. Don'ts: **the join is outer and one-way** — the anchor map only adds a locator, never drops a thread; every anchor-read failure degrades to the flat render plus a `cues.warnings` line (a Developer Preview compliance requirement: no default render may depend on it); the second read is paid only for Slides/Sheets files with open comments (mise-dukacu). Detail: `docs/claude-md-detail.md`. |
| **`do(comment, anchor=…)` writes on the batchUpdate plane, and a misplaced comment is worse than none** | `anchor=` takes the spellings `comments.md` prints (`'slide 3'`, `'Sheet1!B12'`, quoted Docs text) and routes to each surface's `insertComment`. Traps (measured 2026-09-01): resolve Docs quotes in the `SUGGESTIONS_INLINE` index space or the comment lands on a different sentence under a 200; Docs indices are **UTF-16 code units** — borrow `_utf16_len`; keep the field mask `tabs` whole (narrower masks hid table text and nested tabs); `requiredRevisionId` guards Docs and Slides but Sheets ignores it (on a mismatch a Docs quote is re-resolved by content, but `'slide 2'` is position-addressed: its objectId is pinned on the first pass and a deleted target refuses rather than re-aiming); Google stores an assignee who can't open the file, so assignments warn. A refused anchor is NEVER downgraded to an unanchored comment, and Docs landings are checked against `plainTextQuote` after the write. Detail: `docs/claude-md-detail.md`. |
| **The comments read is capped at 100 threads, and the cap used to eat the open ones** | `_enrich_with_comments` asks for 100; the `include_resolved=False` filter runs **inside** the pagination loop so the cap counts kept threads, and a `nextPageToken` surviving at the cap sets `truncated` → header `(100+ — capped…)` plus a warning. `len == max_results` can never tell full from capped, so keep the token check. Detail: `docs/claude-md-detail.md`. |

## Development

```bash
uv sync --all-extras                                # Install deps (full build + dev tools)
uv run --extra extraction python server.py          # Run MCP server (stdio, full build)
uv run --extra extraction python server.py --remote # StreamableHTTP on :8000/mcp
uv run python server.py --help                      # CLI help
uv run --all-extras python -m pytest                # Run tests (suite ASSUMES the full build)
uv run --all-extras python -m pytest tests/unit     # Unit tests only (fast, mocked)
uv run --all-extras python -m mypy models.py extractors/ adapters/ validation.py workspace/
uv run --all-extras python scripts/smoke_stdio.py   # drive the WORKING TREE over real stdio MCP
```

Integration tests: `uv run --all-extras python -m pytest tests/integration -m integration -o addopts="" --no-cov` (~5 minutes, runs as the token's account, creates and bins test files). **Run them before shipping a change to an adapter or a dependency refresh** (mise-pirusu). The first run in months found 13 of 107 red, all stale tests — read every red; don't assume either way. They use the repo's default token store; when that token is dead, point them at a live kit: `MISE_EN_SPACE_OAUTH_CLIENT=<the mit kit's itv-oauth-client.json> MISE_EN_SPACE_DATA_DIR=~/.claude/plugins/data/mit-mit`. Detail: `docs/claude-md-detail.md`.

**`tests/bench/` is the model-qualification battery, not part of the test suite** (mise-rolira): re-runnable against new model strings so each generation is measured against the deposit-format policy (`docs/2026-08-18-deposit-format-policy.md`). Costs real API money — run deliberately, never in CI. Detail: `docs/claude-md-detail.md`.

**Run the bare documented command when you need the count.** It is the last line (`N passed, M deselected`) under a long coverage table. `addopts` carries `-q` and `-m 'not integration'`: adding your own `-q` makes `-qq` and hides the summary, and `-v` cancels to zero verbosity — use `-vv`, validated against a clean tree, because the failure mode is an empty result with exit 0.

**Unit tests run hermetically** — `tests/unit/conftest.py` points `MISE_TOKEN_PATH` at an absent file, so a green never uses the machine's token. Credential-machinery tests state their env with module fixtures; never delete the conftest pin to make a test pass.

**`scripts/smoke_stdio.py` exercises the MCP envelope before publishing** — it spawns the working tree's `server.py` over real stdio MCP. Add a case when you change fetch's failure surface. It spawns the server with the SDK's default environment, which drops custom env vars, so it always reads the real token store.

**mypy's standing errors are baselined and ratcheted in `tests/unit/test_mypy_baseline.py`** — a new error fails naming the mypy line, a fixed one fails until the entry is lowered. Read the number there, never by hand-count.

**The lock is refreshed deliberately, monthly, in slices, with a cooldown:** `uv lock --upgrade --exclude-newer "7 days"`; each slice passes the live integration suite before push.

The stories behind each of these — why the count paragraph once said the opposite, the `-v`/`-q` traps, the mypy count drift, the slice plan and what upstream holds back — are in `docs/development-notes.md`.

### Build flavours (mise-hibere, 0.7.9)

Local extraction (`markitdown[pdf]`, `pdf2image`) lives in an optional `extraction`
extra, **not** core. Two flavours result:

- **Full** — dev/CI and the marketplace plugin (the plugin spawns `uv run --extra
  extraction`). markitdown as the PDF fallback, HTML→markdown, PDF page thumbnails.
- **Slim / embedded** — what Cornichon vendors (`vendor.sh` installs plain core, no
  extra). `markitdown` is absent, `html_convert.py` degrades to tag-stripping, and
  PDF thumbnails are skipped. Image fetch still works (`pillow` is core).

**PDF text is orthogonal to the flavour axis since mise-mitoki (2026-08-18):** the
primary is poppler's `pdftotext -layout`, a SYSTEM binary no pip extra can carry —
so a slim build on a host with poppler gets first-class PDF text, and a full build
on a host without it degrades to markitdown with a teaching warning (plus a one-shot
session-start advisory from `ensure-mise.sh`). Without either, Drive server-side
conversion remains the floor.

Two things follow: (1) **run the test suite with `--extra extraction`** (or
`--all-extras`) — PDF-extraction tests assume markitdown is present and fail in a
slim env; (2) the slim PDF→Drive fallback needs Drive **write** scope (it uploads to
convert) — fine for Cornichon, whose PDFs come from the user's own Drive.

### Call Log

Every MCP tool call is logged to `~/.local/share/mise/calls.jsonl` (5 MB rotation, 3 backups; `MISE_CALLS_LOG` redirects it). Fields: `ts`, `tool`, `params`, `ok`, `error`, `result`. **Rows before 2026-09-23 include test-suite noise** (fixture ids such as `doc1`, `tab='Redraft'`) — filter it before counting errors (mise-bewono). **`params` omits `base_path`**, so its absence in the log says nothing about callers. Detail: `docs/claude-md-detail.md`.

```bash
# Last 10 calls
tail -10 ~/.local/share/mise/calls.jsonl | python3 -c "import json,sys; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin]"

# Failed calls only
grep '"ok": false' ~/.local/share/mise/calls.jsonl | tail -5
```

## Design Decisions and Their Consequences

*Facts about this codebase are recoverable by reading it; grep beats any list we could write. What is **not** recoverable is the reasoning that made a fact deliberate. This section holds only consequences that are expensive to re-derive and cheap to get wrong — if an entry here could be answered by a one-minute grep, it belongs somewhere else or nowhere.*

**Deposits keep content out of context. `Read` is where context is spent.** In stdio mode `fetch` returns `path`, `content_file`, `format`, `type`, `metadata` and `cues` — `FetchResult.content` is `None` except in remote mode, where the client has no filesystem. So the fetch itself costs almost no context; the cost lands later, when the caller reads the deposit. Two things follow, and both have been got wrong in practice:

- **Depositing more is nearly free, so never narrow a fetch to save context.** The lever is what the caller is *pointed at*: when a URL names a tab, heading, slide or comment, deposit everything and make the cue name the artefact holding it. A caller who ignores the cue still has the whole document, so the silent-partial-answer failure cannot occur (mise-dogape). Detail: `docs/claude-md-detail.md`.
- **Remote mode is the exception.** There `content` *is* inline, so payload size is a genuine cost — but only there.

**Three verbs is a budget, not minimalism.** `do()`'s description is hard-capped at 2048 characters and the API silently drops schema properties above it (see the MCP description ceiling in `.bon/understanding.md`). Every new operation name spends that budget three times over: description, dispatch table, and the model's reasoning about which verb to pick. This is why the standing rule is to check whether an existing op already covers a need with different parameters before minting a new one — it is a resource constraint, not an aesthetic.

**`mcp[cli]` rides the 2.x line, and tool bodies run CONCURRENTLY** on anyio worker threads (since 2026-08-24). Shared state is guarded where it lives — a per-resource deposit lock in `workspace/manager.py`, O_EXCL search-deposit naming, single-flight refresh and a locked client mint in `adapters/http_client.py` — pinned by `test_server_concurrency.py` and `test_concurrency_guards.py`. **Do NOT re-serialize with an anyio limiter cap**: the stdio transport's blocked stdin read shares that pool, and capacity 1 deadlocks. Worker threads have no running loop, which is why `asyncio.run()` in `gmail_browser.py`/`cdp.py` works. Cross-process races (two servers, one cwd) are not covered. Detail: `docs/claude-md-detail.md`.

**Two v2 capabilities are deliberately NOT adopted** (mise-huwubi): teaching errors stay **in-band** (mise's error dicts are for the calling model), and typed output schemas are parked — Claude Code passes the model only the JSON text, so a typed contract buys nothing visible while growing `tools/list`. Revisit if Claude Code starts handing the model structuredContent. Detail: `docs/claude-md-detail.md`.

## README skill table is generated

The Skills table in README.md (between `GENERATED:SKILLS` markers) is rendered from
`skills/*/SKILL.md` frontmatter — never hand-edit it. After adding, removing or renaming
a skill: `uv run --script ../batterie-de-savoir/scripts/render-skills.py .` from the repo
root. CI re-checks it on every push (fetching the canonical script from batterie-de-savoir
raw main), so a stale table fails the build. If a table one-liner reads badly, fix the
SKILL.md description (skill-forge), not the table.

**Notes room:** `~/notes/practices/mise/` — the thinking half (usage discipline, field gotchas, what not to trust). Read it when the question is how we *use* this rather than how it works. (bon-jezahi, 2026-08-16)
## OAuth

**In-app bootstrap (canonical):** `mise.do(operation="setup_oauth")` — opens a Mac browser at the consent screen, runs a detached subprocess listener on `localhost:3000`, saves the token via `save_token` (macOS: into the Keychain under `keychain_service()`, then the file is removed; elsewhere: the data-dir `token.json`). Returns immediately with the URL inline as a fallback. This is the path Cowork users hit; it's also the path the friendly error wrapper in `adapters/http_client.py` points at when the token is missing.

**CLI fallback:**
```bash
uv run python -m auth --auto              # Auto (opens browser, runs listener, saves token)
uv run python -m auth                     # Headless — prints URL, paste back via --code
uv run python -m auth --code URL_OR_CODE  # Exchange code from headless flow
```

**Headless / remote-desktop boxes (e.g. tube): use the `--code` path** — mint with plain `uv run python -m auth`, open the URL in a browser signed into the **right** account (tube's xrdp browser is planetmodha; the ITV client is Internal to itv.com), paste the redirect URL back via `--code`. Set `MISE_NO_BROWSER=1` where the browser is on the wrong account. A running server picks up a new token only when the old grant is dead; a re-consent that ADDS scopes is not picked up — verify with a fresh process (mise-tehulu). Detail: `docs/claude-md-detail.md`.

`credentials.json` (OAuth client config, not secret) ships with the repo. The OAuth client lives in ITV's `mit-workspace-mcp-server` GCP project with **User type: Internal** — any `@itv.com` Workspace account can authenticate without verification or a test-user list. Token auto-refreshes; `clear_service_cache` handles revoked refresh tokens.

**Token storage:** on macOS the Keychain entry (`mise-oauth-token`, or `mise-oauth-token:<client_id>` when a kit sets `MISE_EN_SPACE_OAUTH_CLIENT`) is canonical once a consent has written it, and `save_token` deletes the file; elsewhere `TOKEN_FILE` in the data dir is the store. Adoption writes the file only, `security … -w` exit 44 means absent, and an unfilled-placeholder data dir falls back by client project number — the full rules are in `docs/oauth.md`.

**The OAuth-client seam (mise-nujina):** `MISE_EN_SPACE_OAUTH_CLIENT` names an installed-app client JSON and `MISE_EN_SPACE_DATA_DIR` a token-store dir (a kit passes `${CLAUDE_PLUGIN_DATA}`); both unset is the pre-seam behaviour exactly. Four rules, pinned in `tests/unit/test_oauth_seam.py`: (1) a named client that is missing or malformed **refuses** — never falls back to the bundled client; (2) an empty store **adopts by copy** a pre-seam token from the same `client_id`; (3) a token from a DIFFERENT client refuses; (4) an env-supplied client keys the Keychain entry `mise-oauth-token:<client_id>`. **The engine never reads `CLAUDE_PLUGIN_DATA` itself** (the Bash tool doesn't get it, so a `--code` re-auth would land elsewhere) — `setup_oauth`'s printed command carries the `MISE_*` values (`oauth_config.cli_env_prefix`). Detail: `docs/claude-md-detail.md`.

**Ambient mode (service accounts — mise-wasagu):** `MISE_CREDENTIALS=ambient` mints via `google.auth.default()` (`adapters/ambient.py`). Explicit opt-in only, never a fallback; beside `MISE_TOKEN_PATH` it is an error. Drive-family only: search defaults to `['drive']`, and the Gmail/calendar/setup_oauth ops refuse at a dispatch gate. Service accounts own no Drive storage, so their writes land only in Shared Drives (mise-finupa). Detail: `docs/claude-md-detail.md`.

## Remote Mode

`server.py --remote` (or `MISE_REMOTE=1`) runs as a StreamableHTTP server on `/mcp` for Claude.ai custom connectors. Key differences from stdio:

| Aspect | stdio (default) | remote (`--remote`) |
|--------|----------------|---------------------|
| Transport | stdin/stdout | StreamableHTTP on `/mcp` |
| `do()` operations | All 23 | 6 safe ops: create, draft, reply_draft, archive, star, label |
| Content delivery | Filesystem deposits | Inline in JSON-RPC response (`content` + `comments` fields) |
| `base_path` | Required | Optional (temp dir) |
| Tool description | Full | Restricted (only safe ops + relevant params) |
| Health endpoint | N/A | `/health` returns `{"status": "ok"}` |

**Architecture:** `_REMOTE_MODE` is determined at module load time (before `@mcp.tool()` decorators run) so tool descriptions adapt. This is intentional — argparse validates in `__main__` but the value must be available earlier for the conditional `description=` parameter on `@mcp.tool()`. Don't move this to argparse without understanding why it's early.

**Operation gating:** `REMOTE_ALLOWED_OPS` in `tools/remote.py` (the gate itself fires in server.py's do() wrapper). Rejected ops get a generic "not available in remote mode" error listing only allowed ops — restricted op names are not leaked.

**Binary content:** Image fetches in remote mode return metadata and cues but no inline content (binary can't be text-encoded). A cue warning explains this.

## Warnings Pattern

Data models have `warnings: list[str]` fields. Extractors populate them during processing (mutation, not return tuple — preserves simple `str` return type). Exception: `extract_message_content()` returns `tuple[str, list[str]]` for per-message processing.

## File Deposit Structure

```
.mise/
├── slides--ami-deck-2026--1OepZjuwi2em/
│   ├── manifest.json       # Self-describing metadata
│   ├── content.md          # Extracted text/markdown
│   └── slide_01.png        # Thumbnails (selective)
├── doc--meeting-notes--abc123def/
│   ├── manifest.json
│   └── content.md
└── gmail--re-project-update--thread456/
    ├── manifest.json
    └── content.md
```

**Folder naming:** `{type}--{title-slug}--{id-prefix}/` (ID first 12 chars for readability).

## Field Reports

`docs/` contains field reports capturing real-world skill/tool gaps. Pattern: notice gap → write field report → fix → commit together.

## MCP Tool Surface (3 verbs)

| Tool | Purpose | Writes files? |
|------|---------|---------------|
| `search` | Find files/emails/activity/calendar events/**people**/**Google Chat**, return metadata + inline preview | No |
| `fetch` | Download content to `.mise/` in cwd, return path + cues | Yes |
| `do` | Act on Workspace — 23 ops (create, copy, move, rename, share, overwrite, prepend, append, replace_text, draft, reply_draft, archive, star, label, comment, comment_reply, suggest, trash, respond, create_event, update_event, freebusy, setup_oauth) | Varies |

**Key behaviors** — one line each, in order; the full text of every line (the reasoning, measurements and traps) is in `docs/tool-behaviours.md`. Read it before changing a behaviour listed here.
- `search` returns metadata only — Claude triages before fetching
- `search` accepts `type=` for MIME filter
- `search` **paginates** to `max_results` (10-page / 1000-result guard)
- `search` accepts `raw_query=`
- **Drive search runs `corpora=allDrives` since mise-jefaki (2026-08-24).**
- `search` accepts `sources=['people']`
- **`search` Gmail rows arrive with their senders placed**
- **`fetch` of a Gmail thread places its participants too**
- **`org_map.json` is hand-maintained tenant data, and the second ITV-keyed fact mise ships**
- `search` drive results and every Drive deposit manifest carry `last_modified_by` (mise-tanoti)
- `search` gmail results carry `has_invite` (thread has a calendar invite — free, from the parts mask) so triage can spot meetings
- **Google Chat, read as the user**
- `search` accepts `time_min`/`time_max` (ISO date or datetime) for the **calendar** source
- `search` gmail results and `fetch` thread metadata carry `web_link`
- `fetch` auto-detects ID type (Drive file ID vs Gmail thread ID)
- `fetch` of a Drive **shortcut** follows it one hop to its target, disclosed in `cues.shortcut` plus a warning naming both ids …
- `fetch` of a **download-restricted** Drive file (`capabilities.canDownload` false) refuses BEFORE the download with a teaching `permission_denied` naming who set it …
- `fetch` of a Gmail invite adds `cues.invite_state`
- `fetch` on a 16-hex Gmail id that 404s as a thread **resolves it as a MESSAGE id and refetches its thread** …
- **A `fetch` 404 names the likely id type and the next move**
- `fetch` accepts an **RFC 822 Message-ID** (bare or `<angle-bracketed>`, from Gmail's Show original view)
- `fetch` accepts a **Show-original URL** (`?view=om&permmsgid=msg-f:<decimal>`)
- `fetch` of **mise's own draft link** (`…/mail/#drafts/<r-id>`, emitted by every draft/reply_draft result) resolves the draft to its holding thread via `drafts.get` …
- **Gmail URL provenance is cued, not dropped**
- **A self-sent (thread-a) fragment URL resolves via a logged-in CDP browser when one is available**
- **A self-sent (thread-a / msg-a) refusal attaches `candidates`**
- **Gmail body selection is plain-text-first with one exception**
- **Inline answers inside a quote survive stripping**
- **`fetch` of a decorated Drive URL points at the named location instead of throwing it away**
- `fetch` accepts `raw=True` alongside `attachment=`
- `fetch` accepts optional `tabs` param (list of tab names) to fetch only specific tabs from spreadsheets
- `fetch` accepts `thumbnails=False`
- `fetch` accepts `crops=False`
- **PDF page-citation fidelity is measured, never inferred**
- `fetch` accepts `suggestions=` for Google Docs carrying suggested edits
- `fetch` accepts `recursive=True` on folder IDs — returns full indented tree (max depth 5, 1000 items)
- `do` routes via `operation` param — `do(operation="create", ...)`
- `do(move)`, `do(archive)`, `do(star)`, `do(label)` accept `file_id` as `str | list[str]` for batch operations
- **Calendar writes**
- `do(respond)` RSVPs a calendar invite as the user
- `do(create)` and `do(overwrite)` accept `file_path` to read content directly from a local file
- `do(create)` accepts `doc_type='folder'`
- `do(create)` accepts `doc_type='form'`
- `do(create)` accepts `page_setup='pageless'` (doc_type='doc' only) — sets pageless mode via Docs API after creation.
- `do(create)` with `doc_type='doc'` auto-embeds local images
- `do(create)` on a doc and `do(overwrite)` on a Google Doc turn a **whole line of just `@url` into a real smart chip** (mise-rafote, `tools/doc_chips.py`)
- `do(move)` accepts `file_id` as a list for batch moves
- `do(draft)` and `do(reply_draft)` **auto-append the user's real Gmail signature** (sendAs settings) to both MIME parts
- **`do(reply_draft)` quotes the message it answers**
- **Superseded-draft guard**
- **Doc tabs**
- **Sheets editing**
- **Pre-edit restore point**
- **Comments included automatically** — open comments deposited as `comments.md`
- **Cues in every response** — `cues` block surfaces files, comment count, warnings, email context
- `base_path` is required on all tools in stdio mode

