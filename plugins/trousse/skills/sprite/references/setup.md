# Sprite Setup & Bootstrap

## Contents

1. [What Sprites Are](#what-sprites-are)
2. [First-Time Setup](#first-time-setup)
3. [Full Bootstrap Workflow](#full-bootstrap-workflow)
4. [Ghostty Terminal Support](#ghostty-terminal-support)

---

## What Sprites Are

- Persistent Ubuntu VMs with auto-hibernate (no charge when sleeping)
- Wake instantly on any command
- Checkpoints capture full filesystem state (milliseconds, copy-on-write)
- **Pre-installed:** Claude Code, gh, Python, Node.js, Go
- **NOT pre-installed:** uv, bon, locale config, Ghostty terminfo

### Sprite States

| State | Description |
|-------|-------------|
| `cold` | Hibernated, no resources consumed |
| `warm` | Waking up |
| `running` | Active, executing commands |

---

## First-Time Setup

Fresh sprites have `gh` but not authenticated. Run these steps once per sprite:

```bash
# 1. Authenticate with GitHub (interactive)
gh auth login

# 2. CRITICAL: Enable git credential helper for uv/pip
gh auth setup-git

# 3. Fix locale (prevents "can't set locale" errors)
sudo locale-gen en_US.UTF-8
echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc

# 4. Install uv (not pre-installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 5. Install bon (work tracker)
uv tool install git+https://github.com/spm1001/bon@main

# 6. Clone config (HTTPS works with gh auth)
rm -rf ~/.claude
git clone --recurse-submodules https://github.com/spm1001/claude-config.git ~/.claude

# 7. Run setup
cd ~/.claude && ./scripts/setup-machine.sh

# 8. Checkpoint so you don't repeat this
sprite checkpoint create --comment "Fresh setup with gh, uv, bon, locale"
```

---

## Full Bootstrap Workflow

### Create and configure a new sprite

```bash
# Create sprite
sprite create my-sprite
sprite use my-sprite

# GitHub auth (follow browser flow)
sprite exec gh auth login
sprite exec gh auth setup-git

# Full setup in one command
sprite exec bash -c "
  sudo locale-gen en_US.UTF-8 &&
  echo 'export LANG=en_US.UTF-8' >> ~/.bashrc &&
  echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc &&
  curl -LsSf https://astral.sh/uv/install.sh | sh &&
  rm -rf ~/.claude &&
  git clone --recurse-submodules https://github.com/spm1001/claude-config.git ~/.claude &&
  cd ~/.claude && ./scripts/setup-machine.sh
"

# Save checkpoint
sprite checkpoint create --comment "Full setup: gh, uv, locale, config"
```

### Quick bootstrap (minimal)

For testing workflows where you just need GitHub auth:

```bash
sprite create test-sprite
sprite use test-sprite
sprite exec gh auth login
sprite exec gh auth setup-git
sprite checkpoint create --comment "Minimal: gh auth only"
```

### Sync config changes

When `~/.claude` config is updated upstream:

```bash
sprite exec bash -c "cd ~/.claude && git pull origin main"
```

---

## Ghostty Terminal Support

If using [Ghostty](https://ghostty.org/) locally, sprites won't have the `xterm-ghostty` terminfo entry.

### Fix: Copy terminfo from local machine

```bash
# On local machine
infocmp -x xterm-ghostty > /tmp/ghostty.terminfo

# Copy to sprite and install
cat /tmp/ghostty.terminfo | sprite exec bash -c 'cat > /tmp/ghostty.terminfo && tic -x /tmp/ghostty.terminfo'

# Verify
sprite exec infocmp xterm-ghostty
```

### Alternative: Set fallback TERM

Add to sprite's `~/.bashrc`:

```bash
export TERM=xterm-256color
```

---

## Empirical Learnings

| Finding | Implication |
|---------|-------------|
| Fresh sprites have `gh` but not authenticated | Need `gh auth login` before cloning private repos |
| `gh auth` ≠ git credential helper | Must run `gh auth setup-git` for uv/pip access |
| uv uses libgit2, not git CLI | Won't inherit git config; needs credential helper explicitly |
| HTTPS + gh credential helper works | Use HTTPS URLs, not SSH |
| Auth survives checkpoints | Checkpoint after `gh auth login` to preserve |
| Locale not configured by default | Causes "can't set locale" warnings |
| Claude needs NVM sourced in tmux | Add NVM setup before running `claude` |
