# Sprite Command Reference

## Contents

1. [Core Commands](#core-commands)
2. [Checkpoint Commands](#checkpoint-commands)
3. [Exec Options](#exec-options)
4. [Network & Access](#network--access)
5. [SDKs](#sdks)

---

## Core Commands

| Command | Purpose |
|---------|---------|
| `sprite list` | List all sprites |
| `sprite create <name>` | Create new sprite |
| `sprite use <name>` | Set active sprite for current directory |
| `sprite exec <cmd>` | Run command on active sprite |
| `sprite exec -s <name> <cmd>` | Run command on specific sprite |
| `sprite console` | Interactive shell session |
| `sprite destroy` | Delete current sprite |
| `sprite upgrade` | Update CLI to latest version |

### Multi-command execution

```bash
# Use bash -c for multiple commands
sprite exec bash -c "cd ~/project && git pull && npm test"
```

### Tip: Avoid -s flag repetition

```bash
sprite use my-sprite      # Set once
sprite exec ls -la        # No -s needed
sprite exec npm test      # No -s needed
```

---

## Checkpoint Commands

| Command | Purpose |
|---------|---------|
| `sprite checkpoint create` | Snapshot current state |
| `sprite checkpoint create --comment "description"` | Snapshot with comment |
| `sprite checkpoint list` | List all checkpoints |
| `sprite restore <id>` | Restore to checkpoint |

**Important:** Checkpoints are per-sprite. Cannot restore sprite-A's checkpoint to sprite-B.

**Pattern: Virgin snapshot for testing**
```bash
# Create baseline checkpoint after auth setup
sprite checkpoint create --comment "Virgin: gh auth only, no config"

# Restore before each test
sprite restore v11
```

---

## Exec Options

The exec API supports these parameters:

| Parameter | Description |
|-----------|-------------|
| `tty` | Enable TTY mode (interactive, detachable) |
| `env` | Set environment variables (`KEY=VALUE`) |
| `max_run_after_disconnect` | How long command runs after disconnect |
| `rows`, `cols` | Terminal dimensions |

TTY sessions persist after disconnect — start a dev server, disconnect, reconnect later.

---

## Network & Access

### Port forwarding

```bash
# Start server on sprite
sprite exec bash -c "cd ~/app && npm start"

# Forward port locally (separate terminal)
sprite proxy 3000

# Access at http://localhost:3000
```

### Public URL access

```bash
sprite url                        # Show current URL
sprite url update --auth public   # Make publicly accessible
sprite url update --auth sprite   # Restore auth requirement
```

### Network policy (API)

Restrict outbound access by domain:

```bash
sprite api POST /v1/sprites/{name}/policy/network \
  -d '{"rules": [{"domain": "github.com", "action": "allow"}]}'
```

---

## SDKs

Programmatic access beyond CLI:

| Language | Package | Install |
|----------|---------|---------|
| Python | `sprites-py` | `pip install sprites-py` |
| Node.js | `@fly/sprites` | `npm install @fly/sprites` |
| Go | `sprites-go` | `go get github.com/superfly/sprites-go` |
| Elixir | `sprites-ex` | `{:sprites, github: "superfly/sprites-ex"}` |

### Python example

```python
import os
from sprites import SpritesClient

client = SpritesClient(os.environ["SPRITE_TOKEN"])
output = client.sprite("my-sprite").command("ls", "-la").output()
print(output.decode())
```

**API Base:** `https://api.sprites.dev/v1/` with `Authorization: Bearer $SPRITES_TOKEN`

---

## Documentation

- [sprites.dev/api](https://sprites.dev/api) — Official API docs
- [sprites.dev](https://sprites.dev/) — Main site
- [community.fly.io](https://community.fly.io/) — Forum (search "sprites")
- CLI help: `sprite --help`, `sprite checkpoint --help`
