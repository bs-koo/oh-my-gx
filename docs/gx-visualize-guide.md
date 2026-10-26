# gx-visualize 사용 가이드

`gx-visualize`는 GX 작업 산출물을 근거가 추적되는 JSON IR과 한국어 HTML로
변환합니다. 사용자가 시각화를 명시한 경우에만 실행하며,
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
| `service` | 구조, 서비스·화면·API·테이블 관계 | 전체 코드 스캔, 프로젝트 용어집 | 1차 필수 |
| `sequence` | 호출 순서 | 설계서와 명시된 호출 근거 | 후속 범위 |

`service`는 코드 스캔부터 인덱스까지 구현되어 있습니다. `sequence`의 전용 Archify
변환기는 후속 범위이며 현재는 표·Mermaid 폴백으로 확인합니다. 근거가
부족하면 관계를 추정하지 않으며 `missing_inputs`와 실패 상태를 반환합니다.

일반적인 “시각화 포함”은 현재 phase가 design이면 `service`, review이면
`impact`, 그 외에는 `progress`를 기본값으로 사용합니다.

gx-dev·gx-tdd는 complete Step 5.5의 “아키텍처 맵 갱신” 선택으로 service를 호출합니다.
design/review 자동 호출이나 `--visualize` 플래그는 현재 계약이 아닙니다.
헤드리스에서는 완료 단계의 제안을 건너뜁니다.

## 출력과 근거

service 이외 뷰의 기본 출력 디렉터리는 `.dev/{branch-slug}/visual/`입니다. 성공 또는 폴백한 실행은
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
gx-visualize service --project-root <프로젝트 루트>
```

service에서 Archify의 validate와 deliver가 모두 성공하고 non-empty HTML이 확인된 경우에만
`backend: archify`, `validation_status: verified`로 보고합니다. 영수증에는 실제
명령, 종료 코드, stdout/stderr와 artifact 경로가 남습니다.

trace·progress·impact·sequence는 Archify 적용 대상이 아니므로 실행하지 않고
receipt에 `not_applicable`을 남긴 뒤 폴백을 사용합니다. trace를 Archify 성공
예시로 보고하지 않습니다.

### Archify 없음

```text
gx-visualize impact --backend auto
```

service에서 Archify가 발견되지 않거나 실행에 실패하면 Mermaid를 시도하고, 이어서 static을
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

## 아키텍처 맵

구조(`service`) 뷰는 매 실행 프로젝트 전체를 다시 스캔해 도메인별 아키텍처 맵을 만듭니다. 이번 작업분만 따로 그리는 모드는 없습니다 — 변경된 파일만 스캔하면 컨트롤러에서 서비스까지만 이어지고 체인이 끊기기 때문입니다. 이번 사이클에서 무엇이 바뀌었는지는 전체 맵 위에 표시합니다.

### 명령 하나로 만듭니다

```text
python scripts/build_map.py <프로젝트 루트> [--map-dir <출력 폴더>] [--changed-since <기준 ref>] [--domain <도메인>] [--labels <라벨 JSON>]
```

스캔부터 인덱스까지 이 명령이 모두 수행하고 JSON 보고를 출력합니다. gx-dev·gx-tdd 완료 단계에서 "아키텍처 맵 갱신"을 고르면 파이프라인이 기준 브랜치를 `--changed-since`로 넘겨 이 명령을 실행합니다. 전체 스캔은 저장소 규모에 따라 시간이 걸릴 수 있어 실행 전에 먼저 알립니다. 실측(kreb admin, 도메인 8개): 변경 표시를 포함해 약 2분 30초가 걸렸고, 대부분은 Archify가 그림 속 근거 링크를 저장소와 대조하는 시간입니다.

### 산출물은 폴더로 정리되고 인덱스 하나로 모입니다

```text
.dev/architecture/
  아키텍처-맵.html              ← 인덱스. 이것만 열면 전체가 보입니다
  global.ir.json                전체 노드와 도메인 간 관계
  run-manifest.json             이번 실행 결과의 정본
  domains/{domain}.html          도메인별 그림·표
  ir/{domain}.ir.json            GX IR (사람이 읽는 정본)
  receipts/{domain}.receipt.json 영수증
  receipts/{domain}.archify.json 중간 산출물(Archify를 시도한 도메인만)
  assets/mermaid.min.js          Mermaid로 그린 도메인이 있을 때만
