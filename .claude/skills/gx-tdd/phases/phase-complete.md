# phase-complete: 완료 (verify 게이트 강제)

## Iron Law: verify 게이트 통과 필수

```
NO COMMIT/PR WITHOUT VERIFY GATE PASS
```

관련 문서 반영 후 최종 검증에서 **반드시 `Skill("oh-my-gx:gx-verify")` 호출**한다. 통과 못 하면 commit/PR 진입 차단.

이유:
- phase-review가 통과해도 시간이 지나며 외부 환경 변화(의존성 업데이트, 다른 브랜치 머지 등)로 회귀 가능
- "phase-review에서 통과했으니 OK"라는 산문만으로는 증거가 아니다. 같은 실행·트리·설정·명령·범위·로그를 helper가 확인한 결과만 재사용한다.
- commit 직전 verify는 유효한 증거를 다시 확인하고, 코드나 검증 조건이 달라졌을 때 필요한 명령을 실행한다.
- verify는 공통 영향 계획과 동일 실행의 유효한 증거를 확인한다. 완료 단계라는 이유만으로 전체 스위트를 다시 실행하지 않는다. 명시적 전체 검사·공통 설정/의존성 변경·범위 불명확에서만 전체로 확장한다.

위반 시 즉시 중단하고 verify 게이트부터 재시작.

각 단계가 실패하면 사용자에게 보고하고 진행 여부를 확인한다.

---

모든 진입에서 `Read("../references/document-lifecycle.md")`의 사전 대조와 구현 후 계약을 수행한다. 실행 순서는 **TDD 이행 → 현재 AC/인수 대조 → 관련 문서/상태 투영 → 최종 verify → .dev 계획 완료 → 요청한 commit/PR → 상태 완료**다. Step 번호는 기존 참조 호환을 유지하며 아래 파일 순서대로 실행한다.

## Step -2: TDD 이행 게이트 (모든 진입 경로 공통)

commit/PR로 이어지는 이 Phase의 **모든 진입**(전체 모드, `--phase complete` 단독, 수동 수정 후 재호출)에서 수행한다:

0. **ralph 복귀 (선판정)**: state.md가 `pipeline: gx-ralph`이고 `origin: gx-tdd`이면, 구현 상태는 phases 대신 ac-status.json 원장에 있다. phases.implement 부재만으로 TDD 미이행을 판정하지 않는다. 다만 모든 AC의 passes 표식과 별도로, 같은 run-id의 정상 누적 리뷰 report·`review-run-id`·`review-fingerprint`를 현재 트리와 대조한다. 지문은 [기존 계산 규약](../../gx-verify/references/fingerprint.md)으로 확인하고 트리 성분을 비교한다. 누락·불일치·실패이면 `document-sync-pending: true`를 유지하고 `/gx-tdd --phase review`로 복귀하도록 안내 후 중단한다. 현재 리뷰 증거가 유효하면 재실행하지 않고 Step 0으로 진행한다. 현재 AC 실행 증거·관련 문서 대조·최종 verify는 생략하지 않는다.
1. 그 외에는 state.md를 확인한다. 다음 중 하나면 **TDD 미이행 가능성**으로 판정한다:
   - `pipeline: gx-tdd` 필드가 없다 (gx-dev 이력이거나 알 수 없는 state — phases 기록을 신뢰할 수 없다)
   - `phases.implement`가 `completed`가 아니다
   - 핵심 모드(`mode: core` 또는 `flags`의 `--core` 포함)가 **아닌데** `phases.review`가 `completed`가 아니다 (core는 review를 설계상 스킵하므로 review 부재가 정상이다)
2. TDD 미이행 가능성이면 AskUserQuestion으로 위험 수용을 확인한다. 수용 시 `${DEV_DIR}/trust-ledger.md`에 "TDD 미이행 완료 실행" 항목을 기록한 후 진행하고, 거부 시 중단하며 `/gx-tdd`(전체 모드)를 안내한다.
3. 전체 모드의 정상 순서 진입(직전 review 완료)에서는 조건이 모두 충족되므로 이 게이트는 확인만 하고 지나간다.

