# Unattended Upgrades - Repo Origin Patterns

## How to Find Origin for Any Package

```bash
# Method 1: From apt policy
apt-cache policy <package> | grep -E 'origin|http'

# Method 2: From sources lists
cat /var/lib/apt/lists/*_InRelease | grep -E '^Origin:|^Label:|^Codename:'
```

## Common Repo Patterns

Add these to `/etc/apt/apt.conf.d/50unattended-upgrades` in the `Unattended-Upgrade::Origins-Pattern` block:

### Debian (standard)
```
"origin=Debian,codename=${distro_codename}-updates";
"origin=Debian,codename=${distro_codename},label=Debian";
"origin=Debian,codename=${distro_codename},label=Debian-Security";
"origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
```

### Raspberry Pi
```
"origin=Raspberry Pi Foundation";
"origin=Raspbian";
```

### Tailscale
```
"origin=Tailscale,codename=${distro_codename}";
```

### Plex
```
"origin=Artifactory,archive=public,codename=public,label=Artifactory,component=main,site=downloads.plex.tv";
```

## Other Important Settings

```
// Reboot at 4am, not immediately
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";

// Clean up
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
```

## Timer Configuration

The systemd timers must be enabled for unattended-upgrades to actually run:

```bash
# Enable timers (usually done by dpkg-reconfigure, but verify)
sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer

# Check they're active
sudo systemctl status apt-daily.timer apt-daily-upgrade.timer

# See when they'll next run
systemctl list-timers apt-daily*
```

If upgrades aren't happening, check these timers first.

## Verification

```bash
# Dry run
sudo unattended-upgrade --dry-run

# Check logs
cat /var/log/unattended-upgrades/unattended-upgrades.log
```
