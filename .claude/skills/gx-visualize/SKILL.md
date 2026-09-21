---
name: gx-visualize
description: Use when 사용자가 GX 산출물의 요구사항 추적, 진행 상태, 변경 영향, 서비스 구조, 호출 순서를 시각화해 달라고 하거나 "시각화 포함", "구조를 그림으로 보여줘", "변경 영향도를 시각화해줘"라고 요청한다.
argument-hint: <trace|progress|impact|service|sequence> [--input <path>] [--input-path <path>]... [--dev-dir <path>] [--output <path>] [--backend auto|archify|mermaid|static] [--project-root <path>] [--scope session|all] [--map-dir <path>] [--domain <name>]
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# GX 산출물 시각화

GX 작업 산출물을 근거가 추적되는 JSON IR과 한국어 HTML로 변환한다. 이 스킬은 사용자가 시각화를 명시적으로 요청했을 때만 실행하며, 설계·구현·리뷰·커밋 게이트를 대신하지 않는다.

## 호출 계약

```text
gx-visualize <trace|progress|impact|service|sequence> [--input <path>] [--input-path <path>]... [--dev-dir <path>] [--output <path>] [--backend auto|archify|mermaid|static] [--project-root <path>] [--scope session|all] [--map-dir <path>] [--domain <name>]
```

