#!/usr/bin/env python3
"""Fingerprint project files and merge scan candidates into the accumulated map."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

SCAN_SUFFIXES = (".java", ".jsp", ".xml")

EXCLUDED_DIRS = frozenset(
    {".git", ".dev", ".superpowers", "__pycache__", "node_modules", "build", "target", "out", "dist"}
)


def _is_excluded(path: Path, root: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts[:-1])


def fingerprint(path: Path | str, vcs: str) -> str:
    path = Path(path)
    if vcs == "git":
        result = subprocess.run(
            ["git", "hash-object", str(path)],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    stat = path.stat()
    return f"{stat.st_mtime_ns}-{stat.st_size}"


def changed_paths(project_root: Path | str, manifest: dict[str, Any], vcs: str) -> tuple[list[str], list[str]]:
    root = Path(project_root).resolve()
    recorded = manifest.get("files", {})
    present: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if _is_excluded(path, root):
            continue
        present[path.relative_to(root).as_posix()] = fingerprint(path, vcs)

    changed = sorted(
        name for name, value in present.items() if recorded.get(name, {}).get("fingerprint") != value
    )
    removed = sorted(name for name in recorded if name not in present)
    return changed, removed


def merge(
    previous_ir: dict[str, Any],
    candidate: dict[str, Any],
    previous_manifest: dict[str, Any],
    removed_files: list[str],
    fingerprints: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fingerprints = fingerprints or {}
    recorded = dict(previous_manifest.get("files", {}))
    touched = set(candidate.get("files", {})) | set(removed_files)

    stale_ids: set[str] = set()
    for name in touched:
        stale_ids.update(recorded.get(name, {}).get("nodes", []))

    # A node can be claimed by more than one file (e.g. a table referenced from
    # two mapper XMLs). Only drop it if every file that claims it was touched.
    retained = {
        node_id
        for name, entry in recorded.items()
        if name not in touched
        for node_id in entry.get("nodes", [])
    }
    stale_ids -= retained

    nodes = {n["id"]: n for n in previous_ir.get("nodes", []) if n["id"] not in stale_ids}
    for node in candidate.get("nodes", []):
        nodes[node["id"]] = node

    edges = {e["id"]: e for e in previous_ir.get("edges", [])}
    for edge in candidate.get("edges", []):
        edges[edge["id"]] = edge
    edges = {
        key: edge
        for key, edge in edges.items()
        if edge["source"] in nodes and edge["target"] in nodes
    }

    for name in removed_files:
        recorded.pop(name, None)
    for name, node_ids in candidate.get("files", {}).items():
        recorded[name] = {
            "fingerprint": fingerprints.get(name, recorded.get(name, {}).get("fingerprint", "")),
            "nodes": sorted(node_ids),
        }

    merged_ir = dict(previous_ir)
    merged_ir["nodes"] = [nodes[key] for key in sorted(nodes)]
    merged_ir["edges"] = [edges[key] for key in sorted(edges)]
    new_manifest = dict(previous_manifest)
    new_manifest["files"] = dict(sorted(recorded.items()))
    return merged_ir, new_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge scan candidates into the accumulated architecture map.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--vcs", default="git")
    parser.add_argument("--previous-ir", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--removed", action="append", default=[])
    parser.add_argument("--out-ir", required=True)
    parser.add_argument("--out-manifest", required=True)
    args = parser.parse_args()

    def _load(name: str, fallback: dict[str, Any]) -> dict[str, Any]:
        path = Path(name)
        if not path.is_file():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))

    previous_ir = _load(args.previous_ir, {"nodes": [], "edges": []})
    manifest = _load(args.manifest, {"schema_version": 1, "files": {}})
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))

    project_root = Path(args.project_root)
    fingerprints = {
        name: fingerprint(project_root / name, args.vcs) for name in candidate.get("files", {})
    }

    merged_ir, new_manifest = merge(previous_ir, candidate, manifest, args.removed, fingerprints)
    Path(args.out_ir).write_text(json.dumps(merged_ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.out_manifest).write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
