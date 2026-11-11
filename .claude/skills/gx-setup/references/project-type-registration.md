> gx-setup/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 0.5단계: 프로젝트 타입 등록

`.claude/config.json`의 `projectTypes`를 프로젝트에 맞게 등록한다. **SSOT는 config에 등록된 값**이며, 힌트 카탈로그는 제안용이다.

1. **등록 출처와 기존 값 확인**: 상위 스킬의 `CONFIG_SOURCE`를 유지한다. `existing`의 사용자 명령·`roots`·확장 필드는 보존한다. `template`은 이번에 복사한 제안 기본값이므로 검증된 기존 등록이 아니다. 한 타입이 매칭돼도 여기서 7로 단락하지 않는다.
2. **추가·하위 빌드 파일 스캔**: 설치된 [gx-setup-scan.py](../../../../scripts/gx-setup-scan.py)를 `python "<GX_PLUGIN_ROOT>/scripts/gx-setup-scan.py" --cwd "<PROJECT_ROOT>" --config-source "<CONFIG_SOURCE>"`로 실행한다 (Bash는 `python3`, PowerShell은 `python`). helper는 설정을 쓰지 않고 루트·하위 빌드 마커, 등록된 타입·`roots`와 미확인 마커를 반환한다. `.claude`·`.dev`·빌드/의존성·다른 worktree와 링크는 제외한다. 링크는 따라가지 않고 건너뛴 경로를 `skipped_links`에 남기며, 비어 있지 않으면 `requires_confirmation`이 true이므로 사용자에게 그 경로의 하위 프로젝트 표식을 직접 확인받는다. exit 2 또는 `scan_errors`는 조사 실패로 보고하며 '추가 타입 없음'으로 바꾸지 않는다. helper 부재 시 같은 제외 경계의 Glob으로 조사하고 불완전한 범위를 명시한다.
   - 마커: `Makefile`, `CMakeLists.txt`, `project.yml`, `Cargo.toml`, `pom.xml`, `pyproject.toml`, `setup.py`, `requirements.txt`, `go.mod`, `*.csproj`, `*.sln`, `composer.json`, `build.gradle`, `build.gradle.kts`, `package.json`.
   - `existing`이고 미확인 마커·읽기 실패가 없을 때만 `프로젝트 타입 등록 : 완료 ✅ ({타입}, 기존 등록 유지)` 출력 후 **7(하네스 확인)으로 진행**한다. 기존 명령을 힌트 기본값으로 바꾸지 않는다.
   - `template` 또는 미확인 마커가 있으면 아래 3으로 진행한다. `build.gradle` + `frontend/package.json`처럼 하위 스택도 포함한다. 같은 프로젝트의 대체 마커는 하나로 묶고 독립 프로젝트는 분리한다. config 부재를 복구한 이번 실행과 사용자가 검증한 기존 등록을 구별한다.
3. **제안 생성**: `Read("project-type-hints.md")`로 힌트 카탈로그를 읽어 감지 파일과 매칭한다.
   - 매칭되면 해당 행의 타입 키·build/test·warningPattern·artifacts를 제안 값으로 사용한다.
   - **여러 행이 매칭되면** 두 가지 상황을 구분한다. 잘못 고르면 한쪽 레이어가 영구히 검증되지 않으므로 사용자에게 물어본다.
     - **부수 감지**: 한쪽이 도구용일 뿐 별도 테스트 대상이 아닌 경우 (예: C 프로젝트의 도구용 `package.json`, 문서 사이트용 `package.json`). → 주 타입 하나를 고른다.
     - **복합 타입**: 양쪽 모두 실제 소스와 테스트를 가진 경우 (예: `build.gradle.kts` + `frontend/package.json`인 풀스택 모노레포). → **한 타입 키에 양쪽을 `&&`로 이은 복합 명령**을 등록한다. 하나만 고르면 나머지 레이어는 verify 게이트가 아예 실행하지 않아 미검증 상태로 통과한다. 복합 명령은 저장소 루트에서 돌므로 `roots: ["."]`를 함께 등록한다(없으면 `frontend/package.json`의 디렉토리가 별도 프로젝트로 감지된다).
     ```
     AskUserQuestion(
       questions: [{
         header: "타입 구성",
         question: "빌드 파일이 여러 개 감지되었습니다: {목록}. 어떤 구성인가요?",
         multiSelect: false,
         options: [
           { label: "복합 (양쪽 모두 테스트 대상)", description: "한 타입에 양쪽 build/test를 && 로 이어 등록합니다. 풀스택 모노레포의 기본 선택입니다" },
           { label: "{주 타입}만 대상", description: "나머지는 도구용이라 테스트 대상이 아닙니다" }
         ]
       }]
     )
     ```
     복합을 선택하면 각 행의 명령을 `&&`로 잇고 타입 키는 프로젝트를 나타내는 이름으로 제안한다 (예: `fullstack`). 복합 명령은 저장소 루트에서 돌므로 `roots: ["."]`를 함께 등록한다(없으면 `frontend/package.json`의 디렉토리가 별도 프로젝트로 감지된다). 기존에 별도 타입·`roots`가 등록돼 있으면 이를 보존하고 미등록 프로젝트만 추가하는 안도 제시한다. 기존 `roots`를 지우거나 미확인 마커만으로 자동 확대하지 않는다. 명령 조합 규칙과 주의점은 힌트 카탈로그의 "복합 타입" 절을 따른다.
   - 매칭되지 않으면 프로젝트 구조(빌드 스크립트, README, CI 설정)를 근거로 추론해 제안하되 근거를 함께 표시한다. 근거 없는 명령을 지어내지 않는다.
   - 아무 빌드 파일도 감지되지 않으면 → `프로젝트 타입 등록 : 건너뜀 (감지 실패)` 출력 후 1단계로 진행한다 (파이프라인 게이트가 fail-closed로 처리).
