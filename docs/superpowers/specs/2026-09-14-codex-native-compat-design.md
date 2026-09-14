# Codex 네이티브 호환 보강 설계

작성일: 2026-09-14
상태: 설계·계획 작성 완료, 구현 및 종단 검증 전
대상: 현재 작업 트리 1.32.0, Codex CLI 0.154.0

## 목표와 성공 기준

Claude Code의 기존 동작을 유지하면서 Codex 소비 프로젝트에서도 설치, 역할 위임, 검증, 커밋 준비, 무인 반복을 실행한다. 스킬 발견·단위 테스트 통과·실제 세션 통과를 별개의 증거로 기록한다. 이번 작업은 설계와 구현 계획 작성이며 제품 코드 변경이나 배포를 포함하지 않는다.

2026-09-14 감사에서 매니페스트와 17개 GX 스킬 발견은 확인했다. 훅 matcher, 미지원 ask 판정, 역할 전달, Claude 전용 CLI 경로는 남아 있다. 기존 회귀는 hook/lint 통과, behavior mock 30/30, Ralph mock 34/34다. 이 수치는 Codex 종단 실행 합격을 뜻하지 않는다.

## 선택한 접근

1. **공통 원본 + 작은 Codex 어댑터를 채택한다.** 기존 Bash 가드, 역할 Markdown, 상태 원장, 스킬 절차를 재사용한다. Codex 경계에서만 판정·프로세스·역할 전달을 변환한다.
2. 스킬 전체를 Claude/Codex 두 벌로 분기하면 17개 절차와 검증 규칙이 드리프트하므로 채택하지 않는다.
3. 매니페스트와 문서만 수정하는 방식은 실행·출력 계약을 복구하지 못하므로 채택하지 않는다.

납품 단위는 A(보호 게이트), B(스킬·역할·설치), C(네이티브 실행)다. B는 A의 테스트 로더와 기록 계약을 사용하므로 기본 실행 순서는 A→B→C다. C의 종단 합격에는 A/B가 모두 필요하다. 구현 계획은 세 파일로 분리한다.

## 전역 제약

- 지원 검증 기준은 Codex CLI 0.154.0이다. 더 낮은 버전은 호환을 보증하지 않는다.
- Windows PowerShell + Git Bash, Linux Bash를 필수 검증 환경으로 둔다. macOS는 추가 검증 전 미측정으로 표시한다.
- Python 3.10 이상 표준 라이브러리와 기존 Bash/Git/Node를 사용한다. 새 런타임 패키지는 추가하지 않는다.
- `.claude/skills/`의 17개 GX 스킬과 `agents/*.md`를 편집 원본으로 유지한다. Codex 역할 복사본과 config 템플릿은 생성 산출물이다.
- `.claude/config.json`은 하네스 공통 프로젝트 데이터로 유지한다. 이름 변경이나 설정 마이그레이션은 하지 않는다.
- 소비 프로젝트의 AGENTS.md/CLAUDE.md와 명시적 사용자 지시가 플러그인 일반 지침보다 우선한다.
- 구현 브랜치에서 작업하고 기존 미커밋 변경을 임의로 스테이징·되돌리기·삭제하지 않는다. 커밋은 gx-commit 절차를 따른다.
- 전역 설치·훅 신뢰·모델·권한을 진단 명령에서 변경하지 않는다. 신뢰 우회·샌드박스 해제 플래그를 러너에 추가하지 않는다.
- 문서와 커밋 메시지는 한국어로 작성한다. 이모지는 새로 추가하지 않는다.

## A. 보호 게이트

### A1: 훅 경계

Codex `hooks.json`은 `Bash` matcher를 사용한다. `python3 .claude/hooks/codex_hook.py guard`를 POSIX 명령으로, `python .claude/hooks/codex_hook.py guard`를 `commandWindows`로 제공한다. 경로는 `${PLUGIN_ROOT}`를 인용한다. Windows에서 Python 실행 별칭이 동작하지 않으면 진단에서 명시적으로 실패한다.

`codex_hook.py`는 JSON stdin을 읽어 기존 `pre-tool-guard.sh`를 실행한다. 가드의 정상적인 빈 출력은 통과로 보존하고, `ask`만 `deny`로 변환한다. 잘못된 JSON, Bash 부재, timeout, nonzero 가드 종료는 Codex가 지원하는 deny JSON으로 반환한다. stdout에는 판정 JSON만, 진단은 stderr에 쓴다. Claude 플러그인은 기존 Bash 가드 호출을 유지한다.

실행 cwd는 hook payload의 절대경로 `cwd`를 사용한다. 이것은 모든 셸 문장의 `git -C`·`cd`를 완전히 해석한다는 보장이 아니다. 기존 가드의 명령 파싱 범위를 넘는 보편적인 보안 경계라는 주장을 하지 않는다.

### A2: verify 예외 정책

Codex에서는 verify 미통과·지문 불일치를 deny로 처리한다. 플러그인 내부에 일회용 우회 토큰이나 위험 수용 자동 승인 기능을 만들지 않는다. 사용자가 명시적으로 다른 정책을 요구하면 별도 변경으로 다룬다. Claude의 기존 ask 동작은 유지한다.

gx-commit은 훅과 독립적으로 main/master/develop 및 detached HEAD를 중단한다. Codex 경로에서는 verify 미통과를 질문 후 강행하는 기존 분기도 중단으로 바꾼다. 테스트 실행 결과를 조작하거나 verify 상태만 passed로 덮어쓰는 경로를 두지 않는다.

### A3: 기록과 설치

의사결정 기록은 Claude의 질문 문자열 키와 Codex의 질문 id→answers 배열을 정규화한다. 자연어/async 답변은 스킬이 확정된 응답을 같은 기록기에 명시적으로 전달한다. async 도구 호출 직후를 사용자 응답으로 처리하지 않는다. 부가 기록 실패는 실행을 차단하지 않지만 stderr로 드러낸다.

수동 설치 보조 도구는 Python JSON 직렬화, 인용된 절대경로, 기존 비-GX 훅 보존, 충돌 없는 백업을 사용한다. 기본은 렌더링이며 `--write`만 파일을 쓴다. 실제 hook trust는 `/hooks`에서 사용자가 검토한다.

## B. 스킬·역할·온보딩

### B1: 배포 리소스

`scripts/sync-codex-resources.py`가 역할 17개의 frontmatter를 제거한 본문을 `.claude/skills/gx-dev/references/codex-roles/`에 생성한다. 원본의 `model: opus/sonnet`은 `index.json`에서 high/mid로 기록한다. `--check`는 바이트 차이·누락·잔여 파일을 검사하고 쓰지 않는다. 배포 시만 생성하며 사용자가 수동 편집하지 않는다.

원본 frontmatter의 `tools` 목록도 index의 `tools: string[]`로 보존한다. 역할 본문만 복사해 도구 제약을 잃지 않도록, 공통 실행 규약이 해당 목록을 도구 이름 매핑과 함께 자식 프롬프트에 전달한다. 이 목록은 하네스 권한 설정을 변경하지 않는다.

같은 생성기가 `.claude/config.json`을 `gx-setup/references/config.template.json`으로 복사한다. 스킬 디렉토리만 제공되는 설치에서도 역할과 템플릿에 접근할 수 있어야 한다. 필요하지 않은 저장소 루트 파일 전체를 복제하지 않는다.

### B2: 실행 매핑

공통 매핑은 `gx-dev/references/codex-runtime.md`에 둔다. 각 스킬의 Codex 노트는 자신의 SKILL.md 위치에서 이 파일을 찾아 먼저 읽도록 한다. Phase 파일의 상대경로 기준은 해당 phase 파일이다.

현재 spawn API는 `task_name/message/fork_turns/model/reasoning_effort`다. API가 달라지면 노출된 스키마를 먼저 읽는다. 격리 작업은 `fork_turns: none`; 역할 본문·프로젝트 지침·태스크 프롬프트를 모두 전달한다. 역할의 allowed-tools는 Codex 권한 승인을 대신하지 않는다.

모델 후보는 high=`gpt-6-astra/high`, mid=`gpt-5.6-sol/medium`이며 해당 세션 allowlist에 있을 때만 쓴다. 부재 시 동일한 허용 모델의 high/medium으로 구분하고, 그것도 불가능하면 지원 제한을 보고한다. 후보를 유일한 지원 모델로 하드코딩하지 않는다. 기존 태스크별 mid 고정, fix 라운드 승격, eco의 architect 유지 예외를 보존한다.

질문은 가능하면 async 도구를 쓰고 응답 전 독립 작업만 진행한다. Plan 전용 동기 도구를 기본 모드에서 호출하지 않는다. 스킬 상호 호출은 설치된 SKILL.md를 읽고 게이트를 보존한다. 셸은 명시적으로 선택하고 workdir·세션 대기와 실제 timeout을 분리한다. Windows PowerShell의 파일 읽기·쓰기와 Python stdin 파이프는 UTF-8을 명시한다. 샌드박스 계정 차이로 Git 소유권 검사가 실패하면 해당 소비 프로젝트의 절대경로에만 적용되는 프로세스 한정 `safe.directory`를 사용하고 전역 예외를 추가하지 않는다.

humanizer strict는 역할 리소스를 전달한 두 독립 자식을 정상 경로로 복원한다. 자식 실행이 불가능하면 결과에 독립 검증 미수행을 표시한다. 직접 감사로 독립 감사 성공을 대체 보고하지 않는다.

### B3: setup·문서·실측

setup은 템플릿 로드/JSON 파싱/파일 생성 성공 후에만 완료를 표시한다. 기존 config는 자동 덮어쓰지 않는다. Codex 실행 시 `.claude/settings.local.json`에 승인을 추가하지 않고 필요한 실행 권한과 `/hooks` 상태를 안내한다.

README와 어댑터는 0.154 기준 CLI 설치, 훅 신뢰, 사용자 홈과 subprocess 홈 차이, Git source와 local source 차이를 설명한다. 구 설계는 역사 기록으로 유지하고 새 설계를 가리킨다. 루트 portable manifest로의 형식 전환은 범위 밖이다.

## C. Codex 네이티브 프로세스

### C1: 공통 비대화형 실행기

`scripts/codex-run.py`는 prompt 파일을 stdin으로 `codex exec`에 전달한다. 모델 출력 본문은 `--output-last-message` 파일에서만 읽고, `--json` 이벤트 로그와 분리한다. 종료 코드가 nonzero면 최종 파일이 있어도 실패한다. 실행 전에 이전 출력 파일이 존재하면 충돌로 종료하여 과거 COMPLETE를 재사용하지 않는다.

Windows는 `codex.cmd`, POSIX는 `codex`를 탐색한다. 실제 명령 인자는 배열로 조립한다. Windows cmd shim은 prompt 본문을 인자로 받지 않으며 shell 메타문자를 포함한 경로/모델 값은 지원하지 않는 입력으로 거부한다. 공백·한글 경로는 지원한다. timeout 때 프로세스 그룹/트리를 정리하고 nonzero로 종료한다.

review 모드는 read-only, iterate 모드는 workspace-write를 지정한다. 두 모드 모두 기존 승인·훅 신뢰 정책을 유지한다. 비대화형 정책으로 허용되지 않는 작업은 BLOCKED로 끝낸다. 전역 설정을 완화해서 재시도하지 않는다.

### C2: Ralph

`GX_RALPH_HARNESS=claude|codex`를 추가하고 기본 claude를 유지한다. Codex 경로는 설치된 gx-ralph-iterate의 절대경로를 prompt에 전달한다. 기존 lock/state/원장/NO_DRIFT/NO_PROGRESS/종료코드는 공유한다. 출력 계약은 최종 응답의 정확한 한 줄만 인정하며 로그·도구 출력에 나타난 문자열은 무시한다.

프로세스 nonzero, timeout, 빈 응답은 COMPLETE보다 우선한다. COMPLETE는 원장 모든 AC의 `passes == true`도 확인해야 한다. 기존 mock COMPLETE 시나리오도 실제 완료 원장을 만들도록 수정한다. Windows timeout은 실제 자식 트리 종료까지 검증한다.

### C3: cross-review

codex advisor는 공통 실행기의 review 모드로 호출하며 Claude companion을 필수로 요구하지 않는다. `--advisor claude`는 Claude 하네스에서 기존 내부 역할 위임 의미를 유지한다. Codex에서는 이를 Claude 모델 실행으로 위장하지 않고 지원 제한을 안내한다. Codex 내부 다중 역할 리뷰는 별도 `--advisor native` 명칭으로 제공하며 실제 사용 모델을 결과에 기록한다. Claude CLI를 Codex에서 실행하는 제3의 외부 어댑터는 이번 범위에 포함하지 않는다.

## 검증과 릴리스

| 요구사항 | 합격 증거 | 계획 |
|---|---|---|
| A1 | 정상 command 통과, normalized Bash 매칭, adapter 장애 deny | A Task 1 |
| A2 | Claude ask/Codex deny, protected branch 스킬 중단 | A Task 1·4 |
| A3 | Windows 공백 경로, 종료코드, 질문 id·선택지 보존 | A Task 2·3 |
| B1 | clean export에서 역할 17개·template 해시 일치 | B Task 1 |
| B2 | 17개 스킬 매핑 참조, 역할 반환 형식, 독립 감사 | B Task 2 |
| B3 | setup 실패 시 완료 미표시, 사용자 설정 보존, 최신 문서 | B Task 3 |
| C1 | mock argv/stdin/final 분리, nonzero/timeout/출력 충돌 | C Task 1 |
| C2 | Claude 기존 분기+Codex mock, 원장 완료 확인 | C Task 2 |
| C3 | companion 없는 Codex 리뷰, 제공자 명칭 정확성 | C Task 3 |
| 종단 | 소비 프로젝트에서 발견→setup→RGR→review→verify→commit 준비 | C Task 4 |

Codex 실제 모델 검증은 인증된 릴리스 환경에서 별도 실행한다. 3회 반복의 성공/차단/개입 횟수·시간·실제 제공되는 토큰 사용량을 기록한다. 값이 제공되지 않는 지표는 미측정으로 남긴다. 미실행을 PASS로 간주하지 않는다. push/PR 게시 없이 로컬 검증과 생성할 내용 확인까지로 기본 스모크를 제한한다.

## 근거

- [2026-09-14 감사 보고서](D:/Temp/oh-my-gx-codex-audit-2026-09-14.md): 로컬 조사 자료이며 릴리스 문서의 필수 입력은 아니다. 본 설계에 필요한 결론을 옮겼다.
- [Codex 훅 규약](https://learn.chatgpt.com/docs/hooks): Bash 정규화, PreToolUse ask 미지원, 신뢰 절차.
- [플러그인 패키징](https://developers.openai.com/plugins/build/plugins): 호환 매니페스트, 플러그인 루트 변수, local/Git source.
- 실제 `codex.cmd exec --help`(2026-09-14): stdin, --json, --output-last-message, --sandbox, --cd 지원.
