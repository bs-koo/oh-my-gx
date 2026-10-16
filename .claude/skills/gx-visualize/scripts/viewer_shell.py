"""백엔드와 무관하게 읽고 이동할 수 있는 GX 탐색 화면."""
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
KINDS = {"screen": "화면", "api": "API", "service": "서비스", "repository": "저장소", "table": "테이블"}
RELATIONS = {"calls": "호출", "depends_on": "타입 의존", "requests": "요청", "reads": "조회", "writes": "저장"}


def esc(value):
    return html.escape(str(value), quote=True)


def anchor(node_id):
    # Archify SVG의 node-{id}와 다른 이름 공간을 쓴다. URL 인코딩은 href에서만 한다.
    return "gx-detail-" + str(node_id)


def node_href(node):
    domain = node.get("external_domain")
    page = quote(str(domain), safe="") + ".html" if domain and node.get("external_available") is not False else ""
    if page and node.get("external_detail_available") is False:
        return page
    return page + "#" + quote(anchor(node["id"]), safe="")


def node_link(node):
    unavailable = ' <span>현재 결과 없음 · 이 페이지의 참조 정보</span>' if node.get("external_domain") and node.get("external_available") is False else ""
    return f'<a href="{esc(node_href(node))}">{esc(node.get("label", node["id"]))}</a>{unavailable}'


def evidence_html(evidence, project_root=None):
    items = []
    for item in evidence:
        if item.get("kind") == "inferred":
            items.append("<li>추정 근거 · 코드 위치가 확인되지 않았습니다.</li>")
            continue
        file = str(item.get("file", ""))
        line = item.get("line")
        text = file + (f":{line}" if line else "")
        label = f"<code>{esc(text)}</code>"
        if project_root and file:
            root = Path(project_root).resolve()
            source = (root / file).resolve()
            try:
                source.relative_to(root)
            except ValueError:
                pass
            else:
                # 실행 가능한 임의 URL 대신 프로젝트 내부 파일의 편집기 링크만 만든다.
                href = "vscode://file/" + quote(source.as_posix(), safe="/:") + (f":{int(line)}" if line else "")
                label = f'<a href="{esc(href)}" title="편집기에서 근거 열기">{label}</a>'
        locator = item.get("locator", {})
        if locator.get("type") == "xlsx":
            label += f' · {esc(locator.get("sheet", ""))}!{esc(locator.get("cell", ""))}'
        elif locator.get("page"):
            label += f' · {esc(locator["page"])}페이지'
        items.append(f"<li>{label}</li>")
    return '<ul class="gx-evidence">' + "".join(items) + "</ul>" if items else "<p>등록된 근거가 없습니다.</p>"


def navigation(ir, overview=False):
    nav = ir.get("meta", {}).get("navigation", {})
    links = []
    if nav and not overview:
        links.append('<a href="../%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98-%EB%A7%B5.html">전체 구조</a>')
    for domain in nav.get("domains", []):
        name = domain.get("name", domain.get("domain", "")) if isinstance(domain, dict) else str(domain)
        href = ("domains/" if overview else "") + quote(name, safe="") + ".html"
        current = ' aria-current="page"' if name == nav.get("domain") else ""
        if isinstance(domain, dict) and domain.get("available") is False:
            links.append(f'<span aria-disabled="true"{current}>{esc(name)} · 현재 결과 없음</span>')
        else:
            links.append(f'<a href="{esc(href)}"{current}>{esc(name)}</a>')
    if not overview:
        if has_features(ir):
            links.append('<a href="#gx-features">기능별 코드 탐색</a>')
        links.append('<a href="#gx-explorer">구성 요소·근거 찾기</a>')
        if diagnostics(ir):
            links.append('<a href="#gx-diagnostics">확인할 항목</a>')
    return ('<div class="gx-viewer gx-navigation"><nav aria-label="아키텍처 탐색">' + "".join(links)
            + '</nav><button type="button" data-gx-theme>테마 전환</button></div>')


