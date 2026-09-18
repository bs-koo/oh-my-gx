# gx-visualize 누적 아키텍처 맵 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gx-visualize에 코드 근거 기반 누적 아키텍처 맵을 더해, 개발 사이클 직후와 단독 호출 모두에서 "구현된 기능의 구조"를 볼 수 있게 한다.

**Architecture:** 결정적 Python 스캐너가 진입점 체인(화면→API→서비스→리포지터리→테이블)을 file:line 근거와 함께 추출하고, 스킬이 `context/`의 도메인 용어로 한국어 라벨을 입힌다. 파일 지문 매니페스트로 변경분만 재스캔해 이전 IR과 병합하고, 기존 IR 검증기가 병합 사고를 잡는다. 렌더링은 Archify를 우선 쓰되 실패하면 mermaid·static으로 폴백한다.

**Tech Stack:** Python 3.10 표준 라이브러리만 (외부 패키지 금지), Markdown 스킬 계약, Archify CLI(선택 의존성, Node 22), `python -m unittest`

**Spec:** `docs/superpowers/specs/2026-09-18-gx-visualize-architecture-map-design.md`

## Global Constraints

- Python은 **표준 라이브러리만** 사용한다. 외부 패키지를 추가하지 않는다.
- 모든 파일 입출력은 `encoding="utf-8"`을 명시한다 (Windows 기본 인코딩이 cp949다).
- 모든 서브프로세스 실행은 `shell=False`다. 문자열 명령에 셸 연산자를 넣지 않는다.
- 노드 ID·정렬 순서는 **결정적**이어야 한다. 같은 입력은 항상 같은 출력을 낸다.
- 근거 없는 노드를 만들지 않는다. 모든 코드 노드는 `evidence.kind == "code"`와 실재하는 `file`·`line`을 갖는다.
- 기존 `trace`·`progress`·`impact` 뷰의 동작과 출력 경로 `${DEV_DIR}/visual/`를 변경하지 않는다.
- 커밋 메시지는 `{type}: 한국어 요약` 형식이며 `Co-Authored-By` 트레일러를 넣지 않는다.
- 스킬 번들 파일은 **지시가 적힌 파일 기준 상대경로**로 참조한다. `${CLAUDE_PLUGIN_ROOT}`나 cwd를 플러그인 루트로 가정하지 않는다.

### Codex 호환 (모든 태스크 공통)

이 저장소는 Claude Code와 Codex CLI 양쪽에 배포된다. 근거 문서는 [스킬 유지보수 규칙](../../../.claude/rules/skill-maintenance.md), [Codex 하네스 어댑터](../../../.claude/rules/harness-codex.md), 배포 정본인 [공통 실행 규약](../../../.claude/skills/gx-dev/references/codex-runtime.md), 그리고 이 스킬의 [Codex 적응 노트](../../../.claude/skills/gx-visualize/references/codex-runtime.md)다.

- `.codex-plugin/plugin.json`의 `skills`는 `./.claude/skills/` **디렉터리**를 가리킨다. 신규 스킬·스크립트는 자동 포함되므로 per-skill 등록은 불필요하다.
- **하네스 적응은 스킬 수준에 있다.** phase 파일에는 적응 절이 없으며 그것이 이 저장소의 설계다 — gx-dev는 `SKILL.md`의 표, gx-tdd는 `references/harness-adaptation.md`, gx-visualize는 `references/codex-runtime.md`가 정본이다. phase 파일에 새 적응 절을 만들지 않는다.
- 두 파이프라인의 적응 표는 이미 `AskUserQuestion` → `request_user_input`(못 쓰면 자연어로 묻되 승인 없이 진행 금지)과 `Skill(skill: …)` → 해당 `SKILL.md`를 읽어 절차 수행을 규정한다. **그 두 매핑만 쓰는 변경은 적응 갱신이 필요 없다.** 새로운 *종류*의 도구 상호작용을 도입할 때만 스킬 수준 정본을 갱신한다.
- `allowed-tools`나 역할의 `tools` 목록을 Codex 권한 강제로 표현하지 않는다.
- Python 스크립트는 **설치된 `gx-visualize/scripts/`** 에서 찾는다. 소비 프로젝트에 같은 이름의 스크립트가 있어도 대신 실행하지 않는다.
- 셸 명령은 Codex에서 `exec_command` 계열로 옮겨진다. **명령 실행이 샌드박스·승인으로 막힐 수 있으므로**, 막힌 경우를 실패가 아니라 폴백 경로로 처리하고 시도 기록을 receipt에 남긴다. `merge_map.py`의 `git hash-object` 폴백이 이 요구를 이미 만족한다.
- Windows에서 Markdown·JSON·소스 읽기와 쓰기는 **UTF-8을 명시**한다. PowerShell 예시에는 `Get-Content -Encoding UTF8`을 쓰고 Bash 문법은 Bash에서 실행한다.
- 특정 Codex 모델명·도구 인자를 불변 API처럼 쓰지 않는다. 실제 세션의 허용 목록과 스키마를 확인하도록 적는다.
- 검증 명령: `python scripts/sync-codex-resources.py --check`, `bash scripts/lint-consistency.sh`. Codex 실행 경로를 바꿨으면 `python -m unittest discover -s tests -p "test_codex_*.py" -v`, 훅·보호 조건을 바꿨으면 `bash scripts/hook-tests.sh`도 실행한다.
- **로컬 린트·mock 결과로 실제 설치·모델·훅 동작을 검증했다고 표시하지 않는다.** 실제 Codex 세션에서 확인하지 않은 항목은 [Codex smoke 계약](../../../tests/codex-smoke.md)에 **미실행으로 기록**한다.

## File Structure

**신규**

| 파일 | 책임 |
|---|---|
| `.claude/skills/gx-visualize/scripts/scan_entrypoints.py` | 진입점 체인 추출 (언어별 패턴, 결정적) |
| `.claude/skills/gx-visualize/scripts/merge_map.py` | 매니페스트 지문 비교 + 이전 IR과 증분 병합 |
| `.claude/skills/gx-visualize/scripts/to_archify.py` | GX IR → Archify 타입 IR 변환 |
| `.claude/skills/gx-visualize/references/entrypoint-rules.md` | 언어별 추출 규칙 문서 |
| `tests/fixtures/gx-arch-java/` | Java Spring 스캐너 픽스처 |
| `tests/fixtures/gx-arch-jsp/` | JSP·Servlet 스캐너 픽스처 |
| `tests/test_gx_arch_scan.py` | 스캐너 테스트 |
| `tests/test_gx_arch_merge.py` | 병합·매니페스트 테스트 |
| `tests/test_gx_arch_archify.py` | Archify 변환·명령 테스트 |
| `tests/test_gx_arch_pipeline.py` | phase-complete 게이트 계약 테스트 |

**수정**

| 파일 | 변경 |
|---|---|
| `.claude/skills/gx-visualize/scripts/render_archify.py` | CLI 시그니처 수리 + 변환기 연결 |
| `.claude/skills/gx-visualize/SKILL.md` | `service`·`sequence` 승격, `--scope`·`--map-dir` 도입 |
| `.claude/skills/gx-dev/phases/phase-complete.md` | Step 5.5 제안 게이트 추가 |
| `.claude/skills/gx-tdd/phases/phase-complete.md` | Step 5.5 제안 게이트 추가 |
| `README.md`, `index.html`, `docs/gx-visualize-guide.md` | 누적 맵 문서화 (기존 RED 테스트 해소) |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md` | 1.34.0 |

---

### Task 1: 진입점 스캐너 — Java Spring

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/scan_entrypoints.py`
- Create: `tests/fixtures/gx-arch-java/src/main/java/com/sqi/auth/LoginController.java`
- Create: `tests/fixtures/gx-arch-java/src/main/java/com/sqi/auth/LoginService.java`
- Create: `tests/fixtures/gx-arch-java/src/main/java/com/sqi/auth/LoginMapper.java`
- Test: `tests/test_gx_arch_scan.py`

**Interfaces:**
- Produces: `scan(project_root: Path | str, changed_files: list[str] | None = None) -> dict` — 반환값은 `{"nodes": [...], "edges": [...], "files": {rel_path: [node_id, ...]}}`. `nodes`는 `id`로, `edges`는 `id`로 정렬된다. `changed_files`가 주어지면 그 파일들만 스캔한다.
- Produces: `node_id(kind: str, rel_path: str, symbol: str) -> str`

- [ ] **Step 1: 픽스처 3개를 작성한다**

`tests/fixtures/gx-arch-java/src/main/java/com/sqi/auth/LoginController.java`:

```java
package com.sqi.auth;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LoginController {
    private final LoginService loginService;

    public LoginController(LoginService loginService) {
        this.loginService = loginService;
    }

    @PostMapping("/api/auth/login")
    public String login(String userId) {
        return loginService.authenticate(userId);
    }
}
```

`tests/fixtures/gx-arch-java/src/main/java/com/sqi/auth/LoginService.java`:

```java
package com.sqi.auth;

import org.springframework.stereotype.Service;

@Service
public class LoginService {
    private final LoginMapper loginMapper;

    public LoginService(LoginMapper loginMapper) {
        this.loginMapper = loginMapper;
    }

    public String authenticate(String userId) {
        return loginMapper.selectUser(userId);
    }
}
```

`tests/fixtures/gx-arch-java/src/main/java/com/sqi/auth/LoginMapper.java`:

```java
package com.sqi.auth;

import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface LoginMapper {
    String selectUser(String userId);
}
```

- [ ] **Step 2: 실패 테스트를 작성한다**

`tests/test_gx_arch_scan.py`:

```python
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-java"
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "scan_entrypoints.py"


def _module():
    spec = importlib.util.spec_from_file_location("gx_scan_entrypoints", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JavaSpringScanTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_extracts_api_service_repository_nodes(self):
        result = self.scan(FIXTURE)
        kinds = {node["kind"] for node in result["nodes"]}
        self.assertEqual({"api", "service", "repository"}, kinds)

    def test_every_node_carries_real_code_evidence(self):
        result = self.scan(FIXTURE)
        self.assertTrue(result["nodes"])
        for node in result["nodes"]:
            evidence = node["evidence"][0]
            self.assertEqual("code", evidence["kind"])
            self.assertTrue((FIXTURE / evidence["file"]).is_file())
            self.assertGreaterEqual(evidence["line"], 1)

    def test_api_node_preserves_http_path_as_technical_label(self):
        result = self.scan(FIXTURE)
        api = [n for n in result["nodes"] if n["kind"] == "api"][0]
        self.assertEqual("POST /api/auth/login", api["technical_label"])

    def test_edges_connect_api_to_service_to_repository(self):
        result = self.scan(FIXTURE)
        relations = {(e["source"].split("--")[-1], e["target"].split("--")[-1]) for e in result["edges"]}
        self.assertIn(("login", "LoginService"), relations)
        self.assertIn(("LoginService", "LoginMapper"), relations)

    def test_scan_is_deterministic(self):
        self.assertEqual(self.scan(FIXTURE), self.scan(FIXTURE))

    def test_files_index_maps_path_to_node_ids(self):
        result = self.scan(FIXTURE)
        key = "src/main/java/com/sqi/auth/LoginService.java"
        self.assertIn(key, result["files"])
        self.assertTrue(all(nid in {n["id"] for n in result["nodes"]} for nid in result["files"][key]))

    def test_changed_files_limits_scan_scope(self):
        result = self.scan(FIXTURE, changed_files=["src/main/java/com/sqi/auth/LoginService.java"])
        self.assertEqual({"src/main/java/com/sqi/auth/LoginService.java"}, set(result["files"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_scan -v`
