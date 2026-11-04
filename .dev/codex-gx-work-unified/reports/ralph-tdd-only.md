# Ralph TDD-only 전환 검증

## 변경

- 준비 스킬·반복 스킬·러너가 `origin: gx-tdd`만 허용한다. gx-dev/unknown/누락/중복은 원장을 자동 변환하거나 덮어쓰지 않는다. legacy 원장은 보존하고 명시 TDD 전환을 안내한다.
- origin 누락 구버전은 대화형 준비에서 TDD 출처·완료 AC의 RED→GREEN/verify/commit 근거를 확인하고 실제 정규화 승인을 받은 경우만 보완한다. 헤드리스는 fail-closed다.
- coder 단일 구현 분기를 제거했다. 모든 반복에서 red-writer의 실제 실패 확인과 해시 보존 후 implementer를 호출한다. 완료 후 리뷰 복귀는 항상 gx-tdd다.
- 러너 origin 검사는 lock/로그 archive/세션 시작 전에 실행하며, 반복 전후에도 확인한다. 기존 상한·NO_DRIFT·NO_PROGRESS·종료 계약·lock·보호 브랜치·timeout은 유지했다.
- Ralph opt-in의 AC별 로컬 커밋은 유지했다. 작업 계획 갱신 push는 `stop-at: pr` 또는 실제 별도 원격 반영 요청에만 허용한다. 명시 verify와 Ralph 로컬 커밋이 충돌하면 대화형 확인 기록 전 기동을 차단한다.

## RED

- legacy/누락/unknown origin fixture가 이전에는 실제 세션을 시작하고 기존 로그를 archive한 뒤 exit 3을 반환했다. 새 기대는 exit 6 및 state/AC/로그/lock 무변경이다.
- 첫 반복에서 origin이 gx-dev로 바뀌어도 이전에는 두 번째 반복을 시작하고 NO_DRIFT exit 4로 끝났다. 새 기대는 다음 반복 기동 전 exit 6이다.
- 빈 중복 origin은 명령 치환의 trailing newline 제거로 정상 origin처럼 보였다. origin 필드 개수를 별도 확인하는 회귀를 추가했다.
- 명시 `--stop-at verify`가 확인 없이 세션을 기동했다(exit 2). 새 기대는 사전 차단 exit 6이며, 실제 승인 후 기록한 상태에서만 세션이 기동된다.
- 문서 계약은 기존 coder 경로·origin 미검사·무조건 push 때문에 실패하는 것을 먼저 관측했다.

## 검증 결과

- `bash scripts/test-gx-ralph.sh`: **48 pass, 0 fail**. 기존 상한·lock·NO_DRIFT·NO_PROGRESS·CRLF·allowedTools와 새 origin 보존 검사를 포함한다.
- 새 origin/문서 계약 focused 검사: **4 passed**, 16.898초.
- Python Ralph 파일 1회: 22개 중 20개 통과, 2개 환경 timeout. `test_codex_shared_no_drift_guard`·`test_codex_shared_no_progress_guard`가 fixture 외부 subprocess 대기 30초를 초과했다. 같은 시점 부모의 all-Codex 검사도 실행되어 Windows Git Bash 프로세스 시작 비용·경합이 있었다. 제품 반복 timeout·상한은 변경하지 않았다. fixture 외부 대기만 Windows 90초/POSIX 30초로 조정하고 실패한 두 사례만 재실행했다. 재실행 결과는 아래 추가한다.
- Python 컴파일, 두 Bash 파일 syntax 검사, 소유 파일의 diff whitespace 검사는 통과했다.

실패 사례만 재실행한 `python -m unittest discover -s tests -p test_codex_ralph.py -k shared_no -v`는 **2 passed, 25.820초**다. 앞선 20개 성공과 합쳐 Ralph 파일의 22개 사례가 모두 검증됐다. 전체 Ralph 파일이나 저장소 전체 스위트를 재실행하지 않았다.

실제 Codex/Claude 인증 세션의 구현·커밋·push는 실행하지 않았다. mock 러너 분기와 설치된 스킬 계약을 검증했으며 커밋은 만들지 않았다.
