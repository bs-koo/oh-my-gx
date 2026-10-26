# gx-visualize 설계서

## 1. 목적

`gx-visualize`는 oh-my-gx의 작업 산출물을 한국어 중심의 검증 가능한 시각화로 변환하는 독립 스킬이다. 범용 시스템 아키텍처를 그리는 데 그치지 않고, GX 사업본부의 핵심 추적 체인인 요구사항 → 기능 → 화면/API/테이블 → 테스트 → Phase/검증을 한 화면에서 탐색할 수 있게 한다.

이 스킬은 작업을 수행하는 파이프라인과 분리된 선택 기능이다. 사용자가 `--visualize` 또는 “시각화 포함”을 명시했을 때 실행하며, 시각화 실패가 개발·리뷰·커밋 파이프라인 자체를 실패시키지는 않는다.

## 2. 범위

### 포함

- 한국어 UI와 한국어 작성 콘텐츠를 지원하는 시각화 계약
- GX 산출물에서 시각화용 JSON IR 생성
- 요구사항 추적 맵, 작업 진행 맵, 변경 영향 맵의 1차 지원
- Architecture/Workflow/Delta에 대응하는 Archify 선택 연동
- Archify가 없거나 실행할 수 없을 때 Mermaid 및 정적 HTML 폴백
- 노드별 ID, 상태, 파일·라인 근거, 테스트 연결 표시
- `.dev/{branch-slug}/visual/` 아래 JSON·HTML·검증 영수증 저장
- 시각화 결과의 생성 근거와 검증 상태를 작업 보고서에 연결

### 제외

- Archify 렌더러·뷰어 코드를 저장소에 복제
- 운영 인프라를 자동 탐색하거나 런타임 영향도를 추론하는 기능
- WYSIWYG 편집기, hosted sharing, 실시간 협업
- 모든 Phase에서의 무조건 자동 렌더링
- 시각화 성공을 설계·구현 품질의 성공으로 간주하는 판정

## 3. 사용자 경험

### 호출

- 명시 플래그: `--visualize`
- 자연어: “시각화 포함”, “구조를 그림으로 보여줘”, “변경 영향도를 시각화해줘”
- 스킬 직접 호출: `gx-visualize <view> [source]`

명시 요청이 없으면 기본적으로 실행하지 않는다. `gx-dev`의 `phase-design` 완료 후 또는 `phase-review` 진입 시 사용자가 요청한 경우에만 연결한다.

### 뷰 유형

| 뷰 | 핵심 질문 | 기본 입력 |
|---|---|---|
| `trace` | 요구사항이 기능·데이터·테스트까지 연결됐는가? | AN-02/AN-03/DE-08/DE-13 또는 동등 산출물 |
| `progress` | 작업이 어느 Phase와 Gate에 있는가? | `state.md`, `summary.md`, `self-check.md` |
| `impact` | 이번 변경이 무엇을 추가·삭제·변경·우회했는가? | `diff.txt`, `codemap.md`, `design.md` |
| `service` | 서비스·화면·API·테이블의 관계는 무엇인가? | `codemap.md`, 설계서, 프로젝트 context |
| `sequence` | 한 요청이 어떤 호출 순서를 거치는가? | 설계서와 명시된 호출 근거 |

1차 구현은 `trace`, `progress`, `impact`를 필수로 하고 `service`, `sequence`는 계약만 정의한 뒤 후속 범위로 둔다.

### 화면 원칙

- 중앙에는 가장 짧고 중요한 주 경로를 둔다.
- 노드에는 ID·짧은 한국어 이름·상태만 두고 상세 근거는 카드/패널로 분리한다.
- ID와 코드 식별자(`AN-02-001`, API path, table name)는 원문을 보존한다.
- 색상만으로 상태를 구분하지 않고 상태 배지·아이콘·텍스트를 함께 사용한다.
- “코드 근거”, “설계 근거”, “추정”을 서로 다른 근거 등급으로 표시한다.
- 노드 선택 시 연관 요구사항·기능·테스트와 파일·라인 근거를 함께 보여준다.
- 모든 애니메이션은 선택 사항이며 `prefers-reduced-motion`을 존중한다.

