# SSH Hardening

## Quick Setup

```bash
cat <<'EOF' | sudo tee /etc/ssh/sshd_config.d/99-hardening.conf
PasswordAuthentication no
PermitRootLogin no
X11Forwarding no
EOF

# Validate before restart
sudo sshd -t

# Apply
sudo systemctl reload sshd
```

## Verification

```bash
# Check effective config
sudo sshd -T | grep -E 'passwordauth|permitroot|x11forwarding'

# Should show:
# passwordauthentication no
# permitrootlogin no
# x11forwarding no
```

## Passwordless Sudo

RPi OS default location: `/etc/sudoers.d/010_pi-nopasswd`

To add:
```bash
echo "<user> ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/010_<user>-nopasswd
sudo chmod 440 /etc/sudoers.d/010_<user>-nopasswd
```

## Pre-requisites

Before disabling password auth, ensure:
1. SSH key is installed: `~/.ssh/authorized_keys`
2. Test key login works in separate terminal
3. Keep existing session open as backup
