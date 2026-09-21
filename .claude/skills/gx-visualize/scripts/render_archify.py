#!/usr/bin/env python3
"""Run optional Archify validation/delivery with truthful local fallbacks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any


Command = str | os.PathLike[str] | Sequence[str | os.PathLike[str]]
_FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_URL_USERINFO_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)[^/@]+@")


def _strip_userinfo(url: str) -> str:
    """Remove an embedded `//user:pass@` credential from a URL before it reaches HTML/receipts.

    A remote checked out with credentials in the URL (CI's `x-access-token:<PAT>@...`, a
    developer's cached PAT) would otherwise copy that secret into meta.repository and the
    rendered {domain}.html verbatim (2026-09-18 final review I6, design §7). `git remote
    get-url` can also return an SSH shorthand (`git@host:org/repo.git`) with no `//`,
    which this leaves untouched — that `user@` is the SSH syntax itself, not an embedded
    secret.
    """
    return _URL_USERINFO_RE.sub(r"\1", url)


def _json_list_command(command: str) -> list[str] | None:
    """Parse `command` as a JSON array of strings, or return None if it isn't one.

    detect_backend()/ensure_archify() hand back `command` as a **list**, and CLI callers
    must serialize it to a single `--archify-command` string. The obvious serializations
    are not round-trip safe on Windows: `shlex.split(s, posix=False)` does not undo
    `subprocess.list2cmdline()`'s quoting once any argv element (e.g. an install path
    under "Program Files") contains a space, so the executable is split apart and the
    subprocess fails with WinError 5 while exit code 0 hides it (2026-09-18 final review
    I2). A JSON array round-trips exactly regardless of embedded spaces, so callers that
    serialize with `json.dumps(command)` are unaffected by shell-quoting rules at all.
    """
    stripped = command.strip()
    if not stripped.startswith("["):
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list) and parsed and all(isinstance(item, str) for item in parsed):
        return parsed
    return None


def _normalize_command(command: Command) -> list[str]:
    if isinstance(command, os.PathLike):
        return [os.fspath(command)]
    if isinstance(command, str):
        parts = _json_list_command(command)
        if parts is None:
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


def _to_archify_module():
    path = Path(__file__).with_name("to_archify.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_to_archify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Archify 변환기를 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_repository_evidence(project_root: Path | str, cited_paths: list[str]) -> dict[str, str] | None:
    """Return {url, revision, link_mode} when project_root is a git checkout with a resolvable HEAD and origin.

    Archify requires this pinned evidence to verify component.sources against the real
    repository (docs/reports/2026-09-18-archify-ir-schema.md §3.3). Returns None — not
    a failure — for non-git projects, so GX can still render without source evidence.

    `cited_paths` (from to_archify.cited_paths) scopes the dirty check to exactly the
    files that would be published as sources — not the whole working tree. A project's
    unrelated in-flight changes, including gx-visualize's own committed `.dev/` output,
    must not suppress evidence for citations that remain accurate. A *cited* path that
    is modified or untracked does block: a committed-but-modified file still passes
    Archify's blob-existence check at HEAD, but a `line` cited from the working tree may
    no longer match the committed content — a citation that looks verified but may be
    wrong. Requiring the cited paths to be clean trades that silent risk for losing
    links on those specific files, which is honest and reversible (commit, then
    re-render). Changes outside the cited paths can leave the rest of the code
    meaningfully different from the pinned revision while evidence still publishes —
    accepted, because Archify verifies each cited path and line against the revision
    itself, so each individual citation stays accurate regardless of what else moved.

    With no cited paths there is nothing to verify, so this returns None outright —
    Archify also rejects a document that declares meta.repository with zero component
    sources.
    """
    if not cited_paths:
        return None
    root = str(project_root)
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", *cited_paths],
            cwd=root, capture_output=True, text=True, shell=False, check=False,
        )
        if status.returncode != 0 or status.stdout.strip():
            return None
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, shell=False, check=False
        )
        origin = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True, shell=False, check=False
        )
    except (FileNotFoundError, OSError):
        return None
    if revision.returncode != 0 or origin.returncode != 0:
        return None
    sha = revision.stdout.strip()
    url = origin.stdout.strip()
    if not _FULL_SHA_RE.match(sha) or not url:
        return None
    return {"url": _strip_userinfo(url), "revision": sha.lower(), "link_mode": "local-only"}


def _render_fallback(
    ir_path: Path,
    output_dir: Path,
    backend: str,
    project_root: Path | str | None = None,
    output_name: str | None = None,
    snapshot_banner: bool = False,
    html_dir: Path | str | None = None,
) -> dict[str, str]:
    return _fallback_module().render(
        ir_path, output_dir, backend,
        project_root=project_root, output_name=output_name, snapshot_banner=snapshot_banner,
        html_dir=html_dir,
    )


def _view(ir_path: Path) -> str:
    try:
        payload = json.loads(ir_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "trace"
    view = payload.get("view") if isinstance(payload, dict) else None
    return view if view in {"trace", "progress", "impact", "service", "sequence"} else "trace"


_DIAGRAM_TYPES = {"service": "architecture"}


def diagram_type(view: str) -> str | None:
    """Return the Archify diagram type for `view`, or None if Archify does not serve it.

    Only `service` has a converter: Archify's architecture grid maps the service view's
    5-tier kind vocabulary (screen/api/service/repository/table); trace/progress/impact
    carry an unrelated kind vocabulary that collapses onto a single grid column and
    commonly breaches Archify's fixed component width. `sequence` has no converter
    either — to_archify only emits architecture-shaped documents (components/
    connections), but Archify's sequence schema requires participants/messages and
    rejects components/connections/layout outright; writing that converter is deferred.
    None tells render_archify to skip the Archify subprocess entirely rather than spend
    two calls guaranteed to fail.
    """
    return _DIAGRAM_TYPES.get(view)


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


def _last_failed_archify_attempt(attempts: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (attempt for attempt in reversed(attempts) if attempt["backend"] == "archify" and attempt["status"] == "failed"),
        None,
    )


def _fallback(
    ir_path: Path,
    output_dir: Path,
    receipt_path: Path,
    attempts: list[dict[str, Any]],
    project_root: Path | str | None = None,
    status: str = "fallback",
    output_name: str | None = None,
    snapshot_banner: bool = False,
    html_dir: Path | str | None = None,
) -> dict[str, str]:
    html_dir_actual = Path(html_dir) if html_dir is not None else output_dir
    html_path = html_dir_actual / f"{output_name if output_name is not None else _view(ir_path)}.html"
    for backend in ("mermaid", "static"):
        try:
            if project_root is None:
                result = _render_fallback(
                    ir_path, output_dir, backend, output_name=output_name, snapshot_banner=snapshot_banner,
                    html_dir=html_dir,
                )
            else:
                result = _render_fallback(
                    ir_path, output_dir, backend,
                    project_root=project_root, output_name=output_name, snapshot_banner=snapshot_banner,
                    html_dir=html_dir,
                )
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
        failed_archify = _last_failed_archify_attempt(attempts)
        payload = {
            **fallback_receipt,
            "status": status,
            "backend": backend,
            "artifact_path": result["html_path"],
            "command": failed_archify["command"] if failed_archify else None,
            "exit_code": failed_archify["exit_code"] if failed_archify else None,
            "attempts": attempts,
        }
        _write_receipt(receipt_path, payload)
        return {**result, "receipt_path": str(receipt_path)}

    html_path.unlink(missing_ok=True)
    failed_archify = _last_failed_archify_attempt(attempts)
    failed = {
        "status": "failed",
        "backend": "static",
        "artifact_path": None,
        "command": failed_archify["command"] if failed_archify else None,
        "exit_code": failed_archify["exit_code"] if failed_archify else None,
        "attempts": attempts,
    }
    _write_receipt(receipt_path, failed)
    raise RuntimeError("Archify, Mermaid, and static rendering all failed")


def _skip_archify(
    ir_path: Path,
    output_dir: Path,
    receipt_path: Path,
    view: str,
    project_root: Path | str | None = None,
    output_name: str | None = None,
    snapshot_banner: bool = False,
    html_dir: Path | str | None = None,
) -> dict[str, str]:
    """Render via the fallback chain without ever invoking Archify.

    Used when diagram_type(view) is None — Archify has no mapping for this view, so
    spawning validate/deliver would waste two subprocess calls on a document guaranteed
    to fail layout validation. The receipt records this as not_applicable, not failed:
    no Archify attempt actually happened.
    """
    attempts = [
        {
            "backend": "archify",
            "phase": "validate",
            "status": "not_applicable",
            "command": None,
            "exit_code": None,
            "stdout": "",
            "stderr": f"Archify does not support the '{view}' view; only the service view is attempted.",
            "artifact_path": None,
        }
    ]
    return _fallback(
        ir_path, output_dir, receipt_path, attempts,
        project_root=project_root, status="not_applicable", output_name=output_name,
        snapshot_banner=snapshot_banner, html_dir=html_dir,
    )


def render_archify(
    ir_path: Path | str,
    output_dir: Path | str,
    archify_command: Command,
    project_root: Path | str | None = None,
    output_name: str | None = None,
    snapshot_banner: bool = False,
    html_dir: Path | str | None = None,
) -> dict[str, str]:
    """Validate and deliver with Archify, then fall back without hiding failures.

    `output_name`, when given, replaces the view-derived filename stem (`{view}.html`,
    `{view}.receipt.json`, `{view}.archify.json`) with `{output_name}.*` — so a caller
    rendering several IR documents that share the same `view` into one `output_dir`
    (e.g. one per domain under `--scope all`) doesn't have each render overwrite the
    last. `view` itself still decides Archify eligibility (`diagram_type`); only the
    on-disk filenames change. Omit it to keep the existing `{view}.*` behavior.

    `snapshot_banner`, when true, inserts the `--scope session` snapshot banner into the
    HTML - the fallback chain forwards it to render_fallback.render(); the Archify
    success path below injects it into Archify's own HTML after delivery, since Archify
    has no concept of this GX-only banner.

    `html_dir`, when given, writes `{stem}.html`(Archify 성공 시)와 폴백 HTML을 거기에
    쓴다 — `.receipt.json`·`.archify.json`은 여전히 `output_dir`에 남는다. `--scope all`은
    이걸로 `${MAP_DIR}/domains/`와 `${MAP_DIR}/receipts/`를 분리한다. 생략하면
    `output_dir`과 같아 기존 평평한 구조 그대로다.
    """
    ir_path = Path(ir_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_dir_actual = Path(html_dir) if html_dir is not None else output_dir
    html_dir_actual.mkdir(parents=True, exist_ok=True)
    view = _view(ir_path)
    stem = output_name if output_name is not None else view
    html_path = html_dir_actual / f"{stem}.html"
    receipt_path = output_dir / f"{stem}.receipt.json"

    local_receipt = _validator_module().validate(ir_path, project_root=project_root)
    if local_receipt["status"] != "valid":
        # 이전에 성공적으로 렌더된 {stem}.html은 여기서 지우지 않는다 - 이번 IR 검증
        # 실패는 새 산출물을 만들 수 없다는 뜻일 뿐, 지난 실행의 정상 그림을 무효로
        # 만들지 않는다. SKILL.md가 이미 약속하는 "검증 실패 시 이전 IR을 덮어쓰지
        # 않는다"와 같은 원칙을 HTML에도 지킨다(2026-09-18 최종 리뷰 I8).
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

    # 검증을 통과해 새로 렌더를 시도하는 경우에만 이전 산출물을 지운다 - 곧바로
    # Archify 또는 폴백이 같은 이름에 새 HTML을 쓴다.
    html_path.unlink(missing_ok=True)

    kind = diagram_type(view)
    if kind is None:
        return _skip_archify(
            ir_path, output_dir, receipt_path, view,
            project_root=project_root, output_name=output_name, snapshot_banner=snapshot_banner,
            html_dir=html_dir,
        )

    command = _normalize_command(archify_command)

    to_archify_module = _to_archify_module()
    ir_document = json.loads(ir_path.read_text(encoding="utf-8-sig"))
    cited_paths = to_archify_module.cited_paths(ir_document)
    repository = _git_repository_evidence(project_root, cited_paths) if project_root is not None else None
    archify_payload = output_dir / f"{stem}.archify.json"
    archify_document = to_archify_module.to_archify(ir_document, kind, repository=repository)
    archify_payload.write_text(
        json.dumps(archify_document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    repo_root_args = ["--repo-root", str(project_root)] if repository is not None else []

    validate_command = [*command, "validate", kind, str(archify_payload), "--json", *repo_root_args]
    attempts = [_run(validate_command, "validate", html_path)]
    if attempts[-1]["status"] == "failed":
        return _fallback(
            ir_path, output_dir, receipt_path, attempts,
            project_root=project_root, output_name=output_name, snapshot_banner=snapshot_banner,
            html_dir=html_dir,
        )

    deliver_command = [*command, "deliver", kind, str(archify_payload), str(html_path), "--json", *repo_root_args]
    attempts.append(_run(deliver_command, "deliver", html_path))
    if attempts[-1]["status"] == "failed" or not html_path.is_file() or html_path.stat().st_size == 0:
        if attempts[-1]["status"] != "failed":
            attempts[-1]["status"] = "failed"
            attempts[-1]["stderr"] = "Archify returned success without a non-empty artifact"
        html_path.unlink(missing_ok=True)
        return _fallback(
            ir_path, output_dir, receipt_path, attempts,
            project_root=project_root, output_name=output_name, snapshot_banner=snapshot_banner,
            html_dir=html_dir,
        )

    if snapshot_banner:
        # Archify가 만든 HTML은 이 스킬의 배너 개념을 모른다 - 전달 후 그 산출물에
        # 직접 삽입한다. render_fallback.render()가 쓰는 것과 같은 함수라 폴백
        # 경로와 동일한 방식으로 붙는다(2026-09-18 최종 리뷰 I7).
        fallback_module = _fallback_module()
        banner = fallback_module.snapshot_banner_html(project_root)
        html_path.write_text(
            fallback_module.inject_snapshot_banner(html_path.read_text(encoding="utf-8"), banner),
            encoding="utf-8",
        )

    receipt = {
        "status": "valid",
        "backend": "archify",
        "artifact_path": str(html_path),
        "command": deliver_command,
        "exit_code": attempts[-1]["exit_code"],
        "attempts": attempts,
        # 폴백 경로(render_fallback.render)는 local_receipt를 그대로 펼쳐 missing_inputs를
        # 이어받는다 - archify 성공 receipt는 별도로 조립되므로 여기서 명시적으로 옮겨야
        # 두 경로가 대칭이 된다(2026-09-18 최종 리뷰 I1).
        "missing_inputs": local_receipt["missing_inputs"],
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
    parser.add_argument("--output-name")
    parser.add_argument("--snapshot-banner", action="store_true")
    parser.add_argument("--html-dir", type=Path)
    args = parser.parse_args()
    try:
        result = render_archify(
            args.ir_path,
            args.output_dir,
            args.archify_command,
            project_root=args.project_root,
            output_name=args.output_name,
            snapshot_banner=args.snapshot_banner,
            html_dir=args.html_dir,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
