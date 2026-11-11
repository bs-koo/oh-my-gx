#!/usr/bin/env python3
"""gx-work의 상태/계획 계약. 입력을 읽고 stdout JSON만 반환한다.

명령: route, validate-plan, handoff, validate-handoff, reissue, cancel.
오류는 모두 stdout JSON({"error": ..., "issues"?: [...]})과 exit 2다. cancel만 state.md·decisions.md를 쓰고 나머지는 파일을 쓰지 않는다.
"""

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import sys
import tempfile
import uuid


INTENTS = ("understand", "plan", "implement", "status", "resume")
ENDPOINTS = ("understand", "plan", "verify", "commit", "pr")
EXECUTION_ENDPOINTS = ("verify", "commit", "pr")
EXECUTION_METHODS = ("session", "subagents")
MODEL_PROFILES = ("standard", "eco")
MODES = ("all", "core")
LIST_FIELDS = ("sources", "decisions", "unresolved", "requirements", "context-paths", "observed-facts", "questions")
# 작업 ID: W + 두 자리 이상 ASCII 숫자. 하이픈은 이슈 키 패턴과 겹쳐 쓰지 않는다.
WORK_ID = re.compile(r"W[0-9]{2,}")
WORK_ID_RULE = "W + 두 자리 이상 ASCII 숫자(예: W01, W118)"
# run-id는 gx-work 실행 입력 디렉토리 .dev/<run-id>/의 이름으로도 쓴다.
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}")
RUN_ID_RULE = "[A-Za-z0-9][A-Za-z0-9._-]{2,79} (영문·숫자로 시작, 3~80자)"
# .dev/.active 첫 줄 해석은 .claude/hooks/capture_decision.py와 같다.
ACTIVE_SLUG = re.compile(r"[A-Za-z0-9._-]+")
ENTRY_QUESTION_ID = "gx_work_tdd_entry"
ENTRY_PROCEED = "gx-tdd로 진행"
# Codex는 한 호출에 질문 3개까지라 진입 질문을 나누면 둘째 세트(모드·프로파일)를 이 id로 묻는다.
# 값: 답 선택지 label → 요청 파일 필드 값. 알 수 없는 label(직접 입력)은 그대로 돌려준다.
FOLLOWUP_QUESTIONS = {
    "gx_work_mode": ("mode", {"전체": "all", "핵심": "core", "all": "all", "core": "core"}),
    "gx_work_model_profile": ("model-profile", {"표준": "standard", "에코": "eco",
                                                "standard": "standard", "eco": "eco"}),
}
# config workflowDefaults 키 → (route defaults 키, 허용값). 최상위 modelProfile은 configured-model-profile로 따로 싣는다.
WORKFLOW_DEFAULTS = {"stopAt": ("stop-at", EXECUTION_ENDPOINTS), "mode": ("mode", MODES),
                     "modelProfile": ("model-profile", MODEL_PROFILES),
                     "executionMethod": ("execution-method", EXECUTION_METHODS)}
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
# 결정 충돌을 차단으로 보는 impact. gx-context scripts/intake.py의 CONSEQUENTIAL과 같다.
CONSEQUENTIAL = {"scope", "behavior", "architecture", "acceptance", "removal"}
NEW_SCOPE = ("기존 기록·질문·잠금은 그대로 두고 새 범위로 시작하세요. git: 미커밋 변경이 없으면 베이스 브랜치로 돌아가고, "
             "미커밋 변경이 있으면 그 변경이 따라오지 않도록 새 워크트리가 필요합니다. 동의하면 gx-work가 "
             "`git worktree add <경로> -b <새 브랜치> <베이스>`로 직접 만들고 경로와 다음 명령을 알려 줍니다. 그 위치에서 "
             "`/oh-my-gx:gx-work <새 목표>`로 "
             "새 브랜치·새 run-id·새 진입 질문을 씁니다. SVN: 새 목표를 `--slug <새 slug>`로 시작합니다. 이 검사는 그 slug의 "
             "기록에만 적용되고 setup이 `.dev/.active`를 새 slug로 바꿉니다. 같은 브랜치·slug에서 전환을 다시 요청하면 같은 "
             "판정으로 돌아옵니다. 구버전 PRD·AC·커밋은 근거 문서로만 연결합니다.")

RALPH_TOKEN = re.compile(
    r"(?<![\w-])(?:--ralph|/?(?:oh-my-gx:)?gx-ralph(?:-iterate)?)(?![A-Za-z0-9_-])"
    r"|랄프로|ralph로|무인\s*루프로"
    r"|(?:^|(?<=랄프)|(?<=ralph)|(?<=무인))\s*루프\s*돌려", re.I)
NEGATED = re.compile(r"(?:(?:실행|사용|개발|구현|진행)?\s*하지|쓰지|돌리지)\s*(?:말|않)|말고|없이|빼고|제외")
DESCRIBED = re.compile(r"(?:(?:실행|사용|개발|구현|진행)\s*)?(?:하던|했던|돌리던|돌던|쓰던|썼던)")
_NOUNS = (r"(?:(?:옵션|플래그|스킬|문구|설명|문서|지원(?:\s*여부)?|파일|기록|상태|잠금|lock|흔적|잔재|참조|코드"
          r"|관련(?:\s*(?:내용|코드|문서))?|사용법|동작|방식)\s*)*")
_PARTICLES = r"(?:을|를|은|는|이|가|의|에\s*대해서?|에\s*관해서?)?\s*"
MANAGED = re.compile(_NOUNS + _PARTICLES + r"(?:제거|삭제|폐지|설명|수정|정리|지워|지우|없애|빼|알려|확인|조회|찾|검색"
                     r"|검토|분석|보여|읽|뭐|무엇|왜|어떻게|어디|언제|무슨|어떤)", re.I)
TRANSITION = re.compile(_NOUNS + _PARTICLES + r"(?:전환|이관|마이그레이션|옮기|옮겨)", re.I)


class InputError(ValueError):
    """사용자에게 그대로 보여줄 입력·상태 오류. issues는 JSON 출력에 함께 싣는다."""

    def __init__(self, message, issues=None):
        super().__init__(message)
        self.issues = issues or []


class JsonArgumentParser(argparse.ArgumentParser):
    """인자 오류도 stdout JSON(exit 2)으로 돌려주도록 예외로 바꾼다."""

    def error(self, message):
        raise InputError(f"인자 오류: {message}. 사용법: {' '.join(self.format_usage().split())}")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def shown(value):
    rendered = repr(value) if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return rendered if len(rendered) <= 120 else rendered[:117] + "..."


def field_error(field, value, expected, where=""):
    location = f" ({where})" if where else ""
    return InputError(f"{field} 값 {shown(value)}이(가) 올바르지 않습니다{location}. 기대: {expected}")


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def read_text(path, label):
    """UTF-8(BOM 허용)만 읽는다. UTF-16 등은 추측하지 않고 다시 저장하도록 알린다."""
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in data:
        raise InputError(f"{label}이(가) UTF-16 등 UTF-8이 아닌 인코딩입니다: {path}. BOM 없는 UTF-8로 다시 저장하세요")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InputError(f"{label}을(를) UTF-8로 읽을 수 없습니다: {path} ({error.start}바이트). "
                         "BOM 없는 UTF-8로 저장하세요") from error


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"JSON 중복 키 {key!r}")
        result[key] = value
    return result


def read_json(path, label):
    try:
        return json.loads(read_text(path, label), object_pairs_hook=_unique_pairs)
    except RecursionError as error:
        raise InputError(f"{label} JSON 중첩이 너무 깊습니다: {path}") from error
    except InputError as error:
        if str(error).startswith("JSON 중복 키"):
            raise InputError(f"{label}에 {error}가 있습니다: {path}. 같은 키는 한 번만 씁니다") from error
        raise
    except json.JSONDecodeError as error:
        raise InputError(f"{label} JSON 구문 오류: {path} ({error.lineno}행 {error.colno}열, {error.msg})") from error


def same_path(first, second):
    try:
        return os.path.samefile(first, second)
    except OSError:
        return os.path.normcase(str(first)) == os.path.normcase(str(second))


def retired_ralph_request(value):
    """명시 실행만 보수적으로 막는다. 경로·파일명·부정·설명·관리·전환 문맥은 실행 요청으로 보지 않는다."""
    if not isinstance(value, str):
        return False
    for clause in re.split(r"[;,\n]|그리고|하고\s*", value):
        for match in RALPH_TOKEN.finditer(clause):
            word = match.group(0).strip()
            before, after = clause[:match.start()], clause[match.end():]
            # 경로·파일명의 일부(scripts/gx-ralph.sh, skills/gx-ralph-iterate/)는 실행 명령이 아니다.
            if before[-1:] in ("/", "\\", ".") or after[:1] in ("/", "\\") or re.match(r"\.\w", after):
                continue
            tail = after.lstrip(" `\"'")
            # 구버전'에서' 다른 방식으로 옮기는 문맥은 실행이 아니다.
            if re.match(r"(?:에서|으로부터|부터)", tail):
                continue
            direction = re.match(r"(?:으로|로)(?:는|도|만)?(?=[\s`\"'.,!?]|$)", tail)
            toward = word.endswith("로") or bool(direction)
            tail = tail[direction.end():].lstrip() if direction else re.sub(r"^(?:는|은|도|만)(?=\s|$)\s*", "", tail)
            if NEGATED.match(tail) or DESCRIBED.match(tail) or MANAGED.match(tail):
                continue
            # '랄프로 전환'은 Ralph로 바꾸는 실행이고, 방향 없는 전환·이관은 기존 실행을 옮기는 관리다.
            if not toward and TRANSITION.match(tail):
                continue
            return True
    return False


