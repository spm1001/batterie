# Terminal Compatibility

## Ghostty Terminal

**Problem:** `Error opening terminal: xterm-ghostty` when using nano/vim/etc.

### Fix 1: SSH Config (Recommended)

Add to `~/.ssh/config`:
```
Host <hostname>
  SetEnv TERM=xterm-256color
```

Or for all hosts with issues:
```
Host kube.lan kube lambourn.lan lambourn
  SetEnv TERM=xterm-256color
```

### Fix 2: Install Terminfo on Remote

See: https://ghostty.org/docs/help/terminfo

```bash
# On the remote server
infocmp -x xterm-ghostty > /tmp/ghostty.terminfo
tic -x /tmp/ghostty.terminfo
```

### Fix 3: One-off Override

```bash
TERM=xterm-256color ssh user@host
```

## When This Happens

- Older Debian/Ubuntu servers don't have Ghostty's terminfo
- Affects any curses-based tool: nano, vim, htop, less, etc.
- SSH config fix is cleanest - applied automatically on connect
