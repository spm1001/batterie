# tamis

Sieve a web page for its ad / martech / analytics / affiliate tags — and identify each
one by **vendor**, because tag names collide.

Drives a clean headless Chrome on this host that bypasses ControlD DNS filtering and
uBlock via DoH (straight to `1.1.1.1`), captures the full network with cookies accepted,
groups every host by vendor against a known taxonomy, and flags anything unrecognised for
hand identification.

```bash
scripts/tag_scan.py https://www.example.com/ --accept "Accept all cookies"
```

- `SKILL.md` — the workflow, the DoH precondition, the vendor-confirmation method, the geo caveat, and the worked example (a "Lantern" tag that was R.O.EYE affiliate, not ITV Lantern).
- `references/tag-taxonomy.md` — canonical domain → vendor lookup; grow it as you identify new tags.
- `scripts/tag_scan.py` — launch-Chrome-if-needed → `passe` capture → grouped report. Stdlib only (no install).

Composes with the **passe** skill (which does the CDP capture). Reusable rig + the DNS
gotchas also live in global memory as `doh-tag-escape-hatch`.
