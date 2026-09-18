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
import math
import re
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

# 다음 세 상수는 Archify의 architecture 렌더러가 label 적합성을 판정하는 공식을
# 그대로 옮긴 것이다(~/.agents/skills/archify/renderers/architecture/render-architecture.mjs:65,
# :366-368). 컴포넌트 기본 크기는 그 렌더러 안에 하드코딩돼 있고 layout.cellW/cellH와는
# 무관하다: `estLabelW = textUnits(label) * 6.6; estLabelW > width + 8`이면 검증이
# 실패한다. sublabel·tag는 같은 파일 :372-382에서 minimumNodeTextWidth로 축소 구제를
# 받으므로 이 계산에 넣지 않는다.
_DEFAULT_COMPONENT_WIDTH = 120
_DEFAULT_COMPONENT_HEIGHT = 60
_LABEL_WIDTH_PER_UNIT = 6.6
_LABEL_FIT_MARGIN = 8

# 그리드 칸 간격 기본값. renderers/architecture/render-architecture.mjs:384-392의
# rectsOverlap(a, b, 8)이 모든 컴포넌트 쌍에 적용되므로, 같은 행에서 옆 열과 맞닿는
# 폭(stepX = cellW + gapX)이 컴포넌트 폭보다 8px 이상 넉넉해야 한다.
_DEFAULT_LAYOUT = {"mode": "grid", "cols": 5, "gapX": 90, "gapY": 50, "cellW": 150, "cellH": 64}

# renderers/shared/utils.mjs의 textUnits()가 전각으로 판정하는 코드포인트 범위를
# 그대로 옮긴 것이다 — 한글 음절(AC00-D7A3)이 포함되어 한글 라벨은 문자당 2 units다.
# 이모지 variation selector 처리(같은 함수의 나머지 절반)는 라벨에 이모지를 쓰지
# 않으므로 옮기지 않는다.
_FULLWIDTH_RE = re.compile(
    "[ᄀ-ᅟ⌚-⌛〈-〉⏩-⏬⏰⏳"
    "◽-◾☔-☕☰-☷♈-♓♿⚊-⚏"
    "⚓⚡⚪-⚫⚽-⚾⛄-⛅⛎⛔⛪"
    "⛲-⛳⛵⛺⛽✅✊-✋✨❌❎"
    "❓-❕❗➕-➗➰➿⬛-⬜⭐⭕"
    "⺀-꓏ꥠ-ꥼ가-힣豈-﫿︐-︙"
    "︰-﹯！-｠￠-￦"
    "\U00016fe0-\U00018dff\U0001aff0-\U0001afff\U0001b000-\U0001b2ff"
    "\U0001f000-\U0001faff\U00020000-\U0003fffd]"
)


def text_units(text: str) -> int:
    """Count `text` the way Archify's textUnits() does — fullwidth chars (한글 포함) cost 2."""
    return sum(2 if _FULLWIDTH_RE.match(ch) else 1 for ch in text)


def _label_width(label: str) -> int:
    """Minimum component width `label` needs to pass Archify's fit check, rounded up."""
    return math.ceil(text_units(label) * _LABEL_WIDTH_PER_UNIT - _LABEL_FIT_MARGIN)


def _component_size(label: str) -> list[int] | None:
    """`size` override for `label`, or `None` when the default 120x60 box already fits it."""
    if _label_width(label) <= _DEFAULT_COMPONENT_WIDTH:
        return None
    return [_label_width(label), _DEFAULT_COMPONENT_HEIGHT]


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
    size = _component_size(node["label"])
    if size is not None:
        component["size"] = size
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

    layout = dict(_DEFAULT_LAYOUT)
    max_width = max((c["size"][0] for c in components if "size" in c), default=_DEFAULT_COMPONENT_WIDTH)
    required_cell_w = max_width - layout["gapX"] + _LABEL_FIT_MARGIN
    if required_cell_w > layout["cellW"]:
        layout["cellW"] = required_cell_w

    meta: dict[str, Any] = {"title": ir.get("title", ""), "locale": "en"}
    if repository is not None:
        meta["repository"] = repository
    return {
        "schema_version": 1,
        "diagram_type": kind,
        "meta": meta,
        "layout": layout,
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
