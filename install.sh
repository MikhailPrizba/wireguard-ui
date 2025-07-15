#!/bin/bash

set -e

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" >&2
    exit 1
fi

install_pkg() {
    if ! dpkg -s "$1" >/dev/null 2>&1; then
        echo "Installing $1..."
        apt-get update -y
        apt-get install -y "$1"
    else
        echo "$1 already installed."
    fi
}

install_pkg wireguard
install_pkg firejail

group=novpn
user=${SUDO_USER:-$USER}

if ! getent group "$group" >/dev/null; then
    groupadd "$group"
fi

if ! id -nG "$user" | grep -qw "$group"; then
    gpasswd -a "$user" "$group"
fi

gid=$(getent group "$group" | cut -d: -f3)

if ! ip rule list | grep -q "uidrange $gid-$gid"; then
    ip rule add uidrange "$gid-$gid" lookup main priority 1000
fi

mkdir -p /etc/iproute2/rules.d
rule_file=/etc/iproute2/rules.d/novpn.conf
if ! grep -q "uidrange $gid-$gid" "$rule_file" 2>/dev/null; then
    echo "from all uidrange $gid-$gid lookup main priority 1000" > "$rule_file"
fi

session_type=${XDG_SESSION_TYPE:-$(loginctl show-session $XDG_SESSION_ID -p Type --value 2>/dev/null || echo "")}
if [[ "$session_type" == "x11" || "$session_type" == "wayland" ]]; then
    if command -v xhost >/dev/null && [ -n "${DISPLAY:-}" ]; then
        sudo -u "$user" xhost +SI:localuser:root || true
    fi
fi

echo "Setup complete."
