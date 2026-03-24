---
name: pull-request
description: >
  커밋 히스토리에서 제목과 본문을 자동 생성하여 PR을 생성한다.
  사용자가 "PR", "PR 올려", "PR 생성", "풀리퀘", "pull request"라고 말하면 이 스킬을 사용한다.
argument-hint: [base-branch]
allowed-tools:
  - Read
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git push:*)
  - Bash(git remote:*)
  - Bash(git branch:*)
  - Bash(git status:*)
  - Bash(git rev-parse:*)
  - Bash(gh:*)
  # GH_HOST=<host> gh <cmd> 형태의 환경변수 prefix 명령 허용 (GHE 호스트 지정 시 사용)
  - Bash(GH_HOST=github.com gh:*)
  - Bash(which:*)
  - Bash(brew install:*)
  - Bash(curl *)
  - AskUserQuestion
---

현재 브랜치의 커밋 히스토리를 분석하여 PR을 자동 생성한다.

## VCS 가드

`.claude/config.json`의 `"vcs"` 필드를 확인한다.
- `"svn"` → 즉시 종료: "SVN 프로젝트에서는 /pull-request를 지원하지 않습니다. SVN은 PR 개념이 없으므로 커밋 후 리뷰어에게 직접 알려주세요." 출력.
- `"git"` 또는 `""` (미설정) → 아래 절차를 계속 진행한다.

Arguments:
- ARGS[0] (optional): 베이스 브랜치. 미지정 시 자동 감지:
  1. `git branch --list main master develop`로 존재하는 브랜치 확인
  2. 존재하는 브랜치가 **2개 이상**이면 → AskUserQuestion으로 사용자에게 선택지 제시 (예: main, develop)
  3. 존재하는 브랜치가 **1개**이면 → 해당 브랜치를 베이스로 자동 선택
  4. 하나도 없으면 → AskUserQuestion(자유입력)으로 직접 입력 요청
- `--background <파일경로>` (optional): Background 섹션에 반영할 비즈니스 맥락 파일. 지정 시 해당 파일을 Read하여 "배경"과 "요구사항"을 Background 섹션에 포함한다. git log 기반 배경과 함께 병합하여 작성.
- `--extra-section <파일경로>` (optional): Checklist 앞에 삽입할 추가 섹션 파일. 지정 시 해당 파일을 Read하여 요약본을 Checklist 직전에 삽입한다. (예: Trust Ledger → `## Audit Summary` 섹션 생성)

## 사전 확인 (반드시 순차 실행)

**Step 1** (게이트 — 반드시 순차 실행):

1. `which gh`로 gh CLI 존재 확인.
   - **없으면**: AskUserQuestion — "gh CLI가 설치되어 있지 않습니다. 설치할까요?"
     - 예 → `brew install gh` 실행 (`timeout: 300000`). 설치 실패 시 "gh 설치에 실패했습니다. PR 생성을 건너뜁니다." 출력 후 **즉시 종료**.
     - 아니오 → "PR 생성을 건너뜁니다. 수동으로 PR을 생성해주세요." 출력 후 **즉시 종료**.

2. `gh auth status`로 인증 확인.
   - **미인증이면**: "gh 인증이 필요합니다. `gh auth login`을 실행하겠습니다." 안내 후 `gh auth login` 실행.
     - 인증 완료 → 다음 단계 진행.
     - 인증 실패/취소 → "PR 생성을 건너뜁니다." 출력 후 **즉시 종료**.

**Step 2**: 아래를 순차 확인:
- Git 저장소인지 확인
- `git rev-parse --abbrev-ref HEAD`로 현재 브랜치 확인 — 결과가 `HEAD`(detached 상태)이면: "detached HEAD 상태에서는 PR을 생성할 수 없습니다. 브랜치를 checkout한 후 다시 시도해주세요." 출력 후 **즉시 종료**
- `git remote get-url origin` 으로 origin remote 존재 확인 — **없으면**: "origin remote가 설정되어 있지 않습니다. `git remote add origin <URL>`로 설정해주세요." 출력 후 **즉시 종료**
- 베이스 브랜치명 검증: `^[a-zA-Z0-9._/-]+$` 패턴 매칭. 영문자, 숫자, `-`, `_`, `.`, `/`만 허용. 그 외 문자 포함 시 "잘못된 브랜치명 형식입니다." 출력 후 즉시 종료
- 현재 브랜치가 베이스 브랜치가 아닌지 확인 — 같으면: "베이스 브랜치에서는 PR을 생성할 수 없습니다."
- 베이스 브랜치 대비 커밋이 있는지 확인 — 없으면: "PR을 생성할 커밋이 없습니다."
- 미커밋 변경사항이 있으면 경고하고, 커밋 먼저 할지 진행할지 확인

## GH_HOST 감지

```bash
git remote get-url origin
```
- URL에 `github.com` 포함 → 기본값 (GH_HOST 불필요)

## 타입 파싱

브랜치명에서 타입을 추출한다:
1. `git branch --show-current`로 브랜치명 확인
2. 첫 번째 `/` 앞의 세그먼트를 타입으로 사용 (예: `feat/login` → `feat`)
3. `.claude/config.json` → `conventions.prTitleMapping`에서 대문자 매핑을 조회한다
4. 매핑 예: `feat`→`FEATURE`, `fix`→`BUGFIX`, `refactor`→`REFACTOR`, `chore`→`CHORE`, `docs`→`DOCS`

## PR 제목 생성

```bash
git log <base-branch>..HEAD --oneline -n 50
```

