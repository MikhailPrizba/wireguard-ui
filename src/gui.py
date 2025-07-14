#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Графический интерфейс WireGuard с правым-кликом по туннелю:
Подключиться | Отключиться | Переименовать | Изменить конфиг.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from PyQt6.QtCore import QTimer, QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QStyle,
    QMenu,
    QInputDialog,
)

from app_launcher import AppLauncherDialog
from wireguard_core import WireGuard, _run_command


# ───────── строка списка ───────── #
class TunnelRow(QWidget):
    _ACTIVE_MARKER: Final[str] = " [АКТИВЕН]"

    def __init__(self, name: str) -> None:
        super().__init__()
        self.orig_name = name
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(6)
        self.label = QLabel(name)
        lay.addWidget(self.label)
        lay.addStretch(1)

    def mark_active(self, active: bool) -> None:
        self.label.setText(self.orig_name + (self._ACTIVE_MARKER if active else ""))


# ───────── главное окно ───────── #
class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.wg = WireGuard()
        self.setWindowTitle("WireGuard UI (secure)")
        self.resize(460, 380)

        icon_path = Path(__file__).with_name("icons/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        root = QVBoxLayout(self)

        # верхняя панель
        top = QHBoxLayout()
        self.status_label = QLabel("Статус: обновление…")
        top.addWidget(self.status_label)
        top.addStretch(1)

        def tool(icon: QIcon, tip: str, slot) -> QPushButton:
            btn = QPushButton()
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            top.addWidget(btn)
            return btn

        tool(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            "Обновить список и статус",
            self._refresh,
        )
        tool(
            QIcon.fromTheme("list-add")
            or self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Загрузить конфиг WireGuard",
            self._load_config,
        )

        self.info_button = QPushButton("⋯")
        self.info_button.setFixedSize(28, 28)
        self.info_button.setEnabled(False)
        self.info_button.setToolTip("Информация об активном подключении")
        self.info_button.clicked.connect(self._show_active_info)
        top.addWidget(self.info_button)

        root.addLayout(top)

        # список
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_ctx_menu)
        root.addWidget(self.list_widget)

        # нижние кнопки
        self.run_app_button = QPushButton("Запустить приложение вне VPN")
        self.run_app_button.clicked.connect(self._show_app_launcher)
        root.addWidget(self.run_app_button)

        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self._connect_selected)
        root.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Отключиться")
        self.disconnect_btn.clicked.connect(self._disconnect_selected)
        root.addWidget(self.disconnect_btn)

        # начальные данные + таймер
        self._refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_status)
        self.timer.start(3_000)

    # ───────── вспомогательные ───────── #
    def _populate(self, tunnels: list[str]) -> None:
        self.list_widget.clear()
        for name in tunnels:
            item = QListWidgetItem(self.list_widget)
            row = TunnelRow(name)
            item.setSizeHint(row.sizeHint())
            self.list_widget.setItemWidget(item, row)

    def _current_row(self) -> TunnelRow | None:
        item = self.list_widget.currentItem()
        return self.list_widget.itemWidget(item) if item else None  # type: ignore[return-value]

    # ───────── контекстное меню ───────── #
    def _show_ctx_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        row = self.list_widget.itemWidget(item)  # type: ignore[assignment]
        if not isinstance(row, TunnelRow):
            return
        name = row.orig_name

        menu = QMenu(self)
        a_up = menu.addAction("Подключиться")
        a_down = menu.addAction("Отключиться")
        menu.addSeparator()
        a_ren = menu.addAction("Переименовать…")
        a_edit = menu.addAction("Изменить конфиг…")

        act = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        if act is None:
            return
        if act is a_up:
            self._connect(name)
        elif act is a_down:
            self._disconnect(name)
        elif act is a_ren:
            self._rename(name)
        elif act is a_edit:
            self._edit(name)

    # ───────── действия ───────── #
    def _connect(self, name: str) -> None:
        try:
            self.wg.connect(name)
        except Exception as e:  # pylint: disable=broad-except
            self.status_label.setText(f"Ошибка подключения: {e}")
        self._update_status()

    def _disconnect(self, name: str) -> None:
        try:
            self.wg.disconnect(name)
        except Exception as e:  # pylint: disable=broad-except
            self.status_label.setText(f"Ошибка отключения: {e}")
        self._update_status()

    def _rename(self, old: str) -> None:
        new, ok = QInputDialog.getText(self, "Переименование", "Новое имя:", text=old)
        if not ok or not new or new == old:
            return
        if not WireGuard.VALID_WG_NAME.fullmatch(new):
            QMessageBox.warning(self, "WireGuard", "Недопустимое имя.")
            return
        _, err = _run_command(
            ["mv", f"/etc/wireguard/{old}.conf", f"/etc/wireguard/{new}.conf"],
            use_root=True,
        )
        if err:
            QMessageBox.critical(self, "WireGuard", f"Ошибка: {err}")
        else:
            self.status_label.setText("Файл переименован.")
            self._refresh()

    def _edit(self, name: str) -> None:
        conf = Path("/etc/wireguard") / f"{name}.conf"
        _, err = _run_command(["test", "-e", str(conf)], use_root=True)
        if err:
            QMessageBox.warning(self, "WireGuard", "Файл не найден или нет доступа.")
            return

        # 1. Открываем БЕЗ root, но через GVFS-backend admin://

        cmd = [
            "env",
            f"DISPLAY={os.environ.get('DISPLAY')}",
            f"XAUTHORITY={os.environ.get('XAUTHORITY')}",
            f"DBUS_SESSION_BUS_ADDRESS={os.environ.get('DBUS_SESSION_BUS_ADDRESS', '')}",
            "xdg-open",
            str(conf),
        ]
        _, err = _run_command(cmd, use_root=True)

        if err:
            QMessageBox.critical(
                self, "WireGuard", "Не удалось запустить редактор.\n" + err
            )

    # ───────── слоты UI ───────── #
    def _connect_selected(self) -> None:
        row = self._current_row()
        if row:
            self._connect(row.orig_name)

    def _disconnect_selected(self) -> None:
        row = self._current_row()
        if row:
            self._disconnect(row.orig_name)

    def _load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите конфиг WireGuard", "", "WireGuard (*.conf)"
        )
        if not path:
            return
        try:
            self.wg.load_config(path)
            self.status_label.setText("Конфиг загружен.")
        except Exception as e:  # pylint: disable=broad-except
            self.status_label.setText(str(e))
        self._refresh()

    # ───────── обновление списка/статуса ───────── #
    def _refresh(self) -> None:
        try:
            self._populate(self.wg.list_configs())
        except Exception as e:  # pylint: disable=broad-except
            self.status_label.setText(str(e))
        self._update_status()

    def _update_status(self) -> None:
        active = self.wg.active_interfaces()
        self.info_button.setEnabled(bool(active))
        for i in range(self.list_widget.count()):
            row = self.list_widget.itemWidget(self.list_widget.item(i))  # type: ignore[assignment]
            if isinstance(row, TunnelRow):
                row.mark_active(row.orig_name in active)
        self.status_label.setText(
            f"Статус: Подключено к {', '.join(active)}"
            if active
            else "Статус: Не подключено"
        )

    def _show_active_info(self) -> None:
        active = self.wg.active_interfaces()
        if not active:
            QMessageBox.information(self, "WireGuard", "Нет активных подключений.")
            return
        QMessageBox.information(self, "WireGuard", self.wg.tunnel_info(active[0]))

    def _show_app_launcher(self) -> None:
        dialog = AppLauncherDialog(self)
        dialog.exec()