## 4. 아키텍처

```text
GX 산출물 / context
        ↓
입력 수집기
        ↓
GX JSON IR (한국어 콘텐츠 + stable IDs)
        ↓
IR 검증기 (참조 무결성·중복 ID·근거 형식)
        ↓
백엔드 선택기
  ├─ Archify: validate → deliver
  ├─ Mermaid: fenced source + HTML wrapper
  └─ Static: inline SVG/HTML fallback
        ↓
.dev/{branch-slug}/visual/
  ├─ {view}.json
  ├─ {view}.html
  └─ {view}.receipt.json
```

### 4.1 GX JSON IR

IR은 렌더러에 종속되지 않는 정본이다. 최소 필드는 다음과 같다.

```json
{
  "schema_version": 1,
  "view": "trace",
  "locale": "ko-KR",
  "title": "요구사항 추적 맵",
  "nodes": [
    {
      "id": "AN-02-001",
      "kind": "requirement",
      "label": "에너지 사용량을 기간별로 조회한다",
      "status": "verified",
      "evidence": [{"file": ".dev/JIRA-123/prd.md", "line": 18, "kind": "artifact"}]
    }
  ],
  "edges": [
    {"id": "AN-02-001->AN-03-014", "source": "AN-02-001", "target": "AN-03-014", "relation": "realized_by"}
  ],
  "meta": {"project": "example", "generated_at": "2026-09-17T00:00:00Z"}
}
```

IR 규칙:

- `schema_version`은 정수 `1`부터 시작한다.
- 노드 ID는 입력 산출물의 공식 ID를 우선 사용하고, ID가 없으면 `gx-{kind}-{slug}`를 안정적으로 생성한다.
- 모든 edge의 `source`와 `target`은 nodes에 존재해야 한다.
- `evidence.file`은 프로젝트 루트 상대경로로 해석하고, 명시적인 `project_root` 경계 안에 있어야 한다. IR이 `${DEV_DIR}/visual/` 아래 있어도 `../`로 IR 디렉터리를 벗어나는 것은 허용한다.
- 텍스트 근거는 `line`을 사용한다. XLSX/PDF 등 비텍스트 근거는 `locator` 객체를 사용하며, 예를 들어 `{"type":"xlsx","sheet":"요구사항","cell":"B12"}`처럼 원본 위치를 보존한다.
- 근거가 없는 사실은 `inferred`로 표시하고 파일·라인을 가장하지 않는다.
- 상태 값은 `planned|in_progress|review|verified|blocked|unknown`으로 제한한다.
- 한국어 콘텐츠와 코드 식별자를 한 필드에 섞지 않고 `label`과 `technical_label`을 분리할 수 있다.

### 4.2 Archify 연동

Archify가 설치되어 있으면 IR을 Archify의 architecture/workflow 입력으로 변환한다. Archify의 검증·전달 명령이 성공한 경우에만 해당 HTML을 신뢰 산출물로 기록한다. 실패하면 진단 코드와 명령 출력을 영수증에 남기고 폴백으로 전환한다.

Archify 설치 여부·버전·CLI 경로를 추정하지 않는다. `node`와 Archify CLI의 실제 실행 가능 여부를 확인하며, 확인할 수 없으면 폴백한다. 외부 네트워크나 자동 업데이트는 요구하지 않는다.

### 4.3 폴백

- Mermaid 폴백: IR의 노드·edge를 Mermaid flowchart로 변환하고, 한국어 제목·범례를 포함한 HTML wrapper를 생성한다.
- 정적 폴백: Mermaid 실행도 불가능하면 노드 목록·관계 표·근거 카드를 포함한 self-contained HTML을 생성한다.
- 폴백도 동일한 IR과 receipt를 사용하므로 결과 형식과 보고 방식은 백엔드에 따라 달라지지 않는다.