def reading_guide(ir):
    kinds = sorted({node.get("kind", "") for node in ir.get("nodes", [])})
    legend = "".join(f'<li class="gx-kind gx-kind-{esc(kind)}">{esc(KINDS.get(kind, kind))}</li>' for kind in kinds)
    return ('<section class="gx-guide" aria-label="읽는 법"><h2>읽는 법</h2>'
            '<p>진입점에서 시작해 연결된 구성 요소와 코드 근거를 확인하세요. 호출은 메서드 본문에서 확인한 정적 호출이며, 타입 의존은 호출 여부가 확인되지 않은 선언 관계입니다. 실제 실행 순서를 보장하지 않습니다.</p>'
            '<p>화면 → API → 서비스 → 저장소 → 테이블 · 신규와 변경은 배지와 굵은 선으로 표시합니다.</p>'
            f'<ul class="gx-legend">{legend}</ul></section>')


def diagnostics(ir, project_root=None):
    meta = ir.get("meta", {})
    entries = []
    reasons = {"unresolved-target": "연결 대상 미확인", "unsupported-mapping": "매핑 분석 범위 밖", "dynamic-sql": "동적 SQL 확인 필요", "unreadable": "파일 읽기 실패", "ambiguous-target": "연결 대상 후보가 여러 개"}
    for key, title in (("missing_inputs", "필요한 입력"), ("skipped", "분석에서 제외"), ("unresolved_edges", "연결 대상 미확인"), ("diagnostics", "분석 진단")):
        values = ir.get(key, meta.get(key, []))
        for value in values if isinstance(values, list) else []:
            if isinstance(value, dict):
                reason = value.get("reason", value.get("code", title))
                description = reasons.get(reason, str(reason))
                detail = " · ".join(str(value[k]) for k in ("message", "source", "target", "target_symbol", "file", "line") if value.get(k) is not None)
                evidence = value.get("evidence", [])
                location = evidence_html(evidence, project_root) if isinstance(evidence, list) and evidence else ""
                entries.append(f"<li><strong>{esc(title)}: {esc(description)}</strong> {esc(detail)}{location}</li>")
            else:
                entries.append(f"<li><strong>{esc(title)}</strong>: {esc(value)}</li>")
    if not entries:
        return ""
    return ('<section id="gx-diagnostics"><h2>확인이 필요한 항목</h2>'
            '<p>아래 파일과 대상을 확인한 뒤 매핑·주입 선언 또는 입력을 보완하고 다시 생성하세요. 분석 범위 밖 코드는 연결이 없다는 뜻이 아닙니다.</p><ul>'
            + "".join(dict.fromkeys(entries)) + "</ul></section>")


