# family-kit — the Planet Modha family's private marketplace (generated)

One marketplace, `family`, holding one plugin, `family`: Google Workspace tools (the mise engine, unmodified) signed in against the Planet Modha Google account. It stands alone — nothing else needs installing.

```
claude plugin marketplace add spm1001/family-kit
claude plugin install family@family
```

**Every file here is GENERATED** by `spm1001/batterie`'s `assemble.sh` from the public kit's mise component plus `family/` in that repo. Never hand-edit; change the source and re-assemble. The vendored OAuth client (`plugins/family/mise/planetmodha-client.json`) is an installed-app client whose secret is public by design; this repo is private because the claude.ai organisation library needs a private repo, not because of the credential.