## Step 0: 인수 검증 (ProductOwner / 핵심 모드는 AC 자가 검증)

먼저 [문서 수명주기](../references/document-lifecycle.md)의 현재 AC 증거 대조를 수행한다. RGR 테스트의 실제 실행·로그·해시가 현재 구현을 뒷받침해야 한다. 근거가 없거나 변경으로 오래된 AC는 관련 focused 명령을 직접 실행한다. 산문/예전 PASS로 인수하지 않는다. Ralph 복귀는 ac-status.json의 passes 표식만 믿지 않고 각 AC의 실제 실행 근거까지 대조한다. 위험 수용·제외·미검증 AC는 충족 목록에 넣지 않는다. 인수 결과와 남은 AC를 .dev에 기록한다.

**diff 갱신** (모드 무관 공통): phase-review 이후 코드 수정이 있었을 수 있으므로 diff를 갱신한다.
- **git**: `git add -A`로 스테이징한 후 **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트.
- **svn**: `svn diff > ${DIFF_FILE}`로 갱신.

**핵심 모드이면** product-owner를 디스패치하지 않고 오케스트레이터가 **AC 자가 검증**을 직접 수행한다 (현재 RGR/AC의 실제 실행 증거를 위에서 대조했으며 최종 verify는 문서 반영 후 수행한다):
1. `${DEV_DIR}/ac.md`(레거시 재개로 ac.md가 없으면 prd.md)의 G-W-T AC와 RGR 사이클 결과(각 AC의 테스트 통과)·DIFF_FILE을 대조한다.
2. AC별 충족 체크리스트를 사용자에게 표시한다 (예: `AC-1 ✅ (shouldReject401 통과) / AC-2 ⚠️ — 사유`).
3. 모두 충족 → Step 3 진행. 미충족이 있으면 AskUserQuestion으로 확인한다:
   ```
   AskUserQuestion(
     questions: [{
       header: "AC 자가 검증",
       question: "AC 자가 검증에서 미충족 항목이 있습니다. 어떻게 진행할까요?",
       multiSelect: false,
       options: [
         { label: "RGR 수정", description: "미충족 AC를 새 태스크로 phase-implement RGR 사이클을 재실행합니다" },
         { label: "건너뛰기", description: "위험 수용으로 진행합니다 (trust-ledger에 기록)" }
       ]
     }]
   )
   ```
   - "RGR 수정" → phase-implement 복귀 (coder 직접 호출 금지 — Iron Law 1).
   - "건너뛰기" → 위험 수용을 trust-ledger에 기록하고 미충족 목록을 유지한 채 Step 3으로 진행한다. 해당 AC/FR·원래 W행을 완료로 표시하지 않는다.

**전체 모드**는 아래를 따른다. PRD가 없으면 ac.md 또는 Ralph의 승인된 AC 원문으로 대조한다. 원문/실행 증거를 복원할 수 없으면 인수 미확인으로 기록하고 AC/FR·W행·실행 완료 표시는 보류한다.

PRD가 있으면 (`${DEV_DIR}/prd.md`), product-owner에게 인수 검증을 요청한다.

`Task(subagent_type="oh-my-gx:product-owner")` — prompt에 다음을 포함:
- PRD의 "요구사항" + "수용 기준" (Context Slicing 규칙 참조)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- "인수 검증"으로 동작할 것

**결과를 사용자에게 요약만 보고한다** (Agent 전문 출력 금지):
- **ACCEPT**: "인수 검증 통과. 모든 [Must] 수용 기준 충족." Step 3으로 진행.
- **REJECT**: "인수 검증 미통과. [Must] 미충족 N건:" + 미충족 항목 목록만 표시. 수정 여부를 확인한다.
  - **RGR 수정 선택** → phase-implement로 복귀하여 미충족 AC를 새 태스크로 RGR 사이클 실행. (coder 직접 호출 금지 — Iron Law 1)
  - 수동 수정 선택 → 사용자가 직접 수정 후 phase-complete 재호출 (execution-log에 "수동 수정 재주입" 기록)
  - 건너뛰기 선택 → 다음 단계 진행 (위험 수용. trust-ledger에 기록)

