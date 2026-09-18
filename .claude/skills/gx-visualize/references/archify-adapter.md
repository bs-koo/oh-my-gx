# Archify 선택 어댑터 계약

Archify는 선택 의존성이지만 없으면 **묻지 않고 자동 설치한다.** `scripts/detect_backend.py`의 `ensure_archify()`가 `~/.agents/skills/archify/bin/archify.mjs`(또는 그 심링크 `~/.claude/skills/archify`)를 찾지 못하면 `npx -y skills add tt-a1i/archify -g`를 `shell=False`로 1회 실행한다. 이 명령은 무관한 하네스(PromptScript) 실패 2건을 출력하면서 exit 0으로 끝날 수 있으므로 **종료 코드를 성공 판정에 쓰지 않는다** — 성공은 `bin/archify.mjs`가 실재하고 `node bin/archify.mjs doctor`가 성공(exit 0 + "Archify is ready.")하는지로만 판정한다. 설치가 실패하거나 재탐지도 실패하면 예외를 던지지 않고 `{"available": False, "command": None, "attempts": [...]}`을 반환해 폴백 체인(Mermaid → static)으로 넘어간다. 같은 실행 안에서 설치는 두 번 시도하지 않는다. 설치 명령의 타임아웃은 180초이며, 초과해도 예외를 던지지 않고 `attempts`에 기록한 뒤 곧바로 `available: False`로 반환해 폴백으로 넘어간다(타임아웃은 재탐지를 시도하지 않는다 — 프로세스가 아직 끝나지 않았을 수 있으므로). 설치 실행 파일은 `node`·`mmdc`와 같은 방식으로 `shutil.which("npx")`가 해석한 절대경로로 호출한다 — Windows의 `npx.CMD`는 맨 이름으로 `shell=False` 호출하면 찾지 못하며, 해석되지 않으면 설치를 시도하지 않고 그 사실만 `attempts`에 남긴 뒤 폴백으로 넘어간다.

## 탐지

`ensure_archify(command=None)`는 다음 순서로 Archify 사용 가능 여부를 확인한다.

1. `command`가 주어졌으면 그것을, 아니면 `~/.agents/skills/archify/bin/archify.mjs`·`~/.claude/skills/archify/bin/archify.mjs`(둘 중 먼저 발견된 실재 파일) 를 후보로 삼는다. PATH의 `archify`는 탐지 대상이 아니다 — 실제 설치는 `package.json`이 `"private": true`라서 PATH에 바이너리를 두지 않는다.
2. 후보가 있으면 `doctor`로 확인한다. 성공하면 그 명령과 빈 `attempts`를 반환한다.
3. 후보가 없거나 `doctor`가 실패하면 위 설치를 1회 시도하고 같은 후보로 재탐지한다. 그래도 실패하면 `available: False`와 설치 시도 기록을 반환한다.

`scripts/detect_backend.py`의 `detect_backend()`는 위와 별개로 **백엔드 선택**을 담당한다. Archify 명령은 `ensure_archify()`가 돌려준 값을 명시적으로 전달하거나 `GX_ARCHIFY_COMMAND`·PATH의 `archify`로 받는다.

1. Node 실행 가능 여부를 확인한다. 없으면 `static`을 선택한다.
2. Archify 명령(명시적 override, `GX_ARCHIFY_COMMAND`, PATH의 `archify` 순)이 있으면 `doctor`로 확인한다. 버전은 `doctor` 출력에 없으므로 `bin/archify.mjs` 옆 `package.json`의 `version`에서 얻고, 얻을 수 없으면 `null`이다 — 값을 지어내지 않는다.
3. Archify가 없으면 명시적 Mermaid 명령, `GX_MERMAID_COMMAND`, PATH의 `mmdc` 순으로 `--version`을 실행한다(Mermaid는 `--version`을 실제로 지원하므로 이 프로브를 그대로 쓴다).
4. 어느 CLI도 검증되지 않으면 `static`을 선택한다.

반환값은 `backend`, 사람이 읽을 수 있는 `reason`, 확인된 `version` 또는 `null`을 포함한다. 명시적 명령은 Python API에서 argv 목록으로 전달하는 방식을 권장한다. 문자열 명령에는 셸 연산자를 넣지 않는다. 모든 실행은 `shell=False`다.

## Archify 명령 계약

