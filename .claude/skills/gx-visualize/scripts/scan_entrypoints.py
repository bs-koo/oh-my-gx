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
_SERVLET_RE = re.compile(r"\bextends\s+HttpServlet\b")
_WEBSERVLET_RE = re.compile(r'@WebServlet\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
_DO_METHOD_RE = re.compile(r"\b(?:protected|public)\s+void\s+(doGet|doPost)\s*\(")
_NEW_FIELD_RE = re.compile(r"\bprivate\s+final\s+(\w+)\s+\w+\s*=\s*new\s+\w+")
_FORM_ACTION_RE = re.compile(r'<form[^>]*\saction\s*=\s*"([^"]+)"', re.IGNORECASE)
_STATEMENT_RE = re.compile(r"<(select|insert|update|delete)\b[^>]*>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)

_WRITE_STATEMENTS = {"insert", "update", "delete"}
_CLASS_RE = re.compile(r"\b(?:class|interface)\s+(\w+)")
_FIELD_RE = re.compile(r"\bprivate\s+(?:final\s+)?(\w+)\s+\w+\s*;")
_COMMENT_OR_STRING_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/', re.DOTALL)


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


def _strip_comments(text: str) -> str:
    """Blank out comments and preserve string literals, keeping all offsets and line breaks.

    String literals are returned untouched so that "http://..." is never mistaken for a comment.
    Replaces every non-newline character in comments with a space to preserve line numbers.
    """
    def _blank(match: re.Match[str]) -> str:
        chunk = match.group(0)
        if chunk.startswith('"'):
            return chunk
        return "".join("\n" if ch == "\n" else " " for ch in chunk)

    return _COMMENT_OR_STRING_RE.sub(_blank, text)


def _class_kind(text: str) -> str | None:
    if "@RestController" in text or "@Controller" in text:
        return "controller"
    if "@Service" in text:
        return "service"
    if "@Repository" in text or "@Mapper" in text:
        return "repository"
    class_match = _CLASS_RE.search(text)
    if class_match:
        name = class_match.group(1)
        if name.endswith(("DAO", "Dao")):
            return "repository"
        if name.endswith(("Service", "ServiceImpl")):
            return "service"
    return None


def _scan_jsp(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    rel_path = _rel(path, root)
    symbol = path.stem
    node = _node("screen", rel_path, symbol, rel_path, 1, rel_path)
    edges = []
    for match in _FORM_ACTION_RE.finditer(text):
        edges.append({"source": node["id"], "target": match.group(1), "relation": "requests"})
    return [node], edges


def _scan_servlet(path: Path, root: Path, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    rel_path = _rel(path, root)
    class_match = _CLASS_RE.search(text)
    class_name = class_match.group(1) if class_match else path.stem
    url_match = _WEBSERVLET_RE.search(text)
    url_pattern = url_match.group(1) if url_match else class_name
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    collaborators = _FIELD_RE.findall(text) + _NEW_FIELD_RE.findall(text)
    for index, line in enumerate(lines):
        method = _DO_METHOD_RE.search(line)
        if method is None:
            continue
        verb = "GET" if method.group(1) == "doGet" else "POST"
        node = _node(
            "api", rel_path, method.group(1), f"{class_name}.{method.group(1)}", index + 1, f"{verb} {url_pattern}"
        )
        nodes.append(node)
        for collaborator in collaborators:
            edges.append({"source": node["id"], "target": collaborator, "relation": "calls"})
    return nodes, edges


def _scan_mapper_xml(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    rel_path = _rel(path, root)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for match in _STATEMENT_RE.finditer(text):
        verb = match.group(1).lower()
        relation = "writes" if verb in _WRITE_STATEMENTS else "reads"
        line = text[: match.start()].count("\n") + 1
        for table in _TABLE_RE.findall(match.group(2)):
            name = table.upper()
            node = _node("table", rel_path, name, name, line, name)
            # A table's identity is the table itself, not the mapper file that mentions it -
            # the same table referenced from another mapper must resolve to this same node.
            node["id"] = f"gx-table--{name}"
            nodes.setdefault(node["id"], node)
            edges.append({"source": rel_path, "target": node["id"], "relation": relation, "resolved": True})
    return [nodes[key] for key in sorted(nodes)], edges


def _scan_java(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    stripped_text = _strip_comments(text)
    lines = stripped_text.splitlines()
    rel_path = _rel(path, root)
    kind = _class_kind(stripped_text)
    if kind is None:
        return [], []

    class_match = _CLASS_RE.search(stripped_text)
    if class_match is None:
        return [], []
    class_name = class_match.group(1)
    class_line = stripped_text[: class_match.start()].count("\n") + 1

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    if kind == "controller":
        class_text_before = stripped_text[: class_match.start()]
        class_mapping = _CLASS_MAPPING_RE.search(class_text_before)
        class_prefix = class_mapping.group(1) if class_mapping else ""
        class_line_num = class_text_before.count("\n")

        owner_ids: list[str] = []
        for index, line in enumerate(lines):
            if index <= class_line_num:
                continue
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
        collaborators = _FIELD_RE.findall(stripped_text)
        for owner in owner_ids:
            for collaborator in collaborators:
                edges.append({"source": owner, "target": collaborator, "relation": "calls"})
    else:
        nodes.append(_node(kind, rel_path, class_name, class_name, class_line))
        source = nodes[0]["id"]
        for collaborator in _FIELD_RE.findall(stripped_text):
            edges.append({"source": source, "target": collaborator, "relation": "calls"})

    return nodes, edges


def _node_dir(by_id: dict[str, dict[str, Any]], node_id: str) -> str:
    node = by_id.get(node_id)
    if node is None:
        return ""
    file = node["evidence"][0]["file"]
    return file.rsplit("/", 1)[0] if "/" in file else ""


def _resolve_edges(nodes: list[dict[str, Any]], raw_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {node["id"]: node for node in nodes}
    by_symbol: dict[str, list[str]] = {}
    for node in nodes:
        by_symbol.setdefault(node["id"].split("--")[-1], []).append(node["id"])
    by_path = {
        node.get("technical_label", "").split(" ", 1)[-1]: node["id"]
        for node in nodes
        if node["kind"] == "api"
    }

    resolved: dict[str, dict[str, Any]] = {}
    for edge in raw_edges:
        if edge.get("resolved"):
            target = edge["target"]
        else:
            candidates = by_symbol.get(edge["target"], [])
            if len(candidates) == 1:
                target = candidates[0]
            elif len(candidates) > 1:
                source_dir = _node_dir(by_id, edge["source"])
                same_dir = [c for c in candidates if _node_dir(by_id, c) == source_dir]
                target = same_dir[0] if len(same_dir) == 1 else None
            else:
                target = None
            if target is None:
                target = by_path.get(edge["target"])
        source = edge["source"]
        if target is None or target == source:
            continue
        # IR invariant: an edge is only emitted when both endpoints are real nodes. A
        # dangling reference (e.g. an unresolved symbol, or a raw file path left over from
        # an unmatched mapper-to-DAO correction) must be dropped, not passed through.
        if source not in by_id or target not in by_id:
            continue
        edge_id = f"{source}->{target}:{edge['relation']}"
        resolved[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "relation": edge["relation"],
        }
    return [resolved[key] for key in sorted(resolved)]


def scan(project_root: Path | str, changed_files: list[str] | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    suffixes = (".java", ".jsp", ".xml")
    if changed_files is None:
        candidates = sorted(p for p in root.rglob("*") if p.suffix in suffixes)
    else:
        candidates = [root / name for name in sorted(changed_files) if (root / name).suffix in suffixes]

    nodes: list[dict[str, Any]] = []
    node_ids_seen: set[str] = set()
    raw_edges: list[dict[str, Any]] = []
    files: dict[str, list[str]] = {}

    for path in candidates:
        if not path.is_file():
            continue
        if _is_excluded(path, root):
            continue
        if path.suffix == ".jsp":
            file_nodes, file_edges = _scan_jsp(path, root)
        elif path.suffix == ".xml":
            file_nodes, file_edges = _scan_mapper_xml(path, root)
        else:
            stripped_text = _strip_comments(path.read_text(encoding="utf-8"))
            if _SERVLET_RE.search(stripped_text):
                file_nodes, file_edges = _scan_servlet(path, root, stripped_text)
            else:
                file_nodes, file_edges = _scan_java(path, root)
        if not file_nodes:
            continue
        rel_path = _rel(path, root)
        files[rel_path] = sorted(node["id"] for node in file_nodes)
        # A node id (e.g. a table identified by name alone) can be produced by more than one
        # file - keep the first occurrence as the single node and let later files only add edges.
        for node in file_nodes:
            if node["id"] not in node_ids_seen:
                node_ids_seen.add(node["id"])
                nodes.append(node)
        raw_edges.extend(file_edges)

    nodes.sort(key=lambda node: node["id"])

    dao_by_stem = {node["id"].split("--")[-1]: node["id"] for node in nodes if node["kind"] == "repository"}
    for edge in raw_edges:
        if isinstance(edge["source"], str) and edge["source"].endswith(".xml"):
            stem = Path(edge["source"]).stem.replace("Mapper", "DAO")
            edge["source"] = dao_by_stem.get(stem, dao_by_stem.get(Path(edge["source"]).stem, edge["source"]))

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
