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
- 누적 맵의 git 지속화와 파일 지문 기반 증분 갱신 — **2026-09-21 폐기 (Task 11)**: 매 실행 전체 재스캔으로 대체. §5.2 참고
- Archify 백엔드 수리 (명령 시그니처 + IR 변환기)
- `gx-dev`·`gx-tdd` phase-complete의 시각화 제안 게이트

### 제외

- 런타임 토폴로지·실제 트래픽·배포 구조 추론
- Archify 렌더러 코드의 저장소 복제
- 진입점 체인 밖의 유틸리티·DTO·설정 클래스 노드화
- 파일 리네임 추적 (삭제 + 추가로 표현한다)
- Java·JSP 외 언어의 스캐너 (후속 범위)

### 후속 범위 — 연기된 Archify 다이어그램 타입 2종

둘 다 사용자 확인을 거쳐 이번 범위에서 **명시적으로 연기**했다. 구현에 필요한 실측 사실을 여기 남긴다 — 나중에 다시 조사하지 않기 위함이다.

**sequence** (2026-09-18 연기). `~/.agents/skills/archify/schemas/sequence.schema.json`은 `[schema_version, diagram_type, meta, participants, messages]`를 요구하고 `additionalProperties: false`이며 `components`·`connections`·`layout`을 **정의하지 않는다**. 즉 architecture 변환기를 재사용할 수 없고 participants/messages 전용 변환기가 필요하다. 그때까지 `sequence` view는 `_DIAGRAM_TYPES`에 없으므로 `not_applicable` 경로로 폴백한다. 연기 근거: 요구의 중심은 아키텍처 맵이며 반쯤 된 sequence 변환기보다 정확한 architecture 맵이 낫다.

**dataflow** (2026-09-18 연기, 테이블 수준으로 범위 확정). 데이터가 어떻게 처리되어 어느 테이블에 저장되는지를 보여주는 뷰다.

- Archify 쪽 요구: `dataflow.schema.json`의 필수는 `[schema_version, diagram_type, meta, stages, nodes, flows]`. `nodes` 필수는 `id, type, label, stage, row`, `flows` 필수는 `from, to, label`이고 `flows.classification`으로 민감도(PII 등)를 표시할 수 있다. `stages`는 파이프라인 단계(열)를 정의한다.
- **우리가 이미 가진 것**: `scan_entrypoints.py`의 `_scan_mapper_xml`이 MyBatis 구문 단위로 테이블명과 방향을 뽑는다 — `select` → `reads`, `insert|update|delete` → `writes`. 따라서 "어느 기능이 어느 테이블을 읽고 쓰는가"는 추가 스캔 없이 기존 데이터를 재구성하면 된다. 이것이 테이블 수준 dataflow의 뼈대다.
- **컬럼 수준은 범위 밖**이다. §8의 "SQL 본문을 IR에 싣지 않는다"는 규칙은 유지하되, 컬럼 식별자와 리터럴 값을 구분하는 정제 여지가 있다 — 위험한 것은 값(`WHERE ssn = '...'`)이고 컬럼명은 스키마 정보다. 다만 eGov MyBatis는 `SELECT *`와 동적 `<if>` SQL이 지배적이라 정규식으로는 부분만 추출되며, **부분을 완전한 것처럼 표시하면 부정확한 설계도가 된다.** 컬럼 수준을 하려면 추출 실패 지점을 "없음"과 구분해 표시하는 규약이 선행되어야 한다.

## 4. 결정 사항

| # | 결정 | 근거 |
|---|---|---|
| D1 | complete 종료 후 **항상 묻되 헤드리스는 자동 skip** | 대화형에서 발견성을 확보하되 `ralph.lock` 세션은 응답할 사용자가 없다 |
| D2 | 근거는 **코드 스캔 + 한국어 라벨 보강** | 플러그인 도입 이전 레거시 코드가 맵에 들어와야 한다 |
| D3 | 추출 단위는 **진입점 체인만** | 유틸·DTO를 넣으면 그림이 엉키고 비용·환각 위험이 커진다 |
| D4 | `gx-visualize` **확장** (새 스킬 아님) | IR·검증기·백엔드·폴백 4종 중복을 피한다 |
| D5 | ~~누적 맵은 JSON + HTML 둘 다 커밋~~ → **2026-09-21 반전: 아무것도 커밋하지 않는다(단발성)** | 사용자 결정. 원본 스킬은 커밋하지 않았고(`55e427e`의 SKILL.md에 커밋 언급 0건) 저장소 역사에도 `.dev/*/visual/*` 커밋이 0건이다. 커밋은 이번 계획이 새로 넣은 것이었으며, 실측(실행당 HTML 4.70 MB·GSEED 약 16 MB, HEAD SHA 내장으로 매 실행 전량 변경)을 보고 사용자가 원본 동작으로 되돌렸다. 호출할 때마다 만들고 보고하고 끝낸다 |
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
[분할]  split_domains.py  (도메인별 IR로 분리)
            ↓  {domain}.ir.json
