"""AskUserQuestion의 질문·선택지·답변을 .dev/{branch-slug}/decisions.md에 기록한다.

PostToolUse 훅이 stdin으로 넘기는 페이로드를 읽어 append한다. 판정하지 않으므로
항상 정상 종료하며, 어떤 실패도 도구 실행을 막지 않는다.

기록 대상은 구조화된 확인 게이트(AskUserQuestion)뿐이다. 자연어로 오간 확인은
남지 않는다 — 무엇을 물었고 어떤 선택지 중 무엇을 골랐는지가 남아야 판단 근거가
되기 때문이다.
"""
import datetime
import io
import json
import os
import subprocess
import sys


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
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        out = ""
    return (out or "no-branch").replace("/", "-")


def render(payload):
    """페이로드를 마크다운 블록으로 만든다. 답변이 없으면 빈 문자열."""
    response = payload.get("tool_response") or {}
    answers = response.get("answers") or {}
    if not answers:
        return ""

    questions = {
        q.get("question"): q
        for q in (payload.get("tool_input", {}).get("questions") or [])
    }
    notes = response.get("annotations") or {}
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    out = []
    for question, answer in answers.items():
        meta = questions.get(question, {})
        out.append(f"\n## {stamp} · {meta.get('header', '결정')}\n\n")
        out.append(f"**Q.** {question}\n\n")
        options = meta.get("options") or []
        if options:
            out.append("선택지:\n\n")
            for opt in options:
                mark = "**→**" if opt.get("label") == answer else "-"
                out.append(f"{mark} {opt.get('label')} — {opt.get('description', '')}\n")
            out.append("\n")
        out.append(f"**A.** {answer}\n")
        note = (notes.get(question) or {}).get("notes")
        if note:
            out.append(f"\n메모: {note}\n")
    return "".join(out)


def main():
    payload = load_payload()
    if not payload or payload.get("tool_name") != "AskUserQuestion":
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
                "AskUserQuestion으로 오간 질문과 선택을 자동 기록한다. "
                "고른 것뿐 아니라 버린 선택지도 남으므로 왜 그렇게 정했는지가 추적된다.\n"
            )
        io.open(path, "a", encoding="utf-8").write(header + block)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
