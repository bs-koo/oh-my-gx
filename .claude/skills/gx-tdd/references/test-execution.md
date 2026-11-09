# 테스트 선택과 실행 증거

review Mechanical Gate, 완료 verify, commit 빌드 확인이 같은 계약을 사용한다. 태스크의 RED 실패 확인과 구현 직후 focused 직접 확인은 유지한다. 이 문서는 그 이후 경계에서 같은 전체 스위트를 반복하는 일을 줄인다.

## RED·IMPLEMENT의 현재 태스크 명령

태스크 내부 검증은 바깥 review/verify의 영향 계획과 별개다. **현재 태스크의 실제 테스트 파일만** 저장소 상대경로 배열로 저장하고 다음 helper를 사용한다. 과거 태스크 목록을 누적하거나 매 RED/IMPLEMENT마다 전체 `npm test`로 대신하지 않는다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-plan.py" focused \
  --cwd "$PROJECT_ROOT" --project "node:web" \
  --tests-file "$PROJECT_ROOT/$DEV_DIR/current-task-tests.json"
```

`--project`는 config의 타입과 프로젝트 상대 루트를 이은 `TYPE:RELROOT`다. 루트 프로젝트는 `node:.`처럼 쓴다. `--config <path>`로 명시한 설정을 사용할 수도 있다. 프로젝트 marker·등록 root·비어 있지 않은 실제 파일 목록·소유 프로젝트 범위·symlink 범위탈출을 검사한다. 이 명령은 Git 저장소나 지문을 요구하지 않으며 테스트·빌드·proof 기록을 실행하지 않는다. SVN의 태스크 focused 조립에도 사용할 수 있다.

- **exit 0**: `{supported:true, project, cwd, command, scope, runner}` JSON이다. `cwd`에서 `command`를 직접 실행한다. 경로 인용은 Git Bash/POSIX shell 기준이며 JSON을 `eval`하지 않는다. `scope`는 프로젝트 상대 현재 태스크 테스트 경로다.
- **exit 2**: `{supported:false, requires:"focusedTest", reason, ...}`다. custom/미지원 runner 또는 잘못된 template이며 전체 명령으로 조용히 폴백하지 않는다. 명시적 `focusedTest`를 설정하거나 올바른 현재 파일 실행 명령을 확정한다. 헤드리스는 설정 부족으로 차단한다.
- **exit 1**: 프로젝트·경로·파일 목록 오류다. 누락된 파일이나 다른 프로젝트 테스트를 무시하지 말고 정정한다.

명시 `focusedTest`가 최우선이다. `{files}`는 검증한 경로 목록, Java/Kotlin의 `--tests {pattern}`은 현재 테스트 class 목록으로 조립한다. 설정이 없을 때는 다음의 정확한 실행 형태만 추론한다:

| 등록된 test와 실제 script | 현재 파일 실행 |
|---|---|
| `npm test`, package script `vitest` | `npm test -- --run <files>` |
| `npm test`, package script `vitest run` | `npm test -- <files>` |
| `npm test`, package script `jest` | `npm test -- --runInBand --runTestsByPath <files>` |
| `npm test`, package script `node --test` | `npm test -- <files>` |
| 정확한 `pytest`·`python -m pytest`·`python3 -m pytest` | 등록 명령 뒤에 `<files>` |

wrapper·watch·복합 script나 추가 runner 플래그의 의미를 추측하지 않는다. 이 경우 `{files}`가 있는 명시 `focusedTest`가 필요하다. helper가 반환한 파일 명령의 실제 assertion 실패와 실행 수를 RED/IMPLEMENT 게이트가 직접 확인하며, 명령 오류·수집 실패를 RED로 인정하지 않는다. 바깥 경계의 미매핑 전체 폴백 규칙은 아래 계획 생성 절차가 맡는다.

## 계획 생성

설치 플러그인 루트의 `scripts/gx-test-plan.py`를 Python 3.10+로 실행한다. 루트는 이 문서 기준 `../../../..`이며 `.codex-plugin/plugin.json`과 helper 존재를 확인한다. helper는 명령을 실행하지 않고 JSON만 출력한다. 소비 프로젝트 루트와 설치 루트를 혼동하지 않는다.

**태스크 선택 선행**: review를 거치지 않은 단독 verify·complete도 state/report에 `baseline-generation`, `active-case-ids`, `previous-task-ids`, `supersedes`, `case-change-report`, `retired-case-ids` 중 하나라도 있으면 이 파일 기준 [core-replanning.md §5 활성 태스크 선택 정본](core-replanning.md)을 조건부로 Read하여 **`ACTIVE_TASKS`**를 복원한다. 승인된 현재 계획·active 케이스·세대/승계·불변 이력으로 복원한 같은 집합을 아래 해시·필수 테스트·소유권 입력 모두에 사용한다. 리뷰의 `REVIEW_ACTIVE_TASKS`도 이 집합의 별칭이며 다른 집합으로 재선택하지 않는다. 세대 메타데이터가 전혀 없는 legacy는 `ACTIVE_TASKS`를 기존 태스크 전체로 두고, state/태스크 없는 단독 verify는 빈 집합으로 두어 같은 정본의 기존 실제 변경 기반 선택·보수적 폴백을 유지한다.

일부 세대 필드만 있거나 active 태스크/파일 매핑이 모호하면 정본대로 복원 전 게이트를 차단한다. 새 hash로 통과시키거나 과거 hash를 현재 파일과 대조·덮어쓰기는 금지한다. 전체 폴백으로 소유권·무결성 오류를 우회하는 것도 금지한다. 승인된 전체 범위 종료인 `scope-closed`는 여기서 중단하고 일반 검증 완료·complete·자동 commit/PR로 넘기지 않는다. 단순 빈 목록과 기록 부재를 범위 종료로 간주하지 않는다.

1. `run-id`는 파이프라인의 실행 ID다. 새 작업은 새 ID를 만들고 state에 보존한다. 재개는 원래 ID를 복원한다. 같은 실행의 review→verify→commit만 ID를 공유한다. 단독 verify도 새 ID를 만든다.
2. `base`는 작업 시작 시 확정한 기준 ref다. helper가 `base...HEAD`, staged/unstaged 변경, untracked 파일을 합친다. 작업이 커밋되어도 브랜치 변경이 사라지지 않는다. `.dev/` 산출물은 제외한다.
3. `ACTIVE_TASKS`의 현재 소유 파일만 RED 산출물의 `test-file-hash`와 먼저 대조한 뒤, 이 집합의 `test-file`을 중복 제거해 `${DEV_DIR}/required-tests.json`(저장소 상대경로 배열)에 저장한다. retired/superseded 태스크의 과거 hash·삭제된 파일 경로는 재수집하지 않는다. 현재 active 파일의 부재·무단 변경은 검증 실패이며 새 hash 기록이나 전체 폴백으로 숨기지 않는다.
4. 같은 `ACTIVE_TASKS`에 속하고 현재 승인된 plan으로 확인한 태스크 소유 source 파일과 실제 test 파일 관계만 `${DEV_DIR}/test-ownership.json` 배열로 만든다: `[{"sources":["src/Login.java"],"tests":["src/test/LoginTest.java"]}]`. retired/superseded의 과거 관계나 근거 없는 묶음을 추가하지 않는다. 활성 태스크·파일 소유권을 먼저 확정한 뒤 source→test 영향 관계만 불명확하면 기존처럼 해당 관계를 생략해 전체 폴백한다. 소유권 자체가 모호한 상태는 앞의 복구 차단 분기다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-plan.py" plan \
  --cwd "$PROJECT_ROOT" --base "$BASE_REF" --run-id "$RUN_ID" \
  --tests-file "$PROJECT_ROOT/$DEV_DIR/required-tests.json" \
  --ownership-file "$PROJECT_ROOT/$DEV_DIR/test-ownership.json" \
  > "$PROJECT_ROOT/$DEV_DIR/test-plan.json"
```

