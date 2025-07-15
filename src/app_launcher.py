#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import subprocess
from typing import NamedTuple

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
)

from xdg import DesktopEntry


class AppInfo(NamedTuple):
    name: str
    exec_cmd: str
    icon: str | None


class AppLauncherDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Launch app outside VPN")
        self.setMinimumSize(400, 500)

        self.apps: list[AppInfo] = []

        # --- Layout & Widgets ---
        layout = QVBoxLayout(self)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search applications...")
        self.search_input.textChanged.connect(self._filter_apps)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._load_apps()

    def _load_apps(self):
        """Finds and loads all valid .desktop applications by scanning standard directories."""
        self.apps = []
        seen_apps = set()

        app_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]

        desktop_files = []
        for app_dir in app_dirs:
            if not os.path.isdir(app_dir):
                continue

            pattern = os.path.join(app_dir, "**", "*.desktop")
            desktop_files.extend(glob.glob(pattern, recursive=True))

        for path in desktop_files:
            try:
                entry = DesktopEntry.DesktopEntry(path)
                name = entry.getName()

                if entry.getNoDisplay() or entry.get("Hidden") == "true":
                    continue
                if not entry.getExec():
                    continue
                if entry.getTerminal():
                    continue
                if name in seen_apps:
                    continue

                seen_apps.add(name)
                app_info = AppInfo(
                    name=name,
                    exec_cmd=entry.getExec(),
                    icon=entry.getIcon(),
                )
                self.apps.append(app_info)
            except Exception:
                continue

        self.apps.sort(key=lambda x: x.name.lower())
        self._populate_list(self.apps)

    def _populate_list(self, apps_to_show: list[AppInfo]):
        """Clears and fills the list widget with given apps."""
        self.list_widget.clear()
        for app in apps_to_show:
            item = QListWidgetItem(app.name)
            item.setData(Qt.ItemDataRole.UserRole, app)
            if app.icon:
                item.setIcon(QIcon.fromTheme(app.icon))
            self.list_widget.addItem(item)

    def _filter_apps(self, text: str):
        """Filters the list widget based on the search input."""
        query = text.lower()
        if not query:
            self._populate_list(self.apps)
            return

        filtered_apps = [app for app in self.apps if query in app.name.lower()]
        self._populate_list(filtered_apps)

    def _get_selected_app_command(self) -> str | None:
        """Returns the cleaned command of the selected application."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return None

        app_info: AppInfo = selected_items[0].data(Qt.ItemDataRole.UserRole)
        # Clean up the exec command, removing placeholders like %U, %f, etc.
        # We just take the first part of the command, which is usually the executable.
        base_command = app_info.exec_cmd.split(" ")[0]
        return base_command

    @staticmethod
    def launch_app(app_command: str) -> None:
        """
        Launches the given application command outside the VPN using a predefined
        shell command structure.
        """
        if not app_command:
            return

        # Using the command structure you provided
        command = f"""
        sg novpn -c '
        IF=$(ip -o -4 route show default table main | awk "{{print \$5}}"); \
        firejail --noprofile --net=$IF --dns=1.1.1.1 {app_command}
        '
        """
        # We use Popen to run in the background without blocking the GUI
        # shell=True is required for the complex command with pipes and command substitution
        subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def exec(self) -> int:
        """
        Overrides the default exec to handle the launch logic.
        """
        if super().exec() == QDialog.DialogCode.Accepted:
            app_command = self._get_selected_app_command()
            if app_command:
                self.launch_app(app_command)
                return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected
