# 현재 태스크 focused 명령 보완

## API

`python scripts/gx-test-plan.py focused --cwd ROOT --project TYPE:RELROOT --tests-file JSON [--config PATH]`

입력 테스트 파일은 저장소 상대경로의 비어 있지 않은 배열이다. 등록된 타입·root·marker, 실제 파일 존재, 선택 프로젝트 소유, symlink/상위/절대경로 범위탈출을 검증한다. 파일 인용은 Git Bash/POSIX shlex 기준이다. Git·지문·테스트 실행·proof 쓰기는 하지 않는다.

- exit 0: `supported:true,project,cwd,command,scope,runner`.
- exit 2: `supported:false,requires:focusedTest,reason` 및 프로젝트·scope. 전체 테스트 명령을 반환하지 않는다.
- exit 1: 잘못된 프로젝트·파일·범위.

명시 `focusedTest`를 우선 사용한다. 없으면 config의 정확한 npm test와 실제 package script vitest/vitest run/jest/node --test 조합, 또는 정확한 pytest/python -m pytest/python3 -m pytest 명령만 추론한다. custom·watch·복합 script는 설정이 필요하다. 기존 plan/record/reuse와 부모가 보완한 tree fingerprint·TS config·actual diff union·Kotlin·independent 정책은 수정하지 않았다.

## RED → GREEN

새 `TaskFocusedCommandTests` 6개만 실행했다. RED는 focused CLI가 없는 상태의 invalid choice 오류를 관측했다. GREEN은 **6 passed, 19.623초**다.

검증한 범위: 명시 template 우선과 공백/작은따옴표 파일 인용, 알려진 Node script 4종의 현재 파일 실행, custom script의 명시 설정 요구, 빈/삭제/다른 프로젝트/상위/절대경로 거부, Git 없는 pytest 및 config override, Kotlin Gradle focused template이다. 기존 25개 테스트나 전체 저장소 스위트는 재실행하지 않았다. Python 컴파일 및 소유 파일 whitespace 검사는 통과했다.

부모가 phase-implement의 현재 태스크 명령 조립과 Python 도구 허용에 이 CLI를 연결했다. helper의 command와 프로젝트 루트 상대 cwd를 격리 프롬프트·RED/IMPL report·직접 재실행·Ralph 인라인 인계에 함께 보존한다. 실제 consumer runner 실행은 helper 검사와 별도이며, assertion 실패·실행 수 확인은 기존 RED/IMPLEMENT 게이트가 담당한다.
