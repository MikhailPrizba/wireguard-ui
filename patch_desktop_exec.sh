#!/bin/bash
# Fix .desktop Exec line by removing pkexec/sudo wrappers and any
# environment variable assignments.
# Usage: ./patch_desktop_exec.sh /path/to/file.desktop
set -euo pipefail

file="${1:?Usage: $0 /path/to/file.desktop}"
if [[ ! -f $file ]]; then
    echo "File '$file' not found" >&2
    exit 1
fi

exec_line=$(grep -m1 '^Exec=' "$file" || true)
if [[ -z "$exec_line" ]]; then
    exit 0
fi

cmd=${exec_line#Exec=}
# remove optional pkexec/sudo prefixes
cmd=${cmd#pkexec }
cmd=${cmd#sudo }
# strip "env" wrapper if present
if [[ $cmd == env\ * ]]; then
    cmd=${cmd#env }
fi
# drop leading VAR=value assignments
cmd=$(printf '%s\n' "$cmd" | sed -E 's/^([A-Za-z_][A-Za-z0-9_]*=[^ ]* ?)*//')

sed -i "s|^Exec=.*|Exec=$cmd|" "$file"