helper 실패·JSON 미확보·명령 미감지는 게이트 차단이다. 오래된 계획으로 대신하지 않는다. 각 entry의 `cwd`는 프로젝트 루트에 대한 상대 디렉토리다. 각 entry의 `command`를 그 디렉토리에서 순차 실행한다. JSON을 셸의 `eval`에 넘기지 않는다. `{files}`는 POSIX `shlex` 인용을 쓰므로 Windows에서도 Git Bash로 실행한다. PowerShell이 필요한 프로젝트는 파일 선택 명령을 해당 셸에 맞춰 별도 확정하고 그 정확한 명령으로 계획·증거를 다시 만든다. 임의 문자열 치환으로 인용을 제거하지 않는다.

SVN은 Git 전용 `plan`/`record`/`reuse`·지문을 사용하지 않는다. 위의 `focused`는 Git 없이 사용할 수 있다. `.claude/config.json`에 등록되어 감지된 모든 프로젝트의 `test`와 `buildOnly`를 순차 직접 실행한다. 기존 focused RED/구현 확인은 유지하되 최종 경계는 보수적인 전체 폴백이다. 0건·미확정·실패·신규 경고 게이트를 그대로 적용하고 지문은 해당 없음으로 보고한다. Git helper 실패를 SVN 경로로 오인해 우회하지 않는다.