4. **사용자 확인**:
   ```
   AskUserQuestion(
     questions: [{
       header: "타입 등록",
       question: "감지된 프로젝트 타입: {타입키}. 명령을 확인해주세요. build: `{build}`, test: `{test}`",
       multiSelect: false,
       options: [
         { label: "등록 (Recommended)", description: "이 값으로 config.json projectTypes에 기록합니다" },
         { label: "명령 수정", description: "Other로 이동해서 build/test 명령을 직접 입력해주세요" },
         { label: "건너뛰기", description: "등록하지 않습니다. 파이프라인 게이트에서 매번 직접 입력해야 합니다" }
       ]
     }]
   )
   ```
   - "등록" → 5로 진행. "명령 수정" → 입력값 반영 후 5로 진행. "건너뛰기" → `프로젝트 타입 등록 : 건너뜀 (사용자 선택)` 출력 후 1단계로 진행.
5. **config 기록**: 확정 값을 `projectTypes.{타입키}`에 기록한다 (`detect`/`build`/`test`/`focusedTest`/`warningPattern`/`artifacts`. 빈 제안 값은 필드를 생략한다). Codex에서는 위 helper에 `{"projectTypes":{"{타입키}":{확정한 필드만}}}` 형태의 updates만 전달해 기존 타입의 다른 필드와 사용자 정의 필드를 보존한다. Claude Code는 기존 Edit를 사용한다. `focusedTest`는 선택 필드로, 특정 테스트만 실행하는 명령 템플릿이다 — `{files}`(테스트 파일 경로 공백 구분) 또는 `{pattern}`(클래스 글롭 — 파일명에서 유도) 플레이스홀더를 쓴다. 미등록 시 gx-tdd가 전체 `test` 명령으로 폴백한다. 레이어별로 등록할 때 `/`가 든 detect는 그 파일의 디렉토리에서 명령을 실행하고 `{files}`도 그 디렉토리 기준이다. 같은 디렉토리로 들어가는 앞의 `cd`는 helper가 벗기며, 다른 디렉토리로 가는 `cd`와 테스트를 제외하지 않은 custom `build`(`buildOnly` 없음)는 config 오류다.

   **기록 직후 감지 확인** (이번에 등록·변경한 타입이 있을 때, git만): gx-tdd·gx-verify가 쓰는 테스트 계획 helper로 감지되는지 확인한다. 설치된 [gx-test-plan.py](../../../../scripts/gx-test-plan.py)를 `python "<GX_PLUGIN_ROOT>/scripts/gx-test-plan.py" plan --cwd "<PROJECT_ROOT>" --base HEAD --run-id gx-setup-detect --full`로 실행한다 (Bash는 `python3`). 명령은 실행하지 않고 JSON만 출력하며 파일을 쓰지 않는다.
   - 출력 `entries[].project`(`타입:디렉토리`)에 이번 타입이 있으면 `타입 감지 : 확인 ✅ ({타입}:{디렉토리} …)`.
   - exit 1의 `no project types detected`·`configured project root not detected`, 이번 타입이 `entries`에 없음, 그 밖의 config 오류(`cd`·`buildOnly`·test 명령 누락)는 감지 실패다. 원인과 현재 `detect`·`roots`·명령, 그리고 config 수정안(파일명 marker로 바꾸기, 실제 저장소 상대 경로로 고치기, 루트 복합 명령의 `roots: ["."]`, 다른 디렉토리로 가는 `cd` 제거, `buildOnly` 추가 중 해당하는 것)을 보여 주고 `AskUserQuestion`으로 "수정안 적용 (Recommended)"·"그대로 두기 (gx-tdd·gx-verify 검증이 막힘)"를 묻는다. 적용하면 위 config 기록 규칙대로 반영하고 이 확인을 1회 다시 한다. 그대로 두기면 `타입 감지 : 실패 — {원인}`으로 표시하고 진행한다.
   - 커밋이 없어 `HEAD`가 없으면 `타입 감지 : 보류 (커밋 없음)`, svn이면 `타입 감지 : 건너뜀 (SVN — Git 전용 helper)`로 표시한다.
