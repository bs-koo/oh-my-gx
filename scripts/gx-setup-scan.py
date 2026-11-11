#!/usr/bin/env python3
"""설정을 바꾸지 않고 등록된 타입과 추가 빌드 마커를 함께 조사한다."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import runpy
import stat
import sys


MARKERS = ("Makefile", "CMakeLists.txt", "project.yml", "Cargo.toml", "pom.xml",
           "pyproject.toml", "setup.py", "requirements.txt", "go.mod", "*.csproj",
           "*.sln", "composer.json", "build.gradle", "build.gradle.kts", "package.json")
EXCLUDED = {".git", ".svn", ".claude", ".dev", "worktrees", "node_modules", "vendor",
            "build", "out", "dist", "target", ".gradle", ".venv", "venv", "__pycache__",
            ".research", ".next", ".nuxt", "coverage", "bin", "obj"}


def linked(path):
    metadata = path.lstat()
    return path.is_symlink() or bool(getattr(metadata, "st_file_attributes", 0) &
                                    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


_PLAN = None


def plan_rule(name):
    """테스트 계획(gx-test-plan.py)의 detect 판정을 그대로 쓴다."""
    global _PLAN
    if _PLAN is None:
        _PLAN = runpy.run_path(str(Path(__file__).with_name("gx-test-plan.py")))
    return _PLAN[name]


def registered(path, directory, settings):
    """roots가 없으면 detect 일치. roots가 있으면 이름 marker는 root 바로 아래, 경로 marker는 root 아래 어디든."""
    detect = settings.get("detect", [])
    if not plan_rule("detected")(path, detect):
        return False
    if settings.get("roots") is None:
        return True
    names = [p for p in detect if not plan_rule("path_pattern")(p)]
    paths = [p for p in detect if plan_rule("path_pattern")(p)]
    return any((directory == item and plan_rule("detected")(path, names)) or
               (plan_rule("under")(path, item) and plan_rule("detected")(path, paths))
               for item in {relative_root(value) for value in settings["roots"]})


def relative_root(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("roots에는 프로젝트 상대경로를 사용하세요")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValueError("roots가 프로젝트 범위를 벗어납니다")
    return path.as_posix()


def scan(cwd, config_source="auto"):
    root = Path(cwd).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("프로젝트 디렉터리가 없습니다")
    config = root / ".claude/config.json"
    if config_source == "auto":
        config_source = "existing" if config.exists() else "missing"
    if config_source == "missing":
        data = {}
    else:
        if linked(config.parent) or linked(config):
            raise ValueError("설정 링크를 따라가지 않습니다")
        data = json.loads(config.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("projectTypes", {}), dict):
        raise ValueError("projectTypes는 객체여야 합니다")
    types = data.get("projectTypes", {})
    for name, settings in types.items():
        if not isinstance(settings, dict):
            raise ValueError(f"projectTypes.{name}은 객체여야 합니다")
        detect = settings.get("detect", [])
        if not isinstance(detect, list) or any(not isinstance(p, str) or not p for p in detect):
            raise ValueError(f"projectTypes.{name}.detect는 문자열 배열이어야 합니다")
        if "roots" in settings:
            if not isinstance(settings["roots"], list) or not settings["roots"]:
                raise ValueError(f"projectTypes.{name}.roots는 비어 있지 않은 배열이어야 합니다")
            for value in settings["roots"]:
                relative_root(value)
    candidate_patterns = set(MARKERS)
    for settings in types.values():
        candidate_patterns.update(settings.get("detect", []))
    records, errors, skipped_links = [], [], []
    for directory, directories, filenames in os.walk(root, followlinks=False,
                                                    onerror=lambda exc: errors.append(str(exc))):
        current = Path(directory)
        kept = []
        for d in sorted(directories):
            if d.casefold() in EXCLUDED:
                continue
            if linked(current / d):
                skipped_links.append((current / d).relative_to(root).as_posix())
                continue
            kept.append(d)
        directories[:] = kept
        for filename in sorted(filenames):
            candidate = current / filename
            path = candidate.relative_to(root).as_posix()
            if not plan_rule("detected")(path, candidate_patterns) or linked(candidate):
                continue
            local_root = candidate.parent.relative_to(root).as_posix()
            names = [name for name, settings in types.items() if registered(path, local_root, settings)]
            records.append({"path": path, "root": local_root,
                            "registered_types": names,
                            "needs_confirmation": config_source == "template" or not names})
    records.sort(key=lambda item: item["path"])
    registrations = [{"name": name, "detect": settings.get("detect", []),
                      "roots": settings.get("roots"), "has_build": bool(settings.get("build")),
                      "has_test": bool(settings.get("test"))} for name, settings in types.items()]
    return {"config_source": config_source, "registrations": registrations,
            "markers": records, "scan_errors": errors,
            "skipped_links": sorted(skipped_links),
            "requires_confirmation": bool(errors) or bool(skipped_links) or any(item["needs_confirmation"] for item in records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--config-source", choices=("template", "existing", "auto"), default="auto")
    args = parser.parse_args()
    try:
        result = scan(args.cwd, args.config_source)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
