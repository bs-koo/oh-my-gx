> gx-cross-review/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

## 산출물 부재 fallback

Step 0-3에서 prd.md·ac.md·design.md 셋 다 없으면 이 경로를 따른다.

### F-1. fallback 모드 안내

```
산출물(prd.md·ac.md·design.md)이 없습니다.
gx-cross-review의 차별점인 "약속 대비 충실도 검증"을 수행할 수 없습니다.
일반 모드로 진행하면 기본 /codex:review 또는 qa-manager 일반 리뷰와 거의 동일합니다.
```

### F-2. 진행 여부 확인

```
AskUserQuestion(
  questions: [{
    question: "일반 모드로 진행할까요?",
    header: "fallback",
    options: [
      { label: "진행", description: "산출물 없이 diff만으로 일반 리뷰 수행" },
      { label: "중단", description: "/gx-work로 산출물을 먼저 생성하세요" }
    ],
    multiSelect: false
  }]
)
```

### F-3. fallback 실행

**fallback 승인 후 공통 선행 단계**: Step 1의 advisor 선택과 1-1 환경 확인을 수행한다. `--advisor claude`를 Codex 호스트에서 선택했다면 여기서 중단한다. 이어서 Step 2-2의 diff 수집을 **실제로 실행**하여 `${DIFF_FILE}`을 만든다. 산출물이 없는 경우에도 diff 수집을 건너뛰지 않는다. diff가 비었으면 "변경사항이 없습니다"를 보고 종료한다. 이 선행 단계가 끝난 뒤 F-3으로 돌아온다.

**codex 선택 시**: `Read("advisor-codex.md")`의 3a-2 archive·호출 실패 계약을 먼저 확인한다. 일반 리뷰 미션과 `${BASE_BRANCH}`·실제로 수집한 `${DIFF_FILE}` 경로를 `${PROMPT_FILE}`에 기록하고 네이티브 helper의 read-only review 모드로 호출한다. 산출물 없는 경우 AC 매트릭스가 없음을 prompt에 명시한다. 기존 `${RAW_FILE}`, `${DEV_DIR}/cross-review.events.jsonl`, `${DEV_DIR}/cross-review.events.jsonl.stderr` 세 파일 모두 3a-2와 같은 충돌 없는 timestamp archive로 옮긴다.
```bash
python3 "$GX_PLUGIN_ROOT/scripts/codex-run.py" --cwd "$PROJECT_ROOT" \
  --prompt "$PROMPT_FILE" --final "$RAW_FILE" \
  --events "$DEV_DIR/cross-review.events.jsonl" --mode review --timeout 300
```
- 종료 코드가 0이 아니면 결과 정규화 없이 중단한다. diff 수집 범위는 Step 2-2에서 만든 `${DIFF_FILE}`을 따른다.

**native/claude 역할 선택 시**: `qa-manager`만 호출, 일반 contract 사용 (cross-review 미션 제거). security-auditor는 호출하지 않는다 (산출물 없으면 보안 정합성 검증이 불가능). Codex의 claude 선택은 Step 1에서 이미 중단한다.

결과는 동일하게 `${RESULT_FILE}`에 저장. AC 매트릭스 / 설계 범위 이탈 섹션은 생략하고 신규 위험 섹션만 채운다.

---
