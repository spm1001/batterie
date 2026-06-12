---
name: tamis
description: >
  Inspects which ad, martech, analytics, and affiliate tags fire on any website and
  identifies each by vendor — tag names collide, so it confirms identity, not just labels.
  Drives a clean headless Chrome that bypasses ControlD DNS filtering and uBlock via DoH,
  captures the full network with cookies accepted, then groups every host by vendor and
  flags the unknowns for hand identification. Use when asked 'what tags fire on this site',
  'is there a Meta, GA4, or Lantern tag here', 'audit this site for tracking', 'reverse
  engineer the martech', 'accept all cookies and show what loads', 'which vendors does this
  site use'. Triggers on 'tag explorer', 'tag scan', 'tamis'. For page reading or browser
  automation use passe; tamis is the tag-identification layer on top. (user)
allowed-tools: [Bash, Read, WebSearch]
---

# Tamis — sieve a page for its tags

A *tamis* is a drum sieve: you push the whole network through it and what's left in
the mesh is the ad-tech. The point isn't just to *list* tags — it's to **identify them
by vendor**, because tag names collide (the worked example below is a "Lantern" that
turned out to be an affiliate tracker, not the ITV product someone assumed).

## When to use

- "What tags fire on `site`?" / "audit this site's tracking" / "which vendors does it use?"
- "Is there a `<vendor>` tag on this page?" — and you need to *confirm the vendor*, not trust the name.
- You want the **post-consent** picture ("accept all cookies, then show me everything").
- You're on a network (ControlD, uBlock, a corporate DoH ban) that hides the ad-tech from a normal browser.

## When NOT to use

- Reading page *content* or general automation → use the **passe** skill directly.
- You only need one known endpoint's response → `passe fetch` / `passe capture` is enough.
- You need a **specific country's** view of geo-targeted tags → see the geo caveat; this host exits from one fixed location.

## Precondition: the DoH escape hatch (one-time)

This host's DNS is filtered (ControlD via the tailnet resolver) — ad/martech domains
resolve to `0.0.0.0`. The fix is a Chrome **managed policy** doing DoH straight to the
IP literal `1.1.1.1` (a *hostname* DoH template fails — ControlD poisons the bootstrap
names too; command-line `--dns-over-https-*` flags are ignored on Linux, only the policy
takes). `tag_scan.py` checks for the policy and prints the one-line install if it's missing:

```bash
echo '{"DnsOverHttpsMode":"secure","DnsOverHttpsTemplates":"https://1.1.1.1/dns-query"}' \
  | sudo tee /etc/chromium/policies/managed/doh-escape-hatch.json
```

Safe alongside the existing passe Chrome (port 9222): that instance uses a SOCKS5 proxy,
which does its own remote DNS, so the policy never affects it. Policy applies on restart only.

## Workflow

### 1. Scout the cookie banner (don't guess the button text)
```bash
passe --cdp http://127.0.0.1:9333 run -c 'goto https://SITE/; wait 3; ax-find button'
```
Read off the real "Accept all" label (it varies: "Accept all cookies", "I Accept", "Agree", …).
If `tag_scan.py` auto-launches Chrome on first run, run this *after* the first scan, or launch
Chrome yourself first (see script `--port`).

### 2. Scan
```bash
${CLAUDE_SKILL_DIR}/scripts/tag_scan.py https://SITE/ --accept "Accept all cookies"
```
Prints requests grouped by vendor + category, the observed consent state, and an
**UNKNOWN** list of hosts it couldn't label. Add `--json` for machine output, `--screenshot
/tmp/s.jpg` for a visual, `--wait 12` for slow tag stacks. Omit `--accept` for the pre-consent state.

**Success criteria:** the consent line reads `granted (G111)` (the accept click worked — Google
calls flip `gcs=G100`→`G111`); the host count is in the dozens, not single digits (tags fired).
A single-digit host count usually means the banner wasn't dismissed or DNS is still filtered.

### 3. Identify the unknowns and confirm suspects
For each UNKNOWN host — and for any tag whose *name* is the actual question — confirm the
**vendor**, don't trust the label:
- Check `references/tag-taxonomy.md` first.
- Fetch the tag's own script and read its config (it usually self-identifies):
  ```bash
  curl -s --doh-url https://1.1.1.1/dns-query 'https://HOST/path/to/tag.js' | head -c 1000
  ```
  (plain `curl` is DNS-filtered here — the `--doh-url` flag routes round it.)
- `WebSearch` the bare domain + "tracking" / "vendor" / "affiliate".
- Add confirmed vendors to `references/tag-taxonomy.md`.

## Worked example — "there's a Lantern tag on virginmedia.com"

An agency claimed a **Lantern** tag was live on virginmedia.com; the worry was a premature
ITV-Lantern release. The scan found `lantern.roeye.com` + `lantern.roeyecdn.com`. Fetching
`lantern_global_6399.min.js` showed it hardcoded `site=virginmedia`, dropped a first-party
`lantern=<uuid>` cookie with a 30-day window, and only beaconed on external referrers or on
a conversion (`order_id`/`order_value`) — textbook **affiliate** attribution. A web search
identified **R.O.EYE**, a Manchester affiliate agency. Verdict: name collision, *not* ITV
Lantern. (Corroborated by Awin — `dwin1.com` — firing alongside it.) The lesson the skill
encodes: **a tag's name is a hypothesis; its script and its vendor are the evidence.**

## Geo caveat

This host exits from one fixed datacentre location (Hetzner, currently Nuremberg DE), and
it's a *datacentre* IP. So:
- Geo-targeted content, redirects, and regional ad partners can differ from a UK (or any
  other) visitor's view.
- The EU vantage actually *helps* this use case — you get the full GDPR/TCF consent banner,
  i.e. the maximal partner set ("accept all N partners").
- Bot-sensitive sites may treat a DC IP differently from a residential one.
- Need a specific country? Route Chrome through a proxy/exit node there — but note a SOCKS5
  proxy does its *own* remote DNS, which *replaces* the DoH bypass (fine if that proxy's DNS
  is itself clean; you then don't need the policy).

## Anti-patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Trusting a tag because its name matches a product | Name collisions give a false ID (the "Lantern" trap) | Fetch its script + confirm the vendor |
| Guessing the cookie-banner button text | Wrong selector → banner never dismissed, tags don't fire | `ax-find button` first (step 1) |
| Concluding "no tags" from a single-digit host count | The banner wasn't dismissed, or DNS is still filtered | Check the consent flip + that the policy is present |
| Using plain `curl`/`dig` to fetch a blocked tag here | ControlD resolves it to `0.0.0.0` → the fetch fails | `curl --doh-url https://1.1.1.1/dns-query …` |
| Reporting one site's tags as authoritative for all geos | This host exits Nuremberg DE — geo-targeted tags differ | State the vantage (geo caveat) |

## Integration

- **passe** — does the actual CDP capture; tamis is the tag-identification layer on top.
- **deglacer / consomme** — unrelated; tamis is network-capture, not session/BigQuery analysis.
- Reusable rig + gotchas also live in global memory (`doh-tag-escape-hatch`).
