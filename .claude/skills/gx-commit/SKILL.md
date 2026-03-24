---
name: gx-commit
description: 브랜치 타입을 파싱하여 한국어 커밋 메시지를 생성한다. "커밋", "commit" 시 사용.
argument-hint: [커밋 메시지]
allowed-tools:
  # git - 커밋 핵심
  - Bash(git rev-parse:*)
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git show:*)
  - Bash(git branch:*)
  # build - 커밋 전 pre-check
  - Bash(./gradlew:*)
  - Bash(npm:*)
  # 도구 존재 확인 - test 내부 pre-check용
  - Bash(which:*)
  - Bash(test:*)
  # git - 에러 복구, 이력 참고, 빌드 아티팩트 tracking 해제
  - Bash(git reset:*)
  - Bash(git log:*)
  - Bash(git rm:*)
  # 파일 도구
  - Read
  - Glob
  - Grep
  # 사용자 확인 — 민감 파일 경고, 대량 스테이징 확인
  - AskUserQuestion
---

변경사항을 스테이징하고, 브랜치명에서 타입을 파싱하여 `{type}: 한국어 메시지` 형식으로 커밋한다.

Arguments:
- 인자 없음: 타입은 브랜치에서 파싱, 메시지는 변경 내용에서 자동 생성
- ARGS[0]만: 커밋 메시지로 사용. 타입은 브랜치에서 파싱

## VCS 가드

`.claude/config.json`의 `"vcs"` 필드를 확인한다.
- `"svn"` → 즉시 종료: "SVN 프로젝트에서는 /gx-commit을 지원하지 않습니다. `svn commit`을 직접 실행해주세요." 출력.
- `"git"` 또는 `""` (미설정) → 아래 절차를 계속 진행한다.

## 사전 확인

- Git 저장소인지 확인
- **작업 디렉토리 보정**: `git rev-parse --show-toplevel`로 Git 루트를 확인한다. 현재 디렉토리와 다르면 (워크스페이스 root에서 호출된 경우 등), 이후 모든 git/빌드 명령을 Git 루트 기준 서브셸 `(cd <git-root> && <명령>)`로 실행한다.
- 커밋할 변경사항이 있는지 확인 (없으면: "커밋할 변경사항이 없습니다.")
- 커밋 전에 빌드를 실행한다:
  - `.claude/config.json`의 `projectTypes`에서 프로젝트 타입을 감지한다 (빌드/설정 파일 기준).
  - 감지된 프로젝트 타입의 `build` 명령을 실행한다.
  - 빌드 실패 시 커밋을 중단하고 사용자에게 보고.
  - 타임아웃: build Bash 명령에 `timeout: 300000` (5분) 파라미터를 설정한다. 초과 시 해당 단계를 건너뛰고 사용자에게 보고.

## 타입 파싱

브랜치명에서 타입을 추출한다:
1. `git branch --show-current`로 브랜치명 확인
2. 첫 번째 `/` 앞의 세그먼트를 타입으로 사용 (예: `feat/login` → `feat`)
3. 허용 타입: `.claude/config.json` → `conventions.branchTypes` 참조
4. 브랜치명에서 타입을 추출할 수 없으면 (main, develop 등): AskUserQuestion으로 타입을 선택받는다

## 커밋 메시지 생성

메시지를 자동 생성할 때:
1. `git diff --stat` (또는 `--cached --stat`)로 변경 요약 확인
2. 변경 파일 50개 이하면 `git diff --cached`로 상세 diff 확인. 50개 초과면 `--stat` 요약만으로 메시지 생성
3. 어떤 파일이 수정/추가/삭제되었는지 파악

**메시지 구조**:
- **제목 (첫 줄)**: `{type}: {한국어 요약}`. 50자 이내.
  - 예: `feat: 로그인 기능 추가`
- **본문 (빈 줄 이후)**: 구체적 변경사항을 `-` bullet으로 나열

예시:
```
feat: 로그인 기능 추가

- 로그인 API 엔드포인트 구현
- JWT 토큰 발급 로직 추가
- 로그인 폼 UI 구현
```

## 커밋 실행

0. `git diff --cached --name-only`로 기존 staged 파일 목록을 캡처한다. (커밋 실패 시 원래 staged 상태를 복원하기 위함)
1. `git status --short`로 변경 파일 목록을 확인하고, 목록을 사용자에게 표시한다.
2. 빌드 아티팩트 패턴(`.claude/config.json` → `buildArtifactPatterns` 참조)이 tracked 파일 목록에 있으면: `.gitignore` 파일이 존재하는지 `test -f .gitignore`로 먼저 확인한다. 파일이 존재하면 해당 패턴이 `.gitignore`에 있는지 grep으로 확인하고, 있으면 `git rm -r --cached <pattern>`으로 tracking을 해제한다. `.gitignore`가 없거나 패턴이 없으면 사용자에게 `.gitignore` 생성/추가 여부를 확인한다. **주의: 반드시 `--cached` 플래그를 사용할 것. `--cached` 없이 `git rm`을 실행하면 파일이 삭제된다.**
3. 민감 파일 패턴(`.claude/config.json` → `sensitiveFilePatterns` 참조)이 목록에 있으면 사용자에게 경고하고 스테이징에서 제외할지 확인한다.
4. 변경 파일이 20개를 초과하면 사용자에게 전체 스테이징 여부를 확인한다.
5. 스테이징:
   - 제외 파일 없음: `git add -A`
   - 제외 파일 있음: `git add <나머지 파일 각각 지정>`
6. HEREDOC 포맷으로 커밋:
   ```bash
   git commit -m "$(cat <<'EOF'
   {type}: 제목

   - 변경사항 1
   - 변경사항 2
   EOF
   )"
   ```
7. 커밋이 실패하면 `git reset HEAD`로 스테이징을 원복한 뒤, step 0에서 캡처한 기존 staged 파일이 있으면 `git add <파일>`로 재스테이징하여 원래 상태를 복원하고, 사용자에게 에러를 보고한다.
8. `git show --stat HEAD`로 결과 표시

## 커밋 후: context 동기화 체크

커밋이 성공하면, 변경된 파일이 기존 context 도메인과 관련 있는지 확인하여 동기화를 제안한다.

1. `context/` 디렉토리가 존재하는지 확인한다. 없으면 이 단계를 건너뛴다.
2. `context/*/PROJECTS.md`를 Glob으로 탐색한다. 없으면 건너뛴다.
3. 각 `PROJECTS.md`를 Read하여 프로젝트 매핑(소스 경로 패턴)을 파싱한다.
4. 커밋된 파일 목록(`git diff --name-only HEAD~1..HEAD`)과 각 도메인의 소스 경로 패턴을 대조한다.
5. 매칭되는 도메인이 있으면 AskUserQuestion:
   ```
   "{도메인} 도메인(context/{도메인}/)과 관련된 파일이 변경되었습니다.
   context를 동기화할까요?"
   ```
   - 옵션: "예 — context 동기화" / "아니오 — 건너뜀"
   - "예" 선택 시: 안내만 출력한다. "`/gx-context {도메인} 동기화해줘`로 동기화할 수 있습니다." (commit 스킬 내에서 context 스킬을 직접 실행하지 않는다)
6. 매칭되는 도메인이 없으면 이 단계를 건너뛴다.

**금지**: `Co-Authored-By` 라인을 절대 추가하지 말 것.