PRD 부재만으로 인수 통과를 만들지 않는다. 복원한 AC와 실제 실행 증거의 대조 결과가 없으면 미확인으로 남긴다.

## Step 3: 도메인 status.md 갱신 후보 투영

`DOMAIN_CONTEXT`가 비어 있어도 사전 대조의 requirements/work 포인터에서 관련 원장을 찾는다. `--phase complete`·core·Ralph 복귀·SVN도 이번 범위만 동일하게 확인한다. 문서 금지이면 차이만 보고한다.

1. Step 0에서 실제 테스트와 인수 대조를 통과한 AC만 사용한다. 위험 수용·제외·미충족·미검증 AC는 완료 후보가 아니다.
2. `FR-N (status.md 미반영)` 인용 및 승인된 domain+FR/AC 연결로 원래 행을 찾는다. 해당 FR의 이번 범위 모든 AC가 충족될 때만 `⬜ → ✅`를 최종 검증 후보로 투영한다. 부분 통과 FR, AC가 `-`이고 명시 연결도 없는 행은 바꾸지 않는다.
3. [문서 수명주기](../references/document-lifecycle.md)의 journal에 원문 값·전후 해시·이번 실행의 새 ✅와 근거를 보존한 뒤 Edit한다. 기존 ✅·PR 링크·폐기 항목은 유지한다. 완료 FR의 버그 수정은 별도 W/태스크로 추적한다.
4. 새 PR은 아직 없으므로 PR 열을 미리 채우지 않는다. 결과와 미충족 항목을 보고하고 Step 4로 진행한다. 이 투영은 최종 verify 또는 merged 표식이 아니다.

## Step 4: 관련 문서 구현 후 대조

[문서 수명주기](../references/document-lifecycle.md)의 구현 후 대조를 수행한다. 기존 계획·사용자 goal·실제 변경과 관련 README/원장/정책/인터페이스/아키텍처/W계획을 항상 대조하되, 필요한 차이만 Edit한다. `DOMAIN_CONTEXT` 유무나 도메인 레포 매칭만으로 생략하지 않는다. 전체 context 생성·인터뷰·스캔을 시작하지 않는다.

**임의 반영 금지**: 기존 승인·위임 source가 유효한 관련 차이는 같은 승인을 다시 묻지 않는다. 새 의미·범위·위험 또는 아직 받지 않은 저장 승인이 필요한 경우 그 차이만 확인한다. 문서 금지·read-only는 실제 파일을 수정하지 않고 차이/예외를 기록한다. 코드 관측에서 미래 요구사항을 발명하거나 요구사항을 구현에 맞춰 조용히 바꾸지 않는다.

같은 run-id/plan/branch와 보존한 사전 inspect 보고서로 `development.py inspect --phase post --previous <document-pre.json>`을 실행한다. 전체 결과는 파일에 받고 bounded summary만 읽는다. 관련 실제 문서 반영과 구조/의미 대조가 끝나야 Step -1의 최종 영향 계획·proof·fingerprint를 만들 수 있다. 변경 없음도 확인 근거를 .dev 보고서에 남긴다. 충돌·미응답이면 새 ✅를 조건부 원복하고 여기서 대기한다.

`stop-at: verify`는 로컬 문서/검증까지다. 문서 변경만을 이유로 commit·push하지 않는다. 이어서 Step -1로 진행한다.

## Step -1: verify 게이트 (commit/PR 진입 전 필수)