def scalar(raw):
    """YAML 한 줄 스칼라: 따옴표를 풀고 따옴표 밖의 ` #` 주석을 지운다."""
    raw = raw.strip()
    if raw.startswith('"'):
        match = re.match(r'"((?:[^"\\]|\\.)*)"', raw)
        if match:
            try:
                return json.loads(match.group(0))
            except ValueError:
                return match.group(1)
    if raw.startswith("'"):
        match = re.match(r"'((?:[^']|'')*)'", raw)
        if match:
            return match.group(1).replace("''", "'")
    return re.split(r"[ \t]#", raw, maxsplit=1)[0].strip()


STATE_KEY = re.compile(r"([a-z][a-z0-9-]*):[ \t]*(.*)$")


def _state_block(lines, fenced):
    """최상위 `키: 값` 줄을 읽는다. 구분선 안(fenced)이면 닫는 줄까지, 아니면 키가 아닌 첫 줄까지."""
    fields, lists, current = {}, {}, None
    for line in lines:
        stripped = line.strip()
        if stripped in ("---", "...") or (fenced and stripped.startswith("```")):
            break
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            item = re.match(r"-[ \t]*(.*)$", stripped)
            if current and item:
                lists[current].append(scalar(item.group(1)))
            else:
                current = None
            continue
        match = STATE_KEY.match(line)
        if not match:
            if fenced:
                current = None
                continue
            break
        key, raw = match.groups()
        current = None
        if key in fields or key in lists:
            continue
        if raw.strip():
            fields[key] = scalar(raw)
        else:
            lists[key], current = [], key
    for key, items in lists.items():
        fields[key] = "[" + ", ".join(items) + "]" if items else ""
    return fields


def state_fields(path):
    """state.md 첫 상태 블록의 최상위 키만 읽는다.

    앞쪽 빈 줄·`#` 제목을 건너뛰고, 여는 구분선(`---` 또는 ```yaml 펜스)이 있으면 닫는 줄까지 읽는다.
    들여쓴 하위 블록(phases·steps·execution-log)은 무시하고 같은 키가 다시 나오면 처음 값을 쓴다.
    블록 목록(flags:\\n  - --ralph)은 "[a, b]"로 합친다. 그 블록에서 `pipeline`·`status`를 못 찾으면
    (본문 뒤에 상태를 적은 형식 등) 훅처럼 파일 전체의 최상위 `키: 값` 줄을 처음 값으로 읽는다.
    """
    lines = read_text(path, "state.md").splitlines()
    index = 0
    while index < len(lines) and (not lines[index].strip() or lines[index].lstrip().startswith("#")):
        index += 1
    fenced = index < len(lines) and (lines[index].strip() == "---" or lines[index].strip().startswith("```"))
    fields = _state_block(lines[index + 1:] if fenced else lines[index:], fenced)
    if "pipeline" not in fields and "status" not in fields:
        fallback = {}
        for line in lines:
            match = STATE_KEY.match(line)
            if match and match.group(1) not in fallback and match.group(2).strip():
                fallback[match.group(1)] = scalar(match.group(2))
        fields = {**fallback, **fields}
    return fields


def load_settings(root):
    config = root / ".claude" / "config.json"
    try:
        settings = json.loads(read_text(config, "config.json")) if config.is_file() else {}
    except (OSError, ValueError):
        settings = {}
    return settings if isinstance(settings, dict) else {}


