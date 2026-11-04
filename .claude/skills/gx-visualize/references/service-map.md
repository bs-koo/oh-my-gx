> service 뷰를 선택했을 때만 SKILL.md의 라우터에서 필수로 읽는다. 번들 scripts는 이 파일 기준 ../scripts/이며 실제 설치 경로로 해석한다. 소비 프로젝트·출력 경로·변수는 원래 호출 값을 유지한다.

## 아키텍처 맵 (`service` 뷰)

`service` 뷰는 언제나 **프로젝트 전체를 다시 스캔해** `${MAP_DIR}/`(기본 `.dev/architecture/`)를 새로 만든다. 이번 작업분만 따로 그리는 모드는 없다 — 변경 파일만 스캔하면 컨트롤러 → 서비스에서 체인이 끊긴다(2026-09-28 콜드런). 이번 사이클에서 무엇이 바뀌었는지는 `--changed-since`로 전체 맵 위에 표시한다. 산출물은 단발성이며 커밋하지 않는다.

### 실행 — 명령 하나

전체 스캔은 저장소 규모에 따라 시간이 걸릴 수 있음을 먼저 알리고 실행한다.

```text
python ../scripts/build_map.py <PROJECT_ROOT> [--map-dir <MAP_DIR>] [--changed-since <REF>] [--domain <DOMAIN>] [--labels <LABELS_JSON>]
```

스킬 호출의 인자는 이 명령에 이렇게 옮긴다. `--project-root <PROJECT_ROOT>`는 첫 번째 위치 인자 `<PROJECT_ROOT>`가 된다 — `build_map.py`에는 `--project-root` 플래그가 없다. `--map-dir`·`--changed-since`·`--domain`·`--labels`는 이름 그대로 넘긴다. `--map-dir`를 생략하면 `<PROJECT_ROOT>/.dev/architecture/`에 쓴다. 상대경로 `--map-dir`는 명령을 실행한 현재 폴더 기준이므로 절대경로로 넘긴다.

이 명령은 도메인마다 Archify 검증·전달을 거쳐 몇 분이 걸릴 수 있다(kreb admin 도메인 8개 실측 약 2분 30초). 명령 실행의 시간 제한을 10분(600000ms)으로 두거나 백그라운드로 실행하고 끝날 때까지 기다린다. 제한에 걸려 끊겼으면 같은 명령을 다시 실행한다 — 매번 전체를 다시 만들므로 결과는 같다.

이 명령이 스캔 → 변경 표시 → 라벨 적용 → 도메인 분할 → 도메인별 검증·렌더(Archify, 실패하면 Mermaid → static) → Mermaid 자산 확보 → 인덱스 생성을 모두 수행하고 JSON 보고를 stdout에 낸다. 단계를 손으로 나눠 실행하거나 중간 파일을 직접 만들지 않는다. 종료 코드는 `validation_status`가 `failed`면 1, 아니면 0이다.

- `--changed-since <REF>`: `<REF>`와 HEAD의 공통 조상 이후 새로 생기거나 바뀐 구조를 표시한다. gx-work·gx-tdd Step 5.5는 `BASE_BRANCH`를 넘긴다. 단독 호출에서는 사용자가 "이번 브랜치에서 바뀐 것"처럼 비교 기준을 말했을 때만 넘기고, 아니면 생략한다. git 저장소가 아니거나 기준을 정할 수 없으면 맵은 그대로 만들고 표시만 생략하며, 보고의 `changes.reason`에 이유가 남는다. 사용자가 비교를 원하지만 기준 브랜치를 말하지 않았으면 추측하지 말고 묻는다.
- `--labels <LABELS_JSON>`: 한국어 라벨을 붙일 때만 쓴다. `context/{도메인}/glossary.md`에서 스캔 라벨과 **정확히 같은 이름**인 항목만 `{"스캔 라벨": "한국어 라벨"}`로 만들어 `${MAP_DIR}/labels.json`에 쓴다. 스캔 라벨은 클래스명 또는 `클래스.메서드`다. 필요하면 `python ../scripts/scan_entrypoints.py <PROJECT_ROOT> --output <MAP_DIR>/scan.json` 결과의 `label`을 읽는다. 부분 일치·추측으로 항목을 만들지 않는다. 원래 심볼은 `symbol`에, API의 HTTP 경로는 `technical_label`에 보존한다.
- `--domain <DOMAIN>`: 전체 스캔에서 해당 도메인의 렌더링을 선택한다. manifest의 `domains`는 이번 렌더 결과, `map_domains`는 보존된 다른 도메인을 포함한 전체 맵 상태다. 갱신하지 않은 결과에는 `freshness: retained`와 원래 생성 시각을 표시하며 이번 성공으로 세지 않는다. 아직 생성하지 않은 도메인은 링크를 비활성화한다. 전체를 갱신하려면 `--domain` 없이 실행한다.
- `--map-dir <MAP_DIR>`: 출력 폴더. 프로젝트 밖 경로는 사용자가 명시했을 때만 쓴다.

### 출력 구조 — `아키텍처-맵.html` 하나만 열면 된다

