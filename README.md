# wireguard-ui

wireguard-ui for Linux Mint and similar systems.

## Setup

Run the provided `install.sh` as root to install required packages and configure the system:

```bash
sudo ./install.sh
```

The script installs the `wireguard` and `firejail` packages, creates the `novpn` group and adds your user to it, configures an IP rule for that group, and allows root GUI applications via `xhost` for both X11 and Wayland sessions.