```

`아키텍처-맵.html`은 도메인마다 이름·노드 수·백엔드(그림인지 표인지)·통과 여부·누락 건수를 카드로 요약하고 각 `domains/{domain}.html`로 링크합니다. 산출물은 커밋하지 않는 단발성이지만 디스크에는 실제로 쌓입니다 — 실측(SEF, 8도메인): 도메인당 약 800KB, 실행당 합계 약 4.70MB. 매 실행 전체를 다시 만들므로 오래된 산출물은 갱신·대체되고, 이번 스캔에 없는 도메인의 옛 산출물은 지워집니다.

### 이번 변경 표시

`--changed-since <기준 ref>`를 주면 기준 커밋과 현재를 같은 스캐너로 스캔해 비교합니다. 커밋하지 않은 변경도 현재 쪽에 포함됩니다.

| 표시 | 뜻 | 그림에서 |
|---|---|---|
| 신규 | 기준 이후 새로 생긴 노드·관계 | 라벨 앞 `[신규]`, 굵은 선 |
| 변경 | HTTP 경로나 나가는 관계가 달라진 노드 | 라벨 앞 `[변경]` |
| 삭제 | 기준에만 있던 노드·관계 | 인덱스와 해당 도메인의 변경 요약 |

호출 대상이 바뀌면 관계 변경으로 표시하지만, 계산식·문구만 바뀌어 추출 결과가 같으면 구조 변화는 없습니다. 각 도메인 배너가 기준과 신규·변경·삭제를 알려 주며 삭제만 있어도 변경 없음으로 표시하지 않습니다. git 저장소가 아니거나 기준을 찾지 못하면 맵은 그대로 만들고 표시를 생략한 이유를 알립니다.

### 도메인 분할

실제 저장소 규모를 한 장으로 그리면 Archify 검증이 대량으로 실패하고 사람이 읽기도 어렵습니다. 그래서 노드를 도메인별로 나눠 각각 별도 문서로 그립니다. `--domain`을 주면 그 도메인만 다시 그리고, 생략하면 찾은 전 도메인을 각각 그립니다.

한 도메인만 갱신해도 다른 도메인은 개요와 검색에 남습니다. 갱신하지 않은 페이지는 원래 생성 시각과 함께 이전 결과로 표시합니다. 아직 생성한 적 없는 도메인은 이동 링크가 비활성화되며, 전체를 최신 상태로 맞추려면 `--domain` 없이 실행합니다. `run-manifest.json`의 `domains`는 이번 렌더 결과이고 `map_domains`는 이 전체 상태를 담습니다.

**도메인마다 개별로 Archify에 넣어 판정합니다 — 전부 성공 아니면 전부 실패로 묶지 않습니다.** 한 저장소 안에서 어떤 도메인은 Archify 그림이, 어떤 도메인은 Mermaid 그림이 나오는 것이 정상입니다. 예를 들어 실제 GX 프로젝트(kreb-grep-2025-admin)를 도메인 8개로 나눴을 때(2026-09-28) 7개는 Archify 그림, 나머지는 Mermaid 그림으로 그려졌습니다 — 이 비율은 해당 저장소 한 곳의 실측값이며 다른 프로젝트에 그대로 적용되는 일반적 보장이 아닙니다. Mermaid 도메인도 `assets/mermaid.min.js`를 확보하면 브라우저에서 실제 다이어그램을 그립니다(소스는 접어서 함께 보존) — 확보하지 못하면 소스만 보여줍니다.

테이블 노드는 자신을 참조하는 모든 도메인에 복제됩니다. 도메인 경계를 넘는 엣지는 전체 IR에 보존하고 양쪽 상세에 외부 도메인 노드를 표시합니다. 해당 도메인으로 이동해 탐색을 이어갈 수 있으며 이미 확인한 관계를 `missing_inputs`로 세지 않습니다.

`run-manifest.json`이 이번 실행의 정본입니다. 디스크에 남은 과거 정상 HTML을 현재 성공으로 세지 않으며 보존된 과거 결과는 `last_good`로 구분합니다. 빈 스캔이나 없는 도메인도 실패 진단 인덱스를 남깁니다. `index_path`가 있다는 이유만으로 성공으로 판단하지 말고 `validation_status`를 함께 확인하세요.

백엔드 이름과 실제 제공 화면도 구분합니다. `capability`의 `diagram`·`table`·`failed`를 확인하고 Mermaid 자산이 없으면 표와 소스만 제공됨을 보고합니다. 브라우저 그림 생성이 실패해도 표와 근거는 읽을 수 있습니다.

### 스캔 범위

진입점 체인(화면 → API → 서비스 → 저장소 → 테이블)만 추출합니다. 서비스 인터페이스와 `{X}Impl` 구현체는 한 노드로 합치고, 이름이 `*Facade`인 클래스도 서비스 계층으로 봅니다. 유틸·DTO·설정 클래스는 넣지 않습니다.

스캔이 UTF-8로 읽지 못한 소스는 CP949로 재시도합니다. 둘 다 실패한 파일은 `skipped`, 해소하지 못한 관계는 `unresolved_edges`에 이유·파일·대상과 함께 남깁니다. 스캔이 0개 노드를 반환하면 `missing_inputs`에 `entrypoint-scan`을 기록하고 실패 진단 인덱스를 만듭니다.

Java Spring·JSP/Servlet·MyBatis/iBATIS XML 대상의 정적 분석이며 완전한 Java/SQL 파서가 아닙니다. `calls`는 메서드 본문에서 확인한 호출, `depends_on`은 주입된 타입 의존성입니다. SQL은 절별 읽기·쓰기와 스키마가 다른 동명 테이블을 구분합니다. 리플렉션·런타임 DI 선택·동적 테이블명·다른 언어의 전체 구조는 보장하지 않습니다.

### 읽는 순서

인덱스 → 도메인 → 기능/API 선택 → 관련 코드 → 파일·행 근거 순서로 탐색합니다. 도메인에서는 기능별 코드 탐색을 먼저 보여주고, 전체 관계도와 전체 근거 목록은 펼쳐서 확인합니다. API가 없는 도메인은 기존 그림·목록으로 시작합니다.

API·메서드·원래 클래스명·모든 HTTP 경로로 검색할 수 있습니다. 선택한 진입점에서 이어지는 API/화면·서비스·저장소/매퍼·테이블을 계층별로 모으고, 구성 요소를 선택하면 해당 코드와 연결 근거를 표시합니다. 타입 의존 선언은 기본 연결과 구분해 옵션으로 포함합니다. 다른 API나 공유 테이블을 거꾸로 따라가 관련 없는 기능을 섞지 않습니다. 연결이 없는 경우에는 ‘추출된 후속 연결 없음’으로 안내합니다.

서비스·저장소 연결은 클래스 단위이므로 선택한 메서드의 실제 실행 경로나 소요 시간을 확정한 결과가 아닙니다. 기능 선택·검색은 저장된 관계 데이터를 브라우저에서 계산하므로 모델을 추가 호출하지 않습니다. `#gx-feature-…` 주소로 선택 API를 공유할 수 있으며 기존 상세 링크도 유지합니다. 한국어 라벨을 적용해도 원래 심볼은 보존합니다. 작은 화면에서도 목록·코드 근거를 이용할 수 있고, 테마 선택은 유지됩니다.

## 실패와 문제 해결

1. `missing_inputs`를 확인합니다. `progress`에는 `state`, `impact`에는 `diff` 같은
   필수 논리 입력이 필요합니다.
2. receipt의 `errors`와 `attempts`에서 IR 검증 오류, 실행 명령, 종료 코드,
   stdout/stderr를 확인합니다.
3. 근거 오류라면 프로젝트 루트 상대경로와 실제 파일·라인 또는 `locator`가
   일치하는지 확인합니다.
4. service는 build_map 명령으로 재실행하고, 다른 뷰는 필요하면 `--backend static`으로 재실행합니다. 보고서에는 사용한
   재실행 명령을 그대로 남깁니다.

gx-dev의 선택 단계에서 모든 백엔드가 실패하면
`visualization_status: failed`와 실패 이유, receipt 경로를 기록하고 본
개발·리뷰·커밋 파이프라인은 계속할 수 있습니다. 사용자가 “시각화만” 요청한
경우에는 `html_path: null`, 누락 입력, 마지막 진단, 재실행 명령을 반환하며 성공한
것처럼 표현하지 않습니다. 이전 실행의 stale HTML도 성공 근거로 재사용하지
않습니다.
