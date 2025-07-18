# wireguard-ui

wireguard-ui for Linux Mint and similar systems.

## Setup

Run the provided `install.sh` as root to install required packages and configure the system:

```bash
sudo ./install.sh
```


The script installs the `wireguard` and `firejail` packages, creates the `novpn` group and adds your user to it, configures an IP rule for that group, and allows root GUI applications via `xhost` for both X11 and Wayland sessions. When run during package installation and no non-root user is detected, user-specific steps are skipped automatically. The installer also invokes `patch_desktop_exec.sh`, which strips any `sudo`/`pkexec` wrapper and related environment assignments from the program's `.desktop` entry so the GUI starts as your normal user.


When installing the Debian package built with `build_deb.sh`, this setup script
is executed automatically so no additional steps are required.

During installation a helper script automatically cleans the
`/usr/share/applications/wireguard-ui.desktop` entry so the application starts
under the regular user instead of `root`. This prevents losing your GTK theme
and icons when launching from the desktop menu.

## Building a Debian package

Use the provided `build_deb.sh` script to create a `.deb` installer. You can optionally pass a version number:

```bash
./build_deb.sh 0.1.0
```

The resulting `wireguard-ui_<version>_all.deb` will be created in the current directory and can be installed with `dpkg -i` on Ubuntu or Linux Mint.
