# GX 시각화 IR 계약 (schema version 1)

GX 시각화 입력은 UTF-8 JSON 객체다. `schema_version`은 정수 `1`, `view`는
`trace`, `progress`, `impact`, `service`, `sequence` 중 하나이며 `locale`, `title`,
`nodes`, `edges`를 필수로 한다. 노드는 `id`, `kind`, `label`, `status`를 갖고,
상태는 `planned`, `in_progress`, `review`, `verified`, `blocked`, `unknown` 중 하나다.
한국어 표시명은 `label`, 원래 클래스·메서드는 `symbol`, HTTP 경로 같은 보조 정보는 `technical_label`로 분리한다. `symbol`과 `technical_label`은 선택 필드이며 라벨을 바꿔도 원래 식별자를 유지한다.

노드는 선택적인 `change`(`added` 또는 `changed`), edge는 선택적인 `change`(`added`)를
가질 수 있다 — `service` 뷰가 두 스캔을 비교해 이번 사이클에 새로 생기거나 바뀐 구조를
표시한다(설계서 §5.8). 최상위 `meta.changes`는 `available`과 `base_ref`를 항상 갖고,
`available`이 참이면 `base_commit`을, 거짓이면 `reason`을 갖는다 — `build_map.py`가
`compute_changes()` 결과를 도메인 IR에 싣고, 렌더러(`render_fallback.py`)가 이 값으로
'이번 변경' 배너를 만든다.

`meta.changes.removed`·`removed_edges`는 해당 도메인의 삭제 목록이다. 삭제만 있는 경우에도 변경 배너에 표시한다. `meta.navigation`은 현재 `domain`과 이동 가능한 `domains`를 가진다. 경계 노드의 `external_domain`은 원래 도메인을 가리킨다. 경계 엣지는 전체 IR과 양쪽 도메인에 보존하며 누락 입력으로 취급하지 않는다.

`calls`는 본문에서 확인한 정적 호출, `depends_on`은 타입 주입 의존성이다. 스캐너는 관계에도 파일·라인 근거를 보존한다. 현재 validator의 파일·라인 검사는 노드 evidence에 적용되며 edge evidence의 경로·줄까지 검증했다고 보고하지 않는다. `skipped`·`unresolved_edges` 진단은 이유·파일·대상을 제공한다.

service 출력의 `global.ir.json`은 전체 관계, `run-manifest.json`은 현재 실행 결과의 정본이다. 인덱스는 디스크에 남은 과거 성공 receipt 대신 이번 실행 결과를 읽는다. 과거 정상 산출물을 보존한다면 `last_good`로 구분한다. 실제 표시 능력은 `capability`로 기록해 백엔드 이름과 그림 제공 여부를 혼동하지 않는다.

부분 갱신에서는 manifest의 `domains`가 이번 렌더 결과, `map_domains`가 전체 맵 상태다. 다른 도메인의 기존 결과는 `freshness: retained` 및 원래 `generated_at`·`revision`으로 구분하며 이전 변경 배지는 이번 변경으로 집계하지 않는다. 새 도메인의 `not_generated` 상태는 정상 결과가 아니다. manifest의 `project_root`가 다른 프로젝트의 결과는 승계하지 않는다.

상세 HTML 앵커는 `gx-detail-{id}`로 도표의 ID와 분리한다. 이전 `node-{id}` 해시는 새 상세가 있을 때 정규화한다. `meta.navigation.domains`의 `{name, available}`과 외부 노드의 `external_available`로 미생성 페이지 링크를 비활성화한다. 보존 페이지가 새 상세 앵커를 지원하지 않으면 `external_detail_available: false`로 페이지까지만 연결한다.

기능 선택 UI는 원본 IR을 바꾸지 않고 노드·관계의 브라우저용 부분집합을 만든다. `gx-feature-{id}`는 선택한 진입점의 공유 주소이며 `gx-detail-{id}`와 구분한다. 기본 방향성 탐색은 `calls`·`requests`·`reads`·`writes`를 사용하고 `depends_on`은 선택적 후보다. 다른 진입점·공유 테이블의 역참조·외부 도메인에서 무관한 노드를 확장하지 않는다. 서비스·저장소의 클래스 수준 해상도를 메서드 수준 정확성으로 승격하지 않는다. 전체 IR·접힌 상세 목록·기존 앵커는 보존한다.

`unknown`은 모든 view에서 유효한 상태값이지만 의미가 다르다 — `service`는 코드
스캐너가 상태를 알아낼 방법이 없어 모든 노드가 구조적으로 `unknown`이므로
`render_fallback.py`가 그 view에서만 배지·범례에서 뺀다. `trace`·`progress`·
`impact`·`sequence`는 사람이 상태를 채우는 view라 `unknown`이 "아직 확인 안 됨"이라는
실행 가능한 신호이므로 그대로 보여준다(스키마 필드 자체는 어느 view든 그대로 보존한다).

노드 ID는 산출물의 공식 ID를 우선한다. 공식 ID가 없을 때 생성하는 ID는
`gx-{kind}-{slug}` 규칙을 따른다. 모든 edge의 `source`와 `target`은 nodes에 존재해야
하며 edge는 `id`, `source`, `target`, `relation`을 갖는다.

근거는 노드의 선택적인 `evidence` 배열에 기록한다. `file`은 명시적으로 전달한
프로젝트 루트 상대경로이며, 정규화된 실제 경로가 프로젝트 루트 안에 있어야 한다.
절대경로와 루트 밖으로 나가는 `..`는 거부한다. `.dev/work/visual/../prd.md`처럼
`..`를 포함해도 정규화 결과가 프로젝트 루트 안이면 허용한다. 존재하지 않는 근거
파일은 검증 오류이며 `missing_inputs`에도 입력 문자열을 기록한다.

텍스트 근거는 `{file, line, kind}`를 사용한다. `line`은 양의 정수이며 UTF-8 텍스트
파일의 실제 줄 수 이하여야 한다. 비텍스트 근거는 `line` 대신 `locator`를 사용하며
파일을 UTF-8로 읽지 않는다. 최소 locator 형식은 다음과 같다.

- XLSX: `{"type":"xlsx","sheet":"요구사항","cell":"B12"}`
- PDF: `{"type":"pdf","page":2}`

`kind`는 `artifact`, `code`, `test`, `command`, `design` 중 하나다. `line`과
`locator`는 정확히 하나만 존재해야 한다. 근거 없는 사실은 `{"kind":"inferred"}`로
명시하며 이 항목에는 `file`, `line`, `locator`를 넣지 않는다.

## 검증 receipt

`validate(path, project_root=None)`와 CLI는 `status`, `errors`, `warnings`, `node_count`, `edge_count`,
`missing_inputs`를 반환한다. `status`는 오류가 없으면 `valid`, 하나라도 있으면
`failed`다. 오류 문자열은 JSON 경로를 접두사로 하며 경로와 메시지 기준으로
결정적으로 정렬한다. CLI는 유효하면 종료 코드 0, 유효하지 않으면 1을 반환하고,
`--project-root <path>`로 evidence 기준과 confinement 경계를 받는다. 생략 시 하위 API의
호환성을 위해 IR 디렉터리를 경계로 사용한다. `--output receipt.json`을 지정하면
receipt만 해당 UTF-8 파일에 쓴다.
