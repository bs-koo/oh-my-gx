"""Codex hook boundary for the shared Bash protection guard."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent


def deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def find_bash():
    path_candidate = shutil.which("bash")
    candidates = []
    if os.name == "nt":
        # System32\bash.exe is the WSL launcher. It cannot run this Windows
        # workspace's script path, so prefer the standard Git Bash installs.
        candidates.extend(
            [
                str(
                    Path(os.environ.get("ProgramFiles", "C:/Program Files"))
                    / "Git/bin/bash.exe"
                ),
                str(
                    Path(os.environ.get("LOCALAPPDATA", "."))
                    / "Programs/Git/bin/bash.exe"
                ),
            ]
        )
    candidates.append(path_candidate)

    for path in candidates:
        normalized = str(path).replace("\\", "/").lower() if path else ""
        if normalized.endswith("/windows/system32/bash.exe"):
            continue
        if path and Path(path).is_file():
            return path
    return None


def run_guard(payload: dict, *, bash: str | None = None) -> dict | None:
    if not isinstance(payload, dict):
        return deny("GX 훅 입력이 객체가 아닙니다.")
    executable = bash or find_bash()
    if not executable:
        return deny("GX 가드를 실행할 Bash를 찾지 못했습니다.")
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        return deny("GX 훅의 작업 경로가 유효하지 않습니다.")

    try:
        proc = subprocess.run(
            [executable, str(HERE / "pre-tool-guard.sh")],
            input=json.dumps(payload),
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=cwd,
            timeout=30,
        )
        if proc.returncode:
            return deny("GX 가드 실행 실패: " + proc.stderr[-500:])
        if not proc.stdout.strip():
            return None
        result = json.loads(proc.stdout)
        output = result["hookSpecificOutput"]
        if output["permissionDecision"] == "ask":
            output["permissionDecision"] = "deny"
        if output["permissionDecision"] not in ("allow", "deny"):
            return deny("GX 가드가 지원하지 않는 판정을 반환했습니다.")
        return result
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        return deny("GX 가드 오류: " + str(exc))


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in ("guard", "capture"):
        print("사용: codex_hook.py guard|capture", file=sys.stderr)
        return 2
    if mode == "capture":
        proc = subprocess.run([sys.executable, str(HERE / "capture_decision.py")])
        return proc.returncode

    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        result = run_guard(payload)
    except (ValueError, AttributeError, UnicodeError) as exc:
        result = deny("GX 훅 입력 오류: " + str(exc))
    if result is not None:
        print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