`diagram_type(view)`은 `service` → `architecture`로만 값을 반환한다. 그 외 뷰는 `None`을 반환하고, `render_archify`는 이를 **적용 대상 아님**으로 취급해 Archify subprocess를 아예 띄우지 않는다. `trace`/`progress`/`impact`는 kind 어휘가 5계층 grid 매핑 대상이 아니라서 시도해도 항상 레이아웃 검증에서 실패한다(근거: `docs/reports/2026-09-18-archify-ir-schema.md` §3.2, §5). `sequence`는 `to_archify.py`에 변환기가 아예 없다 — architecture 문서(`components`/`connections`)만 만드는데 Archify의 `sequence` 스키마는 `participants`/`messages`를 요구하고 `additionalProperties: false`라 architecture 문서를 그대로 거부한다; sequence 변환기는 이후로 미뤄졌다. 두 경우 모두 receipt의 첫 `attempts` 항목은 `status: "not_applicable"`이고 `command`/`exit_code`는 `null`이다 — 실패가 아니라 애초에 시도하지 않았다는 뜻이다. 최상위 `status`도 `"not_applicable"`로 기록되고, 곧바로 폴백 렌더러가 산출물을 만든다.

`diagram-type`이 있는 경우(현재는 `service`뿐)에만 아래 두 호출을 순서대로 추가한다. 입력은 원본 GX IR이 아니라 `to_archify.py`가 변환한 Archify 문서다 — GX IR(`nodes`/`edges`)과 Archify 스키마(`components`/`connections`)는 필드 이름을 공유하지 않는다.

```text
<archify_command> validate <diagram-type> <converted.archify.json> --json
<archify_command> deliver  <diagram-type> <converted.archify.json> <view.html> --json
```

`--repo-root`는 `architecture`에만 적용되고, 변환된 문서가 `component.sources`를 포함할 때만 붙는다(`render_archify`가 프로젝트의 실제 git HEAD/origin에서 계산 — 얻을 수 없으면 `sources`/`meta.repository`를 함께 비운다). IR이 `component.sources`를 포함하면 Archify는 지정된 리비전의 실제 저장소에 대해 소스 근거를 검증한다 — 해당 리비전에 존재하지 않는 경로는 거부한다.

dirty 검사는 워킹 트리 전체가 아니라 **인용될 파일에만** 국한된다(`git status --porcelain -- <cited paths...>`) — `to_archify.cited_paths(ir)`가 실제로 `sources`에 실릴 파일 목록을 미리 계산해 넘긴다. 인용된 파일 중 하나라도 수정·미추적 상태면 HEAD/origin이 정상 조회되더라도 `repository`를 계산하지 않고 `sources`/`meta.repository`를 함께 비운다 — 커밋됐지만 수정된 파일은 Archify의 블롭 존재 검사는 통과하지만 인용한 `line`이 워킹 트리 기준이라 커밋 시점과 다를 수 있기 때문이다. 인용되지 않은 다른 파일이 바뀌거나 새로 생겨도(이 프로젝트 정책상 커밋되는 `.dev/{branch}/visual/*` 산출물처럼) 이 검사에 영향을 주지 않는다 — Archify가 인용된 각 경로·줄을 리비전 자체에 대해 검증하므로 개별 인용의 정확성은 그것으로 보장된다. 인용할 파일이 하나도 없으면(코드 근거가 없는 IR) git을 조회하지도 않고 바로 `None`이다.

각 호출의 argv, 종료 코드, stdout, stderr, 예상 artifact 경로를 receipt의 `attempts`에 기록한다. `deliver`가 종료 코드 0을 반환해도 HTML이 없거나 비어 있으면 Archify 실패다.

새 실행을 시작하기 전에 대상 `{view}.html`을 제거한다. Archify와 두 폴백이 모두 실패한 경우에도 대상 HTML을 다시 제거해 이전 실행이나 부분 렌더의 stale artifact가 failed receipt와 함께 남지 않게 한다.

## 폴백과 진실성

Archify의 검증 또는 전달이 실패하면 `mermaid`, 이어서 `static`을 시도한다. 기존 `render_fallback.py`가 성공한 HTML과 검증 필드를 사용하고, 최종 receipt의 `status`를 `fallback`으로 기록한다. 최초 Archify 실패 진단과 이후 모든 시도는 삭제하지 않는다. 따라서 최종 `backend`는 실제 HTML을 만든 백엔드이며, 실패한 Archify를 성공으로 표시하지 않는다.

뷰가 애초에 Archify 대상이 아니어서(위 "적용 대상 아님") 같은 폴백 체인을 타는 경우, 최상위 `status`는 `fallback`이 아니라 `not_applicable`이다 — Archify가 실패한 게 아니라 한 번도 시도되지 않았다는 사실을 구분해서 남긴다.

폴백 receipt의 최상위 `command`와 `exit_code`는 성공한 사전 단계가 아니라 폴백을 유발한 마지막 실패 Archify 시도를 나타낸다. 전체 실행 순서와 각 결과의 정본은 항상 `attempts` 배열이다.

세 백엔드가 모두 실패한 경우 failed receipt를 남기고 예외를 반환한다. 이 실패는 시각화 호출의 실패일 뿐 gx-dev의 구현·리뷰 게이트 성공을 뜻하거나 뒤집지 않는다.