Expected: FAIL — `scan_entrypoints.py` 파일이 없어 `spec_from_file_location`이 `None`을 반환하거나 로드에 실패한다.

- [ ] **Step 4: 스캐너를 구현한다**

`.claude/skills/gx-visualize/scripts/scan_entrypoints.py`:

```python
#!/usr/bin/env python3
"""Extract entrypoint chains (screen -> api -> service -> repository -> table)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

MAPPING_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "ANY",
}

_MAPPING_RE = re.compile(
    r'@(' + "|".join(MAPPING_ANNOTATIONS) + r')\s*\(\s*(?:value\s*=\s*)?"([^"]*)"'
)
_METHOD_RE = re.compile(r"\b(?:public|protected)\s+[\w<>\[\],.\s]+?\s+(\w+)\s*\(")
_CLASS_RE = re.compile(r"\b(?:class|interface)\s+(\w+)")
_FIELD_RE = re.compile(r"\bprivate\s+final\s+(\w+)\s+\w+\s*;")


def node_id(kind: str, rel_path: str, symbol: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", rel_path).strip("-")
    return f"gx-{kind}-{slug}--{symbol}"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _node(kind: str, rel_path: str, symbol: str, label: str, line: int, technical: str | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id(kind, rel_path, symbol),
        "kind": kind,
        "label": label,
        "status": "unknown",
        "evidence": [{"kind": "code", "file": rel_path, "line": line}],
    }
    if technical:
        node["technical_label"] = technical
    return node


def _class_kind(text: str) -> str | None:
    if "@RestController" in text or "@Controller" in text:
        return "controller"
    if "@Service" in text:
        return "service"
    if "@Repository" in text or "@Mapper" in text:
        return "repository"
    return None


def _scan_java(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rel_path = _rel(path, root)
    kind = _class_kind(text)
    if kind is None:
        return [], []

    class_match = _CLASS_RE.search(text)
    if class_match is None:
        return [], []
    class_name = class_match.group(1)
    class_line = text[: class_match.start()].count("\n") + 1

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    if kind == "controller":
        owner_ids: list[str] = []
        for index, line in enumerate(lines):
            mapping = _MAPPING_RE.search(line)
            if mapping is None:
                continue
            verb = MAPPING_ANNOTATIONS[mapping.group(1)]
            http_path = mapping.group(2)
            method_name = ""
            for following in lines[index + 1 : index + 6]:
                method = _METHOD_RE.search(following)
                if method:
                    method_name = method.group(1)
                    break
            if not method_name:
                continue
            node = _node("api", rel_path, method_name, f"{class_name}.{method_name}", index + 1, f"{verb} {http_path}")
            nodes.append(node)
            owner_ids.append(node["id"])
        collaborators = _FIELD_RE.findall(text)
        for owner in owner_ids:
            for collaborator in collaborators:
                edges.append({"source": owner, "target": collaborator, "relation": "calls"})
    else:
        nodes.append(_node(kind, rel_path, class_name, class_name, class_line))
        source = nodes[0]["id"]
        for collaborator in _FIELD_RE.findall(text):
            edges.append({"source": source, "target": collaborator, "relation": "calls"})

    return nodes, edges


def _resolve_edges(nodes: list[dict[str, Any]], raw_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol = {node["id"].split("--")[-1]: node["id"] for node in nodes}
    resolved: dict[str, dict[str, Any]] = {}
    for edge in raw_edges:
        target = by_symbol.get(edge["target"])
        if target is None or target == edge["source"]:
            continue
        edge_id = f"{edge['source']}->{target}"
        resolved[edge_id] = {
            "id": edge_id,
            "source": edge["source"],
            "target": target,
            "relation": edge["relation"],
        }
    return [resolved[key] for key in sorted(resolved)]


def scan(project_root: Path | str, changed_files: list[str] | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    if changed_files is None:
        candidates = sorted(root.rglob("*.java"))
    else:
        candidates = [root / name for name in sorted(changed_files) if (root / name).suffix == ".java"]

    nodes: list[dict[str, Any]] = []
    raw_edges: list[dict[str, Any]] = []
    files: dict[str, list[str]] = {}

    for path in candidates:
        if not path.is_file():
            continue
        file_nodes, file_edges = _scan_java(path, root)
        if not file_nodes:
            continue
        rel_path = _rel(path, root)
        files[rel_path] = sorted(node["id"] for node in file_nodes)
        nodes.extend(file_nodes)
        raw_edges.extend(file_edges)

    nodes.sort(key=lambda node: node["id"])
    return {"nodes": nodes, "edges": _resolve_edges(nodes, raw_edges), "files": dict(sorted(files.items()))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan entrypoint chains into GX visualization candidates.")
    parser.add_argument("project_root")
    parser.add_argument("--changed-file", action="append", dest="changed_files")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = scan(args.project_root, args.changed_files)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_scan -v`
Expected: PASS (7 tests)

- [ ] **Step 6: 기존 테스트 회귀가 없는지 확인한다**

Run: `python -m unittest discover -s tests -p "test_gx_visualize_*.py" 2>&1 | tail -3`
Expected: `FAILED (failures=24)` — Task 1은 이 24건을 건드리지 않는다. 숫자가 24보다 커지면 회귀다.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/scan_entrypoints.py tests/test_gx_arch_scan.py tests/fixtures/gx-arch-java
git commit -m "feat: Java Spring 진입점 체인 스캐너 추가"
```

---

### Task 2: 진입점 스캐너 — JSP·Servlet과 테이블 추출

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/scan_entrypoints.py`
- Create: `tests/fixtures/gx-arch-jsp/WEB-INF/src/com/sqi/board/BoardServlet.java`
- Create: `tests/fixtures/gx-arch-jsp/board/list.jsp`
- Create: `tests/fixtures/gx-arch-jsp/WEB-INF/mappers/BoardMapper.xml`
- Modify: `tests/test_gx_arch_scan.py`

**Interfaces:**
- Consumes: Task 1의 `scan(project_root, changed_files=None)`, `node_id(kind, rel_path, symbol)`
- Produces: 같은 `scan()`이 `screen`·`table` 노드와 `requests`·`reads`·`writes` 관계를 추가로 반환한다.

- [ ] **Step 1: 픽스처 3개를 작성한다**

`tests/fixtures/gx-arch-jsp/board/list.jsp`:

```jsp
<%@ page contentType="text/html; charset=UTF-8" %>
<html>
<body>
<form action="/board/list.do" method="post">
  <input type="submit" value="조회" />
</form>
</body>
</html>
```

`tests/fixtures/gx-arch-jsp/WEB-INF/src/com/sqi/board/BoardServlet.java`:

```java
package com.sqi.board;

import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class BoardServlet extends HttpServlet {
    private final BoardDAO boardDAO = new BoardDAO();

    protected void doPost(HttpServletRequest request, HttpServletResponse response) {
        boardDAO.selectList();
    }
}
```

`tests/fixtures/gx-arch-jsp/WEB-INF/mappers/BoardMapper.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mapper namespace="com.sqi.board.BoardDAO">
  <select id="selectList" resultType="map">
    SELECT BOARD_ID, TITLE FROM TB_BOARD WHERE USE_YN = 'Y'
  </select>
  <insert id="insertBoard">
    INSERT INTO TB_BOARD (TITLE) VALUES (#{title})
  </insert>
</mapper>
```

- [ ] **Step 2: 실패 테스트를 추가한다**

`tests/test_gx_arch_scan.py` 끝에 추가:

```python
JSP_FIXTURE = REPO / "tests" / "fixtures" / "gx-arch-jsp"


class JspLegacyScanTests(unittest.TestCase):
    def setUp(self):
        self.scan = _module().scan

    def test_jsp_file_becomes_screen_node(self):
        result = self.scan(JSP_FIXTURE)
        screens = [n for n in result["nodes"] if n["kind"] == "screen"]
        self.assertEqual(1, len(screens))
        self.assertEqual("board/list.jsp", screens[0]["evidence"][0]["file"])

    def test_servlet_dopost_becomes_api_node(self):
        result = self.scan(JSP_FIXTURE)
        apis = [n for n in result["nodes"] if n["kind"] == "api"]
        self.assertEqual(["doPost"], [n["id"].split("--")[-1] for n in apis])

    def test_screen_form_action_links_to_api(self):
        result = self.scan(JSP_FIXTURE)
        self.assertTrue(any(e["relation"] == "requests" for e in result["edges"]))

    def test_mapper_xml_yields_table_nodes_with_statement_evidence(self):
        result = self.scan(JSP_FIXTURE)
        tables = [n for n in result["nodes"] if n["kind"] == "table"]
        self.assertEqual(["TB_BOARD"], sorted(n["technical_label"] for n in tables))
        self.assertEqual("code", tables[0]["evidence"][0]["kind"])

    def test_select_is_reads_and_insert_is_writes(self):
        result = self.scan(JSP_FIXTURE)
        relations = {e["relation"] for e in result["edges"] if e["target"].startswith("gx-table-")}
        self.assertEqual({"reads", "writes"}, relations)

    def test_sql_body_is_not_copied_into_ir(self):
        result = self.scan(JSP_FIXTURE)
        blob = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("SELECT BOARD_ID", blob)
```

같은 파일 상단 import에 `import json`을 추가한다.

