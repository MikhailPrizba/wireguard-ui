# wireguard-ui

wireguard-ui for Linux Mint and similar systems.

## Setup

Run the provided `install.sh` as root to install required packages and configure the system:

```bash
sudo ./install.sh
```

The script installs the `wireguard` and `firejail` packages, creates the `novpn` group and adds your user to it, configures an IP rule for that group, and allows root GUI applications via `xhost` for both X11 and Wayland sessions.

When installing the Debian package built with `build_deb.sh`, this setup script
is executed automatically so no additional steps are required.

## Building a Debian package

Use the provided `build_deb.sh` script to create a `.deb` installer. You can optionally pass a version number:

```bash
./build_deb.sh 0.1.0
```

The resulting `wireguard-ui_<version>_all.deb` will be created in the current directory and can be installed with `dpkg -i` on Ubuntu or Linux Mint.
