#!/usr/bin/env python3
"""Validate a GX visualization IR document using only the standard library."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STATUSES = {"planned", "in_progress", "review", "verified", "blocked", "unknown"}
VIEWS = {"trace", "progress", "impact", "service", "sequence"}
EVIDENCE_KINDS = {"artifact", "code", "test", "command", "design", "inferred"}
LOCATOR_TYPES = {"xlsx", "pdf"}


def _error(path: str, message: str) -> str:
    return f"{path}: {message}"


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value}")


def _validate_locator(locator: Any, base: str, errors: list[tuple[str, str]]) -> None:
    if not isinstance(locator, dict):
        errors.append((base, "must be an object"))
        return
    locator_type = locator.get("type")
    if not isinstance(locator_type, str) or locator_type not in LOCATOR_TYPES:
        errors.append((f"{base}.type", f"must be one of {', '.join(sorted(LOCATOR_TYPES))}"))
        return
    if locator_type == "xlsx":
        for field in ("sheet", "cell"):
            if not isinstance(locator.get(field), str) or not locator[field]:
                errors.append((f"{base}.{field}", "must be a non-empty string"))
    elif locator_type == "pdf":
        page = locator.get("page")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            errors.append((f"{base}.page", "must be a positive integer"))


def validate(path: Path | str, project_root: Path | str | None = None) -> dict[str, Any]:
    """Return a deterministic validation receipt for a UTF-8 IR JSON file."""
    path = Path(path)
    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    missing_inputs: set[str] = set()
    node_count = edge_count = 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=_reject_constant)
    except FileNotFoundError:
        return _receipt("failed", [_error("$", "input file does not exist")], [], 0, 0, [str(path)])
    except (OSError, UnicodeDecodeError) as exc:
        return _receipt("failed", [_error("$", f"cannot read input: {exc}")], [], 0, 0, [str(path)])
    except json.JSONDecodeError as exc:
        return _receipt("failed", [_error("$", f"invalid JSON at line {exc.lineno}, column {exc.colno}")], [], 0, 0, [])
    except ValueError as exc:
        return _receipt("failed", [_error("$", f"invalid JSON: {exc}")], [], 0, 0, [])

    if not isinstance(payload, dict):
        return _receipt("failed", [_error("$", "document must be an object")], [], 0, 0, [])

    try:
        evidence_root = path.parent.resolve() if project_root is None else Path(project_root).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        return _receipt("failed", [_error("$.project_root", f"invalid project root: {exc}")], [], 0, 0, [])
    if not evidence_root.is_dir():
        return _receipt("failed", [_error("$.project_root", "must be an existing directory")], [], 0, 0, [])

    if isinstance(payload.get("schema_version"), bool) or payload.get("schema_version") != 1:
        errors.append(("$.schema_version", "must be integer 1"))
    if not isinstance(payload.get("view"), str) or payload.get("view") not in VIEWS:
        errors.append(("$.view", f"must be one of {', '.join(sorted(VIEWS))}"))
    for field in ("locale", "title"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            errors.append((f"$.{field}", "must be a non-empty string"))
    if "meta" in payload and not isinstance(payload["meta"], dict):
        errors.append(("$.meta", "must be an object"))

    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        errors.append(("$.nodes", "must be an array"))
        nodes = []
    edges = payload.get("edges")
    if not isinstance(edges, list):
        errors.append(("$.edges", "must be an array"))
        edges = []
    node_count, edge_count = len(nodes), len(edges)
    node_ids: dict[str, int] = {}
    for index, node in enumerate(nodes):
        base = f"$.nodes[{index}]"
        if not isinstance(node, dict):
            errors.append((base, "must be an object"))
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            errors.append((f"{base}.id", "must be a non-empty string"))
        elif node_id in node_ids:
            errors.append((f"{base}.id", f"duplicate node id {node_id!r}; first declared at $.nodes[{node_ids[node_id]}].id"))
        else:
            node_ids[node_id] = index
        if not isinstance(node.get("kind"), str) or not node["kind"]:
            errors.append((f"{base}.kind", "must be a non-empty string"))
        if not isinstance(node.get("label"), str) or not node["label"]:
            errors.append((f"{base}.label", "must be a non-empty string"))
        if not isinstance(node.get("status"), str) or node.get("status") not in STATUSES:
            errors.append((f"{base}.status", f"must be one of {', '.join(sorted(STATUSES))}"))
        if "technical_label" in node and not isinstance(node["technical_label"], str):
            errors.append((f"{base}.technical_label", "must be a string"))
        evidence = node.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append((f"{base}.evidence", "must be an array"))
            evidence = []
        for ev_index, evidence_item in enumerate(evidence):
            ev_path = f"{base}.evidence[{ev_index}]"
            if not isinstance(evidence_item, dict):
                errors.append((ev_path, "must be an object"))
                continue
            kind = evidence_item.get("kind")
            if not isinstance(kind, str) or kind not in EVIDENCE_KINDS:
                errors.append((f"{ev_path}.kind", f"must be one of {', '.join(sorted(EVIDENCE_KINDS))}"))
                continue
            if kind == "inferred":
                if any(field in evidence_item for field in ("file", "line", "locator")):
                    errors.append((ev_path, "inferred evidence must not include file, line, or locator"))
                continue
            file_name = evidence_item.get("file")
            if not isinstance(file_name, str) or not file_name:
                errors.append((f"{ev_path}.file", "must be a non-empty relative path"))
                continue
            try:
                candidate = Path(file_name)
                evidence_path = (evidence_root / candidate).resolve()
            except (OSError, ValueError, RuntimeError) as exc:
                errors.append((f"{ev_path}.file", f"invalid evidence path: {exc}"))
                continue
            try:
                evidence_path.relative_to(evidence_root)
                confined = True
            except ValueError:
                confined = False
            if candidate.is_absolute() or not confined:
                errors.append((f"{ev_path}.file", "must be relative to and remain within the project root"))
                continue
            if not evidence_path.is_file():
                errors.append((f"{ev_path}.file", f"evidence file does not exist: {file_name}"))
                missing_inputs.add(file_name)
                continue

            has_line = "line" in evidence_item
            has_locator = "locator" in evidence_item
            if has_line == has_locator:
                errors.append((ev_path, "must include exactly one of line or locator"))
                continue
            if has_locator:
                _validate_locator(evidence_item["locator"], f"{ev_path}.locator", errors)
                continue

            line = evidence_item["line"]
            if not isinstance(line, int) or isinstance(line, bool) or line < 1:
                errors.append((f"{ev_path}.line", "must be a positive integer"))
                continue
            try:
                line_count = len(evidence_path.read_text(encoding="utf-8-sig").splitlines())
            except (OSError, UnicodeError) as exc:
                errors.append((f"{ev_path}.file", f"cannot read evidence file: {exc}"))
            else:
                if line > line_count:
                    errors.append((f"{ev_path}.line", f"must not exceed file line count ({line_count})"))

    edge_ids: dict[str, int] = {}
    for index, edge in enumerate(edges):
        base = f"$.edges[{index}]"
        if not isinstance(edge, dict):
            errors.append((base, "must be an object"))
            continue
        for field in ("id", "source", "target", "relation"):
            if not isinstance(edge.get(field), str) or not edge[field]:
                errors.append((f"{base}.{field}", "must be a non-empty string"))
        edge_id = edge.get("id")
        if isinstance(edge_id, str) and edge_id:
            if edge_id in edge_ids:
                errors.append((f"{base}.id", f"duplicate edge id {edge_id!r}; first declared at $.edges[{edge_ids[edge_id]}].id"))
            else:
                edge_ids[edge_id] = index
        for field in ("source", "target"):
            value = edge.get(field)
            if isinstance(value, str) and value not in node_ids:
                errors.append((f"{base}.{field}", f"references missing node {value!r}"))

    errors.sort(key=lambda item: (item[0], item[1]))
    warnings.sort(key=lambda item: (item[0], item[1]))
    return _receipt("failed" if errors else "valid", [f"{p}: {m}" for p, m in errors], [f"{p}: {m}" for p, m in warnings], node_count, edge_count, sorted(missing_inputs))


def _receipt(status: str, errors: list[str], warnings: list[str], node_count: int, edge_count: int, missing_inputs: list[str]) -> dict[str, Any]:
    return {"status": status, "errors": errors, "warnings": warnings, "node_count": node_count, "edge_count": edge_count, "missing_inputs": missing_inputs}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a GX visualization IR JSON file")
    parser.add_argument("path", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = validate(args.path, project_root=args.project_root)
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if receipt["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