관련 문서 반영을 완료한 현재 트리에서 `Skill("oh-my-gx:gx-verify")`를 호출한다. 최종 영향 계획과 proof를 현재 run-id·문서 포함 지문으로 새로 생성/확인한다. 이전 proof의 지문을 임의로 갱신하거나 context/를 지문에서 제외하지 않는다.

verify 실행 중에는 다른 테스트·빌드 명령을 시작하지 않고 테스트를 실행하는 서브에이전트도 디스패치하지 않는다 — 같은 빌드 데몬·DB·CPU를 나눠 쓰면 시간 제한 테스트가 오탐하고 테스트 프로세스가 메모리 부족으로 죽는다.

verify 게이트는 테스트 0 failures·빌드 성공에 더해, phase-implement Step 0.5(기준선 게이트)가 기록한 `warnings-baseline` 대비 **신규 경고**도 차단한다 (기존 경고는 허용 — 기준선이 RGR 시작 전이므로 이번 구현이 유입한 경고부터 잡힌다). verify가 "위험 수용"으로 통과를 보고하면(신규 경고·검증 명령 미감지 등) **오케스트레이터가 그 내용을 `${DEV_DIR}/trust-ledger.md`에 기록**한다 (gx-verify는 Write 권한이 없다).

**verify 결과 처리**:

- **✅ verify 통과** → state.md 최상위 `verify-status: passed`와 **verify가 보고한 `verify-fingerprint` 값을 함께 갱신**한다 (둘이 커밋/PR 게이트 해제 키다 — 지문이 없으면 통과 후 코드를 고쳐도 게이트가 열리지 않는다). 이후 Step 3.5 (작업 계획 완료)로 진행. 코드 또는 context/ 문서 변경이 발생해 재진입하면 `verify-status: pending`·`verify-fingerprint: ""`로 리셋하고 Step 0의 현재 AC 대조·관련 문서 반영 후 Step -1을 재실행한다. **verify가 지문을 보고하지 않았으면**(svn 등) 지문 없이 `passed`만 기록하고, 게이트는 구 세션과 동일하게 동작함을 인지한다
- **❌ verify 차단**:
  - 먼저 [문서 수명주기](../references/document-lifecycle.md)의 journal로 이번 실행이 만든 새 ✅만 조건부 원복한다. 동시 변경이면 덮어쓰지 않고 중단한다. W행/실행은 진행 상태로 유지하고 verify는 pending·빈 지문으로 둔다.
  1. verify가 실패 테스트·빌드·신규 경고 항목을 보고함
  2. 사용자에게 표시 후 AskUserQuestion:
     - "수정" → 아래 **verify 회귀 수리**를 수행한다
     - "수동 수정" → 사용자 수정 후 phase-complete 재호출 (execution-log에 "수동 수정 재주입" 기록. 재호출 시 Step 0의 현재 AC·문서 대조 후 최종 verify 재실행)
     - "중단" → 조건부 원복 후 state.md에 `status: cancelled` 기록
  3. 자동 수정은 시도하지 않음 (사용자가 "수정"을 고른 경우에만 수리한다. coder 직접 호출 금지)

**verify 회귀 수리** ("수정" 선택 시):

