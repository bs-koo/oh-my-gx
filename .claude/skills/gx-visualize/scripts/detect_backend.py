#!/usr/bin/env python3
"""Detect a local GX visualization backend, installing Archify once if it is missing."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
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


def _archify_doctor_ok(command: Command) -> bool:
    """Archify has no working `--version` (exit 2, "Unknown command"); `doctor` is the real probe.

    docs/reports/2026-09-18-archify-ir-schema.md §1: `doctor` prints 15 `[ok]` lines and
    "Archify is ready." with exit 0 on a working install. Mermaid's `mmdc --version`
    works fine and is left on `_command_version` -- only Archify needed a different probe.
    """
    try:
        argv = [*_normalize_command(command), "doctor"]
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
    except (OSError, TypeError, ValueError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and "Archify is ready" in (result.stdout or "")


def _archify_version(command: Command) -> str | None:
    """Best-effort version lookup: `doctor` carries no version, so read package.json instead.

    Only works when `command` names an actual `.../bin/archify.mjs`. Returns None rather
    than a guessed value when the layout does not match -- no fabricated versions.
    """
    try:
        argv = _normalize_command(command)
    except ValueError:
        return None
    for part in argv:
        candidate = Path(str(part))
        if candidate.name == "archify.mjs" and candidate.parent.name == "bin":
            try:
                data = json.loads((candidate.parent.parent / "package.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            version = data.get("version") if isinstance(data, dict) else None
            return version if isinstance(version, str) else None
    return None


# Real installs live under the home directory, never PATH: archify's package.json is
# "private": true, so there is no npm-published binary to put on PATH
# (docs/reports/2026-09-18-archify-ir-schema.md §1). `~/.claude/skills/archify` is a
# symlink to `~/.agents/skills/archify`; both are checked and the first real file wins.
_ARCHIFY_CANDIDATES: tuple[Path, ...] = (
    Path.home() / ".agents" / "skills" / "archify" / "bin" / "archify.mjs",
    Path.home() / ".claude" / "skills" / "archify" / "bin" / "archify.mjs",
)
_ARCHIFY_INSTALL_COMMAND: list[str] = ["npx", "-y", "skills", "add", "tt-a1i/archify", "-g"]


def _installed_archify_command() -> list[str] | None:
    node = shutil.which("node")
    if node is None:
        return None
    for candidate in _ARCHIFY_CANDIDATES:
        if candidate.is_file():
            return [node, str(candidate)]
    return None


def ensure_archify(command: Command | None = None) -> dict[str, Any]:
    """Return a working Archify command, installing it once via npx if none is found.

    Detection targets `~/.agents/skills/archify/bin/archify.mjs` and its
    `~/.claude/skills/archify` symlink -- never PATH. Success is judged by `doctor`,
    never by the install command's exit code: `npx -y skills add tt-a1i/archify -g`
    prints two unrelated PromptScript-harness failures and still exits 0
    (docs/reports/2026-09-18-archify-ir-schema.md §1). Installation is attempted at
    most once per call; a failure (network blocked, npx missing, doctor still failing
    afterwards) returns `available: False` with the attempt recorded, never an
    exception.
    """
    attempts: list[dict[str, Any]] = []

    if command is not None:
        try:
            resolved = _normalize_command(command)
        except ValueError:
            resolved = None
    else:
        resolved = _installed_archify_command()
    if resolved is not None and _archify_doctor_ok(resolved):
        return {"available": True, "command": resolved, "attempts": attempts}

    try:
        install_result = subprocess.run(
            _ARCHIFY_INSTALL_COMMAND,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=180,
        )
        attempts.append(
            {
                "phase": "install",
                "command": list(_ARCHIFY_INSTALL_COMMAND),
                "exit_code": install_result.returncode,
                "stderr": (install_result.stderr or "").strip(),
            }
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        attempts.append(
            {
                "phase": "install",
                "command": list(_ARCHIFY_INSTALL_COMMAND),
                "exit_code": None,
                "stderr": str(exc),
            }
        )
        return {"available": False, "command": None, "attempts": attempts}

    resolved = _installed_archify_command()
    if resolved is not None and _archify_doctor_ok(resolved):
        return {"available": True, "command": resolved, "attempts": attempts}
    return {"available": False, "command": None, "attempts": attempts}


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
    if archify_command is not None and _archify_doctor_ok(archify_command):
        source = "explicit override" if explicit_archify else "environment/PATH"
        return {
            "backend": "archify",
            "reason": f"Archify executable verified from {source}",
            "version": _archify_version(archify_command),
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


def main() -> int:
    """CLI entry point matching SKILL.md:85 -- ensure_archify() first, then detect_backend().

    Running `python detect_backend.py` alone must reproduce the documented auto-install
    flow: without this, the CLI only ever saw PATH/env Archify and never the
    home-directory install, so the "install automatically if missing" decision never
    actually ran when this script was invoked directly. Existing top-level keys
    (`backend`, `reason`, `version`) keep their original meaning; `archify_install`
    is additive.
    """
    ensure_result = ensure_archify()
    archify_command = ensure_result["command"] if ensure_result["available"] else None
    result = detect_backend(archify_command=archify_command)
    result["archify_install"] = ensure_result
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
