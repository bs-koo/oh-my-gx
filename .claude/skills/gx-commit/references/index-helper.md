# gx-commit 인덱스 helper 절차

gx-commit의 미리보기 분기와 커밋 실행 Step 0·5·7·8, 위험 수용 토큰 기록(`verify-and-branch.md`)에서 읽는다. helper는 이 파일 기준 [../../../../scripts/gx-commit-index.py](../../../../scripts/gx-commit-index.py)이고, SKILL.md 기준으로는 `../../../scripts/gx-commit-index.py`다. 게이트(보호 브랜치·verify·명시 제외 확인)는 SKILL.md가 정본이며 이 파일은 요청 형식과 차단 조건만 다룬다.

## 실행 방법

**Claude Code와 Codex 모두** 확인된 Python 3.10+로 이 helper를 사용한다. 입력은 UTF-8 stdin JSON, 출력은 JSON이며 소비 Git 루트의 절대경로를 `cwd`로 준다. Windows PowerShell은 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $OutputEncoding = [System.Text.UTF8Encoding]::new($false)`로 stdin 인코딩을 맞춘 뒤 확인된 Python 실행 파일과 helper 절대경로를 사용한다. Bash는 `python3 "$GX_PLUGIN_ROOT/scripts/gx-commit-index.py"`에 JSON을 전달한다. helper 부재·실패는 스테이징/커밋 전에 중단한다.

## 미리보기 (`preview`)

Git 루트를 확인한 뒤 `{"action":"preview","cwd":"<PROJECT_ROOT 절대경로>"}`를 UTF-8 stdin으로 전달한다. 커밋용 사전 확인·빌드·타입 질문·snapshot·스테이징·커밋은 실행하지 않는다. main/master/develop에서도 **조회 자체는 허용**한다. 출력 `files`의 경로·포함 후보 여부·`alreadyStaged`·제외 이유를 표로 보여주되 파일 내용/비밀값은 읽어 표시하지 않는다. 민감 패턴 후보는 확정 승인으로 취급하지 않는다. `commitAllowed:false`와 "커밋 가능 판정이 아닌 미리보기"를 표시하고 즉시 종료한다. 조회 오류는 실패로 보고하며 실제 커밋으로 전환하지 않는다. 명시 제외가 이미 확정된 범위라면 실제 상대경로 배열 `excludes`를 함께 전달한다. 전역 설정·작업 파일·index를 변경하지 않는다.

## 스테이징 (`snapshot` → `stage` → `assert-excluded`)

- 먼저 `{"action":"snapshot","cwd":"<PROJECT_ROOT>"}`를 전달해 `snapshot` 절대경로를 보존한다. helper는 `git rev-parse --git-path index`로 **현재 worktree의 실제 index**를 찾고 원 bytes·HEAD/브랜치·hash를 작업 트리 밖에 저장한다. 기존 index가 없는 새 저장소도 구분한다. 기존 `index.lock`, 별도 Git 경로 환경변수, split/shared index는 변경 전에 차단한다. split index를 임의로 일반 index로 바꾸지 않는다.
- `{"action":"stage","cwd":"<PROJECT_ROOT>","snapshot":"<SNAPSHOT>","paths":null,"excludes":[".env"],"untrack":[]}`를 전달한다. `paths:null`은 승인된 전체 변경, 일부 범위만 승인됐다면 실제 상대 파일 경로 배열이다. `excludes`에는 SKILL.md Step 3 및 범위 선택에서 확정한 EXCLUDES, `untrack`에는 Step 2의 UNTRACK을 넣는다. 미해결 병합 충돌 경로(`git ls-files -u`가 비지 않음)가 있으면 helper는 index를 바꾸기 전에 거부한다 — `add -A`가 충돌 표식이 든 파일을 해결된 것으로 스테이징하기 때문이다. 충돌 해결과 `git add <경로>` 해결 표시를 안내하고 커밋하지 않는다. helper는 snapshot 아래 **임시 index**에서 add/제외/tracking 해제·검사를 마친 뒤 실제 `index.lock`을 배타 확보하고 HEAD/기존 index를 다시 확인하여 원자적으로 반영한다. 중간 외부 변경은 helper의 expected 상태로 채택하지 않고 실제 index를 보존하며 차단한다. staging 실패 시 임시 index를 정리한다. 기존 staged 제외 파일도 HEAD 기준으로 내리고 작업 파일은 보존한다. `paths`가 배열이면 범위 밖에 이미 staged된 항목도 같은 방식으로 HEAD 기준으로 내리고(작업 파일 보존) 결과 `unstaged` 배열로 보고하므로, 사용자에게 "범위 밖 staged N건을 내렸다"고 알린다. helper의 git 호출은 `GIT_LITERAL_PATHSPECS` 등 pathspec 환경변수를 무시한다. tracking 해제는 `--cached`만 사용한다.
- **항상 제외**(helper의 `RUNTIME`, `.gitignore` 상태와 무관): pathspec은 `git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' '.dev/*/auto-stash.txt' '.dev/architecture' '.dev/*/visual/*' '.dev/main/decisions.md' '.dev/master/decisions.md' '.dev/develop/decisions.md' '.dev/trunk/decisions.md' '.dev/*/pending-question.json' '.dev/*/answered-question.json' '.dev/*/.question-lock' '.dev/*/model-dispatches.jsonl' '.dev/*/discarded-question-*.json' '.dev/*/logs/*' '.dev/*/evidence/*' '.dev/*/verify-risk-accepted' '.dev/*/rgr-*-porcelain.now.txt' '.dev/*/reports/*-diff*.txt'`와 같다. 루프 락·로그는 다른 사용자의 게이트 판별을 흐리고, 시각화 산출물은 단발성이며, 보호 브랜치 결정 기록은 이후 모든 작업 브랜치에 섞인다. 질문 대기·모델 기록·로그·증거는 머신 로컬 런타임(`../../gx-work/references/dev-sharing.gitignore`와 같은 목록)이고, 위험 수용 토큰은 이 PC의 확인 기록이다. `rgr-*-porcelain.now.txt`와 `reports/t{N}-diff*.txt`는 리뷰 직전에 다시 수집하는 비교본이라 재개에 쓰지 않는다. 재개 기준선인 `rgr-t{N}-porcelain.txt`·report·state는 커밋한다.
- **큰 파일·로컬 모드**: 50MiB 초과 `.dev/` 파일(GitHub이 50MiB 초과에 경고하고 100MiB 초과 push를 거부한다)은 모드와 무관하게 빼고 결과 `largeExcluded`로 알린다. `stage`·`preview`에 `"devArtifacts":"local"`을 주면 `.dev/plan.md`를 뺀 `.dev/` 변경도 빼고 `devExcluded`로 알린다. 값은 `commit`(기본)·`local`만 허용한다. 두 목록은 명시 제외와 같이 `assert-excluded`가 다시 확인한다.
- 커밋 **직전** `{"action":"assert-excluded","cwd":"<PROJECT_ROOT>","snapshot":"<SNAPSHOT>"}`의 exit 0을 확인한다. 명시 제외 경로가 cached diff에 남거나 HEAD/index가 바뀌면 커밋하지 않는다. helper 오류를 빈 목록/성공으로 간주하지 않는다.

## 위험 수용 토큰 (`accept-risk`, Claude Code 전용)

`verify-and-branch.md`의 위험 수용 질문에 실제 응답을 받았을 때만, 응답 직후가 아니라 `assert-excluded` exit 0 뒤 `git commit` 직전에 `{"action":"accept-risk","cwd":"<PROJECT_ROOT>"}`를 전달한다. 스테이징 중 중단·실패하면 쓰지 않는다. `.dev`·`.dev/{branch-slug}`·토큰이 링크이거나 저장소 밖으로 해석되면 helper는 쓰지 않고 실패한다. helper는 같은 디렉터리의 `codex-fingerprint.py`로 `.git/objects`에 쓰지 않고 트리 지문을 계산해 `.dev/{branch-slug}/verify-risk-accepted`에 `tree: <12자>` 한 줄을 쓰고 `{"token":…,"tree":…}`를 돌려준다. detached HEAD·지문 계산 실패는 오류다. 토큰 밖의 index·작업 파일은 바꾸지 않는다. Codex에서는 호출하지 않는다.

## 실패 복원 (`restore`)

스테이징/커밋이 실패하면 `{"action":"restore","cwd":"<PROJECT_ROOT>","snapshot":"<SNAPSHOT>"}`를 전달한다. 원 index bytes를 복원하므로 부분 스테이징·staged 삭제·기존 index 부재를 보존하며 tracked/untracked 작업 파일은 변경하지 않는다. **파일명 목록으로 reset/add하여 복원하지 않는다.** HEAD/브랜치 변경·다른 index 변경·lock·snapshot 손상·복구 실패면 강제 덮어쓰기/lock 삭제 없이 중단하고 에러와 보존된 snapshot 경로를 보고한다. 중단 재개도 새 snapshot으로 기존 것을 덮지 않고 원 snapshot·현재 HEAD/index를 먼저 확인한다.

## 성공 정리 (`finish`)

커밋이 성공하면 `{"action":"finish","cwd":"<PROJECT_ROOT>","snapshot":"<SNAPSHOT>"}`로 이 실행의 백업과 snapshot 디렉터리만 정리한다(다른 실행의 snapshot은 유지). 성공한 새 HEAD 확인/정리 실패는 커밋 재시도 사유가 아니다. 커밋 결과와 남은 snapshot 경로를 보고한다.