6. **권한 등록 (Claude Code만)**: build/test 명령의 첫 토큰에서 prefix 권한을 도출하고 (예: `make test` → `Bash(make *)`) 확인받는다. **Codex에서는 이 단계에서 `.claude/settings.local.json`을 읽거나 수정하지 않는다.** 대신 Python/Bash/Git 명령의 실제 실행 가능 여부와 `/hooks`에서 사용자가 GX hook을 검토·신뢰했는지 확인한다. 필요한 명령 권한은 현재 Codex 정책에 따라 처리하며 확인되지 않은 상태를 `권한 설정 완료`로 표시하지 않는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "권한 등록",
       question: "등록한 명령을 권한 프롬프트 없이 실행하도록 `.claude/settings.local.json`에 허용을 추가할까요? ({권한 prefix 목록})",
       multiSelect: false,
       options: [
         { label: "추가 (Recommended)", description: "permissions.allow에 병합합니다 (기존 항목 보존)" },
         { label: "건너뛰기", description: "추가하지 않습니다. 파이프라인 실행 중 권한 프롬프트가 발생할 수 있습니다" }
       ]
     }]
   )
   ```
   - "추가" → `.claude/settings.local.json`의 `permissions.allow` 배열에 병합한다. 파일 부재 시 `{"permissions":{"allow":[...]}}`로 생성하고, 기존 항목은 보존하며, 중복은 추가하지 않는다. JSON 파싱 실패 시 갱신하지 않고 수동 설정을 안내한다.
7. **하네스 확인** (등록·유지 경로 공통, 1회 실행):

   등록된 `test` 명령을 실제로 **한 번 실행**한다. config에 명령이 적혀 있다는 것과 그 명령이 도는 것은 별개이고, 이 차이는 온보딩에서 알면 몇 분이지만 파이프라인 후반에 알면 PRD·설계를 되돌려야 한다. 복합 명령이면 `&&`로 이어진 **각 조각을 나눠 실행**해 어느 레이어가 비어 있는지까지 보고한다.

   타임아웃은 config `timeouts.build`를 쓴다. 실행 결과에 따라:

   | 결과 | 출력 | 안내 |
   |---|---|---|
   | 정상 실행, 테스트 1건 이상 | `테스트 하네스 : 확인 ✅ ({N}건)` | 그대로 진행 |
   | 실행되지만 0건 | `테스트 하네스 : 명령은 동작하나 테스트 0건` | 첫 테스트 작성 필요를 안내 (gx-tdd는 이 상태로 진입하지 않는다) |
   | 명령 실행 불가 (러너 미설치·스크립트 부재) | `테스트 하네스 : 실행 실패 — {명령}` | 러너 설치를 안내하고 `docs/test-harness-guide.md`를 가리킨다 |
   | 기존 테스트가 실패 중 | `테스트 하네스 : 확인 ✅ ({N}건, {M}건 실패)` | 실패는 보고만 한다 — 기존 테스트를 고치는 것은 setup의 일이 아니다 |

   복합 명령의 부분 실패는 이렇게 보고한다:
   ```
   테스트 하네스 : 부분 확인
     ./gradlew test           → 7건 ✅
     pnpm --dir frontend test → 실행 실패 (러너 미설치)
   ```

   **이 확인은 정보 제공이며 setup을 중단시키지 않는다.** gx-setup은 문서·조사·분석처럼 테스트 러너가 필요 없는 스킬도 함께 쓰는 공통 설정이므로, 여기서 차단하면 정상적인 사용을 막게 된다. 하네스가 필수인 쪽은 gx-tdd이며, 그 강제는 phase-implement의 하네스 게이트와 gx-verify가 담당한다. 다만 이 단계에서 미리 알려주면 사용자가 파이프라인을 시작하기 전에 결정할 수 있다.

   test 명령이 등록되지 않은 타입(2에서 건너뛰었거나 test 필드가 없는 경우)은 `테스트 하네스 : 건너뜀 (test 명령 미등록)`을 출력한다.
8. `프로젝트 타입 등록 : 완료 ✅ ({타입키})` 출력.
