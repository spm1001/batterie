# Packages to Remove by Role

## Raspberry Pi OS - Headless Jump Box

```bash
# Video/media
mkvtoolnix

# Compiler toolchain
gcc g++ gcc-14 g++-14
gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
gcc-14-aarch64-linux-gnu g++-14-aarch64-linux-gnu

# Pi-specific bloat
rpi-connect-lite

# Modem support
modemmanager

# Bluetooth
bluez bluetooth pi-bluetooth

# Audio
alsa-utils

# mDNS (if not using)
avahi-daemon

# Man pages (saves processing on updates)
man-db
```

## Services to Disable (Headless)

```bash
# Serial console
sudo systemctl disable serial-getty@ttyS0

# Bluetooth
sudo systemctl disable bluetooth

# LLMNR (Windows name resolution)
# Edit /etc/systemd/resolved.conf: LLMNR=no
sudo systemctl restart systemd-resolved
```

## General Debian Server

Consider removing:
- `man-db` - if truly headless
- `triggerhappy` - RPi input daemon, useless headless

Consider disabling:
- LLMNR (port 5355) if not using Windows clients

## What NOT to Remove

- **swap** - keeps system stable under memory pressure
- **cron** - used by logrotate, maintenance tasks
- **systemd-timesyncd** - needed for time sync (especially Tailscale)
- **NetworkManager** - if using WiFi
