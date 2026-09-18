# gx-visualize 누적 아키텍처 맵 설계서

작성일: 2026-09-18

## 1. 목적

개발자가 gx-tdd·gx-dev 사이클을 돌린 뒤 **"내가 만든 기능이 코드상 어떤 구조로 구현됐는가"** 를 한 화면에서 파악하게 한다. 나아가 스킬을 단독 호출하면 **그 프로젝트에 지금까지 구현된 전체 아키텍처와 호출 흐름**을 보여준다.

기존 `gx-visualize`(2026-09-17 설계서)는 작업 **산출물**(PRD·상태·diff)을 그렸다. 이 설계서는 같은 스킬에 **코드 자체**를 근거로 하는 누적 아키텍처 맵을 더한다. 대상 사용자는 GX 사업본부 개발자와 비개발 이해관계자다.

## 2. 기존 설계와의 관계

`gx-visualize`를 확장한다. 새 스킬을 만들지 않는다.

- `view` enum의 `service`·`sequence`는 이미 정의되어 있으나 "계약 지원"으로 구현이 미뤄져 있다. 이 둘을 1급으로 승격한다.
- IR 스키마의 `node.kind`는 자유 문자열이고 `evidence.kind`에 `code`(file+line)가 있다. 스키마 변경 없이 코드 근거 노드를 담을 수 있다.
- IR 검증기(`validate_ir.py`), 폴백 렌더러(`render_fallback.py`), 백엔드 선택기(`detect_backend.py`), 영수증 계약을 그대로 재사용한다.
- 기존 `trace`·`progress`·`impact` 뷰의 동작과 출력 경로(`${DEV_DIR}/visual/`)는 변경하지 않는다.

## 3. 범위

### 포함

- 진입점 체인 기반 결정적 코드 스캐너 (Java Spring / JSP·Servlet)
- 스캔 결과를 GX IR로 변환하고 `context/`·설계서에서 한국어 도메인 라벨 보강
- 누적 맵의 git 지속화와 파일 지문 기반 증분 갱신
- Archify 백엔드 수리 (명령 시그니처 + IR 변환기)
- `gx-dev`·`gx-tdd` phase-complete의 시각화 제안 게이트

### 제외

- 런타임 토폴로지·실제 트래픽·배포 구조 추론
- Archify 렌더러 코드의 저장소 복제
- 진입점 체인 밖의 유틸리티·DTO·설정 클래스 노드화
- 파일 리네임 추적 (삭제 + 추가로 표현한다)
- Java·JSP 외 언어의 스캐너 (후속 범위)

## 4. 결정 사항

| # | 결정 | 근거 |
|---|---|---|
| D1 | complete 종료 후 **항상 묻되 헤드리스는 자동 skip** | 대화형에서 발견성을 확보하되 `ralph.lock` 세션은 응답할 사용자가 없다 |
| D2 | 근거는 **코드 스캔 + 한국어 라벨 보강** | 플러그인 도입 이전 레거시 코드가 맵에 들어와야 한다 |
| D3 | 추출 단위는 **진입점 체인만** | 유틸·DTO를 넣으면 그림이 엉키고 비용·환각 위험이 커진다 |
| D4 | `gx-visualize` **확장** (새 스킬 아님) | IR·검증기·백엔드·폴백 4종 중복을 피한다 |
| D5 | 누적 맵은 **JSON + HTML 둘 다 커밋** | JSON은 diff 추적용 정본, HTML은 비개발자 열람용 |
| D6 | 스캐너는 **결정적 Python**, LLM은 라벨만 | 구조 추출을 LLM에 맡기면 근거 없는 노드가 생긴다 |
| D7 | 세션 스냅샷은 `.dev/`, 누적 맵은 `docs/` — **폴더 분리** | 세션 HTML은 갱신되지 않는다. 한 폴더에 섞이면 낡은 그림을 최신으로 오인한다 |

## 5. 아키텍처

```text
[스캔]  scan_entrypoints.py  (결정적, 언어별 패턴)
          화면 → Controller/Servlet → Service → DAO/Mapper → Table
          각 노드에 file:line 근거 부착
            ↓  scan.raw.json  (technical_label만, 한국어 없음)
[보강]  스킬(LLM)이 context/*/glossary.md·design.md로 한국어 label 부여
            ↓  후보 IR
[병합]  merge_map.py  (이전 IR + 후보 IR + manifest)
          변경 파일의 노드만 교체, 사라진 파일의 노드 제거
            ↓  service.ir.json
[검증]  validate_ir.py  — edge 참조 무결성이 병합 사고를 잡는다
            ↓
[렌더]  archify → mermaid → static
            ↓
docs/architecture/
  service.ir.json         정본 (커밋)
  service.html            렌더 결과 (커밋)
  sequence-{도메인}.ir.json / .html
  .scan-manifest.json     파일별 지문 (커밋)
```

