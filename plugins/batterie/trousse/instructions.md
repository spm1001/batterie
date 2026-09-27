# Trousse — Instruction Shard

Auto-loaded via `~/.claude/rules/trousse.md`.

## Skill Loading

- When writing or editing a SKILL.md, invoke `Skill(skill-forge)` first — it has the quality framework and lint criteria.
- When making a repo public, use the sharing-scanner skill first — it checks for leaked secrets and sensitive content.

## Isolated Claude

- **Context isolation:** `ardoise.sh` in trousse. Interactive (default) or print (`-p`). No containers needed.
- **Security/VM isolation:** Apple Container CLI. See ardoise skill `references/apple-containers.md`.