- 기본 백엔드: `auto`
- 기본 출력: `${DEV_DIR}/visual/`; `DEV_DIR`가 없으면 프로젝트 안의 `.dev/{branch-slug}/visual/`
- `--input`: 한 파일 또는 산출물 디렉터리. 생략하면 아래 입력 수집 계약을 적용한다.
- `--input-path`는 반복 가능하며 호출자가 이미 확인한 개별 산출물 경로를 전달한다. 이 옵션은 기본 수집을 제한하지 않는다. 파이프라인 호출은 각 기존 파일에 한 번씩 사용한다.
- `--dev-dir`: 현재 작업의 산출물 디렉터리. 파이프라인 호출은 `DEV_DIR`을 명시적으로 전달하며, 생략 시 기존 기본값 탐색을 사용한다.
- `--output`: 프로젝트 안의 출력 디렉터리. 외부 경로를 쓰려면 사용자의 명시적 경로가 있어야 한다.
- `--project-root`: evidence 경로를 해석하고 가둘 명시적 프로젝트 루트. 파이프라인 호출은 항상 `PROJECT_ROOT`를 전달한다.
- `--scope`: `service`·`sequence` 뷰의 출력 위치를 가른다. 기본값은 `session`. 자세한 내용은 [누적 아키텍처 맵](#누적-아키텍처-맵)을 읽는다.
- `--map-dir`: `--scope all`의 출력 디렉터리. 기본값은 `.dev/architecture/`.
- `--domain`: `context/{도메인}/`로 라벨을 보강하고, `--scope all`에서는 **그릴 도메인 선택**도 겸한다. 생략하면 스캔 대상 파일 경로에서 도메인을 추정하고 전 도메인을 그린다.
- 잘못된 view나 backend는 허용 목록을 보여 주고 렌더링 전에 실패한다.

명시 요청이 없으면 자동 실행하지 않는다. 직접 호출 외에 “시각화 포함”, “구조를 그림으로 보여줘”, “변경 영향도를 시각화해줘”도 명시 요청으로 본다.

## 하네스 적응

이 문서는 파일 읽기·검색·명령 실행이라는 기능으로 절차를 서술한다. 하네스의 도구 이름을 계약으로 고정하지 않는다.

- Codex에서는 설치된 [공통 실행 규약](../gx-dev/references/codex-runtime.md)을 먼저 읽고, 이어서 이 스킬의 [Codex 적응 노트](references/codex-runtime.md)를 적용한다.
- 모든 번들 파일은 이 `SKILL.md` 또는 그 지시가 적힌 파일을 기준으로 한 상대경로로 찾는다. cwd, 개발 저장소 위치, 캐시 절대경로를 플러그인 루트로 간주하지 않는다.
- Windows에서는 Markdown·JSON을 UTF-8로 읽고 쓴다.

## 뷰 라우터

view가 없는 자연어 요청은 다음 키워드로 정규화한다.

- `변경 영향도` → `impact`
- `구조` → `service`; `서비스 관계` → `service`
- `호출 순서` → `sequence`
- `진행` → `progress`; `상태` → `progress`
- `추적` → `trace`; `요구사항` → `trace`

일반적인 “시각화 포함”에 view 키워드가 없으면 현재 phase 기본값을 쓴다: `design` → `service`, `review` → `impact`, `그 외` → `progress`. 서로 다른 view를 가리키는 단서가 함께 있거나 현재 phase를 확인할 수 없어 모호하면 사용자에게 view를 질문하고 답을 기다린다.

| view | 답할 질문 | 수집 그룹 | 지원 범위 |
|---|---|---|---|
| `trace` | 요구사항이 기능·데이터·테스트까지 연결됐는가? | `prd`, `design`, `DE-08`, `DE-13` | 1차 필수 |
| `progress` | 현재 Phase·Gate·검증 상태는 무엇인가? | `state`, `summary`, `self-check` | 1차 필수 |
| `impact` | 변경이 무엇을 추가·삭제·변경·이동했는가? | `diff`, `codemap`, `design` | 1차 필수 |
| `service` | 서비스·화면·API·테이블 관계는 무엇인가? | `codemap`, `design`, 프로젝트 context | 1차 필수 |
| `sequence` | 명시된 요청의 호출 순서는 무엇인가? | `design`, 명시된 호출 근거 | 후속 범위 |

`sequence`는 후속 범위다. Archify의 `sequence.schema.json`은 `participants`·`messages`를 필수로 요구하고 `components`·`connections`·`layout`은 정의하지 않으므로, `service` 뷰가 쓰는 architecture 변환기를 그대로 재사용할 수 없다. 전용 participants/messages 변환기가 나오기 전까지 `sequence` 뷰는 Archify 시도 자체를 건너뛰고 폴백 백엔드(mermaid → static)로 렌더된다. 요구의 중심은 아키텍처 맵이므로 반쯤 완성된 sequence 변환기보다 정확한 architecture 맵을 우선했다.

입력 근거가 부족하면 런타임 관계를 상상해서 완성하지 말고 `missing_inputs`를 보고한다. 상세 파일 후보와 IR 변환 규칙은 [GX 산출물 매핑](references/gx-mapping.md)을, 코드 근거 기반 진입점 체인 추출 규칙은 [진입점 체인 추출 규칙](references/entrypoint-rules.md)을 읽는다.

## 입력 수집 계약

`collect_inputs(project_root, dev_dir, view) -> {"files": [...], "missing_inputs": [...]}`

1. `project_root`와 `dev_dir`를 실제 존재하는 디렉터리로 해석하고, 읽을 수 있는 프로젝트 내부 경로만 허용한다.
2. `--input`이 있으면 그 파일 또는 디렉터리 안에서 선택한 view의 후보만 수집한다. 없으면 `dev_dir`, 프로젝트 `context/`, 프로젝트 루트의 명시 산출물 순으로 찾는다. 반복 `--input-path`가 있으면 명시 경로와 기본 탐색 결과를 합친다. 따라서 파이프라인이 현재 산출물을 정확히 넘겨도 service 뷰의 프로젝트 context 기본 탐색은 유지된다.
3. 같은 논리 산출물의 후보가 여러 개면 `dev_dir`의 현재 작업 산출물을 우선하고, 선택한 실제 경로만 `files`에 넣는다.
4. 존재하고 읽을 수 있는 일반 파일만 프로젝트 루트 상대경로로 기록한다. `files`와 `missing_inputs`를 정렬하고 중복을 제거한다.
5. 충족되지 않은 필수 논리 그룹만 매핑 표의 안정된 그룹명으로 `missing_inputs`에 넣는다. 보조 그룹은 넣지 않고, `A 또는 B` 필수 그룹은 후보가 하나라도 있으면 충족이다. 누락 입력을 추정하거나 조용히 채우지 않는다.

누락이 있어도 근거가 충분한 부분 뷰는 만들 수 있다. 다만 누락 항목을 최종 report와 receipt에 그대로 보존하고, 없는 산출물의 ID·상태·관계를 생성하지 않는다.

## 실행 절차

1. view와 옵션을 검증하고 입력을 수집한다.
2. [IR 계약](references/ir-contract.md)에 맞춰 `{view}.json`을 만든다. 공식 ID와 한국어 표시명을 보존하고, 텍스트는 실제 파일·라인, XLSX/PDF는 실제 파일·locator를 쓴다.
3. `scripts/validate_ir.py {view}.json --project-root <PROJECT_ROOT>`로 IR을 검증한다. renderer API와 CLI에도 같은 `project_root`를 전달한다. 실패하면 성공 HTML을 만들거나 이전 HTML을 재사용하지 않는다.
4. `auto`이면 `scripts/detect_backend.py`의 `ensure_archify()`가 Archify 설치를 확인하고, 없으면 사용자에게 묻지 않고 `npx -y skills add tt-a1i/archify -g`로 1회 자동 설치를 시도한 뒤 그 결과로 `detect_backend()`가 실행 가능한 백엔드를 확정한다. 설치 성공은 exit code가 아니라 `doctor` 결과로 판정하며, 설치·재탐지가 모두 실패해도 예외 없이 폴백(Mermaid → static)으로 넘어간다.
5. Archify는 [선택 어댑터 계약](references/archify-adapter.md)에 따라 validate 후 deliver한다. `--archify-command`에는 4번이 확정한 `command`를 그대로(verbatim) 전달한다 — 경로 형태를 바꾸지 않는다(예: Git Bash 경로로 재조립 금지). 실패하면 Mermaid, 이어서 static을 시도한다. 명시한 `mermaid` 또는 `static`은 `scripts/render_fallback.py`로 렌더링한다.
6. HTML이 존재하고 비어 있지 않으며 IR·receipt의 view와 경로가 일치하는지 확인한다.
7. 아래 출력 계약으로 결과를 보고한다. 전체 예시는 [trace 요청 예시](examples/trace-request.md)를 참고한다.

## 누적 아키텍처 맵

`--scope`가 출력 위치를 가른다. 파일명은 기존 `{view}.json`·`{view}.html` 규칙 그대로다.

| scope | 위치 | 성격 |
|---|---|---|
| `session` | `${DEV_DIR}/visual/` | 그 시점 스냅샷, 갱신하지 않는다 |
| `all` | `${MAP_DIR}/` (기본 `.dev/architecture/`, `--map-dir`로 변경) | 매 실행 전체를 다시 스캔, 도메인별로 분할 |

두 산출물을 **한 폴더에 섞지 않는다**. 세션 출력은 갱신되지 않으므로 누적 맵과 같은 위치에 두면 낡은 그림을 최신으로 오인하게 된다.

`--scope session` HTML 상단에는 **스냅샷 배너**를 넣는다 — 생성 시각과 `git rev-parse --short HEAD` 결과, 그리고 "이 그림은 해당 시점의 스냅샷이며 갱신되지 않습니다". `--scope all`에는 넣지 않는다.

### 도메인 분할 (`--scope all`)

실제 저장소 규모(86노드)를 한 장으로 그리면 Archify 검증이 대량으로 실패하고, 애초에 사람이 읽을 수도 없다(설계서 §5.7). 그래서 `--scope all`은 `scripts/split_domains.py`의 `split_by_domain()`으로 노드를 도메인별로 나눠 각각 별도 문서로 그린다. `--scope session`은 분할하지 않는다 — 세션 diff는 이미 작아서 나눌 필요가 없다.

- 파일명은 `{domain}.ir.json`·`{domain}.html`이다(예: `auth.ir.json`, `auth.html`). `--scope all`에는 기존 `service.json`·`service.html` 단일 파일 규칙을 더 이상 적용하지 않는다. `scripts/render_archify.py`·`scripts/render_fallback.py`는 기본적으로 IR의 `view`(항상 `service`)로 파일명을 짓기 때문에, 도메인마다 그대로 호출하면 전부 `service.html`을 서로 덮어쓴다 — 도메인별로 렌더할 때는 반드시 `--output-name {domain}`을 전달해 `{domain}.html`·`{domain}.receipt.json`을 받는다. 이 인자를 생략하면 기존 `{view}.*` 단일 문서 동작이 그대로 유지된다(예: `--scope session`).
- 테이블 노드는 경로로 도메인을 판정하지 않고, 자신을 참조하는 모든 도메인에 복제된다. 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않으므로 조용히 지우지 않고 관련된 각 도메인 IR의 `missing_inputs`에 `cross-domain-edge`로 남기며, 보고에 건수를 포함한다.
- **도메인마다 개별로 Archify에 넣어 판정한다 — 전부 성공 아니면 전부 실패로 묶지 않는다.** 한 저장소 안에서 어떤 도메인은 그림이 나오고 어떤 도메인은 표(폴백)로 떨어지는 것이 정상이며, 그 사실을 보고에 드러낸다. 실패한 도메인만 mermaid → static으로 폴백하고, 통과한 도메인의 그림은 그대로 둔다.
- `--domain`을 주면 그 도메인만 그린다. 생략하면 `split_by_domain()`이 찾은 전 도메인을 각각 그린다.

1. `--scope all`이면 프로젝트 전체를 `scripts/scan_entrypoints.py`로 스캔한다. `--scope session`이면 호출자가 `--input-path`로 반복 전달한 이번 사이클 변경 파일 목록(gx-dev·gx-tdd phase-complete Step 5.5가 이미 파악한 목록) 중 `.java`·`.jsp`·`.xml`만 골라 `scan_entrypoints.py`의 `--changed-file`로 하나씩 넘겨 그 파일들만 스캔한다. 전체 스캔은 저장소 규모에 따라 시간이 걸릴 수 있음을 먼저 알린다. `scan()`은 UTF-8로 읽지 못한 소스를 CP949로 재시도한다(오래된 한국어 JSP·Java 코드베이스에 흔하다). 둘 다 실패한 파일은 크래시시키지 않고 결과의 `skipped`에 담아 건너뛴다 — 조용히 버리지 않고 사용자에게 보고한다. 관계를 해소하지 못한 엣지(대상 매퍼·서비스·API를 찾지 못함)는 `unresolved_edges`에 `source`·`target`·`relation`으로 담아 함께 보고한다 — "노드가 없다"(`skipped`)와 "관계를 해소하지 못했다"(`unresolved_edges`)는 다른 사실이다. SQL 본문은 여기에도 담지 않는다. `--scope all`의 도메인 분할 이후에는 `split_by_domain()`이 두 값을 실행 순간에만 보이고 사라지지 않도록 관련 파일 경로가 속한 도메인의 IR에 각각 담아 보존한다.
2. 스캔 결과의 `label`은 기술 식별자다. `context/{도메인}/glossary.md`와 `${DEV_DIR}/design.md`를 읽어 **한국어 라벨**로 바꾼다. API path·테이블명·클래스명은 `technical_label`에 원문 그대로 보존한다. 근거가 없으면 기술 식별자를 그대로 둔다 — 도메인 용어를 지어내지 않는다.
3. `--scope all`이면 `split_by_domain()`으로 스캔 결과를 도메인별 IR로 나눈다. `--scope session`은 분할하지 않는다 — 스냅샷이므로 나눌 필요가 없다.
4. `--scope all`은 도메인별로, `--scope session`은 단일 문서로 `scripts/validate_ir.py`를 실행해 검증한다. **검증에 실패한 도메인의 이전 `${MAP_DIR}/{domain}.ir.json`은 덮어쓰지 않는다** — 다른 도메인의 갱신에는 영향을 주지 않는다.
5. 생성된 경로를 보고한다 — `--scope all`은 도메인마다 `${MAP_DIR}/{domain}.ir.json`·`{domain}.html`, `--scope session`은 `${DEV_DIR}/visual/service.json`·`service.html`. 둘 다 단발성 산출물이며 커밋하지 않는다.

스캔이 **0개 노드**를 반환하면 빈 IR을 쓰지 않는다. `missing_inputs`에 언어 감지 실패를 기록하고 중단한다.

## 런타임 사실 제약

런타임 사실을 추론하지 않는다.

- 정적 파일명, 함수명, API 문자열만으로 실제 배포 토폴로지·호출 순서·운영 영향도를 단정하지 않는다.
- 설치 여부, 실행 파일 경로, 버전, 명령 성공 여부는 실제 probe 또는 실행 receipt로만 기록한다.
- 소스나 산출물이 “예정”, “추정”, “가정”으로 표시한 내용은 사실 노드로 승격하지 않는다. IR에 꼭 필요하면 위치를 가장하지 않고 `inferred` 근거로 분리한다.
- 운영 비밀·토큰·개인정보를 label, HTML, receipt에 복사하지 않는다.

## 출력과 영수증 계약

기본 파일명은 `{view}.json`, `{view}.html`, `{view}.receipt.json`이다. 최종 report는 다음 필드를 모두 반환한다.

- `view`: 요청한 view
- `backend`: 실제 HTML을 만든 `archify|mermaid|static`, 실패 시 마지막 시도
- `html_path`: 성공 또는 폴백 산출물 경로, 실패 시 `null`
- `ir_path`: JSON IR 경로
- `receipt_path`: 검증·백엔드 시도 영수증 경로
- `validation_status`: `verified|fallback|failed`
- `missing_inputs`: 정렬된 누락 논리 입력 목록

저수준 validator/renderer receipt의 `valid|fallback|not_applicable|failed`는 [GX 산출물 매핑](references/gx-mapping.md)의 표에 따라 report의 `verified|fallback|failed`로 정규화한다 — `not_applicable`(Archify가 대상 view가 아니어서 애초에 시도하지 않음)도 `fallback`으로 올린다. `backend`는 요청값이나 최초 시도가 아니라 실제 HTML 생성자를 보고한다. `backend`가 `archify`가 아니면 실제 그림(다이어그램)은 생성되지 않았다는 사실을 report에 명시한다 — `mermaid`는 소스 코드만, `static`은 노드·관계 표만 보여준다.

## 실패 계약

- gx-dev 등의 선택 단계에서 시각화가 실패하면 `visualization_status: failed`, 실패 이유, receipt 경로를 기록하되 개발·리뷰·커밋 파이프라인은 실패시키지 않는다.
- 사용자가 “시각화만” 요청했거나 이 스킬을 직접 호출했다면 실패 이유, 누락 입력, 마지막 진단, 재실행 명령을 반환하고 시각화 호출 자체를 실패로 끝낸다. HTML 경로를 성공처럼 제시하지 않는다.
- 폴백 HTML이 검증되면 `fallback`으로 성공 산출물을 반환하되 Archify 성공이라고 표현하지 않는다.
- 모든 백엔드가 실패하면 stale HTML을 제거하고 `failed` receipt를 남긴다.
