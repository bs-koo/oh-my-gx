#!/usr/bin/env python3
"""Build the single entry-point index HTML for the accumulated architecture map.

`service` 뷰(build_map.py)가 도메인마다 `domains/{domain}.html`을 따로 만들면(실측: SEF 8도메인)
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
from urllib.parse import quote


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
IR_SUFFIX = ".ir.json"
RECEIPT_SUFFIX = ".receipt.json"

# archify·mermaid 모두 실제 그림을 그린다(mermaid는 그림 아래에 노드·관계 표도
# 함께 보여준다). static은 표만 있다. 셋 다 아니면(receipt 없음/backend 미기록)
# 산출물 자체가 없다는 뜻이므로 "실패"로 표시한다 - 빈칸으로 남기지 않는다.
DIAGRAM_BACKENDS = {"archify", "mermaid"}
BACKEND_LABELS = {"archify": "그림", "mermaid": "표 + 그림", "static": "표"}
STATUS_LABELS = {"valid": "통과", "fallback": "폴백", "not_applicable": "폴백", "failed": "실패"}

# "이번 변경" 절에 도메인마다 보여 줄 항목 수. 나머지는 "외 N개"로 센다.
MAX_LISTED = 8


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


def _collect_domains(map_dir: Path, change_labels: dict[str, str]) -> list[dict[str, Any]]:
    ir_dir = map_dir / "ir"
    receipts_dir = map_dir / "receipts"
    domains: list[dict[str, Any]] = []
    manifest = _load_json(map_dir / "run-manifest.json")
    current = {entry["domain"]: entry for entry in manifest.get("map_domains", manifest.get("domains", []))} if manifest is not None else None
    names = sorted(current) if current is not None else [_domain_name(p) for p in sorted(ir_dir.glob(f"*{IR_SUFFIX}"))]
    for domain in names:
        run = current[domain] if current is not None else None
        ir = (_load_json(ir_dir / f"{domain}{IR_SUFFIX}") or {}) if run is None or run.get("ir_path") else {}
        receipt = _load_json(receipts_dir / f"{domain}{RECEIPT_SUFFIX}") or {}
        nodes = [node for node in ir.get("nodes", []) if not node.get("external_domain")]
        edges = ir.get("edges", [])
        missing_inputs = ir.get("missing_inputs", [])
        unresolved_edges = ir.get("unresolved_edges", [])
        change_nodes = sorted(
            (node["change"], str(node.get("label", "")))
            for node in (nodes if isinstance(nodes, list) else [])
            if isinstance(node, dict) and node.get("change") in change_labels
        )
        retained = run is not None and run.get("freshness") == "retained"
        if retained:
            change_nodes = []
        meta = ir.get("meta") if isinstance(ir.get("meta"), dict) else {}
        html_exists = (map_dir / "domains" / f"{domain}.html").is_file()
        failed = run is not None and (run.get("validation_status") in {"failed", "pending"} or not run.get("html_path"))
        capability = (run or receipt).get("capability")
        if failed or not html_exists:
            capability = "failed"
        elif capability is None:
            capability = "diagram" if receipt.get("backend") == "archify" else "table"
            if receipt.get("backend") == "mermaid" and (map_dir / "assets" / "mermaid.min.js").is_file():
                capability = "diagram"
        domains.append(
            {
                "domain": domain,
                "node_count": len(nodes) if isinstance(nodes, list) else 0,
                "edge_count": len(edges) if isinstance(edges, list) else 0,
                "edge_ids": {edge["id"] for edge in edges},
                "missing_count": len(missing_inputs) if isinstance(missing_inputs, list) else 0,
                "unresolved_count": len(unresolved_edges) if isinstance(unresolved_edges, list) else 0,
                "backend": receipt.get("backend"),
                "status": "failed" if failed or not html_exists else receipt.get("status"),
                "run_status": (run or {}).get("validation_status"),
                "capability": capability,
                "html_exists": html_exists and not failed,
                "nodes": nodes,
                "errors": (run or {}).get("errors", []),
                "last_good": (run or {}).get("last_good"),
                "retained": retained,
                "generated_at": (run or receipt).get("generated_at"),
                "revision": (run or receipt).get("revision"),
                "detail_anchor_prefix": (run or receipt).get("detail_anchor_prefix"),
                "diagnostics": ir.get("diagnostics", []),
                "evidence_files": _evidence_files(ir),
                "added": sum(1 for change, _ in change_nodes if change == "added"),
                "changed": sum(1 for change, _ in change_nodes if change == "changed"),
                "change_nodes": change_nodes,
                "removed": 0 if retained else len(meta.get("changes", {}).get("removed", [])),
                "removed_edges": 0 if retained else len(meta.get("changes", {}).get("removed_edges", [])),
                "changes_meta": meta.get("changes") if not retained and isinstance(meta.get("changes"), dict) else None,
            }
        )
    return domains


def _domain_card(entry: dict[str, Any]) -> str:
    domain = entry["domain"]
    backend = entry["backend"]
    status = entry["status"]
    if entry["capability"] == "diagram":
        css_class = "diagram"
    elif entry["capability"] == "table":
        css_class = "table"
    else:
        css_class = "failed"
    diagram_label = {"diagram": "그림 + 목록", "table": "목록·관계 표", "failed": "현재 산출물 없음"}.get(entry["capability"], "확인 필요")
    status_label = STATUS_LABELS.get(status, "확인 필요")
    if entry.get("run_status") == "not_generated":
        status_label = "미생성"
    backend_text = backend if backend else "없음"
    missing_text = "누락 없음" if entry["missing_count"] == 0 else f'누락 입력 {entry["missing_count"]}건'
    unresolved_text = "누락 없음" if entry["unresolved_count"] == 0 else f'미해소 관계 {entry["unresolved_count"]}건'
    has_changes = bool(entry["added"] or entry["changed"] or entry["removed"] or entry["removed_edges"])
    changed_class = " domain-changed" if has_changes else ""
    change_html = (
        f'<p class="change-line">이번 변경: 신규 {entry["added"]}개 · 변경 {entry["changed"]}개 · 삭제 {entry["removed"]}개 · 삭제 관계 {entry["removed_edges"]}개</p>'
        if has_changes else ""
    )
    endpoints = [node for node in entry["nodes"] if node.get("kind") in {"api", "screen"}]
    examples = " · ".join(str(node.get("technical_label") or node.get("label")) for node in endpoints[:3])
    context = f'<p class="entrypoint-summary">진입점 {len(endpoints)}개: {_escape(examples)}</p>' if endpoints else '<p>서비스·저장소에서 연결 관계를 살펴보세요.</p>'
    link = (f'<a href="domains/{quote(domain, safe="")}.html">{_escape(domain)} 구조 살펴보기</a>'
            if entry["html_exists"] else '<span>생성을 다시 실행해 주세요.</span>')
    if entry.get("run_status") == "not_generated":
        link = '<span>이 도메인은 아직 생성하지 않았습니다.</span>'
    errors = "".join(f'<li>{_escape(error)}</li>' for error in entry["errors"])
    last_good = entry.get("last_good")
    freshness = (f'<p>이번 실행에서 갱신하지 않은 이전 결과 · {_escape(entry.get("generated_at") or "생성 시각 미기록")} · 커밋 {_escape(entry.get("revision") or "미기록")}</p>'
                 if entry.get("retained") else "")
    if last_good and (Path(last_good.get("html_path", ""))).is_file():
        link += f' · <a href="domains/{quote(domain, safe="")}.last-good.html">이전 정상 결과</a> (현재 결과 아님 · {_escape(last_good.get("generated_at") or "생성 시각 미기록")})'
    return (
        f'<li data-domain-search="{_escape(domain + " " + examples)}"><article class="domain-card domain-{css_class}{changed_class}">'
        f'<h3>{_escape(domain)}</h3>'
        f'<p class="domain-kind">{_escape(diagram_label)} · 백엔드 <code>{_escape(backend_text)}</code> · {_escape(status_label)}</p>'
        f'<p>노드 {entry["node_count"]}개 · 관계 {entry["edge_count"]}개</p>'
        f'{context}'
        f'{freshness}'
        f'<p>{_escape(missing_text)} · {_escape(unresolved_text)}</p>'
        f"{change_html}"
        f'<p>{link}</p><ul>{errors}</ul>'
        "</article></li>"
    )


def _listed(items: list[str]) -> str:
    rest = len(items) - MAX_LISTED
    return ", ".join(items[:MAX_LISTED]) + (f" 외 {rest}개" if rest > 0 else "")


def _domain_link(domain: str, available: set[str]) -> str:
    label = _escape(domain)
    return f'<a href="domains/{quote(domain, safe="")}.html">{label}</a>' if domain in available else f'{label} (현재 결과 없음)'


def _analysis_scope_section(manifest, viewer, project_root=None):
    """개요에는 한계를 요약하고, 중복을 제거한 근거 위치는 펼쳐서 확인한다."""
    labels = {
        "dynamic-sql-branch": "조건에 따라 달라지는 SQL",
        "dynamic-sql-identifier": "실행 시 결정되는 테이블명",
        "dynamic-sql-loop": "반복문으로 생성하는 SQL",
    }
    groups = {}
    seen = set()
    for category, values in (("diagnostics", manifest.get("diagnostics", [])),
                             ("skipped", manifest.get("skipped", []))):
        for value in values if isinstance(values, list) else []:
            key = (category, json.dumps(value, ensure_ascii=False, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            item = value if isinstance(value, dict) else {"reason": str(value)}
            code = str(item.get("code", ""))
            group = groups.setdefault((category, code), {"rows": [], "reasons": []})
            reason = str(item.get("reason") or item.get("message") or "")
            if reason and reason not in group["reasons"]:
                group["reasons"].append(reason)
            evidence = item.get("evidence", [])
            evidence = list(evidence) if isinstance(evidence, list) else []
            if item.get("file"):
                evidence.insert(0, {"file": item["file"], "line": item.get("line")})
            evidence = list({json.dumps(entry, sort_keys=True): entry for entry in evidence
                             if isinstance(entry, dict)}.values())
            target = item.get("target_symbol") or item.get("target") or item.get("source")
            location = viewer.evidence_html(evidence, project_root) if evidence else ""
            detail = f'<p>{_escape(target)}</p>' if target is not None else ""
            if not reason and not location and not detail and code not in labels:
                group["reasons"].append(code or "위치 정보 없음")
            group["rows"].append(detail + location)
    if not groups:
        return ""
    sections = []
    total = 0
    for (category, code), group in groups.items():
        count = len(group["rows"])
        total += count
        title = "읽지 못한 파일" if category == "skipped" else labels.get(code, "기타 분석 항목")
        descriptions = "".join(f'<p>{_escape(reason)}</p>' for reason in group["reasons"])
        rows = "".join(f"<li>{row}</li>" for row in group["rows"] if row)
        sections.append(f'<h3>{_escape(title)} · {count}건</h3>{descriptions}' + (f'<ul>{rows}</ul>' if rows else ''))
    skipped = sum(len(group["rows"]) for (category, _), group in groups.items() if category == "skipped")
    note = (f'읽지 못해 분석에서 제외한 항목 {skipped}건이 있습니다.' if skipped else
            '일부 SQL은 실행 조건에 따라 달라져 테이블 연결이 맵에 포함되지 않을 수 있습니다.'
            if any(code in labels for _, code in groups) else '정적 분석으로 확정하지 못한 항목이 있습니다.')
    return ('<section class="gx-viewer" id="gx-analysis-scope"><h2>분석 범위 확인</h2>'
            f'<p>{note}</p><details><summary>세부 위치 보기 · {total}건 · {len(groups)}유형</summary>'
            + "".join(sections) + '</details></section>')


def _change_section(domains: list[dict[str, Any]], changes: Any, change_labels: dict[str, str]) -> str:
    """인덱스 맨 위의 '이번 변경' 절. 변경 표시를 요청하지 않은 실행(changes 없음)에는 만들지 않는다."""
    if not isinstance(changes, dict):
        return ""
    heading = '<section aria-labelledby="changes-title"><h2 id="changes-title">이번 변경</h2>'
    if not changes.get("available"):
        reason = changes.get("reason") or "기준 시점을 정할 수 없습니다"
        return f'{heading}<p class="fallback-note">변경 표시를 생략했습니다: {_escape(reason)}</p></section>'
    base = f'{changes.get("base_ref", "")} ({changes.get("base_commit", "")})'
    available = {entry["domain"] for entry in domains if entry["html_exists"]}
    items = [
        f'<li>{_domain_link(entry["domain"], available)} — '
        f'신규 {entry["added"]}개 · 변경 {entry["changed"]}개: '
        f'{_escape(_listed([f"[{change_labels[change]}] {label}" for change, label in entry["change_nodes"]]))}</li>'
        for entry in domains
        if entry["change_nodes"]
    ]
    parts = [heading]
    if items:
        parts.append(f"<p>기준 {_escape(base)} 이후 구조가 바뀐 곳입니다.</p>")
        parts.append(f'<ul class="change-summary">{"".join(items)}</ul>')
    elif changes.get("added") or changes.get("changed"):
        parts.append(f'<p>전체 스캔 기준 신규 {int(changes.get("added", 0))}개 · 변경 {int(changes.get("changed", 0))}개입니다. 갱신하지 않은 도메인의 그림에는 아직 반영되지 않았을 수 있습니다.</p>')
    elif not changes.get("removed") and not changes.get("removed_edges"):
        parts.append(f"<p>기준 {_escape(base)} 이후 구조 변경이 없습니다. 메서드 내부의 로직 변경은 이 비교에 포함하지 않습니다.</p>")
    removed = changes.get("removed") if isinstance(changes.get("removed"), list) else []
    if removed:
        names = _listed([str(item.get("label", "")) for item in removed if isinstance(item, dict)])
        parts.append(f"<p>삭제된 항목 {len(removed)}개 (그림에는 없습니다): {_escape(names)}</p>")
    if changes.get("removed_edges"):
        parts.append(f'<p>삭제된 관계 {len(changes["removed_edges"])}개</p>')
    parts.append("</section>")
    return "".join(parts)


def build_index(
    map_dir: Path | str, project_root: Path | str | None = None, changes: dict[str, Any] | None = None
) -> Path:
    """`map_dir`의 `ir/`·`receipts/`를 읽어 `아키텍처-맵.html` 인덱스를 만들고 그 경로를 반환한다.

    `changes`는 build_map.py가 넘기는 전체 변경 요약(삭제 목록 포함)이다. 생략하면 도메인
    IR의 `meta.changes`에서 기준 정보만 읽는다 - 삭제 목록은 도메인 IR에 없으므로 인덱스만
    따로 다시 만들면 삭제 목록이 빠진다.
    """
    map_dir = Path(map_dir)
    fallback = _fallback_module()
    viewer = fallback._viewer_module()
    domains = _collect_domains(map_dir, fallback.CHANGE_LABELS)
    manifest = _load_json(map_dir / "run-manifest.json") or {}
    if changes is None:
        changes = manifest.get("changes") if manifest else next((entry["changes_meta"] for entry in domains if entry["changes_meta"]), None)

    node_total = len({node["id"] for entry in domains for node in entry["nodes"]})
    edge_total = len({edge_id for entry in domains for edge_id in entry["edge_ids"]})
    diagram_count = sum(1 for entry in domains if entry["capability"] == "diagram")
    table_only_count = sum(1 for entry in domains if entry["capability"] == "table")
    evidence_files: set[str] = set()
    for entry in domains:
        evidence_files |= entry.pop("evidence_files")
        entry.pop("changes_meta")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha = fallback._short_head(project_root)
    revision_text = f" · 커밋 {_escape(sha)}" if sha else ""
    change_text = ""
    if isinstance(changes, dict) and changes.get("available"):
        change_text = f' · 이번 변경 기준 {changes.get("base_ref", "")} ({changes.get("base_commit", "")})'
    summary = (
        f"도메인 {len(domains)}개 · 근거로 인용된 소스 파일 {len(evidence_files)}개 · "
        f"노드 {node_total}개 · 관계 {edge_total}개 · 그림 {diagram_count}개 · 표 {table_only_count}개 · "
        f"생성 시각 {generated_at}{revision_text}{change_text}"
    )

    if domains:
        cards = "".join(_domain_card(entry) for entry in domains)
        body = '<section class="gx-viewer" aria-labelledby="start-title"><h2 id="start-title">어디부터 살펴볼까요?</h2><p>진입점을 찾아 도메인을 열고, 호출·의존 관계와 코드 근거를 따라가세요. 이 맵은 정적 소스 분석 결과이며 실제 실행 순서를 보장하지 않습니다.</p><label for="map-search">도메인·API·클래스 검색</label><input id="map-search" type="search" placeholder="예: /users, UserService" autocomplete="off"><p id="map-search-status" role="status"></p></section>'
        relations = manifest.get("domain_relations", [])
        if relations:
            available = {entry["domain"] for entry in domains if entry["html_exists"]}
            links = ''.join(f'<li>{_domain_link(a, available)} → {_domain_link(b, available)}</li>' for a, b in relations)
            body += f'<section><h2>도메인 간 연결</h2><ul>{links}</ul></section>'
        body += _change_section(domains, changes, fallback.CHANGE_LABELS) + (
            f'<section aria-labelledby="domains-title"><h2 id="domains-title">도메인</h2><ul class="domain-list">{cards}</ul></section>'
        )
        found = []
        for entry in domains:
            if not entry["html_exists"]:
                continue
            for node in entry["nodes"]:
                label = str(node.get("label", ""))
                routes = " · ".join(node.get("routes", []))
                search = " ".join([entry["domain"], label, str(node.get("technical_label", "")), str(node.get("symbol", "")), routes])
                # 이전 버전의 보존 페이지에는 새 상세 앵커가 없으므로 페이지로 안내한다.
                fragment = "#" + quote(viewer.anchor(node["id"]), safe="") if entry.get("detail_anchor_prefix") == viewer.anchor("") else ""
                found.append(f'<li data-node-search="{_escape(search)}"><a href="domains/{quote(entry["domain"], safe="")}.html{fragment}">{_escape(label)}</a> · {_escape(routes or node.get("technical_label", ""))} · {_escape(entry["domain"])}</li>')
        body += '<section id="map-results" hidden><h2>노드 검색 결과</h2><ul>' + ''.join(found) + '</ul></section>'
        body += '''<script>(()=>{const q=document.getElementById('map-search');const cards=[...document.querySelectorAll('[data-domain-search]')],nodes=[...document.querySelectorAll('[data-node-search]')];q.addEventListener('input',()=>{const s=q.value.toLocaleLowerCase().trim();let count=0;nodes.forEach(n=>{n.hidden=!s||!n.dataset.nodeSearch.toLocaleLowerCase().includes(s);if(!n.hidden)count++});cards.forEach(n=>{n.hidden=!!s&&!n.dataset.domainSearch.toLocaleLowerCase().includes(s)&&!nodes.some(x=>!x.hidden&&x.dataset.nodeSearch.startsWith(n.dataset.domainSearch.split(' ')[0]+' '))});document.getElementById('map-results').hidden=!s;document.getElementById('map-search-status').textContent=s?count+'개 노드가 검색되었습니다.':''});})();</script>'''
    else:
        body = _change_section(domains, changes, fallback.CHANGE_LABELS) + '<p class="fallback-note">생성된 도메인 산출물이 없습니다.</p>'
    if manifest.get("reason"):
        body = f'<p role="status">{_escape(manifest["reason"])}</p>' + body
    if manifest.get("validation_status") == "in_progress":
        body = '<p role="status">새 맵을 생성하고 있습니다. 완료 후 이 페이지를 다시 열어 주세요.</p>' + body
    body += _analysis_scope_section(manifest, viewer, project_root)

    template = (TEMPLATE_DIR / "fallback.html").read_text(encoding="utf-8")
    css = (TEMPLATE_DIR / "fallback.css").read_text(encoding="utf-8")
    replacements = {
        "TITLE": "아키텍처 맵",
        "SUMMARY": _escape(summary),
        "CSS": css.rstrip(),
        "MERMAID_SECTION": "",
        "STATIC_CONTENT": body,
    }
    document = fallback.TEMPLATE_TOKEN.sub(lambda match: replacements.get(match.group(1), ""), template)
    overview_ir = {"meta": {"navigation": {"domains": [entry["domain"] for entry in domains if entry["html_exists"]]}}}
    document = document.replace("</head>", viewer.styles() + viewer.theme_bootstrap() + "</head>", 1)
    document = document.replace("<body>", "<body>" + viewer.navigation(overview_ir, overview=True), 1)
    document = document.replace("</body>", viewer.scripts() + "</body>", 1)

    index_path = map_dir / "아키텍처-맵.html"
    map_dir.mkdir(parents=True, exist_ok=True)
    pending = index_path.with_suffix(".html.tmp")
    pending.write_text(document, encoding="utf-8")
    pending.replace(index_path)
    return index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="아키텍처 맵의 인덱스 HTML(아키텍처-맵.html)을 만듭니다.")
    parser.add_argument("map_dir", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    index_path = build_index(args.map_dir, project_root=args.project_root)
    print(json.dumps({"index_path": str(index_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
