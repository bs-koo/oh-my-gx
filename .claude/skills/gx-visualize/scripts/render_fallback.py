#!/usr/bin/env python3
"""Render validated GX visualization IR as Korean self-contained HTML."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import shutil
import subprocess
from datetime import datetime
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
        # 노드 ID는 넣지 않는다 - 노드 목록 카드에 이미 있고, 여기 넣으면 라벨이 긴
        # 기술 ID로 시작해 실제 이름을 가린다(버그 B, 2026-09-21 컨트롤러가 reb.html에서
        # 발견: "gx-api-webframework-public-src-main-java-..."가 라벨 맨 앞에 왔다).
        label_parts = [node["label"]]
        if "technical_label" in node:
            label_parts.append(node["technical_label"])
        label_parts.append(STATUS_LABELS.get(node["status"], STATUS_LABELS["unknown"]))
        label = "#10;".join(_mermaid_text(part) for part in label_parts)
        lines.append(f'  {aliases[node["id"]]}["{label}"]')
    for edge in edges:
        relation = _mermaid_text(edge["relation"])
        lines.append(f'  {aliases[edge["source"]]} -->|{relation}| {aliases[edge["target"]]}')
    return "\n".join(lines)


# Mermaid의 flowchart 문법을 깨뜨릴 수 있는 문자만 인코딩한다: `"`(따옴표 라벨을 조기
# 종료), `#`·`;`(Mermaid 자신의 십진 엔티티 문법), `|`(파이프로 구분되는 엣지 라벨의
# 끝), 줄바꿈(각 statement가 한 줄이어야 한다). 그 외 ASCII·한글은 원문 그대로 남긴다
# - 예전에는 모든 문자를 `#{ord};`로 인코딩해 "g" 하나까지 "#103;"가 되었고, 화면에는
# "#103;#120;..." 같은 읽을 수 없는 문자열이 떴다(버그 A, 2026-09-21 컨트롤러가
# reb.html에서 발견).
_MERMAID_UNSAFE_CHARS = frozenset('"#;|\n\r')


def _mermaid_text(value: Any) -> str:
    """Encode only the characters Mermaid's flowchart grammar cannot take literally."""
    return "".join(
        f"#{ord(character)};" if character in _MERMAID_UNSAFE_CHARS else character
        for character in str(value)
    )


_NO_DIAGRAM_NOTE = (
    '다이어그램은 생성되지 않았습니다. 아래는 같은 IR의 노드 목록과 관계 표입니다.'
    ' 그림을 보려면 Archify가 필요합니다: npx -y skills add tt-a1i/archify -g'
)


def _mermaid_section(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]], mermaid_asset_href: str | None = None
) -> str:
    source = _escape(_mermaid_source(nodes, edges))
    if mermaid_asset_href is None:
        # assets/mermaid.min.js를 확보하지 못했거나 시도하지 않은 호출 - 지금까지처럼
        # 소스만 보여주고 그림이 없다는 사실을 알린다. 없는데 있는 척하지 않는다.
        return (
            '<section aria-labelledby="mermaid-title"><h2 id="mermaid-title">Mermaid 다이어그램 소스</h2>'
            f'<p class="fallback-note">{_NO_DIAGRAM_NOTE}</p>'
            f'<pre class="mermaid-source"><code>{source}</code></pre></section>'
        )
    # 브라우저에서 실제로 그림을 렌더한다(사용자 요청 2, 2026-09-21) - 소스는 사라지지
    # 않고 <details>로 접어 확인용으로 남긴다.
    return (
        '<section aria-labelledby="mermaid-title"><h2 id="mermaid-title">아키텍처 다이어그램</h2>'
        f'<pre class="mermaid">{source}</pre>'
        f'<script src="{_escape(mermaid_asset_href)}"></script>'
        '<script>mermaid.initialize({startOnLoad: true});</script>'
        '<details><summary>Mermaid 소스 보기</summary>'
        f'<pre class="mermaid-source"><code>{source}</code></pre></details>'
        '</section>'
    )


def _no_diagram_section() -> str:
    # static 백엔드는 Mermaid 소스조차 없다 - 그림 부재 문구가 _mermaid_section() 안에만
    # 있으면 --backend static HTML에는 0건이 된다(설계서 §5.5.2는 두 폴백 모두에서 그림
    # 부재 명시를 요구한다, 2026-09-18 최종 리뷰 M4).
    return f'<p class="fallback-note">{_NO_DIAGRAM_NOTE}</p>'


