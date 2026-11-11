> gx-setup/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 3.6단계: 기본 베이스 브랜치 (git)

`main`과 `develop`이 함께 있는 저장소(git-flow)는 PR·작업 브랜치의 베이스를 실행마다 묻게 된다. 여기서 한 번 정해 `conventions.baseBranch`에 저장한다. 값이 있으면 gx-pull-request와 gx-tdd는 베이스를 묻지 않는다. 비어 있으면 실행 시 기존 자동 감지·질문을 쓴다.

1. `conventions.baseBranch`에 값이 있으면 `git rev-parse --verify --quiet <값>` 또는 `origin/<값>`으로 브랜치가 있는지 확인한다. 있으면 `기본 베이스 브랜치 : 완료 ✅ ({값}, 기존 설정 유지)`를 출력하고 끝낸다. 바꾸려면 config 값을 비우고 gx-setup을 다시 실행한다. 브랜치를 찾지 못했으면 그렇게 알리고 2로 간다.
2. `git branch --list main develop`과 `git branch -r --list origin/main origin/develop`으로 로컬·원격 브랜치를 확인한다. `main`과 `develop`이 **함께** 있을 때만 3으로 간다. 그 밖이면 `기본 베이스 브랜치 : 건너뜀 (main·develop 동시 존재 아님 — 실행 시 자동 감지)`를 출력한다.
3. 사용자에게 묻는다.
   ```
   AskUserQuestion(
     questions: [{
       header: "베이스 브랜치",
       question: "main과 develop이 함께 있습니다. PR·작업 브랜치의 기본 베이스를 무엇으로 할까요? 저장하면 이후 실행에서 묻지 않습니다.",
       multiSelect: false,
       options: [
         { label: "develop (Recommended)", description: "기능 브랜치를 develop에서 따고 develop으로 PR합니다 (git-flow)" },
         { label: "main", description: "main에서 따고 main으로 PR합니다" },
         { label: "매번 묻기", description: "저장하지 않고 실행마다 고릅니다" }
       ]
     }]
   )
   ```
4. develop·main을 고르면 `conventions.baseBranch`에 기록한다. Codex는 상위 스킬의 config helper에 `{"conventions":{"baseBranch":"{선택}"}}` updates만 전달하고, Claude Code는 기존 Edit를 사용한다. `기본 베이스 브랜치 : 완료 ✅ ({선택})`을 출력한다. "매번 묻기"면 기록하지 않고 `기본 베이스 브랜치 : 건너뜀 (매번 묻기)`를 출력한다.