- [ ] **Step 3: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_scan -v`
Expected: FAIL — `JspLegacyScanTests` 6건 실패. `JavaSpringScanTests` 7건은 계속 통과해야 한다.

- [ ] **Step 4: JSP·Servlet·Mapper 추출을 구현한다**

`scan_entrypoints.py`의 `_METHOD_RE` 아래에 정규식을 추가한다:

```python
_SERVLET_RE = re.compile(r"\bextends\s+HttpServlet\b")
_DO_METHOD_RE = re.compile(r"\b(?:protected|public)\s+void\s+(doGet|doPost)\s*\(")
_NEW_FIELD_RE = re.compile(r"\bprivate\s+final\s+(\w+)\s+\w+\s*=\s*new\s+\w+")
_FORM_ACTION_RE = re.compile(r'<form[^>]*\saction\s*=\s*"([^"]+)"', re.IGNORECASE)
_STATEMENT_RE = re.compile(r"<(select|insert|update|delete)\b[^>]*>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)

_WRITE_STATEMENTS = {"insert", "update", "delete"}
```

`_class_kind()` 바로 아래에 추출 함수 세 개를 추가한다:

```python
def _scan_jsp(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    rel_path = _rel(path, root)
    symbol = path.stem
    node = _node("screen", rel_path, symbol, rel_path, 1, rel_path)
    edges = []
    for match in _FORM_ACTION_RE.finditer(text):
        edges.append({"source": node["id"], "target": match.group(1), "relation": "requests"})
    return [node], edges


def _scan_servlet(path: Path, root: Path, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    rel_path = _rel(path, root)
    class_match = _CLASS_RE.search(text)
    class_name = class_match.group(1) if class_match else path.stem
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    collaborators = _FIELD_RE.findall(text) + _NEW_FIELD_RE.findall(text)
    for index, line in enumerate(lines):
        method = _DO_METHOD_RE.search(line)
        if method is None:
            continue
        verb = "GET" if method.group(1) == "doGet" else "POST"
        node = _node(
            "api", rel_path, method.group(1), f"{class_name}.{method.group(1)}", index + 1, f"{verb} {class_name}"
        )
        nodes.append(node)
        for collaborator in collaborators:
            edges.append({"source": node["id"], "target": collaborator, "relation": "calls"})
    return nodes, edges


def _scan_mapper_xml(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    rel_path = _rel(path, root)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for match in _STATEMENT_RE.finditer(text):
        verb = match.group(1).lower()
        relation = "writes" if verb in _WRITE_STATEMENTS else "reads"
        line = text[: match.start()].count("\n") + 1
        for table in _TABLE_RE.findall(match.group(2)):
            name = table.upper()
            node = _node("table", rel_path, name, name, line, name)
            nodes.setdefault(node["id"], node)
            edges.append({"source": rel_path, "target": node["id"], "relation": relation, "resolved": True})
    return [nodes[key] for key in sorted(nodes)], edges
```

`_resolve_edges()`에서 이미 해석된 edge를 통과시키도록 루프 시작부에 다음을 넣는다:

```python
        if edge.get("resolved"):
            target = edge["target"]
        else:
            target = by_symbol.get(edge["target"])
```

그리고 화면 → API 연결을 위해 `by_symbol`을 만든 직후 HTTP 경로 색인을 추가한다:

```python
    by_path = {
        node.get("technical_label", "").split(" ", 1)[-1]: node["id"]
        for node in nodes
        if node["kind"] == "api"
    }
```

`target` 해석 실패 시 `by_path`를 한 번 더 조회한다:

```python
        if target is None:
            target = by_path.get(edge["target"])
```

`scan()`의 후보 수집과 파일 분기를 교체한다:

```python
    suffixes = (".java", ".jsp", ".xml")
    if changed_files is None:
        candidates = sorted(p for p in root.rglob("*") if p.suffix in suffixes)
    else:
        candidates = [root / name for name in sorted(changed_files) if (root / name).suffix in suffixes]
```

```python
        if path.suffix == ".jsp":
            file_nodes, file_edges = _scan_jsp(path, root)
        elif path.suffix == ".xml":
            file_nodes, file_edges = _scan_mapper_xml(path, root)
        else:
            text = path.read_text(encoding="utf-8")
            if _SERVLET_RE.search(text):
                file_nodes, file_edges = _scan_servlet(path, root, text)
            else:
                file_nodes, file_edges = _scan_java(path, root)
```

`_scan_mapper_xml`의 edge `source`는 파일 경로이므로, DAO 노드가 같은 스캔에 있으면 그 노드로 바꿔야 한다. `_resolve_edges` 직전에 보정한다:

```python
    dao_by_stem = {
        node["id"].split("--")[-1]: node["id"] for node in nodes if node["kind"] == "repository"
    }
    for edge in raw_edges:
        if isinstance(edge["source"], str) and edge["source"].endswith(".xml"):
            stem = Path(edge["source"]).stem.replace("Mapper", "DAO")
            edge["source"] = dao_by_stem.get(stem, dao_by_stem.get(Path(edge["source"]).stem, edge["source"]))
```

JSP 스택에서 `*DAO`·`*Service` 클래스를 잡도록 `_class_kind()`에 이름 규칙 분기를 더한다:

```python
    class_match = _CLASS_RE.search(text)
    if class_match:
        name = class_match.group(1)
        if name.endswith(("DAO", "Dao")):
            return "repository"
        if name.endswith(("Service", "ServiceImpl")):
            return "service"
    return None
```

- [ ] **Step 5: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_scan -v`
Expected: PASS (13 tests)

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/scan_entrypoints.py tests/test_gx_arch_scan.py tests/fixtures/gx-arch-jsp
git commit -m "feat: JSP·Servlet 진입점과 MyBatis 테이블 추출 추가"
```

---

### Task 3: 스캔 매니페스트와 증분 병합

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/merge_map.py`
- Test: `tests/test_gx_arch_merge.py`

**Interfaces:**
- Consumes: Task 1·2의 `scan()` 반환 구조 `{"nodes", "edges", "files"}`
- Produces: `fingerprint(path: Path, vcs: str) -> str`
- Produces: `merge(previous_ir: dict, candidate: dict, previous_manifest: dict, removed_files: list[str]) -> tuple[dict, dict]` — `(병합된 IR, 갱신된 manifest)`를 반환한다. IR의 `nodes`·`edges`는 `id` 정렬을 유지하고, 끊긴 edge는 제거한다.
- Produces: `changed_paths(project_root: Path, manifest: dict, vcs: str) -> tuple[list[str], list[str]]` — `(변경·추가된 경로, 삭제된 경로)`

- [ ] **Step 1: 실패 테스트를 작성한다**

`tests/test_gx_arch_merge.py`:

```python
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "merge_map.py"


def _module():
    spec = importlib.util.spec_from_file_location("gx_merge_map", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _node(node_id, kind="service"):
    return {
        "id": node_id,
        "kind": kind,
        "label": node_id,
        "status": "unknown",
        "evidence": [{"kind": "code", "file": "a.java", "line": 1}],
    }


def _edge(source, target):
    return {"id": f"{source}->{target}", "source": source, "target": target, "relation": "calls"}


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_unchanged_nodes_are_preserved(self):
        previous = {"nodes": [_node("n1"), _node("n2")], "edges": [_edge("n1", "n2")]}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}, "b.java": {"fingerprint": "y", "nodes": ["n2"]}}}
        candidate = {"nodes": [_node("n1")], "edges": [], "files": {"a.java": ["n1"]}}
        merged, _ = self.m.merge(previous, candidate, manifest, [])
        self.assertEqual(["n1", "n2"], [n["id"] for n in merged["nodes"]])

    def test_changed_file_nodes_are_replaced_not_duplicated(self):
        previous = {"nodes": [_node("n1")], "edges": []}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}}}
        candidate = {"nodes": [_node("n1b")], "edges": [], "files": {"a.java": ["n1b"]}}
        merged, new_manifest = self.m.merge(previous, candidate, manifest, [])
        self.assertEqual(["n1b"], [n["id"] for n in merged["nodes"]])
        self.assertEqual(["n1b"], new_manifest["files"]["a.java"]["nodes"])

    def test_removed_file_drops_its_nodes(self):
        previous = {"nodes": [_node("n1"), _node("n2")], "edges": []}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}, "b.java": {"fingerprint": "y", "nodes": ["n2"]}}}
        merged, new_manifest = self.m.merge(previous, {"nodes": [], "edges": [], "files": {}}, manifest, ["b.java"])
        self.assertEqual(["n1"], [n["id"] for n in merged["nodes"]])
        self.assertNotIn("b.java", new_manifest["files"])

    def test_dangling_edges_are_removed_with_their_node(self):
        previous = {"nodes": [_node("n1"), _node("n2")], "edges": [_edge("n1", "n2")]}
        manifest = {"files": {"a.java": {"fingerprint": "x", "nodes": ["n1"]}, "b.java": {"fingerprint": "y", "nodes": ["n2"]}}}
        merged, _ = self.m.merge(previous, {"nodes": [], "edges": [], "files": {}}, manifest, ["b.java"])
        self.assertEqual([], merged["edges"])

    def test_merge_output_is_sorted_and_deterministic(self):
        previous = {"nodes": [_node("n2"), _node("n1")], "edges": []}
        manifest = {"files": {}}
        merged, _ = self.m.merge(previous, {"nodes": [], "edges": [], "files": {}}, manifest, [])
        self.assertEqual(["n1", "n2"], [n["id"] for n in merged["nodes"]])


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_non_git_fingerprint_changes_with_content(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_text("one", encoding="utf-8")
            first = self.m.fingerprint(path, "none")
            path.write_text("one-two-three", encoding="utf-8")
            self.assertNotEqual(first, self.m.fingerprint(path, "none"))

    def test_changed_paths_reports_new_and_removed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kept.java").write_text("class A {}", encoding="utf-8")
            manifest = {"files": {"gone.java": {"fingerprint": "stale", "nodes": []}}}
            changed, removed = self.m.changed_paths(root, manifest, "none")
            self.assertIn("kept.java", changed)
            self.assertEqual(["gone.java"], removed)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_merge -v`
Expected: FAIL — `merge_map.py`가 없다.

- [ ] **Step 3: 병합기를 구현한다**

`.claude/skills/gx-visualize/scripts/merge_map.py`:

```python
#!/usr/bin/env python3
"""Fingerprint project files and merge scan candidates into the accumulated map."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

SCAN_SUFFIXES = (".java", ".jsp", ".xml")


def fingerprint(path: Path | str, vcs: str) -> str:
    path = Path(path)
    if vcs == "git":
        result = subprocess.run(
            ["git", "hash-object", str(path)],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    stat = path.stat()
    return f"{stat.st_mtime_ns}-{stat.st_size}"


def changed_paths(project_root: Path | str, manifest: dict[str, Any], vcs: str) -> tuple[list[str], list[str]]:
    root = Path(project_root).resolve()
    recorded = manifest.get("files", {})
    present: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        present[path.relative_to(root).as_posix()] = fingerprint(path, vcs)

    changed = sorted(
        name for name, value in present.items() if recorded.get(name, {}).get("fingerprint") != value
    )
    removed = sorted(name for name in recorded if name not in present)
    return changed, removed


def merge(
    previous_ir: dict[str, Any],
    candidate: dict[str, Any],
    previous_manifest: dict[str, Any],
    removed_files: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    recorded = dict(previous_manifest.get("files", {}))
    touched = set(candidate.get("files", {})) | set(removed_files)

    stale_ids: set[str] = set()
    for name in touched:
        stale_ids.update(recorded.get(name, {}).get("nodes", []))

    nodes = {n["id"]: n for n in previous_ir.get("nodes", []) if n["id"] not in stale_ids}
    for node in candidate.get("nodes", []):
        nodes[node["id"]] = node

    edges = {e["id"]: e for e in previous_ir.get("edges", [])}
    for edge in candidate.get("edges", []):
        edges[edge["id"]] = edge
    edges = {
        key: edge
        for key, edge in edges.items()
        if edge["source"] in nodes and edge["target"] in nodes
    }

    for name in removed_files:
        recorded.pop(name, None)
    for name, node_ids in candidate.get("files", {}).items():
        recorded[name] = {"fingerprint": recorded.get(name, {}).get("fingerprint", ""), "nodes": sorted(node_ids)}

    merged_ir = dict(previous_ir)
    merged_ir["nodes"] = [nodes[key] for key in sorted(nodes)]
    merged_ir["edges"] = [edges[key] for key in sorted(edges)]
    new_manifest = dict(previous_manifest)
    new_manifest["files"] = dict(sorted(recorded.items()))
    return merged_ir, new_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge scan candidates into the accumulated architecture map.")
    parser.add_argument("--previous-ir", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--removed", action="append", default=[])
    parser.add_argument("--out-ir", required=True)
    parser.add_argument("--out-manifest", required=True)
    args = parser.parse_args()

    def _load(name: str, fallback: dict[str, Any]) -> dict[str, Any]:
        path = Path(name)
        if not path.is_file():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))

    previous_ir = _load(args.previous_ir, {"nodes": [], "edges": []})
    manifest = _load(args.manifest, {"schema_version": 1, "files": {}})
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))

    merged_ir, new_manifest = merge(previous_ir, candidate, manifest, args.removed)
    Path(args.out_ir).write_text(json.dumps(merged_ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.out_manifest).write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_merge -v`
Expected: PASS (7 tests)

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/merge_map.py tests/test_gx_arch_merge.py
git commit -m "feat: 스캔 지문 매니페스트와 증분 병합기 추가"
```

---

### Task 4: Archify CLI 시그니처 수리

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/render_archify.py:229-235`
- Modify: `.claude/skills/gx-visualize/references/archify-adapter.md`
- Test: `tests/test_gx_arch_archify.py`

**Interfaces:**
- Consumes: 기존 `render_archify(ir_path, output_dir, archify_command, project_root=None) -> dict[str, str]`
- Produces: `diagram_type(view: str) -> str` — `service` → `architecture`, `sequence` → `sequence`, 그 외는 `architecture`

- [ ] **Step 1: 실패 테스트를 작성한다**

`tests/test_gx_arch_archify.py`:

```python
import importlib.util
import json
import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "render_archify.py"

VALID_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "서비스 구조",
    "nodes": [
        {"id": "n1", "kind": "api", "label": "로그인", "status": "unknown",
         "evidence": [{"kind": "code", "file": "a.java", "line": 1}]}
    ],
    "edges": [],
}


def _module():
    spec = importlib.util.spec_from_file_location("gx_render_archify", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_archify(directory: Path) -> Path:
    """Record argv to argv.log and exit 1 so the adapter falls back."""
    script = directory / "fake_archify.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "log = Path(__file__).with_name('argv.log')\n"
        "with log.open('a', encoding='utf-8') as handle:\n"
        "    handle.write(json.dumps(sys.argv[1:], ensure_ascii=False) + '\\n')\n"
        "sys.exit(1)\n",
        encoding="utf-8",
    )
    return script


class ArchifyCommandTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_service_view_maps_to_architecture_diagram_type(self):
        self.assertEqual("architecture", self.m.diagram_type("service"))

    def test_sequence_view_maps_to_sequence_diagram_type(self):
        self.assertEqual("sequence", self.m.diagram_type("sequence"))

    def test_validate_and_deliver_use_real_archify_signature(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.java").write_text("class A {}", encoding="utf-8")
            ir_path = root / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(root)
            out = root / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=root)

            calls = [json.loads(line) for line in (root / "argv.log").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["validate", "architecture", str(ir_path), "--json"], calls[0])
            self.assertEqual(
                ["deliver", "architecture", str(ir_path), str(out / "service.html"), "--json"], calls[1]
            )

    def test_failed_archify_still_produces_fallback_html(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.java").write_text("class A {}", encoding="utf-8")
            ir_path = root / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            out = root / "out"
            result = self.m.render_archify(ir_path, out, ["python", str(_fake_archify(root))], project_root=root)
            self.assertTrue(Path(result["html_path"]).is_file())
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual("fallback", receipt["status"])
            self.assertNotEqual("archify", receipt["backend"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: FAIL — `diagram_type`이 없고, argv가 `["validate", "<ir>"]` 형태로 기록된다.

- [ ] **Step 3: 명령 조립을 고친다**

`render_archify.py`에 `_view()` 함수 아래 추가:

```python
_DIAGRAM_TYPES = {"service": "architecture", "sequence": "sequence"}


def diagram_type(view: str) -> str:
    return _DIAGRAM_TYPES.get(view, "architecture")
```

229~235행을 교체한다:

```python
    kind = diagram_type(view)
    validate_command = [*command, "validate", kind, str(ir_path), "--json"]
    attempts = [_run(validate_command, "validate", html_path)]

    if attempts[0]["exit_code"] != 0:
        return _fallback(ir_path, output_dir, html_path, receipt_path, attempts, local_receipt, project_root)

    deliver_command = [*command, "deliver", kind, str(ir_path), str(html_path), "--json"]
    attempts.append(_run(deliver_command, "deliver", html_path))
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 어댑터 문서를 실제 시그니처로 고친다**

`references/archify-adapter.md`의 "Archify 명령 계약" 코드 블록을 교체한다:

```text
<archify_command> validate <diagram-type> <ir_path> --json
<archify_command> deliver  <diagram-type> <ir_path> <view.html> --json
```

같은 절에 한 줄 추가한다: "`diagram-type`은 view에서 파생한다 — `service` → `architecture`, `sequence` → `sequence`."

- [ ] **Step 6: 기존 백엔드 테스트 회귀를 확인한다**

Run: `python -m unittest tests.test_gx_visualize_backend -v`
Expected: PASS. 실패하면 그 테스트가 옛 argv를 단언하고 있는 것이므로 실제 시그니처로 갱신한다.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/render_archify.py .claude/skills/gx-visualize/references/archify-adapter.md tests/test_gx_arch_archify.py
git commit -m "fix: Archify CLI 시그니처를 실제 명령 형식으로 수정"
```

---

### Task 5: Archify IR 변환기

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/to_archify.py`
- Create: `docs/reports/2026-09-18-archify-ir-schema.md`
- Modify: `.claude/skills/gx-visualize/scripts/render_archify.py`
- Modify: `tests/test_gx_arch_archify.py`

**Interfaces:**
- Consumes: Task 4의 `diagram_type(view)`
- Produces: `to_archify(ir: dict, kind: str) -> dict` — GX IR을 Archify 입력 문서로 변환한다.

- [x] **Step 1: Archify를 설치하고 실제 IR 스키마를 실측한다** — 오케스트레이터가 2026-09-18에 완료

결과는 [Archify IR 스키마 실측 보고](../../reports/2026-09-18-archify-ir-schema.md)에 있다. **이 문서를 먼저 읽는다.** 아래 Step들의 `REQUIRED_TOP_LEVEL`·`NODE_KEY`·`EDGE_KEY`는 그 실측으로 확정되었다.

확정된 값:

```python
REQUIRED_TOP_LEVEL = {"schema_version", "diagram_type", "meta", "components"}
NODE_KEY = "components"
EDGE_KEY = "connections"
```

호출 경로는 PATH 바이너리가 아니라 `node ~/.agents/skills/archify/bin/archify.mjs`다. 최상위가 `additionalProperties: false`이므로 GX IR을 그대로 넘기면 반드시 실패한다.

- [ ] **Step 2: 기록한 스키마에 맞춘 실패 테스트를 추가한다**

`tests/test_gx_arch_archify.py`에 추가한다. `REQUIRED_TOP_LEVEL`·`NODE_KEY`·`EDGE_KEY`는 Step 1에 이미 확정값으로 주어져 있으니 그대로 모듈 상수로 정의해 쓴다 — 다시 조사하지 않는다.

```python
TO_ARCHIFY = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "to_archify.py"


def _converter():
    spec = importlib.util.spec_from_file_location("gx_to_archify", TO_ARCHIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToArchifyTests(unittest.TestCase):
    def setUp(self):
        self.to_archify = _converter().to_archify

    def test_output_carries_required_top_level_keys(self):
        # REQUIRED_TOP_LEVEL은 docs/reports/2026-09-18-archify-ir-schema.md에 기록한 실제 키 집합이다.
        from_schema = set(REQUIRED_TOP_LEVEL)
        self.assertTrue(from_schema.issubset(set(self.to_archify(VALID_IR, "architecture"))))

    def test_node_ids_are_preserved_verbatim(self):
        out = self.to_archify(VALID_IR, "architecture")
        self.assertEqual(["n1"], [n["id"] for n in out[NODE_KEY]])

    def test_korean_labels_survive_conversion(self):
        out = self.to_archify(VALID_IR, "architecture")
        self.assertEqual("로그인", out[NODE_KEY][0]["label"])

    def test_gx_evidence_maps_to_archify_sources(self):
        out = self.to_archify(VALID_IR, "architecture")
        component = out[NODE_KEY][0]
        self.assertEqual([{"path": "a.java", "line": 1}], component["sources"])

    def test_gx_only_fields_are_not_leaked(self):
        # 최상위가 additionalProperties: false이므로 GX 전용 필드는 반드시 빠져야 한다.
        blob = json.dumps(self.to_archify(VALID_IR, "architecture"), ensure_ascii=False)
        for gx_only in ("evidence", "technical_label", "status", '"view"', "ko-KR"):
            self.assertNotIn(gx_only, blob)

    def test_inferred_evidence_is_dropped(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [{"kind": "inferred"}]
        self.assertNotIn("sources", self.to_archify(ir, "architecture")[NODE_KEY][0])

    def test_sources_are_capped_at_three(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [
            {"kind": "code", "file": f"f{n}.java", "line": n} for n in range(1, 6)
        ]
        self.assertEqual(3, len(self.to_archify(ir, "architecture")[NODE_KEY][0]["sources"]))

    def test_conversion_is_deterministic(self):
        self.assertEqual(self.to_archify(VALID_IR, "architecture"), self.to_archify(VALID_IR, "architecture"))
```

- [ ] **Step 3: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: FAIL — `to_archify.py`가 없다.

- [ ] **Step 4: 변환기를 구현한다**

`to_archify.py`를 작성한다. 노드·엣지 키 이름과 최상위 필드는 Step 1에서 기록한 스키마를 따르고, 아래 규칙을 지킨다.

- `id`·`label`은 GX IR 값을 그대로 옮긴다. 한국어를 변형하지 않는다.
- `technical_label`은 `sublabel`로 옮긴다.
- **`evidence` → `component.sources`로 매핑한다.** `{kind:"code", file, line}` → `{path: file, line: line}`. 최대 3개까지만 싣고 초과분은 버린다. `kind: "inferred"` 근거는 `path`가 없으므로 넘기지 않는다. (실측 보고 §3.3 — 초기 계획의 "싣지 않는다"는 정정되었다.)
- `sources`를 실으면 Archify가 `meta.repository{url, revision}`과 실행 시 `--repo-root`를 요구하고 경로 존재를 실제로 검증한다. `revision`은 40자 hex여야 한다. **비-git 프로젝트이거나 40자 SHA를 얻을 수 없으면 `sources`를 싣지 않는다** — 그래도 렌더는 성공한다.
- 배치는 `layout: {mode: "grid", cols: 5, ...}`와 component별 `row`/`col`을 쓴다. `pos`/`size`는 쓰지 않는다. `col`은 실측 보고 §3.2의 표를 따른다.
- `meta.locale`은 `en`으로 둔다. enum이 `["en","zh-CN"]`이라 한국어를 넣을 수 없다 — 라벨의 한국어는 자유 문자열로 정상 렌더된다.
- `status`·`view`·`locale: ko-KR` 등 GX 전용 필드는 넘기지 않는다. 최상위가 `additionalProperties: false`라 거부된다.
- 노드·엣지는 `id` 정렬을 유지한다.
- `kind` → `type` 매핑표를 모듈 상단 상수로 둔다. `type` enum은 `frontend|backend|database|cloud|security|messagebus|external`이다.

- [ ] **Step 5: render_archify가 변환기를 쓰도록 연결한다**

`render_archify.py`에서 validate 호출 전에 변환 산출물을 임시 파일로 쓰고, 그 경로를 Archify에 넘긴다. GX IR 원본 경로는 영수증에 계속 기록한다.

```python
    archify_payload = output_dir / f"{view}.archify.json"
    archify_payload.write_text(
        json.dumps(_to_archify_module().to_archify(json.loads(ir_path.read_text(encoding="utf-8")), kind),
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

이후 `validate_command`·`deliver_command`의 입력 경로를 `str(archify_payload)`로 바꾸고, Task 4의 argv 테스트 기대값도 같은 경로로 갱신한다.

- [ ] **Step 6: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: PASS

- [ ] **Step 7: 실제 Archify로 종단 확인한다**

```bash
python .claude/skills/gx-visualize/scripts/render_archify.py tests/fixtures/gx-trace.valid.json /tmp/gx-archify-out --command archify
```

영수증의 `status`가 `valid`이고 `backend`가 `archify`인지 확인한다. 실패하면 영수증의 `attempts`에 남은 Archify 진단을 읽고 변환기를 고친다. **가짜 실행 파일 결과로 이 확인을 대체하지 않는다.**

- [ ] **Step 8: 커밋**

```bash
git add .claude/skills/gx-visualize/scripts/to_archify.py .claude/skills/gx-visualize/scripts/render_archify.py tests/test_gx_arch_archify.py docs/reports/2026-09-18-archify-ir-schema.md
git commit -m "feat: GX IR을 Archify 입력으로 변환하는 어댑터 추가"
```

---

### Task 6: service·sequence 뷰 승격과 누적 맵 계약

**Files:**
- Modify: `.claude/skills/gx-visualize/SKILL.md`
- Create: `.claude/skills/gx-visualize/references/entrypoint-rules.md`
- Modify: `.claude/skills/gx-visualize/references/gx-mapping.md`
- Test: `tests/test_gx_visualize_skill_contract.py`

**Interfaces:**
- Consumes: Task 1~3의 `scan_entrypoints.py`, `merge_map.py`
- Produces: 스킬 호출 계약 `gx-visualize <view> [--scope session|all] [--map-dir <path>] [--domain <name>]`

- [ ] **Step 1: 실패 테스트를 추가한다**

`tests/test_gx_visualize_skill_contract.py`에 추가한다:

```python
class AccumulatedMapContractTests(unittest.TestCase):
    def setUp(self):
        self.skill = (
            REPO / ".claude" / "skills" / "gx-visualize" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_scope_flag_is_documented(self):
        self.assertIn("--scope session|all", self.skill)

    def test_map_dir_default_is_docs_architecture(self):
        self.assertIn("docs/architecture/", self.skill)

    def test_service_and_sequence_are_no_longer_deferred(self):
        self.assertNotIn("계약 지원 뷰", self.skill)

    def test_skill_links_entrypoint_rules(self):
        self.assertIn("references/entrypoint-rules.md", self.skill)
        self.assertTrue((REPO / ".claude" / "skills" / "gx-visualize" / "references" / "entrypoint-rules.md").is_file())

    def test_korean_label_enrichment_is_required(self):
        self.assertIn("context/", self.skill)
        self.assertIn("한국어 라벨", self.skill)

    def test_empty_scan_must_not_write_empty_ir(self):
        self.assertIn("0개 노드", self.skill)

    def test_session_scope_writes_to_dev_dir(self):
        self.assertIn("`session` | `${DEV_DIR}/visual/`", self.skill)

    def test_all_scope_writes_to_map_dir(self):
        self.assertIn("`all` | `${MAP_DIR}/`", self.skill)

    def test_session_html_carries_snapshot_banner(self):
        self.assertIn("스냅샷 배너", self.skill)

    def test_session_and_accumulated_outputs_are_not_mixed(self):
        self.assertIn("한 폴더에 섞지 않는다", self.skill)
```

`REPO` 상수가 없으면 파일 상단에 `REPO = Path(__file__).resolve().parents[1]`을 추가한다.

- [ ] **Step 2: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_visualize_skill_contract -v`
Expected: FAIL — 새 6건 실패, 기존 케이스는 통과 유지.

- [ ] **Step 3: entrypoint-rules.md를 작성한다**

설계서 §5.4의 추출 규칙 표와 `relation` 값, "체인 밖 클래스는 노드로 만들지 않는다", "같은 파일 안의 타입 참조로만 호출 관계를 판정한다"를 그대로 옮긴다.

- [ ] **Step 4: SKILL.md를 갱신한다**

- 호출 계약 줄에 `[--scope session|all] [--map-dir <path>] [--domain <name>]`을 추가한다.
- 뷰 라우터 표에서 `service`·`sequence`의 "지원 범위" 칸을 `계약 지원`에서 `1차 필수`로 바꾸고, "`service`와 `sequence`는 계약 지원 뷰다" 문단을 삭제한다.
- 실행 절차에 누적 맵 경로를 추가한다:

```markdown
## 누적 아키텍처 맵

`--scope`가 출력 위치를 가른다. 파일명은 기존 `{view}.json`·`{view}.html` 규칙 그대로다.

| scope | 위치 | 성격 |
|---|---|---|
| `session` | `${DEV_DIR}/visual/` | 그 시점 스냅샷, 갱신하지 않는다 |
| `all` | `${MAP_DIR}/` (기본 `docs/architecture/`, `--map-dir`로 변경) | 항상 최신, 증분 갱신 |

두 산출물을 **한 폴더에 섞지 않는다**. 세션 출력은 갱신되지 않으므로 누적 맵과 같은 위치에 두면 낡은 그림을 최신으로 오인하게 된다.

`--scope session` HTML 상단에는 **스냅샷 배너**를 넣는다 — 생성 시각과 `git rev-parse --short HEAD` 결과, 그리고 "이 그림은 해당 시점의 스냅샷이며 갱신되지 않습니다". `--scope all`에는 넣지 않는다.

1. `scripts/merge_map.py`의 `changed_paths`로 변경·삭제 파일을 구한다. `--scope session`이면 이번 사이클 diff의 파일로 제한하고 병합 없이 그 결과만 렌더링한다.
2. `scripts/scan_entrypoints.py`로 그 파일들만 스캔한다. 매니페스트가 없으면 전체를 스캔하고, 이것이 최초 전체 스캔임을 사용자에게 먼저 알린다.
3. 스캔 결과의 `label`은 기술 식별자다. `context/{도메인}/glossary.md`와 `${DEV_DIR}/design.md`를 읽어 **한국어 라벨**로 바꾼다. API path·테이블명·클래스명은 `technical_label`에 원문 그대로 보존한다. 근거가 없으면 기술 식별자를 그대로 둔다 — 도메인 용어를 지어내지 않는다.
4. `--scope all`이면 `scripts/merge_map.py`로 이전 IR과 병합한다. `--scope session`은 병합하지 않는다 — 스냅샷이므로 누적 IR과 매니페스트를 건드리지 않는다.
5. `scripts/validate_ir.py`로 검증한다. **실패하면 이전 `${MAP_DIR}/service.ir.json`을 덮어쓰지 않는다.**
6. 커밋 대상을 보고한다 — `--scope all`은 `${MAP_DIR}/service.ir.json`·`service.html`·`.scan-manifest.json`, `--scope session`은 `${DEV_DIR}/visual/service.json`·`service.html`. 영수증은 어느 쪽도 커밋하지 않는다.

스캔이 **0개 노드**를 반환하면 빈 IR을 쓰지 않는다. `missing_inputs`에 언어 감지 실패를 기록하고 중단한다.
```

- [ ] **Step 5: gx-mapping.md에 코드 근거 매핑을 추가한다**

기존 표에 행을 더한다: `진입점 체인 스캔 | service/sequence 뷰의 screen·api·service·repository·table 노드와 code 근거`

- [ ] **Step 6: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_visualize_skill_contract -v`
Expected: PASS

- [ ] **Step 7: 커밋 (1단위)**

```bash
git add .claude/skills/gx-visualize/SKILL.md .claude/skills/gx-visualize/references tests/test_gx_visualize_skill_contract.py
git commit -m "feat: service·sequence 뷰를 누적 아키텍처 맵으로 승격"
```

---

#### 2단위: 한국어 라벨 적합 (Task 5에서 이월)

여기부터는 문서가 아니라 `to_archify.py`의 계산 로직이다. 1단위와 파일도 성격도 다르므로 별도로 커밋한다.

Task 5의 구현자가 Archify의 `renderers/shared/render-architecture.mjs`를 읽어 확인한 사실이다. **정확한 수치와 심볼은 [Task 5 보고서](../../../.superpowers/sdd/2026-09-18-gx-visualize-architecture-map/task-5-report.md)에서 확인하고 시작한다** — 아래는 요지다.

- 컴포넌트 박스 크기의 기본값은 하드코딩 **120×60**이며, 문서의 `layout.cellW/cellH`와 **무관하다**. 그 둘은 그리드 칸 간격만 정하고 박스 크기는 건드리지 않는다.
- `label`에는 shrink-to-fit이 **없다**. `sublabel`과 `tag`에는 있다.
- 적합 판정은 `textUnits(label) * 6.6 <= width + 8`이고 **한글은 문자당 2 units**다. 즉 `label`이 한글 약 **9자**에서 넘친다.

`"에너지 사용량 조회 API"`가 11자다. 그대로 두면 전형적인 한국어 라벨이 Archify 검증에 걸려 조용히 mermaid로 떨어진다 — 한국어 우선 플러그인에서 가장 나쁜 실패 방식이다.

- [ ] **Step 8: 실패 테스트를 추가한다**

`tests/test_gx_arch_archify.py`에 추가한다. 실제 한국어 라벨을 쓴다.

```python
def test_long_korean_label_gets_explicit_size(self):
    # "에너지 사용량 조회 API" = 11자 → 기본 120px를 넘는다
    ir = _ir_with_label("에너지 사용량 조회 API")
    component = self.to_archify(ir, "architecture")[NODE_KEY][0]
    self.assertIn("size", component)
    width = component["size"][0]
    self.assertGreaterEqual(width + 8, _text_units("에너지 사용량 조회 API") * 6.6)

def test_short_label_omits_size(self):
    # 기본 박스에 들어가면 size를 내보내지 않는다 — 불필요한 필드를 만들지 않는다
    self.assertNotIn("size", self.to_archify(_ir_with_label("로그인"), "architecture")[NODE_KEY][0])

def test_sublabel_length_does_not_force_size(self):
    # sublabel에는 shrink-to-fit이 있으므로 길어도 size를 강제하지 않는다
    ir = _ir_with_label("로그인", technical="POST /api/v1/authentication/login/session")
    self.assertNotIn("size", self.to_archify(ir, "architecture")[NODE_KEY][0])

def test_size_is_deterministic(self):
    ir = _ir_with_label("에너지 사용량 조회 API")
    self.assertEqual(self.to_archify(ir, "architecture"), self.to_archify(ir, "architecture"))
```

- [ ] **Step 9: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_archify -v`
Expected: FAIL — 현재 `to_archify`는 `size`를 내보내지 않는다.

- [ ] **Step 10: 적합 계산을 구현한다**

`to_archify.py`에 Archify **자신의 공식**을 옮긴다. 추측한 상수를 쓰지 않고, 모듈 상단 주석에 출처(`render-architecture.mjs`의 해당 심볼)를 적는다.

- `text_units(s)`: 한글·전각은 2, 그 외는 1.
- 필요한 최소 너비를 그 식에서 역산하고, **기본 120×60에 들어가면 `size`를 생략**한다. 들어가지 않을 때만 내보낸다.
- 높이는 기본값을 유지한다 — 라벨은 한 줄이고 넘치는 축은 너비뿐이다.
- `sublabel`·`tag`는 계산에 넣지 않는다. 그 둘은 Archify가 줄여서 맞춘다.

- [ ] **Step 11: 실제 Archify로 확인한다**

한국어 라벨이 긴 5계층 사슬 IR을 만들어 `render_archify.py`로 종단 실행한다. receipt의 `status`가 `valid`이고 `backend`가 `archify`여야 한다 — 폴백이면 적합 계산이 틀린 것이다. 생성된 HTML을 열어 **라벨이 박스 안에 들어가는지 눈으로 확인**하고 본 것을 보고한다. `gapX`·`cellW`는 조정하지 않는다.

- [ ] **Step 12: 커밋 (2단위)**

```bash
git add .claude/skills/gx-visualize/scripts/to_archify.py tests/test_gx_arch_archify.py
git commit -m "fix: 한국어 라벨이 Archify 박스를 넘칠 때 크기를 명시한다"
```

---

### Task 7: phase-complete 시각화 제안 게이트

**Files:**
- Modify: `.claude/skills/gx-dev/phases/phase-complete.md` (Step 5와 Step 6 사이)
- Modify: `.claude/skills/gx-tdd/phases/phase-complete.md` (Step 5와 Step 6 사이)
- Test: `tests/test_gx_arch_pipeline.py`

**Interfaces:**
- Consumes: Task 6의 호출 계약 `gx-visualize service --scope session|all`

- [ ] **Step 1: 실패 테스트를 작성한다**

`tests/test_gx_arch_pipeline.py`:

```python
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHASES = [
    REPO / ".claude" / "skills" / "gx-dev" / "phases" / "phase-complete.md",
    REPO / ".claude" / "skills" / "gx-tdd" / "phases" / "phase-complete.md",
]


class CompletionGateTests(unittest.TestCase):
    def _text(self, path):
        return path.read_text(encoding="utf-8")

    def test_both_pipelines_have_a_visualization_step(self):
        for path in PHASES:
            self.assertIn("Step 5.5", self._text(path), path.name)

    def test_gate_offers_session_and_full_scope(self):
        for path in PHASES:
            text = self._text(path)
            self.assertIn("--scope session", text, path.name)
            self.assertIn("--scope all", text, path.name)

    def test_headless_sessions_skip_without_asking(self):
        for path in PHASES:
            text = self._text(path)
            self.assertIn("ralph.lock", text, path.name)
            self.assertIn("strict no-op", text, path.name)

    def test_gate_never_fails_commit_or_pr(self):
        for path in PHASES:
            self.assertIn("커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다", self._text(path), path.name)

    def test_first_full_scan_warns_before_running(self):
        for path in PHASES:
            self.assertIn(".scan-manifest.json", self._text(path), path.name)

    def test_step_order_places_gate_between_5_and_6(self):
        for path in PHASES:
            text = self._text(path)
            self.assertLess(text.index("## Step 5.5"), text.index("## Step 6"), path.name)
            self.assertLess(text.index("## Step 5:"), text.index("## Step 5.5"), path.name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_pipeline -v`
Expected: FAIL (6 tests) — 두 phase-complete 모두 Step 5.5가 없다.

- [ ] **Step 3: 두 phase-complete에 같은 절을 삽입한다**

`## Step 5: 진행 상태 완료` 절의 끝과 `## Step 6: 다음 단계` 사이에 삽입한다. 두 파일에 동일 내용을 넣는다.

```markdown
## Step 5.5: 구현 구조 시각화 제안

**헤드리스 판정 먼저**: `${DEV_DIR}/ralph.lock`이 존재하거나 state.md의 `pipeline`이 `gx-ralph`이면 이 절 전체를 **strict no-op**으로 건너뛴다. 질문하지 않고 기존 완료 출력을 바꾸지 않는다 — 응답할 사용자가 없다.

대화형 세션이면 아래를 질문한다.

```
AskUserQuestion(
  questions: [{
    header: "구조 시각화",
    question: "이번 사이클에서 구현된 구조를 시각화할까요?",
    multiSelect: false,
    options: [
      { label: "전체 갱신 + 이번 반영", description: "누적 아키텍처 맵을 증분 갱신합니다 — docs/architecture/에 저장 (gx-visualize service --scope all)" },
      { label: "이번 세션분만", description: "이번 사이클이 변경한 파일의 체인만 그립니다 — .dev/{slug}/visual/에 스냅샷 저장 (gx-visualize service --scope session)" },
      { label: "아니요", description: "시각화하지 않고 완료합니다" }
    ]
  }]
)
```

- **전체 갱신** → `${MAP_DIR}/.scan-manifest.json`(기본 `docs/architecture/`)이 없으면 최초 전체 스캔이라 오래 걸린다고 먼저 알리고 재확인한 뒤, `oh-my-gx:gx-visualize`를 `service --scope all`로 호출한다.
- **이번 세션분만** → `oh-my-gx:gx-visualize`를 `service --scope session`으로 호출하고 이번 사이클의 변경 파일 목록을 전달한다.
- **아니요** → 건너뛴다.

호출 결과의 `view`·`backend`·`html_path`·`validation_status`·`missing_inputs`를 그대로 보고한다. 검증된 HTML이 없으면 `visualization_status: failed`로 보고하고 경로를 성공처럼 제시하지 않는다.

이 절의 실패·누락·fallback은 **커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다.** Step 1~2가 이미 실패했다면 시각화 성공으로 그 실패를 덮지 않는다.
```

**하네스 적응**: 이 절은 두 파이프라인의 적응 표가 이미 규정한 매핑만 쓴다 — `AskUserQuestion` → `request_user_input`, `Skill(skill: …)` → 해당 `SKILL.md`를 읽어 절차 수행. **새 적응 절을 만들지 않는다.**

다만 이 게이트에는 다른 게이트와 구별되는 성질이 하나 있으니 절 본문에 명시한다. 기존 적응 표의 "승인 없이 다음 단계로 넘어가지 않는다"는 **진행을 막는 게이트**에 대한 규정이고, 이 절은 막지 않는 **제안**이다. 따라서 두 상황을 섞지 않는다.

- **구조화된 질문 도구가 없는 대화형 세션** → 자연어로 묻고 실제 답을 기다린다. 도구가 없다는 이유로 건너뛰지 않는다 — 그러면 Codex에서 시각화가 영원히 제안되지 않는다.
- **응답할 사용자가 없는 헤드리스 세션**(`ralph.lock` 존재 또는 `pipeline: gx-ralph`) → strict no-op.

"질문 도구가 없음"과 "사용자가 없음"은 다른 조건이다. 전자를 후자로 취급하지 않는다.

- [ ] **Step 4: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_pipeline -v`
Expected: PASS (6 tests)

- [ ] **Step 5: 기존 라우팅 테스트 상태를 확인한다**

Run: `python -m unittest tests.test_gx_visualize_routing -v`
Expected: 일부 통과로 전환. 남은 실패는 Task 8에서 README·index.html과 함께 해소한다. 실패 수가 늘어나면 회귀다.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/gx-dev/phases/phase-complete.md .claude/skills/gx-tdd/phases/phase-complete.md tests/test_gx_arch_pipeline.py
git commit -m "feat: complete 단계에 구현 구조 시각화 제안 게이트 추가"
```

---

### Task 8: Archify 자동 설치와 폴백 정직성

**Files:**
- Modify: `.claude/skills/gx-visualize/scripts/detect_backend.py`
- Modify: `.claude/skills/gx-visualize/references/archify-adapter.md`
- Modify: `.claude/skills/gx-visualize/SKILL.md`
- Modify: `.claude/skills/gx-visualize/scripts/render_fallback.py`
- Test: `tests/test_gx_arch_install.py`

**Interfaces:**
- Consumes: Task 4의 `diagram_type(view)`, Task 5의 `to_archify(ir, kind)`
- Produces: `ensure_archify(command=None) -> dict` — `{"available": bool, "command": list[str] | None, "attempts": [...]}`. 탐지 실패 시 1회 설치를 시도하고 재탐지한다.

이 태스크는 사용자 결정을 구현한다: **archify가 없으면 묻지 않고 자동 설치한다.** 이 결정은 기존 계약 세 곳을 뒤집으므로 함께 고쳐야 한다.

- [ ] **Step 1: 실패 테스트를 작성한다**

`tests/test_gx_arch_install.py`에 다음을 담는다. 실제 네트워크를 쓰지 않도록 설치 명령 실행을 가짜 실행 파일로 대체한다.

```python
def test_absent_archify_triggers_one_install_attempt(self):
    # 탐지 실패 → 설치 1회 시도 → 재탐지. attempts에 설치 시도가 기록된다.

def test_install_is_attempted_only_once_per_failure(self):
    # 설치가 실패하면 같은 실행에서 재시도하지 않는다.

def test_install_failure_falls_back_without_raising(self):
    # 네트워크 차단을 흉내낸 0이 아닌 종료 코드에도 예외가 아니라 available=False를 반환한다.

def test_exit_code_zero_with_promptscript_warning_is_not_success(self):
    # `npx skills add`는 PromptScript 실패를 출력하면서 exit 0으로 끝난다.
    # 성공 판정은 exit code가 아니라 bin/archify.mjs 존재로 한다.

def test_fallback_html_states_no_diagram_was_produced(self):
    # 폴백 HTML에 "다이어그램이 생성되지 않았습니다"와 설치 안내가 들어간다.
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_install -v`
Expected: FAIL — `ensure_archify`가 없다.

- [ ] **Step 3: `ensure_archify()`를 구현한다**

`detect_backend.py`에 추가한다. 실측 보고(`docs/reports/2026-09-18-archify-ir-schema.md` §1)의 사실을 따른다.

- 탐지 대상은 PATH의 `archify`가 아니라 `~/.agents/skills/archify/bin/archify.mjs`다. `~/.claude/skills/archify`는 그 심링크이므로 둘 중 먼저 발견된 실재 파일을 쓴다.
- 없으면 `npx -y skills add tt-a1i/archify -g`를 `shell=False`로 1회 실행한다.
- **exit code로 성공을 판정하지 않는다.** 이 명령은 PromptScript 실패 2건을 출력하면서 exit 0으로 끝난다. 성공은 `bin/archify.mjs`가 실재하고 `node bin/archify.mjs doctor`가 성공하는 것으로 판정한다.
- 실패하면 예외를 던지지 않고 `available: False`를 반환하며, 시도한 argv·종료 코드·stderr를 `attempts`에 남긴다.
- 같은 실행 안에서 설치를 두 번 시도하지 않는다.

- [ ] **Step 4: 폴백 문구를 정직하게 고친다**

`render_fallback.py:167`의 "Mermaid를 실행할 수 없어도 아래의 정적 노드 목록과 관계 표에서 같은 내용을 확인할 수 있습니다"를 교체한다. 표와 그림은 같은 내용이 아니다 — 현재 mermaid 백엔드는 소스를 `<pre>`에 넣을 뿐 렌더하지 않는다.

```
다이어그램은 생성되지 않았습니다. 아래는 같은 IR의 노드 목록과 관계 표입니다.
그림을 보려면 Archify가 필요합니다: npx -y skills add tt-a1i/archify -g
```

- [ ] **Step 5: 뒤집힌 계약 네 곳을 고친다**

1. `references/archify-adapter.md` 첫 문단 "어댑터는 패키지를 설치하거나 네트워크에 접속하지 않으며" — 자동 설치 정책으로 교체하고 1회 시도·exit code 불신·실패 시 폴백을 명시한다.
2. `SKILL.md` 실행 절차의 "설치·업데이트·네트워크 접근은 하지 않는다" — 같은 방식으로 교체한다.
3. `SKILL.md` 출력 계약에 `backend != archify`일 때 그림 부재를 보고하도록 한 줄 추가한다.
4. **`references/codex-runtime.md`의 "경로와 실행" 절** — 다음 한 문장이 새 정책을 세 군데에서 동시에 위반한다.

   > 현재 PATH와 사용자가 명시한 override만 probe한다. 패키지를 자동 설치하거나 외부 네트워크를 호출하거나 홈 디렉터리를 탐색하지 않는다.

   - **자동 설치 금지** → 이제 설치한다
   - **네트워크 호출 금지** → `npx`가 네트워크를 쓴다
   - **홈 디렉터리 탐색 금지** → 실제 설치 위치가 `~/.agents/skills/archify`이므로 홈을 봐야 한다. PATH에는 바이너리가 아예 없어 PATH probing만으로는 영원히 찾지 못한다

   교체 시 다음을 명시한다: 탐지 대상은 `~/.agents/skills/archify/bin/archify.mjs`와 `~/.claude/skills/archify`(심링크)이며 그 밖의 홈 경로를 뒤지지 않는다. 설치는 1회만 시도한다. **Codex에서 명령 실행이 샌드박스·승인으로 막히면 실패가 아니라 폴백으로 처리하고 시도 기록을 receipt에 남긴다.** 고정 절대경로를 산출물에 저장하지 않는다.

- [ ] **Step 6: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_install -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/gx-visualize tests/test_gx_arch_install.py
git commit -m "feat: Archify 자동 설치와 폴백 부재 표시를 추가"
```

---

### Task 9: 문서·버전·Codex 동기화

**Files:**
- Modify: `README.md`, `index.html`, `docs/gx-visualize-guide.md`, `tests/codex-smoke.md`
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 6·7의 최종 호출 계약과 게이트 문구

- [ ] **Step 1: 남은 RED 테스트가 무엇을 요구하는지 확인한다**

Run: `python -m unittest discover -s tests -p "test_gx_visualize_*.py" -v 2>&1 | grep -E "^(FAIL|ERROR):"`

`test_gx_visualize_docs`·`test_gx_visualize_guide`의 실패 메시지가 요구하는 정확한 문자열을 목록으로 적는다. 이 문자열들이 이번 Task의 작업 지시다.

- [ ] **Step 2: 버전을 1.34.0으로 올린다**

`origin/main`이 이미 1.33.0이므로 1.34.0을 쓴다. 네 곳을 동일하게 바꾼다.

```bash
python - <<'PY'
import io, json, re
from pathlib import Path
for name in [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]:
    p = Path(name)
    d = json.loads(p.read_text(encoding="utf-8"))
    d["version"] = "1.34.0"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
p = Path(".claude-plugin/marketplace.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["plugins"][0]["version"] = "1.34.0"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
```

`CHANGELOG.md` 맨 위에 `## 1.34.0` 절을 추가하고 누적 아키텍처 맵, Archify 시그니처 수정, complete 제안 게이트를 항목으로 적는다.

- [ ] **Step 3: README와 index.html에 누적 맵을 문서화한다**

Step 1에서 적은 요구 문자열(`gx-visualize`, `impact`, `.dev/{branch-slug}/visual/`, `docs/gx-visualize-guide.md` 등)을 모두 포함하도록 쓴다. index.html은 스킬 수 표기를 현재 카탈로그에 맞추고 태그 균형을 확인한다.

- [ ] **Step 4: docs/gx-visualize-guide.md에 누적 맵 절을 추가한다**

`--scope` 선택, 최초 전체 스캔 경고, 비-git 프로젝트의 mtime 지문을 설명한다. **산출물은 도메인별이다** — `${MAP_DIR}/{domain}.ir.json`·`{domain}.html`과 공유 `.scan-manifest.json`. `SKILL.md`의 "도메인 분할" 절이 정본이므로 그대로 옮기고 새로 지어내지 마라.

특히 **도메인마다 개별 판정**한다는 사실을 독자가 놓치지 않게 쓴다 — 한 저장소 안에서 어떤 도메인은 그림이 나오고 어떤 도메인은 표로 떨어지는 것이 정상이다. 실제 GX 프로젝트 측정값(도메인 8개 중 6개 통과)을 예로 들면 독자가 이 동작을 오해하지 않는다.

**Archify 자동 설치 정책은 이미 이 파일에 있다** (Task 8이 넣었다). 다시 쓰지 말고 모순되게 고치지도 마라 — 확인만 하고 넘어간다.

- [ ] **Step 5: codex-smoke.md에 시나리오를 추가한다**

`tests/codex-smoke.md`에는 현재 `visualize` 언급이 **0건**이다. 아래 다섯 시나리오를 `## 시각화` 절로 추가한다. 앞의 셋은 기능 표면이고, 뒤의 둘은 Codex에서만 드러나는 위험이다.

1. **누적 맵 생성** — `gx-visualize service --scope all`이 `docs/architecture/`에 **도메인별** IR·HTML과 공유 매니페스트를 만들고, 도메인마다 개별로 판정한다(일부 통과·일부 폴백이 정상).
2. **Archify 미설치 폴백** — 설치가 불가능한 환경에서 표가 생성되고 **그림 부재가 명시**된다.
3. **시각화 실패의 진실한 보고** — 모든 백엔드 실패 시 `html_path: null`과 재실행 명령이 반환되고 stale HTML이 남지 않는다.
4. **complete 단계 질문 게이트의 도구 대응** — Task 7이 `AskUserQuestion`을 쓴다. Codex에서 그 자리에 실제로 제공되는 질문 도구로 옮겨지고 **실제 사용자 응답을 기다리는지** 확인한다. 동기 질문 도구가 현재 모드에 없으면 어떻게 처리되는지 기록한다.
5. **자동 설치가 샌드박스·승인으로 막힌 경우** — Task 8의 `npx` 실행이 Codex에서 차단될 때 예외가 아니라 폴백으로 처리되고 시도 기록이 receipt에 남는지 확인한다.

**실제 Codex 세션에서 실행하지 않은 항목은 미실행으로 표시한다.** 로컬 mock·유닛 테스트 결과를 실제 설치·모델·훅 동작의 근거로 적지 않는다.

- [ ] **Step 6: Codex 리소스를 동기화하고 린트를 돌린다**

```bash
python scripts/sync-codex-resources.py --check
bash scripts/lint-consistency.sh
```

`--check`가 실패하면 `python scripts/sync-codex-resources.py`로 동기화한 뒤 다시 검사한다. 린트는 약 4분 걸리므로 Bash timeout을 600000으로 설정한다.

- [ ] **Step 7: 전체 테스트를 돌려 0 실패를 확인한다**

```bash
python -m unittest discover -s tests -p "test_gx_*.py" -v 2>&1 | tail -5
python -m unittest discover -s tests -p "test_codex_*.py" -v 2>&1 | tail -5
bash scripts/hook-tests.sh
```

Expected: `test_gx_visualize_routing`의 **7건만 실패로 남고 그 수가 늘지 않는다.** 나머지는 전부 `OK`.

그 7건은 `--visualize` 플래그 통합 배선(gx-dev SKILL.md의 플래그·한국어 트리거 정규화, phase-setup의 `visualize-view` resume 지속, phase-review의 "Step 1.5")을 요구하며 **이 계획의 범위가 아니다.** 이 브랜치의 기준선 보존 커밋이 "통합 배선 24건은 후속 계획의 RED 테스트로 의도적 미포함"이라고 명시했고, 수용 기준 17개 어디에도 없다. **고치려 들지 마라.**

- [ ] **Step 8: 커밋**

변경한 파일만 명시적으로 스테이징한다 (`git add -A`를 쓰지 마라 — 다른 세션의 잔여물이 섞인다).

```bash
git add README.md index.html docs/gx-visualize-guide.md tests/codex-smoke.md
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json CHANGELOG.md
git commit -m "docs: 누적 아키텍처 맵 문서화와 1.34.0 버전 갱신"
```

---

### Task 10: 도메인 분할과 변환기 결함 2건

설계서 §5.7·§5.7.1을 구현한다. 실제 GX 프로젝트 측정으로 확정된 작업이며, 세 가지 모두 해법이 실측으로 검증돼 있다.

**Files:**
- Create: `.claude/skills/gx-visualize/scripts/split_domains.py`
- Modify: `.claude/skills/gx-visualize/scripts/to_archify.py`
- Modify: `.claude/skills/gx-visualize/SKILL.md`
- Modify: `.claude/skills/gx-visualize/references/entrypoint-rules.md`
- Test: `tests/test_gx_arch_split.py`, `tests/test_gx_arch_archify.py`

**Interfaces:**
- Consumes: Task 1~3의 IR, Task 5의 `to_archify(ir, kind, repository=None)`
- Produces: `domain_of(path) -> str | None`, `split_by_domain(ir) -> dict[str, dict]`

- [ ] **Step 1: 도메인 추출 실패 테스트를 쓴다**

`tests/test_gx_arch_split.py`. 경로는 실제 GX 프로젝트에서 측정한 두 형태를 쓴다.

```python
LAYER_DIRS = ("controller", "service", "repository", "dao", "mapper", "web", "api")

def test_domain_is_segment_before_layer_dir(self):
    # SEF: .../modules/auth/controller/AuthController.java
    self.assertEqual(domain_of("webframework-public/src/main/java/com/sqisoft/sef/modules/auth/controller/AuthController.java"), "auth")
    # GSEED: .../gseed/board/controller/BoardController.java
    self.assertEqual(domain_of("src/main/java/com/sqisoft/gseed/board/controller/BoardController.java"), "board")

def test_layer_dir_named_api_still_yields_owning_domain(self):
    # `api`는 계층 이름이자 도메인 이름일 수 있다. 계층으로 먼저 소비하지 않는다.
    self.assertEqual(domain_of("src/main/java/com/sqisoft/gseed/api/controller/ApiController.java"), "api")

def test_unknown_layout_falls_back_to_parent_dir(self):
    self.assertEqual(domain_of("src/main/java/com/example/Foo.java"), "example")

def test_domain_is_none_for_empty_path(self):
    self.assertIsNone(domain_of(""))
```

- [ ] **Step 2: 분할 실패 테스트를 쓴다**

```python
def test_split_groups_nodes_by_domain(self):
    parts = split_by_domain(ir_two_domains())
    self.assertEqual(sorted(parts), ["auth", "code"])

def test_table_nodes_join_every_domain_that_references_them(self):
    # 테이블 노드는 파일 근거가 없다. 그 테이블을 읽고 쓰는 도메인 전부에 들어간다.
    parts = split_by_domain(ir_shared_table())
    for d in parts:
        self.assertIn("gx-table--TB_USER", [n["id"] for n in parts[d]["nodes"]])

def test_edges_crossing_domains_are_dropped_and_reported(self):
    # 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않는다.
    # 조용히 버리지 않고 해당 도메인 IR의 missing_inputs에 남긴다.
    parts = split_by_domain(ir_cross_domain())
    self.assertTrue(any("cross-domain-edge" in p.get("missing_inputs", []) for p in parts.values()))

def test_split_is_deterministic(self):
    self.assertEqual(split_by_domain(ir_two_domains()), split_by_domain(ir_two_domains()))
```

- [ ] **Step 3: 테스트를 실행해 실패를 확인한다**

Run: `python -m unittest tests.test_gx_arch_split -v`
Expected: FAIL — 모듈이 없다.

- [ ] **Step 4: `split_domains.py`를 구현한다**

`domain_of(path)`: 경로를 `/`로 쪼개고 **계층 폴더 이름이 나오는 첫 위치**를 찾아 그 **바로 앞 세그먼트**를 반환한다. 앞 세그먼트가 없거나 계층 폴더가 없으면 파일명 바로 앞 디렉터리를 반환한다. 빈 경로는 `None`.

두 실제 프로젝트에서 측정한 형태가 모두 이 규칙을 만족한다(설계서 §5.7). 특정 저장소의 `modules/` 같은 관례에 의존하지 않는다.

`split_by_domain(ir)`: 노드의 첫 `evidence.file`로 도메인을 정한다. **단 `kind == "table"`인 노드는 예외다** — 테이블 노드도 MyBatis XML 파일 근거를 가지므로 경로로 판정하면 `mybatis` 같은 가짜 도메인이 생긴다(컨트롤러 실측: 86엣지 중 32건이 이 오분류 때문에 교차 엣지로 잡혔다). 테이블은 경로를 보지 말고 **자신을 참조하는 모든 도메인에 복제**한다.

도메인 경계를 넘는 엣지(실측: 86건 중 약 13건, 대부분 `user → auth` 같은 도메인 간 서비스 호출)는 어느 한 장에도 온전히 담기지 않는다. 버리되 그 사실을 해당 도메인 IR의 `missing_inputs`에 남긴다 — 조용히 지우지 않는다. Step 9에서 **교차 엣지 건수를 보고**한다.

- [ ] **Step 5: 결함 A(같은 열 엣지) 실패 테스트를 쓴다**

`tests/test_gx_arch_archify.py`:

```python
def test_same_column_edge_gets_explicit_sides(self):
    # service -> service, repository -> repository 는 실제로 존재한다(설계서 5.7.1).
    conn = self.to_archify(_ir_same_layer_chain(), "architecture")[EDGE_KEY][0]
    self.assertEqual(conn["fromSide"], "bottom")
    self.assertEqual(conn["toSide"], "top")

def test_cross_column_edge_has_no_explicit_sides(self):
    conn = self.to_archify(_ir_normal_chain(), "architecture")[EDGE_KEY][0]
    self.assertNotIn("fromSide", conn)
```

- [ ] **Step 6: 결함 B(sublabel 하한) 실패 테스트를 쓰고 틀린 테스트를 고친다**

기존 `test_sublabel_length_does_not_force_size`는 **틀린 동작을 고정하고 있다.** 삭제하고 아래로 교체한다.

```python
def test_long_sublabel_widens_the_box(self):
    # sublabel은 6px까지만 줄고 그 아래로는 Archify가 문서를 거부한다.
    ir = _ir_with_label("조회", technical="GET /adm/v1/reb/versions/{targetGrcodeCd}/download/by-building-pk")
    c = self.to_archify(ir, "architecture")[NODE_KEY][0]
    self.assertGreaterEqual(c["size"][0] - 8, _text_units(c["sublabel"]) * 6 * 0.6)

def test_short_sublabel_does_not_widen(self):
    ir = _ir_with_label("조회", technical="GET /a")
    self.assertNotIn("size", self.to_archify(ir, "architecture")[NODE_KEY][0])
```

- [ ] **Step 7: 두 결함을 구현한다**

`to_archify.py`의 폭 계산을 두 조건의 최댓값으로 바꾼다. 상수 출처는 모듈 상단 주석에 적는다.

```
width = max(120, ceil(max(text_units(label) * 6.6 - 8,
                          text_units(sublabel) * 6 * 0.6 + 8)))
layout.cellW = max(150, max(width) - gapX + 8)
```

같은 열 엣지(`from`과 `to`의 `col`이 같음)에는 `fromSide`/`toSide`를 준다 — 타깃 `row`가 크면 `bottom`→`top`, 아니면 `top`→`bottom`.

- [ ] **Step 8: 테스트를 실행해 통과를 확인한다**

Run: `python -m unittest tests.test_gx_arch_split tests.test_gx_arch_archify -v`
Expected: PASS

- [ ] **Step 9: 실제 프로젝트로 종단 확인한다**

`D:\SQ\kereb-grep-2025-admin\sqisoft-sef-2024`를 스캔해 도메인별로 나누고 각각 Archify `validate`를 돌린다. 기대값(컨트롤러 실측): `code`(15노드)·`auth`(7노드)는 **통과**, `reb`(32노드)는 실패가 남는다. 통과 도메인이 하나도 없으면 구현이 틀린 것이다. **결과를 도메인별 표로 보고한다.**

- [ ] **Step 10: SKILL.md와 entrypoint-rules.md를 갱신한다**

- `## 누적 아키텍처 맵` 절: `--scope all`이 도메인별로 나눠 그린다는 것, 파일명이 `{domain}.ir.json`·`{domain}.html`이라는 것, **도메인마다 개별 판정**하며 실패한 도메인만 폴백한다는 것을 적는다. 전부 성공 아니면 전부 실패로 묶지 않는다
- `--domain`은 이제 라벨 보강뿐 아니라 **그릴 도메인 선택**도 한다 — 생략하면 전 도메인을 그린다
- `entrypoint-rules.md`: `calls`가 `api→service`·`service→repository`뿐이라는 현재 서술은 실제 스캐너 동작과 다르다. **같은 계층 안의 호출(`service→service`, `repository→repository`)도 나온다**는 사실을 규칙에 반영한다

- [ ] **Step 11: 커밋**

```bash
git add .claude/skills/gx-visualize tests/test_gx_arch_split.py tests/test_gx_arch_archify.py
git commit -m "feat: 아키텍처 맵을 도메인별로 분할하고 변환기 결함 2건을 수정"
```

---

## Self-review

**스펙 커버리지**

| 수용 기준 | 담당 Task |
|---|---|
| 1. Java Spring 노드 추출 | Task 1 |
| 2. 결정적 노드 ID·정렬 | Task 1 (Step 2의 `test_scan_is_deterministic`) |
| 3. 변경분 교체·삭제 노드 제거 | Task 3 |
| 4. 병합 후 검증·기존 IR 보존 | Task 3 + Task 6 Step 4의 5번 항목 |
| 5. Archify 변환·실제 시그니처 | Task 4, Task 5 |
| 6. 미설치 시 폴백 | Task 4 (`test_failed_archify_still_produces_fallback_html`) |
| 7. complete 제안·헤드리스 skip | Task 7 |
| 8. 비-git mtime 지문 | Task 3 (`test_non_git_fingerprint_changes_with_content`) |
| 9. scope별 출력 위치 분리 | Task 6 (`test_session_scope_writes_to_dev_dir`, `test_all_scope_writes_to_map_dir`) |
| 10. 세션 HTML 스냅샷 배너 | Task 6 (`test_session_html_carries_snapshot_banner`) |
| 11. 동기화·린트 통과 | Task 9 |
| 12. Archify 자동 설치와 1회 시도 | Task 8 (`test_absent_archify_triggers_one_install_attempt`, `test_install_is_attempted_only_once_per_failure`) |
| 13. 설치 실패 시 폴백·그림 부재 표시 | Task 8 (`test_install_failure_falls_back_without_raising`, `test_fallback_html_states_no_diagram_was_produced`) |
| 14. 긴 한국어 라벨이 Archify 검증을 통과 | Task 6 2단위 (`test_long_korean_label_gets_explicit_size`, Step 11 종단 확인) |
| 15. `--scope all`이 도메인별로 나눠 그린다 | Task 10 (`test_split_groups_nodes_by_domain`) |
| 16. 도메인마다 개별 판정하고 실패 도메인만 폴백 | Task 10 Step 9·10 |
| 17. 같은 열 엣지와 긴 sublabel이 Archify 검증을 통과 | Task 10 (`test_same_column_edge_gets_explicit_sides`, `test_long_sublabel_widens_the_box`) |

JSP·Servlet·테이블 추출(설계서 §5.4)은 Task 2가 담당한다.

**알려진 미확정 지점**

Task 5의 `REQUIRED_TOP_LEVEL`·`NODE_KEY`·`EDGE_KEY`는 Archify 실제 스키마를 실측해야 확정된다. Task 5 Step 1이 이를 기록하는 전용 단계이며, 기록 전에는 변환기를 작성하지 않는다. Archify 설치가 불가능하면 Task 5를 중단하고 보고한다 — Task 1~4, 6~8은 Archify 없이도 완료된다.
