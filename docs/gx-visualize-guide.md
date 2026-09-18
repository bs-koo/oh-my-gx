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

기본값인 `auto`는 현재 환경에서 실제로 실행 가능한 백엔드만 선택합니다.
Archify나 Mermaid를 설치하거나 자동 업데이트하지 않습니다. 설치 여부·버전·CLI
경로는 실제 probe 또는 실행 영수증으로만 보고합니다.

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
