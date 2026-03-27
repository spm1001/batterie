# Sprite Troubleshooting

## Contents

1. [OuterClaude/InnerClaude Issues](#outerclaude-innerclaude-issues)
2. [Authentication Issues](#authentication-issues)
3. [Command Execution Issues](#command-execution-issues)
4. [Network Issues](#network-issues)

---

## OuterClaude/InnerClaude Issues

### tmux capture-pane shows nothing / minimal output

**Cause:** Claude uses alternate screen buffer which `capture-pane` doesn't capture.

**Fix:** Use `pipe-pane` instead:

```bash
# Set up continuous capture
tmux pipe-pane -t innerClaude "cat > /tmp/claude-output.txt"

# Read captured output
cat /tmp/claude-output.txt | strings | tail -100
```

### Claude won't start in tmux session

**Cause:** NVM not sourced, so `node` not in PATH.

**Fix:** Source NVM before running Claude:

```bash
tmux send-keys -t innerClaude 'export NVM_DIR="/.sprite/languages/node/nvm" && . "$NVM_DIR/nvm.sh" && nvm use default' Enter
sleep 3
tmux send-keys -t innerClaude "claude" Enter
```

### `claude -p` returns empty output

**Cause:** Claude's `-p` mode needs a TTY for output.

**Fix:** Use `script` wrapper:

```bash
sprite exec bash -c 'script -q /dev/null -c "claude -p \"your prompt\"" 2>&1'
```

### OAuth token expired / "Please run /login"

**Cause:** Token in checkpoint was already expired, or token expired since checkpoint was created.

**Fix:** Either:

1. Export token as environment variable:
   ```bash
   export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
   ```

2. Or run `claude setup-token`:
   ```bash
   tmux send-keys -t innerClaude "claude setup-token" Enter
   # Capture auth URL from output, have user authorize, paste code back
   ```

### Prompts not rendering / can't see dialogs

**Cause:** Output capture not set up, or not waiting long enough.

**Fix:**
1. Ensure `pipe-pane` is set up BEFORE starting Claude
2. Add sufficient `sleep` between commands (Claude UI takes time to render)
3. Use `strings` to filter escape codes: `cat /tmp/output.txt | strings | tail -100`

---

## Authentication Issues

### "Permission denied (publickey)"

**Cause:** Using SSH URL without SSH key, or gh not authenticated.

**Fix:**
1. Use HTTPS URLs instead of SSH
2. Run `gh auth login` to authenticate

### "could not read Username"

**Cause:** Git credential helper not configured.

**Fix:** Run `gh auth login` to configure credential helper.

### `uv tool install` fails on private repo

**Cause:** uv uses libgit2 which doesn't inherit git config.

**Fix:** Run `gh auth setup-git` — this sets up the credential helper that uv needs.

### "Keychain is locked" / "Keychain access denied" (macOS)

**Note:** This applies to local macOS, not sprites (which are Linux).

**Fix:** Unlock Keychain or use `TODOIST_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` environment variables.

---

## Command Execution Issues

### "Command not found" in sprite exec

**Cause:** Command needs full path or bash wrapper.

**Fix:** Use `bash -c`:

```bash
sprite exec bash -c "cd ~/project && npm test"
```

### Checkpoint not found

**Cause:** Checkpoints are per-sprite.

**Fix:** Use checkpoints from the same sprite. Cannot restore sprite-A's checkpoint to sprite-B.

### beads "legacy database" error

**Cause:** Old beads format (deprecated).

**Fix:** Beads is deprecated. Migrate to bon with `bon migrate --from-beads .beads/`.

### "can't set the locale" warnings

**Cause:** Locale not configured on fresh sprite.

**Fix:**

```bash
sudo locale-gen en_US.UTF-8
echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc
```

---

## Network Issues

### Port not accessible

**Cause:** Port not forwarded to local machine.

**Fix:** Use `sprite proxy`:

```bash
sprite proxy 3000
# Now access http://localhost:3000
```

### "Request timed out" / "Could not connect to Todoist"

**Cause:** Network issues or API problems.

**Fix:** Check network connection, retry in a moment.

### Sprite URL not working

**Cause:** Auth requirement blocking access.

**Fix:** Make public if needed:

```bash
sprite url update --auth public
```

---

## Quick Diagnostic

Run this to diagnose common issues:

```bash
sprite exec bash -c '
echo "=== Node/NVM ==="
which node || echo "node not found"
node --version 2>/dev/null || echo "node not working"

echo ""
echo "=== Claude ==="
which claude || echo "claude not found"
claude --version 2>/dev/null || echo "claude not working"

echo ""
echo "=== GitHub Auth ==="
gh auth status 2>&1 | head -5

echo ""
echo "=== Locale ==="
locale 2>&1 | head -3
'
```
