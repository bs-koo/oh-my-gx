#!/usr/bin/env python3
"""개발 전후 관련 문서와 업무 계획을 로컬에서 읽어 차이·연결·구조를 점검한다.

쓰기, 명세 도출, 승인, 테스트 실행, 완료 판정은 수행하지 않는다.
snapshot 일치는 관련 자료의 재사용 힌트이며 의미적 정합성의 증명이 아니다.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import re
import sys


LIMIT = 20
REF = re.compile(r"N?FR-(?:0|[1-9][0-9]*)\Z")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def local(root, value):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("비어 있거나 잘못된 프로젝트 경로입니다")
    candidate = Path(value)
    if (not candidate.is_absolute() and PureWindowsPath(value).drive) or ".." in candidate.parts:
        raise ValueError(f"프로젝트 밖 경로는 사용할 수 없습니다: {value}")
    candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"프로젝트 밖 경로를 가리킵니다: {value}")
    return candidate


def relative(root, path):
    # resolve한 별칭 대신 저장소의 원래 이름을 보존해 변경 위치를 보여준다.
    return Path(path).relative_to(root).as_posix()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parser_module():
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("gx_document_plan", Path(__file__).with_name("plan.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = previous


def domain(value):
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or value in (".", "..", "공통", "통합") or any(c in value for c in "/\\:\x00")):
        raise ValueError(f"명시적인 원장 도메인이 필요합니다: {value}")
    return value


def qualified(root, groups):
    if not isinstance(groups, list):
        raise ValueError("requirements는 도메인과 ID 목록이어야 합니다")
    result = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("requirements 항목 형식 오류")
        name = domain(group.get("domain"))
        if group.get("path") is not None:
            supplied = local(root, group["path"])
            if supplied != local(root, f"context/{name}/status.md"):
                raise ValueError("requirements.path는 해당 도메인의 status.md여야 합니다")
        ids = group.get("ids", [])
        if not isinstance(ids, list) or any(not isinstance(item, str) or not REF.fullmatch(item) for item in ids):
            raise ValueError("요구사항 ID 형식 오류 (선행 0 별칭은 허용하지 않습니다)")
        result.update((name, item) for item in ids)
    return result


def validate_previous(root, previous, run_id, work_id):
    if previous is None:
        return None
    value = read_json(local(root, str(previous)))
    if isinstance(value, dict) and "snapshot" in value:
        value = value["snapshot"]
    if (not isinstance(value, dict) or value.get("schema-version") != 1
            or value.get("project-root") != str(root) or value.get("run-id") != run_id
            or value.get("work-id") not in (None, work_id)):
        raise ValueError("snapshot의 프로젝트·실행·작업이 현재 요청과 다릅니다")
    for field in ("files", "requirements"):
        items = value.get(field)
        if not isinstance(items, dict):
            raise ValueError(f"snapshot {field} 형식 오류")
        for key, sha in items.items():
            if not isinstance(key, str) or (sha is not None and
                    (not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha))):
                raise ValueError("snapshot 해시 형식 오류")
            if field == "files":
                local(root, key)
            else:
                name, separator, identifier = key.rpartition(":")
                if not separator or not REF.fullmatch(identifier):
                    raise ValueError("snapshot 요구사항 키 형식 오류")
                domain(name)
    for field in ("input-digest", "global-digest"):
        if not isinstance(value.get(field), str) or not re.fullmatch(r"[a-f0-9]{64}", value[field]):
            raise ValueError("snapshot 지문 형식 오류")
    return value


def state_fields(path):
    return {key: value.strip().strip("\"'") for key, value in
            re.findall(r"^([a-z][a-z-]*):[ \t]*([^\r\n]*)", path.read_text(encoding="utf-8"), re.M)}


def summarize(report):
    """완전한 점검 기록은 파일에 두고 모델에는 현재 판단에 필요한 부분만 전달한다."""
    if not isinstance(report, dict):
        raise ValueError("문서 점검 보고서 형식 오류")
    keys = ("schema-version", "phase", "run-id", "work-id", "action", "ready-for-tdd",
            "document-write-allowed", "work", "next-work-id", "structural-errors", "global-summary", "input-error")
    result = {key: report[key] for key in keys if key in report}
    result["goal"] = str(report.get("goal", ""))[:400]
    result["requirements"] = [
        {key: (str(item[key])[:500] if key in ("text", "ac") else item[key])
         for key in ("domain", "id", "text", "ac", "status", "pr", "path") if key in item}
        for item in report.get("requirements", [])[:LIMIT]]
    result["relevant-documents"] = [{"path": item["path"], "reason": item["reason"]}
                                    for item in report.get("relevant-documents", [])[:LIMIT]]
    for key in ("changed-paths", "changed-requirements", "blockers", "notices", "candidate-work-ids"):
        result[key] = report.get(key, [])[:LIMIT]
    result["omitted-counts"] = {key: max(0, len(report.get(key, [])) - LIMIT) for key in
                                ("requirements", "relevant-documents", "changed-paths", "changed-requirements")}
    result["limits"] = ["요약에 생략된 현재 작업 자료는 원본 보고서에서 필요한 항목만 확인합니다",
                        "snapshot·원문 전체를 모델 입력에 반복 포함하지 않습니다"]
    return result


def inspect(project_root, plan_path, run_id, *, phase="pre", work_id=None, previous=None,
            intent="implement", no_document_write=False, branch=None, request_data=None):
    root = Path(project_root).resolve()
    if not root.is_dir() or not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("프로젝트 디렉터리와 비어 있지 않은 run-id가 필요합니다")
    if phase not in ("pre", "post") or intent not in ("implement", "resume", "understand", "plan", "status"):
        raise ValueError("phase 또는 intent 형식 오류")
    parser = parser_module()
    if work_id is not None and (not isinstance(work_id, str) or not parser.ID_RE.match(work_id)):
        raise ValueError(f"work-id는 W와 두 자리 이상 ASCII 숫자여야 합니다 (예: W01, W118): {work_id!r}")
    if branch is not None and (not isinstance(branch, str) or not branch.strip() or "\n" in branch or "\r" in branch):
        raise ValueError("실제 branch/slug 값이 필요합니다")
    if request_data is None:
        plan_path = local(root, str(plan_path))
        request = read_json(plan_path)
    else:
        if plan_path not in (None, "-"):
            raise ValueError("request_data와 계획 파일을 동시에 지정할 수 없습니다")
        plan_path, request = None, request_data
    if not isinstance(request, dict) or not isinstance(request.get("goal"), str) or not request["goal"].strip():
        raise ValueError("요청 근거를 가진 goal이 필요합니다")
    units = request.get("units", [])
    if not isinstance(units, list) or any(not isinstance(unit, dict) for unit in units):
        raise ValueError("units는 작업 객체 목록이어야 합니다")
    requested = qualified(root, request.get("requirements", []))
    old = validate_previous(root, previous, run_id, work_id)
    errors, notices, rows, ledger = [], [], [], []
    docs = {}

    def add(value, reason):
        target = local(root, str(value))
        original = Path(value)
        original = original if original.is_absolute() else root / original
        key = relative(root, original)
        if target.exists() and not target.is_file():
            raise ValueError(f"파일 경로가 필요합니다: {value}")
        sha = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        docs.setdefault(key, {"path": key, "sha256": sha, "reason": reason})
        return target

    if plan_path is not None:
        add(plan_path, "request")
    for name in ("AGENTS.md", "CLAUDE.md", ".claude/config.json", "context/README.md", "context/glossary.md"):
        add(name, "shared-policy")
    rules = local(root, ".claude/rules")
    if rules.is_dir():
        for path in sorted(rules.glob("*.md")):
            add(path, "shared-policy")
    for unit in units:
        paths = unit.get("files", [])
        if not isinstance(paths, list):
            raise ValueError("unit.files는 프로젝트 파일 경로 목록이어야 합니다")
        for path in paths:
            add(path, "implementation-scope")
    for field in ("sources", "context-paths"):
        pointers = request.get(field, [])
        if not isinstance(pointers, list) or any(not isinstance(item, dict) for item in pointers):
            raise ValueError(f"{field}는 파일 포인터 목록이어야 합니다")
        for pointer in pointers:
            if pointer.get("path") is not None:
                add(pointer["path"], field)

    context = local(root, "context")
    if context.is_dir():
        for path in sorted(context.glob("*/status.md")):
            safe = local(root, str(path))
            try:
                items = parser.parse_table(safe.read_text(encoding="utf-8"), parser.LEDGER_HEADER, allow_empty=True)
                for item in items:
                    if not REF.fullmatch(item["ID"]):
                        errors.append(f"원장 ID 형식 오류: {path.parent.name}:{item['ID']}")
                    ledger.append({"domain": path.parent.name, "id": item["ID"], "text": item["요구사항"],
                                   "status": item["상태"], "ac": item["AC"], "pr": item["PR"],
                                   "path": relative(root, path)})
            except (ValueError, OSError) as exc:
                errors.append(f"{relative(root, path)}: {exc}")
    work_plan = add(".dev/plan.md", "work-registry")
    if work_plan.is_file():
        try:
            rows = parser.parse_table(work_plan.read_text(encoding="utf-8"), parser.HEADER, allow_empty=True)
        except (ValueError, OSError) as exc:
            errors.append(f".dev/plan.md: {exc}")
    # 원장에 없는 거대 범위가 확장되기 전에 차단한다. W 원장의 크기와 별도로 제한한다.
    for row in rows:
        for token in re.split(r"[,·]", row["요구사항"]):
            raw = token.strip().split(":")[-1]
            for part in re.findall(r"N?FR-(\d+)", raw):
                if len(part) > 1 and part.startswith("0"):
                    errors.append(f"{row['ID']}: 요구사항 선행 0 별칭은 허용하지 않습니다")
            match = re.search(r"(\d+)[~～](?:N?FR-)?(\d+)", raw)
            if match and any(len(part) > 1 and part.startswith("0") for part in match.groups()):
                errors.append(f"{row['ID']}: 요구사항 선행 0 별칭은 허용하지 않습니다")
            if match and int(match[2]) - int(match[1]) > max(len(ledger), 10000):
                errors.append(f"{row['ID']}: 원장에 비해 과도한 요구사항 범위입니다")
    analysis = {}
    if not errors:
        analysis = parser.analyze(rows, ledger)
        for error in analysis["errors"]:
            if not work_plan.is_file() and error.startswith("미배정 요구사항:"):
                notices.append(error)
            else:
                errors.append(error)
    selected = next((row for row in rows if row["ID"] == work_id), None)
    row_refs = set()
    if selected and not errors:
        row_refs = set(parser.requirement_refs(selected, {item["domain"] for item in ledger}))
    if requested and row_refs and not requested.issubset(row_refs):
        errors.append("선택한 작업에 이번 요청의 요구사항이 모두 연결되어 있지 않습니다")
    scope = requested | row_refs
    index = {(item["domain"], item["id"]): item for item in ledger}
    related = [index[key] for key in sorted(scope) if key in index]
    for name, _ in sorted(scope):
        domain(name)
        for filename in ("README.md", "status.md", "architecture.md", "glossary.md", "PROJECTS.md"):
            add(f"context/{name}/{filename}", "related-domain")

    blockers = []
    if any(item["status"] == "🚫" for item in related):
        blockers.append("폐기된 요구사항은 구현할 수 없습니다. 명시적인 요구사항 결정이 필요합니다")
    if work_id and selected is None:
        blockers.append("지정한 작업 행이 없습니다. 임의 생성하거나 다른 작업으로 바꾸지 않습니다")
    if selected:
        if selected["상태"] in ("완료", "폐기"):
            blockers.append("완료·폐기 작업은 자동 재개하지 않습니다. 새 작업 또는 명시 전환이 필요합니다")
        if selected["작업 위치"] not in ("", "-") and branch and selected["작업 위치"] != branch:
            blockers.append("다른 브랜치/실행 위치에 배정된 작업입니다")
        dependencies = [item.strip() for item in re.split(r"[,·]", selected["의존"]) if item.strip() not in ("", "-")]
        states = {row["ID"]: row["상태"] for row in rows}
        if any(states.get(item) != "완료" for item in dependencies):
            blockers.append("미완료 선행 작업이 있습니다")
    for path in sorted(local(root, ".dev").glob("*/state.md")):
        safe = local(root, str(path))
        state = state_fields(safe)
        same_directory = bool(branch and path.parent.name == branch.replace("/", "-"))
        # 같은 slug는 W/run이 달라도 덮어쓸 수 없다. 완료된 과거 실행도 명시 인계가 필요하다.
        if same_directory and state.get("branch") not in (None, branch):
            blockers.append("현재 브랜치 slug에 다른 브랜치 state가 있습니다. 기존 실행을 덮어쓰지 않습니다")
        if state.get("status") == "in_progress" and (same_directory or (branch and state.get("branch") == branch)):
            if work_id and state.get("work-id") not in (None, "", "-", work_id):
                blockers.append("기존 실행의 작업 연결이 다릅니다. 명시적인 작업 전환 전에 state를 덮어쓰지 않습니다")
        if state.get("status") == "in_progress" and (
                (work_id is not None and state.get("work-id") == work_id)
                or (branch and state.get("branch") == branch) or same_directory):
            if state.get("run-id") != run_id or (branch and state.get("branch") not in (None, branch)):
                blockers.append("다른 진행 중 run/브랜치가 선택 작업을 사용하고 있습니다")
    # W99 다음은 W100이다. 폐기·완료 행을 포함한 최댓값 다음 번호를 쓰고 기존 ID를 재사용하지 않는다.
    numbers = [int(row["ID"][1:]) for row in rows if parser.ID_RE.match(row["ID"])]
    next_work = f"W{max(numbers, default=0) + 1:02d}"
    registered = bool(selected and row_refs and scope.issubset(index))
    file_hashes = {key: value["sha256"] for key, value in sorted(docs.items())}
    req_hashes = {f"{item['domain']}:{item['id']}": digest(item) for item in related}
    input_hash = digest({"request": request, "work-id": work_id, "branch": branch, "intent": intent,
                         "no-document-write": bool(no_document_write)})
    snapshot = {"schema-version": 1, "project-root": str(root), "run-id": run_id, "work-id": work_id,
                "input-digest": input_hash, "files": file_hashes, "requirements": req_hashes,
                "global-digest": digest({"rows": rows, "ledger": ledger})}
    changed = sorted(path for path in set(file_hashes) | set(old["files"] if old else {})
                     if not old or file_hashes.get(path) != old["files"].get(path))
    changed_refs = sorted(key for key in set(req_hashes) | set(old["requirements"] if old else {})
                          if not old or req_hashes.get(key) != old["requirements"].get(key))
    readonly = no_document_write or intent in ("understand", "plan", "status")
    ready = registered and not errors and not blockers
    if readonly:
        action = "report-only"
    elif errors or blockers:
        action = "repair-required"
    elif not registered:
        action = "register-required"
    elif old and old["input-digest"] == input_hash and not changed and not changed_refs:
        action = "reuse"
    else:
        action = "review-required"
    candidates = []
    if requested and not errors:
        for row in rows:
            if row["상태"] in ("대기", "진행") and requested.issubset(
                    set(parser.requirement_refs(row, {item["domain"] for item in ledger}))):
                candidates.append(row["ID"])
    return {"schema-version": 1, "phase": phase, "run-id": run_id, "goal": request["goal"],
            "work-id": work_id, "action": action, "ready-for-tdd": bool(ready),
            "document-write-allowed": not readonly, "work": selected, "next-work-id": next_work,
            "candidate-work-ids": candidates,
            "requirements": related, "relevant-documents": list(docs.values()),
            "structural-errors": {"count": len(errors), "items": errors[:LIMIT]},
            "blockers": blockers[:LIMIT], "notices": notices[:LIMIT],
            "global-summary": {"work-count": len(rows), "requirement-count": len(ledger)},
            "changed-paths": changed, "changed-requirements": changed_refs,
            "snapshot": snapshot,
            "limits": ["해시는 의미적 정합성·승인·AC 통과를 증명하지 않습니다",
                       "완료 FR의 기존 상태·PR은 이번 작업의 완료 근거가 아닙니다"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("inspect")
    command.add_argument("--project-root", required=True, type=Path)
    command.add_argument("--plan", required=True, help="프로젝트 계획 파일 또는 stdin JSON(-)")
    command.add_argument("--run-id", required=True)
    command.add_argument("--phase", choices=("pre", "post"), default="pre")
    command.add_argument("--work")
    command.add_argument("--previous", type=Path)
    command.add_argument("--intent", choices=("implement", "resume", "understand", "plan", "status"), default="implement")
    command.add_argument("--branch")
    command.add_argument("--no-document-write", action="store_true")
    summary = commands.add_parser("summary")
    summary.add_argument("--report", required=True, help="점검 보고서 또는 stdin JSON(-)")
    args = parser.parse_args()
    try:
        if args.command == "summary":
            result = summarize(json.load(sys.stdin) if args.report == "-" else read_json(args.report))
            code = 0
        else:
            result = inspect(args.project_root, args.plan, args.run_id, phase=args.phase, work_id=args.work,
                             previous=args.previous, intent=args.intent, branch=args.branch,
                             no_document_write=args.no_document_write,
                             request_data=json.load(sys.stdin) if args.plan == "-" else None)
            code = 1 if result["structural-errors"]["count"] else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {"action": "repair-required", "ready-for-tdd": False, "input-error": str(exc)}
        code = 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return code


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    raise SystemExit(main())
