> gx-setup/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 0.5단계: 프로젝트 타입 등록

`.claude/config.json`의 `projectTypes`를 프로젝트에 맞게 등록한다. **SSOT는 config에 등록된 값**이며, 힌트 카탈로그는 제안용이다.

1. **기존 등록 확인**: config `projectTypes` 중 `detect` 파일이 프로젝트 루트에 존재하는 타입이 있으면 → `프로젝트 타입 등록 : 완료 ✅ ({타입}, 기존 등록 유지)` 출력 후 **7(하네스 확인)으로 진행**한다 (config는 갱신하지 않는다). 등록 내용을 그대로 두더라도 하네스 확인은 수행한다 — 명령이 config에 적혀 있다는 것과 그 명령이 실제로 도는 것은 다른 문제이고, 이 간극이 파이프라인 후반(구현 직전)에야 드러나면 PRD·설계를 다 만든 뒤 되돌아가야 한다.
   **여러 타입의 detect 파일이 동시에 존재하면** 첫 매칭으로 단락하지 않고 아래 3의 다중 감지 분기로 처리한다.
2. **빌드 파일 스캔**: Glob으로 `Makefile`, `CMakeLists.txt`, `project.yml`, `Cargo.toml`, `pom.xml`, `pyproject.toml`, `setup.py`, `requirements.txt`, `go.mod`, `*.csproj`, `*.sln`, `composer.json`, `build.gradle`, `build.gradle.kts`, `package.json`을 탐색한다.
3. **제안 생성**: `Read("project-type-hints.md")`로 힌트 카탈로그를 읽어 감지 파일과 매칭한다.
   - 매칭되면 해당 행의 타입 키·build/test·warningPattern·artifacts를 제안 값으로 사용한다.
   - **여러 행이 매칭되면** 두 가지 상황을 구분한다. 잘못 고르면 한쪽 레이어가 영구히 검증되지 않으므로 사용자에게 물어본다.
     - **부수 감지**: 한쪽이 도구용일 뿐 별도 테스트 대상이 아닌 경우 (예: C 프로젝트의 도구용 `package.json`, 문서 사이트용 `package.json`). → 주 타입 하나를 고른다.
     - **복합 타입**: 양쪽 모두 실제 소스와 테스트를 가진 경우 (예: `build.gradle.kts` + `frontend/package.json`인 풀스택 모노레포). → **한 타입 키에 양쪽을 `&&`로 이은 복합 명령**을 등록한다. 하나만 고르면 나머지 레이어는 verify 게이트가 아예 실행하지 않아 미검증 상태로 통과한다.
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
     복합을 선택하면 각 행의 명령을 `&&`로 잇고 타입 키는 프로젝트를 나타내는 이름으로 제안한다 (예: `fullstack`). 명령 조합 규칙과 주의점은 힌트 카탈로그의 "복합 타입" 절을 따른다.
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
5. **config 기록**: 확정 값을 `projectTypes.{타입키}`에 기록한다 (`detect`/`build`/`test`/`focusedTest`/`warningPattern`/`artifacts`. 빈 제안 값은 필드를 생략한다). Codex에서는 위 helper에 `{"projectTypes":{"{타입키}":{확정한 필드만}}}` 형태의 updates만 전달해 기존 타입의 다른 필드와 사용자 정의 필드를 보존한다. Claude Code는 기존 Edit를 사용한다. `focusedTest`는 선택 필드로, 특정 테스트만 실행하는 명령 템플릿이다 — `{files}`(테스트 파일 경로 공백 구분) 또는 `{pattern}`(클래스 글롭 — 파일명에서 유도) 플레이스홀더를 쓴다. 미등록 시 gx-tdd가 전체 `test` 명령으로 폴백한다.
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
