# gx-visualize 사용 가이드

`gx-visualize`는 GX 작업 산출물을 근거가 추적되는 JSON IR과 한국어 HTML로
변환합니다. 사용자가 `--visualize` 또는 시각화를 명시한 경우에만 실행하며,
시각화 결과가 개발·리뷰·커밋 게이트를 대신하지 않습니다.

## 요청하기

직접 호출 형식은 다음과 같습니다.

```text
gx-visualize <trace|progress|impact|service|sequence> [--input <path>] [--output <path>] [--backend auto|archify|mermaid|static]
```

다음 자연어도 명시적 요청으로 인식합니다.

- “시각화 포함”
- “구조를 그림으로 보여줘”
- “변경 영향도를 시각화해줘”

명시 요청이 없으면 자동 실행하지 않습니다. 뷰를 쓰지 않은 요청은 다음 기준으로
라우팅하며, 서로 다른 뷰의 단서가 섞이면 먼저 사용자에게 확인합니다.

| view | 질문과 대표 표현 | 주요 입력 | 지원 범위 |
|---|---|---|---|
| `trace` | 요구사항 추적, 기능·데이터·테스트 연결 | `prd.md`/AN-02, `design.md`/AN-03, DE-08, DE-13 | 1차 필수 |
| `progress` | 진행 상태, Phase·Gate·검증 상태 | `state.md`, `summary.md`, `self-check.md` | 1차 필수 |
| `impact` | 변경 영향도, 추가·삭제·변경·이동 | `diff.txt`, `codemap.md`, `design.md` | 1차 필수 |
| `service` | 구조, 서비스·화면·API·테이블 관계 | `codemap.md`, 설계서, 프로젝트 context | 계약 지원 |
| `sequence` | 호출 순서 | 설계서와 명시된 호출 근거 | 계약 지원 |

`trace`, `progress`, `impact`는 1차 필수 구현 범위이고, `service`와
`sequence`는 입력·출력 계약을 정의한 후속 범위입니다. 두 계약 지원 뷰는 근거가
부족하면 관계를 추정하지 않으며 `missing_inputs`와 실패 상태를 반환합니다.

일반적인 “시각화 포함”은 현재 phase가 design이면 `service`, review이면
`impact`, 그 외에는 `progress`를 기본값으로 사용합니다.

## 출력과 근거

기본 출력 디렉터리는 `.dev/{branch-slug}/visual/`입니다. 성공 또는 폴백한 실행은
같은 이름의 세 파일을 만듭니다.

```text
{view}.json
{view}.html
{view}.receipt.json
```

검증 또는 입력 감지에 실패하면 HTML은 만들지 않거나 기존 HTML을 제거하고
`failed receipt`를 남깁니다. 입력 감지 단계에서 IR을 만들 수 없었다면 IR도 없을
수 있으며, IR 검증 실패라면 진단을 위해 생성된 IR만 남을 수 있습니다. 모든
백엔드 실패에서는 검증된 IR과 failed receipt를 보존하되 HTML을 제거합니다.
따라서 실패 receipt와 최종 보고는 존재하지 않는 산출물 경로를 성공 결과처럼
기록하지 않습니다.

최종 보고에는 다음 필드가 포함됩니다.

- `view`: 요청한 뷰
- `backend`: 실제 HTML을 만든 `archify|mermaid|static`
- `html_path`: HTML 경로. 실패하면 `null`
- `ir_path`: 생성한 JSON IR 경로. 입력 감지 전에 실패하면 `null`
- `receipt_path`: 검증·백엔드 시도 영수증 경로
- `validation_status`: `verified|fallback|failed`
- `missing_inputs`: 찾지 못한 필수 입력 그룹

노드의 근거는 텍스트 파일이면 실제 파일·라인을, XLSX/PDF이면 원본 위치를
나타내는 `locator`를 사용합니다. 근거가 없는 내용은 위치를 꾸미지 않고
`inferred`로 표시합니다. 운영 토폴로지나 호출 관계도 파일명만 보고 추정하지
않습니다.

## 백엔드별 예시

기본값인 `auto`는 현재 환경에서 실제로 실행 가능한 백엔드를 선택합니다.
Archify가 없으면 사용자에게 묻지 않고 `npx -y skills add tt-a1i/archify -g`로
1회 자동 설치를 시도합니다. 설치 성공은 exit code가 아니라 `doctor` 결과로만
판정하며, 설치·재탐지가 모두 실패해도 예외 없이 Mermaid → 정적 HTML로 넘어갑니다.
Mermaid는 자동 설치하지 않습니다. 설치 여부·버전·CLI 경로는 실제 probe 또는
실행 영수증으로만 보고합니다.

### Archify 사용 가능

```text
gx-visualize trace --backend auto
```

Archify의 validate와 deliver가 모두 성공하고 non-empty HTML이 확인된 경우에만
`backend: archify`, `validation_status: verified`로 보고합니다. 영수증에는 실제
명령, 종료 코드, stdout/stderr와 artifact 경로가 남습니다.

### Archify 없음

```text
gx-visualize impact --backend auto
```

Archify가 발견되지 않거나 실행에 실패하면 Mermaid를 시도하고, 이어서 static을
시도합니다. 성공한 폴백은 `validation_status: fallback`이며 `backend`에는 실제
HTML 생성자를 기록합니다. 최초 진단과 시도 순서를 영수증에 보존합니다.
실패한 Archify를 성공으로 표시하지 않습니다.

