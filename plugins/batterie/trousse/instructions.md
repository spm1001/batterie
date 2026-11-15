# Trousse — Instruction Shard

Auto-loaded via `~/.claude/rules/trousse.md`.

## Skill Loading

- When writing or editing a SKILL.md, invoke `Skill(skill-forge)` first — it has the quality framework and lint criteria.
- When making a repo public, run skill-forge's sharing scan first (`references/sharing-scan.md`) — it checks for leaked secrets and sensitive content.

## Isolated Claude

- **Context isolation:** the `fresh` skill (engine: `scripts/ardoise.sh` in trousse). Interactive (default) or print (`-p`). No containers needed.
- **Security/VM isolation:** Apple Container CLI. See the `fresh` skill's `references/apple-containers.md`.
