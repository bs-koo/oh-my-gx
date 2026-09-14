#!/usr/bin/env python3
"""Export Codex-consumable role bodies and the setup config template."""

import argparse
import json
from pathlib import Path
import re
import sys


ROLE_DIR = Path(".claude/skills/gx-dev/references/codex-roles")
TEMPLATE = Path(".claude/skills/gx-setup/references/config.template.json")


def _role(source: Path) -> tuple[str, str, list[str], str]:
    text = source.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", text, flags=re.S)
    if not match:
        raise ValueError(f"역할 frontmatter 오류: {source}")
    header, body = match.groups()
    name = re.search(r"^name:\s*([^\s]+)\s*$", header, flags=re.M)
    model = re.search(r"^model:\s*([^\s]+)\s*$", header, flags=re.M)
    tools_section = re.search(r"^tools:\s*\n((?:[ \t]+- [^\n]+\n?)+)", header, flags=re.M)
    if not name or name[1] != source.stem:
        raise ValueError(f"역할 이름 오류: {source}")
    if not model or model[1] not in {"opus", "sonnet"}:
        raise ValueError(f"역할 티어를 결정할 수 없습니다: {source}")
    if not tools_section:
        raise ValueError(f"역할 도구 목록 오류: {source}")
    tools = [line.split("- ", 1)[1].strip() for line in tools_section[1].splitlines()]
    if not all(tools):
        raise ValueError(f"역할 도구 목록 오류: {source}")
    return name[1], model[1], tools, body


def expected_files(root: Path) -> dict[Path, bytes]:
    root = Path(root)
    files: dict[Path, bytes] = {}
    index = {}
    for source in sorted((root / "agents").glob("*.md")):
        name, model, tools, body = _role(source)
        files[root / ROLE_DIR / source.name] = body.encode("utf-8")
        index[name] = {
            "tier": "high" if model == "opus" else "mid",
            "file": source.name,
            "tools": tools,
        }
    if not index:
        raise ValueError("역할 원본이 없습니다.")
    files[root / ROLE_DIR / "index.json"] = (
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    config = (root / ".claude/config.json").read_bytes()
    json.loads(config.decode("utf-8"))
    files[root / TEMPLATE] = config
    return files


def check_files(root: Path) -> list[str]:
    files = expected_files(root)
    errors = [str(path) for path, content in files.items()
              if not path.is_file() or path.read_bytes() != content]
    role_dir = Path(root) / ROLE_DIR
    errors.extend(str(path) for path in sorted(role_dir.glob("*.md")) if path not in files)
    return errors


def write_files(root: Path) -> None:
    files = expected_files(root)
    role_dir = Path(root) / ROLE_DIR
    stale = sorted(path for path in role_dir.glob("*.md") if path not in files)
    if stale:
        raise ValueError("잔여 역할 파일을 수동 검토 후 삭제하세요: " + ", ".join(map(str, stale)))
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="생성물 바이트 정합성 검사")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.check:
            errors = check_files(root)
            for error in errors:
                print(f"리소스 드리프트: {error}", file=sys.stderr)
            return 1 if errors else 0
        write_files(root)
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"리소스 입력 오류: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
