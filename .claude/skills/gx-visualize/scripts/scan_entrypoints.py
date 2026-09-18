#!/usr/bin/env python3
"""Extract entrypoint chains (screen -> api -> service -> repository -> table)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = frozenset(
    {".git", ".dev", ".superpowers", "__pycache__", "node_modules", "build", "target", "out", "dist"}
)

MAPPING_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "ANY",
}

_MAPPING_RE = re.compile(
    r'@(' + "|".join(MAPPING_ANNOTATIONS) + r')\s*\(\s*(?:value\s*=\s*)?"([^"]*)"'
)
_CLASS_MAPPING_RE = re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]*)"')
_METHOD_RE = re.compile(r"\b(?:public|protected)\s+[\w<>\[\],.\s]+?\s+(\w+)\s*\(")
_CLASS_RE = re.compile(r"\b(?:class|interface)\s+(\w+)")
_FIELD_RE = re.compile(r"\bprivate\s+(?:final\s+)?(\w+)\s+\w+\s*;")


def node_id(kind: str, rel_path: str, symbol: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", rel_path).strip("-")
    return f"gx-{kind}-{slug}--{symbol}"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_excluded(path: Path, root: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts[:-1])


def _node(kind: str, rel_path: str, symbol: str, label: str, line: int, technical: str | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id(kind, rel_path, symbol),
        "kind": kind,
        "label": label,
        "status": "unknown",
        "evidence": [{"kind": "code", "file": rel_path, "line": line}],
    }
    if technical:
        node["technical_label"] = technical
    return node


def _class_kind(text: str) -> str | None:
    if "@RestController" in text or "@Controller" in text:
        return "controller"
    if "@Service" in text:
        return "service"
    if "@Repository" in text or "@Mapper" in text:
        return "repository"
    return None


def _scan_java(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rel_path = _rel(path, root)
    kind = _class_kind(text)
    if kind is None:
        return [], []

    class_match = _CLASS_RE.search(text)
    if class_match is None:
        return [], []
    class_name = class_match.group(1)
    class_line = text[: class_match.start()].count("\n") + 1

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    if kind == "controller":
        class_text_before = text[: class_match.start()]
        class_mapping = _CLASS_MAPPING_RE.search(class_text_before)
        class_prefix = class_mapping.group(1) if class_mapping else ""

        owner_ids: list[str] = []
        for index, line in enumerate(lines):
            mapping = _MAPPING_RE.search(line)
            if mapping is None:
                continue
            verb = MAPPING_ANNOTATIONS[mapping.group(1)]
            method_path = mapping.group(2)

            if class_prefix and method_path:
                http_path = class_prefix.rstrip("/") + "/" + method_path.lstrip("/")
            else:
                http_path = class_prefix + method_path

            method_name = ""
            for following in lines[index + 1 : index + 6]:
                method = _METHOD_RE.search(following)
                if method:
                    method_name = method.group(1)
                    break
            if not method_name:
                continue
            node = _node("api", rel_path, method_name, f"{class_name}.{method_name}", index + 1, f"{verb} {http_path}")
            nodes.append(node)
            owner_ids.append(node["id"])
        collaborators = _FIELD_RE.findall(text)
        for owner in owner_ids:
            for collaborator in collaborators:
                edges.append({"source": owner, "target": collaborator, "relation": "calls"})
    else:
        nodes.append(_node(kind, rel_path, class_name, class_name, class_line))
        source = nodes[0]["id"]
        for collaborator in _FIELD_RE.findall(text):
            edges.append({"source": source, "target": collaborator, "relation": "calls"})

    return nodes, edges


def _resolve_edges(nodes: list[dict[str, Any]], raw_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol = {node["id"].split("--")[-1]: node["id"] for node in nodes}
    resolved: dict[str, dict[str, Any]] = {}
    for edge in raw_edges:
        target = by_symbol.get(edge["target"])
        if target is None or target == edge["source"]:
            continue
        edge_id = f"{edge['source']}->{target}"
        resolved[edge_id] = {
            "id": edge_id,
            "source": edge["source"],
            "target": target,
            "relation": edge["relation"],
        }
    return [resolved[key] for key in sorted(resolved)]


def scan(project_root: Path | str, changed_files: list[str] | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    if changed_files is None:
        candidates = sorted(root.rglob("*.java"))
    else:
        candidates = [root / name for name in sorted(changed_files) if (root / name).suffix == ".java"]

    nodes: list[dict[str, Any]] = []
    raw_edges: list[dict[str, Any]] = []
    files: dict[str, list[str]] = {}

    for path in candidates:
        if not path.is_file():
            continue
        if _is_excluded(path, root):
            continue
        file_nodes, file_edges = _scan_java(path, root)
        if not file_nodes:
            continue
        rel_path = _rel(path, root)
        files[rel_path] = sorted(node["id"] for node in file_nodes)
        nodes.extend(file_nodes)
        raw_edges.extend(file_edges)

    nodes.sort(key=lambda node: node["id"])
    return {"nodes": nodes, "edges": _resolve_edges(nodes, raw_edges), "files": dict(sorted(files.items()))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan entrypoint chains into GX visualization candidates.")
    parser.add_argument("project_root")
    parser.add_argument("--changed-file", action="append", dest="changed_files")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = scan(args.project_root, args.changed_files)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