- 커밋 1개: 해당 커밋 내용을 기반으로 PR 제목 생성
- 커밋 여러 개: 전체 변경을 한국어로 요약
- 커밋 50개 초과: `--oneline` 요약만으로 제목 생성
- 포맷: `[{TYPE}] 설명을 ~한다.` (대괄호 타입 + 서술형 한국어 문장)
  - 예: `[FEATURE] 로그인 기능을 구현한다.`
  - 예: `[BUGFIX] 인증 토큰 만료 오류를 수정한다.`
  - 예: `[REFACTOR] API 응답 구조를 개선한다.`
- 50자 이내

## PR 본문 생성

```bash
git log <base-branch>..HEAD -n 50
git diff <base-branch>...HEAD --stat
```

- 커밋 50개 이하: 전체 log로 본문 작성
- 커밋 50개 초과: `--oneline` 요약과 `--stat`만으로 본문 작성

커밋 메시지와 diff 통계를 분석하여 본문 작성. `--background`가 지정된 경우 해당 파일을 Read하여 Background 섹션에 비즈니스 맥락(배경, 요구사항)을 병합한다.

```
## Background
이 변경이 필요한 배경을 설명한다. 어떤 문제가 있었는지, 비즈니스 맥락은 무엇인지를
리뷰어가 코드를 읽기 전에 이해할 수 있도록 자연스러운 문장으로 서술한다.
(--background 파일이 있으면 해당 문서의 "배경"과 "요구사항"을 우선 반영하고, git log 정보로 보완한다)

## Summary
이 PR에서 무엇을 했는지 요약한다. 핵심 접근 방식과 설계 판단을
간결한 문장으로 설명한다. 리뷰어가 diff를 열기 전에 전체 그림을 잡을 수 있어야 한다.

## Changes
구체적으로 무엇이 바뀌었는지를 기능 단위로 설명한다. 파일 단위가 아니라
"무엇을 왜 그렇게 바꿨는지"를 문장으로 풀어쓴다.

(--extra-section 파일이 있으면 여기에 해당 파일을 Read하여 요약 섹션을 삽입한다. 예: Trust Ledger → ## Audit Summary)

## Checklist
- [ ] 주요 기능이 로컬에서 정상 동작하는지 확인
- [ ] 기존 테스트가 통과하는지 확인
- [ ] (해당 시) 새로운 테스트를 추가했는지 확인
- [ ] (해당 시) 마이그레이션/설정 변경이 문서화되었는지 확인
```

**작성 규칙**:
1. **문장형 서술**: 모든 섹션은 `-` bullet이 아닌 자연스러운 한국어 문장으로 쓴다. 단, Checklist는 체크박스 형태.
2. **Background ≠ Summary**: Background는 "왜(문제/맥락)", Summary는 "무엇을(해결책)". 둘을 혼합하지 않는다.
3. **Changes는 기능 단위**: 파일명 나열이 아니라 기능 관점에서 "무엇이 어떻게 바뀌었고, 왜 그 방식을 선택했는지".
4. **Checklist는 동적 생성**: 변경 내용에 따라 항목을 조정한다. 테스트가 없는 변경이면 테스트 항목 생략. 마이그레이션이 없으면 마이그레이션 항목 생략.

## PR 생성

1. 기존 PR 확인: `gh pr view --json url` — 이미 존재하면 URL을 표시하고 선택지 제시:
   - "업데이트": push 후 기존 PR 본문을 `gh pr edit`으로 갱신
   - "신규 생성": push 후 `gh pr create` (기존 PR은 열린 상태로 유지됨을 안내)
   - "취소": 스킬 종료
2. 브랜치 푸시: `git push -u origin <branch-name>` (`timeout: 120000`)
   - push 실패 시: 에러 메시지를 표시하고 "PR 생성을 건너뜁니다." 출력 후 **즉시 종료**
3. PR 생성 (HEREDOC으로 body 전달):
   ```bash
   gh pr create --base <base-branch> --title "<title>" --body "$(cat <<'EOF'
   ## Background
   ...

   ## Summary
   ...

   ## Changes
   ...

   ## Checklist
   ...
   EOF
   )"
   ```
   (GH_HOST가 필요하면 `GH_HOST=<host>` 환경변수 prefix)
   - gh pr create 실패 시: "PR 생성에 실패했습니다. push는 완료되었으므로 수동으로 PR을 생성해주세요." 안내 후 **즉시 종료**. push는 의도적으로 유지한다 (브랜치가 원격에 존재해야 수동 PR 생성이 가능하므로 롤백하지 않음).
4. PR URL을 사용자에게 표시

## PR 생성 후 알림

**선행 조건:** 이 섹션은 신규 PR 생성(`gh pr create`) 시에만 실행하며, 기존 PR 업데이트(`gh pr edit`) 시에는 건너뛴다.

PR이 성공적으로 생성되었으면:

1. `.claude/config.json`의 `notifications.googleChat` 확인
   - `enabled`가 `false`이거나 `webhookUrl`이 비어있으면:
     "Google Chat 알림이 설정되어 있지 않습니다. `/setup`을 실행하면 웹훅을 연동할 수 있습니다." 안내 후 건너뜀

2. 전송 (`timeout: 10000`):

   ```bash
   PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel)")
   TMPFILE=$(mktemp)
   trap 'rm -f "$TMPFILE"' EXIT
   cat > "$TMPFILE" <<JSONEOF
   {"text":"[$PROJECT_NAME] 새로운 PR을 확인해주세요: $PR_URL"}
   JSONEOF
   curl --max-time 10 -s -o /dev/null -X POST "$WEBHOOK_URL" \
     -H "Content-Type: application/json; charset=utf-8" \
     --data-binary "@$TMPFILE"
   ```

3. 실패해도 작업 흐름을 중단하지 않음. 경고만 출력.
