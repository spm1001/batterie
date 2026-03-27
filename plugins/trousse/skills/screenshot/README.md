# Screenshotting Skill

Take screenshots to see what's on screen — window captures or full screen.

## What This Skill Does

Enables Claude to capture and analyze screen state:
- Capture specific app windows by name
- Capture windows by title match
- Full screen capture
- Automatic resizing for API efficiency

## Installation

Install via batterie-de-savoir marketplace: `/plugin marketplace add spm1001/batterie-de-savoir` then `/plugin install trousse`

## When Claude Uses This Skill

**Reactive (user asks):**
- "have a look at this", "can you see?"
- "what does it look like?", "check the screen"

**Proactive (verify state):**
- After uncertain CLI operations
- When tool state is unclear
- To verify visual changes happened

## Usage

```bash
# Capture specific app
uv run ${CLAUDE_SKILL_DIR}/scripts/look.py --app Chrome

# Capture by window title
uv run ${CLAUDE_SKILL_DIR}/scripts/look.py --app Chrome --title "GitHub"

# Full screen
uv run ${CLAUDE_SKILL_DIR}/scripts/look.py --screen

# List available windows
uv run ${CLAUDE_SKILL_DIR}/scripts/look.py --list
```

## Output

- **Ephemeral**: Screenshots go to `/tmp/claude-screenshots/` by default
- **Persistent**: Specify a path for documentation workflows

## Requirements

- macOS (uses Quartz CGWindowList API)
- Screen Recording permission for the terminal app

## License

MIT