```text
${MAP_DIR}/
  아키텍처-맵.html              ← 인덱스. 이것만 열면 된다
  global.ir.json                도메인 경계를 포함한 전체 관계
  run-manifest.json             이번 실행 상태와 도메인별 결과의 정본
  domains/{domain}.html          도메인별 그림·표
  ir/{domain}.ir.json            GX IR (사람이 읽는 정본)
  receipts/{domain}.receipt.json 영수증
  receipts/{domain}.archify.json 중간 산출물(Archify를 시도한 도메인만)
  assets/mermaid.min.js          Mermaid로 폴백한 도메인이 있을 때만
```

### 기능별 코드 탐색

API·화면 진입점이 있는 도메인은 기능 선택 화면을 먼저 제공한다. API·메서드·모든 HTTP 경로로 검색하고, 선택한 진입점에서 이어지는 코드와 근거만 확인한다. 탐색은 생성된 관계 데이터를 브라우저에서 처리하므로 API를 선택할 때 모델을 다시 호출하지 않는다.

기본 연결은 `calls`·`requests`·`reads`·`writes`다. `depends_on`은 ‘타입 의존성 후보도 포함’으로 별도 선택한다. 다른 API, 공유 테이블의 역방향 관계, 외부 도메인을 따라 무관한 기능을 합치지 않는다. 서비스·저장소가 클래스 단위이므로 후속 연결은 선택한 API의 메서드별 실행 경로로 단정하지 않는다. 실제 요청 시간이나 메서드 변경 영향을 확정하려면 별도 메서드 색인·실측 근거가 필요하다.

전체 도메인 관계도와 구성 요소·관계·진단 목록은 펼쳐서 확인한다. 기존 `gx-detail-` 깊은 링크는 접힌 목록을 열고 해당 근거로 이동한다. API가 없는 도메인과 다른 뷰는 기존 목록·그림을 제공한다. JavaScript가 없을 때도 전체 관계도와 근거 목록은 읽을 수 있다.

### 무엇이 표시되는가

`--changed-since`를 주면 기준 커밋의 소스를 임시 폴더에 꺼내 같은 스캐너로 스캔하고, 두 결과를 노드 ID로 비교한다. 작업 트리·인덱스는 건드리지 않고, 커밋하지 않은 변경도 현재 쪽에 포함된다.

| 표시 | 판정 | 그림에서 |
|---|---|---|
| 신규 | 현재 스캔에만 있는 노드·관계 | 라벨 앞 `[신규]`, 초록 채움(Mermaid), 굵은 선 |
| 변경 | 양쪽에 있고 HTTP 경로(`technical_label`)나 나가는 관계가 달라진 노드 | 라벨 앞 `[변경]`, 노랑 채움(Mermaid) |
| 삭제 | 기준에만 있는 노드·관계 | 인덱스·해당 도메인의 변경 요약과 보고에 목록으로 표시 |

구조가 바뀐 것만 표시한다. 메서드 본문에서 호출 대상이 바뀌면 관계 변경으로 잡히지만, 계산식·문구만 바뀌어 추출된 노드·관계가 같으면 구조 변경은 없다. 각 도메인 배너는 기준 ref·커밋과 신규·변경·삭제를 보여 준다. 삭제만 있어도 변경 없음으로 표시하지 않는다. 인덱스의 "이번 변경" 절이 바뀐 도메인과 항목을 모아 보여 준다.

### 도메인 분할

실제 저장소 규모(86노드)를 한 장으로 그리면 Archify 검증이 대량으로 실패하고 사람이 읽을 수도 없다(설계서 §5.7). 그래서 노드를 도메인별로 나눠 각각 별도 문서로 그린다.

- 도메인은 파일 경로에서 계층 폴더(`controller`·`service`·`facade`·`repository`·`dao`·`mapper`·`web`·`api`) 바로 앞 세그먼트다. 서비스 인터페이스와 `{X}Impl`은 한 노드로 합쳐지고, 이름이 `*Facade`인 클래스는 서비스 계층으로 본다. 추출 규칙은 [진입점 체인 추출 규칙](entrypoint-rules.md)을 읽는다.
- 테이블 노드는 자신을 참조하는 모든 도메인에 복제된다. 도메인 경계를 넘는 엣지는 전체 IR에 보존하고, 양쪽 상세에는 `external_domain`을 가진 경계 노드를 넣어 원래 도메인으로 이동할 수 있게 한다. 이미 확인한 관계이므로 `missing_inputs`로 세지 않는다. `cross_domain_edge_count`는 중복 복제 전 실제 경계 엣지 수다.
- **도메인마다 개별로 Archify에 넣어 판정한다.** 한 저장소 안에서 어떤 도메인은 Archify 그림이, 어떤 도메인은 Mermaid 그림이 나오는 것이 정상이며 보고에 드러난다. Mermaid로 떨어진 도메인이 있으면 `assets/mermaid.min.js`를 1회 확보해 브라우저에서 실제 그림으로 그린다. 확보하지 못하면 소스만 보이는 HTML이 최종 상태다.
- 이번 실행 결과는 `run-manifest.json`으로 판정한다. 이전 파일이 남아 있어도 현재 성공으로 재사용하지 않는다. 보존한 과거 정상 결과는 `last_good`로 구분한다. 전체 실행에서는 이번 스캔에 없는 도메인의 이전 산출물을 정리한다.
- 스캔은 UTF-8로 읽지 못한 소스를 CP949로 재시도하고, 둘 다 실패한 파일은 `skipped`에 담는다. 관계를 해소하지 못한 엣지는 `unresolved_edges`로 남는다 — "노드가 없다"와 "관계를 해소하지 못했다"는 다른 사실이다. SQL 본문은 IR에 담지 않는다.
- 스캔이 **0개 노드**를 반환하면 `missing_inputs: ["entrypoint-scan"]`으로 실패하고, 실패 이유를 볼 수 있는 인덱스와 실행 manifest를 남긴다. 빈 결과를 정상 아키텍처로 보고하지 않는다.

