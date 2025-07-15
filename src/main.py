#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point: launches GUI and root helper."""

import sys
from PyQt6.QtWidgets import QApplication

from wireguard_core import _start_root_helper
from gui import MainWindow

if __name__ == "__main__":
    _start_root_helper()  # request polkit before window appears
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
