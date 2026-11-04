#!/usr/bin/env python3
"""gx-work의 상태/계획 계약. 입력을 읽고 stdout JSON만 반환한다."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import sys
import uuid


INTENTS = ("understand", "plan", "implement", "status", "resume")
ENDPOINTS = ("understand", "plan", "verify", "commit", "pr")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def state_fields(path):
    fields = dict(re.findall(r"^([a-z][a-z-]*):[ \t]*([^\r\n]*)", path.read_text(encoding="utf-8"), re.M))
    return {key: value.strip().strip('\"\'') for key, value in fields.items()}


def active_state(project_root):
    """현재 state를 읽고, SVN 활성 포인터가 없고 후보가 여럿이면 선택만 요청한다."""
    root = Path(project_root).resolve()
    if not (root / ".dev").resolve().is_relative_to(root):
        raise ValueError("작업 디렉터리가 프로젝트 밖을 가리킵니다")
    config = root / ".claude" / "config.json"
    try:
        settings = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
    except (OSError, ValueError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    if settings.get("vcs") == "svn":
        active = root / ".dev" / ".active"
        slug = active.read_text(encoding="utf-8").strip() if active.exists() else ""
        if not slug:
            candidates = []
            for path in sorted((root / ".dev").glob("*/state.md")):
                if not path.resolve().is_relative_to((root / ".dev").resolve()):
                    raise ValueError("활성 작업 경로가 .dev 밖을 가리킵니다")
                if state_fields(path).get("status") == "in_progress":
                    candidates.append(str(path.resolve()))
            questions = []
            for path in sorted((root / ".dev").glob("*/pending-question.json")):
                if not path.resolve().is_relative_to(root):
                    raise ValueError("질문 기록이 프로젝트 밖을 가리킵니다")
                questions.append(str(path.resolve()))
            directories = sorted({str(Path(path).parent) for path in candidates + questions})
            if len(directories) > 1:
                return {"resume-candidates": candidates, "pending-candidates": questions,
                        "work-candidates": directories}, None
            if candidates:
                path = Path(candidates[0])
                return state_fields(path), str(path)
            if questions:
                return {"work-directory": str(Path(questions[0]).parent)}, None
        slug = slug or "trunk"
    else:
        result = subprocess.run(["git", "branch", "--show-current"], cwd=root,
                                capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0 or not result.stdout.strip():
            return {}, None
        slug = result.stdout.strip().replace("/", "-")
    directory = (root / ".dev" / slug).resolve()
    if not directory.is_relative_to(root) or not directory.is_relative_to((root / ".dev").resolve()):
        raise ValueError("활성 작업 경로가 .dev 밖을 가리킵니다")
    path = directory / "state.md"
    if not path.exists():
        return {"work-directory": str(directory)}, None
    if not path.resolve().is_relative_to(root):
        raise ValueError("실행 상태가 프로젝트 밖을 가리킵니다")
    return state_fields(path), str(path)


def route(project_root, intent, stop_at=None, goal=""):
    if intent not in INTENTS or (stop_at is not None and stop_at not in ENDPOINTS):
        raise ValueError("알 수 없는 intent 또는 stop-at")
    if intent in ("implement", "resume") and stop_at in ("understand", "plan"):
        raise ValueError("읽기 전용 종료점은 understand 또는 plan intent로 요청하세요")
    default = {"understand": "understand", "plan": "plan", "status": None}.get(intent, "verify")
    if intent in ("understand", "plan", "status") and stop_at not in (None, default):
        raise ValueError("읽기 전용 intent와 stop-at가 충돌합니다")
    state, state_file = active_state(project_root)
    directory = Path(state_file).parent if state_file else Path(state["work-directory"]) if state.get("work-directory") else None
    pending = directory / "pending-question.json" if directory else None
    if intent in ("implement", "resume") and pending and pending.exists():
        if not pending.resolve().is_relative_to(Path(project_root).resolve()):
            raise ValueError("질문 기록이 프로젝트 밖을 가리킵니다")
        question = json.loads(pending.read_text(encoding="utf-8"))
        if not isinstance(question, dict):
            raise ValueError("질문 기록 형식 오류")
        return {"action": "awaiting-decision", "skill": None, "read-only": True,
                "requested-goal": goal,
                "pending-question-file": str(pending), "state-file": state_file,
                "run-id": state.get("run-id"), "goal": state.get("goal", goal),
                "stop-at": state.get("stop-at", stop_at or default),
                "phase": question.get("phase"), "requires-user-decision": True}
    if intent in ("implement", "resume") and (state.get("resume-candidates") or state.get("work-candidates")):
        return {
            "action": "resume-selection-required", "skill": None if state.get("pending-candidates") else "oh-my-gx:gx-tdd", "skill-args": "--resume",
            "read-only": True, "goal": goal, "stop-at": None, "requested-stop-at": stop_at,
            "run-id": None, "state-file": None, "candidate-state-files": state["resume-candidates"],
            "candidate-pending-files": state.get("pending-candidates", []),
            "candidate-work-directories": state.get("work-candidates", []), "requires-user-decision": True,
            "existing-pipeline": None, "phase": None,
        }
    active = state.get("status") == "in_progress"
    action = intent
    if intent in ("implement", "resume"):
        action = "resume" if active else ("no-active-run" if intent == "resume" else "implement")
        if active and state.get("pipeline") != "gx-tdd":
            if state.get("pipeline") == "gx-ralph":
                locked = Path(state_file).with_name("ralph.lock").exists()
                action = "loop-active" if locked else "loop-resume-required"
            else:
                action = "migration-required"
        if active and stop_at and state.get("stop-at") and stop_at != state["stop-at"]:
            raise ValueError("기존 stop-at 변경은 사용자 명시 결정 후 state에 먼저 반영하세요")
        if (active and state.get("pipeline") == "gx-tdd" and intent == "implement"
                and goal and goal != state.get("goal", state.get("args", ""))):
            action = "scope-review-required"
    restore = active and intent in ("implement", "resume")
    return {
        "action": action,
        "skill": "oh-my-gx:gx-tdd" if action == "resume" else None,
        "requires-user-decision": action in ("implement", "scope-review-required"),
        "requested-goal": goal,
        "read-only": action not in ("implement", "resume"),
        "goal": state.get("goal", state.get("args", goal)) if restore else goal,
        "stop-at": state.get("stop-at", stop_at or default) if restore else (stop_at or default),
        "run-id": state.get("run-id") if restore else None,
        "state-file": state_file,
        "existing-pipeline": state.get("pipeline"),
        "phase": state.get("phase"),
    }


def validate_plan(value):
    """부족·충돌만 반환한다. 외부 계획을 수정하거나 승인 상태를 추론하지 않는다."""
    issues = []

    def issue(path, message, kind="missing"):
        issues.append({"kind": kind, "path": path, "message": message})

    def required_text(obj, key, prefix=""):
        if not text(obj.get(key)):
            issue(prefix + key, "비어 있지 않은 문자열이 필요합니다")

    def strings(obj, key, prefix="", nonempty=False):
        items = obj.get(key)
        if not isinstance(items, list) or (nonempty and not items) or (isinstance(items, list) and any(not text(x) for x in items)):
            issue(prefix + key, "문자열 목록이 필요합니다")

    if not isinstance(value, dict):
        return [{"kind": "missing", "path": "$", "message": "계획 JSON 객체가 필요합니다"}]
    if type(value.get("schema-version")) is not int or value["schema-version"] != 1:
        issue("schema-version", "지원하는 스키마 버전은 1입니다")
    required_text(value, "goal")
    units = value.get("units")
    if not isinstance(units, list) or not units:
        issue("units", "하나 이상의 작업 단위가 필요합니다")
        units = []
    unit_ids, ac_ids, dependencies = set(), set(), {}
    for number, unit in enumerate(units):
        prefix = f"units[{number}]."
        if not isinstance(unit, dict):
            issue(prefix.rstrip("."), "작업 단위 객체가 필요합니다")
            continue
        for key in ("id", "spec"):
            required_text(unit, key, prefix)
        identifier = unit.get("id")
        if text(identifier):
            if identifier in unit_ids:
                issue(prefix + "id", "작업 ID 중복", "conflict")
            unit_ids.add(identifier)
        for key in ("constraints", "files", "consumes", "produces", "review-focus"):
            strings(unit, key, prefix, nonempty=key in ("files", "review-focus"))
        if isinstance(unit.get("files"), list):
            for index, file in enumerate(unit["files"]):
                if not text(file):
                    continue
                windows = PureWindowsPath(file)
                if (PurePosixPath(file).is_absolute() or windows.drive or windows.root
                        or ".." in file.replace("\\", "/").split("/") or "\x00" in file):
                    issue(f"{prefix}files[{index}]", "프로젝트 안의 상대경로만 허용합니다", "scope")
        tests = unit.get("test")
        if not isinstance(tests, dict):
            issue(prefix + "test", "테스트 의도·경계·명령이 필요합니다")
        else:
            for key in ("intent", "boundary", "command"):
                required_text(tests, key, prefix + "test.")
        criteria = unit.get("ac")
        if not isinstance(criteria, list) or not criteria:
            issue(prefix + "ac", "Given-When-Then AC 목록이 필요합니다")
            criteria = []
        for index, criterion in enumerate(criteria):
            ac_prefix = f"{prefix}ac[{index}]."
            if not isinstance(criterion, dict):
                issue(ac_prefix.rstrip("."), "AC 객체가 필요합니다")
                continue
            for key in ("id", "given", "when", "then"):
                required_text(criterion, key, ac_prefix)
            ac_id = criterion.get("id")
            if text(ac_id):
                if ac_id in ac_ids:
                    issue(ac_prefix + "id", "AC ID 중복", "conflict")
                ac_ids.add(ac_id)
        if "depends-on" in unit:
            strings(unit, "depends-on", prefix)
        if text(identifier):
            deps = unit.get("depends-on", [])
            dependencies[identifier] = deps if isinstance(deps, list) and all(text(x) for x in deps) else []
    for identifier, deps in dependencies.items():
        for dep in deps:
            if dep not in unit_ids:
                issue(f"units.{identifier}.depends-on", f"존재하지 않는 입력 단위: {dep}", "conflict")
    visited, visiting = set(), set()
    for identifier in dependencies:
        if identifier in visited:
            continue
        visiting.add(identifier)
        stack = [(identifier, iter(dependencies.get(identifier, [])))]
        while stack:
            current, remaining = stack[-1]
            dep = next(remaining, None)
            if dep is None:
                stack.pop()
                visiting.remove(current)
                visited.add(current)
            elif dep in visiting:
                issue("units.depends-on", f"작업 의존성 순환: {dep}", "conflict")
            elif dep not in visited:
                visiting.add(dep)
                stack.append((dep, iter(dependencies.get(dep, []))))
    decisions = value.get("decisions", [])
    if not isinstance(decisions, list):
        issue("decisions", "결정 목록이 필요합니다")
        decisions = []
    known = {}
    for index, decision in enumerate(decisions):
        prefix = f"decisions[{index}]."
        if not isinstance(decision, dict):
            issue(prefix.rstrip("."), "결정 객체가 필요합니다")
            continue
        for key in ("topic", "value", "source", "status"):
            required_text(decision, key, prefix)
        topic, selected = decision.get("topic"), decision.get("value")
        if text(topic) and text(selected):
            if topic in known and known[topic] != selected:
                issue(prefix + "value", f"같은 결정의 값이 충돌합니다: {topic}", "conflict")
            known[topic] = selected
        if decision.get("status") not in ("explicit", "inferred", "unresolved"):
            issue(prefix + "status", "explicit/inferred/unresolved 중 하나가 필요합니다")
        if decision.get("status") == "unresolved":
            issue(prefix + "status", "구현 전 결정이 필요합니다", "unresolved")
    unresolved = value.get("unresolved", [])
    if not isinstance(unresolved, list):
        issue("unresolved", "미해결 사항 목록이 필요합니다")
    else:
        for index, item in enumerate(unresolved):
            if not isinstance(item, dict) or type(item.get("blocking")) is not bool:
                issue(f"unresolved[{index}]", "blocking 불리언이 필요합니다")
            elif item["blocking"]:
                issue(f"unresolved[{index}]", str(item.get("topic", "미해결 사항")), "unresolved")
    return issues


def scope_digest(value, path, kind, root, run_id, stop_at):
    scope = {"input": value, "file": str(path), "kind": kind, "project-root": str(root),
             "run-id": run_id, "stop-at": stop_at}
    return hashlib.sha256(json.dumps(scope, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def local_file(root, value):
    path = Path(value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("인계 입력은 현재 프로젝트 안의 파일이어야 합니다")
    return path


def handoff(plan_path=None, stop_at="verify", run_id=None, approval_source=None, *,
            request_path=None, project_root=None, entry_approval_source=None, question_set_id=None):
    if stop_at not in ENDPOINTS:
        raise ValueError("알 수 없는 stop-at")
    if (plan_path is None) == (request_path is None):
        raise ValueError("plan 또는 request 파일 하나만 지정하세요")
    path = Path(plan_path if plan_path is not None else request_path).resolve()
    root = Path(project_root).resolve() if project_root is not None else None
    if root is not None:
        if not root.is_dir():
            raise ValueError("유효한 프로젝트 디렉터리가 필요합니다")
        path = local_file(root, path)
    value = json.loads(path.read_text(encoding="utf-8"))
    kind = "plan" if plan_path is not None else "request"
    issues = validate_plan(value) if kind == "plan" else []
    if not isinstance(value, dict) or not text(value.get("goal")):
        raise ValueError("사용자 목표가 있는 요청 객체가 필요합니다")
    for key in ("sources", "decisions", "unresolved", "requirements", "context-paths", "observed-facts", "questions"):
        if not isinstance(value.get(key, []), list):
            raise ValueError(f"{key}는 목록이어야 합니다")
    if value.get("work-id") is not None and (not isinstance(value["work-id"], str) or not re.fullmatch(r"W\d{2}", value["work-id"])):
        raise ValueError("work-id 형식 오류")
    if issues:
        raise ValueError(json.dumps({"issues": issues}, ensure_ascii=False))
    if approval_source is not None and not text(approval_source):
        raise ValueError("실제 사용자 승인 근거가 필요합니다")
    if entry_approval_source is not None and not text(entry_approval_source):
        raise ValueError("실제 TDD 진입 응답 근거가 필요합니다")
    if question_set_id is not None and not text(question_set_id):
        raise ValueError("실제 질문 식별자가 필요합니다")
    if entry_approval_source and (root is None or not text(run_id)):
        raise ValueError("진입 응답을 결박할 project-root와 현재 run-id가 필요합니다")
    if run_id is not None and not text(run_id):
        raise ValueError("비어 있지 않은 run-id가 필요합니다")
    identifier = run_id or (value.get("run-id") if stop_at in ("understand", "plan") else None) or str(uuid.uuid4())
    fingerprint = scope_digest(value, path, kind, root, identifier, stop_at)
    readonly = stop_at in ("understand", "plan")
    ready = bool(entry_approval_source and root)
    entry_fingerprint = hashlib.sha256(json.dumps(
        {"scope": fingerprint, "request-source": approval_source or entry_approval_source,
         "source": entry_approval_source, "question-set-id": question_set_id},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    result = {
        "schema-version": 1, "origin": "gx-work", "handoff-kind": kind, "run-id": identifier,
        "project-root": str(root) if root else None, "input-sha256": fingerprint,
        "goal": value["goal"], "intent": stop_at if stop_at in ("understand", "plan") else "implement",
        "stop-at": stop_at, "plan-file": str(path) if kind == "plan" else None,
        "request-file": str(path) if kind == "request" else None, "work-id": value.get("work-id"),
        "approval": {"status": "approved" if approval_source or entry_approval_source else "unconfirmed",
                     "source": approval_source or entry_approval_source},
        "entry-approval": {"status": "approved" if ready else "unconfirmed", "source": entry_approval_source,
                           "question-set-id": question_set_id, "scope-sha256": entry_fingerprint if ready else None},
        "ready-for-tdd": ready, "read-only": readonly, "execution-authorized": ready and not readonly,
    }
    for key in ("sources", "decisions", "unresolved", "requirements", "context-paths", "observed-facts", "questions"):
        result[key] = value.get(key, [])
    return result


def validate_handoff(handoff_path, project_root):
    """인계를 재검사한다. 응답 source가 실제 사용자 사건인지는 하네스가 확인한다."""
    try:
        root = Path(project_root).resolve()
        data = json.loads(local_file(root, handoff_path).read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or type(data.get("schema-version")) is not int
                or data["schema-version"] != 1 or data.get("origin") != "gx-work"):
            raise ValueError("gx-work 인계 형식 오류")
        if data.get("project-root") != str(root) or not text(data.get("run-id")):
            raise ValueError("현재 프로젝트·실행 ID와 인계가 다릅니다")
        kind = data.get("handoff-kind")
        if kind not in ("plan", "request"):
            raise ValueError("지원하지 않는 인계 종류")
        pointer = "plan-file" if kind == "plan" else "request-file"
        other = "request-file" if kind == "plan" else "plan-file"
        if not text(data.get(pointer)) or data.get(other) is not None:
            raise ValueError("원문 포인터가 없거나 충돌합니다")
        entry = data.get("entry-approval")
        approval = data.get("approval")
        if not isinstance(entry, dict) or not isinstance(approval, dict):
            raise ValueError("TDD 진입 응답이 없습니다")
        expected = handoff(**{"plan_path" if kind == "plan" else "request_path": data[pointer]},
                           stop_at=data.get("stop-at"), run_id=data["run-id"], project_root=root,
                           approval_source=approval.get("source"), entry_approval_source=entry.get("source"),
                           question_set_id=entry.get("question-set-id"))
        for key in ("input-sha256", "goal", "intent", "ready-for-tdd", "read-only", "execution-authorized", "work-id", "sources", "decisions", "unresolved",
                    "requirements", "context-paths", "observed-facts", "questions", "entry-approval", "approval"):
            if data.get(key) != expected.get(key):
                raise ValueError(f"승인한 요청·실행·종료점 또는 인계가 바뀌었습니다: {key}")
        if not expected["ready-for-tdd"]:
            raise ValueError("관련 결과와 다음 단계를 제시하고 실제 TDD 진입 응답을 기다리세요")
        return {"ready-for-tdd": True, "run-id": data["run-id"], "stop-at": data["stop-at"],
                "handoff-kind": kind, "plan-file": data.get("plan-file"), "request-file": data.get("request-file"),
                "read-only": expected["read-only"], "execution-authorized": expected["execution-authorized"],
                "intent": expected["intent"]}
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        return {"ready-for-tdd": False, "error": str(error)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    routing = commands.add_parser("route")
    routing.add_argument("--project-root", required=True)
    routing.add_argument("--intent", choices=INTENTS, required=True)
    routing.add_argument("--stop-at", choices=ENDPOINTS)
    routing.add_argument("--goal", default="")
    validation = commands.add_parser("validate-plan")
    validation.add_argument("--plan", required=True)
    transfer = commands.add_parser("handoff")
    inputs = transfer.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--plan")
    inputs.add_argument("--request")
    transfer.add_argument("--project-root")
    transfer.add_argument("--stop-at", choices=ENDPOINTS, default="verify")
    transfer.add_argument("--run-id")
    transfer.add_argument("--approval-source")
    transfer.add_argument("--entry-approval-source")
    transfer.add_argument("--question-set-id")
    recheck = commands.add_parser("validate-handoff")
    recheck.add_argument("--handoff", required=True)
    recheck.add_argument("--project-root", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "route":
            result = route(args.project_root, args.intent, args.stop_at, args.goal)
        elif args.command == "validate-plan":
            issues = validate_plan(json.loads(Path(args.plan).read_text(encoding="utf-8")))
            result = {"valid": not issues, "issues": issues, "approval": "unconfirmed"}
        elif args.command == "validate-handoff":
            result = validate_handoff(args.handoff, args.project_root)
        else:
            result = handoff(args.plan, args.stop_at, args.run_id, args.approval_source,
                             request_path=args.request, project_root=args.project_root,
                             entry_approval_source=args.entry_approval_source, question_set_id=args.question_set_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if (args.command == "validate-plan" and issues) or (args.command == "validate-handoff" and not result["ready-for-tdd"]) else 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
