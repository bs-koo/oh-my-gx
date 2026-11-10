---
name: gx-commit
description: Git 변경사항의 커밋(commit), 커밋 대상 미리보기, 포함·제외 파일 확인 요청에 사용한다. 보호 브랜치·검증 상태를 확인하고 브랜치 규칙에 맞는 한국어 메시지로 커밋한다.
argument-hint: "[커밋 메시지 | --preview] [--skip-context-sync]"
allowed-tools:
  # git - 커밋 핵심
  - Bash(git rev-parse:*)
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git show:*)
  - Bash(git branch:*)
  - Bash(git check-ignore:*)
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
  # 양 하네스의 인덱스 보존·제외 helper (Python 3.10+)
  - Bash(python:*)
  - Bash(python3:*)
  # 파일 도구
  - Read
  - Glob
  - Grep
  # 사용자 확인 — 민감 파일 경고, 대량 스테이징 확인
  - AskUserQuestion
  # 사용자가 커밋과 PR을 함께 요청했을 때 PR 연쇄
  - Skill
---

# 커밋 작성

변경사항을 스테이징하고, 브랜치명에서 타입을 파싱하여 `{type}: 한국어 메시지` 형식으로 커밋한다.

Arguments:
- 인자 없음: 타입은 브랜치에서 파싱, 메시지는 변경 내용에서 자동 생성
- ARGS[0]만: 커밋 메시지로 사용. 타입은 브랜치에서 파싱
- `--preview` 또는 "커밋 대상 미리보기": 아래 조회 분기로 실행하고 종료한다.
- `--skip-context-sync`: 커밋 후 context 동기화 질문을 생략한다. context 동기화를 자체 단계로 처리하는 파이프라인(gx-tdd phase-complete)이 전달한다. 플래그는 먼저 분리하며 커밋 메시지로 쓰지 않는다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("../gx-work/references/codex-runtime.md")`로 공통 실행 규약을 읽고, 이 스킬의 절차·게이트를 유지한다. 상대경로는 이 SKILL.md 위치 기준이다.
Codex 지문 helper의 설치 경로는 **이 SKILL.md 디렉토리 기준** [../../../scripts/codex-fingerprint.py](../../../scripts/codex-fingerprint.py)다. 실제 설치된 SKILL.md 절대경로 `SKILL_PATH`에 대해 `Path(SKILL_PATH).resolve().parents[3]`가 `GX_PLUGIN_ROOT`이며, `.codex-plugin/plugin.json`과 helper의 존재를 확인한다. Windows PowerShell: `$skillPath = (Resolve-Path -LiteralPath '<installed SKILL.md>').Path; $pluginRoot = (Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $skillPath) '..\..\..')).Path; $helper = (Resolve-Path -LiteralPath (Join-Path $pluginRoot 'scripts/codex-fingerprint.py')).Path`. 아래 지문 명령의 `<GX_PLUGIN_ROOT>`는 이 경로로만 치환하고, Windows에서는 확인한 `$helper` 절대경로를 사용한다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → 공통 codex-runtime의 질문 대기 계약으로 옮긴다. 실제 모드·용도가 허용하는 `request_user_input`·`request_user_input_async` 또는 자연어를 사용한다. 필수 질문은 pending 상태를 저장하고 실제 답변·결정 기록 전 다음 단계로 넘어가지 않는다. async 반환은 답변이 아니며 본문·선택지를 표시한다.

- `Skill` → Codex는 대상 스킬(커밋 후 PR 연쇄의 gx-pull-request)의 설치된 `SKILL.md`를 읽고 절차와 게이트를 그대로 수행한다.

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.

## VCS 가드

`.claude/config.json`의 `"vcs"` 필드를 확인한다.
- `"svn"` → 즉시 종료: "SVN 프로젝트에서는 /gx-commit을 지원하지 않습니다. `svn commit`을 직접 실행해주세요." 출력.
- `"git"` 또는 `""` (미설정) → 아래 절차를 계속 진행한다.

## 사전 확인

**미리보기 선행 분기**: `--preview`/"커밋 대상 미리보기"는 `Read("references/index-helper.md")`의 미리보기 절차만 수행하고 종료한다(보호 브랜치에서도 조회 허용, 커밋 가능 판정 아님, 파일 내용·비밀값 미출력, index·작업 파일 불변). 아래 사전 확인·빌드·스테이징·커밋은 실행하지 않는다.

레거시 선행 검사: 현재 작업의 `status: in_progress`인 state에 `pipeline: gx-ralph` 또는 `flags`의 `--ralph`/`RALPH`가 있거나, state 유무·완료 표식과 무관하게 `ralph.lock`이 남아 있으면 빌드·스테이징·커밋·push·PR 전에 중단하고 전환을 안내한다. 훅이 로드되지 않았어도 적용한다.

- Git 저장소인지 확인
- **작업 디렉토리 보정**: `git rev-parse --show-toplevel`로 Git 루트를 확인한다. 현재 디렉토리와 다르면 (워크스페이스 root에서 호출된 경우 등), 이후 모든 git/빌드 명령을 Git 루트 기준 서브셸 `(cd <git-root> && <명령>)`로 실행한다.
- **보호 브랜치 선행 중단**: 현재 브랜치를 먼저 확인한다. `main`/`master`/`develop` 또는 detached HEAD이면 빌드·스테이징·커밋을 하지 않고 작업 브랜치가 필요하다고 안내하며 종료한다. 훅 로드 여부와 관계없이 적용한다.
- 커밋할 변경사항이 있는지 확인 (없으면: "커밋할 변경사항이 없습니다.")
- **verify 게이트 (gx-tdd·레거시 gx-ralph 기록)**: Git 루트 기준 `.dev/{branch-slug}/state.md`(branch-slug = `git branch --show-current` 결과의 `/`를 `-`로 치환)가 존재하고 `pipeline: gx-tdd` 또는 `pipeline: gx-ralph`이며 `status: in_progress`이고 **(a) `verify-status`가 `passed`가 아니거나 (b) `verify-fingerprint`가 기록되어 있는데 현재 코드 지문과 트리 성분이 다르면**(=verify 통과 후 코드가 바뀜 — HEAD 성분은 참고용이며, 검증된 코드가 그대로 커밋되어 HEAD만 전진한 경우는 일치로 간주한다) verify 게이트 미통과(또는 통과 후 코드 변경) 상태다. **Codex에서는 gx-verify 수행을 안내하고 빌드·스테이징·커밋 전에 중단한다. 사용자 질문이나 위험 수용만으로 미통과를 통과로 취급하지 않는다.** Claude Code에서는 기존 경고·사용자 위험 수용 분기를 유지하되, 위 보호 브랜치 중단을 먼저 적용한다. `pipeline: gx-ralph`는 제거된 레거시 실행이다. status가 in_progress이거나 ralph.lock이 남아 있으면 검증 표식과 무관하게 커밋 전에 중단한다. 기록을 보존하고 진행 중인 외부 프로세스 종료와 명시적 gx-tdd 전환을 안내하며 자동 재개·상태 변환을 하지 않는다.
  - **지문 계산 규약** (훅·gx-verify와 동일): 임시 인덱스에 워킹트리 전체를 `add -A`한 뒤 `.dev`를 인덱스에서 제거하고 `write-tree`한 **트리 해시**(앞 12자)를 `git rev-parse --short HEAD`와 `:`로 이은 값 (스테이징 여부와 무관하도록 트리 해시를 쓴다 — `git diff HEAD`는 신규 파일이 스테이징되면 값이 바뀐다). `.dev/`를 제외하는 이유는 파이프라인 산출물이 코드가 아니며, 포함하면 상태 기록 때마다 지문이 스스로 무효화되기 때문이다. **대조는 트리 성분(콜론 뒤 12자)만 수행한다** — HEAD 성분은 기록·추적용이며, 커밋으로 HEAD가 전진해도 트리가 같으면 일치다.
  - **Codex 계산 경로**: 설치된 GX 플러그인 루트의 `scripts/codex-fingerprint.py` 존재를 확인하고, `git rev-parse --show-toplevel`로 얻은 소비 프로젝트 절대경로를 `--cwd`에 전달한다. Windows는 확인된 Python 3.10+로 `python "<GX_PLUGIN_ROOT>/scripts/codex-fingerprint.py" --cwd "<PROJECT_ROOT>"`, Linux는 `python3 "$GX_PLUGIN_ROOT/scripts/codex-fingerprint.py" --cwd "$PROJECT_ROOT"`를 실행한다. **exit 0과 stdout의 정확한 한 줄 `^[0-9a-f]+:[0-9a-f]{12}$`**을 확인한 뒤 **트리 성분만** state.md와 대조한다. helper 실패·부재·빈/잘못된 출력이면 커밋 전에 중단한다. Codex에서 임시 인덱스 직접 Git 명령으로 대체하지 않는다. `git add`/`write-tree`가 실제 `.git/objects`에도 쓰기 때문이다. Claude Code는 위 기존 계산을 유지한다.
  - `verify-fingerprint` 필드가 없는 구 세션은 (a)만 판정한다 (하위 호환). `pipeline` 필드가 없거나 다른 값인 state.md(제거된 gx-dev의 레거시 기록 등)에는 적용하지 않는다.
- 커밋 전 검증은 [공통 테스트 실행 계약](../gx-tdd/references/test-execution.md)을 따른다. 같은 run-id의 최신 verify가 같은 트리 지문·설정·buildOnly 명령·scope의 성공 proof를 제공하면 `reuse`로 확인하고 빌드를 반복하지 않는다. 검증되지 않은 과거 로그·모델의 기억은 증거가 아니다.
- 코드·설정·명령·범위가 달라지거나 로그가 변조되면 영향 계획을 다시 계산해 필요한 buildOnly/테스트를 실행한다. 실패·0건·helper 오류는 우회하지 않는다. Gradle `build`에 테스트가 포함되므로 별도 테스트 이후에는 명시된 `buildOnly`를 사용한다. 독립 커밋에 proof가 없으면 같은 계약으로 검증한다.
- 타임아웃: config.json `timeouts.build`(기본 300000ms). 타임아웃을 성공이나 단순 건너뛰기로 처리하지 않는다.

## 타입 파싱

브랜치명에서 타입을 추출한다:
1. `git branch --show-current`로 브랜치명 확인
2. 첫 번째 `/` 앞의 세그먼트를 타입으로 사용 (예: `feat/login` → `feat`). `codex/feat-...`처럼 하네스 접두사가 있으면 다음 세그먼트의 명시 타입을 사용한다. 명시 커밋 메시지에 유효한 타입이 있으면 그 타입을 보존한다.
3. 허용 타입: `.claude/config.json` → `conventions.branchTypes` 참조
4. 브랜치명에서 타입을 추출할 수 없으면 (예: `release-without-prefix`; 보호 브랜치는 사전 확인에서 이미 중단):
   ```
   AskUserQuestion(
     questions: [{
       header: "커밋 타입",
       question: "브랜치명에서 타입을 추출할 수 없습니다. 커밋 타입을 선택해주세요.",
       multiSelect: false,
       options: [
         { label: "feat", description: "새 기능" },
         { label: "fix", description: "버그 수정" },
         { label: "refactor", description: "리팩토링" },
         { label: "Other로 입력", description: "Other로 이동해서 다른 타입(docs, test, chore 등)을 자연어로 입력해주세요" }
       ]
     }]
   )
   ```

## 커밋 메시지 생성

메시지를 자동 생성할 때:
1. `git diff --stat` (또는 `--cached --stat`)로 변경 요약 확인
2. 변경 파일 50개 이하면 `git diff --cached`로 상세 diff 확인. 50개 초과면 `--stat` 요약만으로 메시지 생성
3. 어떤 파일이 수정/추가/삭제되었는지 파악

**메시지 구조**:
- **제목 (첫 줄)**: `{type}: {한국어 요약}` (config.json `conventions.commitFormat` 형식). 50자 이내.
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

0. `Read("references/index-helper.md")`로 helper 실행 방법을 확인한다. **Claude Code와 Codex 모두** 설치 루트의 [../../../scripts/gx-commit-index.py](../../../scripts/gx-commit-index.py)를 확인된 Python 3.10+로 사용한다(UTF-8 stdin JSON 입력·JSON 출력, `cwd`는 소비 Git 루트 절대경로). helper 부재·실패는 스테이징/커밋 전에 중단한다.
1. `git status --short`로 변경 파일 목록을 확인하고, 목록을 사용자에게 표시한다. 목록에 **현재 브랜치 슬러그가 아닌 `.dev/{다른-slug}/`** 경로가 있으면 다른 작업의 잔재일 수 있으므로 포함 여부를 사용자에게 확인한다. 단 `.dev/architecture/`와 `.dev/*/visual/`은 gx-visualize의 단발성 산출물이므로 묻지 않는다 — 5단계에서 스테이징하지 않는다. 현재 state의 `run-id`(`^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$`)가 가리키는 `.dev/<run-id>/`와 보호 브랜치 질문의 결정 기록 `.dev/{main,master,develop,trunk}/decisions.md`는 잔재로 묻지 않는다. run 디렉토리는 다른 PC·워크트리에서 재개하도록 커밋에 포함하고(질문·잠금 런타임 파일은 `.gitignore` 공유 블록이 제외한다), 보호 브랜치 결정 기록은 5단계 helper가 제외한다. 이를 `커밋 포함: .dev/<run-id>/ · 커밋 제외: .dev/main/decisions.md`처럼 한 줄 알린다.
2. 빌드 아티팩트 패턴(`.claude/config.json`의 모든 `projectTypes.*.artifacts`와 레거시 `buildArtifactPatterns`의 **합집합** — 타입별 artifacts가 SSOT)이 tracked 파일 목록에 있으면: `.gitignore` 파일 존재와 패턴을 확인한다. 일치하는 실제 tracked 파일 경로를 `UNTRACK` 배열에 모은다. `.gitignore`가 없거나 패턴이 없으면 사용자에게 생성/추가 여부를 확인한다. 이 단계에서는 index를 변경하지 않고 Step 5 helper의 `untrack`으로 넘긴다. helper의 tracking 해제는 `--cached`만 사용하여 작업 파일을 보존한다.
3. 민감 파일 패턴(`.claude/config.json` → `sensitiveFilePatterns` 참조)이 목록에 있으면 사용자에게 경고하고 스테이징에서 제외할지 확인한다. 사용자가 명시적으로 제외한 **실제 파일 경로**를 `EXCLUDES` 배열에 기록한다. 이미 staged인 파일도 같은 제외 대상이다. 응답 대기 중에는 index를 변경하지 않는다.
4. 변경 파일이 20개를 초과하면 변경 범위를 요약한다. 사용자가 이번 범위의 구현·커밋·PR을 이미 요청했고 다른 작업 변경이 없으면 동일 스테이징 승인을 반복하지 않는다. 관련 없는 변경이 섞였거나 범위가 불명확할 때만 포함 여부를 확인한다.
4.5. **`.dev` 무시 경고**: `.dev/` 디렉토리가 있고 `git check-ignore -q .dev/gx-ignore-probe`가 종료 코드 0이면 `.dev`가 git에서 무시되는 상태다. `git add -A`가 작업 계획과 산출물을 소리 없이 빼고 커밋하므로, `git check-ignore -v .dev/gx-ignore-probe`의 출처·줄과 함께 "`.dev`가 무시되어 작업 계획·산출물이 이 커밋에 들어가지 않습니다. `/gx-setup`에서 고칠 수 있습니다"를 경고한다. 커밋은 막지 않고 `.gitignore`도 여기서 고치지 않는다 — 커밋 도중 무시 규칙을 바꾸면 사용자가 의도하지 않은 파일까지 스테이징된다.
5. 스테이징·보존은 helper로 수행한다(요청 형식·차단 조건은 참조 파일). 같은 작업 중 외부 Git/index 변경을 병행하지 않는다.
   - `snapshot`으로 현재 worktree의 실제 index를 작업 트리 밖에 보존한다. 기존 `index.lock`·별도 Git 경로 환경변수·split index면 변경 전에 중단한다.
   - `stage`에 `paths`(`null`은 승인된 전체 변경, 일부 범위만 승인됐다면 실제 상대 파일 경로 배열이다(현재 run 디렉토리는 넣고 보호 브랜치 결정 기록은 넣지 않는다)), `excludes`(Step 3·범위 선택에서 확정한 EXCLUDES. 이미 staged인 파일도 HEAD 기준으로 내리고 작업 파일은 보존한다), `untrack`(Step 2의 UNTRACK, `--cached`만 사용)을 전달한다. runtime·시각화 산출물·보호 브랜치 결정 기록은 항상 제외한다. 해당 pathspec은 `git reset -q -- '.dev/*/ralph.lock' '.dev/*/iter-*.log' '.dev/*/auto-stash.txt' '.dev/architecture' '.dev/*/visual/*' '.dev/main/decisions.md' '.dev/master/decisions.md' '.dev/develop/decisions.md' '.dev/trunk/decisions.md'`와 같다 (루프 락·로그는 다른 사용자의 게이트 판별을 흐리고, 시각화 산출물은 단발성이며, 보호 브랜치 결정 기록은 이후 모든 작업 브랜치에 섞인다). 현재 run 디렉토리는 제외하지 않는다.
   - 커밋 **직전** `assert-excluded`의 exit 0을 확인한다. 명시 제외 경로가 cached diff에 남거나 HEAD/index가 바뀌면 커밋하지 않는다. helper 오류를 빈 목록/성공으로 간주하지 않는다.
6. HEREDOC 포맷으로 커밋:
   ```bash
   git commit -m "$(cat <<'EOF'
   {type}: 제목

   - 변경사항 1
   - 변경사항 2
   EOF
   )"
   ```
7. 스테이징/커밋이 실패하면 `restore`로 원 index bytes를 복원한다. **파일명 목록으로 reset/add하여 복원하지 않는다.** 복원할 수 없으면 강제 덮어쓰기·lock 삭제 없이 중단하고 에러와 보존된 snapshot 경로를 보고한다.
8. 성공하면 `git show --stat HEAD`로 결과를 표시하고 `finish`로 이 실행의 백업만 정리한다. 정리 실패는 커밋 재시도 사유가 아니며 남은 snapshot 경로를 보고한다.

## 커밋과 PR을 함께 요청한 경우

사용자가 같은 요청에서 PR도 원했으면("커밋하고 PR", "커밋 후 PR 올려줘") 커밋이 성공한 뒤에만 `Skill(skill: "oh-my-gx:gx-pull-request")`를 이어서 수행한다(Codex는 설치된 gx-pull-request `SKILL.md` 절차와 게이트를 그대로 수행한다). 커밋이 실패·중단되면 PR을 진행하지 않고 그 결과를 보고한다. gx-tdd 파이프라인처럼 다른 스킬이 이 스킬을 호출한 경우에는 호출한 쪽이 PR 단계를 직접 관리하므로 적용하지 않는다.

## 커밋 후: context 동기화 체크

커밋이 성공하면, 변경된 파일이 기존 context 도메인과 관련 있는지 확인하여 동기화를 제안한다.

0. `--skip-context-sync`를 받았으면 이 단계를 건너뛴다. 호출한 파이프라인이 같은 변경의 context 동기화를 이미 확인했으므로 같은 질문을 반복하지 않는다.
1. `context/` 디렉토리가 존재하는지 확인한다. 없으면 이 단계를 건너뛴다.
2. `context/*/PROJECTS.md`를 Glob으로 탐색한다. 없으면 건너뛴다.
3. 각 `PROJECTS.md`를 Read하여 프로젝트 매핑(소스 경로 패턴)을 파싱한다.
4. 커밋된 파일 목록(`git diff --name-only HEAD~1..HEAD`)과 각 도메인의 소스 경로 패턴을 대조한다.
5. 매칭되는 도메인이 있으면:
   ```
   AskUserQuestion(
     questions: [{
       header: "context 동기화",
       question: "{도메인} 도메인(context/{도메인}/)과 관련된 파일이 변경되었습니다. context를 동기화할까요?",
       multiSelect: false,
       options: [
         { label: "동기화", description: "context 동기화 안내를 출력합니다" },
         { label: "건너뛰기", description: "동기화하지 않고 진행합니다" }
       ]
     }]
   )
   ```
   - "동기화" 선택 시: 안내만 출력한다. "`/gx-context {도메인} 동기화해줘`로 동기화할 수 있습니다." (commit 스킬 내에서 context 스킬을 직접 실행하지 않는다)
6. 매칭되는 도메인이 없으면 이 단계를 건너뛴다.

**금지**: `Co-Authored-By` 라인을 절대 추가하지 말 것.
