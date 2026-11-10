# PR #104 병합과 독립 리뷰 반영 기록 (2026-11-10)

PR #103(gx-work 전수조사 47건, `4fa31bf`) 위에 Codex 세션의 PR #104(`codex/fix-aux-skill-edges`, `d901e17`: 보조 스킬 경계 보강·gx-tdd 요구사항 문답)를 합치고, 합친 상태를 독립 리뷰 3건으로 다시 검토해 반영했다. #104의 트리(`90458dc`)는 병합에 쓴 스냅샷과 같다.

## 1. 병합

- 방식: #104 워크트리를 건드리지 않고 임시 index로 트리 스냅샷을 만든 뒤 `git apply --3way`로 적용.
- 충돌 3건
  - `gx-commit/SKILL.md`: #104의 index helper 절차를 쓰고, #103의 실행 기록 커밋 범위(현재 run 디렉토리 포함, auto-stash·보호 브랜치 결정 기록 제외)를 helper 제외 목록(`RUNTIME`)에 넣었다. 문서 pathspec과 helper 목록이 같은지 `test_codex_release_audit`가 대조한다.
  - `gx-research/SKILL.md`: #103의 대화 모드 기본 + #104의 실행별 경로 helper를 저장 모드에서만 사용.
  - `tests/codex-smoke.md`: 두 실세션 시나리오 표(W1~W7, A1~A10·I1~I5)를 모두 유지.
- 병합으로 생긴 문제 2건
  - SKILL.md 20KB 예산 초과(gx-commit 22.3KB, gx-research 22.2KB, gx-tdd 20.2KB) → helper 절차를 `gx-commit/references/index-helper.md`, Phase 0 API 표를 `gx-research/references/phase0-apis.md`로 옮기고 중복 문장을 줄였다.
  - #104 커밋 훅이 `python3` 이름만 보고 실패하면 모든 커밋을 막음 → python3 → python 순서로 실제 실행해 3.10 이상을 고른다.

## 2. 독립 리뷰

| 리뷰 | 범위 | 판정 | High | Medium | Low |
|---|---|---|---|---|---|
| 문서 계약 | gx-tdd 문답·인계, 병합 지시문, 보조 스킬 지시문 | REVISE | 1 | 7 | 10 |
| 분석·윤문·시각화 helper | humanizer·research·setup-scan·dependency·lens·visualize | REQUEST CHANGES | 1 | 7 | 13 |
| 커밋·훅 helper | commit-index·git-target·review-diff·test-integrity | REQUEST CHANGES | 2 | 8 | 11 |

## 3. 반영 (기존 → 개선)

모든 항목은 실패하는 테스트를 먼저 쓰고 실패 이유를 확인한 뒤 고쳤다.

| 영역 | 기존 | 개선 | 테스트 |
|---|---|---|---|
| 읽기 전용 인계 (문서 H1·M1·M2) | #103은 "요청 문서만 저장", #104는 "아무것도 쓰지 않음". 미정이어도 저장부터 함 | 요청한 PRD·설계만 `.dev/<run-id>/`에 저장, state·질문 기록 무쓰기, 미정이면 저장 전 대기. Claude 결정 기록 훅은 명시 예외 | test_codex_merge_review |
| 설계 반복 상한 (문서 M3) | 2회 뒤 사용자 답을 반영할 반복이 없음 | 사용자 응답이 추가 반복 1회를 승인 | 〃 |
| 문답 종료 (문서 M4) | 위임 불인정, 탈출구는 중단뿐 | 표시 질문의 항목별 위임 인정, 3회 초과 시 계속·위임·중단 선택 | 〃 |
| Codex 질문 계약 (문서 L1) | 읽기 전용 예외 없음 | 등록 없이 자연어로 묻는 예외 명시 | — |
| humanizer 출력 (분석 H1) | cp949 출력, 작업 완료 후 실패 보고 | UTF-8 고정 | test_gx_aux_integrity |
| humanizer 원문 (분석 M1·M2) | 빈 원문 동결, PowerShell 5.1 파이프에서 `?`로 깨진 채 동결 | 빈 원문 차단, UTF-8 파이프 설정·`--input-file` 우선 | test_gx_aux_integrity, test_codex_merge_review |
| humanizer 권한 (분석 M7·문서 M6) | 범위 없는 `Bash` 사전 승인 | python·sha256sum만 | test_codex_merge_review |
| research 출력 (분석 M3·문서 L5) | `--output` 지정에도 `.research/`·`.gitignore` 변경(F37 역행) | 건드리지 않고 근거는 작업 메모리 | test_gx_aux_analysis, test_codex_merge_review |
| research 날짜 (분석 L5) | `2026111` 통과 | 8자리만 | test_gx_aux_analysis |
| 단독 GREEN 지문 (커밋 H2·M4·M5·L7·L8, 문서 M5·L8) | 러너 캐시·빌드 산출물 지문으로 pytest·Maven에서 항상 실패, "test" 부분문자열 오분류, 앱 설정 보호, 의존성 추가를 변조로 차단, cp949 출력 | 캐시·ignore 제외, 관례 기반 판정, 러너 설정만 보호, 의존성 변경은 exit 3으로 별도 보고, UTF-8 | test_gx_aux_integrity |
| 커밋 index (커밋 M6·L1·L2) | 일부 범위 커밋에 범위 밖 staged 혼입, pathspec 환경변수가 제외 무력화, snapshot 폴더 누적 | 범위 밖 내림·보고, 변수 제거, 성공 시 정리 | test_gx_aux_delivery |
| 교차 리뷰 diff (커밋 M7·L4·L5·L6) | diff 전체를 stdout으로 넘겨 잘림 위험, CP949 깨짐, 직전 diff 혼입, 파일별 프로세스 | 파일 직접 저장·요약만 출력, 바이트 보존, 출력 파일 제외, 일괄 처리 | test_gx_aux_delivery |
| 커밋 훅 (커밋 H1·M1·M2·M3·L9) | `bash -c`·`eval`·`$(...)` 안의 커밋이 main에서 통과(회귀), `cd` 뒤 커밋을 cwd로 판정, `git log \| grep commit`·HEREDOC 등 거짓 차단, Python 없으면 모든 커밋 차단, 루프 변수 `GIT_DIR` 충돌 | 셸 문법 분석으로 안쪽 명령·`cd` 추적, 해석 불가 흔적은 cwd 검사, git 커밋만 판정·원인별 사유, Python 없으면 이전 bash 판정으로 폴백, `TARGET_DIR` | test_gx_aux_hook_target, hook-tests.sh |
| 시각화 잠금 (분석 M5) | 강제 종료 뒤 잠금 잔존·소유 정보 없음 | pid·호스트·시작 시각 기록, 같은 호스트의 종료 확인 시 회수 | test_gx_aux_visualize |
| 설정 탐색 (분석 M6) | junction 하위 프로젝트 무기록 건너뜀 | `skipped_links` 보고·확인 요구 | test_gx_aux_analysis |