def _render_document(ir: dict[str, Any], backend: str, mermaid_asset_href: str | None = None) -> str:
    nodes = _sorted_nodes(ir)
    edges = _sorted_edges(ir)
    template = (TEMPLATE_DIR / "fallback.html").read_text(encoding="utf-8")
    css = (TEMPLATE_DIR / "fallback.css").read_text(encoding="utf-8")
    static_content = "\n".join((_legend(), _node_list(nodes), _relationship_table(edges), _evidence_cards(nodes)))
    mermaid_section = _mermaid_section(nodes, edges, mermaid_asset_href) if backend == "mermaid" else _no_diagram_section()
    summary = f'노드 {len(nodes)}개와 관계 {len(edges)}개 · {"Mermaid + 정적 폴백" if backend == "mermaid" else "정적 HTML"}'
    replacements = {
        "TITLE": _escape(ir["title"]),
        "SUMMARY": _escape(summary),
        "CSS": css.rstrip(),
        "MERMAID_SECTION": mermaid_section,
        "STATIC_CONTENT": static_content,
    }
    return TEMPLATE_TOKEN.sub(lambda match: replacements[match.group(1)], template)


_BODY_TAG_RE = re.compile(r"<body[^>]*>", re.IGNORECASE)


def _short_head(project_root: Path | str | None) -> str | None:
    if project_root is None:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(project_root), capture_output=True, text=True, shell=False, check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def snapshot_banner_html(project_root: Path | str | None) -> str:
    """Build the `--scope session` snapshot banner - SKILL.md의 세 가지 요구사항을 그대로 담는다:
    생성 시각, `git rev-parse --short HEAD`, "갱신되지 않는다" 고지(2026-09-18 최종 리뷰 I7).
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha = _short_head(project_root)
    revision_text = f" · 커밋 {_escape(sha)}" if sha else ""
    return (
        '<p class="snapshot-banner" role="note">'
        f'생성 시각: {_escape(generated_at)}{revision_text}'
        " · 이 그림은 해당 시점의 스냅샷이며 갱신되지 않습니다.</p>"
    )


def inject_snapshot_banner(document: str, banner_html: str) -> str:
    """Insert `banner_html` right after the opening `<body>` tag of `document`.

    Both render_fallback.render()과 render_archify.render_archify()가 이 함수를 공유해
    폴백 산출물과 Archify 산출물 양쪽에 같은 방식으로 배너를 붙인다 - 렌더러마다 다른
    HTML 구조에 각자 배너 절차를 만들지 않는다.
    """
    match = _BODY_TAG_RE.search(document)
    if match is None:
        return document
    return document[: match.end()] + banner_html + document[match.end() :]


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
    snapshot_banner: bool = False,
    html_dir: Path | str | None = None,
    mermaid_asset_href: str | None = None,
) -> dict[str, str]:
    """Validate and render an IR document, returning stable artifact paths.

    `output_name`, when given, replaces the view-derived filename stem (`{view}.html`,
    `{view}.receipt.json`) with `{output_name}.*` — see render_archify.render_archify()
    for why (shared `output_dir`, several documents of the same `view`). Omit it to keep
    the existing `{view}.*` behavior.

    `snapshot_banner`, when true, inserts the `--scope session` snapshot banner (생성
    시각·커밋 해시·갱신되지 않는다는 고지) into the rendered HTML. `--scope all` 호출은
    이 인자를 생략(기본 False)한다 - 누적 맵에는 배너를 넣지 않는다.

    `html_dir`, when given, writes `{stem}.html` there instead of `output_dir` while
    `.receipt.json` stays in `output_dir` — `--scope all`은 이걸로 `${MAP_DIR}/domains/`와
    `${MAP_DIR}/receipts/`를 분리한다(2026-09-21 사용자 리뷰: 32개 파일이 평평하게 쌓여
    "뭐가 뭔지 모르겠다"는 지적). 생략하면 `output_dir`과 같아 기존 평평한 구조 그대로다.

    `mermaid_asset_href`, when given, renders an actual `<pre class="mermaid">` diagram
    that loads Mermaid from this href (`--scope all`이 도메인들과 공유하는
    `${MAP_DIR}/assets/mermaid.min.js`) instead of showing only the Mermaid source text.
    생략하면(기본값) 지금까지처럼 소스만 보여준다 - 자산을 못 구했을 때도 이 경로를
    그대로 쓴다.
    """
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of: {', '.join(sorted(BACKENDS))}")

    ir_path = Path(ir_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_dir = Path(html_dir) if html_dir is not None else output_dir
    html_dir.mkdir(parents=True, exist_ok=True)
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
        (html_dir / f"{stem}.html").unlink(missing_ok=True)
        raise ValueError("IR 검증 실패: " + "; ".join(receipt["errors"]))

    document = _render_document(ir, backend, mermaid_asset_href=mermaid_asset_href)
    if snapshot_banner:
        document = inject_snapshot_banner(document, snapshot_banner_html(project_root))
    html_path = html_dir / f"{stem}.html"
    html_path.write_text(document, encoding="utf-8")
    return {"html_path": str(html_path), "backend": backend, "receipt_path": str(receipt_path)}


_MERMAID_ASSET_NAME = "mermaid.min.js"
_MERMAID_ASSET_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
# 실측 3.4MB(2026-09-21)에 한참 못 미치면 다운로드가 잘렸거나 오류 페이지를 받은
# 것으로 본다 - 손상된 파일을 "확보 성공"으로 착각하지 않는다.
_MERMAID_ASSET_MIN_BYTES = 500_000


def ensure_mermaid_asset(assets_dir: Path | str) -> dict[str, Any]:
    """폴백 도메인들이 공유하는 `mermaid.min.js`를 `assets_dir`에 1회 확보한다.

    Archify 자동 설치(detect_backend.ensure_archify)와 같은 결: 이미 받아 둔 자산이
    있으면 재다운로드하지 않고(여러 도메인이 같은 assets_dir를 공유), 없으면 curl로
    1회 내려받는다. 실패해도 예외를 던지지 않고 attempts에 시도를 기록만 한다 -
    호출자는 `available`이 False면 `mermaid_asset_href` 없이 렌더해 지금까지처럼
    소스만 보여주는 경로로 폴백한다(없는데 있는 척하지 않는다).
    """
    assets_dir = Path(assets_dir)
    target = assets_dir / _MERMAID_ASSET_NAME
    attempts: list[dict[str, Any]] = []

    if target.is_file() and target.stat().st_size >= _MERMAID_ASSET_MIN_BYTES:
        return {"available": True, "path": str(target), "attempts": attempts}

    assets_dir.mkdir(parents=True, exist_ok=True)
    curl = shutil.which("curl")
    if curl is None:
        attempts.append(
            {"phase": "download", "command": None, "exit_code": None, "stderr": "curl executable not found on PATH"}
        )
        return {"available": False, "path": None, "attempts": attempts}

    tmp_path = assets_dir / f".{_MERMAID_ASSET_NAME}.download"
    argv = [curl, "-fsSL", "--max-time", "60", "-o", str(tmp_path), _MERMAID_ASSET_URL]
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        tmp_path.unlink(missing_ok=True)
        attempts.append({"phase": "download", "command": argv, "exit_code": None, "stderr": str(exc)})
        return {"available": False, "path": None, "attempts": attempts}

    attempts.append(
        {"phase": "download", "command": argv, "exit_code": result.returncode, "stderr": (result.stderr or "").strip()}
    )
    if result.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size < _MERMAID_ASSET_MIN_BYTES:
        tmp_path.unlink(missing_ok=True)
        return {"available": False, "path": None, "attempts": attempts}

    tmp_path.replace(target)
    return {"available": True, "path": str(target), "attempts": attempts}


def main() -> int:
    parser = argparse.ArgumentParser(description="GX 시각화 IR을 self-contained HTML로 렌더링합니다.")
    parser.add_argument("ir_path", type=Path, nargs="?")
    parser.add_argument("output_dir", type=Path, nargs="?")
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="mermaid")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output-name")
    parser.add_argument("--snapshot-banner", action="store_true")
    parser.add_argument("--html-dir", type=Path)
    parser.add_argument("--mermaid-asset-href")
    parser.add_argument("--ensure-mermaid-asset", type=Path, metavar="ASSETS_DIR")
    args = parser.parse_args()

    if args.ensure_mermaid_asset is not None:
        print(json.dumps(ensure_mermaid_asset(args.ensure_mermaid_asset), ensure_ascii=False, sort_keys=True))
        return 0
    if args.ir_path is None or args.output_dir is None:
        parser.error("ir_path와 output_dir는 --ensure-mermaid-asset이 없으면 필수입니다.")

    try:
        result = render(
            args.ir_path, args.output_dir, args.backend,
            project_root=args.project_root, output_name=args.output_name,
            snapshot_banner=args.snapshot_banner, html_dir=args.html_dir,
            mermaid_asset_href=args.mermaid_asset_href,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