def detect_projects(root, types):
    """verify가 쓰는 scripts/gx-test-plan.py discover를 그대로 불러 같은 기준으로 프로젝트 타입을 감지한다."""
    spec = importlib.util.spec_from_file_location("gx_work_test_plan", Path(__file__).with_name("gx-test-plan.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.discover(root, types)


def setup_issue(root):
    """새 실행 전 설정 누락. gx-tdd phase-setup의 config 가드(파일 존재·JSON 객체)와 프로젝트 타입 감지
    (gx-test-plan.py discover: 이름 패턴은 파일 이름, `/`가 든 패턴은 저장소 상대경로로 비교)를 따른다.
    문제 없으면 None."""
    config = root / ".claude" / "config.json"
    if not config.is_file():
        return "config-missing", ".claude/config.json이 없습니다"
    try:
        settings = json.loads(read_text(config, "config.json"))
    except (OSError, ValueError):
        settings = None
    if not isinstance(settings, dict):
        return "config-invalid", ".claude/config.json이 손상되었습니다(JSON 객체가 아님)"
    types = settings.get("projectTypes")
    detail = "projectTypes가 비어 있음"
    if isinstance(types, dict) and types:
        try:
            detect_projects(root, types)
            return None
        except (OSError, ValueError, TypeError, AttributeError) as error:
            detail = str(error) or type(error).__name__
    return "project-type-unregistered", f"이 프로젝트에 맞는 projectTypes(detect 감지 파일)가 등록되어 있지 않습니다({detail})"


def workflow_defaults(settings):
    """config workflowDefaults 중 허용값만 route defaults(질문 생략 근거)로 싣고, 무시한 값은 notices로 알린다.

    최상위 modelProfile은 템플릿 기본값이 들어 있어 사용자 선택으로 보지 않는다. 추천·현재 설정 표시용으로만
    따로 돌려준다(허용값이 아니면 None과 notice).
    """
    defaults, notices = {}, []
    configured = settings.get("workflowDefaults", {})
    if not isinstance(configured, dict):
        notices.append(f"config workflowDefaults {shown(configured)}은(는) 객체가 아니라 무시합니다")
        configured = {}
    entries = [(f"workflowDefaults.{key}", configured.get(key), *WORKFLOW_DEFAULTS[key]) for key in WORKFLOW_DEFAULTS]
    entries.append(("modelProfile", settings.get("modelProfile"), "configured-model-profile", MODEL_PROFILES))
    for label, value, field, allowed in entries:
        if value in (None, ""):
            continue
        if value in allowed:
            defaults[field] = value
        else:
            notices.append(f"config {label} 값 {shown(value)}은(는) 허용값({'|'.join(allowed)})이 아니라 무시합니다")
    return defaults, defaults.pop("configured-model-profile", None), notices


def plugin_version(directory):
    try:
        data = json.loads((directory / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    match = SEMVER.fullmatch(version) if isinstance(version, str) else None
    return tuple(int(part) for part in match.groups()) if match else None


def update_notices(plugin_root=None):
    """플러그인 캐시(<상위>/<semver>/)에서 로드된 판보다 높은 판이 형제 디렉토리로 설치돼 있으면 안내한다.

    로드된 루트 이름이 semver가 아니면(개발 체크아웃 등 캐시 형식이 아님) 조용히 넘어간다.
    """
    root = Path(plugin_root) if plugin_root is not None else Path(__file__).resolve().parents[1]
    try:
        current = plugin_version(root)
        if current is None or not SEMVER.fullmatch(root.name):
            return []
        newest = current
        for sibling in root.parent.iterdir():
            if sibling.name != root.name and SEMVER.fullmatch(sibling.name) and sibling.is_dir():
                version = plugin_version(sibling)
                newest = max(newest, version) if version else newest
    except OSError:
        return []
    if newest == current:
        return []
    return [f"새 판 {'.'.join(map(str, newest))}가 설치되어 있습니다. Claude Code는 /reload-plugins, Codex는 새 세션으로 "
            f"다시 시작하세요(현재 로드된 판 {'.'.join(map(str, current))})"]


def git(root, safe_directory, *args):
    """git을 실행한다. 소유권 예외는 확인된 프로젝트 경로 하나에만 명령별 -c로 준다."""
    command = ["git"] + (["-c", f"safe.directory={safe_directory}"] if safe_directory else []) + list(args)
    # 'not a git repository' 판별이 번역 메시지에 흔들리지 않도록 메시지 언어를 고정한다.
    environment = {**os.environ, "LC_ALL": "C", "LANGUAGE": "C"}
    return subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=environment)


def git_failure(result, action):
    detail = (result.stderr or result.stdout or "").strip().splitlines()
    first = detail[0] if detail else f"exit {result.returncode}"
    return InputError(f"git {action} 실패: {first}. 상태 없음으로 추측하지 않고 멈춥니다. Codex 샌드박스의 소유권 "
                      "불일치(dubious ownership)라면 확인된 프로젝트 경로로 --git-safe-directory <프로젝트 루트>를 지정하세요")


def svn_root(start):
    """가장 가까운 .svn 작업 사본 루트. svn 명령이 되면 wc-root를 우선한다."""
    marker = next((parent for parent in (start, *start.parents) if (parent / ".svn").is_dir()), None)
    if marker is None:
        return None
    try:
        result = subprocess.run(["svn", "info", "--non-interactive", "--show-item", "wc-root"], cwd=start,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return marker


def project_layout(project_root, git_safe_directory=None):
    """gx-tdd와 같은 규칙으로 루트·VCS를 정한다: config vcs > git toplevel > SVN wc-root > 입력 경로."""
    requested = Path(project_root).resolve()
    if not requested.is_dir():
        raise field_error("project-root", str(project_root), "존재하는 프로젝트 디렉터리")
    safe = None
    if git_safe_directory is not None:
        if not same_path(Path(git_safe_directory).resolve(), requested):
            raise field_error("git-safe-directory", str(git_safe_directory),
                              f"확인된 project-root와 같은 경로({requested})")
        safe = requested.as_posix()
    layout = {"requested": requested, "root": requested, "vcs": None, "safe": safe}
    if load_settings(requested).get("vcs") == "svn":
        return {**layout, "root": svn_root(requested) or requested, "vcs": "svn"}
    try:
        result = git(requested, safe, "rev-parse", "--show-toplevel")
    except FileNotFoundError:
        result = None
    if result is not None and result.returncode == 0 and result.stdout.strip():
        return {**layout, "root": Path(result.stdout.strip()).resolve(), "vcs": "git"}
    if result is not None and "not a git repository" not in (result.stderr or "").lower():
        raise git_failure(result, "저장소 확인(rev-parse --show-toplevel)")
    root = svn_root(requested)
    return {**layout, "root": root, "vcs": "svn"} if root is not None else layout


def active_pointer(root):
    """capture_decision.py와 같게 첫 줄만 slug로 본다. 비었으면 None, 안전하지 않으면 trunk."""
    path = root / ".dev" / ".active"
    if not path.is_file():
        return None
    lines = read_text(path, ".dev/.active").splitlines()
    first = lines[0] if lines else ""
    if not first.strip():
        return None
    if ACTIVE_SLUG.fullmatch(first) and first != "." and ".." not in first and not first.endswith("."):
        return first
    return "trunk"


def safe_slug(value):
    return isinstance(value, str) and bool(ACTIVE_SLUG.fullmatch(value)) and value != "." \
        and ".." not in value and not value.endswith(".")


def active_state(layout, slug=None):
    """현재 state를 읽고, SVN 활성 포인터가 없고 후보가 여럿이면 선택만 요청한다.

    SVN에서 slug를 명시하면 .dev/.active와 후보 탐색을 쓰지 않고 그 slug의 기록만 검사한다.
    """
    root = layout["root"]
    if not (root / ".dev").resolve().is_relative_to(root):
        raise InputError("작업 디렉터리(.dev)가 프로젝트 밖을 가리킵니다")
    if slug is not None and layout["vcs"] != "svn":
        raise InputError("--slug는 SVN 작업 사본에서만 씁니다. git은 현재 브랜치가 작업 디렉터리를 정합니다")
    if layout["vcs"] == "svn":
        slug = slug or active_pointer(root)
        if not slug:
            candidates = []
            for path in sorted((root / ".dev").glob("*/state.md")):
                if not path.resolve().is_relative_to((root / ".dev").resolve()):
                    raise InputError("활성 작업 경로가 .dev 밖을 가리킵니다")
                if state_fields(path).get("status") == "in_progress":
                    candidates.append(str(path.resolve()))
            questions = []
            for path in sorted((root / ".dev").glob("*/pending-question.json")):
                if not path.resolve().is_relative_to(root):
                    raise InputError("질문 기록이 프로젝트 밖을 가리킵니다")
                questions.append(str(path.resolve()))
            locks = []
            for path in sorted((root / ".dev").glob("*/ralph.lock")):
                if not path.resolve().is_relative_to((root / ".dev").resolve()):
                    raise InputError("잠금 기록이 .dev 밖을 가리킵니다")
                locks.append(str(path.parent.resolve() / path.name))
            directories = sorted({str(Path(path).parent) for path in candidates + questions + locks})
            if len(directories) > 1:
                return {"resume-candidates": candidates, "pending-candidates": questions,
                        "lock-candidates": locks, "work-candidates": directories}, None
            if candidates:
                path = Path(candidates[0])
                return state_fields(path), str(path)
            if questions:
                return {"work-directory": str(Path(questions[0]).parent)}, None
            if locks:
                return {"work-directory": str(Path(locks[0]).parent)}, None
        slug = slug or "trunk"
    elif layout["vcs"] == "git":
        result = git(root, layout["safe"], "branch", "--show-current")
        if result.returncode != 0:
            raise git_failure(result, "현재 브랜치 확인(branch --show-current)")
        branch = result.stdout.strip()
        if not branch:
            return {"detached-head": True}, None
        slug = branch.replace("/", "-")
    else:
        return {}, None
    directory = (root / ".dev" / slug).resolve()
    if not directory.is_relative_to(root) or not directory.is_relative_to((root / ".dev").resolve()):
        raise InputError("활성 작업 경로가 .dev 밖을 가리킵니다")
    path = directory / "state.md"
    if not path.exists():
        return {"work-directory": str(directory)}, None
    if not path.resolve().is_relative_to(root):
        raise InputError("실행 상태가 프로젝트 밖을 가리킵니다")
    return state_fields(path), str(path)


def elsewhere_candidates(layout, current):
    """현재 위치에 진행 중 실행이 없을 때 다른 slug·워크트리의 진행 중 gx-tdd 실행을 읽기만 해서 찾는다.

    이 체크아웃의 .dev/*/state.md와 `git worktree list --porcelain`의 각 워크트리 .dev/*/state.md를 본다.
    같은 run이 여러 곳에 있으면 그 브랜치가 체크아웃된 워크트리의 기록을 쓴다. git 실패는 이 체크아웃만 본다.
    git은 그 브랜치가 로컬 또는 원격 추적 ref(refs/remotes, 네트워크 조회 없음)에 있을 때만 후보로 낸다.
    머지 뒤 지워진 브랜치의 기록은 이어갈 곳이 없다. ref 조회가 실패하면 이 거르기를 하지 않는다.
    """
    root, worktrees, branches = layout["root"], [], None
    if layout["vcs"] == "git":
        result = git(root, layout["safe"], "worktree", "list", "--porcelain")
        for record in result.stdout.split("\n\n") if result.returncode == 0 else ():
            lines = record.splitlines()
            path = next((line[9:] for line in lines if line.startswith("worktree ")), None)
            branch = next((line[18:] for line in lines if line.startswith("branch refs/heads/")), None)
            if path and "bare" not in lines:
                worktrees.append((Path(path).resolve(), branch))
        refs = git(root, layout["safe"], "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes")
        if refs.returncode == 0:
            branches = {ref[11:] for ref in refs.stdout.splitlines() if ref.startswith("refs/heads/")}
            branches |= {ref.split("/", 3)[3] for ref in refs.stdout.splitlines()
                         if ref.startswith("refs/remotes/") and ref.count("/") >= 3}
    if not any(same_path(path, root) for path, _ in worktrees):
        worktrees.insert(0, (root, None))
    chosen = {}
    for worktree, branch in worktrees:
        for path in sorted((worktree / ".dev").glob("*/state.md")) if worktree.is_dir() else ():
            if current is not None and same_path(path.parent, current):
                continue
            try:
                fields = state_fields(path)
            except (OSError, ValueError):
                continue
            if fields.get("pipeline") != "gx-tdd" or fields.get("status") != "in_progress":
                continue
            own = branch is not None and branch.replace("/", "-") == path.parent.name
            name = fields.get("branch") or (branch if own else None)
            if branches is not None and name not in branches:
                continue
            checkout =next((place for place, held in worktrees if name and held == name), None)
            candidate = {"branch": name, "slug": path.parent.name, "worktree": str(checkout) if checkout else None,
                         "state-file": str(path.resolve()), "run-id": fields.get("run-id"),
                         "work-id": fields.get("work-id"), "goal": fields.get("goal", fields.get("args")),
                         "stop-at": fields.get("stop-at"), "phase": fields.get("phase"),
                         "current-step": fields.get("current-step")}
            key = fields.get("run-id") or candidate["state-file"]
            if key not in chosen or (own and not chosen[key][0]):
                chosen[key] = (own, candidate)
    return [candidate for _, candidate in chosen.values()]


def requested_here(candidate, goal):
    """새 구현 요청이 다른 위치의 진행 중 실행과 같은 일인지: 같은 목표 문장이거나 같은 W ID를 말한다."""
    if not text(goal):
        return False
    words = re.findall(r"(?<![A-Za-z0-9_-])W[0-9]{2,}(?![A-Za-z0-9_-])", goal)
    return candidate["goal"] == goal or (candidate["work-id"] is not None and candidate["work-id"] in words)


def question_file(path, label):
    value = read_json(path, label)
    if not isinstance(value, dict):
        raise InputError(f"{label} 형식 오류: JSON 객체가 아닙니다 ({path})")
    return value


def route(project_root, intent, stop_at=None, goal="", git_safe_directory=None, slug=None):
    if intent not in INTENTS:
        raise field_error("intent", intent, "|".join(INTENTS))
    if stop_at is not None and stop_at not in ENDPOINTS:
        raise field_error("stop-at", stop_at, "|".join(ENDPOINTS))
    if slug is not None and not safe_slug(slug):
        raise field_error("slug", slug, "영문·숫자·._- 조합(., .. 포함·마침표로 끝남 불가), setup이 정규화한 SVN 작업 slug")
    mutating = intent in ("implement", "resume")
    if mutating and stop_at in ("understand", "plan"):
        raise InputError(f"stop-at {stop_at!r}은 읽기 전용 종료점입니다. understand 또는 plan intent로 요청하세요")
    default = {"understand": "understand", "plan": "plan", "status": None}.get(intent, "verify")
    if not mutating and stop_at not in (None, default):
        expected = "생략" if default is None else f"생략 또는 {default}"
        raise InputError(f"읽기 전용 intent {intent!r}와 stop-at {stop_at!r}이(가) 충돌합니다. 기대: {expected}")
    layout = project_layout(project_root, git_safe_directory)
    root = layout["root"]
    state, state_file = active_state(layout, slug)
    defaults, configured_profile, notices = workflow_defaults(load_settings(root))
    base = {"requested-goal": goal, "requested-stop-at": stop_at, "project-root": str(root),
            "defaults": defaults, "configured-model-profile": configured_profile,
            "notices": update_notices() + notices}
    if not same_path(root, layout["requested"]):
        base["requested-project-root"] = str(layout["requested"])
    if slug is not None:
        base["requested-slug"] = slug
    if state.pop("detached-head", False):
        base["detached-head"] = True
    if base.get("detached-head") and mutating:
        return {**base, "action": "detached-head", "skill": None, "read-only": True,
                "requires-user-decision": False, "goal": goal, "stop-at": stop_at or default, "run-id": None,
                "state-file": None, "existing-pipeline": None, "phase": None,
                "reason": "브랜치가 없는 HEAD(detached)라 이어갈 작업을 정할 수 없습니다. 읽기 전용으로 보고만 하고 "
                          "체크아웃·브랜치 생성은 사용자가 정합니다."}
    directory = Path(state_file).parent if state_file else Path(state["work-directory"]) if state.get("work-directory") else None
    locked = bool(directory and (directory / "ralph.lock").exists())
    active = state.get("status") == "in_progress"
    pipeline = state.get("pipeline")
    retired_flags = bool(re.search(r"(?<![\w-])(?:--)?ralph(?![\w-])", state.get("flags", ""), re.I))
    retired = active and (pipeline == "gx-ralph" or retired_flags)
    legacy = active and not retired and pipeline != "gx-tdd"
    saved_goal = state.get("goal", state.get("args", goal))

    # 미응답 질문은 진행 중 gx-tdd 실행 또는 state 없는 작업의 것만 기다린다. 완료·구버전 실행의 질문은 알리기만 한다.
    pending = directory / "pending-question.json" if directory else None
    question, awaitable = {}, False
    if pending is not None and pending.exists():
        if not pending.resolve().is_relative_to(root):
            raise InputError("질문 기록이 프로젝트 밖을 가리킵니다")
        if state_file is None or (active and pipeline == "gx-tdd"):
            try:
                question = question_file(pending, "질문 기록(pending-question.json)")
            except InputError as error:
                if mutating:
                    raise InputError(f"{error}. 형식이 깨진 질문 기록은 실제 사용자 결정이 있을 때 codex-question.py discard "
                                     f"--dev-dir {pending.parent.relative_to(root).as_posix()} --reason \"<근거>\"로 "
                                     "원문을 보관한 뒤 해제할 수 있습니다") from error
            awaitable = True
            base.update({"pending-question-file": str(pending),
                         "pending-goal": question.get("goal") or (state.get("goal") if state_file else None),
                         "pending-run-id": question.get("run_id") or (state.get("run-id") if state_file else None),
                         "pending-phase": question.get("phase"),
                         "pending-question-set-id": question.get("question_set_id")})
        else:
            base["stale-pending-file"] = str(pending)
    # state 없는 작업에 같은 목표·run의 진입 질문 답변 영수증이 있으면 다시 묻지 않도록 알린다.
    # 진행으로 답했을 때만 결정이 끝난 것으로 보고, 완료된 run의 영수증은 오래된 기록으로만 알린다.
    proceed = False
    receipt_file = directory / "answered-question.json" if directory and state_file is None else None
    if receipt_file is not None and receipt_file.is_file() and not awaitable:
        try:
            record = question_file(receipt_file, "답변 영수증(answered-question.json)")
        except InputError:
            record = {}
        receipt = record.get("question")
        if isinstance(receipt, dict):
            receipt_run = receipt.get("run_id")
            if text(receipt_run) and completed_state(root, receipt_run):
                base["stale-answered-file"] = str(receipt_file)
            else:
                selection = entry_selection(record)
                base.update({"answered-question-file": str(receipt_file),
                             "answered-question-set-id": receipt.get("question_set_id"),
                             "answered-phase": receipt.get("phase"), "answered-goal": receipt.get("goal"),
                             "answered-run-id": receipt_run})
                if selection is not None:
                    base["answered-selection"] = selection
                # 분할 질문은 영수증이 마지막 세트로 바뀌어도 같은 run의 답을 run_answers에 누적한다.
                answers = run_answers(record)
                if text(goal) and receipt.get("goal") == goal and text(receipt_run) and ENTRY_QUESTION_ID in answers:
                    base["entry-answer-recorded"] = True
                    proceed = is_proceed(selection)
                    if proceed:
                        choices, missing = followup_answers(answers)
                        if choices:
                            base["answered-choices"] = choices
                        # 설정 기본값으로 정해진 항목은 둘째 세트에서 묻지 않으므로 빠진 답으로 보지 않는다.
                        missing = [item for item in missing if FOLLOWUP_QUESTIONS[item][0] not in defaults]
                        if missing:
                            base["entry-followup-missing"] = missing
                            proceed = False

    if mutating and (locked or retired or retired_ralph_request(goal)):
        action = "loop-active" if locked else "migration-required" if retired else "unsupported-request"
        reason = {
            "loop-active": "ralph.lock이 있어 새 실행을 시작하지 않습니다. 잠금·프로세스는 건드리지 않습니다. "
                           "러너 종료를 사용자가 확인한 뒤 " + NEW_SCOPE,
            "migration-required": "Ralph 지원이 중단되어 이 브랜치의 진행 중 무인 반복 실행은 자동 재개하지 않습니다. " + NEW_SCOPE,
            "unsupported-request": "Ralph(무인 반복) 실행은 지원이 중단되었습니다. 다른 실행으로 대체하지 않습니다. "
                                   "일반 TDD로 진행하려면 무인 반복 표현 없이 다시 요청하세요.",
        }[action]
        return {**base, "action": action, "skill": None, "read-only": True, "requires-user-decision": False,
                "reason": reason, "goal": saved_goal if active else goal,
                "stop-at": state.get("stop-at", stop_at or default) if active else (stop_at or default),
                "run-id": state.get("run-id") if active else None, "state-file": state_file,
                "existing-pipeline": pipeline, "phase": state.get("phase")}
    if mutating and legacy:
        return {**base, "action": "migration-required", "skill": None, "read-only": True,
                "requires-user-decision": False,
                "reason": f"진행 중 실행의 파이프라인({pipeline or '없음'})이 gx-tdd가 아니라 자동 재개하지 않습니다. " + NEW_SCOPE,
                "goal": saved_goal, "stop-at": state.get("stop-at", stop_at or default),
                "run-id": state.get("run-id"), "state-file": state_file, "existing-pipeline": pipeline,
                "phase": state.get("phase")}
    if mutating and awaitable:
        return {**base, "action": "awaiting-decision", "skill": None, "read-only": True,
                "state-file": state_file, "run-id": state.get("run-id"), "goal": state.get("goal", goal),
                "stop-at": state.get("stop-at", stop_at or default), "phase": question.get("phase"),
                "requires-user-decision": True, "existing-pipeline": pipeline}
    if mutating and active and "stop-at" in state and state["stop-at"] not in ENDPOINTS:
        raise field_error("stop-at", state["stop-at"], "|".join(ENDPOINTS), f"state.md {state_file}")
    if mutating and (state.get("resume-candidates") or state.get("work-candidates")):
        return {
            **base, "action": "resume-selection-required",
            "skill": None if state.get("pending-candidates") or state.get("lock-candidates") else "oh-my-gx:gx-tdd",
            "skill-args": "--resume", "read-only": True, "goal": goal, "stop-at": None,
            "run-id": None, "state-file": None, "candidate-state-files": state["resume-candidates"],
            "candidate-pending-files": state.get("pending-candidates", []),
            "candidate-lock-files": state.get("lock-candidates", []),
            "candidate-work-directories": state.get("work-candidates", []), "requires-user-decision": True,
            "existing-pipeline": None, "phase": None,
        }
    # 여기부터 현재 위치에 이어갈 실행이 없으면 새 실행(implement) 또는 no-active-run이다.
    if (mutating and not active and layout["vcs"] in ("git", "svn") and slug is None
            and not base.get("entry-answer-recorded")):
        # 재개 요청은 다른 브랜치·워크트리의 진행 중 실행을 모두, 새 구현은 같은 목표·W ID인 것만 보여준다.
        found = [item for item in elsewhere_candidates(layout, directory)
                 if intent == "resume" or requested_here(item, goal)]
        if found:
            setup = setup_issue(root)
            return {**base, "action": "resume-elsewhere", "skill": None, "read-only": True,
                    "requires-user-decision": True, "goal": goal, "stop-at": None, "run-id": None,
                    "state-file": state_file, "existing-pipeline": pipeline, "phase": state.get("phase"),
                    "elsewhere-candidates": found, "setup-reason": setup[0] if setup else None}
    setup = setup_issue(root) if mutating and not active and intent == "implement" else None
    if setup:
        return {**base, "action": "setup-required", "skill": None, "read-only": True,
                "requires-user-decision": False, "goal": goal, "stop-at": stop_at or default, "run-id": None,
                "state-file": state_file, "existing-pipeline": pipeline, "phase": state.get("phase"),
                "setup-reason": setup[0],
                "reason": f"{setup[1]}. 진입 질문 전에 멈춥니다. /oh-my-gx:gx-setup으로 설정과 프로젝트 타입을 "
                          "등록한 뒤 같은 요청을 다시 하세요."}
    action, endpoint_change = intent, False
    if mutating:
        action = "resume" if active else ("no-active-run" if intent == "resume" else "implement")
        # 목표가 다르면 종료점보다 범위 검토가 먼저다. 같은 실행의 종료점 변경은 결정으로 알리고 넓히지 않는다.
        if active and intent == "implement" and goal and goal != state.get("goal", state.get("args", "")):
            action = "scope-review-required"
        elif active and stop_at and state.get("stop-at") and stop_at != state["stop-at"]:
            endpoint_change = True
    restore = active and mutating
    result = {
        **base,
        "action": action,
        "skill": "oh-my-gx:gx-tdd" if action == "resume" else None,
        "requires-user-decision": action in ("implement", "scope-review-required") and not proceed,
        "read-only": action not in ("implement", "resume"),
        "goal": saved_goal if restore else goal,
        "stop-at": state.get("stop-at", stop_at or default) if restore else (stop_at or default),
        "run-id": state.get("run-id") if restore else None,
        "state-file": state_file,
        "existing-pipeline": pipeline,
        "phase": state.get("phase"),
    }
    if endpoint_change:
        result["stop-at-change-required"] = True
    return result


def shared_field_issues(value):
    """요청·계획 공통 필드 형식. validate-plan과 handoff가 같은 규칙을 쓴다."""
    issues = []
    for key in LIST_FIELDS:
        if key in value and not isinstance(value[key], list):
            issues.append({"kind": "format", "path": key, "message": f"목록이 필요합니다 (현재 값 {shown(value[key])})"})
    rules = (("work-id", lambda item: isinstance(item, str) and WORK_ID.fullmatch(item), WORK_ID_RULE),
             ("execution-method", lambda item: item in EXECUTION_METHODS, "|".join(EXECUTION_METHODS)),
             ("model-profile", lambda item: item in MODEL_PROFILES, "|".join(MODEL_PROFILES)),
             ("mode", lambda item: item in MODES, "|".join(MODES)))
    for key, valid, expected in rules:
        if value.get(key) is not None and not valid(value[key]):
            issues.append({"kind": "format", "path": key,
                           "message": f"{key} 값 {shown(value[key])}이(가) 올바르지 않습니다. 기대: {expected}"})
    return issues


def request_blocking_issues(value):
    """요청 인계의 차단 항목: blocking 미정과 차단 impact의 근거 있는 explicit 결정 충돌.

    gx-context intake.py와 같은 기준이다. metadata 충돌, unresolved 상태 결정, 위임 추론과의 차이는
    차단하지 않는다(그런 미정은 unresolved 목록이 정한다).
    """
    issues, grounded = [], {}
    decisions = value.get("decisions", [])
    for index, decision in enumerate(decisions if isinstance(decisions, list) else []):
        if not isinstance(decision, dict):
            issues.append({"kind": "format", "path": f"decisions[{index}]", "message": "결정 객체가 필요합니다"})
            continue
        if (decision.get("status") == "explicit" and text(decision.get("topic")) and decision.get("source")
                and decision.get("value") not in (None, "", "❓")):
            grounded.setdefault(decision["topic"], []).append((index, decision))
    for topic, answers in grounded.items():
        first = answers[0][1]["value"]
        differing = [index for index, decision in answers if decision["value"] != first]
        if differing and any(decision.get("impact", "metadata") in CONSEQUENTIAL for _, decision in answers):
            issues.append({"kind": "conflict", "path": f"decisions[{differing[0]}].value",
                           "message": f"같은 결정의 explicit 값이 충돌합니다: {topic}"})
    unresolved = value.get("unresolved", [])
    for index, item in enumerate(unresolved if isinstance(unresolved, list) else []):
        if not isinstance(item, dict) or type(item.get("blocking")) is not bool:
            issues.append({"kind": "format", "path": f"unresolved[{index}]", "message": "blocking 불리언이 필요합니다"})
        elif item["blocking"]:
            issues.append({"kind": "unresolved", "path": f"unresolved[{index}]",
                           "message": f"구현 전 결정이 필요합니다: {item.get('topic', '미해결 사항')}"})
    return issues


def issue_summary(label, issues):
    listed = "; ".join(f"{issue['path']}: {issue['message']}" for issue in issues[:5])
    more = f" 외 {len(issues) - 5}건" if len(issues) > 5 else ""
    return f"{label} 검증 실패 {len(issues)}건 — {listed}{more}"


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
    reported = {item["path"] for item in issues}
    issues.extend(problem for problem in shared_field_issues(value) if problem["path"] not in reported)
    return issues


def scope_digest(value, path, kind, root, run_id, stop_at):
    """v1(3.0.0) 입력 지문. 절대 파일 경로와 프로젝트 루트 문자열을 포함한다."""
    return sha({"input": value, "file": str(path), "kind": kind, "project-root": str(root),
                "run-id": run_id, "stop-at": stop_at})


def scope_digest_v2(value, pointer, kind, run_id, stop_at, legacy_origin=False, choices=None):
    """v2 입력 지문. 프로젝트 기준 POSIX 상대경로만 넣어 위치가 바뀌어도 같다.

    3.0.0(v1) 실행을 재발급한 인계는 legacy-run-id를 지문에 묶어 다른 인계가 v1 규칙을 빌려 쓰지 못하게 한다.
    handoff --mode·--model-profile로 원문 밖에서 받은 진입 답(choices)도 지문에 묶는다. 없으면 이전 지문과 같다.
    """
    scope = {"schema-version": 2, "input": value, "file": pointer, "kind": kind, "run-id": run_id, "stop-at": stop_at}
    if legacy_origin:
        scope["legacy-run-id"] = True
    if choices:
        scope["entry-choices"] = choices
    return sha(scope)


def entry_choices(value, mode, model_profile):
    """handoff CLI로 받은 모드·프로파일 답. 원문(요청·외부 계획)에 같은 필드가 있으면 값이 같아야 하고,
    원문에 없을 때만 인계에 덧붙인다(외부 계획 파일은 고치지 않는다)."""
    choices = {}
    for key, given, allowed in (("mode", mode, MODES), ("model-profile", model_profile, MODEL_PROFILES)):
        if given is None:
            continue
        if given not in allowed:
            raise field_error(key, given, "|".join(allowed))
        if value.get(key) is None:
            choices[key] = given
        elif value[key] != given:
            raise InputError(f"{key} 값 {given!r}이(가) 원문 파일의 {value[key]!r}와 다릅니다. 같은 값으로 지정하거나 "
                             "옵션을 빼세요")
    return choices


def entry_digest(fingerprint, request_source, entry_source, question_set_id):
    return sha({"scope": fingerprint, "request-source": request_source, "source": entry_source,
                "question-set-id": question_set_id})


def project_file(root, value, label):
    candidate = Path(value)
    path = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise InputError(f"{label} {str(value)!r}은(는) 현재 프로젝트({root}) 안의 파일이어야 합니다")
    return path


def relative_pointer(value):
    return (isinstance(value, str) and bool(value) and "\\" not in value and "\x00" not in value
            and not PurePosixPath(value).is_absolute() and not PureWindowsPath(value).drive
            and ".." not in value.split("/"))


def legacy_relative(pointer, root_text):
    """v1 절대경로 포인터를 원래 루트 기준 POSIX 상대경로로 바꾼다(다른 OS의 표기도 처리)."""
    flavor = PureWindowsPath if re.match(r"(?:[A-Za-z]:[\\/]|\\\\)", str(root_text or "")) else PurePosixPath
    try:
        return flavor(pointer).relative_to(flavor(root_text)).as_posix()
    except (TypeError, ValueError) as error:
        raise InputError(f"v1 인계의 포인터 {pointer!r}가 원래 project-root {root_text!r} 안에 있지 않습니다") from error


def is_uuid(value):
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def run_answers(receipt):
    """영수증의 같은 run 누적 답(run_answers, 분할 질문). 없으면 이번 질문세트의 답(answers)."""
    for key in ("run_answers", "answers"):
        value = receipt.get(key) if isinstance(receipt, dict) else None
        if isinstance(value, dict):
            return value
    return {}


def entry_selection(receipt):
    """답변 영수증에 기록된 진입 질문 선택(문자열 목록). 없으면 None."""
    entry = run_answers(receipt).get(ENTRY_QUESTION_ID)
    selected = entry.get("answers") if isinstance(entry, dict) else None
    return selected if isinstance(selected, list) and all(isinstance(item, str) for item in selected) else None


def followup_answers(answers):
    """둘째 세트(모드·프로파일) 답을 요청 파일 값으로 바꾼다. 반환: ({필드: 값}, 답이 없는 질문 id 목록)."""
    choices, missing = {}, []
    for identifier, (field, labels) in FOLLOWUP_QUESTIONS.items():
        entry = answers.get(identifier)
        chosen = entry.get("answers") if isinstance(entry, dict) else None
        if not (isinstance(chosen, list) and chosen and isinstance(chosen[0], str)):
            missing.append(identifier)
            continue
        label = re.sub(r"\s*\(Recommended\)\s*$", "", chosen[0]).strip()
        choices[field] = labels.get(label, label)
    return choices, missing


def marker_selection(text, start):
    """decisions.md의 답변 표식(start 위치) 뒤 블록에서 진입 질문 선택을 읽는다. 읽을 수 없으면 None.

    블록 형식은 codex-question answer가 남기는 capture_decision.render 그대로다:
    `## 시각 · 헤더` / `**ID.** <id>` / 선택 줄 `**→** <label> — <설명>` 또는 `**→** (직접 입력) <값>`.
    """
    end = text.find("<!-- gx-question", start + 1)
    block = text[start:end if end != -1 else len(text)]
    for section in re.split(r"(?m)^## ", block)[1:]:
        if not re.search(r"(?m)^\*\*ID\.\*\* " + re.escape(ENTRY_QUESTION_ID) + r"[ \t]*\r?$", section):
            continue
        chosen = []
        for line in re.findall(r"(?m)^\*\*→\*\* (.+?)[ \t]*\r?$", section):
            free = re.match(r"\(직접 입력\) (.+)$", line)
            chosen.append(free.group(1) if free else line.split(" — ", 1)[0])
        return chosen or None
    return None


def is_proceed(selection):
    return bool(selection) and re.sub(r"\s*\(Recommended\)\s*$", "", selection[0]).strip() == ENTRY_PROCEED


def question_status(root, identifier, run_id=None):
    """같은 question_set_id의 미응답 여부(.dev/*/ 전체)와 run_id에 결박된 응답 여부·진입 선택을 찾는다.

    응답은 (a) 영수증(answered-question.json)의 question.run_id가 run_id와 같거나
    (b) `.dev/<run_id>/decisions.md`에 질문 helper 답변 표식 줄이 그대로 있을 때만 인정한다.
    다른 run 디렉토리의 표식이나 run이 다른 영수증은 인정하지 않는다.
    """
    pending, answered, selection = False, False, None
    dev = root / ".dev"
    directories = [item for item in sorted(dev.iterdir()) if item.is_dir() and not item.is_symlink()] if dev.is_dir() else []
    for directory in directories:
        for name in ("pending-question.json", "answered-question.json"):
            path = directory / name
            if not path.is_file():
                continue
            try:
                record = question_file(path, name)
            except (OSError, ValueError):
                continue
            if name == "pending-question.json":
                # 같은 run의 둘째 세트(모드·프로파일)가 미응답이면 진입 답도 아직 인계에 쓰지 않는다.
                followup = run_id is not None and record.get("run_id") == run_id and any(
                    isinstance(item, dict) and item.get("id") in FOLLOWUP_QUESTIONS for item in record.get("questions") or [])
                pending = pending or record.get("question_set_id") == identifier or followup
                continue
            recorded = record.get("question")
            earlier = record.get("earlier_question_set_ids")
            identifiers = [recorded.get("question_set_id") if isinstance(recorded, dict) else None,
                           *(earlier if isinstance(earlier, list) else [])]
            if (run_id is not None and isinstance(recorded, dict)
                    and identifier in identifiers and recorded.get("run_id") == run_id):
                answered, selection = True, entry_selection(record)
    if run_id is not None and not answered and not re.search(r"[\\/\x00-\x1f]|\.\.", run_id):
        decisions = dev / run_id / "decisions.md"
        marker = re.compile(r"^<!-- gx-question:" + re.escape(identifier) + r":[0-9a-f]{64} -->\r?$", re.M)
        try:
            content = read_text(decisions, "decisions.md") if decisions.is_file() else ""
        except (OSError, ValueError):
            content = ""
        found = marker.search(content)
        if found:
            answered, selection = True, marker_selection(content, found.start())
    return pending, answered, selection


def completed_state(root, run_id):
    for path in sorted((root / ".dev").glob("*/state.md")):
        try:
            fields = state_fields(path)
        except (OSError, ValueError):
            continue
        if fields.get("run-id") == run_id and fields.get("status") == "completed":
            return path.relative_to(root).as_posix()
    return None


def build_handoff(kind, source, root, *, stop_at, run_id, approval_source, entry_approval_source,
                  question_set_id, schema_version, legacy_origin=False, mode=None, model_profile=None):
    """인계 본문을 만든다. root는 확정된 프로젝트 루트(없으면 미리보기용 인계)다.

    legacy_origin은 3.0.0(v1) 실행을 재발급한 v2 인계다. run-id 형식과 요청 차단 규칙을 소급하지 않는다.
    mode·model_profile은 handoff CLI로 받은 진입 답이다(v2만, entry_choices 규칙).
    """
    if stop_at not in ENDPOINTS:
        raise field_error("stop-at", stop_at, "|".join(ENDPOINTS))
    legacy = schema_version == 1
    label = "계획 파일" if kind == "plan" else "요청 파일"
    path = project_file(root, source, label) if root is not None else Path(source).resolve()
    value = read_json(path, label)
    if not isinstance(value, dict) or not text(value.get("goal")):
        raise InputError(f"{label}에 비어 있지 않은 goal 문자열이 있는 JSON 객체가 필요합니다: {path}")
    if retired_ralph_request(value["goal"]):
        raise InputError("Ralph 지원이 중단되었습니다. 일반 TDD 전환 범위를 먼저 확인하세요")
    issues = validate_plan(value) if kind == "plan" else shared_field_issues(value)
    if kind == "request" and not legacy and not legacy_origin:
        issues += request_blocking_issues(value)
    if issues:
        raise InputError(issue_summary(label, issues), issues)
    if legacy and (mode is not None or model_profile is not None):
        raise InputError("v1 인계에는 모드·프로파일을 싣지 않습니다. reissue로 v2 인계를 발급하세요")
    choices = entry_choices(value, mode, model_profile)
    if approval_source is not None and not text(approval_source):
        raise InputError("approval-source(최초 요청 근거)는 비어 있지 않은 문자열이어야 합니다")
    if entry_approval_source is not None and not text(entry_approval_source):
        raise InputError("entry-approval-source(실제 TDD 진입 응답 근거)는 비어 있지 않은 문자열이어야 합니다")
    if question_set_id is not None and not text(question_set_id):
        raise InputError("question-set-id는 비어 있지 않은 문자열이어야 합니다")
    if entry_approval_source and (root is None or not text(run_id)):
        raise InputError("진입 응답을 결박할 project-root와 현재 run-id가 필요합니다")
    if run_id is not None and not text(run_id):
        raise InputError("비어 있지 않은 run-id가 필요합니다")
    identifier = run_id or (value.get("run-id") if stop_at in ("understand", "plan") else None) or str(uuid.uuid4())
    if legacy_origin:
        # 3.0.0 run-id는 형식을 소급하지 않지만 경로를 깨는 값(구분자·..·제어문자)은 받지 않는다.
        if not text(identifier) or re.search(r"[\\/\x00-\x1f]|\.\.", identifier):
            raise field_error("run-id", identifier, "경로 구분자·..·제어문자가 없는 기존 3.0.0 run-id")
    elif not legacy and (not isinstance(identifier, str) or not RUN_ID.fullmatch(identifier)):
        raise field_error("run-id", identifier, RUN_ID_RULE)
    if question_set_id is not None:
        if not legacy and not is_uuid(question_set_id):
            raise field_error("question-set-id", question_set_id,
                              "Codex 질문 helper(register)가 반환한 UUID. Claude Code 진입 질문에는 넘기지 않습니다")
        if root is None:
            if not legacy:
                raise InputError("question-set-id의 질문 기록을 확인하려면 project-root가 필요합니다")
        else:
            pending, answered, selection = question_status(root, question_set_id, None if legacy else identifier)
            if pending:
                raise InputError(f"question-set-id {question_set_id!r}의 질문(같은 run의 모드·프로파일 둘째 세트 포함)이 "
                                 "아직 응답되지 않았습니다(pending-question.json). 실제 답변을 질문 helper answer로 "
                                 "기록한 뒤 다시 발급하세요")
            if not legacy and not answered:
                raise InputError(f"question-set-id {question_set_id!r}의 응답 기록을 찾을 수 없습니다. 이 run의 답변 영수증"
                                 f"(answered-question.json의 run_id {identifier!r})이나 `.dev/{identifier}/decisions.md`의 "
                                 "답변 표식 줄(<!-- gx-question:<id>:<digest> -->)이 필요합니다. 질문 helper answer가 "
                                 "exit 0으로 끝났는지, 다른 위치로 옮겼다면 표식 줄을 "
                                 f"`.dev/{identifier}/decisions.md`에 그대로 복사했는지 확인하세요")
            if not legacy and selection is not None and not is_proceed(selection):
                raise InputError(f"question-set-id {question_set_id!r}에 기록된 진입 답변은 {selection!r}입니다. "
                                 f"'{ENTRY_PROCEED}' 답변일 때만 진입 승인으로 씁니다")
    if root is not None:
        finished = completed_state(root, identifier)
        if finished:
            raise InputError(f"run-id {identifier!r}의 실행은 이미 완료되었습니다({finished}). 완료된 실행의 인계는 "
                             "재사용하지 않습니다. 새 run-id로 진입 질문부터 시작하세요")
    readonly = stop_at in ("understand", "plan")
    if legacy:
        pointer = str(path)
        fingerprint = scope_digest(value, path, kind, root, identifier, stop_at)
    else:
        pointer = path.relative_to(root).as_posix() if root is not None else str(path)
        fingerprint = scope_digest_v2(value, pointer, kind, identifier, stop_at, legacy_origin, choices)
    ready = bool(entry_approval_source and root)
    entry_fingerprint = entry_digest(fingerprint, approval_source or entry_approval_source,
                                     entry_approval_source, question_set_id)
    result = {
        "schema-version": schema_version, "origin": "gx-work", "handoff-kind": kind, "run-id": identifier,
        "project-root": str(root) if root else None, "input-sha256": fingerprint,
        "goal": value["goal"], "intent": stop_at if readonly else "implement",
        "stop-at": stop_at, "plan-file": pointer if kind == "plan" else None,
        "request-file": pointer if kind == "request" else None, "work-id": value.get("work-id"),
    }
    if not legacy:
        result["execution-method"] = value.get("execution-method")
        result["model-profile"] = choices.get("model-profile", value.get("model-profile"))
        result["mode"] = choices.get("mode", value.get("mode"))
    if legacy_origin:
        result["legacy-run-id"] = True
    result.update({
        "approval": {"status": "approved" if approval_source or entry_approval_source else "unconfirmed",
                     "source": approval_source or entry_approval_source},
        "entry-approval": {"status": "approved" if ready else "unconfirmed", "source": entry_approval_source,
                           "question-set-id": question_set_id, "scope-sha256": entry_fingerprint if ready else None},
        "ready-for-tdd": ready, "read-only": readonly, "execution-authorized": ready and not readonly,
    })
    for key in LIST_FIELDS:
        result[key] = value.get(key, [])
    return result


def handoff(plan_path=None, stop_at="verify", run_id=None, approval_source=None, *,
            request_path=None, project_root=None, entry_approval_source=None, question_set_id=None,
            git_safe_directory=None, mode=None, model_profile=None):
    """새 인계(schema v2)를 만든다. 포인터·지문은 프로젝트 기준 상대경로다.

    mode·model_profile은 진입 질문의 모드·프로파일 답이다. 기존 계획(--plan)처럼 원문에 실을 수 없을 때 쓴다.
    """
    if stop_at not in ENDPOINTS:
        raise field_error("stop-at", stop_at, "|".join(ENDPOINTS))
    if (plan_path is None) == (request_path is None):
        raise InputError("plan 또는 request 파일 하나만 지정하세요")
    root = project_layout(project_root, git_safe_directory)["root"] if project_root is not None else None
    kind = "plan" if plan_path is not None else "request"
    return build_handoff(kind, plan_path if kind == "plan" else request_path, root, stop_at=stop_at,
                         run_id=run_id, approval_source=approval_source,
                         entry_approval_source=entry_approval_source, question_set_id=question_set_id,
                         schema_version=2, mode=mode, model_profile=model_profile)


def handoff_document(path):
    data = read_json(path, "인계 파일")
    if (not isinstance(data, dict) or type(data.get("schema-version")) is not int
            or data["schema-version"] not in (1, 2) or data.get("origin") != "gx-work"):
        raise InputError("gx-work 인계 형식 오류: schema-version 1 또는 2와 origin gx-work가 필요합니다")
    if not text(data.get("run-id")):
        raise InputError("인계에 run-id가 없습니다")
    kind = data.get("handoff-kind")
    if kind not in ("plan", "request"):
        raise field_error("handoff-kind", kind, "plan|request")
    pointer, other = ("plan-file", "request-file") if kind == "plan" else ("request-file", "plan-file")
    if not text(data.get(pointer)) or data.get(other) is not None:
        raise InputError("원문 포인터가 없거나 충돌합니다")
    if data["schema-version"] == 2 and not relative_pointer(data[pointer]):
        raise field_error(pointer, data[pointer], "프로젝트 루트 기준 POSIX 상대경로(v2)")
    if not isinstance(data.get("entry-approval"), dict) or not isinstance(data.get("approval"), dict):
        raise InputError("TDD 진입 응답이 없습니다")
    return data, kind, pointer


def validate_handoff(handoff_path, project_root, git_safe_directory=None):
    """인계를 재검사한다. 응답 source가 실제 사용자 사건인지는 하네스가 확인한다."""
    try:
        requested = Path(project_root).resolve()
        if not requested.is_dir():
            raise field_error("project-root", str(project_root), "존재하는 프로젝트 디렉터리")
        candidate = Path(handoff_path)
        path = (candidate if candidate.is_absolute() else requested / candidate).resolve()
        if not path.is_file():
            raise InputError(f"인계 파일 {str(handoff_path)!r}을(를) 찾을 수 없습니다")
        data, kind, pointer = handoff_document(path)
        legacy = data["schema-version"] == 1
        # v1은 3.0.0과 같이 입력 루트에 묶이고 git을 부르지 않는다. v2는 gx-tdd와 같은 루트 규칙을 쓴다.
        root = requested if legacy else project_layout(requested, git_safe_directory)["root"]
        if not path.is_relative_to(root):
            raise InputError(f"인계 파일은 현재 프로젝트({root}) 안에 있어야 합니다: {path}")
        if legacy and data.get("project-root") != str(root):
            raise InputError(f"v1 인계의 project-root {data.get('project-root')!r}가 현재 프로젝트 {str(root)!r}와 "
                             "다릅니다. 위치가 바뀌었으면 reissue로 v2 인계를 다시 발급하세요")
        entry, approval = data["entry-approval"], data["approval"]
        expected = build_handoff(kind, data[pointer], root, stop_at=data.get("stop-at"), run_id=data["run-id"],
                                 approval_source=approval.get("source"),
                                 entry_approval_source=entry.get("source"),
                                 question_set_id=entry.get("question-set-id"),
                                 schema_version=data["schema-version"],
                                 legacy_origin=not legacy and data.get("legacy-run-id") is True,
                                 mode=None if legacy else data.get("mode"),
                                 model_profile=None if legacy else data.get("model-profile"))
        keys = ["input-sha256", "goal", "intent", "ready-for-tdd", "read-only", "execution-authorized", "work-id",
                *LIST_FIELDS, "entry-approval", "approval"]
        if not legacy:
            keys += ["execution-method", "model-profile", "mode", "plan-file", "request-file", "legacy-run-id"]
        for key in keys:
            if data.get(key) != expected.get(key):
                raise InputError(f"승인한 요청·실행·종료점 또는 인계가 바뀌었습니다: {key}")
        if not expected["ready-for-tdd"]:
            raise InputError("관련 결과와 다음 단계를 제시하고 실제 TDD 진입 응답을 기다리세요")
        return {"ready-for-tdd": True, "schema-version": data["schema-version"], "run-id": data["run-id"],
                "stop-at": data["stop-at"], "handoff-kind": kind, "plan-file": data.get("plan-file"),
                "request-file": data.get("request-file"), "project-root": str(root),
                "read-only": expected["read-only"], "execution-authorized": expected["execution-authorized"],
                "intent": expected["intent"]}
    except (OSError, ValueError, TypeError, RuntimeError, RecursionError) as error:
        failure = {"ready-for-tdd": False, "error": str(error)}
        if isinstance(error, InputError) and error.issues:
            failure["issues"] = error.issues
        return failure


def reissue(handoff_path, project_root, stop_at=None, change_source=None, question_set_id=None,
            git_safe_directory=None):
    """기존 인계를 같은 run-id의 v2 인계로 다시 발급해 반환한다. 파일은 쓰지 않는다.

    종료점 변경은 실제 사용자 결정 근거(change_source)가 새 진입 승인 근거가 된다. 위치만 바뀐 경우 기존
    진입 승인을 유지한다. 요청·계획 내용이 바뀌었거나 진입 승인이 없으면 재발급하지 않는다.
    """
    root = project_layout(project_root, git_safe_directory)["root"]
    path = project_file(root, handoff_path, "인계 파일")
    raw = path.read_bytes()
    data, kind, pointer = handoff_document(path)
    entry, approval = data["entry-approval"], data["approval"]
    if entry.get("status") != "approved" or not text(entry.get("source")):
        raise InputError("진입 승인이 없는 인계는 재발급할 수 없습니다. 결과와 다음 단계를 보여주고 진입 질문부터 다시 하세요")
    old_stop = data.get("stop-at")
    if old_stop not in ENDPOINTS:
        raise field_error("stop-at", old_stop, "|".join(ENDPOINTS), "기존 인계")
    label = "계획 파일" if kind == "plan" else "요청 파일"
    # 3.0.0에서 시작한 실행(v1 또는 v1에서 재발급한 v2)은 v1의 run-id·요청 차단 규칙을 유지한다.
    legacy_origin = data["schema-version"] == 1 or data.get("legacy-run-id") is True
    mode = model_profile = None
    if data["schema-version"] == 1:
        relative = legacy_relative(data[pointer], data.get("project-root"))
        value = read_json(project_file(root, relative, label), label)
        fingerprint = scope_digest(value, data[pointer], kind, data.get("project-root"), data["run-id"], old_stop)
    else:
        relative = data[pointer]
        value = read_json(project_file(root, relative, label), label)
        # 인계에 실린 모드·프로파일 답(원문 밖에서 받은 값)을 그대로 이어 싣는다.
        mode, model_profile = data.get("mode"), data.get("model-profile")
        choices = entry_choices(value, mode, model_profile) if isinstance(value, dict) else {}
        fingerprint = scope_digest_v2(value, relative, kind, data["run-id"], old_stop, legacy_origin, choices)
    if fingerprint != data.get("input-sha256"):
        raise InputError("인계 이후 요청·계획 내용이나 인계가 바뀌었습니다. 재발급이 아니라 결과를 다시 보여주고 "
                         "새 진입 질문으로 확인하세요")
    if entry.get("scope-sha256") != entry_digest(fingerprint, approval.get("source"), entry.get("source"),
                                                 entry.get("question-set-id")):
        raise InputError("인계의 진입 승인 지문이 입력과 맞지 않습니다. 새 진입 질문으로 확인하세요")
    if stop_at is not None and stop_at not in EXECUTION_ENDPOINTS:
        raise field_error("stop-at", stop_at, "|".join(EXECUTION_ENDPOINTS))
    old_identifier = entry.get("question-set-id")
    old_answered = False
    if old_identifier is not None:
        pending, old_answered, old_selection = question_status(root, old_identifier, data["run-id"])
        if pending:
            raise InputError(f"원래 진입 질문(question-set-id {old_identifier!r})이 아직 응답되지 않았습니다. 실제 답변을 "
                             "기록하거나 실제 결정으로 폐기한 뒤 진입 질문부터 다시 하세요")
        if old_selection is not None and not is_proceed(old_selection):
            raise InputError(f"원래 진입 질문(question-set-id {old_identifier!r})에 기록된 답변은 {old_selection!r}입니다. "
                             f"'{ENTRY_PROCEED}' 답변이 아닌 실행은 재발급하지 않습니다. 진입 질문부터 다시 하세요")
    new_stop = stop_at or old_stop
    dropped = None
    if new_stop != old_stop:
        if old_stop not in EXECUTION_ENDPOINTS:
            raise InputError(f"읽기 전용 인계(stop-at {old_stop})는 실행 종료점으로 재발급하지 않습니다. "
                             "개발 진입 질문으로 새 인계를 만드세요")
        if not text(change_source):
            raise InputError(f"종료점을 {old_stop}에서 {new_stop}(으)로 바꾸려면 --change-source에 실제 사용자 결정 "
                             "근거가 필요합니다")
        entry_source, identifier = change_source, question_set_id
    else:
        if change_source is not None or question_set_id is not None:
            raise InputError("종료점이 그대로면 --change-source·--question-set-id를 쓰지 않습니다. 기존 진입 승인을 유지합니다")
        entry_source, identifier = entry["source"], old_identifier
        if identifier is not None and (not is_uuid(identifier) or not old_answered):
            # 응답도 미응답도 아닌 식별자(3.0.0의 고정 문자열, 옮기며 유실된 기록)만 버리고 승인 근거 문장을 남긴다.
            dropped, identifier = identifier, None
    result = build_handoff(kind, relative, root, stop_at=new_stop, run_id=data["run-id"],
                           approval_source=approval.get("source"), entry_approval_source=entry_source,
                           question_set_id=identifier, schema_version=2, legacy_origin=legacy_origin,
                           mode=mode, model_profile=model_profile)
    result["reissued-from-sha256"] = hashlib.sha256(raw).hexdigest()
    # 위치 변경: 기록된 project-root(v2는 표시용)나 v1 절대 포인터가 현재 위치와 다르다.
    result["relocated"] = data.get("project-root") != str(root) or (
        data["schema-version"] == 1 and data[pointer] != str((root / relative).resolve()))
    if new_stop != old_stop:
        result["stop-at-changed-from"] = old_stop
    if dropped is not None:
        result["dropped-question-set-id"] = dropped
    return result


def cancel(project_root, reason, run_id=None, git_safe_directory=None, slug=None):
    """현재 위치의 진행 중 gx-tdd 실행 state를 status: cancelled로 바꾸고 같은 디렉터리 decisions.md에 취소 근거를
    덧붙인다. 다른 줄·파일(질문·보고서, decisions.md의 기존 내용)은 그대로 둔다. 구버전(gx-tdd 외·Ralph) 기록은 바꾸지 않는다.

    주의: 사용자가 작업 취소를 실제로 답했을 때만 부른다. 추천·무응답·시간 경과·헤드리스 판단으로 부르지 않는다.
    reason에는 그 실제 응답 근거를 넣는다(helper는 응답 사건의 진위를 증명하지 않는다). 호출 조건은 gx-work 문서가 정한다.
    """
    if not text(reason):
        raise InputError("reason(작업 취소를 고른 실제 사용자 응답 근거)이 필요합니다")
    if slug is not None and not safe_slug(slug):
        raise field_error("slug", slug, "영문·숫자·._- 조합, setup이 정규화한 SVN 작업 slug")
    layout = project_layout(project_root, git_safe_directory)
    state, state_file = active_state(layout, slug)
    if state.get("detached-head"):
        raise InputError("브랜치가 없는 HEAD(detached)라 취소할 실행을 정할 수 없습니다")
    if state.get("resume-candidates") or state.get("work-candidates"):
        raise InputError("진행 중 실행 후보가 여럿입니다. 취소할 작업의 slug를 --slug로 지정하세요")
    if state_file is None or state.get("status") != "in_progress":
        raise InputError(f"취소할 진행 중 실행이 없습니다(state {state_file or '없음'}, status "
                         f"{state.get('status') or '없음'}). 진행 중(in_progress)인 실행만 취소합니다")
    # route의 구버전 판정(pipeline·flags의 Ralph 흔적)과 같은 규칙이다. 구버전 기록은 고치지 않고 새 범위로 빠져나온다.
    if state.get("pipeline") != "gx-tdd" or re.search(r"(?<![\w-])(?:--)?ralph(?![\w-])", state.get("flags", ""), re.I):
        raise InputError(f"gx-tdd 실행만 취소합니다(pipeline {state.get('pipeline') or '없음'}, flags "
                         f"{state.get('flags') or '없음'}). 구버전 기록은 바꾸지 않고 그대로 둡니다")
    if run_id is not None and state.get("run-id") != run_id:
        raise InputError(f"run-id {run_id!r}이(가) 현재 실행의 run-id {state.get('run-id')!r}와 다릅니다. 취소하지 않습니다")
    path = Path(state_file)
    if (path.parent / "ralph.lock").exists():
        raise InputError("ralph.lock이 있어 state를 바꾸지 않습니다. 잠금·러너는 사용자가 먼저 정리합니다")
    raw = path.read_bytes()
    lines = read_text(path, "state.md").splitlines(keepends=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    for index, line in enumerate(lines):
        match = STATE_KEY.match(line.rstrip("\r\n"))
        if match and match.group(1) == "status":
            # state_fields가 읽는 첫 최상위 status 줄만 바꾸고 취소 시각·근거를 바로 뒤에 덧붙인다.
            if scalar(match.group(2)) != "in_progress":
                raise InputError(f"state.md의 첫 status 줄이 in_progress가 아닙니다: {path}. 손으로 확인하세요")
            ending = line[len(line.rstrip("\r\n")):] or "\n"
            lines[index:index + 1] = ["status: cancelled" + ending, f"cancelled-at: {now}" + ending,
                                      "cancel-source: " + json.dumps(reason, ensure_ascii=False) + ending]
            break
    else:
        raise InputError(f"state.md에서 최상위 status 줄을 찾지 못했습니다: {path}")
    content = ("﻿" if raw.startswith(b"\xef\xbb\xbf") else "") + "".join(lines)
    # 취소 근거를 state보다 먼저 남긴다(pipeline-state cancelled 수명주기). 헤더는 질문 helper의 decisions.md와 같다.
    decisions = path.parent / "decisions.md"
    note = (f"\n## {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} · 작업 취소\n\n"
            f"**결정.** 작업 취소 (run-id {state.get('run-id') or '없음'}, phase {state.get('phase') or '없음'})\n\n"
            f"**근거.** {reason}\n")
    with open(decisions, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(note if decisions.stat().st_size else "# 의사결정 기록\n\n확인 질문과 선택을 기록한다.\n" + note)
    descriptor, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"status": "cancelled", "previous-status": "in_progress", "state-file": str(path),
            "run-id": state.get("run-id"), "goal": state.get("goal", state.get("args")),
            "pipeline": state.get("pipeline"), "phase": state.get("phase"), "cancelled-at": now,
            "reason": reason, "reason-provenance": "caller_supplied; user_event_not_verified",
            "decisions-file": str(decisions)}


def build_parser():
    parser = JsonArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    routing = commands.add_parser("route")
    routing.add_argument("--project-root", required=True)
    routing.add_argument("--intent", choices=INTENTS, required=True)
    routing.add_argument("--stop-at", choices=ENDPOINTS)
    routing.add_argument("--goal", default="")
    routing.add_argument("--git-safe-directory")
    routing.add_argument("--slug")
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
    transfer.add_argument("--git-safe-directory")
    transfer.add_argument("--mode", choices=MODES)
    transfer.add_argument("--model-profile", choices=MODEL_PROFILES)
    recheck = commands.add_parser("validate-handoff")
    recheck.add_argument("--handoff", required=True)
    recheck.add_argument("--project-root", required=True)
    recheck.add_argument("--git-safe-directory")
    again = commands.add_parser("reissue")
    again.add_argument("--handoff", required=True)
    again.add_argument("--project-root", required=True)
    again.add_argument("--stop-at", choices=EXECUTION_ENDPOINTS)
    again.add_argument("--change-source")
    again.add_argument("--question-set-id")
    again.add_argument("--git-safe-directory")
    # 실제 사용자 취소 응답이 있을 때만 쓴다(cancel 함수 주석).
    stop = commands.add_parser("cancel")
    stop.add_argument("--project-root", required=True)
    stop.add_argument("--reason", required=True)
    stop.add_argument("--run-id")
    stop.add_argument("--git-safe-directory")
    stop.add_argument("--slug")
    return parser


def main(argv=None):
    command = None
    try:
        args = build_parser().parse_args(argv)
        command = args.command
        code = 0
        if command == "route":
            result = route(args.project_root, args.intent, args.stop_at, args.goal, args.git_safe_directory, args.slug)
        elif command == "validate-plan":
            issues = validate_plan(read_json(Path(args.plan), "계획 파일"))
            result = {"valid": not issues, "issues": issues, "approval": "unconfirmed"}
            code = 2 if issues else 0
        elif command == "validate-handoff":
            result = validate_handoff(args.handoff, args.project_root, args.git_safe_directory)
            code = 0 if result["ready-for-tdd"] else 2
        elif command == "reissue":
            result = reissue(args.handoff, args.project_root, args.stop_at, args.change_source,
                             args.question_set_id, args.git_safe_directory)
        elif command == "cancel":
            result = cancel(args.project_root, args.reason, args.run_id, args.git_safe_directory, args.slug)
        else:
            result = handoff(args.plan, args.stop_at, args.run_id, args.approval_source,
                             request_path=args.request, project_root=args.project_root,
                             entry_approval_source=args.entry_approval_source,
                             question_set_id=args.question_set_id, git_safe_directory=args.git_safe_directory,
                             mode=args.mode, model_profile=args.model_profile)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        failure = {"error": str(error) or type(error).__name__}
        if isinstance(error, InputError) and error.issues:
            failure["issues"] = error.issues
        if command in ("handoff", "reissue", "validate-handoff"):
            failure["ready-for-tdd"] = False
        print(json.dumps(failure, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
