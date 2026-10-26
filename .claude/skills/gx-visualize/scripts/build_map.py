#!/usr/bin/env python3
"""Build the architecture map in one command.

스캔 → 변경 표시 → (선택) 한국어 라벨 → 도메인 분할 → 도메인별 검증·렌더 → Mermaid
자산 → 인덱스를 한 번에 수행하고 JSON 보고를 낸다(설계서 §5.8.3·§5.8.4). 2026-09-28
콜드런에서 문서만 보고 실행한 모델이 이 단계들을 손으로 잇느라 13~24분이 걸렸고, 도메인
분할에는 실행 명령이 없어 매번 연결 코드를 새로 짰다. 결정적인 단계는 여기 모으고,
모델은 이 명령 하나를 실행해 보고를 전달한다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import shutil
import html
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
DEFAULT_MAP_DIR = Path(".dev") / "architecture"
MERMAID_ASSET_HREF = "../assets/mermaid.min.js"
ENTRYPOINT_SCAN_GROUP = "entrypoint-scan"
IR_SUFFIX = ".ir.json"


def _load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"gx_visualize_{name}_for_build_map", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scanner = _load("scan_entrypoints")
changes_module = _load("changes")
splitter = _load("split_domains")
validator = _load("validate_ir")
archify_renderer = _load("render_archify")
fallback_renderer = _load("render_fallback")
index_builder = _load("build_index")
backend_detector = _load("detect_backend")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + ".tmp")
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def apply_labels(ir: dict[str, Any], labels: dict[str, str]) -> int:
    """스캔 라벨과 **정확히 일치하는** 항목만 한국어 라벨로 바꾸고 바꾼 노드 수를 반환한다.

    부분 일치·추측은 하지 않는다(SKILL.md "도메인 용어를 지어내지 않는다"). 원래 기술
    식별자는 technical_label이 비어 있을 때만 그리로 옮긴다 - API 노드의 technical_label
    (HTTP 경로)은 덮어쓰지 않는다.
    """
    applied = 0
    for node in ir["nodes"]:
        korean = labels.get(node["label"])
        if not isinstance(korean, str) or not korean.strip():
            continue
        node.setdefault("symbol", node["label"])
        node.setdefault("technical_label", node["label"])
        node["label"] = korean.strip()
        applied += 1
    return applied


def _clear_stale(map_dir: Path, keep: set[str]) -> None:
    """이번 스캔에 없는 도메인의 이전 산출물을 지운다.

    매 실행 전체를 다시 스캔하므로 사라진 도메인의 그림이 인덱스에 남으면 없는 구조를
    있는 것처럼 보여 준다. `--domain`으로 한 도메인만 그릴 때는 부르지 않는다.
    """
    for ir_path in sorted((map_dir / "ir").glob(f"*{IR_SUFFIX}")):
        name = ir_path.name[: -len(IR_SUFFIX)]
        if name in keep:
            continue
        ir_path.unlink(missing_ok=True)
        (map_dir / "domains" / f"{name}.html").unlink(missing_ok=True)
        for suffix in (".receipt.json", ".archify.json"):
            (map_dir / "receipts" / f"{name}{suffix}").unlink(missing_ok=True)


def _domain_status(receipt: dict[str, Any]) -> str:
    """렌더 영수증을 보고 계약의 verified·fallback·failed로 정규화한다(references/gx-mapping.md)."""
    if receipt.get("status") == "failed" or not receipt.get("artifact_path"):
        return "failed"
    if receipt.get("backend") == "archify" and receipt.get("status") == "valid":
        return "verified"
    return "fallback"


def _overall_status(domains: list[dict[str, Any]]) -> str:
    statuses = {entry["validation_status"] for entry in domains}
    if not domains or "failed" in statuses:
        return "failed"
    return "fallback" if "fallback" in statuses else "verified"


def _render_domain(
    name: str,
    part: dict[str, Any],
    map_dir: Path,
    project_root: Path,
    archify_command: Any,
    archify_discovery: dict[str, Any] | None = None,
    preserve_previous: bool = True,
) -> dict[str, Any]:
    ir_path = map_dir / "ir" / f"{name}{IR_SUFFIX}"
    receipts_dir = map_dir / "receipts"
    entry: dict[str, Any] = {
        "domain": name,
        "backend": None,
        "validation_status": "failed",
        "html_path": None,
        "ir_path": None,
        "receipt_path": None,
        "missing_inputs": sorted(set(part.get("missing_inputs", []))),
        "added": sum(1 for node in part["nodes"] if node.get("change") == "added" and not node.get("external_domain")),
        "changed": sum(1 for node in part["nodes"] if node.get("change") == "changed" and not node.get("external_domain")),
    }
    previous_receipt = receipts_dir / f"{name}.receipt.json"
    previous_html = map_dir / "domains" / f"{name}.html"
    try:
        previous = json.loads(previous_receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    if not preserve_previous:
        previous = {}
    if previous.get("last_good"):
        entry["last_good"] = previous["last_good"]
    if previous.get("status") != "failed" and previous.get("artifact_path") and previous_html.is_file():
        saved = previous_html.with_name(f"{name}.last-good.html")
        shutil.copyfile(previous_html, saved)
        entry["last_good"] = {"html_path": str(saved), "generated_at": previous.get("generated_at"),
                              "revision": previous.get("revision")}

    def failed(errors: list[Any]) -> dict[str, Any]:
        entry["errors"] = errors
        entry["capability"] = "failed"
        receipt_path = receipts_dir / f"{name}.receipt.json"
        _write_json(receipt_path, {"status": "failed", "backend": None, "artifact_path": None,
                                 "errors": errors, "last_good": entry.get("last_good")})
        entry["receipt_path"] = str(receipt_path)
        diagnostic_path = map_dir / "domains" / f"{name}.html"
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        reasons = ''.join(f'<li>{html.escape(str(error))}</li>' for error in errors)
        document = ('<!doctype html><html lang="ko"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    f'<title>{html.escape(name)} 생성 실패</title><body><main>'
                    '<a href="../아키텍처-맵.html">전체 구조</a>'
                    f'<h1>{html.escape(name)} 생성 실패</h1><p>이번 실행의 구조를 확인하지 못했습니다. 오류를 해결한 뒤 다시 생성해 주세요.</p>'
                    f'<ul>{reasons}</ul></main></body></html>')
        pending_html = diagnostic_path.with_suffix(".html.tmp")
        pending_html.write_text(document, encoding="utf-8")
        pending_html.replace(diagnostic_path)
        return entry
    # 검증을 통과하기 전에는 이전 {domain}.ir.json을 덮어쓰지 않는다(설계서 §6).
    pending = map_dir / "ir" / f".{name}{IR_SUFFIX}.pending"
    _write_json(pending, part)
    receipt = validator.validate(pending, project_root=project_root)
    if receipt["status"] != "valid":
        pending.unlink(missing_ok=True)
        return failed(receipt["errors"])
    pending.replace(ir_path)
    entry["ir_path"] = str(ir_path)
    try:
        result = archify_renderer.render_archify(
            ir_path, receipts_dir, archify_command,
            project_root=project_root, output_name=name, html_dir=map_dir / "domains",
            archify_discovery=archify_discovery,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        return failed([str(exc)])
    try:
        rendered = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError) as exc:
        return failed([f"렌더 결과를 확인하지 못했습니다: {exc}"])
    if _domain_status(rendered) == "failed":
        return failed(rendered.get("errors", ["렌더러가 현재 HTML을 생성하지 못했습니다."]))
    entry.update(
        backend=result["backend"],
        validation_status=_domain_status(rendered),
        html_path=result["html_path"],
        receipt_path=result["receipt_path"],
        missing_inputs=rendered.get("missing_inputs", entry["missing_inputs"]),
        capability=rendered.get("capability", "diagram" if result["backend"] == "archify" else "table"),
    )
    rendered["generated_at"] = datetime.now(timezone.utc).isoformat()
    rendered["revision"] = fallback_renderer._short_head(project_root)
    entry.update(generated_at=rendered["generated_at"], revision=rendered["revision"], freshness="current",
                 detail_anchor_prefix=fallback_renderer._viewer_module().anchor(""))
    rendered["detail_anchor_prefix"] = entry["detail_anchor_prefix"]
    _write_json(Path(result["receipt_path"]), rendered)
    return entry


def _rerender_with_mermaid_asset(entry: dict[str, Any], map_dir: Path, project_root: Path) -> None:
    """Mermaid로 폴백한 도메인을 공유 자산으로 다시 그려 브라우저에서 실제 그림이 보이게 한다.

    render_fallback.render()는 영수증을 검증기 결과로 새로 쓴다. 그대로 두면 Archify 실패
    기록(attempts)과 폴백 판정이 사라지고 인덱스가 이 도메인을 "통과"로 표시한다(2026-09-28
    콜드런에서 관찰). 다시 그리기 전의 영수증을 되돌려 놓는다.
    """
    receipt_path = Path(entry["receipt_path"])
    preserved = json.loads(receipt_path.read_text(encoding="utf-8"))
    try:
        result = fallback_renderer.render(
            entry["ir_path"], map_dir / "receipts", "mermaid",
            project_root=project_root, output_name=entry["domain"],
            html_dir=map_dir / "domains", mermaid_asset_href=MERMAID_ASSET_HREF,
        )
        if result.get("html_path") and Path(result["html_path"]).is_file():
            preserved["capability"] = "diagram"
            entry["capability"] = "diagram"
    except (OSError, ValueError, RuntimeError) as exc:
        entry.setdefault("errors", []).append(f"Mermaid 자산으로 다시 그리지 못했습니다: {exc}")
    finally:
        _write_json(receipt_path, preserved)


def build_map(
    project_root: Path | str,
    map_dir: Path | str | None = None,
    changed_since: str | None = None,
    domain: str | None = None,
    labels: dict[str, str] | None = None,
    archify_command: Any = None,
) -> dict[str, Any]:
    """`project_root`의 아키텍처 맵을 `map_dir`(기본 `<project_root>/.dev/architecture`)에 만든다.

    `archify_command`는 테스트용이다 - 생략하면 도메인 루프 전에 ensure_archify()를 한 번
    불러 모든 도메인이 그 결과를 쓴다(2026-09-28 최종 리뷰 I1 - 도메인마다 재탐색·재설치를
    막는다). CLI에는 노출하지 않는다: 셸을 거친 명령 문자열이 깨지는 경로를 다시 열지
    않는다(T15).
    """
    root = Path(project_root).resolve()
    map_dir = (Path(map_dir) if map_dir is not None else root / DEFAULT_MAP_DIR).resolve()
    map_dir.mkdir(parents=True, exist_ok=True)
    previous = index_builder._load_json(map_dir / "run-manifest.json") or {}
    # 부분 갱신은 이전 도메인 결과를 보존하지만, 다른 프로젝트의 산출물을 섞지 않는다.
    previous_entries = previous.get("map_domains", previous.get("domains", []))
    previous_domains = {entry["domain"]: entry for entry in previous_entries
                        if isinstance(entry, dict) and isinstance(entry.get("domain"), str)}
    retained = {name: {**deepcopy(entry), "freshness": "retained"}
                for name, entry in previous_domains.items()} if (
                    domain is not None and previous.get("project_root") in (None, str(root))) else {}
    known_domains: set[str] = set(retained)
    report: dict[str, Any] = {
        "view": "service",
        "project_root": str(root),
        "requested_domain": domain,
        "map_dir": str(map_dir),
        "index_path": None,
        "validation_status": "failed",
        "domains": [],
        "changes": None,
        "cross_domain_edge_count": 0,
        "unresolved_edge_count": 0,
        "skipped": [],
        "mermaid_asset": None,
        "missing_inputs": [],
        "labels_applied": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "revision": fallback_renderer._short_head(root),
    }

    def publish() -> None:
        entries = {name: {"domain": name, "validation_status": "not_generated", "html_path": None,
                          "ir_path": None, "backend": None, "capability": "failed"} for name in known_domains}
        entries.update(retained)
        entries.update({entry["domain"]: entry for entry in report["domains"]})
        report["map_domains"] = [entries[name] for name in sorted(entries)]
        _write_json(map_dir / "run-manifest.json", report)
        report["index_path"] = str(index_builder.build_index(map_dir, project_root=root, changes=report["changes"]))
        _write_json(map_dir / "run-manifest.json", report)

    report["validation_status"] = "in_progress"
    publish()
    try:
        head = scanner.scan(root)
    except (OSError, ValueError, RuntimeError) as exc:
        report["validation_status"] = "failed"
        report["reason"] = f"소스 분석을 완료하지 못했습니다: {exc}"
        publish()
        return report
    report["skipped"] = head["skipped"]
    report["unresolved_edge_count"] = len(head["unresolved_edges"])
    report["diagnostics"] = head.get("diagnostics", [])
    # 마지막 소스가 삭제된 경우에도 기준 스캔과 비교해 삭제 내용을 남긴다.
    changes = changes_module.compute_changes(root, changed_since, head) if changed_since else None
    report["changes"] = changes
    if not head["nodes"]:
        retained.clear()
        known_domains.clear()
        report["validation_status"] = "failed"
        _write_json(map_dir / "global.ir.json", {"schema_version": 1, "view": "service", "locale": "ko-KR", "title": "아키텍처 맵", "nodes": [], "edges": []})
        report["missing_inputs"] = [ENTRYPOINT_SCAN_GROUP]
        report["reason"] = (
            "스캔이 노드를 하나도 찾지 못했습니다. 지원 언어(Java Spring·JSP/Servlet) 소스가 없거나 "
            "project_root가 소스 트리를 포함하지 않습니다."
        )
        publish()
        return report

    # 변경 판정은 라벨 적용보다 먼저 한다 - 라벨이 technical_label을 채우면 기준 스캔과
    # 달라져 라벨을 붙인 노드가 모두 "변경"으로 표시된다(설계서 §5.8.3).
    if labels:
        report["labels_applied"] = apply_labels(head, labels)

    ir = {
        "schema_version": 1,
        "view": "service",
        "locale": "ko-KR",
        "title": "아키텍처 맵",
        "nodes": head["nodes"],
        "edges": head["edges"],
        "missing_inputs": [],
        "skipped": head["skipped"],
        "unresolved_edges": head["unresolved_edges"],
        "diagnostics": head.get("diagnostics", []),
    }
    _write_json(map_dir / "global.ir.json", ir)
    parts = splitter.split_by_domain(ir)
    report["cross_domain_edge_count"] = len({eid for part in parts.values() for eid in part.get("cross_domain_edges", [])})
    owners = {node["id"]: name for name, part in parts.items() for node in part["nodes"]
              if not node.get("external_domain") and node.get("kind") != "table"}
    report["domain_relations"] = sorted({(owners[e["source"]], owners[e["target"]])
        for e in head["edges"] if e["source"] in owners and e["target"] in owners
        and owners[e["source"]] != owners[e["target"]]})
    all_domains = sorted(parts)
    known_domains = set(all_domains)
    retained = {name: entry for name, entry in retained.items() if name in known_domains}

    if domain is not None:
        if domain not in parts:
            report["validation_status"] = "failed"
            found = ", ".join(sorted(parts)) or "없음"
            report["reason"] = f"도메인 '{domain}'을 찾지 못했습니다. 찾은 도메인: {found}"
            publish()
            return report
        parts = {domain: parts[domain]}
    else:
        _clear_stale(map_dir, set(parts))

    domain_meta = None
    if changes is not None:
        domain_meta = {key: changes[key] for key in ("available", "base_ref", "base_commit", "reason") if key in changes}
    report["domains"] = [{"domain": name, "validation_status": "pending", "html_path": None,
                           "ir_path": None, "backend": None, "capability": "failed"} for name in sorted(parts)]
    report["validation_status"] = "in_progress"
    publish()
    report["domains"] = []
    # Archify 탐지·설치는 실행당 한 번만 - 도메인마다 다시 부르면 사내망이 막힌
    # 환경에서 도메인 수만큼 설치 시도가 되풀이된다(2026-09-28 최종 리뷰 I1).
    discovery = backend_detector.ensure_archify() if archify_command is None else None
    available_domains = set(parts) | {name for name, entry in retained.items()
        if entry.get("validation_status") in {"verified", "fallback"}
        and entry.get("html_path") and (map_dir / "domains" / f"{name}.html").is_file()}
    detail_prefix = fallback_renderer._viewer_module().anchor("")
    for name in sorted(parts):
        part = parts[name]
        part["title"] = f"{name} 도메인 구조"
        part.setdefault("meta", {})["navigation"] = {"domain": name, "domains": [
            {"name": item, "available": item in available_domains} for item in all_domains]}
        for node in part["nodes"]:
            if node.get("external_domain"):
                node["external_available"] = node["external_domain"] in available_domains
                node["external_detail_available"] = (node["external_domain"] in parts or
                    retained.get(node["external_domain"], {}).get("detail_anchor_prefix") == detail_prefix)
        if domain_meta is not None:
            removed = [item for item in changes.get("removed", [])
                       if any(splitter.domain_of(e.get("file", "")) == name for e in item.get("evidence", []))]
            removed_edges = [item for item in changes.get("removed_edges", [])
                             if any(splitter.domain_of(e.get("file", "")) == name
                                    for e in item.get("source_evidence", []) + item.get("target_evidence", []))]
            part["meta"]["changes"] = {**domain_meta, "removed": removed, "removed_edges": removed_edges}
        report["domains"].append(_render_domain(name, part, map_dir, root, archify_command, discovery,
            preserve_previous=(previous.get("project_root") in (None, str(root))
                and bool(previous_domains.get(name, {}).get("html_path") or previous_domains.get(name, {}).get("last_good")))))

    mermaid_domains = [entry for entry in report["domains"] if entry["backend"] == "mermaid"]
    if mermaid_domains:
        asset = fallback_renderer.ensure_mermaid_asset(map_dir / "assets")
        report["mermaid_asset"] = {"available": asset["available"], "attempts": asset["attempts"]}
        if asset["available"]:
            for entry in mermaid_domains:
                _rerender_with_mermaid_asset(entry, map_dir, root)

    report["validation_status"] = _overall_status(report["domains"])
    publish()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="프로젝트 전체를 스캔해 아키텍처 맵(아키텍처-맵.html)을 만듭니다.")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--map-dir", type=Path)
    parser.add_argument("--changed-since", metavar="REF")
    parser.add_argument("--domain")
    parser.add_argument("--labels", type=Path)
    args = parser.parse_args()

    labels = None
    if args.labels is not None:
        try:
            labels = json.loads(args.labels.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parser.error(f"--labels 파일을 읽을 수 없습니다: {exc}")
        if not isinstance(labels, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in labels.items()
        ):
            parser.error('--labels는 {"스캔 라벨": "한국어 라벨"} 형태의 JSON 객체여야 합니다.')

    report = build_map(args.project_root, args.map_dir, args.changed_since, args.domain, labels)
    # Windows 콘솔 기본 인코딩(cp949)은 보고의 일부 문자(—)를 쓰지 못해 UnicodeEncodeError로
    # 죽는다(2026-09-28 콜드런). 보고는 항상 UTF-8로 낸다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["validation_status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