### 정적 HTML 폴백 지정

```text
gx-visualize progress --backend static
```

외부 렌더러 없이 self-contained HTML을 만듭니다. 노드 목록, 관계 표, 상태 배지,
근거 카드를 포함하므로 Mermaid 실행이 불가능한 환경에서도 내용을 확인할 수
있습니다.

## 누적 아키텍처 맵

`service`·`sequence` 뷰는 `--scope`로 출력 위치가 갈립니다. 기본값은 `session`입니다.

| scope | 위치 | 성격 |
|---|---|---|
| `session` | `.dev/{branch-slug}/visual/` | 그 시점 스냅샷, 갱신하지 않음 |
| `all` | `docs/architecture/`(`--map-dir`로 변경 가능) | 매 실행 전체를 다시 스캔, 도메인별로 분할 |

두 산출물은 한 폴더에 섞이지 않습니다. `--scope session` HTML에는 생성 시각과 커밋 해시가 담긴 스냅샷 배너가 붙고, `--scope all`에는 붙지 않습니다.

### `--scope all`의 산출물은 도메인별입니다

실제 저장소 규모를 한 장으로 그리면 Archify 검증이 대량으로 실패하고 사람이 읽기도 어렵습니다. 그래서 `--scope all`은 노드를 도메인별로 나눠 각각 별도 문서로 그립니다 — 파일명은 `{domain}.ir.json`·`{domain}.html`(예: `auth.ir.json`, `auth.html`)입니다. `--scope session`은 분할하지 않습니다. `--domain`을 주면 그 도메인만 그리고, 생략하면 찾은 전 도메인을 각각 그립니다.

**도메인마다 개별로 Archify에 넣어 판정합니다 — 전부 성공 아니면 전부 실패로 묶지 않습니다.** 한 저장소 안에서 어떤 도메인은 그림이 나오고 어떤 도메인은 표(폴백)로 떨어지는 것이 정상입니다. 예를 들어 실제 GX 프로젝트(kreb-grep-2025-admin, Java 456개 파일)를 도메인 8개로 나눴을 때 6개(auth·code·config·mail·role·security)는 Archify 그림으로 통과했고, 나머지 2개(reb 44노드, user 13노드)는 노드 수가 많아 정적 HTML 표로 폴백했습니다 — 이 비율은 해당 저장소 한 곳의 실측값이며 다른 프로젝트에 그대로 적용되는 일반적 보장이 아닙니다. 실패한 도메인만 Mermaid → 정적 HTML로 폴백하고, 통과한 도메인의 그림은 그대로 둡니다.

테이블 노드는 파일 경로로 도메인을 정하지 않고, 자신을 참조하는 모든 도메인에 복제됩니다. 도메인 경계를 넘는 엣지는 어느 한 장에도 온전히 담기지 않으므로 조용히 지우지 않고, 관련된 각 도메인 IR의 `missing_inputs`에 `cross-domain-edge`로 남기며 건수를 보고에 포함합니다. 검증에 실패한 도메인의 이전 `${MAP_DIR}/{domain}.ir.json`은 덮어쓰지 않으므로 다른 도메인의 갱신에는 영향을 주지 않습니다.

### 스캔 범위와 변경 감지

`--scope all`은 매 실행마다 프로젝트 전체를 `scripts/scan_entrypoints.py`로 다시 스캔합니다 — 저장소 규모에 따라 시간이 걸릴 수 있으므로 실행 전에 사용자에게 먼저 알립니다. `--scope session`은 호출자(gx-dev·gx-tdd phase-complete 등)가 `--input-path`로 반복 전달한 이번 사이클 변경 파일 목록 중 `.java`·`.jsp`·`.xml`만 스캔 대상으로 삼습니다.

스캔이 UTF-8로 읽지 못한 소스는 CP949로 재시도합니다(오래된 한국어 JSP·Java 코드베이스에 흔합니다). 둘 다 실패한 파일은 크래시시키지 않고 결과의 `skipped`에 담아 보고합니다. 스캔이 0개 노드를 반환하면 빈 IR을 쓰지 않고 `missing_inputs`에 언어 감지 실패를 기록한 뒤 중단합니다.

## 실패와 문제 해결

1. `missing_inputs`를 확인합니다. `progress`에는 `state`, `impact`에는 `diff` 같은
   필수 논리 입력이 필요합니다.
2. receipt의 `errors`와 `attempts`에서 IR 검증 오류, 실행 명령, 종료 코드,
   stdout/stderr를 확인합니다.
3. 근거 오류라면 프로젝트 루트 상대경로와 실제 파일·라인 또는 `locator`가
   일치하는지 확인합니다.
4. 자동 선택이 실패하면 `--backend static`으로 재실행합니다. 보고서에는 사용한
   재실행 명령을 그대로 남깁니다.

gx-dev의 선택 단계에서 모든 백엔드가 실패하면
`visualization_status: failed`와 실패 이유, receipt 경로를 기록하고 본
개발·리뷰·커밋 파이프라인은 계속할 수 있습니다. 사용자가 “시각화만” 요청한
경우에는 `html_path: null`, 누락 입력, 마지막 진단, 재실행 명령을 반환하며 성공한
것처럼 표현하지 않습니다. 이전 실행의 stale HTML도 성공 근거로 재사용하지
않습니다.
