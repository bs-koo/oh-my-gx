#!/usr/bin/env python3
"""Mark what changed since a base ref by comparing two entrypoint scans.

이번 사이클에서 무엇이 새로 생기고 바뀌었는지를 줄 단위 diff가 아니라 **두 스캔의
비교**로 판정한다(설계서 §5.8.1). 노드 ID는 (종류, 경로, 심볼)로 정해지고 줄 번호를
포함하지 않으므로, 기준 시점 트리를 같은 스캐너로 한 번 더 스캔하면 새로 생긴
노드·관계가 ID 차집합으로 나온다. 줄 단위 diff는 컨트롤러 한 파일에 엔드포인트가
여럿일 때 파일 전체를 칠하거나, 선언 줄만 보면 새 호출 관계를 놓친다.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path
from typing import Any

SCANNED_SUFFIXES = (".java", ".jsp", ".xml")


class ChangeBaseError(RuntimeError):
    """기준 시점을 정할 수 없다 - 호출자는 변경 표시를 생략하고 이 메시지를 보고한다."""


def _scanner():
    path = Path(__file__).with_name("scan_entrypoints.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_scan_for_changes", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"스캐너를 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(cwd: Path | str, *args: str, stdin: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(["git", *args], cwd=str(cwd), input=stdin, capture_output=True, check=False)
    except OSError as exc:
        raise ChangeBaseError(f"git을 실행할 수 없습니다: {exc}") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip() or f"종료 코드 {result.returncode}"
        raise ChangeBaseError(f"git {args[0]} 실패: {message}")
    return result.stdout


def resolve_base(project_root: Path | str, since_ref: str) -> dict[str, str]:
    """`since_ref`와 HEAD의 공통 조상 커밋, 저장소 최상위, 프로젝트 루트의 접두 경로를 구한다."""
    # `-`로 시작하는 값은 git이 옵션으로 해석한다 - ref로 넘기지 않는다.
    if not since_ref or since_ref.startswith("-"):
        raise ChangeBaseError(f"기준 ref가 올바르지 않습니다: {since_ref!r}")
    root = Path(project_root).resolve()
    top = _git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    prefix = _git(root, "rev-parse", "--show-prefix").decode("utf-8").strip()
    commit = _git(root, "merge-base", since_ref, "HEAD").decode("utf-8").strip()
    return {"ref": since_ref, "commit": commit, "top": top, "prefix": prefix}


def extract_base_tree(base: dict[str, str], destination: Path) -> Path:
    """기준 커밋의 스캔 대상 소스만 `destination`에 꺼내고, 프로젝트 루트에 해당하는 경로를 반환한다.

    `git archive`는 pathspec 하나라도 매치가 없으면(예: JSP가 없는 프로젝트) 전체가
    실패한다. 그래서 목록은 `ls-tree -z`로 받아 파이썬에서 거르고(-z라 한국어 경로가
    인용되지 않는다), 내용은 `cat-file --batch` 프로세스 하나로 받는다 - 파일마다 git을
    띄우지 않는다. 작업 트리·인덱스는 건드리지 않는다.
    """
    top = base["top"]
    pathspec = [base["prefix"]] if base["prefix"] else []
    listing = _git(top, "ls-tree", "-r", "-z", "--name-only", base["commit"], "--", *pathspec)
    paths = [
        raw for raw in listing.split(b"\0")
        if raw and raw.decode("utf-8", errors="replace").endswith(SCANNED_SUFFIXES)
    ]
    destination = destination.resolve()
    if paths:
        request = b"".join(base["commit"].encode("ascii") + b":" + raw + b"\n" for raw in paths)
        data = _git(top, "cat-file", "--batch", stdin=request)
        offset = 0
        for raw in paths:
            header_end = data.index(b"\n", offset)
            header = data[offset:header_end].split(b" ")
            offset = header_end + 1
            if len(header) != 3 or header[1] != b"blob":
                continue  # missing·submodule 등 - 내용이 따라오지 않는다
            size = int(header[2])
            content = data[offset : offset + size]
            offset += size + 1  # 내용 뒤의 LF
            target = (destination / raw.decode("utf-8", errors="replace")).resolve()
            try:
                target.relative_to(destination)
            except ValueError:
                continue  # 트리 밖을 가리키는 경로는 쓰지 않는다
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            except (OSError, UnicodeError):
                continue
    project = destination / base["prefix"] if base["prefix"] else destination
    project.mkdir(parents=True, exist_ok=True)
    return project


def mark_changes(head: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """`head`의 노드·엣지에 `change`를 표시하고(제자리 수정) 요약을 반환한다.

    - 신규 노드: `head`에만 있는 ID
    - 변경 노드: 양쪽에 있고 `technical_label`(API의 HTTP 경로) 또는 나가는 엣지 ID 집합이 다름
    - 신규 엣지: `head`에만 있는 엣지 ID
    - 삭제: `base`에만 있는 테이블 외 노드 - 그릴 수 없으므로 목록으로만 돌려준다
    구조가 바뀐 것만 표시한다. 메서드 본문만 바뀐 경우는 그림이 달라지지 않는다.
    """
    base_nodes = {node["id"]: node for node in base.get("nodes", [])}
    base_edge_ids = {edge["id"] for edge in base.get("edges", [])}
    base_out: dict[str, set[str]] = {}
    for edge in base.get("edges", []):
        base_out.setdefault(edge["source"], set()).add(edge["id"])
    head_out: dict[str, set[str]] = {}
    for edge in head.get("edges", []):
        head_out.setdefault(edge["source"], set()).add(edge["id"])

    added = changed = 0
    for node in head.get("nodes", []):
        previous = base_nodes.get(node["id"])
        if previous is None:
            node["change"] = "added"
            added += 1
        elif previous.get("technical_label") != node.get("technical_label") or base_out.get(
            node["id"], set()
        ) != head_out.get(node["id"], set()):
            node["change"] = "changed"
            changed += 1

    added_edges = 0
    for edge in head.get("edges", []):
        if edge["id"] not in base_edge_ids:
            edge["change"] = "added"
            added_edges += 1

    head_ids = {node["id"] for node in head.get("nodes", [])}
    removed = [
        {"id": node["id"], "kind": node["kind"], "label": node["label"]}
        for node in base.get("nodes", [])
        if node["id"] not in head_ids and node.get("kind") != "table"
    ]
    return {"added": added, "changed": changed, "added_edges": added_edges, "removed": removed}


def compute_changes(project_root: Path | str, since_ref: str, head: dict[str, Any]) -> dict[str, Any]:
    """기준 시점 트리를 스캔해 `head`에 변경을 표시한다. 기준을 정할 수 없으면 표시 없이 이유를 반환한다."""
    try:
        base = resolve_base(project_root, since_ref)
        with tempfile.TemporaryDirectory(prefix="gx-visualize-base-") as temporary:
            base_scan = _scanner().scan(extract_base_tree(base, Path(temporary)))
    except ChangeBaseError as exc:
        return {"available": False, "base_ref": since_ref, "reason": str(exc)}
    summary = mark_changes(head, base_scan)
    return {"available": True, "base_ref": since_ref, "base_commit": base["commit"][:7], **summary}