1. state.md를 `verify-status: pending`·`verify-fingerprint: ""`로 두고 `current-step`을 `"verify 회귀 수리"`로 갱신한다 (이전 통과 기록이 남아 커밋 게이트가 열리는 것을 막는다).
2. 차단 사유를 분류해 처리한다. **verify 회귀 수리에서는 테스트 파일은 수정하지 않는다** — 수리 diff는 다시 리뷰하지 않으므로, 테스트를 바꾸는 수리를 이 경로에 두면 실제 회귀가 테스트 수정으로 덮여 리뷰 없이 커밋될 수 있다.

   | 차단 사유 | 처리 | 새 RED |
   |---|---|---|
   | 기존 테스트 실패 (프로덕션 코드가 기대를 깨뜨림) | implementer **수리 모드** — 깨진 테스트 + 에러 전문 + 깨진 대상으로 조립한 focused 검증 명령. 프로덕션 코드로만 해결하고 수리 뒤 테스트 파일 무변경을 확인한다 | 불필요 (깨진 테스트가 RED) |
   | 빌드 실패 — 프로덕션 소스 | implementer 수리 모드 | 불필요 |
   | 신규 경고 — 동작 불변으로 정리 가능 | 정리 모드 — 세션 직접(`--isolated`면 implementer 정리 모드), phase-implement 세션 IMPLEMENT 절차의 REFACTOR 규칙·수행 불가능한 정리 목록을 따른다 | 불필요 |
   | 신규 경고 — 고치려면 동작이 바뀜 | 실패 항목을 새 AC로 정의해 phase-implement로 복귀 (RGR) | 필요 |
   | 테스트를 고쳐야만 해결됨 (테스트 기대가 틀렸다고 의심되거나 테스트 소스가 컴파일되지 않음) | 수리하지 않는다. 근거(실패 단언·관련 AC)를 보여 주고 "수동 수정"·"중단"으로 안내한다 | — |

3. 처리 뒤 Step 0의 현재 AC/인수 대조와 Step 3·4의 문서 반영을 다시 수행한 다음 Step -1(verify)을 실행한다. 구현 수리 전 완료 투영을 복원하지 않고 옛 proof를 재사용하지 않는다.
4. **수리 라운드 상한 2회**: 이번 phase-complete 진입 이후 execution-log의 `verify 회귀 수리 R{n}` 항목 수로 센다. 2회 수행한 뒤에도 차단되면 "수정" 선택지를 빼고 "수동 수정"·"중단"만 묻는다. RGR로 phase-implement에 복귀했다가 다시 들어오면 새로 센다.
5. 수리 diff는 다시 리뷰하지 않는다. execution-log에 `{ phase: complete, gate: "verify 회귀 수리 R{n}", result: "{분류} — {대상} — {결과}" }`를 남긴다.
6. `--resume`이 `"verify 회귀 수리"`에서 재개되면 Step 0의 현재 AC/문서 대조 후 최종 Step -1을 실행한다 (state는 1에서 이미 pending이다).

**Iron Law 위반 감지**: verify 통과 없이 Step 3.5 또는 commit/PR을 진입하려는 시도가 감지되면 즉시 중단.

`current-step`을 `"verify 게이트"`로 갱신.

---

최종 verify 뒤에는 context/·원장·기타 지문 대상 문서를 쓰지 않는다. 새 PR URL은 `${DEV_DIR}/delivery.md`에만 남기고 후속 명시적 sync에서 반영한다. 요청받은 추가 문서 변경은 다시 문서 대조·최종 verify를 거친다.

## Step 3.5: 작업 계획(plan.md) 갱신

**Step 3과 독립적으로 판정한다.** `DOMAIN_CONTEXT`·PRD의 존재가 아니라 사전/사후 대조의 W행·현재 AC/인수 증거와 최종 verify를 사용한다. `.dev/plan.md`가 없으면 새로 만들지 않는다. 문서 금지이면 기존 행의 Edit/완료 표시도 하지 않고 차이만 보고한다.

1. `work-id`가 있으면 그 ID, 없으면 확인된 현재 branch/slug와 승인된 범위로 행을 찾는다. 명시한 ID가 없거나 여러 행이 맞으면 repair-required로 보고하며 임의 행을 완료 처리하지 않는다.
2. 최상위 `verify-status: passed`와 현재 트리의 일치 지문, 관련 문서 대조 완료, 해당 W행의 **모든 AC**의 실제 테스트·인수 충족을 확인한다. 미충족·미검증·위험 수용·제외 AC가 있으면 원래 W행은 `진행`으로 유지하고 남은 범위를 보고한다. 기존 FR의 ✅만으로 새 버그 수정 W행을 완료 처리하지 않는다.
3. 위 조건이 충족된 행만 `완료`로 바꾼다. `폐기`이면 바꾸지 않고 "폐기된 작업이 완료 처리 대상입니다 — 계획을 확인하세요"를 경고한다. 완료는 검증된 작업 범위이며 병합/배포 완료가 아니다.
4. **전용 반영**은 [실행 종료점 계약](../references/execution-boundaries.md)을 따른다. verify는 로컬 갱신만, commit/pr는 다음 Step 1의 허용된 커밋에 함께 포함한다. 이미 포함된 변경에 `docs: [plan] {ID} 완료` 전용 커밋을 중복 생성하지 않는다. 원격 반영은 pr 또는 별도 명시적 요청에서만 현재 작업 브랜치로 수행하고 베이스 브랜치로 보내지 않는다. svn이면 로컬 갱신·미공유 상태를 알린다.