### 5.1 산출물 위치 — scope가 위치를 결정한다

`--scope`가 출력 디렉터리를 가른다. 파일명은 기존 `{view}.json`·`{view}.html` 규칙을 그대로 쓴다.

| scope | 위치 | 성격 | 독자 |
|---|---|---|---|
| `session` | `${DEV_DIR}/visual/` | 그 시점 **스냅샷**, 갱신하지 않음 | PR 리뷰어 — 해당 PR diff에 함께 올라간다 |
| `all` | `docs/architecture/` (기본값, `--map-dir`로 변경) | **항상 최신**, 증분 갱신 | 사업부 전체, 신규 투입자 |

둘을 한 폴더에 섞지 않는다. 세션 산출물은 갱신되지 않으므로, 누적 맵과 같은 위치에 두면 낡은 그림을 최신으로 오인하게 된다. 폴더를 분리하면 이 혼동이 구조적으로 발생하지 않는다.

`session` 출력은 `trace`·`progress`·`impact`가 이미 쓰는 `${DEV_DIR}/visual/` 계약을 그대로 따른다. 새 경로 규칙을 만들지 않는다.

`session` HTML 상단에는 **스냅샷 배너**를 넣는다: 생성 시각과 `git rev-parse --short HEAD` 결과를 표시하고 "이 그림은 해당 시점의 스냅샷이며 갱신되지 않습니다"를 명시한다. 누적 맵(`all`)에는 배너를 넣지 않는다.

영수증(`*.receipt.json`)은 scope와 무관하게 `${DEV_DIR}/visual/`에 남기고 커밋하지 않는다.

**알려진 비용**: self-contained HTML은 브랜치마다 수백 KB가 `.dev/`에 축적된다. 실제 크기를 측정한 뒤 억제 수단이 필요한지 판단한다 — 측정 전에 설정 항목을 추가하지 않는다.

### 5.2 스캔 매니페스트

```json
{
  "schema_version": 1,
  "vcs": "git",
  "generated_at": "2026-09-18T00:00:00Z",
  "files": {
    "src/main/java/com/sqi/auth/LoginController.java": {
      "fingerprint": "a3f9c1d2...",
      "nodes": ["gx-api-src-main-java-com-sqi-auth-LoginController-java--login"]
    }
  }
}
```

- git 프로젝트: `fingerprint`는 `git hash-object <file>`의 blob SHA.
- 비-git 프로젝트(GSEED 계열): `fingerprint`는 `"{mtime_ns}-{size}"`.
- `nodes`는 그 파일이 만들어 낸 노드 ID 목록이다. 파일이 사라지면 이 목록의 노드를 제거한다.

### 5.3 노드 ID 안정성

`gx-{kind}-{프로젝트 루트 상대경로의 비영숫자를 -로 치환}--{심볼}`

같은 파일·같은 심볼이면 실행 간 동일하다. 파일 리네임은 삭제 + 추가로 나타난다. 리네임 추적은 구현하지 않는다.

### 5.4 진입점 체인 추출 규칙

| kind | Java Spring | JSP·Servlet |
|---|---|---|
| `screen` | — | `**/*.jsp` 파일 |
| `api` | `@RequestMapping`·`@GetMapping`·`@PostMapping`·`@PutMapping`·`@DeleteMapping`·`@PatchMapping`이 붙은 메서드 | `HttpServlet` 상속 클래스의 `doGet`·`doPost` |
| `service` | `@Service` 클래스 | `*Service`·`*ServiceImpl` 클래스 |
| `repository` | `@Repository`·`@Mapper` 클래스·인터페이스 | `*DAO`·`*Dao` 클래스 |
| `table` | MyBatis XML의 `<select>`·`<insert>`·`<update>`·`<delete>` 본문에서 추출한 테이블명 | 동일 |

edge `relation` 값: `calls`(api→service, service→repository), `reads`·`writes`(repository→table), `requests`(screen→api).

체인 밖 클래스는 노드로 만들지 않는다. 호출 관계는 **같은 파일 안의 타입 참조**로만 판정한다 — 런타임 주입 경로를 추론하지 않는다.

### 5.5 Archify 연동 수리

현재 `render_archify.py`는 실행되면 반드시 실패한다.

