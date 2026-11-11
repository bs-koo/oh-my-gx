# phase-setup 보조 — 작업 브랜치 준비

phase-setup Step 2(git)에서 Read하고 Step 5까지 같은 판정을 쓴다. "이름 충돌 확인"은 svn slug에도 적용한다. Step 번호는 phase-setup의 위치를 가리킨다.

아래 두 AskUserQuestion은 필수 질문이다. Codex는 [질문 대기 계약](../../gx-work/references/codex-questions.md)대로 등록·표시하고 실제 답을 기다린다. 무응답·추천 값으로 브랜치 전환·stash 정리를 진행하지 않는다.

## 2.1 미커밋 변경 분류

checkout·pull 전에 `git status --porcelain`을 본다. 비어 있으면 2.2로 간다. 비어 있지 않으면 아래 표를 위에서부터 판정해 처음 맞는 행을 따른다.

**이번 실행 입력**은 `.dev/<run-id>/` 아래 파일과, 인계·문서 사전 대조가 이번 실행에서 만들거나 고쳤다고 가리키는 관련 문서(`.dev/plan.md`의 이번 W행, 인계 `context-paths`·`requirements`의 원장)뿐이다.

| 순서 | 상황 | 처리 |
|---|---|---|
| 1 | 현재 브랜치의 `.dev/<현재 slug>/state.md`가 이번과 다른 run-id의 `status: in_progress`이고, 이번 실행 입력 밖의 변경이 있다 | **중단**. stash·checkout 없이 멈춘다. 그 실행의 미커밋 변경을 새 작업 브랜치로 옮기지 않기 위해서다. 사용자 동의를 받아 새 워크트리(`git worktree add <경로> -b <새 브랜치> <베이스>`)를 직접 만들고 경로와 다음 명령(그 경로에서 `/oh-my-gx:gx-work <목표>`)을 제시하거나(절차: gx-work [새 범위용 워크트리 만들기](../../gx-work/references/tdd-entry.md#새-범위용-워크트리-만들기)), 그 실행을 마무리한 뒤 다시 실행하라고 안내한다. gx-work 인계였다면 미커밋 인계 파일은 새 워크트리에 없으므로 진입 질문부터 다시 받는다 |
| 2 | 변경에 이번 실행 입력이 있다 (베이스 위이거나 HEAD가 베이스와 같으면 대표적인 경우) | **stash하지 않는다**. 2.2의 checkout·pull과 Step 5의 브랜치 생성이 변경을 그대로 가져간다. checkout이 "덮어쓸 수 없다"며 거부하면 그 파일 목록을 알리고 중단해 베이스 위나 별도 워크트리에서 다시 실행하도록 안내한다 — stash하면 setup이 그 문서를 읽지 못한다. pull이 그 파일 때문에 거부되면 경고하고 로컬 상태로 진행한다 |
| 3 | 그 밖 (이번 실행 입력 없이 다른 변경만 있다) | **자동 stash** (2.1.1) |

`git stash list`에 다른 run의 `gx-tdd-auto-` 항목이 있으면 알리기만 하고 적용·삭제하지 않는다. 이번 run의 `.dev/<run-id>/auto-stash.txt`가 이미 있으면(같은 실행의 setup을 다시 시작했다) 새로 stash하지 않고 그 SHA를 `AUTO_STASH_SHA`로 써서 2.2로 간다.

### 2.1.1 자동 stash

run-id를 먼저 확정한다(인계 값. 직접 호출은 여기서 만든 값을 Step 7까지 쓴다). stash 목록은 다른 세션·워크트리와 공유되므로 `stash@{0}`나 bare `git stash pop`을 쓰지 않고 run-id를 넣은 메시지와 SHA로만 다룬다. 이번 실행 디렉토리는 stash에서 빼서 인계·검사 결과를 계속 읽는다.

```bash
git stash push -u -m "gx-tdd-auto-${RUN_ID}" -- . ":(exclude).dev/${RUN_ID}"
AUTO_STASH_SHA=$(git stash list --format='%H %gs' | awk -v tag="gx-tdd-auto-${RUN_ID}" '$NF == tag {print $1; exit}')
test -z "${AUTO_STASH_SHA}" || { mkdir -p ".dev/${RUN_ID}" && printf '%s %s\n' "${AUTO_STASH_SHA}" "$(git branch --show-current)" > ".dev/${RUN_ID}/auto-stash.txt"; }
```

`AUTO_STASH_SHA`가 비면 저장할 변경이 실행 입력뿐이었으므로 stash 없이 진행한다. 값이 있으면 `AUTO_STASHED=true`다. **state가 생기기 전의 기록 위치**는 `.dev/<run-id>/auto-stash.txt`(SHA·원래 브랜치)와 stash 메시지 `gx-tdd-auto-<run-id>`다. Step 3~4에서 질문을 기다리다 끊긴 뒤 같은 실행을 이어 가면 이 파일로 복원 대상을 찾는다. Step 7과 충돌 골격은 같은 SHA를 state `auto-stash`에 옮긴다. 이 파일은 머신 로컬 기록이라 커밋하지 않는다.

Step 5 전에 setup을 끝내야 하면(사용자 중단·오류) 원래 브랜치(`auto-stash.txt`의 둘째 값)로 돌아가 2.3의 적용·정리를 하고 멈춘다. 질문 대기처럼 같은 실행을 이어 갈 때는 그대로 두고 대기 응답에 보관 중인 SHA를 함께 알린다.

**새 범위용 워크트리 브랜치 재사용**: 현재 브랜치가 보호 브랜치가 아니고, 그 브랜치의 `.dev/<slug>/state.md`가 없으며, HEAD가 베이스 브랜치 끝과 같으면(새 범위 안내대로 `git worktree add <경로> -b <새 브랜치> <베이스>`로 막 만든 경우) 2.2의 베이스 checkout과 Step 5의 새 브랜치 생성을 건너뛰고 현재 브랜치를 작업 브랜치로 쓴다. 베이스가 다른 워크트리에서 사용 중이라 checkout이 실패하는 것을 피하고, 사용자가 만든 브랜치를 빈 채로 남기지 않기 위해서다.

## 2.2 베이스 브랜치 동기화

1. `git remote get-url origin`으로 remote 존재를 확인한다. 없으면 pull 단계만 건너뛴다.
2. `git checkout <base-branch>`를 실행한다. 2.1 표 2행의 덮어쓰기 거부는 그 행대로 중단한다. 그 밖의 실패(다른 워크트리가 베이스를 사용 중 등)는 경고를 표시하고 현재 위치에서 진행한다.
3. checkout 성공 시 `git pull origin <base-branch>`를 실행한다. pull 실패 시(네트워크 오류 등) 경고를 표시하고 현재 로컬 상태로 계속 진행한다.

## 이름 충돌 확인 (Step 5)

브랜치명(svn은 slug)을 정한 뒤 만들거나 전환하기 전에 같은 이름의 진행 중 실행을 확인한다. git은 브랜치가 이미 있으면 `git show <브랜치>:.dev/<slug>/state.md`와 작업 트리의 `.dev/<slug>/state.md`를, 없으면 작업 트리 파일만 읽고 `git worktree list`로 다른 워크트리의 체크아웃 여부도 본다. svn은 `.dev/<slug>/state.md`를 읽는다. 이번과 다른 run-id의 `status: in_progress`이거나(파이프라인 무관) 다른 워크트리가 그 브랜치를 쓰고 있으면 전환·덮어쓰기 없이 묻는다. 같은 run-id면 이번 실행이므로 그대로 진행한다.

```
AskUserQuestion(
  questions: [{
    header: "이름 충돌",
    question: "{브랜치}에 진행 중인 다른 실행({run-id}: {goal})이 있습니다. 어떻게 할까요?",
    options: [
      { label: "다른 브랜치명으로 시작 (Recommended)", description: "{브랜치}-2처럼 겹치지 않는 이름으로 새 작업을 만듭니다" },
      { label: "기존 실행 이어서", description: "새로 시작하지 않습니다. 그 브랜치나 워크트리에서 --resume으로 이어 갑니다" },
      { label: "중단", description: "아무것도 바꾸지 않고 멈춥니다" }
    ],
    multiSelect: false
  }]
)
```

- **다른 브랜치명으로 시작** → 겹치지 않을 때까지 `-2`, `-3`을 붙인 이름(svn은 slug)으로 다시 확인하고 진행한다. 작업 계획의 `작업 위치`도 이 이름으로 기록한다.
- **기존 실행 이어서** → 새 실행을 만들지 않는다. 그 브랜치(또는 워크트리)에서 `/oh-my-gx:gx-tdd --resume`으로 이어 가라고 안내하고 멈춘다.
- **중단** → 바꾸지 않고 멈춘다.

자동 stash가 남아 있는데 이어서·중단을 고르면 2.1.1의 중단 처리(원래 브랜치에서 복원)를 먼저 한다.

## 2.3 stash 복원 (Step 5 직후)

`AUTO_STASHED=true`이면 작업 브랜치 전환 직후 같은 SHA를 적용한다. 베이스 브랜치로 변경이 섞이지 않도록 Step 5 전에는 적용하지 않는다(중단 시 원래 브랜치 복원은 예외).

```bash
git stash apply "${AUTO_STASH_SHA}"
```

성공하면 그 항목만 지우고 기록을 정리한다.

```bash
AUTO_STASH_REF=$(git stash list --format='%gd %H' | awk -v sha="${AUTO_STASH_SHA}" '$2 == sha {print $1; exit}')
test -z "${AUTO_STASH_REF}" || git stash drop "${AUTO_STASH_REF}"
rm -f ".dev/${RUN_ID}/auto-stash.txt"
```

`AUTO_STASHED=false`로 두고 execution-log에 `auto-stash-restored`를 남긴다.

충돌하면 충돌 파일(`git diff --name-only --diff-filter=U`)을 보여 주고 묻는다. 두 선택 모두 stash 항목을 바로 지우지 않는다.

```
AskUserQuestion(
  questions: [{
    header: "stash 복원",
    question: "자동 stash를 새 작업 브랜치에 적용하다 충돌했습니다({파일 목록}). 어떻게 할까요?",
    options: [
      { label: "직접 해결 후 재개 (Recommended)", description: "충돌을 그대로 두고 멈춥니다. 해결한 뒤 --resume으로 이어 가며 stash는 해결 확인 후 지웁니다" },
      { label: "stash 보관하고 계속", description: "적용을 되돌리고 변경은 stash에 남긴 채 진행합니다. 나중에 직접 적용해야 합니다" }
    ],
    multiSelect: false
  }]
)
```

- **직접 해결 후 재개** → 중단 전에 DEV_DIR을 Step 6.5 규칙(`.dev/{branch-slug}`)으로 확정해 `mkdir -p` 후 state 골격을 Write한다: `pipeline: gx-tdd`, `status: in_progress`, `phase: setup`, `current-step: stash 복원 충돌`, `auto-stashed: true`, `auto-stash: <SHA>`, Step 7 보존 필드. 골격이 없으면 `--resume`이 작업을 못 찾는다. 충돌 파일과 SHA를 알리고 멈춘다.
- **stash 보관하고 계속** → `git reset --merge`로 적용을 되돌리고 `git ls-tree -r --name-only "${AUTO_STASH_SHA}^3"`(그 커밋이 있을 때만)가 나열하는 파일, 즉 이번 적용이 만든 untracked 파일을 지운다. stash 항목은 남기고 `.dev/<run-id>/auto-stash.txt`는 지운다. `AUTO_STASHED=false`로 두고 trust-ledger `### 위험 수용`에 `- [자동 stash 미복원] {SHA}: 충돌로 stash에 보관 (setup/Step 5)`를 기록한 뒤 진행한다.

## 재개 (setup-resume에서)

- `current-step: stash 복원 충돌` → `git diff --name-only --diff-filter=U`가 비어야 한다. 남았으면 파일을 알리고 다시 멈춘다. 비었으면 2.3의 성공 정리(그 SHA 항목·기록 파일 삭제)를 하고 `auto-stashed: false`로 갱신한 뒤 phase-setup Step 5.5부터 남은 setup(5.5·6·6.5·7)을 마친다.
- `auto-stashed: true`인데 위 단계가 아니면(적용 전에 끊김) 현재 작업 브랜치에서 2.3을 수행한다.
