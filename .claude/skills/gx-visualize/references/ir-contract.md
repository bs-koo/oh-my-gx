# GX 시각화 IR 계약 (schema version 1)

GX 시각화 입력은 UTF-8 JSON 객체다. `schema_version`은 정수 `1`, `view`는
`trace`, `progress`, `impact`, `service`, `sequence` 중 하나이며 `locale`, `title`,
`nodes`, `edges`를 필수로 한다. 노드는 `id`, `kind`, `label`, `status`를 갖고,
상태는 `planned`, `in_progress`, `review`, `verified`, `blocked`, `unknown` 중 하나다.
한국어 표시명은 `label`, 코드 식별자는 선택적인 `technical_label`로 분리한다.

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
