# phase-complete: 완료

각 단계가 실패하면 사용자에게 보고하고 진행 여부를 확인한다.

## 5.1 인수 검증 (ProductOwner)
PRD가 없으면 이 단계를 건너뛴다.

PRD가 있으면 (`.dev/prd.md`), product-owner에게 인수 검증을 요청한다.

**diff 갱신**: phase-review 이후 coder 수정이 있었을 수 있으므로, `git add -A`로 스테이징한 후 **Diff 수집 규칙**에 따라 diff를 `DIFF_FILE`에 리다이렉트하여 갱신한다.

`Task(subagent_type="product-owner")` — prompt에 다음을 포함:
- PRD의 "요구사항" + "수용 기준" (Context Slicing 규칙 참조)
- 변경사항 diff 파일 경로 (`DIFF_FILE`) + Read 지시
- 코드 맵
- "인수 검증"으로 동작할 것

**결과를 사용자에게 요약만 보고한다** (Agent 전문 출력 금지):
- **ACCEPT**: "인수 검증 통과. 모든 [Must] 수용 기준 충족." 다음 단계 진행.
- **REJECT**: "인수 검증 미통과. [Must] 미충족 N건:" + 미충족 항목 목록만 표시. 수정 여부를 확인한다.
  - 수정 선택 → coder로 수정 후 인수 검증 1회 재실행.
  - 건너뛰기 선택 → 다음 단계 진행.

위 5.1 진입 조건에 의해 PRD 부재 또는 `--hotfix` 모드이면 이 단계 전체가 건너뛰어진다.

## 5.2 Commit
`commit` 스킬을 Read하여 프로세스를 실행한다 (test → commit 일괄).

**test 실패 시 자동 수정 (1회):**
1. commit이 test 실패로 중단하면, 실패 로그와 코드 맵, PROJECT_ROOT를 `Task(subagent_type="coder")`에 전달하여 수정 요청.
2. 수정 완료 후 commit을 재호출한다.
3. 재호출도 실패하면 사용자에게 실패 목록을 보고하고 진행 여부를 확인한다.

## 5.3 PR 생성
`pull-request` 스킬을 Read하여 프로세스를 실행한다. pull-request은 독립 스킬이므로 dev 컨텍스트를 알지 못한다. 오케스트레이터가 PR 본문을 구성할 때 아래 내용을 직접 조립하여 pull-request의 본문 생성 과정에 반영한다:

1. **비즈니스 맥락 조립**: pull-request이 PR 본문을 생성할 때, 오케스트레이터가 다음을 "비즈니스 맥락"으로 함께 전달한다:
   - PRD의 "배경"과 "요구사항", 설계서의 "배경 및 목적". `--hotfix`이면 ARGS[0]을 사용.
   - pull-request의 Background/Requirements 섹션에 이 내용이 반영된다.
2. **Trust Ledger 요약 삽입**: `.dev/trust-ledger.md`가 존재하면 Read하여, pull-request이 생성하는 PR 본문의 Checklist 앞에 `## Audit Summary` 섹션을 추가한다:
   ```
   ## Audit Summary
   - 총 N건 (CRITICAL: n, HIGH: n, MEDIUM: n)
   - [주요 발견 항목 1줄 요약] (최대 5건)
   ```
   Trust Ledger가 없으면 이 섹션을 생략한다.
3. pull-request이 전제조건 미충족(gh 미설치, remote 미설정 등)으로 종료하면, 오케스트레이터는 후속 안내를 추가한다: "나중에 `/pull-request`로 PR을 생성할 수 있습니다."
4. **PR 생성 후 알림**: PR이 성공적으로 생성되었으면, pull-request 스킬의 "PR 생성 후 알림" 섹션을 **반드시 실행**한다. 이 단계는 PR 생성과 분리되어 누락되기 쉬우므로, PR URL을 받은 직후 알림 전송 절차를 즉시 수행할 것. 중단 후 재개 시에도 PR이 생성되었으나 알림이 미전송 상태이면 알림부터 실행한다.

## 5.4 도메인 status.md 갱신

`DOMAIN_CONTEXT`가 있고 (phase-setup에서 도메인 매칭 성공), 5.1 인수 검증이 ACCEPT이면 실행한다. 그 외에는 건너뛴다.

1. 5.1 인수 검증 결과에서 **통과한 AC 목록**을 추출한다 (예: AC-1, AC-4, AC-7).
2. 매칭된 도메인의 `context/{domain}/status.md`를 Read한다.
3. 통과한 AC와 일치하는 행의 상태를 `⬜`→`✅`로, PR 열에 생성된 PR 링크를 기입한다.
4. AC가 `-`인 행은 변경하지 않는다 (PR 머지 시 수동 판정).
5. Edit으로 status.md를 갱신한다.
6. 갱신 결과를 사용자에게 보고한다:
   ```
   status.md 갱신: ✅ AC-1, AC-4, AC-7 (FR-1, FR-16, FR-19)
   ```

## 5.5 context 환류 제안

`DOMAIN_CONTEXT`가 있으면 실행한다. 없으면 건너뛴다.

PRD와 설계서에서 context 갱신 후보를 추출하여 사용자에게 제안한다:

1. **glossary 후보**: PRD/설계서에 등장하는 도메인 용어 중, 현재 `glossary.md`에 없는 것을 추출한다.
2. **주제 문서 후보**: PRD 제목과 배경을 기반으로, 주제 문서 생성을 제안한다.
3. **architecture.md 갱신 후보**: 설계서에 새로운 구조적 결정(레이어, 의존관계 등)이 있으면 인덱스 갱신을 제안한다.

사용자에게 AskUserQuestion으로 제안:
- "context 문서에 반영할까요?" + 후보 목록 표시
- 반영 선택 → 해당 파일 Edit/Write. 주제 문서 생성 시 architecture.md 인덱스에 링크 추가.
- 건너뛰기 선택 → 다음 단계 진행.

**임의 반영 금지**: 사용자 승인 없이 context 문서를 수정하지 않는다.

## 5.6 진행 상태 완료
`.dev/state.md`의 `status`를 `completed`, `phases.complete`를 `completed`로 갱신한다.

## 5.8 다음 단계

PR이 생성되었으면 완료이다. **PR 머지는 절대 실행하지 않는다** — 머지는 리뷰어가 직접 수행한다.

리뷰 수정 요청에 대비하여 작업환경 유지를 안내한다:
"리뷰 피드백 대응을 위해 현재 브랜치를 유지합니다. 리뷰 완료 후 베이스 브랜치로 전환하세요."
