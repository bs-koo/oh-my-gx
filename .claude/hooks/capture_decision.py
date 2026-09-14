"""AskUserQuestion의 질문·선택지·답변을 .dev/{branch-slug}/decisions.md에 기록한다.

PostToolUse 훅이 stdin으로 넘기는 페이로드를 읽어 append한다. 판정하지 않으므로
항상 정상 종료하며, 어떤 실패도 도구 실행을 막지 않는다.

기록 대상은 구조화된 확인 게이트(AskUserQuestion·request_user_input)다.
자연어로 오간 확인은 답변이 확정된 뒤 같은 기록기에 명시적으로 전달해야 한다.
"""
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import sys

# hooks.json·plugin.json의 PostToolUse matcher와 같은 집합이어야 한다. matcher만 넓히고
# 여기를 좁혀두면 Codex의 request_user_input이 matcher에는 걸리고 기록은 남지 않는다.
CAPTURED_TOOLS = ("AskUserQuestion", "request_user_input")


def load_payload():
    """훅 페이로드를 읽는다.

    Windows에서 sys.stdin은 cp949로 디코드되어 한글이 서로게이트로 깨진다.
    바이너리로 읽어 UTF-8로 직접 디코드한다.
    """
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        return json.loads(raw)
    except Exception:
        return None


def branch_slug(cwd):
    """현재 브랜치명을 slug로 돌려준다. git이 아니거나 실패하면 no-branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode and "detected dubious ownership in repository" in (result.stderr or "").lower():
            resolved_cwd = Path(cwd).resolve()
            root = next((parent for parent in (resolved_cwd, *resolved_cwd.parents)
                         if (parent / ".git").exists()), None)
            if root is not None:
                result = subprocess.run(
                    ["git", "-c", f"safe.directory={root.as_posix()}", "branch", "--show-current"],
                    cwd=cwd, capture_output=True, text=True, timeout=5,
                )
        out = result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        out = ""
    return (out or "no-branch").replace("/", "-")


def answer_rows(payload: dict) -> list[tuple[str, dict, list[str], str | None]]:
    """질문 본문 키와 Codex 질문 id 키를 같은 답변 행으로 정규화한다."""
    questions = (payload.get("tool_input") or {}).get("questions") or []
    by_key = {}
    for question in questions:
        for key in (question.get("id"), question.get("question")):
            if key:
                by_key[key] = question

    response = payload.get("tool_response") or {}
    notes = response.get("annotations") or {}
    rows = []
    for key, answer in (response.get("answers") or {}).items():
        meta = by_key.get(key, {})
        values = answer.get("answers", []) if isinstance(answer, dict) else answer
        if not isinstance(values, list):
            values = [values]
        values = [str(value) for value in values if value is not None]
        values = [value for value in values if value.strip()]
        if values:
            note = (notes.get(key) or {}).get("notes")
            rows.append((meta.get("question", key), meta, values, note))
    return rows


def render(payload):
    """페이로드를 마크다운 블록으로 만든다. 답변이 없으면 빈 문자열."""
    rows = answer_rows(payload)
    if not rows:
        return ""

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    out = []
    for question, meta, values, note in rows:
        out.append(f"\n## {stamp} · {meta.get('header', '결정')}\n\n")
        out.append(f"**Q.** {question}\n\n")
        if meta.get("id"):
            out.append(f"**ID.** {meta['id']}\n\n")
        options = meta.get("options") or []
        if options:
            out.append("선택지:\n\n")
            matched = set()
            for opt in options:
                chosen = opt.get("label") in values
                if chosen:
                    matched.add(opt.get("label"))
                out.append(f"{'**→**' if chosen else '-'} {opt.get('label')} — {opt.get('description', '')}\n")
            for value in values:
                if value not in matched:
                    out.append(f"**→** (직접 입력) {value}\n")
            out.append("\n")
        out.append(f"**A.** {', '.join(values)}\n")
        if note:
            out.append(f"\n메모: {note}\n")
    return "".join(out)


def main():
    payload = load_payload()
    if not payload or payload.get("tool_name") not in CAPTURED_TOOLS:
        return 0

    block = render(payload)
    if not block:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    out_dir = os.path.join(cwd, ".dev", branch_slug(cwd))
    path = os.path.join(out_dir, "decisions.md")
    try:
        os.makedirs(out_dir, exist_ok=True)
        header = ""
        if not os.path.exists(path):
            header = (
                "# 의사결정 기록\n\n"
                "확인 질문과 선택을 기록한다. "
                "고른 것뿐 아니라 버린 선택지도 남으므로 왜 그렇게 정했는지가 추적된다.\n"
            )
        io.open(path, "a", encoding="utf-8").write(header + block)
    except Exception as exc:
        print(f"의사결정 기록 저장 실패: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