## 5. GX 산출물 매핑

| 입력 | IR 변환 |
|---|---|
| `codemap.md` | service/screen/api/table 노드 후보와 프로젝트 루트 기준 파일 근거 |
| `prd.md` 또는 AN-02 | requirement 노드 |
| `design.md` 또는 AN-03 | function·service·sequence 관계 |
| DE-08 | table/data 노드 |
| DE-13 | test 노드와 verifies 관계 |
| `state.md` | Phase·상태·Gate 노드 |
| `diff.txt` | impact 뷰의 added/removed/changed/moved 관계 |
| `summary.md`, `self-check.md`, `trust-ledger.md` | 검증·근거 카드 |

입력 산출물이 없는 경우 조용히 채워 넣지 않는다. `missing_inputs`에는 충족되지 않은 필수 논리 그룹만 기록한다. 보조 입력이 없거나 `A 또는 B` 그룹에서 한 후보만 발견된 경우는 누락으로 기록하지 않고, 모든 후보가 없을 때만 그룹명을 기록한다.

## 6. 스킬·파이프라인 경계

`gx-visualize`는 독립 스킬로 제공한다. `gx-dev`는 사용자가 시각화를 요청한 경우에만 호출하며, `phase-design`·`phase-review`는 출력 경로와 입력 산출물만 전달한다. 스킬은 다른 스킬의 구현·커밋·PR 게이트를 대신 수행하지 않는다.

Claude Code와 Codex 양쪽에서 동일한 SKILL.md를 사용한다. Codex에서는 설치된 `codex-runtime.md`에 따라 `Task`·`AskUserQuestion`·`Skill`을 대응하고, 특정 도구명이나 모델명을 고정 계약으로 쓰지 않는다.

## 7. 검증·실패 처리

검증 단계는 다음 순서다.

1. 입력 파일 존재·UTF-8·허용 경로 확인
2. IR JSON 스키마와 ID·edge 참조 무결성 확인
3. 백엔드별 렌더링/검증 실행
4. 결과 HTML 존재·빈 파일·receipt 일치 확인
5. 결과 요약에 backend, view, validation status, output path, missing inputs를 기록

시각화 실패는 `visualization_status: failed`로 기록하고 본 개발·리뷰 Phase는 계속할 수 있다. 단, 사용자가 “시각화만” 요청한 경우에는 실패 이유와 재실행 명령을 반환하고 성공으로 표현하지 않는다.

## 8. 보안·개인정보

- 기본 출력은 작업 디렉토리 내부에만 저장한다.
- 소스 근거는 사용자가 접근 가능한 파일 경로만 사용한다.
- 운영 비밀·토큰·개인정보를 노드 label이나 카드에 복사하지 않는다.
- 외부 URL 캡처·업로드·호스팅은 1차 범위에서 지원하지 않는다.

## 9. 수용 기준

1. `trace` IR이 AN-02 → AN-03 → DE-08/DE-13 관계를 보존한다.
2. 한국어 제목·범례·상태가 생성되고 API path·table name·ID는 원문 보존된다.
3. Archify가 실행 가능하면 Archify backend의 검증 영수증과 HTML 경로를 반환한다.
4. Archify가 없거나 실패해도 Mermaid 또는 정적 HTML과 receipt가 생성된다.
5. 존재하지 않는 edge target, 중복 ID, 허위 파일·라인 근거는 검증 단계에서 실패한다.
6. `gx-dev`의 기본 실행은 시각화를 자동 실행하지 않는다.
7. Claude Code와 Codex 설치 경로에서 스킬의 상대 참조가 깨지지 않는다.
8. 로컬 Codex 리소스 동기화·일관성 린트·관련 단위 테스트가 통과한다.