### 보고

`build_map.py`의 JSON 보고가 `service` 뷰의 최종 report다. 도메인이 여럿이라 단일 경로 필드를 쓰지 않는다.

| 필드 | 내용 |
|---|---|
| `view` | `service` |
| `map_dir`, `index_path` | 출력 폴더와 `아키텍처-맵.html` 경로. 빈 스캔·없는 도메인도 실패 진단 인덱스를 남긴다. 경로 존재가 성공을 뜻하지 않으므로 `validation_status`를 함께 읽는다 |
| `validation_status` | 도메인 하나라도 `failed`거나 도메인이 없으면 `failed`, 아니면 `fallback`이 하나라도 있으면 `fallback`, 전부 Archify면 `verified` |
| `domains[]` | 도메인마다 `domain`, `backend`, `capability`, `validation_status`, `html_path`, `ir_path`, `receipt_path`, `missing_inputs`, `added`, `changed`, 실패한 도메인에는 `errors`; 보존된 과거 결과는 `last_good` |
| `map_domains[]` | 전체 개요에 표시할 상태. 이번 결과와 `freshness: retained`인 기존 결과, 아직 생성하지 않은 `not_generated` 항목을 구분한다. `domains[]`의 이번 실행 성공 판정을 대신하지 않는다 |
| `changes` | `--changed-since`가 없으면 `null`. 있으면 `available`, `base_ref`, 그리고 `base_commit`·`added`·`changed`·`added_edges`·`removed[]`·`removed_edges[]` 또는 `reason` |
| `cross_domain_edge_count` | 전체 IR과 경계 노드로 보존한 도메인 간 엣지 수 |
| `unresolved_edge_count`, `skipped` | 스캔 진단 |
| `mermaid_asset` | Mermaid 폴백 도메인이 있을 때만: `available`, `attempts` |
| `missing_inputs` | 스캔이 0개 노드면 `["entrypoint-scan"]` |
| `reason` | 실패했을 때만: 실패 이유(스캔 0개 노드, 찾지 못한 도메인) |
| `labels_applied` | `--labels`로 바꾼 노드 수 |

사용자에게는 먼저 `index_path`(`아키텍처-맵.html`)를 안내하고, 도메인별 `backend`·`validation_status`, `changes` 요약(신규·변경·삭제 수 또는 생략 이유), `cross_domain_edge_count`·`unresolved_edge_count`·`skipped`를 그대로 전한다. Archify가 아닌 도메인을 Archify 성공으로 표현하지 않는다.

백엔드 이름과 실제 표시 능력은 구분한다. `capability`에서 `diagram`·`table`·`failed`를 확인하고, Mermaid 자산을 확보하지 못했으면 그림 대신 표와 소스가 제공됨을 알린다. 브라우저에서 그림 렌더가 실패해도 읽을 수 있는 표·근거를 유지한다.

### 읽는 순서와 분석 범위

인덱스의 대표 API·도메인 간 관계에서 시작해 도메인 → 노드 → 연결된 노드 → 파일·라인 근거로 이동한다. 검색은 표시명·원래 심볼·HTTP 경로를 함께 찾는다. 작은 화면에서는 그림을 축소해 글씨를 읽기 어렵게 만들기보다 스크롤·확대와 목록 보기를 사용한다.

`calls`는 메서드 본문에서 확인한 호출, `depends_on`은 주입된 타입 의존성이다. 둘 다 정적 근거이며 실제 실행 순서·호출 빈도·배포 구조를 뜻하지 않는다. Java Spring·JSP/Servlet·MyBatis XML을 대상으로 하고, 완전한 Java/SQL 파서가 아니다. 처리하지 못한 매핑·동적 SQL·모호한 타입은 진단과 근거를 확인한다. 상세 범위는 [진입점 체인 추출 규칙](entrypoint-rules.md)에 있다.

gx-work·gx-tdd는 complete Step 5.5의 "아키텍처 맵 갱신" 선택으로 service를 호출한다. design/review 자동 호출이나 별도 `--visualize` 플래그를 요구하지 않는다. 헤드리스에서는 이 선택 단계를 건너뛰며, 사용자가 이미 요청한 시각화를 다시 승인받지 않는다.
