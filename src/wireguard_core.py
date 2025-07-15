#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WireGuard core: minimal privileges, root helper and all business logic."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

# ───────── root-process helpers ───────── #
_ROOT_HELPER: subprocess.Popen | None = None
_VALID_WG_NAME: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_.-]+$")


def _start_root_helper() -> None:
    """Launch this file in root-helper mode via pkexec."""
    global _ROOT_HELPER
    if _ROOT_HELPER is not None:
        return
    exepath = str(Path(__file__).resolve())
    _ROOT_HELPER = subprocess.Popen(
        ["pkexec", sys.executable, exepath, "--root-helper"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def _root_helper_main() -> None:  # launched via pkexec
    def _reply(**payload: str | int | None) -> None:
        print(json.dumps(payload, ensure_ascii=False), flush=True)

    for line in sys.stdin:
        if not line:
            break
        try:
            cmd = json.loads(line)
            if not isinstance(cmd, list) or not all(
                isinstance(x, str) for x in cmd
            ):
                _reply(error="Invalid request format")
                continue
            proc = subprocess.run(
                cmd, capture_output=True, text=True, check=False
            )
            _reply(
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
            )
        except Exception as exc:  # pylint: disable=broad-except
            _reply(error=str(exc))
    sys.exit(0)


# ───────── тонкая обёртка вокруг subprocess ───────── #
def _run_command(
    cmd: list[str], *, use_root: bool = False
) -> tuple[str | None, str | None]:
    """Execute *cmd*. Delegate to helper when use_root=True."""
    if use_root:
        _start_root_helper()
        helper = _ROOT_HELPER
        if helper is None or helper.stdin is None or helper.stdout is None:
            return None, "Failed to start root process."
        try:
            json.dump(cmd, helper.stdin)
            helper.stdin.write("\n")
            helper.stdin.flush()
            line = helper.stdout.readline()
            if not line:
                return None, "Root process exited unexpectedly."
            result = json.loads(line)
            if result.get("error") is not None:
                return None, str(result["error"])
            if result.get("returncode", 1) != 0:
                return (
                    None,
                    result.get("stderr")
                    or f"Код выхода: {result.get('returncode')}",
                )
            return result.get("stdout", "").strip(), None
        except Exception as exc:  # pylint: disable=broad-except
            return None, f"IPC error: {exc}"

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return (
                None,
                proc.stderr.strip() or f"Код выхода: {proc.returncode}",
            )
        return proc.stdout.strip(), None
    except FileNotFoundError:
        return None, f"Executable '{cmd[0]}' not found."
    except Exception as exc:  # pylint: disable=broad-except
        return None, f"Unknown error: {exc}"


# ───────── основной класс ───────── #
class WireGuard:
    """Инкапсулирует работу с WireGuard."""

    VALID_WG_NAME = _VALID_WG_NAME

    def list_configs(self) -> list[str]:
        cmd = [
            "find",
            "/etc/wireguard",
            "-maxdepth",
            "1",
            "-type",
            "f",
            "-name",
            "*.conf",
            "-printf",
            "%f\n",
        ]
        out, err = _run_command(cmd, use_root=True)
        if err:
            raise RuntimeError(err)
        return (
            [
                f.removesuffix(".conf")
                for f in out.splitlines()
                if self.VALID_WG_NAME.fullmatch(f.removesuffix(".conf"))
            ]
            if out
            else []
        )

    def active_interfaces(self) -> list[str]:
        out, _ = _run_command(["wg", "show", "interfaces"])
        return out.split() if out else []

    # действия
    def connect(self, name: str) -> None:
        _, err = _run_command(["wg-quick", "up", name], use_root=True)
        if err:
            raise RuntimeError(err)

    def disconnect(self, name: str) -> None:
        _, err = _run_command(["wg-quick", "down", name], use_root=True)
        if err:
            raise RuntimeError(err)

    def load_config(self, file_path: str) -> None:
        src = Path(file_path)
        dest = Path("/etc/wireguard") / src.name
        if not self.VALID_WG_NAME.fullmatch(src.stem):
            raise ValueError("Invalid file name.")
        _, exists_err = _run_command(["test", "-e", str(dest)], use_root=True)
        if exists_err is None:
            raise FileExistsError("File already exists.")
        _, err = _run_command(
            ["install", "-m", "600", str(src), str(dest)], use_root=True
        )
        if err:
            raise RuntimeError(err)

    def tunnel_info(self, name: str) -> str:
        out, err = _run_command(["wg", "show", name], use_root=True)
        return err or out or "Failed to get information."


# export internal utilities needed by GUI
__all__ = [
    "WireGuard",
    "_start_root_helper",
    "_root_helper_main",
    "_run_command",
]

# entry point for pkexec
if __name__ == "__main__":
    if "--root-helper" in sys.argv:
        _root_helper_main()
    else:
        print("wireguard_core: library; run main.py", file=sys.stderr)