[검증]  validate_ir.py  — edge 참조 무결성을 확인한다
            ↓
[렌더]  archify → mermaid → static
            ↓
.dev/architecture/
  {domain}.ir.json        정본 (단발성, 도메인별)
  {domain}.html           렌더 결과 (단발성, 도메인별)
```

> **2026-09-21 폐기** — 위 다이어그램은 최초 설계 당시(병합·매니페스트 기반 증분 갱신)를 반영한다. 실측(전체 3.155초 vs 증분 관문 126.9초)과 C1(무손실 누적 IR 부재)로 사용자가 증분 폐기를 결정했다(Task 11). 현재 `--scope all`은 매 실행 프로젝트 전체를 다시 스캔하고, `merge_map.py`와 `.scan-manifest.json`은 존재하지 않는다. 위 도식은 현재 파이프라인이다 — 병합·매니페스트 단계가 사라진 이유의 기록은 §5.2·§5.3에 남긴다.

### 5.1 산출물 위치 — scope가 위치를 결정한다

`--scope`가 출력 디렉터리를 가른다. 파일명은 기존 `{view}.json`·`{view}.html` 규칙을 그대로 쓴다.

| scope | 위치 | 성격 | 독자 |
|---|---|---|---|
| `session` | `${DEV_DIR}/visual/` | 그 시점 **스냅샷**, 갱신하지 않음 | PR 리뷰어 — 해당 PR diff에 함께 올라간다 |
| `all` | `.dev/architecture/` (기본값, `--map-dir`로 변경) | **매 실행 전체 재스캔**으로 갱신 (2026-09-21 폐기: 증분 갱신 → §5.2) | 사업부 전체, 신규 투입자 |

둘을 한 폴더에 섞지 않는다. 세션 산출물은 갱신되지 않으므로, 누적 맵과 같은 위치에 두면 낡은 그림을 최신으로 오인하게 된다. 폴더를 분리하면 이 혼동이 구조적으로 발생하지 않는다.

`session` 출력은 `trace`·`progress`·`impact`가 이미 쓰는 `${DEV_DIR}/visual/` 계약을 그대로 따른다. 새 경로 규칙을 만들지 않는다.

`session` HTML 상단에는 **스냅샷 배너**를 넣는다: 생성 시각과 `git rev-parse --short HEAD` 결과를 표시하고 "이 그림은 해당 시점의 스냅샷이며 갱신되지 않습니다"를 명시한다. 누적 맵(`all`)에는 배너를 넣지 않는다.

영수증(`*.receipt.json`)은 산출물과 같은 디렉터리에 남긴다. **D5 반전(2026-09-21) 이후 어떤 산출물도 커밋하지 않으므로** 영수증만 따로 분리할 이유가 사라졌다 — 원래 이 규정의 목적이 '영수증이 커밋되지 않게' 하는 것이었기 때문이다.

**알려진 비용**: self-contained HTML은 브랜치마다 수백 KB가 `.dev/`에 축적된다. 실제 크기를 측정한 뒤 억제 수단이 필요한지 판단한다 — 측정 전에 설정 항목을 추가하지 않는다.

### 5.2 스캔 매니페스트

> **2026-09-21 폐기** — 실측(전체 3.155초 vs 증분 관문 126.9초)과 C1(무손실 누적 IR 부재)로 사용자가 증분 폐기를 결정했다(Task 11). `.scan-manifest.json`은 더 이상 생성되지 않으며 `--scope all`은 매 실행 전체를 다시 스캔한다. 아래는 폐기된 설계이며, 왜 이런 구조를 시도했는지의 기록으로 남긴다.

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

### 5.5.1 설치 정책 — 묻지 않고 자동 설치

Archify가 없으면 **사용자에게 묻지 않고 자동 설치한다** (2026-09-18 사용자 결정). 이는 초기 설계의 "외부 네트워크나 자동 업데이트는 요구하지 않는다"를 뒤집는다.

```bash
npx -y skills add tt-a1i/archify -g
```

- 설치 경로는 `~/.agents/skills/archify`이고 `~/.claude/skills/archify`는 그 심링크다. **PATH에 `archify` 바이너리는 생기지 않는다** — 호출은 `node <설치경로>/bin/archify.mjs`다.
- 이 명령은 exit 0으로 끝나면서도 출력에 `PromptScript does not support global skill installation` 실패 2건을 포함한다. 다른 하네스용 설치를 건너뛴 것이므로 무해하다. **따라서 exit code로 성공을 판정하지 않고** `bin/archify.mjs` 존재와 `doctor` 결과로 판정한다.
- `dependencies`가 비어 있어 별도 `npm install`이 불필요하다.
- 설치 실패(사내망 차단·권한·오프라인)는 파이프라인을 실패시키지 않는다. 폴백하고, 시도한 명령·종료 코드·stderr를 영수증의 `attempts`에 남긴다.
- 설치는 **1회만 시도한다.** 실패를 매 호출마다 재시도하면 차단된 환경에서 호출마다 수 초가 낭비된다.

### 5.5.2 폴백의 정직성

Archify 미설치·설치 실패 시 mermaid → static 폴백이 동작하지만, **현재 폴백 경로에는 다이어그램이 없다** — mermaid 백엔드도 Mermaid 소스를 `<pre>`에 넣을 뿐 렌더하지 않는다. 따라서 폴백 HTML과 최종 report는 "다이어그램이 생성되지 않았다"를 명시하고 archify 설치 안내를 제시한다. 표와 그림을 같은 내용으로 표현하지 않는다.

### 5.5.3 확인된 제약 2건

- **한국어 UI 크롬 불가.** `meta.locale` enum이 `["en","zh-CN"]`이다. 노드 라벨·부라벨·카드는 자유 문자열이라 한국어가 정상 렌더되지만, Archify가 생성하는 범례 제목 등은 영어 또는 중국어만 가능하다. `en`을 사용한다.
- **비-git 프로젝트는 소스 근거를 실을 수 없다.** `component.sources`를 쓰면 `meta.repository{url, revision}`(revision은 40자 hex)과 실행 시 `--repo-root`가 필수이고, Archify가 경로 존재를 실제로 검증한다. 40자 SHA를 얻을 수 없으면 `sources`를 생략한다 — 렌더 자체는 성공한다.

상세 실측 근거는 [Archify IR 스키마 실측 보고](../../reports/2026-09-18-archify-ir-schema.md)에 있다.

### 5.6 phase-complete 제안 게이트

`gx-dev`·`gx-tdd`의 `phase-complete.md`에 Step 5.5를 추가한다. Step 5(진행 상태 완료) 직후, Step 6(다음 단계) 직전이다.

헤드리스 판정: `${DEV_DIR}/ralph.lock`이 존재하거나 `pipeline: gx-ralph`이면 질문하지 않고 strict no-op으로 건너뛴다.

대화형 질문:

```
이번 사이클에서 구현된 구조를 시각화할까요?
  1. 이번 세션 개발분만       이번 사이클이 변경한 파일의 체인만
  2. 전체 갱신 + 이번 세션 반영  누적 맵 전체를 다시 스캔해 갱신 (권장)
  3. 아니요
