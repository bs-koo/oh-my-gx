"""Codex 질문을 등록하고 실제 답변 기록 전까지 phase 진행을 차단한다.

이 helper는 정규화된 입력을 검증한다. 앱 팝업, 질문 도구의 용도 제한,
실제 사용자 이벤트 여부는 증명하지 않으므로 호출자가 현재 스키마와 응답을 확인한다.
모든 명령은 --cwd PROJECT --dev-dir .dev/SLUG를 받고 register/answer는
--input UTF8_JSON_FILE을 받는다. status의 exit 2는 미응답 또는 상태 오류다.
"""

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid


PENDING = "pending-question.json"
RECEIPT = "answered-question.json"
HEADER = "# 의사결정 기록\n\n확인 질문과 선택을 기록한다.\n"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_text(path, text):
    """임시 파일과 replace로 기존 파일을 완전한 내용으로만 교체한다."""
    descriptor, temporary = tempfile.mkstemp(prefix=".question-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def workspace(cwd, dev_dir):
    root = Path(cwd).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("cwd가 디렉터리가 아닙니다.")
    relative = Path(dev_dir)
    segment = relative.parts[1] if len(relative.parts) == 2 else ""
    if (relative.is_absolute() or len(relative.parts) != 2
            or relative.parts[0] != ".dev" or not segment
            or segment in (".", "..") or segment.endswith((".", " "))
            or any(ord(char) < 32 or ord(char) == 127 or char in '<>:"/\\|?*' for char in segment)
            or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", segment, re.IGNORECASE)):
        raise ValueError("dev-dir는 .dev/<안전한 작업 slug> 형식이어야 합니다.")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("dev-dir가 프로젝트 외부를 가리킵니다.")
    # 기존 파일 symlink를 통해 외부를 읽거나 수정하지 않는다.
    for name in (PENDING, RECEIPT, "decisions.md", ".question-lock"):
        path = target / name
        if path.is_symlink() or not path.resolve().is_relative_to(target):
            raise ValueError("질문 상태 파일은 외부 경로를 가리킬 수 없습니다.")
    return target


@contextmanager
def locked(directory):
    """동시 호출은 보류한다. 비정상 종료 후 lock은 확인 후 수동 복구한다."""
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / ".question-lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + "은 빈 문자열일 수 없습니다.")
    return value


def questions_input(value):
    if not isinstance(value, dict):
        raise ValueError("질문 입력은 객체여야 합니다.")
    phase = nonempty(value.get("phase"), "phase")
    questions = value.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= 3:
        raise ValueError("질문은 1~3개여야 합니다.")
    result, identifiers = [], set()
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("각 질문은 객체여야 합니다.")
        identifier = question.get("id")
        if (not isinstance(identifier, str)
                or not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", identifier)
                or identifier in identifiers):
            raise ValueError("질문 id는 중복 없는 snake_case여야 합니다.")
        identifiers.add(identifier)
        header = nonempty(question.get("header"), "header")
        if len(header) > 12:
            raise ValueError("header는 12자 이하여야 합니다.")
        body = nonempty(question.get("question"), "question")
        options = question.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 3:
            raise ValueError("각 질문의 선택지는 2~3개여야 합니다.")
        normalized, labels = [], set()
        for option in options:
            if not isinstance(option, dict):
                raise ValueError("선택지는 label/description 객체여야 합니다.")
            label = nonempty(option.get("label"), "label")
            if label in labels:
                raise ValueError("선택지 label은 중복될 수 없습니다.")
            labels.add(label)
            normalized.append({"label": label,
                               "description": nonempty(option.get("description"), "description")})
        result.append({"id": identifier, "header": header, "question": body,
                       "options": normalized})
    return {"phase": phase, "questions": result}


def pending_input(value):
    normalized = questions_input(value)
    identifier = value.get("question_set_id")
    if value.get("version") != 1 or not isinstance(identifier, str):
        raise ValueError("pending 질문 버전 또는 식별자가 유효하지 않습니다.")
    try:
        uuid.UUID(identifier)
    except ValueError as exc:
        raise ValueError("pending 질문 식별자가 유효하지 않습니다.") from exc
    return {"version": 1, "question_set_id": identifier, **normalized}


def view(pending, status="pending"):
    questions = pending["questions"]
    visible = []
    for question in questions:
        visible.append(f"{question['header']}: {question['question']}")
        visible.extend(f"- {option['label']} — {option['description']}"
                       for option in question["options"])
    return {**pending, "status": status,
            "sync_payload": {"questions": questions},
            "async_payload": {"questions": [
                {"title": question["question"], "options": [
                    option['label'] for option in question["options"]]} for question in questions]},
            "visible_question": "\n".join(visible),
            "limitations": "실제 도구 스키마·용도와 사용자 응답 여부는 호출자가 확인합니다."}


def register(directory, value):
    normalized = questions_input(value)
    path = directory / PENDING
    if path.exists():
        pending = pending_input(read_json(path))
        if {key: pending[key] for key in ("phase", "questions")} != normalized:
            raise ValueError("미응답 질문을 다른 질문 또는 phase로 덮어쓸 수 없습니다.")
    else:
        pending = {"version": 1, "question_set_id": str(uuid.uuid4()), **normalized}
        atomic_json(path, pending)
    return view(pending)


def normalize_answers(value, questions, question_set_id):
    # 등록 ack, default/selected만 있는 응답, 부분 응답을 답변으로 추측하지 않는다.
    if not isinstance(value, dict) or set(value) != {"answers", "question_set_id"}:
        raise ValueError("실제 응답을 question_set_id와 answers 객체로 정규화해야 합니다.")
    if value["question_set_id"] != question_set_id:
        raise ValueError("이 질문세트의 question_set_id를 실제 답변과 함께 전달해야 합니다.")
    answers = value["answers"]
    if not isinstance(answers, dict) or set(answers) != {q["id"] for q in questions}:
        raise ValueError("모든 pending 질문 id에 대한 실제 답변이 필요합니다.")
    normalized = {}
    for key, answer in answers.items():
        if not isinstance(answer, dict) or set(answer) != {"answers"}:
            raise ValueError("각 답변은 answers 문자열 목록이어야 합니다.")
        values = answer["answers"]
        if not isinstance(values, list) or not values:
            raise ValueError("빈 답변은 질문을 해제하지 않습니다.")
        normalized[key] = {"answers": [nonempty(item, "답변") for item in values]}
    return {"answers": normalized}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def render_decision(pending, response):
    path = Path(__file__).resolve().parents[1] / ".claude/hooks/capture_decision.py"
    spec = importlib.util.spec_from_file_location("gx_question_capture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render({"tool_input": {"questions": pending["questions"]},
                          "tool_response": response})


def answer(directory, value):
    path = directory / PENDING
    if not path.exists():
        receipt = read_json(directory / RECEIPT)
        pending = pending_input(receipt["question"])
        response = normalize_answers(value, pending["questions"], pending["question_set_id"])
        marker = f"<!-- gx-question:{pending['question_set_id']}:{digest(response)} -->"
        if (receipt.get("answer_digest") != digest(response)
                or marker not in (directory / "decisions.md").read_text(encoding="utf-8")):
            raise ValueError("완료된 질문의 답변과 다른 재시도입니다.")
        return {"status": "answered", "phase": pending["phase"], "repeated": True}
    pending = pending_input(read_json(path))
    response = normalize_answers(value, pending["questions"], pending["question_set_id"])
    answer_digest = digest(response)
    prefix = f"<!-- gx-question:{pending['question_set_id']}:"
    marker = prefix + answer_digest + " -->"
    decisions = directory / "decisions.md"
    text = decisions.read_text(encoding="utf-8") if decisions.exists() else HEADER
    if prefix in text and marker not in text:
        raise ValueError("이미 기록한 답변과 다릅니다. pending 상태를 먼저 복구하세요.")
    repeated = marker in text
    if not repeated:
        atomic_text(decisions, text + "\n" + marker + "\n" + render_decision(pending, response))
    atomic_json(directory / RECEIPT, {"question": pending, "answer_digest": answer_digest})
    path.unlink()
    return {"status": "answered", "phase": pending["phase"], "repeated": repeated,
            "answer_provenance": "caller_normalized; user_event_not_verified"}


def run(command, cwd, dev_dir, value=None):
    directory = workspace(cwd, dev_dir)
    if command == "status":
        path = directory / PENDING
        if (directory / ".question-lock").exists():
            raise ValueError("질문 상태 변경 중입니다. 잠금이 남았다면 작업 상태를 확인하세요.")
        if not path.exists():
            return {"status": "clear"}, 0
        return view(pending_input(read_json(path))), 2
    with locked(directory):
        return (register(directory, value) if command == "register"
                else answer(directory, value)), 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("register", "answer", "status"))
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--dev-dir", required=True)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        if args.command != "status" and args.input is None:
            raise ValueError("register/answer는 --input JSON 파일이 필요합니다.")
        value = read_json(args.input) if args.input else None
        result, code = run(args.command, args.cwd, args.dev_dir, value)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result, code = {"status": "blocked", "error": str(exc)}, 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
