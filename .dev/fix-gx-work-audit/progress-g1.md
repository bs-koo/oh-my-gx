# G1 helper 진행 기록

담당 파일: `scripts/gx-work.py`, `scripts/codex-question.py`, `tests/test_gx_work*.py`, `tests/test_codex_question_gate.py`, 신규 `tests/test_gx_work_audit.py`.
실행: `PYTHONPATH=tests python -m unittest tests.test_gx_work_audit -v` (tests 디렉토리의 `codex_test_support` import 때문에 PYTHONPATH 필요).

- 시작(2026-11-10): 원본 그대로 확인, 기준선 gx-work 64개·질문 게이트 17개 통과.
- RED 작성: `tests/test_gx_work_audit.py` 61개 테스트(F01·F04·F06~F17·F25·F30·F36). 원본 helper 대상 실행 결과 failures=80·errors=30(subTest 포함). 통과 6건은 의도한 가드(3.0.0 v1 인계 검증 유지, v1 재현 픽스처=실제 6ef7517 출력, 명시 Ralph 실행 차단 유지, 응답된 qsid 수용, non-blocking 미정 보존). BOM state 테스트는 단언 보강 후 RED.
- F17(I5) GREEN: `codex-question.py discard --reason` 추가(보관 `discarded-question-<UTC>.json` → decisions.md `<!-- gx-question-discarded:<id> -->` 기록 → pending 해제, 재시도 시 보관·기록 재사용, pending 없음·잠금·사유 없음 exit 2). register 입력에 선택 `goal`·`run_id`를 받아 pending에 보존하고 다른 작업으로 덮어쓰기 거절. 기존 질문 게이트 17개 유지.
- F01 GREEN: work-id `^W[0-9]{2,}$`(ASCII), W118·W1000 허용·W1/W０１/W-01/W١٢ 거절, validate-plan과 handoff 같은 규칙.
- F04 GREEN: 새 인계 schema v2(프로젝트 상대 POSIX 포인터, 지문에 절대 root 없음), v1은 3.0.0과 같은 지문 경로로 계속 검증(실제 6ef7517 출력과 픽스처 일치 확인), `reissue` 추가(종료점 변경은 --change-source 필수, v1 이동은 relocated true, 내용 변경·읽기 전용 확장·미승인 거절), run-id 형식 검증(v2).
- F06 GREEN: git 오류(not a git repository 제외)는 exit 2 오류, detached HEAD는 `detached-head` 읽기 전용, `--git-safe-directory`(project-root와 같은 경로만, 명령별 -c), git 메시지 언어 고정(LC_ALL=C).
- F07 GREEN: awaiting-decision은 진행 중 gx-tdd 또는 state 없는 pending만, 완료 run의 pending은 `stale-pending-file`, 구버전(gx-dev) 판정이 pending보다 먼저.
- F08 GREEN: 범위 검토가 종료점 비교보다 먼저, 모든 route 결과에 `requested-stop-at`, 같은 실행의 종료점 변경은 오류 대신 `stop-at-change-required: true`(저장 종료점 유지).
- F09 GREEN: 읽기 전용 intent는 Ralph 언급으로 막지 않음, 경로·파일명·부정·설명·관리·'에서' 전환 문맥 제외, 절 분할에서 `.` 제외, `루프 돌려`는 절 시작·랄프/ralph/무인 뒤만.
- F10 GREEN: 모든 입력을 utf-8-sig로 읽고 UTF-16·NUL은 명확한 오류, `.active`는 첫 줄 + capture_decision 규칙(안전하지 않으면 trunk), config BOM에도 SVN 유지.
- F11 GREEN: v2 qsid는 UUID + 미응답 아님 + 응답 기록(answered 영수증 또는 decisions marker) 필수, 완료 run의 인계 재사용·재발급 거절, state 없는 답변 영수증이 같은 목표의 진입 질문이면 `entry-answer-recorded`로 재질문 생략.
- F12 GREEN: validate-plan이 공통 필드(목록 필드·work-id·execution-method·model-profile)를 handoff와 같이 검사, JSON 중복 키 거절.
- F13 GREEN: state.md 첫 YAML 블록만, 주석·따옴표·블록 목록 flags 처리, 첫 값 우선, 진행 중 gx-tdd state의 빈/미정의 stop-at은 오류.
- F14 GREEN: 요청 인계도 blocking 미정·결정 값 충돌이면 exit 2와 `ready-for-tdd: false`·`issues`(v2만, v1 검증은 3.0.0 규칙 유지).
- F15 GREEN: argparse 오류·깊은 중첩 JSON도 stdout JSON exit 2(stderr 없음).
- F16 GREEN: git 하위 디렉토리 → toplevel 정규화(`project-root`·`requested-project-root`), config 없는 `.svn` 작업 사본 인식(svn info wc-root 우선).
- F17 GREEN(route): pending이 있으면 `pending-goal`·`pending-run-id`·`pending-phase`·`pending-question-set-id`(읽기 전용 intent에도).
- F25 GREEN: 선택 필드 `execution-method`(session|subagents)·`model-profile`(standard|eco) 검증·v2 인계에 보존·지문 결박.
- F30 GREEN: 오류에 필드·값·기대 형식, 계획/요청 검증 실패는 사람이 읽는 요약 + 구조화된 `issues`.
- F36 GREEN: migration-required·loop-active reason에 "새 브랜치·새 워크트리에서 /oh-my-gx:gx-work <새 목표>로 새 범위 시작" 절차.
- 기존 테스트 계약 변경 4건: test_gx_work `test_resume_does_not_silently_expand_authorized_endpoint`(F08: 오류→stop-at-change-required), orchestration `test_actual_next_step_answer...`·`test_entry_response_metadata...`(F11: 임의 qsid 'q-entry' → 실제 helper 응답 qsid), `test_run_endpoint_goal_and_digest_tampering...`(I2: v2 project-root 변조 대신 포인터 변조로 결박 확인). 결과 gx-work 125개 통과.
- F36 추가(G2 요청) GREEN: route `--slug <SVN slug>`(SVN 전용, .dev/.active·후보 탐색 대신 그 slug만 검사, 결과 `requested-slug`, 안전하지 않은 값·git에서는 오류). migration-required·loop-active reason에 git(베이스/새 워크트리 `git worktree add <경로> -b <새 브랜치> <베이스>`)·SVN(`--slug <새 slug>`, setup이 .dev/.active 변경) 탈출 경로 둘 다.
- F04 보완 GREEN: reissue `relocated`는 기록된 project-root(v2 표시용 포함)나 v1 절대 포인터가 현재 위치와 다르면 true(v2 이동 후 재발급도 true).
- 독립 리뷰 RED: `tests/test_gx_work_audit.py`에 Review* 클래스 16개 추가(리뷰 1~9), 기존 F11(feature-limit 영수증에 run_id)·F14(충돌 사례를 근거 있는 explicit·architecture로) 사례를 새 계약으로 조정. 원본 대상 failures=10·errors=12. 경로 위험 legacy run-id 거절 테스트는 가드(이미 통과).
- 리뷰 1 GREEN: v2 qsid 응답은 영수증 question.run_id == 인계 run-id이거나 `.dev/<run-id>/decisions.md`에 완전한 표식 줄(`<!-- gx-question:<id>:<64hex> -->`)이 있을 때만 인정(다른 run 디렉토리·다른 run 영수증·부분 문자열 표식 거절). route는 영수증 run이 completed면 `stale-answered-file`만, entry-answer-recorded에는 영수증 run_id 필요.
- 리뷰 2 GREEN: reissue는 원래 qsid가 pending이면 종료점 변경 여부와 관계없이 거절, qsid는 응답도 미응답도 아닐 때만 버림(`dropped-question-set-id`).
- 리뷰 3 GREEN: v1(또는 v1에서 재발급한 v2)을 재발급하면 `legacy-run-id: true`(v2 지문에 결박), run-id 형식·요청 차단 규칙 소급 안 함. 경로를 깨는 run-id(구분자·..·제어문자)는 계속 거절. 새 인계가 legacy-run-id를 붙이면 validate 실패.
- 리뷰 4 GREEN: 요청 인계의 결정 충돌은 status explicit + source + 값(None·""·❓ 제외)이 있는 결정끼리, 하나라도 impact가 scope|behavior|architecture|acceptance|removal일 때만 차단(intake.py CONSEQUENTIAL과 동일).
- 리뷰 5 GREEN: codex-question answer 영수증에 `answers` 저장, route는 `answered-selection`을 돌려주고 'gx-tdd로 진행'((Recommended) 접미 허용)일 때만 requires-user-decision false. 추가: 영수증이 진행이 아닌 진입 답변을 증명하면 handoff도 그 qsid를 거절.
- 리뷰 6 GREEN: 형식이 깨진 pending도 discard가 원문 바이트(base64)와 raw-sha256을 보관하고 `<!-- gx-question-discarded:raw-sha256:<hex> -->`로 기록 후 해제(재시도 시 보관 재사용). route의 pending 형식 오류 메시지에 discard 출구 안내.
- 리뷰 7 GREEN: awaiting-decision 판정을 진행 중 state의 stop-at 오류보다 먼저.
- 리뷰 8 GREEN: detached HEAD면 모든 route 결과에 `detached-head: true`.
- 리뷰 9 GREEN: 응답 기록을 못 찾는 오류에 `.dev/<run-id>/decisions.md` 표식 줄 복사 확인 단서.
- 리뷰 재확인(표식 경로 선택) GREEN: `.dev/<run-id>/decisions.md` 표식으로 응답을 인정할 때 표식 뒤 답변 블록(`**ID.** gx_work_tdd_entry` 절의 `**→**` 선택 줄)에서 선택을 읽어 진행이 아니면 handoff·validate·reissue 거절. reissue는 원래 qsid의 기록 답변이 진행이 아니면 종료점 변경과 관계없이 거절. 블록에서 선택을 못 읽으면(표식 줄만 복사 등) 판단 보류(응답으로만 인정).
