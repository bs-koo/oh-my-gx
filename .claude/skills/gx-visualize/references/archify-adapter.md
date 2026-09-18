# Archify 선택 어댑터 계약

Archify는 선택 의존성이다. 어댑터는 패키지를 설치하거나 네트워크에 접속하지 않으며, 사용자 override·`GX_ARCHIFY_COMMAND`·현재 `PATH` 밖의 설치 경로를 추측하지 않는다.

## 탐지

`scripts/detect_backend.py`의 `detect_backend()`는 다음 순서로 선택한다.

1. Node 실행 가능 여부를 확인한다. 없으면 `static`을 선택한다.
2. 명시적 Archify 명령, `GX_ARCHIFY_COMMAND`, PATH의 `archify` 순으로 `--version`을 실행한다.
3. Archify가 없으면 명시적 Mermaid 명령, `GX_MERMAID_COMMAND`, PATH의 `mmdc` 순으로 확인한다.
4. 어느 CLI도 검증되지 않으면 `static`을 선택한다.

반환값은 `backend`, 사람이 읽을 수 있는 `reason`, 확인된 `version` 또는 `null`을 포함한다. 명시적 명령은 Python API에서 argv 목록으로 전달하는 방식을 권장한다. 문자열 명령에는 셸 연산자를 넣지 않는다. 모든 실행은 `shell=False`다.

## Archify 명령 계약

`render_archify(ir_path, output_dir, archify_command)`는 같은 기본 argv에 다음 두 호출을 순서대로 추가한다.

```text
<archify_command> validate <diagram-type> <ir_path> --json
<archify_command> deliver  <diagram-type> <ir_path> <view.html> --json
```

`diagram-type`은 view에서 파생한다 — `service` → `architecture`, `sequence` → `sequence`.

`--repo-root`는 `architecture`에만 적용된다. IR이 `component.sources`를 포함하면 Archify는 지정된 리비전의 실제 저장소에 대해 소스 근거를 검증한다 — 해당 리비전에 존재하지 않는 경로는 거부한다.

각 호출의 argv, 종료 코드, stdout, stderr, 예상 artifact 경로를 receipt의 `attempts`에 기록한다. `deliver`가 종료 코드 0을 반환해도 HTML이 없거나 비어 있으면 Archify 실패다.

새 실행을 시작하기 전에 대상 `{view}.html`을 제거한다. Archify와 두 폴백이 모두 실패한 경우에도 대상 HTML을 다시 제거해 이전 실행이나 부분 렌더의 stale artifact가 failed receipt와 함께 남지 않게 한다.

## 폴백과 진실성

Archify의 검증 또는 전달이 실패하면 `mermaid`, 이어서 `static`을 시도한다. 기존 `render_fallback.py`가 성공한 HTML과 검증 필드를 사용하고, 최종 receipt의 `status`를 `fallback`으로 기록한다. 최초 Archify 실패 진단과 이후 모든 시도는 삭제하지 않는다. 따라서 최종 `backend`는 실제 HTML을 만든 백엔드이며, 실패한 Archify를 성공으로 표시하지 않는다.

폴백 receipt의 최상위 `command`와 `exit_code`는 성공한 사전 단계가 아니라 폴백을 유발한 마지막 실패 Archify 시도를 나타낸다. 전체 실행 순서와 각 결과의 정본은 항상 `attempts` 배열이다.

세 백엔드가 모두 실패한 경우 failed receipt를 남기고 예외를 반환한다. 이 실패는 시각화 호출의 실패일 뿐 gx-dev의 구현·리뷰 게이트 성공을 뜻하거나 뒤집지 않는다.