## 선택 규칙

**SSOT는 config** `projectTypes`다. `detect` marker가 있는 모든 프로젝트 디렉토리를 탐색한다. `roots` 배열이 있으면 그 명시 경로를 모두 감지·검사한다. `.git/`, `.dev/`, 빌드·의존성 디렉토리는 탐색에서 제외한다. 복수 타입·같은 타입의 여러 프로젝트를 한쪽만 선택하지 않는다.

각 타입의 선택 설정:

| 필드 | 의미 |
|---|---|
| `test` | 안전한 전체 폴백 명령 |
| `focusedTest` | `{files}` 또는 Java의 `--tests {pattern}` 템플릿 |
| `affectedTest` | 관련 source/test 경로를 `{files}`에 넣는 runner 명령 |
| `testSelection.mappings` | 프로젝트 상대 `sources` glob 배열 → `tests` 경로 배열 |
| `testSelection.crosscutting` | 항상 전체 회귀가 필요한 공유 코드 glob |
| `testSelection.tests` | 변경된 테스트 파일을 식별하는 glob (미설정 시 일반적인 테스트 이름 사용) |
| `testSelection.ignore` | 실행 영향이 없다는 근거가 있는 경로만 명시적으로 제외 |
| `buildOnly` | 테스트를 실행하지 않는 명시적 빌드 명령 |

- 변경 테스트·태스크 필수 테스트·명시적 매핑 테스트의 합집합을 실행한다. 매핑된 테스트 파일 부재/삭제도 전체 폴백이다.
- 단순 `vitest`/`vitest run`·`jest` npm test script는 source만 선택할 때 runner의 related 모드를 쓴다. 별도 필수 테스트도 있으면 그 실행을 보장하는 명시적 `affectedTest`가 필요하며 없으면 전체 폴백한다. 다른 runner는 `affectedTest` 또는 매핑+`focusedTest`가 필요하다. runner가 파일을 받는다는 추측으로 플래그를 붙이지 않는다.
- 의존성/lock/build 설정, runner config, `crosscutting` 일치, 미매핑 source, focused 미지원은 해당 프로젝트 전체 폴백이다. 소유 프로젝트 밖의 경로·공유 의존성·검증 config 변경은 감지된 모든 프로젝트로 폴백한다. 감지된 프로젝트가 영향 분석 없이 빠지지 않도록 미변경 프로젝트도 보수적으로 전체를 계획한다. 프로젝트가 독립적이라는 근거로 testSelection.independent:true를 명시한 경우에만 영향 없는 프로젝트를 생략한다. 공유 설정·의존성 변경은 이 설정과 무관하게 전체로 확장한다.
- docs-only는 명시적 ignore 정책으로만 테스트를 생략할 수 있다. 플러그인 스킬 Markdown처럼 실행 의미가 있는 문서는 ignore 대상이 아니다. 저장소가 요구하는 구조 검사·린트는 별도 필수 검증으로 유지한다.
- 출력의 `scope`, `reason`, `skipped`를 execution-log에 기록한다. 전체 폴백 사유가 없으면 완료 단계라는 이유만으로 전체 스위트로 확대하지 않는다.
- 사용자가 전체 회귀를 요청하거나 CI가 전체 스위트를 요구하면 `plan --full`을 전달한다. full scope는 `['*']`이며 관련 테스트 scope의 증거로 대신 통과시키지 않는다.