def explorer(ir, project_root=None):
    nodes = sorted(ir.get("nodes", []), key=(lambda n: (n.get("kind") != "api", n.get("label", ""), n["id"]))
                   if ir.get("view") == "service" else (lambda n: n["id"]))
    lookup = {node["id"]: node for node in nodes}
    outgoing, incoming = {}, {}
    for edge in ir.get("edges", []):
        outgoing.setdefault(edge["source"], []).append(edge)
        incoming.setdefault(edge["target"], []).append(edge)
    cards = []
    for node in nodes:
        badges = f'<span class="gx-kind gx-kind-{esc(node.get("kind", ""))}">{esc(KINDS.get(node.get("kind"), node.get("kind", "")))}</span>'
        if node.get("change") in {"added", "changed"}:
            badges += f'<span class="change change-{esc(node["change"])}">{"신규" if node["change"] == "added" else "변경"}</span>'
        status = node.get("status", "unknown")
        if status != "unknown" or ir.get("view") != "service":
            labels = {"planned": "계획됨", "in_progress": "진행 중", "review": "검토 중", "verified": "검증됨", "blocked": "차단됨", "unknown": "확인 필요"}
            badges += f'<span class="status status-{esc(status)}">{labels.get(status, "확인 필요")}</span>'
        identifiers = list(dict.fromkeys(str(node[k]) for k in ("symbol", "technical_label") if node.get(k) and node[k] != node.get("label")))
        identifiers = list(dict.fromkeys(identifiers + [str(route) for route in node.get("routes", [])]))
        technical = "".join(f'<p class="technical-label"><code>{esc(value)}</code></p>' for value in identifiers)
        connections = []
        for title, edges, endpoint in (("들어오는 관계", incoming.get(node["id"], []), "source"), ("나가는 관계", outgoing.get(node["id"], []), "target")):
            if edges:
                links = "".join(f'<li>{esc(RELATIONS.get(edge["relation"], edge["relation"]))} · {node_link(lookup[edge[endpoint]])}{evidence_details(edge.get("evidence", []), project_root, "관계 근거") if edge.get("evidence") else ""}</li>' for edge in edges if edge[endpoint] in lookup)
                connections.append(f'<h4>{title}</h4><ul>{links}</ul>')
        external = f'<p>다른 도메인: {node_link(node)}</p>' if node.get("external_domain") else ""
        cards.append(f'<li data-gx-search><article class="node-card" id="{esc(anchor(node["id"]))}" tabindex="-1">'
                     f'<h3>{esc(node.get("label", node["id"]))}</h3>{badges}{technical}{external}'
                     + "".join(connections) + evidence_details(node.get("evidence", []), project_root, "코드·산출물 근거")
                     + f'<details><summary>내부 ID</summary><code>{esc(node["id"])}</code></details></article></li>')
    return ('<section aria-labelledby="nodes-title" id="gx-explorer"><h2 id="nodes-title">구성 요소 탐색</h2>'
            '<label for="gx-node-search">이름·API 경로·심볼 검색</label><input id="gx-node-search" type="search" placeholder="예: 사용자, GET /users, UserService" autocomplete="off">'
            f'<p data-gx-result role="status">{len(nodes)}개 구성 요소</p><ul class="node-list">' + "".join(cards)
            + '</ul><p data-gx-empty hidden>일치하는 구성 요소가 없습니다. 검색어를 줄여 보세요.</p></section>')


def has_features(ir):
    return ir.get("view") == "service" and any(
        node.get("kind") in {"api", "screen"} and not node.get("external_domain")
        for node in ir.get("nodes", []))


