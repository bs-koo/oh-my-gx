#!/usr/bin/env python3
"""Run optional Archify validation/delivery with truthful local fallbacks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
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
        raise ValueError("archify_command must contain an executable")
    return parts


def _fallback_module():
    path = Path(__file__).with_name("render_fallback.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_render_fallback", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"fallback renderer could not be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validator_module():
    path = Path(__file__).with_name("validate_ir.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_validate_ir", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"IR validator could not be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render_fallback(
    ir_path: Path,
    output_dir: Path,
    backend: str,
    project_root: Path | str | None = None,
) -> dict[str, str]:
    return _fallback_module().render(ir_path, output_dir, backend, project_root=project_root)


def _view(ir_path: Path) -> str:
    try:
        payload = json.loads(ir_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "trace"
    view = payload.get("view") if isinstance(payload, dict) else None
    return view if view in {"trace", "progress", "impact", "service", "sequence"} else "trace"


_DIAGRAM_TYPES = {"service": "architecture", "sequence": "sequence"}


def diagram_type(view: str) -> str:
    return _DIAGRAM_TYPES.get(view, "architecture")


def _run(command: list[str], phase: str, artifact_path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
        return {
            "backend": "archify",
            "phase": phase,
            "status": "valid" if result.returncode == 0 else "failed",
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "artifact_path": str(artifact_path),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "backend": "archify",
            "phase": phase,
            "status": "failed",
            "command": command,
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "artifact_path": str(artifact_path),
        }


def _write_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fallback(
    ir_path: Path,
    output_dir: Path,
    receipt_path: Path,
    attempts: list[dict[str, Any]],
    project_root: Path | str | None = None,
) -> dict[str, str]:
    html_path = output_dir / f"{_view(ir_path)}.html"
    for backend in ("mermaid", "static"):
        try:
            if project_root is None:
                result = _render_fallback(ir_path, output_dir, backend)
            else:
                result = _render_fallback(ir_path, output_dir, backend, project_root=project_root)
        except Exception as exc:  # preserve diagnostics and continue the explicit chain
            attempts.append(
                {
                    "backend": backend,
                    "phase": "render",
                    "status": "failed",
                    "command": None,
                    "exit_code": None,
                    "stdout": "",
                    "stderr": str(exc),
                    "artifact_path": str(html_path),
                }
            )
            continue

        fallback_receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
        attempts.append(
            {
                "backend": backend,
                "phase": "render",
                "status": "valid",
                "command": None,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "artifact_path": result["html_path"],
            }
        )
        failed_archify = next(
            attempt
            for attempt in reversed(attempts)
            if attempt["backend"] == "archify" and attempt["status"] == "failed"
        )
        payload = {
            **fallback_receipt,
            "status": "fallback",
            "backend": backend,
            "artifact_path": result["html_path"],
            "command": failed_archify["command"],
            "exit_code": failed_archify["exit_code"],
            "attempts": attempts,
        }
        _write_receipt(receipt_path, payload)
        return {**result, "receipt_path": str(receipt_path)}

    html_path.unlink(missing_ok=True)
    failed_archify = next(
        attempt
        for attempt in reversed(attempts)
        if attempt["backend"] == "archify" and attempt["status"] == "failed"
    )
    failed = {
        "status": "failed",
        "backend": "static",
        "artifact_path": None,
        "command": failed_archify["command"],
        "exit_code": failed_archify["exit_code"],
        "attempts": attempts,
    }
    _write_receipt(receipt_path, failed)
    raise RuntimeError("Archify, Mermaid, and static rendering all failed")


def render_archify(
    ir_path: Path | str,
    output_dir: Path | str,
    archify_command: Command,
    project_root: Path | str | None = None,
) -> dict[str, str]:
    """Validate and deliver with Archify, then fall back without hiding failures."""
    ir_path = Path(ir_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    view = _view(ir_path)
    html_path = output_dir / f"{view}.html"
    receipt_path = output_dir / f"{view}.receipt.json"
    html_path.unlink(missing_ok=True)

    local_receipt = _validator_module().validate(ir_path, project_root=project_root)
    if local_receipt["status"] != "valid":
        failed_receipt = {
            **local_receipt,
            "backend": None,
            "artifact_path": None,
            "command": None,
            "exit_code": None,
            "attempts": [
                {
                    "backend": "local-validator",
                    "phase": "validate",
                    "status": "failed",
                    "command": None,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "\n".join(local_receipt["errors"]),
                    "artifact_path": None,
                }
            ],
        }
        _write_receipt(receipt_path, failed_receipt)
        raise ValueError(f"IR validation failed; see {receipt_path}")

    command = _normalize_command(archify_command)

    kind = diagram_type(view)
    validate_command = [*command, "validate", kind, str(ir_path), "--json"]
    attempts = [_run(validate_command, "validate", html_path)]
    if attempts[-1]["status"] == "failed":
        return _fallback(ir_path, output_dir, receipt_path, attempts, project_root=project_root)

    deliver_command = [*command, "deliver", kind, str(ir_path), str(html_path), "--json"]
    attempts.append(_run(deliver_command, "deliver", html_path))
    if attempts[-1]["status"] == "failed" or not html_path.is_file() or html_path.stat().st_size == 0:
        if attempts[-1]["status"] != "failed":
            attempts[-1]["status"] = "failed"
            attempts[-1]["stderr"] = "Archify returned success without a non-empty artifact"
        html_path.unlink(missing_ok=True)
        return _fallback(ir_path, output_dir, receipt_path, attempts, project_root=project_root)

    receipt = {
        "status": "valid",
        "backend": "archify",
        "artifact_path": str(html_path),
        "command": deliver_command,
        "exit_code": attempts[-1]["exit_code"],
        "attempts": attempts,
    }
    _write_receipt(receipt_path, receipt)
    return {
        "html_path": str(html_path),
        "backend": "archify",
        "receipt_path": str(receipt_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Archify를 시도하고 GX HTML 폴백을 생성합니다.")
    parser.add_argument("ir_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--archify-command", required=True)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    try:
        result = render_archify(
            args.ir_path,
            args.output_dir,
            args.archify_command,
            project_root=args.project_root,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
