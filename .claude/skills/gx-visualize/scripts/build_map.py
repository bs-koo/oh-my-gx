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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    name: str, part: dict[str, Any], map_dir: Path, project_root: Path, archify_command: Any
) -> dict[str, Any]:
    ir_path = map_dir / "ir" / f"{name}{IR_SUFFIX}"
    receipts_dir = map_dir / "receipts"
    entry: dict[str, Any] = {
        "domain": name,
        "backend": None,
        "validation_status": "failed",
        "html_path": None,
        "ir_path": str(ir_path) if ir_path.is_file() else None,
        "receipt_path": None,
        "missing_inputs": sorted(set(part.get("missing_inputs", []))),
        "added": sum(1 for node in part["nodes"] if node.get("change") == "added"),
        "changed": sum(1 for node in part["nodes"] if node.get("change") == "changed"),
    }
    # 검증을 통과하기 전에는 이전 {domain}.ir.json을 덮어쓰지 않는다(설계서 §6).
    pending = map_dir / "ir" / f".{name}{IR_SUFFIX}.pending"
    _write_json(pending, part)
    receipt = validator.validate(pending, project_root=project_root)
    if receipt["status"] != "valid":
        pending.unlink(missing_ok=True)
        entry["errors"] = receipt["errors"]
        return entry
    pending.replace(ir_path)
    entry["ir_path"] = str(ir_path)
    try:
        result = archify_renderer.render_archify(
            ir_path, receipts_dir, archify_command,
            project_root=project_root, output_name=name, html_dir=map_dir / "domains",
        )
    except (OSError, ValueError, RuntimeError) as exc:
        entry["errors"] = [str(exc)]
        entry["receipt_path"] = str(receipts_dir / f"{name}.receipt.json")
        return entry
    rendered = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    entry.update(
        backend=result["backend"],
        validation_status=_domain_status(rendered),
        html_path=result["html_path"],
        receipt_path=result["receipt_path"],
        missing_inputs=rendered.get("missing_inputs", entry["missing_inputs"]),
    )
    return entry


def _rerender_with_mermaid_asset(entry: dict[str, Any], map_dir: Path, project_root: Path) -> None:
    """Mermaid로 폴백한 도메인을 공유 자산으로 다시 그려 브라우저에서 실제 그림이 보이게 한다.

    render_fallback.render()는 영수증을 검증기 결과로 새로 쓴다. 그대로 두면 Archify 실패
    기록(attempts)과 폴백 판정이 사라지고 인덱스가 이 도메인을 "통과"로 표시한다(2026-09-28
    콜드런에서 관찰). 다시 그리기 전의 영수증을 되돌려 놓는다.
    """
    receipt_path = Path(entry["receipt_path"])
    preserved = receipt_path.read_text(encoding="utf-8")
    try:
        fallback_renderer.render(
            entry["ir_path"], map_dir / "receipts", "mermaid",
            project_root=project_root, output_name=entry["domain"],
            html_dir=map_dir / "domains", mermaid_asset_href=MERMAID_ASSET_HREF,
        )
    except (OSError, ValueError) as exc:
        entry.setdefault("errors", []).append(f"Mermaid 자산으로 다시 그리지 못했습니다: {exc}")
    finally:
        receipt_path.write_text(preserved, encoding="utf-8")


def build_map(
    project_root: Path | str,
    map_dir: Path | str | None = None,
    changed_since: str | None = None,
    domain: str | None = None,
    labels: dict[str, str] | None = None,
    archify_command: Any = None,
) -> dict[str, Any]:
    """`project_root`의 아키텍처 맵을 `map_dir`(기본 `<project_root>/.dev/architecture`)에 만든다.

    `archify_command`는 테스트용이다 - 생략하면 render_archify가 스스로 Archify를 찾는다.
    CLI에는 노출하지 않는다: 셸을 거친 명령 문자열이 깨지는 경로를 다시 열지 않는다(T15).
    """
    root = Path(project_root).resolve()
    map_dir = Path(map_dir) if map_dir is not None else root / DEFAULT_MAP_DIR
    report: dict[str, Any] = {
        "view": "service",
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
    }

    head = scanner.scan(root)
    report["skipped"] = head["skipped"]
    report["unresolved_edge_count"] = len(head["unresolved_edges"])
    if not head["nodes"]:
        report["missing_inputs"] = [ENTRYPOINT_SCAN_GROUP]
        report["reason"] = (
            "스캔이 노드를 하나도 찾지 못했습니다. 지원 언어(Java Spring·JSP/Servlet) 소스가 없거나 "
            "project_root가 소스 트리를 포함하지 않습니다."
        )
        return report

    # 변경 판정은 라벨 적용보다 먼저 한다 - 라벨이 technical_label을 채우면 기준 스캔과
    # 달라져 라벨을 붙인 노드가 모두 "변경"으로 표시된다(설계서 §5.8.3).
    changes = changes_module.compute_changes(root, changed_since, head) if changed_since else None
    report["changes"] = changes
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
    }
    parts = splitter.split_by_domain(ir)
    kept_edges = {edge["id"] for part in parts.values() for edge in part["edges"]}
    report["cross_domain_edge_count"] = sum(1 for edge in head["edges"] if edge["id"] not in kept_edges)

    if domain is not None:
        if domain not in parts:
            found = ", ".join(sorted(parts)) or "없음"
            report["reason"] = f"도메인 '{domain}'을 찾지 못했습니다. 찾은 도메인: {found}"
            return report
        parts = {domain: parts[domain]}
    else:
        _clear_stale(map_dir, set(parts))

    domain_meta = None
    if changes is not None:
        domain_meta = {key: changes[key] for key in ("available", "base_ref", "base_commit", "reason") if key in changes}
    for name in sorted(parts):
        part = parts[name]
        part["title"] = f"{name} 도메인 구조"
        if domain_meta is not None:
            part["meta"] = {"changes": domain_meta}
        report["domains"].append(_render_domain(name, part, map_dir, root, archify_command))

    mermaid_domains = [entry for entry in report["domains"] if entry["backend"] == "mermaid"]
    if mermaid_domains:
        asset = fallback_renderer.ensure_mermaid_asset(map_dir / "assets")
        report["mermaid_asset"] = {"available": asset["available"], "attempts": asset["attempts"]}
        if asset["available"]:
            for entry in mermaid_domains:
                _rerender_with_mermaid_asset(entry, map_dir, root)

    report["index_path"] = str(index_builder.build_index(map_dir, project_root=root, changes=changes))
    report["validation_status"] = _overall_status(report["domains"])
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