```python
# 현재 (틀림)
validate_command = [*command, "validate", str(ir_path)]
deliver_command = [*command, "deliver", str(ir_path), "--output", str(html_path)]

# 실제 Archify CLI
# archify validate <diagram-type> <input.json> [--json]
# archify deliver  <diagram-type> <input.json> <output.html> [--json]
```

또한 GX IR을 Archify 타입 IR로 바꾸는 변환기가 없다. 다음을 수행한다.

1. Archify를 실제 설치해 `demo`가 생성하는 예제 IR로 스키마를 실측한다 (선행 spike).
2. `to_archify.py`에 `service` → Archify `architecture`, `sequence` → Archify `sequence` 변환을 구현한다.
3. 명령 조립을 실제 시그니처로 고친다.
4. 가짜 실행 파일이 아닌 실제 Archify로 검증한다.

Archify는 계속 **선택 의존성**이다. 미설치 환경에서는 mermaid → static 폴백이 동작하고, 영수증은 Archify 성공으로 표현하지 않는다.

### 5.6 phase-complete 제안 게이트

`gx-dev`·`gx-tdd`의 `phase-complete.md`에 Step 5.5를 추가한다. Step 5(진행 상태 완료) 직후, Step 6(다음 단계) 직전이다.

헤드리스 판정: `${DEV_DIR}/ralph.lock`이 존재하거나 `pipeline: gx-ralph`이면 질문하지 않고 strict no-op으로 건너뛴다.

대화형 질문:

```
이번 사이클에서 구현된 구조를 시각화할까요?
  1. 이번 세션 개발분만       이번 사이클이 변경한 파일의 체인만
  2. 전체 갱신 + 이번 세션 반영  누적 맵을 증분 갱신 (권장)
  3. 아니요
```

`.scan-manifest.json`이 없는 상태에서 2번을 선택하면 최초 전체 스캔임을 먼저 알리고 재확인한다.

이 게이트의 실패·취소는 commit·PR 결과를 바꾸지 않는다. Step 1~2가 이미 실패했다면 시각화 성공으로 그 실패를 덮지 않는다.

## 6. 실패 처리

- 스캔이 0개 노드를 반환하면 빈 IR을 쓰지 않고 `missing_inputs`에 언어 감지 실패를 기록하고 중단한다.
- 병합 후 검증 실패 시 이전 `service.ir.json`을 덮어쓰지 않는다.
- 모든 백엔드 실패 시 stale HTML을 제거하고 `failed` 영수증을 남긴다.
- 파이프라인 안에서 호출된 시각화의 실패는 `visualization_status: failed`로만 보고하고 파이프라인을 실패시키지 않는다.

## 7. 보안·개인정보

- 출력은 프로젝트 내부 경로에만 저장한다.
- 노드 label·HTML·영수증에 커넥션 문자열, 토큰, 개인정보를 복사하지 않는다.
- SQL 본문은 IR에 싣지 않는다. 테이블명만 추출한다.

## 8. 수용 기준

1. `scan_entrypoints.py`가 Java Spring 픽스처에서 screen·api·service·repository·table 노드를 각각 file:line 근거와 함께 추출한다.
2. 같은 입력을 두 번 스캔하면 노드 ID와 정렬 순서가 동일하다.
3. `merge_map.py`가 변경 파일의 노드만 교체하고, 삭제된 파일의 노드와 그 노드를 가리키는 edge를 함께 제거한다.
4. 병합 결과가 `validate_ir.py` 검증을 통과한다. 끊긴 edge가 남으면 검증이 실패하고 기존 IR이 보존된다.
5. `to_archify.py`가 GX IR을 Archify `architecture`·`sequence` 입력으로 변환하고, `render_archify.py`가 실제 CLI 시그니처로 호출한다.
6. Archify 미설치 환경에서 mermaid 또는 static HTML과 영수증이 생성된다.
7. `gx-dev`·`gx-tdd`의 complete가 대화형에서 시각화를 제안하고, `ralph.lock` 존재 시 질문 없이 건너뛴다.
8. 비-git 프로젝트에서 mtime+size 지문으로 증분 갱신이 동작한다.
9. `--scope session`은 `${DEV_DIR}/visual/`에, `--scope all`은 `docs/architecture/`에 쓴다. 세션 출력이 누적 맵을 덮어쓰지 않는다.
10. `--scope session` HTML에 생성 시각과 커밋 해시 스냅샷 배너가 있고, `--scope all` HTML에는 없다.
11. `sync-codex-resources.py --check`와 `lint-consistency.sh`가 통과한다.