```

2번을 선택하면 프로젝트 전체를 다시 스캔하므로 저장소 규모에 따라 시간이 걸릴 수 있음을 먼저 알리고 재확인한다. (2026-09-21 폐기: 매니페스트 유무에 따른 최초/증분 구분 → §5.2)

이 게이트의 실패·취소는 commit·PR 결과를 바꾸지 않는다. Step 1~2가 이미 실패했다면 시각화 성공으로 그 실패를 덮지 않는다.

### 5.7 도메인 분할 — 실제 저장소 규모에서 확정 (2026-09-18)

실제 GX 프로젝트(`kreb-grep-2025-admin`, Java 456개)에 스캐너를 돌려 확정한 설계다. 픽스처가 아니라 현장 코드로 측정했다.

스캔 자체는 정확했다 — 86노드(api 30·service 20·repository 14·table 22), 86엣지, 전부 실제 `file:line` 근거를 가진다. 그러나 **전체를 한 장으로 그리면 Archify 검증이 109건으로 실패한다.** 대부분 연결선이 다른 박스를 관통하는 `clean-flow/edge-through-node`이고, 애초에 86노드 한 장은 사람이 읽을 수 없다.

**결정: `--scope all`은 도메인 단위로 나눠 그린다.** 측정 근거:

| 대상 | 노드 | Archify 검증 |
|---|---|---|
| code 모듈 | 15 | 통과 (문제 0건) |
| auth 모듈 | 7 | 통과 (문제 0건) |
| reb 모듈 | 32 | 실패 (8건) |
| 전체 한 장 | 86 | 실패 (109건) |

위 표는 구현 전에 돌린 probe로 잰 값이며, 분할 규칙이 확정되기 전이라 테이블을 연결된 것만 남기는 거친 필터를 썼다. 구현된 규칙(§5.7.1)으로 다시 재면 도메인 8개에 **6개 통과**(auth·code·config·mail·role·security), 2개 실패(reb 44노드, user 13노드)다 — 통과·실패의 구도는 같고 노드 수만 테이블 복제분만큼 커진다.

도메인 분할만으로 보통 규모 모듈은 깨끗해진다. 아주 큰 도메인은 여전히 실패하므로 **도메인별로 개별 판정하고 실패한 도메인만 폴백시킨다** — 전부 성공 아니면 전부 실패로 묶지 않는다. 한 저장소 안에서 어떤 도메인은 그림이, 어떤 도메인은 표가 나오는 상태가 정상이며 그 사실이 보고에 드러나야 한다.

### 5.7.1 함께 확정된 변환기 결함 2건

분할을 측정하는 과정에서 `to_archify.py`의 결함 2건이 드러났다. 둘 다 해법까지 실측으로 검증했다.

**결함 A — 같은 열 내부 엣지.** 스캐너는 `service → service`(5건)와 `repository → repository`(1건) 엣지를 낸다(예: `RefreshTokenRepository → RefreshTokenMapper`). `KIND_TO_COL`이 둘을 같은 열에 놓으므로 Archify의 `clean-flow/endpoint-side-direction` 규칙이 거부한다. §5.4의 규칙 표는 `calls`를 api→service, service→repository로만 규정하므로 **규칙 문서와 스캐너가 어긋나 있다**. 이 엣지는 실제 호출이므로 버리지 않는다 — Archify가 이미 지원하는 `fromSide`/`toSide`를 지정해 해결한다(타깃 row가 크면 `bottom`→`top`). 실측: auth 모듈 2건 → 0건.

**결함 B — sublabel 하한 초과.** 크기 계산이 `sublabel`을 제외했다. `sublabel`에 shrink-to-fit이 있는 것은 맞지만 **6px 하한까지만**이고 그 아래로는 Archify가 문서를 거부한다. 실제 API 경로(`GET /adm/v1/reb/versions/{targetGrcodeCd}/download/by-building-pk`)가 그 한계를 넘는다. 올바른 폭은 두 조건을 모두 만족해야 한다:

```
width >= textUnits(label) * 6.6 - 8
width >= textUnits(sublabel) * 6 * 0.6 + 8
cellW  = max(150, maxWidth - gapX + 8)
```

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
3. ~~`merge_map.py`가 변경 파일의 노드만 교체하고, 삭제된 파일의 노드와 그 노드를 가리키는 edge를 함께 제거한다.~~ **폐기 (Task 11, 사용자 결정 2026-09-21)** — §5.2 참고.
4. 병합 결과가 `validate_ir.py` 검증을 통과한다. 끊긴 edge가 남으면 검증이 실패하고 기존 IR이 보존된다.
5. `to_archify.py`가 GX IR을 Archify `architecture`·`sequence` 입력으로 변환하고, `render_archify.py`가 실제 CLI 시그니처로 호출한다.
6. Archify 미설치 환경에서 mermaid 또는 static HTML과 영수증이 생성된다.
7. `gx-dev`·`gx-tdd`의 complete가 대화형에서 시각화를 제안하고, `ralph.lock` 존재 시 질문 없이 건너뛴다.
8. ~~비-git 프로젝트에서 mtime+size 지문으로 증분 갱신이 동작한다.~~ **폐기 (Task 11, 사용자 결정 2026-09-21)** — §5.2 참고.
9. `--scope session`은 `${DEV_DIR}/visual/`에, `--scope all`은 `.dev/architecture/`에 쓴다. 세션 출력이 누적 맵을 덮어쓰지 않는다.
10. `--scope session` HTML에 생성 시각과 커밋 해시 스냅샷 배너가 있고, `--scope all` HTML에는 없다.
11. `sync-codex-resources.py --check`와 `lint-consistency.sh`가 통과한다.