## 실행과 재사용

각 entry는 실행 전에 먼저 `reuse`를 확인한다. proof 파일은 `${DEV_DIR}/evidence/{entry.id}.json`, 로그는 entry별 별도 경로를 사용한다. 재사용을 허용하는 모든 값은 **같은 runId + fingerprint의 트리 성분(HEAD는 추적용) + configHash + 프로젝트 cwd/타입 + command + scope**다. 로그가 존재하고 해시가 같아야 한다. 코드·명령·config·범위·실행 ID가 달라지면 재실행한다. 이전 세션 결과·에이전트 산문 보고·빌드 도구 캐시만으로 통과시키지 않는다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-plan.py" reuse --cwd "$PROJECT_ROOT" \
  --plan "$PLAN" --entry "$ENTRY_ID" --proof "$PROOF"
```

exit 0이면 같은 실행에서 직접 확보한 결과를 읽고 재사용한다. 실패하면 entry 명령을 직접 실행해 로그로 캡처하고 원 명령 exit code·실제 실행 수·실패 수를 확정한 뒤 기록한다:

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-plan.py" record --cwd "$PROJECT_ROOT" \
  --plan "$PLAN" --entry "$ENTRY_ID" --proof "$PROOF" --log "$LOG" \
  --exit-code "$EXIT_CODE" --tests "$TEST_COUNT" --failures "$FAILURE_COUNT"
```

빌드 entry는 `--tests`를 생략한다. 실패, 테스트 0건, 수 미확정(-1), 로그 부재, 지문/config 불일치는 passed 증거를 만들지 않으며 같은 proof의 기존 성공도 무효화한다. record 이전에 파일이 바뀌었으면 새 계획을 만든 뒤 다시 실행한다. 실행 시작 전 지문도 계획과 대조하며 실행 중 코드를 바꾸지 않는다. 실패/수 미확정도 `record`하여 이전 성공이 남지 않도록 한다.

테스트 실패와 명령 오류를 구분한다. related/focused 명령이 runner 미지원으로 실패하면 사유를 남기고 `plan --full`로 새 계획을 확정해 실행한다. 실제 assertion 실패는 범위 폴백으로 숨기지 않고 수리 경로로 보낸다. Gradle `UP-TO-DATE`처럼 캐시만 확인된 실행은 XML의 0이 아닌 실제 실행 수를 확인하고, 이번 실행의 신선한 증거가 아니면 `plan --rerun-tests`로 새 계획을 만든다. 이 옵션은 알려진 Gradle test 명령에만 `--rerun-tasks`를 붙이고 영향 범위는 유지한다. 이후 경계도 그 계획과 옵션을 유지해 실제 명령이 다른 증거를 재사용하지 않는다.

## 빌드와 경고

`buildOnly`를 우선 사용한다. 정확히 `./gradlew build`, `gradlew build`, `gradlew.bat build`인 기본값만 `build -x test testClasses`로 바꿀 수 있다. 이 제외는 기본 `test` task에 대한 것이다. custom integrationTest 등 별도 테스트 task가 연결되어 있으면 모든 테스트 실행을 제외하는 검증된 `buildOnly`를 설정해야 한다. 복합/custom build를 임의로 고치지 않고 설정이 없으면 차단한다. `clean`을 자동으로 추가하지 않는다.

경고 baseline은 동일 command·scope의 로그끼리만 비교한다. 선택 범위가 다른 baseline은 경고 수 합계로 차단하지 않고 신규 경고 원문을 대조한다. `warningPattern` 측정·실패·신규 경고 게이트는 gx-verify가 소유한다. commit은 동일 build 증거를 재사용하고, 불일치면 테스트가 없는 buildOnly만 실행한다. verify-fingerprint와 보호 브랜치 게이트는 그대로 유지한다.
