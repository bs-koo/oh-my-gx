---
name: worktree
version: 2.0.0
argument-hint: "<create|list|switch|status|done|remove> [name]"
description: "표준 Git worktree 관리. 트리거: '/worktree create', '/worktree list', '/worktree remove', '/worktree done', '/worktree switch', '/worktree status'. 격리된 기능 개발을 지원."
allowed-tools:
  # git - worktree 관리 핵심
  - Bash(git worktree:*)
  - Bash(git branch:*)
  - Bash(git checkout:*)
  - Bash(git rev-parse:*)
  - Bash(git log:*)
  - Bash(git status:*)
  - Bash(git remote:*)
  # 파일시스템
  - Bash(pwd:*)
  - Bash(basename:*)
  - Bash(dirname:*)
  - Bash(mkdir:*)
  - Bash(ls:*)
  - Bash(test:*)
  # 빌드 - worktree 생성 후 환경 세팅
  - Bash(./gradlew:*)
  - Read
  - Glob
  - Grep
  # 사용자 확인
  - AskUserQuestion
---

# Worktree 스킬

표준 Git worktree를 관리하여 격리된 기능 개발을 지원한다.

## 핵심 개념

Git worktree는 하나의 저장소에서 여러 브랜치를 동시에 체크아웃할 수 있게 해준다. 각 worktree는 독립된 작업 디렉토리를 가진다.

```
project-root/           ← 메인 작업 디렉토리
├── .git/
├── src/...
└── ...

# worktree는 프로젝트 외부 또는 .worktrees/ 하위에 생성
.worktrees/
├── feature-x/
└── feature-y/
```

## 동작 규칙

### 반드시 수행
- 모든 명령 전에 git repo 내부인지 확인: `git rev-parse --is-inside-work-tree`
- `git worktree add` / `git worktree remove` 표준 명령 사용
- 삭제 전 uncommitted changes + unpushed commits 확인 → 경고 → 사용자 확인
- 브랜치명은 사용자 입력 그대로 사용 (prefix 추가 금지)

### 금지 사항
- 사용자 확인 없이 `--force` 삭제
- orphaned 워크트리 방치
- 워크트리 디렉토리 직접 `rm -rf` (반드시 `git worktree remove` 우선. 실패 시에만 사용자 확인 후 수동 삭제)

## 명령어

### `/worktree create <name>`

새 워크트리 + 브랜치를 생성한다.

1. git repo 확인
2. **브랜치명 검증**:
   - 형식: `{type}/{description}` (예: `feat/login`, `fix/auth-bug`, `refactor/api-cleanup`)
   - 허용 타입: `.claude/config.json` → `conventions.branchTypes` 참조 (`feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `perf`, `ci`)
   - 사용자가 타입 없이 이름만 제공하면 AskUserQuestion으로 타입을 선택받는다
   - description은 영문 소문자 + 하이픈 (`kebab-case`) 권장
   - **Claude가 브랜치명을 임의로 생성하지 않는다** — 반드시 사용자가 지정하거나 확인해야 한다
3. 브랜치 중복 체크 (중복 시: 기존 사용 / 다른 이름 / 기존 삭제 중 선택)
4. `git worktree add .worktrees/<name> -b <name>`
5. 빌드 도구 감지 후 의존성 설치 제안 (의존성 설치 Bash 명령에 `timeout: 300000` 설정)
6. 생성 완료 안내

### `/worktree list`

모든 워크트리 목록을 표시한다. (`git worktree list`)

### `/worktree switch <name>`

작업 대상 워크트리를 안내한다.

1. 대상 디렉토리 존재 확인
2. 워크트리 경로를 안내

### `/worktree status`

현재 git status + 최근 커밋(`git log --oneline -n 10`)을 표시한다.

### `/worktree done`

현재 워크트리 작업을 마무리한다.

1. uncommitted changes + unpushed commits 표시
2. 미커밋/미푸시 변경이 있으면 경고하고, `/commit`과 `/pull-request`을 사용하도록 안내
3. 워크트리 삭제 여부 확인

### `/worktree remove <name>`

워크트리를 삭제한다.

1. uncommitted changes + unpushed commits 확인 → 위험 시 경고
2. 사용자 확인 후 `git worktree remove <path>` (`--force`는 명시적 확인 후만)
3. 브랜치 삭제 여부 확인
4. `git worktree prune`

## 안전 규칙

- **remove 전**: uncommitted changes + unpushed commits → 경고 → 확인
- `--force`는 사용자 명시적 확인 후에만
- 브랜치는 명시적 요청 없이 삭제하지 않음
- 수동 삭제된 워크트리는 `git worktree prune`으로 정리

## 에러 처리

| 상황 | 대응 |
|------|------|
| git repo가 아님 | `git init` 또는 git 프로젝트에서 실행 안내 |
| 브랜치명 중복 | 기존 사용 / 다른 이름 / 기존 삭제 선택지 제공 |
| 워크트리 디렉토리 이미 존재 | `git worktree list`로 확인 → orphan이면 삭제 확인 |
| 의존성 설치 실패 | 워크트리는 생성됨, 수동 해결 안내 |

## 예시

```
User: /worktree create feat/login

Claude: 워크트리 생성 완료.
  브랜치: feat/login
  경로:   .worktrees/feat/login/
  기반:   main (abc1234)

User: /worktree create login
Claude: 브랜치 타입을 선택해주세요. → [feat / fix / refactor / ...]
User: feat
Claude: 워크트리 생성 완료.
  브랜치: feat/login
  경로:   .worktrees/feat/login/

User: /worktree list

Claude: 워크트리 목록:
  /path/to/project                      abc1234 [main]
  /path/to/.worktrees/feat/login        def5678 [feat/login]

User: /worktree done

Claude: [uncommitted changes, unpushed commits 확인 후 안내]
```

---

## Permission 참고

이 스킬의 `allowed-tools`는 **스킬 실행 중에만** 유효하다. 워크트리 안에서 일반 개발(테스트, 빌드 등)을 할 때는 사용자의 `settings.json` permission이 적용된다.

**Note:** 이 스킬은 워크트리 관리만 담당한다. 커밋, 푸시 등은 `/commit`, `/pull-request` 등을 사용한다.
