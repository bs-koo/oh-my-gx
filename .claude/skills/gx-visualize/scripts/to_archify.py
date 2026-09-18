#!/usr/bin/env python3
"""Convert a GX visualization IR document into an Archify input document.

GX IR (`nodes`/`edges`) and Archify's architecture schema (`components`/
`connections`) share no field names — Archify's top level is
`additionalProperties: false`, so passing GX IR through unchanged always
fails validation. See docs/reports/2026-09-18-archify-ir-schema.md for the
measured schema this conversion targets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


KIND_TO_TYPE = {
    "screen": "frontend",
    "api": "backend",
    "service": "backend",
    "repository": "backend",
    "table": "database",
}

KIND_TO_COL = {
    "screen": 0,
    "api": 1,
    "service": 2,
    "repository": 3,
    "table": 4,
}

MAX_SOURCES = 3


def _sources(evidence: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    sources = []
    for item in evidence:
        if item.get("kind") != "code":
            continue
        file_name = item.get("file")
        if not isinstance(file_name, str):
            continue
        source: dict[str, Any] = {"path": file_name}
        if "line" in item:
            source["line"] = item["line"]
        sources.append(source)
        if len(sources) == MAX_SOURCES:
            break
    return sources or None


def cited_paths(ir: dict[str, Any]) -> list[str]:
    """Return the sorted, deduplicated file paths that `to_archify` would cite as sources.

    Mirrors `_sources`'s per-node cap so a caller can scope a git dirty check to exactly
    the paths that would be published as evidence, instead of the whole working tree.
    """
    paths: set[str] = set()
    for node in ir.get("nodes", []):
        sources = _sources(node.get("evidence", []))
        if sources:
            paths.update(source["path"] for source in sources)
    return sorted(paths)


def _component(node: dict[str, Any], row: int, col: int, include_sources: bool) -> dict[str, Any]:
    component: dict[str, Any] = {
        "id": node["id"],
        "type": KIND_TO_TYPE.get(node.get("kind"), "external"),
        "label": node["label"],
        "row": row,
        "col": col,
    }
    if "technical_label" in node:
        component["sublabel"] = node["technical_label"]
    if include_sources:
        sources = _sources(node.get("evidence", []))
        if sources is not None:
            component["sources"] = sources
    return component


def _connection(edge: dict[str, Any]) -> dict[str, Any]:
    connection: dict[str, Any] = {"from": edge["source"], "to": edge["target"]}
    if "relation" in edge:
        connection["label"] = edge["relation"]
    return connection


def to_archify(ir: dict[str, Any], kind: str, repository: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert a validated GX IR document into an Archify `<kind>` document.

    `repository` gates `component.sources` and `meta.repository` together: Archify
    requires a pinned `{url, revision}` (verified against a real repo via --repo-root)
    the instant any component carries `sources`, so the two must appear or disappear
    as one unit (docs/reports/2026-09-18-archify-ir-schema.md §3.3). Pass `None` when
    the caller has no 40-hex commit SHA to pin (e.g. a non-git project).
    """
    nodes = sorted(ir.get("nodes", []), key=lambda node: node["id"])
    edges = sorted(ir.get("edges", []), key=lambda edge: edge["id"])

    # 요청 경로 하나가 한 가로줄에 놓이도록, 열 안에서의 순서를 "첫 수신 연결의
    # 출발지가 배정된 행"으로 정한다 (id만으로 매기면 서로 다른 체인의 노드가
    # 우연히 같은 행에 섞인다). 수신 연결이 없는 노드(기준 열)는 id 순으로 둔다.
    node_col = {node["id"]: KIND_TO_COL.get(node.get("kind"), 0) for node in nodes}
    first_incoming_source: dict[str, str] = {}
    for edge in edges:
        first_incoming_source.setdefault(edge["target"], edge["source"])

    nodes_by_col: dict[int, list[dict[str, Any]]] = {}
    for node in nodes:
        nodes_by_col.setdefault(node_col[node["id"]], []).append(node)

    row_of: dict[str, int] = {}

    def _sort_key(node: dict[str, Any]) -> tuple[int, int, str]:
        source_row = row_of.get(first_incoming_source.get(node["id"], ""))
        return (0, source_row, node["id"]) if source_row is not None else (1, 0, node["id"])

    for col in sorted(nodes_by_col):
        for row, node in enumerate(sorted(nodes_by_col[col], key=_sort_key)):
            row_of[node["id"]] = row

    components = [_component(node, row_of[node["id"]], node_col[node["id"]], repository is not None) for node in nodes]
    meta: dict[str, Any] = {"title": ir.get("title", ""), "locale": "en"}
    if repository is not None:
        meta["repository"] = repository
    return {
        "schema_version": 1,
        "diagram_type": kind,
        "meta": meta,
        "layout": {"mode": "grid", "cols": 5, "gapX": 90, "gapY": 50, "cellW": 150, "cellH": 64},
        "components": components,
        "connections": [_connection(edge) for edge in edges],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a GX visualization IR into an Archify input document")
    parser.add_argument("ir_path", type=Path)
    parser.add_argument("kind")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ir = json.loads(args.ir_path.read_text(encoding="utf-8"))
    rendered = json.dumps(to_archify(ir, args.kind), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
