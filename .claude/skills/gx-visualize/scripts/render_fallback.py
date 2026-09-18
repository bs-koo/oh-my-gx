#!/usr/bin/env python3
"""Render validated GX visualization IR as Korean self-contained HTML."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


BACKENDS = {"mermaid", "static"}
STATUS_LABELS = {
    "planned": "계획됨",
    "in_progress": "진행 중",
    "review": "검토 중",
    "verified": "검증됨",
    "blocked": "차단됨",
    "unknown": "확인 필요",
}
EVIDENCE_LABELS = {
    "artifact": "산출물 근거",
    "code": "코드 근거",
    "test": "테스트 근거",
    "command": "명령 근거",
    "design": "설계 근거",
    "inferred": "추정",
}
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_TOKEN = re.compile(r"\{\{(TITLE|SUMMARY|CSS|MERMAID_SECTION|STATIC_CONTENT)\}\}")


def _validator_module():
    validator_path = Path(__file__).with_name("validate_ir.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_validate_ir", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"IR 검증기를 불러올 수 없습니다: {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _load_ir(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sorted_nodes(ir: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(ir["nodes"], key=lambda node: node["id"])


def _sorted_edges(ir: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(ir["edges"], key=lambda edge: edge["id"])


def _status_badge(status: str) -> str:
    label = STATUS_LABELS.get(status, STATUS_LABELS["unknown"])
    return f'<span class="status status-{_escape(status)}">{_escape(label)}</span>'


def _legend() -> str:
    items = "".join(
        f'<li>{_status_badge(status)}</li>'
        for status in ("planned", "in_progress", "review", "verified", "blocked", "unknown")
    )
    return f'<section aria-labelledby="legend-title"><h2 id="legend-title">범례</h2><ul class="legend-list">{items}</ul></section>'


def _node_list(nodes: list[dict[str, Any]]) -> str:
    cards = []
    for node in nodes:
        technical = node.get("technical_label")
        technical_html = (
            f'<p class="technical-label"><span class="sr-only">기술 식별자: </span><code>{_escape(technical)}</code></p>'
            if technical is not None
            else ""
        )
        cards.append(
            '<li><article class="node-card">'
            f'<span class="node-id">{_escape(node["id"])}</span> '
            f'{_status_badge(node["status"])}'
            f'<h3>{_escape(node["label"])}</h3>'
            f'<p>유형: {_escape(node["kind"])}</p>{technical_html}'
            '</article></li>'
        )
    return '<section aria-labelledby="nodes-title"><h2 id="nodes-title">노드 목록</h2><ul class="node-list">' + "".join(cards) + "</ul></section>"


def _relationship_table(edges: list[dict[str, Any]]) -> str:
    rows = "".join(
        "<tr>"
        f'<td><code>{_escape(edge["id"])}</code></td>'
        f'<td><code>{_escape(edge["source"])}</code></td>'
        f'<td>{_escape(edge["relation"])}</td>'
        f'<td><code>{_escape(edge["target"])}</code></td>'
        "</tr>"
        for edge in edges
    )
    if not rows:
        rows = '<tr><td colspan="4">표시할 관계가 없습니다.</td></tr>'
    return (
        '<section aria-labelledby="relations-title"><h2 id="relations-title">관계</h2>'
        '<div class="table-wrap"><table><thead><tr><th>관계 ID</th><th>출발</th><th>관계</th><th>도착</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div></section>'
    )


def _evidence_cards(nodes: list[dict[str, Any]]) -> str:
    cards = []
    for node in nodes:
        for evidence in sorted(
            node.get("evidence", []),
            key=lambda item: (item.get("kind", ""), item.get("file", ""), item.get("line", 0)),
        ):
            kind = evidence["kind"]
            if kind == "inferred":
                detail = "파일 위치 없이 추정으로 명시된 근거입니다."
            elif "locator" in evidence:
                locator = evidence["locator"]
                if locator["type"] == "xlsx":
                    location = f'{_escape(locator["sheet"])}!{_escape(locator["cell"])}'
                else:
                    location = f'{int(locator["page"])}페이지'
                detail = f'<code>{_escape(evidence["file"])}</code> · {location}'
            else:
                detail = f'<code>{_escape(evidence["file"])}</code> · {int(evidence["line"])}행'
            cards.append(
                '<li class="evidence-card">'
                f'<p><strong>{_escape(node["id"])}</strong> — {_escape(EVIDENCE_LABELS.get(kind, kind))}</p>'
                f'<p>{detail}</p></li>'
            )
    if not cards:
        cards.append('<li class="evidence-card">등록된 근거가 없습니다.</li>')
    return '<section aria-labelledby="evidence-title"><h2 id="evidence-title">근거</h2><ul class="evidence-list">' + "".join(cards) + "</ul></section>"


def _mermaid_source(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    aliases = {node["id"]: f"n{index}" for index, node in enumerate(nodes)}
    lines = ["flowchart LR"]
    for node in nodes:
        label_parts = [node["id"], node["label"]]
        if "technical_label" in node:
            label_parts.append(node["technical_label"])
        label_parts.append(STATUS_LABELS.get(node["status"], STATUS_LABELS["unknown"]))
        label = "#10;".join(_mermaid_text(part) for part in label_parts)
        lines.append(f'  {aliases[node["id"]]}["{label}"]')
    for edge in edges:
        relation = _mermaid_text(edge["relation"])
        lines.append(f'  {aliases[edge["source"]]} -->|{relation}| {aliases[edge["target"]]}')
    return "\n".join(lines)


def _mermaid_text(value: Any) -> str:
    """Encode user text entirely as Mermaid decimal entities."""
    return "".join(f"#{ord(character)};" for character in str(value))


def _mermaid_section(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    source = _escape(_mermaid_source(nodes, edges))
    return (
        '<section aria-labelledby="mermaid-title"><h2 id="mermaid-title">Mermaid 다이어그램 소스</h2>'
        '<p class="fallback-note">다이어그램은 생성되지 않았습니다. 아래는 같은 IR의 노드 목록과 관계 표입니다.'
        ' 그림을 보려면 Archify가 필요합니다: npx -y skills add tt-a1i/archify -g</p>'
        f'<pre class="mermaid-source"><code>{source}</code></pre></section>'
    )


def _render_document(ir: dict[str, Any], backend: str) -> str:
    nodes = _sorted_nodes(ir)
    edges = _sorted_edges(ir)
    template = (TEMPLATE_DIR / "fallback.html").read_text(encoding="utf-8")
    css = (TEMPLATE_DIR / "fallback.css").read_text(encoding="utf-8")
    static_content = "\n".join((_legend(), _node_list(nodes), _relationship_table(edges), _evidence_cards(nodes)))
    mermaid_section = _mermaid_section(nodes, edges) if backend == "mermaid" else ""
    summary = f'노드 {len(nodes)}개와 관계 {len(edges)}개 · {"Mermaid + 정적 폴백" if backend == "mermaid" else "정적 HTML"}'
    replacements = {
        "TITLE": _escape(ir["title"]),
        "SUMMARY": _escape(summary),
        "CSS": css.rstrip(),
        "MERMAID_SECTION": mermaid_section,
        "STATIC_CONTENT": static_content,
    }
    return TEMPLATE_TOKEN.sub(lambda match: replacements[match.group(1)], template)


def _input_view(ir_path: Path, allowed_views: set[str]) -> str:
    """Return a valid input view when readable, otherwise the stable default."""
    try:
        payload = _load_ir(ir_path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "trace"
    if isinstance(payload, dict) and payload.get("view") in allowed_views:
        return payload["view"]
    return "trace"


def render(
    ir_path: Path | str,
    output_dir: Path | str,
    backend: str,
    project_root: Path | str | None = None,
    output_name: str | None = None,
) -> dict[str, str]:
    """Validate and render an IR document, returning stable artifact paths.

    `output_name`, when given, replaces the view-derived filename stem (`{view}.html`,
    `{view}.receipt.json`) with `{output_name}.*` — see render_archify.render_archify()
    for why (shared `output_dir`, several documents of the same `view`). Omit it to keep
    the existing `{view}.*` behavior.
    """
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of: {', '.join(sorted(BACKENDS))}")

    ir_path = Path(ir_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    validator = _validator_module()
    receipt = validator.validate(ir_path, project_root=project_root)
    view = _input_view(ir_path, validator.VIEWS)
    stem = output_name if output_name is not None else view
    if receipt["status"] == "valid":
        ir = _load_ir(ir_path)
    receipt_path = output_dir / f"{stem}.receipt.json"
    receipt_payload = {**receipt, "backend": backend}
    receipt_path.write_text(
        json.dumps(receipt_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if receipt["status"] != "valid":
        (output_dir / f"{stem}.html").unlink(missing_ok=True)
        raise ValueError("IR 검증 실패: " + "; ".join(receipt["errors"]))

    html_path = output_dir / f"{stem}.html"
    html_path.write_text(_render_document(ir, backend), encoding="utf-8")
    return {"html_path": str(html_path), "backend": backend, "receipt_path": str(receipt_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="GX 시각화 IR을 self-contained HTML로 렌더링합니다.")
    parser.add_argument("ir_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="mermaid")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output-name")
    args = parser.parse_args()
    try:
        result = render(
            args.ir_path, args.output_dir, args.backend,
            project_root=args.project_root, output_name=args.output_name,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
