# setup-testplan: 단위테스트계획서(DE-13) 연동

phase-setup 3.1의 6번 항목이 이 파일을 읽는다. 계획서가 없으면 아무것도 하지 않고 돌아간다. 헬퍼는 [de13.py](../../gx-test-plan/scripts/de13.py)이며, 이 파일 위치 기준 `../../gx-test-plan/scripts/de13.py`의 절대경로를 `DE13`으로 둔다 (소비 프로젝트 cwd 기준이 아니다). 실행은 `python3 "<DE13>" …`, Windows는 `python "<DE13>" …`. 둘 다 없으면 "Python이 없어 단위테스트계획서 연동을 건너뜁니다" 1줄을 안내하고 돌아간다.

## 1. 계획서 탐지

`PROJECT_ROOT` 아래에서 `*단위테스트계획서*.xlsx`를 찾는다. `~$`로 시작하는 파일, 이름에 `_결과반영_`이 든 파일, `.dev/` 아래, 빌드 산출물 디렉터리(`projectTypes.*.artifacts`)는 뺀다.

- 0개: 연동하지 않는다. 안내도 출력하지 않는다.
- 1개: 그 파일을 `TESTPLAN`으로 둔다.
- 2개 이상: 최근 수정 순 2개와 "연동 안 함"으로 묻는다. 다른 파일은 UI Other로 경로를 받는다.

```
AskUserQuestion(
  questions: [{
    question: "단위테스트계획서가 여러 개입니다. 어느 파일을 이번 작업의 하한선으로 쓸까요?",
    header: "계획서",
    options: [
      { label: "{파일 1}", description: "최근 수정: {날짜}" },
      { label: "{파일 2}", description: "최근 수정: {날짜}" },
      { label: "연동 안 함", description: "계획서 없이 gx-tdd를 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

## 2. 범위 확정

`python3 "<DE13>" scope --plan "<TESTPLAN>" --out "${PROJECT_ROOT}/.dev/ut-results/export/functions.json"`을 실행해 기능 목록을 얻는다 (`DEV_DIR`이 아직 정해지지 않은 시점이라 커밋되지 않는 반영 사본 폴더에 쓴다 — gx-commit이 이 폴더를 언스테이징한다). 같은 폴더에 `*기능명세서*.xlsx`가 하나 있으면 `--spec "<그 파일>"`을 붙인다. 종료 코드 2면 메시지를 보여주고 연동하지 않는다.

1. **`--work` 사용 시**: plan.md 해당 행의 `요구사항` 열에서 목록에 있는 기능ID를 찾는다.
2. **그 외**: ARGS[0]의 토큰 중 목록의 `기능ID`와 정확히 같은 것을 범위로 삼는다.
3. 찾은 기능ID는 **ARGS[0]에서 지운다** — Step 5가 `REB-FN-001`의 `FN-001`을 이슈 키(`대문자-숫자`)로 오인해 타입 없는 브랜치를 만들지 않게 하기 위해서다. 지운 자리에는 목록의 `기능명`을 넣어 Step 4 코드 맵 키워드로 쓴다.
4. 기능ID가 하나도 없으면 목록의 `기능명`(비어 있으면 그 기능 UT 행의 입력·기대결과)과 요청 문장이 가장 많이 겹치는 기능을 최대 2개 고른다.

```
AskUserQuestion(
  questions: [{
    question: "이번 작업이 단위테스트계획서의 어느 기능에 해당하나요? 해당 기능의 단위테스트 케이스가 최소 하한선이 됩니다.",
    header: "계획서 기능",
    options: [
      { label: "{기능ID 1} {기능명 1}", description: "단위테스트 {UT수}건" },
      { label: "{기능ID 2} {기능명 2}", description: "단위테스트 {UT수}건" },
      { label: "연동 안 함", description: "계획서 하한선 없이 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

겹치는 후보가 하나도 없으면 다음 질문을 쓴다.

```
AskUserQuestion(
  questions: [{
    question: "요청과 겹치는 계획서 기능을 찾지 못했습니다. 기능ID를 지정할까요?",
    header: "계획서 기능",
    options: [
      { label: "기능ID 지정", description: "다음 질문에서 기능ID를 받습니다" },
      { label: "연동 안 함", description: "계획서 하한선 없이 진행합니다" }
    ],
    multiSelect: false
  }]
)
```

"기능ID 지정"을 고르면 별도 후속 질문으로 기능ID(여러 개면 쉼표)를 묻고 실제 답변을 기다린 뒤 진행한다. 답이 목록에 없으면 한 번 더 묻고, 두 번째도 없으면 연동하지 않는다.

## 3. 하한선 저장

범위가 정해지면 Step 6.5에서 `DEV_DIR`이 확정된 뒤 실행한다:

`python3 "<DE13>" scope --plan "<TESTPLAN>" --fn "<기능ID,…>" --out "${PROJECT_ROOT}/${DEV_DIR}/ut-floor.md"`

`--plan`은 `PROJECT_ROOT` 기준 상대경로로 넘긴다 (ut-floor의 `출처`에 그대로 남는다). 종료 코드 2면 메시지를 보여주고 연동하지 않는다. 성공하면 Step 7에서 state.md에 `ut-scope: <기능ID,…>`를 기록하고, 결과 한 줄(`하한선 N행(대상 M)`)과 `제외(미확정 행)` 행 수를 사용자에게 보고한다.

## 4. ignore 보강 (연동이 켜졌을 때만)

- **git**: `.gitignore`에 `~$*.xlsx`와 `.dev/ut-results/export/`가 없으면 추가한다.
- **svn**: `svn propget svn:ignore .`에 `~$*.xlsx`가 없으면 추가하고, `.dev/ut-results/export`는 `svn:ignore`를 `.dev/ut-results`에 설정한다 (디렉터리가 없으면 만든 뒤 `svn add --depth=empty`).

## 5. 단독 진입 (`--phase implement`·`--phase complete`)

SKILL.md 환경 감지 8이 이 절을 읽는다. state.md에 `ut-scope`가 있고 `${DEV_DIR}/ut-floor.md`가 있으면 그대로 쓴다. 둘 다 없으면 1(계획서 탐지)을 수행하고, 계획서가 있으면 2의 기능 질문을 한 번 한 뒤 3을 수행한다. "연동 안 함"이면 1줄 안내 후 진행한다.

## 6. 계획서 교체 감지

`ut-floor.md`의 `출처` 줄 sha256과 현재 계획서의 sha256 앞 12자(`python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:12])" "<TESTPLAN>"`)가 다르면 phase-complete 게이트 2가 경고한다. 범위를 다시 추출할지는 그 게이트가 묻는다.
