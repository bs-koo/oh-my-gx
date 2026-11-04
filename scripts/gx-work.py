#!/usr/bin/env python3
"""gx-work의 상태/계획 계약. 입력을 읽고 stdout JSON만 반환한다."""

import argparse
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
            if len(candidates) > 1:
                return {"resume-candidates": candidates}, None
            if candidates:
                path = Path(candidates[0])
                return state_fields(path), str(path)
        slug = slug or "trunk"
    else:
        result = subprocess.run(["git", "branch", "--show-current"], cwd=root,
                                capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0 or not result.stdout.strip():
            return {}, None
        slug = result.stdout.strip().replace("/", "-")
    directory = (root / ".dev" / slug).resolve()
    if not directory.is_relative_to((root / ".dev").resolve()):
        raise ValueError("활성 작업 경로가 .dev 밖을 가리킵니다")
    path = directory / "state.md"
    if not path.exists():
        return {}, None
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
    if intent in ("implement", "resume") and state.get("resume-candidates"):
        return {
            "action": "resume-selection-required", "skill": "oh-my-gx:gx-tdd", "skill-args": "--resume",
            "read-only": True, "goal": goal, "stop-at": None, "requested-stop-at": stop_at,
            "run-id": None, "state-file": None, "candidate-state-files": state["resume-candidates"],
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
    restore = active and intent in ("implement", "resume")
    return {
        "action": action,
        "skill": "oh-my-gx:gx-tdd" if action in ("implement", "resume") else None,
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


def handoff(plan_path, stop_at="verify", run_id=None, approval_source=None):
    if stop_at not in ENDPOINTS:
        raise ValueError("알 수 없는 stop-at")
    path = Path(plan_path).resolve()
    value = json.loads(path.read_text(encoding="utf-8"))
    issues = validate_plan(value)
    if issues:
        raise ValueError(json.dumps({"issues": issues}, ensure_ascii=False))
    if approval_source is not None and not text(approval_source):
        raise ValueError("실제 사용자 승인 근거가 필요합니다")
    result = {
        "schema-version": 1, "run-id": run_id or (value.get("run-id") if stop_at in ("understand", "plan") else None) or str(uuid.uuid4()),
        "goal": value["goal"], "intent": stop_at if stop_at in ("understand", "plan") else "implement",
        "stop-at": stop_at, "plan-file": str(path),
        "approval": {"status": "approved" if approval_source else "unconfirmed", "source": approval_source},
    }
    for key in ("sources", "decisions", "unresolved", "requirements", "context-paths", "observed-facts", "questions"):
        result[key] = value.get(key, [])
    return result


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
    transfer.add_argument("--plan", required=True)
    transfer.add_argument("--stop-at", choices=ENDPOINTS, default="verify")
    transfer.add_argument("--run-id")
    transfer.add_argument("--approval-source")
    args = parser.parse_args(argv)
    try:
        if args.command == "route":
            result = route(args.project_root, args.intent, args.stop_at, args.goal)
        elif args.command == "validate-plan":
            issues = validate_plan(json.loads(Path(args.plan).read_text(encoding="utf-8")))
            result = {"valid": not issues, "issues": issues, "approval": "unconfirmed"}
        else:
            result = handoff(args.plan, args.stop_at, args.run_id, args.approval_source)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.command == "validate-plan" and issues else 0
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
