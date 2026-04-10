# VCS 워크플로우

이 규칙은 `.claude/config.json`의 `"vcs"` 값에 따라 분기한다.

---

## Git 워크플로우 (vcs: "git" 또는 미설정)

**이 섹션은 `config.json`의 `vcs`가 `"git"`이거나 미설정(`""`)일 때만 적용한다. `"svn"`이면 아래 SVN 섹션을 따른다.**

### 브랜치 규칙

코드를 수정할 때는 **main에서 직접 수정하지 마세요.**

1. **파일을 수정하기 전에** 작업 브랜치를 먼저 생성하세요. 수정 후에 브랜치를 만드는 것이 아니라, 브랜치를 만든 뒤 수정을 시작하세요.

#### 브랜치 정리 시 안전 규칙

브랜치 삭제, `git clean` 등 정리 작업 전에 반드시 확인하세요:

1. `git status`로 미커밋 변경사항(modified, untracked) 확인
2. `git stash list`로 stash 확인
3. **미커밋 변경사항이 있으면 절대 삭제하지 않는다** — 사용자에게 먼저 알리고 지시를 받을 것
4. `--force` 옵션(`git branch -D` 등) 사용 금지 — 사용자가 명시적으로 요청한 경우에만
5. PR이 머지되었더라도 워킹 디렉토리에 새 작업이 시작되었을 수 있으므로 **PR 상태만으로 판단하지 않는다**

### 커밋 규칙

커밋/PR 스킬 라우팅 규칙은 `.claude/rules/skill-routing.md`를 따른다.

### 최신 상태 유지

**매 요청 시작 전** 아래를 순서대로 실행하세요:

1. `git branch --show-current`로 현재 브랜치 확인
2. **main이 아닌 브랜치에 있다면**:
   - `GH_HOST=github.com gh pr view --json state,mergedAt`로 해당 브랜치의 PR 상태를 확인
   - PR이 merged 상태일 때만 `git checkout main && git pull` 로 복귀
   - PR이 open이거나 PR이 없으면 **브랜치를 유지** — 임의로 main으로 돌아가지 마세요
3. **main 브랜치에 있다면**: uncommitted 변경이 없으면 `git pull --rebase --autostash` 실행

---

## SVN 워크플로우 (vcs: "svn")

### 브랜치 규칙

SVN은 브랜치 없이 trunk에서 직접 작업한다. 별도 브랜치 생성/관리가 불필요하다.

### 커밋 규칙

SVN에서는 `/gx-commit`, `/gx-pull-request` 스킬을 지원하지 않는다. `svn commit`을 직접 실행하세요.

### 최신 상태 유지

**매 요청 시작 전** `svn update`를 실행하여 최신 상태를 동기화하세요.