**status.md는 건드리지 않는다.** 최종 verify 후 바꿀 수 있는 것은 `.dev` 진행/전달 기록뿐이다. 필요한 context 수정이 생기면 Step 0·3·4를 거쳐 새 최종 검증을 한다.

**되돌림은 여기서 하지 않는다.** 완료한 작업에 재진입할 때의 `완료 → 진행`은 phase-setup Step 7에서 처리한다. 최종 verify 실패 시 새 ✅의 조건부 원복은 Step -1이 즉시 처리한다.

## Step 1: Commit

`stop-at: verify`이면 이 Step을 실행하지 않고 Step 5로 이동한다. 종료점이 없는 구 세션은 기존 사용자 요청에서 복원하며, 요청 없는 커밋을 기본값으로 삼지 않는다.

**svn인 경우** → `gx-commit` 스킬은 git 전용이므로 건너뛴다. "SVN 프로젝트입니다. verify 게이트 통과를 확인하고, `svn add --force .`로 신규 파일(.dev 산출물 포함)이 등록되었는지 확인한 뒤 `svn commit`을 직접 실행해주세요." 출력 후 Step 5로 진행한다.

**git인 경우:**
`Skill("oh-my-gx:gx-commit")`을 호출하여 커밋한다 (Step -1 verify 게이트 통과 후 → commit).

> 주의: `oh-my-gx:gx-commit`은 독립적으로도 사용하는 스킬로 verify 실행(테스트 실행 증거 수집)을 포함하지 않는다 (`verify-status` 기반 조건부 경고 게이트만 있다).
> verify 책임은 전적으로 Step -1(`oh-my-gx:gx-verify`)에 있다. Step -1 이후 코드 변경이 발생했다면 commit 전에 Step 0·3·4에서 문서를 다시 대조/반영한 뒤 Step -1의 최종 영향 계획을 생성하고 유효한 동일 증거만 재사용한다.

**build/test 실패 시**: Step -1 verify 게이트의 차단 처리 분기를 그대로 따른다 (동일 절차의 이중 서술을 피하기 위해 **Step -1이 단일 기준**이다). `coder`(deprecated) 직접 호출 금지 — 수정은 RGR 사이클로만 한다.

## Step 2: PR 생성

`stop-at: pr`인 경우에만 실행한다. `commit`·`verify`이면 Step 5로 이동한다. PR 생성·push의 실제 권한은 이번 요청 또는 보존한 결정 기록에 있어야 한다.

**svn인 경우** → 건너뛴다 (Step 1에서 이미 건너뜀. SVN은 PR 개념이 없다).

**git인 경우:**
`Skill("oh-my-gx:gx-pull-request")`를 호출하여 PR을 생성한다. pull-request은 독립 스킬이므로 dev 컨텍스트를 알지 못하며, **dev 산출물을 자동 감지하지도 않는다**. 오케스트레이터가 **스킬 호출 전에** `${DEV_DIR}/pr-context.md`를 조립하고 `--background` 인자로 명시 전달한다.

### Step 2-1: `${DEV_DIR}/pr-context.md`·`pr-rulings.md` 조립 (Skill 호출 전)

오케스트레이터가 아래 1·2를 `${DEV_DIR}/pr-context.md`에, 3을 `${DEV_DIR}/pr-rulings.md`에 Write한다:

