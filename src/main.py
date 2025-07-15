#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point: launches GUI and root helper."""

import os
import pwd
import sys
from PyQt6.QtWidgets import QApplication

from wireguard_core import _start_root_helper
from gui import MainWindow


def _reexec_as_user() -> None:
    """If running as root, relaunch as a regular user."""
    if os.geteuid() != 0:
        return

    user = os.environ.get("SUDO_USER") or os.environ.get("PKEXEC_UID")
    if user and user.isdigit():
        try:
            user = pwd.getpwuid(int(user)).pw_name
        except Exception:
            user = None

    if not user:
        try:
            user = os.getlogin()
        except Exception:
            user = None

    if not user:
        for entry in pwd.getpwall():
            if entry.pw_uid >= 1000 and entry.pw_name != "nobody":
                user = entry.pw_name
                break

    if not user:
        sys.exit("Unable to determine non-root user")

    os.execvp(
        "sudo",
        [
            "sudo",
            "-u",
            user,
            "-E",
            sys.executable,
            __file__,
            *sys.argv[1:],
        ],
    )

if __name__ == "__main__":
    _reexec_as_user()
    _start_root_helper()  # request polkit before window appears
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
