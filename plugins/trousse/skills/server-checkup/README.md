# Server Maintenance Skill

Systematic Linux server management with autonomous execution, risk assessment, and documentation.

## What This Skill Does

Provides a phased workflow for server audits and maintenance:
- **Phase 0**: Context discovery (existing docs)
- **Phase 1**: Connect and triage (baseline capture)
- **Phase 2**: Security audit (SSH, firewall, services)
- **Phase 3**: Maintenance setup (unattended-upgrades)
- **Phase 4**: Tailscale configuration
- **Phase 5**: Cleanup (unnecessary packages/services)
- **Phase 6**: Verification
- **Phase 7**: Report generation

## Installation

Install via batterie-de-savoir marketplace: `/plugin marketplace add spm1001/batterie-de-savoir` then `/plugin install trousse`

## When Claude Uses This Skill

Activates on:
- "check this server", "audit this server"
- "set up this machine", "security audit"
- "server health check"

## File Structure

```
server-maintenance/
├── SKILL.md              # Main skill with all phases
└── references/
    ├── unattended-upgrades.md  # Repo origin patterns
    ├── packages-to-remove.md   # Common unnecessary packages
    ├── ssh-hardening.md        # SSH configuration
    └── terminal-compat.md      # Ghostty/terminfo fixes
```

## Execution Modes

- **Interactive** (default): Execute each phase, ask for decisions
- **Auto mode**: "full server audit" spawns subagents for parallel execution
- **Partial**: "security audit: host" runs only relevant phases

## Risk Scoring

Findings are automatically scored:
- **CRITICAL**: Remote exploit possible — fix immediately
- **HIGH**: Exposure + missing control — fix today
- **MEDIUM**: Unnecessary attack surface — fix this week
- **LOW**: Optimization — optional

## License

MIT