1. **비즈니스 맥락**: PRD의 "배경"과 "요구사항", 설계서의 "배경 및 목적". 핵심 모드이면 ac.md의 "배경"과 "요구사항 (AC)"를 사용 (레거시 재개로 ac.md가 없으면 prd.md, 그것도 없으면 ARGS[0]).
2. **Trust Ledger 요약**: `${DEV_DIR}/trust-ledger.md`가 존재하면 Read하여 아래 형식으로 포함한다:
   ```
   ## Audit Summary
   - 총 N건 (CRITICAL: n, HIGH: n, MEDIUM: n)
   - [주요 발견 항목 1줄 요약] (최대 5건)
   ```
   Trust Ledger가 없으면 이 섹션을 생략한다.

   **핵심 모드 긴급 감사 병기**: Trust Ledger에 `### 핵심 모드 긴급 감사` 섹션이 포함되어 있으면, `## Audit Summary` 블록 끝에 `- 핵심 모드 긴급 감사: CRITICAL n건, HIGH n건 (자세한 내용은 Trust Ledger 참조)` 한 줄을 추가한다. 전체·핵심 모드 모두 동일한 Audit Summary 포맷을 사용하여 PR 본문의 일관성을 유지한다.

3. **Rulings·Deferred**: `${DEV_DIR}/decisions.md`에 `· Ruling: ` 블록이 하나라도 있거나 `${DEV_DIR}/reports/review-deferred.md`가 있으면 `${DEV_DIR}/pr-rulings.md`를 Write한다. 둘 다 없으면 만들지 않는다.
   ```
   ## Rulings
   - {Ruling 블록 제목} — {**판정.** 줄 요약} (틀리면: {**틀리면.** 줄 요약})

   ## Deferred
   - [Minor] {파일:라인} — {요약}
   - [MEDIUM] {파일:라인} — {요약}
   ```
   Rulings는 decisions.md의 블록 순서대로 전부 나열한다 — 사용자가 되돌릴 판정을 고르는 목록이므로 요약으로 줄이지 않는다.

### Step 2-2: `Skill("oh-my-gx:gx-pull-request")` 호출

`${DEV_DIR}/pr-context.md` 조립이 완료된 후 **args로 파일을 명시 전달**하여 호출한다:

`Skill(skill: "oh-my-gx:gx-pull-request", args: "--background ${DEV_DIR}/pr-context.md --extra-section ${DEV_DIR}/pr-rulings.md")` — `pr-rulings.md`를 만들지 않았으면 `--extra-section` 인자를 뺀다.

pull-request 스킬은 `--background`로 받은 파일만 PR 본문(Background + Audit Summary)에 반영한다 — 자동 감지는 없다 (gx-dev phase-complete와 동일한 명시 전달 방식). `--extra-section`의 `## Rulings`·`## Deferred`는 요약 없이 같은 제목으로 실린다.

### Step 2-3: 후속 처리

- pull-request 스킬이 전제조건 미충족(gh 미설치, remote 미설정 등)으로 종료하면, 오케스트레이터는 후속 안내를 추가한다: "나중에 `/oh-my-gx:gx-pull-request`로 PR을 생성할 수 있습니다."
- **PR 생성 후 알림**: pull-request 스킬이 알림까지 처리한다. 스킬 종료 후 알림이 누락된 정황이 있으면 (PR URL은 있으나 알림 미전송) 오케스트레이터가 알림 전송을 직접 수행한다.

새 PR URL과 전달 결과는 `${DEV_DIR}/delivery.md`에만 기록한다. context/status.md의 PR 열은 여기서 수정하지 않는다. PR 생성은 pr-open이며 실제 merged 근거 없이 병합 완료로 표시하지 않는다.

