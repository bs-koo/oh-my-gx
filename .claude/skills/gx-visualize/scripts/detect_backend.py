#!/usr/bin/env python3
"""Detect an optional local GX visualization backend without installing anything."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from typing import Any


Command = str | os.PathLike[str] | Sequence[str | os.PathLike[str]]


def _normalize_command(command: Command) -> list[str]:
    if isinstance(command, os.PathLike):
        return [os.fspath(command)]
    if isinstance(command, str):
        parts = shlex.split(command, posix=os.name != "nt")
    else:
        parts = [os.fspath(part) for part in command]
    if not parts or any(not part for part in parts):
        raise ValueError("command must contain an executable")
    return parts


def _command_version(command: Command) -> str | None:
    try:
        argv = _normalize_command(command)
        probe = argv if any(part in {"--version", "-V"} for part in argv[1:]) else [*argv, "--version"]
        result = subprocess.run(
            probe,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (OSError, TypeError, ValueError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "unknown"


def detect_backend(
    archify_command: Command | None = None,
    *,
    node_command: Command | None = None,
    mermaid_command: Command | None = None,
) -> dict[str, Any]:
    """Return the best executable backend visible through overrides, env, or PATH."""
    explicit_archify = archify_command is not None
    explicit_mermaid = mermaid_command is not None
    archify_command = archify_command or os.environ.get("GX_ARCHIFY_COMMAND")
    mermaid_command = mermaid_command or os.environ.get("GX_MERMAID_COMMAND")

    node = node_command or shutil.which("node")
    if node is None:
        return {
            "backend": "static",
            "reason": "node executable is unavailable; Archify and Mermaid were skipped",
            "version": None,
        }
    if _command_version(node) is None:
        return {
            "backend": "static",
            "reason": "node executable candidate failed its version check; Archify and Mermaid were skipped",
            "version": None,
        }

    if archify_command is None:
        archify_path = shutil.which("archify")
        archify_command = [archify_path] if archify_path else None
    if archify_command is not None:
        version = _command_version(archify_command)
        if version is not None:
            source = "explicit override" if explicit_archify else "environment/PATH"
            return {
                "backend": "archify",
                "reason": f"Archify executable verified from {source}",
                "version": version,
            }

    if mermaid_command is None:
        mermaid_path = shutil.which("mmdc")
        mermaid_command = [mermaid_path] if mermaid_path else None
    if mermaid_command is not None:
        version = _command_version(mermaid_command)
        if version is not None:
            source = "explicit override" if explicit_mermaid else "environment/PATH"
            return {
                "backend": "mermaid",
                "reason": f"Archify unavailable; Mermaid executable verified from {source}",
                "version": version,
            }

    return {
        "backend": "static",
        "reason": "Archify and Mermaid executables are unavailable or failed version checks",
        "version": None,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(detect_backend(), ensure_ascii=False, sort_keys=True))
