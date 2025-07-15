#!/bin/bash
# Fix .desktop Exec line to remove pkexec or sudo prefixes
# Usage: ./patch_desktop_exec.sh /path/to/file.desktop
set -e

file="$1"
if [[ -z "$file" || ! -f "$file" ]]; then
    echo "Usage: $0 /path/to/file.desktop" >&2
    exit 1
fi

exec_line=$(grep -m1 '^Exec=' "$file" || true)
if [[ -z "$exec_line" ]]; then
    exit 0
fi

cmd=${exec_line#Exec=}
# remove leading pkexec or sudo and trailing arguments like pkexec env ...
cmd=${cmd#pkexec }
cmd=${cmd#sudo }
# remove 'env ' if used with pkexec env
if [[ $cmd == env* ]]; then
    cmd=${cmd#env }
fi
sed -i "s|^Exec=.*|Exec=$cmd|" "$file"