## Step 5: 진행 상태 완료
현재 트리의 최종 verify·관련 문서 대조·요청 범위 모든 AC/인수 충족·요청한 종료점의 성공을 확인한 뒤에만 `${DEV_DIR}/state.md`의 `status`와 `phases.complete`를 `completed`, `document-sync-pending`을 false로 갱신한다. pending 질문·미충족/미검증 AC·commit/PR 실패가 남으면 진행 상태를 유지하고 남은 조건을 보고한다. 구현 완료와 검증 완료를 구분하며, completed는 merged 표식이 아니다. 코드·context 변경이 뒤따르면 pending·빈 지문으로 되돌리고 문서 대조부터 다시 수행한다.

## Step 5.5: 구현 구조 시각화 제안

**헤드리스 판정 먼저**: ARGS에 `--non-interactive`가 있거나 `${DEV_DIR}/ralph.lock`이 존재하면 이 절 전체를 **strict no-op**으로 건너뛴다. 질문하지 않고 기존 완료 출력을 바꾸지 않는다 — 응답할 사용자가 없다. (gx-ralph 루프는 완료 처리를 gx-ralph-iterate Step 5.5에서 직접 수행하고 phase-complete를 거치지 않으므로, 이 판정은 현재 도달하지 않는 향후 진입 경로를 위한 예약이다.)

대화형 세션이면 아래를 질문한다. 구조화된 질문 도구가 없는 세션에서는 같은 선택지를 **자연어로 묻고 실제 답을 기다린다** — 도구가 없다는 이유로 건너뛰지 않는다. "질문 도구가 없음"과 "응답할 사용자가 없음"은 다른 조건이다: 앞의 것은 묻는 방식만 바뀌고, 뒤의 것만 strict no-op이다.

```
AskUserQuestion(
  questions: [{
    header: "구조 시각화",
    question: "이번 사이클에서 구현된 구조를 아키텍처 맵에 표시할까요?",
    multiSelect: false,
    options: [
      { label: "아키텍처 맵 갱신", description: "프로젝트 전체를 다시 스캔해 .dev/architecture/를 갱신하고, 이번 사이클에서 새로 생기거나 바뀐 구조를 신규·변경으로 표시합니다" },
      { label: "아니요", description: "시각화하지 않고 완료합니다" }
    ]
  }]
)
```

- **아키텍처 맵 갱신** → 프로젝트 전체를 다시 스캔하므로 저장소 규모에 따라 시간이 걸릴 수 있음을 먼저 알린 뒤, `oh-my-gx:gx-visualize`를 `service --project-root ${PROJECT_ROOT} --changed-since ${BASE_BRANCH}`로 호출한다. 선택이 곧 동의이므로 다시 묻지 않는다. **svn이면** `--changed-since`를 넘기지 않는다 — 변경 표시는 git 기준 시점이 필요하다. 이때는 맵을 변경 표시 없이 갱신했다고 함께 보고한다.
- **아니요** → 건너뛴다.

호출 결과의 `index_path`·`validation_status`, 도메인별 `backend`·`capability`·`validation_status`, `changes`(신규·변경·삭제 수 또는 생략 이유)를 그대로 보고한다. `validation_status`가 `failed`이거나 `index_path`가 없으면 `visualization_status: failed`로 보고한다. 실패 시에도 존재하는 인덱스는 진단 화면으로 안내하며 경로를 성공처럼 제시하지 않는다. `last_good`는 이전 정상 결과라는 시점과 함께 구분한다.

이 절의 실패·누락·fallback은 **커밋·PR 단계를 중단하거나 실패로 바꾸지 않는다.** Step 1~2가 이미 실패했다면 시각화 성공으로 그 실패를 덮지 않는다.

## Step 6: 다음 단계

PR이 생성되었으면 완료이다. **PR 머지는 절대 실행하지 않는다** — 머지는 리뷰어가 직접 수행한다.

리뷰 수정 요청에 대비하여 작업환경 유지를 안내한다:
"리뷰 피드백 대응을 위해 현재 브랜치를 유지합니다. 리뷰 완료 후 베이스 브랜치로 전환하세요."