## 4. 보류 (이번 범위 밖)

- 커밋 M8: gx-commit·cross-review의 `Bash(python:*)` 사전 승인. helper 실행에 필요해 유지(gx-tdd도 같은 수준).
- 커밋 L3: 지시문 Bash 예시의 `python3` 고정. 커밋 L10: 약한 단언(`assertIn('2', text)`). 커밋 L11: 사전 검사 밖 형태(`git  commit`, `"git" commit`)는 기존 한계.
- 문서 L2(질문 개수 규칙 차이), L4(Phase 0 표는 2-2a에서 반드시 Read하도록 지시), L6(humanizer `.humanize/` 커밋 제외), L9(gx-work·gx-tdd 차단 미정 기준 차이), L10(중단 시 "진행 상황 저장" 문구), 빠진 것 3건(읽기 전용의 모델 디스패치 기록 위치, 문답으로 범위가 넓어질 때 진입 재승인, 읽기 전용 대기 뒤 답을 받는 스킬).
- 분석 L1~L4·L6~L13: humanizer JSON 형상 오류 traceback, 라운드 보존 메시지, 구 기록 표시, research `..` 정규화·지정 경로 미예약, setup-scan·test-plan의 roots·제외 목록 차이, POSIX 권한, 잠금 밖 labels/scan 쓰기, npm·pip-audit 구형 출력 분류, dependency 입력 전달 문서, 테스트 이름.
- 훅: `env -C`·`sudo -D` 같은 디렉터리 변경 래퍼는 cwd로 판정, Python 없을 때의 한계는 이전 훅과 같음, PID 재사용 잠금은 수동 삭제.
- 실세션 미검증: smoke W1~W7, A1~A10, I1~I5. Codex 훅 payload 래핑 형태와 샌드박스 소유권 불일치 상황의 훅 동작.

## 5. 검증

반영 후 전체 검사(2026-11-10, CI와 같은 `PYTHONUTF8=1`, `PYTHONIOENCODING` 미설정): 모두 통과.

| 검사 | 결과 |
|---|---|
| `sync-codex-resources.py --check` | 통과 |
| `test_codex_*.py` | 449건 OK (드리프트 린트 테스트는 태그 접두사 변수화 후 10건 재실행 OK) |
| `test_gx_aux_*.py` | 126건 OK |
| `test_gx_work*.py` | 149건 OK (SKILL.md 20KB 예산 포함) |
| context 31 · dev-context 25 · history 22 · lens 15 · test-plan 38 | OK |
| `test_gx_arch_*.py` 251 · `test_gx_visualize_*.py` 135 · feature-graph 12 · commit-visualize 3 | OK |
| `hook-tests.sh` · behavior mock 30 | 통과 |
| `lint-consistency.sh` 36구간 | 통과 |
| `git diff --check` | 통과 |

추가 조치: 린트 [1/36]의 릴리스 태그 접두사를 `RELEASE_TAG_PREFIX` 변수로 뺐다. 사업부 모노레포 사본(`oh-my-gx--v<버전>` 태그)은 이 한 줄만 바꾸면 되고, 드리프트 테스트는 린트의 변수를 읽어 태그를 만든다.
