> gx-cross-review/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 3-A. codex 경로

`${ADVISOR}` == `codex`인 경우.

#### 3a-1. prompt 빌드

`${PROMPT_FILE}` (= `${DEV_DIR}/cross-review-prompt.md`)에 다음 형식으로 작성한다.

> **prompt 본문 작성 규칙**: helper가 파일을 UTF-8로 읽어 stdin으로 전달한다. `$`·백틱·따옴표를 임의로 삭제하지 않고 산출물 원문을 보존한다.

```xml
<task>
oh-my-gx 파이프라인 산출물(PRD/설계/Trust Ledger)과 변경 코드를 교차 검증한다.
변경된 코드가 산출물의 약속을 충족하는지, 산출물에 정의되지 않은 신규 위험이 있는지 보고한다.

diff 파일: ${DIFF_FILE}
이 파일을 Read하여 변경사항을 확인한다.
</task>

<grounding_rules>
- 모든 지적은 PRD 또는 설계서의 정확한 인용으로 근거를 제시한다.
- trust-ledger.md에 이미 보고된 항목은 보고하지 않는다 (중복 금지).
- self-check.md의 Warning/Info는 중복 보고하지 않는다.
- 코드를 직접 확인하지 못한 추정은 ASSUMPTION으로 분리한다.
- PRD 자체가 코드와 일치하지 않을 가능성이 의심되면 ASSUMPTION으로 분류한다.
</grounding_rules>

<structured_output_contract>
다음 4개 섹션을 정확히 이 순서로 출력한다:

## AC 충족 매트릭스
| AC | 충족 | 근거 (파일:라인 또는 PRD 인용) |
|----|------|--------|
| AC-1 | O/X/부분 | ... |

## 설계 범위 이탈
설계서의 "변경 범위"에 명시되지 않은 파일 수정 목록.
항목별로: 파일 경로 / 변경 요약 / 이탈 사유 추정.
없으면 "이탈 없음".

## 신규 위험
trust-ledger.md에 없는 신규 risk/policy/gap/assumption만.
- [Critical/Warning/Info] [RISK/POLICY/GAP/ASSUMPTION] 항목 설명
  - 위치: 파일:라인
  - 근거: ...
  - 권고: ...

## references 위반 (해당 시)
references/ 디렉토리의 파일별로 위반 여부.
없으면 섹션 자체 생략.

## 총평
- 강점 1-2개
- Critical/Warning 합산
- 권고 사항 1줄
</structured_output_contract>

<language>
모든 출력은 한국어로 작성한다. 영어 단어는 고유명사·기술 용어에 한해 허용한다.
</language>

<artifacts>
다음 산출물을 참조한다.

### PRD 수용 기준
{prd.md의 "수용 기준" 섹션 내용}

### 설계서 변경 범위 + 구현 순서
{design.md의 해당 섹션 내용}

### 기존 Trust Ledger (이미 보고된 항목, 중복 금지)
{trust-ledger.md 전체}

### 자기점검 발견 사항 (중복 금지)
{self-check.md 전체}

### 코드 맵 (탐색 가이드)
{codemap.md의 "핵심 파일" 섹션}

### references (외부 표준)
{references 파일별 요약}
</artifacts>
```

#### 3a-2. codex 호출

재실행 전 기존 `${RAW_FILE}`, `${DEV_DIR}/cross-review.events.jsonl`, `${DEV_DIR}/cross-review.events.jsonl.stderr` **세 파일 모두** 존재하는 것만 충돌 없는 timestamp archive로 옮긴다. 하나라도 그대로 남으면 helper가 기존 출력 충돌로 거절할 수 있다. 백업 이름이 이미 있으면 새 suffix를 사용하고 기존 archive를 덮어쓰지 않는다. 이전 성공 응답을 재사용하지 않는다. 아래는 Bash 실행 예시이며 Python 실행 파일은 setup에서 검증한 실제 경로로 치환한다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/codex-run.py" --cwd "$PROJECT_ROOT" \
  --prompt "$PROMPT_FILE" --final "$RAW_FILE" \
  --events "$DEV_DIR/cross-review.events.jsonl" --mode review --timeout 300
```

helper가 prompt를 stdin으로 전달하고 read-only 세션을 연다. 프로세스 종료 코드가 0이 아니면 `${RAW_FILE}` 내용이 있어도 실패다. stderr와 이벤트를 보고하고 중단하며 정규화·자동 수정을 진행하지 않는다.

#### 3a-3. 응답 검증

1. 종료 코드 0 확인. 실패 시 stderr 마지막 20줄을 사용자에게 표시하고 중단.
2. `${RAW_FILE}` 줄 수 확인. 0줄이면 호출 실패로 간주.
3. 영어 응답 감지: 첫 50줄에서 한국어 문자(가-힣) 비율이 20% 미만이면 영어로 간주. 이 경우 한국어 정규화 단계를 추가:
   - 오케스트레이터가 직접 응답을 한국어로 재작성한다 (의미는 보존).
