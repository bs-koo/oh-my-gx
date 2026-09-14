#!/usr/bin/env python3
"""Render and optionally merge manually installed Codex hooks."""

import argparse
from copy import deepcopy
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def windows_command(*args: str) -> str:
    # cmd.exe expands %...% even inside quotes. Reject forms that cannot be
    # represented safely as a command string; always quote the rest.
    if any(any(char in arg for char in ('%', '^', '"', '\r', '\n', '\0')) for arg in args):
        raise ValueError("Windows cmd 경로에 %, ^, 따옴표, 줄바꿈 또는 NUL 문자는 사용할 수 없습니다.")
    return " ".join(f'"{arg}"' for arg in args)


def render(root: Path, python: str) -> dict:
    script = (root / ".claude/hooks/codex_hook.py").as_posix()
    posix_python = python.replace("\\", "/")
    events = {}
    for event, matcher, mode in (
        ("PreToolUse", "^Bash$", "guard"),
        ("PostToolUse", "AskUserQuestion|request_user_input", "capture"),
    ):
        events[event] = [{
            "matcher": matcher,
            "hooks": [{
                "type": "command",
                "command": shlex.join([posix_python, script, mode]),
                "commandWindows": windows_command(python, script, mode),
                "timeout": 35,
            }],
        }]
    return {"hooks": events}


def merge(existing: dict, generated: dict) -> dict:
    if not isinstance(existing, dict):
        raise ValueError("기존 설정은 JSON 객체여야 합니다.")
    result = deepcopy(existing)
    hooks = result.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("기존 hooks는 JSON 객체여야 합니다.")
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError(f"기존 hooks.{event}는 배열이어야 합니다.")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError(f"기존 hooks.{event} 항목의 hooks는 배열이어야 합니다.")
            if any(not isinstance(item, dict) for item in group["hooks"]):
                raise ValueError(f"기존 hooks.{event} 명령은 객체여야 합니다.")
    for event, groups in generated["hooks"].items():
        target = hooks.setdefault(event, [])
        if not isinstance(target, list):
            raise ValueError(f"기존 hooks.{event}는 배열이어야 합니다.")
        for group in groups:
            if group not in target:
                target.append(deepcopy(group))
    return result


def check_generated_command(command: str, payload: dict, expected: str | None) -> None:
    proc = subprocess.run(
        command,
        shell=True,
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=35,
    )
    if proc.returncode:
        raise RuntimeError(f"생성된 훅 명령 실패 (rc={proc.returncode}): {proc.stderr[-500:]}")
    if expected is None:
        if proc.stdout.strip():
            raise RuntimeError("무해한 명령에 훅이 출력했습니다: " + proc.stdout[-500:])
    else:
        try:
            decision = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("훅 판정 JSON이 유효하지 않습니다.") from exc
        if decision != expected:
            raise RuntimeError(f"훅 판정 오류: {decision!r} (기대: {expected!r})")


def self_test(generated: dict) -> None:
    command = generated["hooks"]["PreToolUse"][0]["hooks"][0]
    field = "commandWindows" if os.name == "nt" else "command"
    for instruction, expected in (("git push --force origin main", "deny"), ("git status", None)):
        payload = {
            "cwd": str(Path.cwd().resolve()),
            "tool_name": "Bash",
            "tool_input": {"command": instruction},
        }
        check_generated_command(command[field], payload, expected)


def warn_old_gx(existing: dict, generated: dict) -> None:
    for event, groups in generated["hooks"].items():
        current = generated["hooks"][event][0]
        for group in existing.get("hooks", {}).get(event, []):
            if group == current or not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []):
                commands = str(hook.get("command", "")) + " " + str(hook.get("commandWindows", ""))
                if any(name in commands for name in ("codex_hook.py", "pre-tool-guard.sh", "capture-decision.sh")):
                    print(f"경고: 기존 {event} GX 훅이 남아 중복 실행될 수 있습니다.", file=sys.stderr)
                    break


def backup(target: Path, original: bytes) -> Path:
    start = datetime.now()
    for attempt in range(1000):
        stamp = (start + timedelta(microseconds=attempt)).strftime("%Y%m%dT%H%M%S%f")
        path = target.with_name(target.name + ".bak-" + stamp)
        try:
            with path.open("xb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            return path
        except FileExistsError:
            continue
    raise RuntimeError("충돌 없는 백업 파일 이름을 만들지 못했습니다.")


def write_config(target: Path, generated: dict) -> None:
    original = target.read_bytes() if target.exists() else None
    if original is None:
        existing = {}
    else:
        try:
            existing = json.loads(original.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise ValueError("기존 설정 JSON을 읽을 수 없습니다.") from exc
    merged = merge(existing, generated)
    warn_old_gx(existing, generated)
    if merged == existing:
        print(f"이미 설치됨: {target}", file=sys.stderr)
        return
    contents = (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=target.name + ".tmp-", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        if original is not None:
            saved = backup(target, original)
            print(f"기존 파일 백업: {saved}", file=sys.stderr)
        os.replace(temp_path, target)
        print(f"기록 완료: {target}", file=sys.stderr)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Codex hooks 설정을 렌더링하고 자체 검증합니다.")
    parser.add_argument("--write", type=Path, metavar="PATH", help="기존 hooks를 보존하며 PATH에 기록")
    parser.add_argument("--cmd", action="store_true", help="Windows commandWindows 호환 옵션")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        generated = render(root, sys.executable)
        self_test(generated)
        if args.write is None:
            print(json.dumps(generated, ensure_ascii=True, indent=2))
        else:
            write_config(args.write, generated)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"훅 설치 실패: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
