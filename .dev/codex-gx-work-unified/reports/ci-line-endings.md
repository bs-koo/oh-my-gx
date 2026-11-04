# PR 97 Windows 생성 리소스 개행 수정

## 원인

`_role()`은 원본 role을 LF로 정규화하여 기대값을 만든다. 반면 `check_files()`는 checkout된 생성물을 바이트 그대로 비교했다. `.gitattributes`의 LF 강제 경로가 삭제된 gx-dev 아래를 가리켜, 새 gx-work의 17개 role Markdown과 index.json이 fresh Windows checkout에서 CRLF가 되면 본문이 같아도 18개 drift로 판정됐다. Linux에서는 LF라 통과한다.

## 변경

소유 파일 `scripts/sync-codex-resources.py`, `tests/test_codex_resources.py`만 수정했다. 검사할 때 실제값·기대값에서 CRLF 바이트쌍만 LF로 바꿔 비교한다. JSON 의미 비교나 공백 제거를 하지 않으므로 BOM, lone CR, 추가 빈 줄, 본문·설정·도구 목록 차이는 계속 drift다. role/index 생성은 기존 LF를 유지하고 config.template도 원본 config의 CRLF만 LF로 정규화해 canonical UTF-8/LF로 쓴다. help/docstring도 이 기준으로 명확히 했다.

`.gitattributes`의 gx-dev→gx-work 경로 수정과 실제 속성 확인은 부모가 별도로 담당한다. 생성물 자체를 이 작업에서 다시 쓰지 않았다.

## RED → GREEN

- fresh-checkout 모사: LF/CRLF 원본으로 생성한 파일을 CRLF로 바꿨을 때 기존 check가 drift를 보고하는 실패를 먼저 관측했다.
- canonical writer: CRLF config에서 생성된 config.template이 CRLF를 유지하는 실패를 별도로 관측했다.
- 최종 `python -m unittest discover -s tests -p test_codex_resources.py -k newline -v`: **2 passed, 0.294초**. checkout 개행 동등성과 writer LF, BOM/lone CR/빈 줄/본문 차이 차단을 확인했다.
- 기존 내용 보호 회귀 `-k check_detects`: **1 passed, 0.747초**. role 본문·config 변경·잔여 role 차단을 유지했다.
- 실제 저장소 `python scripts/sync-codex-resources.py --check`: exit 0.
- 소유 파일 `git diff --check`: exit 0.

전체 스위트는 실행하지 않았으며 커밋·push도 하지 않았다. 실제 Windows CI 재실행 결과는 부모가 확인한다.
