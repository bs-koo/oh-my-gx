> gx-cross-review/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 3-B. native/claude 역할 경로

`${ADVISOR}` == `native`이거나 Claude Code 호스트에서 `${ADVISOR}` == `claude`인 경우. Codex native는 공통 실행 규약의 역할 본문·도구 제약과 현재 태스크 prompt 전문을 자식에게 전달한다. Claude Code의 기존 Task 타입은 유지한다.

#### 3b-1. cross-review contract

각 에이전트에 일반 phase-review와 다른 contract를 명시한다.

**Task A: qa-manager (cross-review 미션)**

`Task(subagent_type="oh-my-gx:qa-manager")` — prompt에 다음을 포함:

```
[중요] 이 호출은 일반 phase-review가 아닌 gx-cross-review이다.
일반적인 코드 품질 리뷰가 아니라, 다음 미션을 정확히 수행하라:

미션:
1. AC 충족 매트릭스 작성: PRD의 각 [Must] AC에 대해 충족 여부(O/X/부분)와 근거 파일:라인을 명시.
2. 설계 범위 이탈 점검: 설계서의 "변경 범위"에 없는 파일이 수정되었는지 확인. 이탈 시 정당성을 평가.
3. 중복 보고 금지:
   - trust-ledger.md에 이미 있는 항목은 다시 보고하지 않는다.
   - self-check.md의 Warning/Info는 중복 보고하지 않는다.
4. 신규 위험만 보고: trust-ledger에 없는 신규 발견 사항만 Critical/Warning/Info로 분류.

산출물:
- PRD: ${prd.md 내용}
- 설계서: ${design.md 내용}
- Trust Ledger: ${trust-ledger.md 내용}
- self-check: ${self-check.md 내용}
- 코드 맵: ${codemap.md 핵심 파일 섹션}
- diff 파일 경로: ${DIFF_FILE}
- references (있으면): ${references 요약}

출력 포맷은 cross-review 표준에 맞춘다 (Step 4의 정규화 형식 참조).
한국어로 출력한다.
```

**Task B: security-auditor (cross-review 미션)**

`Task(subagent_type="oh-my-gx:security-auditor")` — prompt에 다음을 포함:

```
[중요] 이 호출은 일반 review가 아닌 gx-cross-review이다.
다음 미션을 정확히 수행하라:

미션:
1. PRD 정책/제약 vs 코드 정합성: PRD에 명시된 정책/권한/제약이 코드에 반영되었는지 1:1 검증.
2. 설계 보안 약속 vs 코드: 설계서의 보안/장애대응(fallback/timeout/재시도)이 구현되었는지 검증.
3. trust-ledger 신선도: 기존 trust-ledger 항목 중 다시 발생한 것이 있는지 확인.
4. references 위반: references/ 디렉토리의 외부 표준 위반 여부 검증.
5. 중복 보고 금지: trust-ledger에 이미 있는 항목은 보고하지 않는다.

산출물 (qa-manager와 동일).

한국어로 출력한다.
```

#### 3b-2. 병렬 호출

`Task A`와 `Task B`를 **하나의 메시지에서** 동시에 발행한다 (병렬 실행).

#### 3b-3. 결과 통합

두 결과를 합산한다:
- AC 매트릭스 → qa-manager 결과를 우선 사용.
- 설계 범위 이탈 → qa-manager 결과 사용.
- 신규 위험 → 두 결과를 합치고 같은 위치(파일:라인)는 병합.
- references 위반 → security-auditor 결과 사용.

---
