#!/usr/bin/env python3
"""Build the single entry-point index HTML for the accumulated architecture map.

`--scope all`이 도메인마다 `domains/{domain}.html`을 따로 만들면(실측: SEF 8도메인)
사용자는 32개 파일 중 무엇부터 열어야 할지 모른다(2026-09-21 사용자 리뷰: "파일이
너무 많아서 뭐가 뭔지도 잘 모르겠어"). 이 스크립트는 `ir/`와 `receipts/`를 읽어
`아키텍처-맵.html` 한 장으로 요약한다 - 파일 목록이 아니라 도메인마다 판단에 필요한
정보(노드 수, 그림/표 여부, 누락 건수)를 준다.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
IR_SUFFIX = ".ir.json"
RECEIPT_SUFFIX = ".receipt.json"

# archify·mermaid 모두 실제 그림을 그린다(mermaid는 그림 아래에 노드·관계 표도
# 함께 보여준다). static은 표만 있다. 셋 다 아니면(receipt 없음/backend 미기록)
# 산출물 자체가 없다는 뜻이므로 "실패"로 표시한다 - 빈칸으로 남기지 않는다.
DIAGRAM_BACKENDS = {"archify", "mermaid"}
BACKEND_LABELS = {"archify": "그림", "mermaid": "표 + 그림", "static": "표"}
STATUS_LABELS = {"valid": "통과", "fallback": "폴백", "not_applicable": "폴백", "failed": "실패"}


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _fallback_module():
    path = Path(__file__).with_name("render_fallback.py")
    spec = importlib.util.spec_from_file_location("gx_visualize_render_fallback_for_index", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"fallback renderer를 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _domain_name(ir_path: Path) -> str:
    name = ir_path.name
    return name[: -len(IR_SUFFIX)] if name.endswith(IR_SUFFIX) else ir_path.stem


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _evidence_files(ir: dict[str, Any]) -> set[str]:
    files: set[str] = set()
    for node in ir.get("nodes", []) if isinstance(ir.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        for item in node.get("evidence", []) if isinstance(node.get("evidence"), list) else []:
            if isinstance(item, dict) and item.get("kind") == "code" and isinstance(item.get("file"), str):
                files.add(item["file"])
    return files


def _collect_domains(map_dir: Path) -> list[dict[str, Any]]:
    ir_dir = map_dir / "ir"
    receipts_dir = map_dir / "receipts"
    domains: list[dict[str, Any]] = []
    for ir_path in sorted(ir_dir.glob(f"*{IR_SUFFIX}")):
        domain = _domain_name(ir_path)
        ir = _load_json(ir_path) or {}
        receipt = _load_json(receipts_dir / f"{domain}{RECEIPT_SUFFIX}") or {}
        nodes = ir.get("nodes", [])
        edges = ir.get("edges", [])
        missing_inputs = ir.get("missing_inputs", [])
        unresolved_edges = ir.get("unresolved_edges", [])
        domains.append(
            {
                "domain": domain,
                "node_count": len(nodes) if isinstance(nodes, list) else 0,
                "edge_count": len(edges) if isinstance(edges, list) else 0,
                "missing_count": len(missing_inputs) if isinstance(missing_inputs, list) else 0,
                "unresolved_count": len(unresolved_edges) if isinstance(unresolved_edges, list) else 0,
                "backend": receipt.get("backend"),
                "status": receipt.get("status"),
                "evidence_files": _evidence_files(ir),
            }
        )
    return domains


def _domain_card(entry: dict[str, Any]) -> str:
    domain = entry["domain"]
    backend = entry["backend"]
    status = entry["status"]
    if backend in DIAGRAM_BACKENDS:
        css_class = "diagram"
    elif backend == "static":
        css_class = "table"
    else:
        css_class = "failed"
    diagram_label = BACKEND_LABELS.get(backend, "산출물 없음")
    status_label = STATUS_LABELS.get(status, "확인 필요")
    backend_text = backend if backend else "없음"
    missing_text = "누락 없음" if entry["missing_count"] == 0 else f'누락 입력 {entry["missing_count"]}건'
    unresolved_text = "누락 없음" if entry["unresolved_count"] == 0 else f'미해소 관계 {entry["unresolved_count"]}건'
    return (
        f'<li><article class="domain-card domain-{css_class}">'
        f'<h3>{_escape(domain)}</h3>'
        f'<p class="domain-kind">{_escape(diagram_label)} · 백엔드 <code>{_escape(backend_text)}</code> · {_escape(status_label)}</p>'
        f'<p>노드 {entry["node_count"]}개 · 관계 {entry["edge_count"]}개</p>'
        f'<p>{_escape(missing_text)} · {_escape(unresolved_text)}</p>'
        f'<p><a href="domains/{_escape(domain)}.html">{_escape(domain)}.html 열기</a></p>'
        "</article></li>"
    )


def build_index(map_dir: Path | str, project_root: Path | str | None = None) -> Path:
    """`map_dir`의 `ir/`·`receipts/`를 읽어 `아키텍처-맵.html` 인덱스를 만들고 그 경로를 반환한다."""
    map_dir = Path(map_dir)
    domains = _collect_domains(map_dir)

    node_total = sum(entry["node_count"] for entry in domains)
    edge_total = sum(entry["edge_count"] for entry in domains)
    diagram_count = sum(1 for entry in domains if entry["backend"] in DIAGRAM_BACKENDS)
    table_only_count = sum(1 for entry in domains if entry["backend"] == "static")
    evidence_files: set[str] = set()
    for entry in domains:
        evidence_files |= entry.pop("evidence_files")

    fallback = _fallback_module()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha = fallback._short_head(project_root)
    revision_text = f" · 커밋 {_escape(sha)}" if sha else ""
    summary = (
        f"도메인 {len(domains)}개 · 근거로 인용된 소스 파일 {len(evidence_files)}개 · "
        f"노드 {node_total}개 · 관계 {edge_total}개 · 그림 {diagram_count}개 · 표 {table_only_count}개 · "
        f"생성 시각 {generated_at}{revision_text}"
    )

    if domains:
        cards = "".join(_domain_card(entry) for entry in domains)
        body = f'<section aria-labelledby="domains-title"><h2 id="domains-title">도메인</h2><ul class="domain-list">{cards}</ul></section>'
    else:
        body = '<p class="fallback-note">생성된 도메인 산출물이 없습니다.</p>'

    template = (TEMPLATE_DIR / "fallback.html").read_text(encoding="utf-8")
    css = (TEMPLATE_DIR / "fallback.css").read_text(encoding="utf-8")
    replacements = {
        "TITLE": "아키텍처 맵",
        "SUMMARY": _escape(summary),
        "CSS": css.rstrip(),
        "MERMAID_SECTION": "",
        "STATIC_CONTENT": body,
    }
    document = fallback.TEMPLATE_TOKEN.sub(lambda match: replacements[match.group(1)], template)

    index_path = map_dir / "아키텍처-맵.html"
    index_path.write_text(document, encoding="utf-8")
    return index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="누적 아키텍처 맵의 인덱스 HTML(아키텍처-맵.html)을 만듭니다.")
    parser.add_argument("map_dir", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    index_path = build_index(args.map_dir, project_root=args.project_root)
    print(json.dumps({"index_path": str(index_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