def feature_explorer(ir, project_root=None):
    if not has_features(ir):
        return ""
    fields = ("id", "kind", "label", "symbol", "technical_label", "routes", "external_domain", "external_available")
    nodes = [{key: node[key] for key in fields if key in node} for node in ir["nodes"]]
    features = sorted((node for node in nodes if node["kind"] in {"api", "screen"} and not node.get("external_domain")),
                      key=lambda node: (node.get("technical_label", ""), node.get("label", ""), node["id"]))
    buttons = []
    for node in features:
        label = node.get("label", node["id"])
        symbol = node.get("symbol", "")
        title = label.rsplit(".", 1)[-1] if "." in label and (not symbol or label == symbol) else label
        routes = ([node["technical_label"]] if node.get("technical_label") else []) + node.get("routes", [])
        route = " · ".join(dict.fromkeys(routes))
        buttons.append(f'<li><button type="button" data-gx-feature="{esc(node["id"])}" aria-pressed="false">'
                       f'<span class="gx-feature-name">{esc(title)}</span><span class="gx-feature-route">{esc(route or label)}</span></button></li>')
    edges = [{key: edge[key] for key in ("id", "source", "target", "relation")} |
             {"evidence_html": evidence_html(edge.get("evidence", []), project_root)} for edge in ir.get("edges", [])]
    data = json.dumps({"nodes": nodes, "edges": edges, "features": [node["id"] for node in features]}, ensure_ascii=False)
    # script 종료 태그가 포함된 라벨도 실행되지 않는 데이터로 보존한다.
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    domain = ir.get("meta", {}).get("navigation", {}).get("domain")
    title = f"{domain} · 기능별 코드 탐색" if domain else "기능별 코드 탐색"
    return ('<section class="gx-viewer gx-feature" id="gx-features" aria-labelledby="gx-features-title">'
            f'<header class="gx-feature-heading"><div><h2 id="gx-features-title">{esc(title)}</h2>'
            '<p>API를 선택하면 연결된 코드만 모아 볼 수 있습니다.</p></div>'
            '<a href="#gx-full-map">전체 관계도 보기</a></header>'
            '<div class="gx-feature-layout"><aside class="gx-feature-picker" aria-label="기능 선택">'
            '<label for="gx-feature-search">API·메서드 검색</label><input id="gx-feature-search" type="search" placeholder="예: uploadExcel, /intake/excel" autocomplete="off">'
            f'<p data-gx-feature-search-count role="status">{len(features)}개 API·화면</p>'
            '<ul class="gx-feature-list">' + "".join(buttons) + '</ul>'
            '<p data-gx-feature-empty hidden>일치하는 API가 없습니다. 검색어를 줄여 보세요.</p></aside>'
            '<div class="gx-feature-workspace"><div class="gx-feature-selection"><h3 data-gx-feature-title>API를 선택하세요.</h3>'
            '<p data-gx-feature-route></p><p data-gx-feature-count role="status" aria-live="polite"></p></div>'
            '<label class="gx-feature-dependency"><input type="checkbox" id="gx-feature-dependencies"><span data-gx-feature-dependency-label>타입 의존성 후보도 포함</span></label>'
            '<p class="gx-feature-caveat">서비스·저장소 이후는 클래스 단위 연결입니다. 선택한 메서드의 실제 실행 경로나 소요 시간을 뜻하지 않습니다.</p>'
            '<div class="gx-feature-flow" aria-label="선택한 API의 계층별 관련 코드"></div>'
            '<details class="gx-feature-connections"><summary>추출된 연결과 코드 근거</summary><div data-gx-feature-connections></div></details>'
            '<div class="gx-feature-inspector"><h3>선택한 코드의 근거</h3><div data-gx-feature-detail><p>구성 요소를 선택하면 파일과 연결 근거가 여기에 표시됩니다.</p></div></div>'
            '</div></div><noscript><p>기능 선택에는 JavaScript가 필요합니다. 아래 전체 관계도와 구성 요소 목록을 이용하세요.</p></noscript>'
            f'<script type="application/json" id="gx-feature-data">{data}</script></section>')


def full_map(content):
    return ('<details class="gx-full-map" id="gx-full-map" open data-gx-collapse-on-ready>'
            '<summary>전체 도메인 관계도 보기</summary><div class="gx-full-map-content">' + content + '</div></details>')


def full_evidence(content):
    return ('<details class="gx-full-evidence"><summary>전체 구성 요소·관계·분석 근거 보기</summary>' + content + '</details>')


def evidence_details(evidence, project_root, title):
    return f'<details><summary>{esc(title)} · {len(evidence)}건</summary>{evidence_html(evidence, project_root)}</details>'


def styles():
    return '<style>' + (TEMPLATES / "viewer.css").read_text(encoding="utf-8") + '</style>'


def scripts():
    graph = (TEMPLATES / "feature-graph.js").read_text(encoding="utf-8")
    return '<script data-gx-viewer>' + graph + '\n' + (TEMPLATES / "viewer.js").read_text(encoding="utf-8") + '</script>'


def theme_bootstrap():
    # Archify 자체 bootstrap보다 먼저 실행하여 시스템 dark 기본값 대신 저장값/밝음을 적용한다.
    return "<script>try{if(!['light','dark'].includes(localStorage.getItem('archify-theme')))localStorage.setItem('archify-theme','light');document.documentElement.dataset.theme=localStorage.getItem('archify-theme')||'light'}catch(_){document.documentElement.dataset.theme='light'}</script>"


def supplement(ir, project_root=None):
    content = '<div class="gx-viewer gx-supplement">' + reading_guide(ir) + diagnostics(ir, project_root) + explorer(ir, project_root) + '</div>'
    return full_evidence(content) if has_features(ir) else content
