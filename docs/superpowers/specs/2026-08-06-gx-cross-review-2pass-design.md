# 설계: gx-cross-review 2패스 재설계 (open-code-review delegate 연동)

- 날짜: 2026-08-06
- 상태: 승인됨 (브레인스토밍 완료)
- 대상 릴리스: v1.22.0 (minor — 신규 에이전트 + 스킬 구조 변경, 하위 호환 유지)
- 배경 요청: alibaba/open-code-review(OCR)의 결정론적 리뷰 파이프라인을 조사한 결과, 현재 gx-cross-review의 구조적 약점을 정확히 메우는 것으로 확인되어 도입을 결정.

## 1. 문제 정의

현재 `gx-cross-review`는 "산출물 약속 대비 충실도 검증"이라는 고유 정체성을 갖지만, 검증의 **입력을 만드는 층**에 세 가지 구조적 약점이 있다.

1. **커버리지 미보장.** Step 2-2가 `git diff <merge-base>`를 파일 하나에 통째로 리다이렉트한 뒤 advisor에게 넘긴다. 어떤 파일이 실제로 검토됐는지 확인할 수단이 없다.
2. **대형 변경에서 검증이 사실상 포기된다.** diff가 500줄을 넘으면 `--stat`으로 전환하며 "위는 요약입니다. 변경된 파일을 Read 도구로 직접 확인하라"를 덧붙인다. 커버리지가 advisor 재량에 통째로 위임된다.
3. **fallback 모드가 무의미하다.** SKILL.md 스스로 "일반 모드로 진행하면 기본 `/codex:review` 또는 qa-manager 일반 리뷰와 거의 동일합니다"라고 인정한다. 즉 산출물(PRD/설계)이 없는 저장소에서는 이 스킬을 쓸 이유가 없다.

또한 리뷰 품질 층에도 두 가지 공백이 있다.

4. **파일별 규칙이 없다.** 언어·파일 유형별 결함 체크리스트 없이 advisor의 일반 지식에만 의존한다.
5. **오탐 필터가 없다.** advisor가 낸 지적이 그대로 사용자에게 올라간다.

OCR의 delegate 모드가 1·2·4를, 프롬프트 설계 이식이 5를 해결하고, 그 결과로 3이 자연히 해소된다.

## 2. 목표 / 비목표

**목표:**
- 리뷰 대상 파일이 결정론적으로 확정되고, 제외된 파일은 사유와 함께 보고된다.
- 대형 변경에서도 파일 단위 분해로 커버리지가 유지된다 (`--scope stat` 포기 경로 제거).
- 산출물이 없는 저장소에서도 규칙 기반 결함 리뷰가 온전히 동작한다.
- 프로젝트 고유 규약(레이어·네이밍) 위반이 파일 단계에서 탐지된다. OCR 규칙은 언어 일반의 결함만 다루므로 프로젝트 컨벤션을 함께 주입한다.
- `gx-cross-review`의 기존 정체성(산출물 대비 충실도 검증, 자동 수정 금지, 한국어 강제, 단발 호출)은 그대로 유지한다.

**비목표:**
- OCR의 Go 코드 수정 또는 포크. 배포된 CLI를 그대로 사용한다.
- OCR `review` 모드(자체 LLM 호출) 사용. delegate 모드만 쓴다.
- 사내 표준(`references/`)을 OCR 규칙 체계로 이관. 두 체계는 분리 유지한다.
- `gx-dev`·`gx-tdd` 파이프라인 내부 phase 구조 변경. 이번 개편은 `gx-cross-review` 스킬과 신규 에이전트에 국한한다.

## 3. 전제 사실 (조사 결과)

설계 근거가 되는 OCR 사실. 저장소 `alibaba/open-code-review`(Apache-2.0) 소스 확인분이다.

| 항목 | 확인 내용 |
|---|---|
| delegate 모드의 LLM 의존 | 없음. OCR은 파일 선택과 규칙 해석만 수행하고 텍스트를 생성하지 않는다. 따라서 **LLM 엔드포인트·API 키 설정이 불필요하고 한국어 문제도 발생하지 않는다** (출력은 전부 Claude가 작성). |
| `ocr delegate preview` 출력 | mode(workspace/range/commit), from/to/commit/merge_base, 리뷰 대상 파일 목록(경로·상태·증감 라인수), 제외 파일 목록(제외 사유 포함). |
| `ocr delegate rule <paths...>` 출력 | 규칙 내용 기준으로 묶인 그룹. 같은 규칙을 공유하는 파일이 한 그룹으로 나오므로 중복이 없다. |
| 규칙 체계 | 내장 규칙 34종(`rule_docs/*.md`)을 경로 glob으로 first-match-wins 매칭. 사용자 규칙 4계층(`--rule` > `<repo>/.opencodereview/rule.json` > `~/.opencodereview/rule.json` > 내장). |
| 코멘트 스키마 | `path`, `content`, `start_line`, `end_line`, `category`(bug/security/performance/maintainability/test/style/documentation/other), `severity`(critical/high/medium/low). |
| 라이선스 | Apache-2.0. 프롬프트 규율 이식 시 출처 표기로 충족된다. |

> 참고: `review` 모드를 택했더라도 한국어는 가능했다. `internal/config/template/template.go`의 `resolveLang`이 설정값을 허용목록 검증 없이 그대로 `"Always respond in <lang>."`로 주입하기 때문이다. 다만 delegate 모드를 택했으므로 이 경로는 사용하지 않는다.

## 4. 설계

### 4.1 전체 구조

기존 Step 골격을 유지하고 Step 2를 교체, Step 3을 두 갈래로 분리한다.

| Step | 내용 | 변경 |
|---|---|---|
| 0 | 환경 감지 (브랜치·`DEV_DIR`·산출물) + **ocr 존재 확인** | 확장 |
| 1 | advisor 선택 — **Pass 2에만 적용** | 범위 축소 |
| 2 | `ocr delegate`로 대상 파일·규칙 확보 | **교체** |
| 3A | **Pass 1** — 파일별 병렬 결함 리뷰 + 오탐 필터 | **신규** |
| 3B | **Pass 2** — 산출물 대조 (advisor) | 입력 변경 |
| 4 | 결과 통합 정규화 + 커버리지 보고 | 확장 |
| 5 | 항목 처리 (사용자 승인 후 coder 위임) | 유지 |

두 패스의 역할 분담:

| 패스 | 묻는 질문 | 단위 | 산출 섹션 |
|---|---|---|---|
| Pass 1 | "이 코드에 결함이 있는가" | 파일 | 신규 위험 |
| Pass 2 | "이 변경이 산출물의 약속을 지켰는가" | 변경 전체 | AC 충족 매트릭스, 설계 범위 이탈, references 위반 |

### 4.2 Step 0 확장 — ocr 존재 확인

산출물 점검(기존 0-3) 이후 다음을 수행한다.

```bash
which ocr
```

실패 시 안내 후 **종료한다.** 자동 설치는 하지 않는다 (기존 codex 선례 준수 — 사용자 환경 침해 방지).

```
open-code-review(ocr) CLI가 설치되어 있지 않습니다.

설치:
  npm install -g @alibaba-group/open-code-review

설치 후 /gx-cross-review를 다시 호출해주세요.
(delegate 모드로 사용하므로 별도 LLM 설정은 필요하지 않습니다.)
```

환경 보고(기존 0-4)에 `ocr: v{버전}` 한 줄을 추가한다.

### 4.3 Step 2 교체 — 대상 파일·규칙 확보

**2-1. preview 2회 호출 후 병합.**

`gx-cross-review`는 "`/gx-dev` 직후 `git add` 전 호출"을 명시적으로 지원한다. 그런데 `ocr delegate preview --from/--to`(range 모드)는 커밋된 변경만 본다. 따라서 두 번 호출해 경로 기준으로 병합한다.

```bash
ocr delegate preview --from "${BASE_BRANCH}" --to HEAD > "${DEV_DIR}/preview-range.txt"
ocr delegate preview                                    > "${DEV_DIR}/preview-workspace.txt"
```

- 첫 호출: 커밋된 변경. merge-base는 OCR이 계산하여 출력에 포함한다.
- 둘째 호출: staged + unstaged + untracked.
- 두 출력의 리뷰 대상 파일 목록을 합집합으로 병합하고 경로 중복을 제거한다. 같은 경로가 양쪽에 있으면 한 항목으로 합치고 상태는 workspace 쪽 값을 채택한다.
- 제외 파일 목록도 합쳐 사유를 보존한다. 같은 경로가 한쪽에서 리뷰 대상, 다른 쪽에서 제외로 나오면 **리뷰 대상을 우선한다.**
- 병합 결과를 `${DEV_DIR}/targets.md`에 기록한다.

> **preview의 역할은 파일 목록 확정에 한정한다.** diff 본문 획득에는 사용하지 않는다 (3A-2 참조). 두 모드의 diff를 각각 받아 합치면 같은 파일의 커밋분과 미커밋분이 분리되어 리뷰어가 변경 전체를 못 보게 된다.

**2-2. 규칙 확보.**

```bash
ocr delegate rule <병합된 경로들...> > "${DEV_DIR}/rules.md"
```

출력은 규칙 내용 기준 그룹이므로 그대로 저장한다.

파일이 많아 명령줄 길이가 문제되면 50개 단위로 나눠 호출한다. 이때 **단순히 이어붙이면 안 된다** — 각 호출이 `### Rule Group 1`부터 독립적으로 번호를 매기므로 번호가 중복되고, 여러 배치에 걸친 같은 규칙 그룹이 중복 출력된다. 병합 규칙:

1. 배치별 출력에서 그룹을 파싱한다 (그룹 헤더의 출처·패턴, 규칙 본문, 적용 파일 목록).
2. **출처·패턴·본문 3개가 모두 같은 그룹을 하나로 합치고 적용 파일 목록을 합집합한다.** (OCR이 그룹을 나누는 기준과 동일하다.)
3. 합친 결과에 `1`부터 다시 번호를 매겨 `rules.md`에 기록한다.

**2-3. 조기 종료.**

병합된 리뷰 대상이 0건이면 `"변경사항이 없습니다."`를 표시하고 종료한다.

### 4.4 Step 3A 신규 — Pass 1 파일별 결함 리뷰

**3A-1. 배분.**

- 원칙: **파일 1개당 `defect-reviewer` 1개.** OCR의 파일당 독립 세션을 재현하는 것이 이 패스의 존재 이유다.
- 동시 디스패치 상한: **5개.** 한 메시지에 최대 5개 Task를 발행하고, 완료되면 다음 묶음을 발행한다.
- 파일이 **15개를 초과**하면 AskUserQuestion으로 확인한다.

```
AskUserQuestion(
  questions: [{
    question: "리뷰 대상이 N개 파일입니다. 어떻게 진행할까요?",
    header: "대상 규모",
    options: [
      { label: "전체 리뷰", description: "N개 파일 전부 리뷰 (에이전트 N회 디스패치)" },
      { label: "변경량 상위 15개", description: "증감 라인수 기준 상위 15개만 리뷰. 나머지는 커버리지에 '사용자 선택 제외'로 기록" },
      { label: "중단", description: "범위를 좁혀 다시 호출" }
    ],
    multiSelect: false
  }]
)
```

**3A-2. `defect-reviewer` 입력.**

각 디스패치에 다음을 전달한다.

- 대상 파일 경로 1개
- **해당 파일의 diff 파일 경로** (`${DEV_DIR}/diffs/<슬러그>.diff`)

> **diff는 오케스트레이터가 미리 파일로 만들어 경로만 넘긴다.** `defect-reviewer`의 도구는 `Read, Glob, Grep`이라 Bash가 없어 스스로 git을 실행할 수 없다. 또한 `phase-review`가 에이전트에 `diff 파일 경로: {DIFF_FILE}`를 전달하는 oh-my-gx의 확립된 패턴과도 일치시킨다.

Step 3A 진입 전에 오케스트레이터가 대상 파일마다 diff를 생성한다. **파일이 range·workspace 어느 쪽에서 왔든 동일한 명령을 쓴다** — 커밋분과 미커밋분이 쪼개지면 리뷰어가 변경 전체를 보지 못하기 때문이다.

```bash
mkdir -p "${DEV_DIR}/diffs"
MB=$(git merge-base HEAD "${BASE_BRANCH}")
# tracked: 커밋 + staged + unstaged를 한 번에 포함
git diff "${MB}" -- "<path>" > "${DEV_DIR}/diffs/<슬러그>.diff"
# untracked: 전체를 신규 코드로 간주
git diff --no-index /dev/null "<path>" > "${DEV_DIR}/diffs/<슬러그>.diff" 2>/dev/null
```

**슬러그 규칙**: 경로의 `/`를 `-`로 치환한다 (`src/main/App.java` → `src-main-App.java.diff`). `DEV_DIR`/`BRANCH_SLUG`와 동일한 치환 규칙이다.

생성 결과가 0줄인 파일은 리뷰 대상에서 제외하고 커버리지 `excluded`에 `diff 없음` 사유로 기록한다 (커밋 후 워킹 트리에서 되돌린 파일 등).

- `rules.md`에서 해당 파일이 속한 규칙 그룹의 체크리스트
- 요구사항 배경 (산출물이 있으면 PRD 수용 기준 요약, 없으면 생략)
- **프로젝트 컨벤션** — 프로젝트 루트 `CLAUDE.md`의 아키텍처·패턴·컨벤션 섹션. 없으면 생략한다.

> **컨벤션을 주입하는 이유**: OCR 규칙은 언어 일반의 결함(NPE, 스레드 안전성, SQL 인젝션)을 다루지 어떤 프로젝트의 레이어 규약이나 네이밍 규칙도 알지 못한다. 컨벤션 없이는 사내 규약 위반이 파일 단계에서 전부 누락되어 Pass 2나 사후 리뷰로 밀린다. 기존 `quality-reviewer`가 `config.json`에서 `"diff + 코드 맵 + 컨벤션"`을 입력으로 정의한 것과 같은 수준을 맞춘다.
>
> **주입 범위는 컨벤션까지다.** `references/`(사내 표준 문서)는 Pass 2에서만 사용한다 (4.1 규칙 체계 분리 원칙). 규격 준수 검증은 문서 전문 대조가 필요해 파일 단위 리뷰에 넣으면 파일마다 표준 문서를 반복 로드하게 된다.

**3A-3. `defect-reviewer` 출력.**

코멘트 목록 + 기존 에이전트 관례에 따른 YAML verdict 블록.

```yaml
defect_verdict:
  file: src/main/java/com/example/PaymentService.java
  status: reviewed | failed
  comments: 3
  by_severity: { critical: 1, high: 0, medium: 2, low: 0 }
```

코멘트 항목 스키마는 OCR과 정렬한다: `path`, `start_line`, `end_line`, `category`(8종), `severity`(4단계), 근거, 권고.

**3A-4. 오탐 필터.**

수집된 코멘트가 **4건 이상**이면 반증 기반 필터를 1회 적용한다 (3건 이하는 생략 — 비용 대비 이득이 없다).

필터의 판정 원칙은 비대칭이다.

- 제거 대상: diff만으로 **핵심 주장이 틀렸다고 입증되는** 코멘트
- 통과: 확인 불가한 코멘트. 리뷰어는 Read/Grep으로 필터가 못 보는 컨텍스트를 확인했을 수 있다
- 통과: 의심스럽지만 반증하지 못하는 코멘트

필터는 오케스트레이터가 직접 수행한다 (에이전트 추가 없음). 제거된 항목은 **`${DEV_DIR}/filtered-out.md`**에 사유와 함께 보존한다.

> **`RAW_FILE`을 재사용하지 않는 이유**: 기존 `SKILL.md`의 `${RAW_FILE}`(`cross-review.raw.md`)은 "advisor 원시 응답" 전용이고, Step 3a-2의 codex 호출이 `> "${RAW_FILE}"`로 **덮어쓴다.** Pass 1의 필터 기록을 같은 파일에 쓰면 Pass 2 실행 시 소실된다.

### 4.5 신규 에이전트 `defect-reviewer`

`agents/defect-reviewer.md`를 추가한다. 도구는 `Read, Glob, Grep`(읽기 전용).

핵심 규율 세 가지를 에이전트 정의에 명시한다. 이는 OCR 프롬프트 설계에서 가져온 것이다 (Apache-2.0, 출처 표기).

1. **탐색 도구는 이해용이다.** Read/Grep으로 다른 파일을 읽어도 되지만, **코멘트는 배정된 파일의 변경분에만** 단다. 다른 파일에서 문제를 발견하면 무시한다.
2. **precision > recall.** 오탐은 리뷰어 신뢰를 깎는다. 확신이 서지 않으면 보고하지 않는다. 컴파일러·린터·포매터가 이미 잡는 것은 중복 보고하지 않는다.
3. **보고하지 말아야 할 케이스를 명시한다.** 삭제된 코드, 변경되지 않은 코드, 스타일 취향 문제.

컨벤션 위반은 **근거를 인용해야 한다.** 프로젝트 `CLAUDE.md`의 해당 규약을 인용하지 못하면 스타일 취향으로 간주하고 보고하지 않는다 (규율 2의 연장).

`config.json`의 `contextLimits`에 `defect-reviewer` 항목을 추가한다.

```json
"defect-reviewer": { "maxInputLines": 800, "note": "파일 1개 diff + 규칙 그룹 + 컨벤션 (파일당 호출이므로 작게 유지)" }
```

기존 리뷰 에이전트와의 경계:

| 에이전트 | 범위 | 호출 주체 |
|---|---|---|
| `spec-reviewer` | AC 충족 여부 | gx-tdd phase-review |
| `quality-reviewer` | 코드 품질 (변경 전체) | gx-tdd phase-review |
| `defect-reviewer` | **파일 1개의 결함 (OCR 규칙 + 프로젝트 컨벤션)** | **gx-cross-review Pass 1** |

`defect-reviewer`는 파이프라인 내부에서 호출하지 않는다. `gx-cross-review` 전용이다.

### 4.6 Step 3B — Pass 2 입력 변경

advisor 호출 구조(codex 경로 / claude 경로)는 유지하고 **입력만 바꾼다.**

- 입력: `diff 통째` → `리뷰 대상 파일 목록 + 파일별 변경 요약(증감 라인수·상태) + 산출물`
- **500줄 `--scope stat` 전환 규칙을 삭제한다.** 파일 분해가 Pass 1에서 끝났으므로 존재 이유가 없다. advisor가 세부 확인이 필요하면 Read로 본다.
- `--scope` 플래그도 함께 폐기한다 (인식하지 못한 옵션 경고로 처리).
- Pass 1이 확정한 신규 위험 목록을 함께 전달하고, **중복 보고를 금지**한다 (기존 trust-ledger·self-check 중복 차단과 동일한 규율).
- **`${DIFF_FILE}` 변수를 폐기한다.** Step 2-2(diff 통째 수집)가 사라지므로 이 변수를 생성하는 곳이 없어진다. 기존 `SKILL.md`에서 이 변수를 참조하는 네 곳을 함께 정리한다.

| 기존 위치 | 처리 |
|---|---|
| 공유 변수 정의 (`DIFF_FILE`) | 삭제. 대신 `DIFFS_DIR`(`${DEV_DIR}/diffs/`), `TARGETS_FILE`, `RULES_FILE`, `FILTERED_FILE`을 추가 |
| Step 2-1 우선순위 표의 `diff` 행 | `리뷰 대상 파일 목록 + 파일별 변경 요약`으로 교체 |
| codex prompt `diff 파일: ${DIFF_FILE}` | `대상 파일 목록: ${TARGETS_FILE}` + "세부 확인이 필요하면 해당 파일을 Read하라"로 교체 |
| claude prompt `diff 파일 경로: ${DIFF_FILE}` | 위와 동일하게 교체 |
- **산출물(prd/ac/design)이 셋 다 없으면 Pass 2를 통째로 생략한다.** Step 4에서 AC 매트릭스·설계 범위 이탈·references 위반 섹션을 생략하고 Pass 1 결과만으로 보고한다.

### 4.7 Step 4 — 통합 정규화

기존 4-1 포맷에 커버리지 섹션을 추가하고 순서를 확정한다.

```markdown
# Cross-Review 결과

- advisor: codex | claude | (Pass 2 생략)
- 브랜치: ${BRANCH} (base: ${BASE_BRANCH})
- DEV_DIR: ${DEV_DIR}
- 실행 시각: ...

## 커버리지
- 리뷰: 12개 파일
- 제외: 5개 (테스트 3, 생성 코드 1, binary 1)
- 실패: 0개
- 오탐 필터: 15건 중 3건 제거

제외 사유 범주는 다음 다섯 가지다. 앞의 셋은 OCR preview가 판정하고, 뒤의 둘은 이 스킬이 판정한다.

| 사유 | 판정 주체 |
|---|---|
| 테스트 / 생성 코드 / binary / 대형 diff 등 | `ocr delegate preview` |
| `사용자 선택 제외` | 3A-1의 "변경량 상위 15개" 선택 |
| `diff 없음` | 3A-2의 diff 생성 결과가 0줄 |

## AC 충족 매트릭스
(산출물 없으면 섹션 생략)

## 설계 범위 이탈
(산출물 없으면 섹션 생략)

## 신규 위험
### Critical
- [bug] PaymentService.java:55 — 한도 초과 검증 누락
  - 근거: ...
  - 권고: ...
### High
### Medium
### Low

## references 위반
(해당 없으면 섹션 생략)

## 총평
```

**심각도 표기 통일**: OCR 스키마에 맞춰 `Critical / High / Medium / Low` 4단계로 **전면 통일한다.** 기존 `Critical / Warning / Info` 3단계는 폐기한다.

- 두 패스가 같은 어휘를 써야 통합 집계가 성립한다. Pass 1만 4단계로 두면 Pass 2 결과와 합산할 수 없다.
- 따라서 **Pass 2 advisor의 출력 계약(`structured_output_contract`)도 4단계로 갱신한다.**
- Step 5의 처리 대상 식별·일괄 처리 옵션 문구도 4단계 표현으로 바꾼다 (처리 흐름 자체는 불변).

사용자 요약(기존 4-3)에 커버리지 한 줄을 추가한다.

```
## Cross-Review 완료

- advisor: codex
- 커버리지: 12개 파일 리뷰 / 5개 제외 / 0개 실패
- AC 충족: [Must] 4/5, [Should] 2/3
- 설계 범위 이탈: 1건
- 신규 위험: Critical 1, High 2, Medium 3, Low 0
- references 위반: 없음

전문: ${DEV_DIR}/cross-review.md
```

### 4.8 진행 상태 추적 확장

`${DEV_DIR}/cross-review-state.md`의 `findings`에 커버리지 필드를 추가한다.

```yaml
coverage:
  reviewed: 12
  excluded: 5
  failed: 0
  filtered_out: 3
```

## 5. 에러 처리

| 상황 | 동작 |
|---|---|
| `ocr` 미설치 | 설치 안내 후 종료. 자동 설치 금지 |
| `ocr delegate` 종료 코드 ≠ 0 | stderr 마지막 20줄 표시 후 중단. 폴백 없음 |
| preview 병합 결과 0건 | "변경사항이 없습니다." 후 종료 |
| `defect-reviewer` 일부 실패 | 성공분만 사용하고 커버리지 `failed`에 파일명 기록. 결과 보고에 부분 결과임을 명시 |
| `defect-reviewer` 전부 실패 | 실패로 보고하고 중단. 부분 성공과 전면 실패를 구분한다 |
| Pass 2 advisor 실패 | Pass 1 결과만으로 보고하고 부분 결과임을 명시 |
| 산출물 부재 | 오류가 아니다. Pass 2 생략 후 Pass 1 결과로 정상 완료 |

기존 "산출물 부재 fallback" 섹션(F-1~F-3)은 **삭제한다.** 산출물 부재가 더 이상 예외 경로가 아니라 정상 분기이므로, 진행 여부를 묻는 AskUserQuestion도 함께 제거한다.

## 6. 검증

oh-my-gx의 기존 2층 검증 방식을 따른다.

**골든 시나리오** (`tests/golden-scenarios.md`에 추가):

| ID | 전제 | 트리거 | 기대 동작 |
|---|---|---|---|
| S18 | `ocr` 미설치 | `/gx-cross-review` | 설치 안내 후 종료. 자동 설치 시도 0회 |
| S19 | 산출물 없는 저장소 + 변경 3파일 | `/gx-cross-review` | Pass 1만 동작. AC 매트릭스·설계 범위 이탈 섹션 미출력. 진행 여부 질문 없음 |
| S20 | **커밋된 변경 1파일** + `git add` 전 미커밋 변경 1파일 + untracked 신규 1파일 | `/gx-cross-review` | 세 파일 모두 리뷰 대상에 포함. 커밋 파일은 range preview에서만, 나머지는 workspace preview에서만 나오므로 **2회 병합이 동작해야 통과**한다 |
| S21 | 변경 20개 파일 | `/gx-cross-review` | 15개 초과 확인 질문 1회. 전체 선택 시 동시 5개씩 배분 디스패치 |
| S22 | 산출물 있는 저장소 | `/gx-cross-review` | 커버리지 섹션 출력 + Pass 1 결과가 Pass 2 advisor 프롬프트에 중복 금지 항목으로 전달됨 |
| S23 | 프로젝트 `CLAUDE.md`에 레이어·네이밍 규약이 있고 이를 위반한 변경 | `/gx-cross-review` | 컨벤션 위반이 Pass 1에서 보고되고 **근거로 `CLAUDE.md` 규약이 인용됨**. 인용 없는 스타일 지적은 보고되지 않음 |

**정적 불변식** (`scripts/lint-consistency.sh`):

기존 스크립트의 검사 [5/22]("디스패치 이름 ↔ `agents/` 대조", `lint-consistency.sh:116-123`)는 디스패치 이름에서 `agents/<name>.md` 존재를 확인하므로 `defect-reviewer` 추가만으로 자동 적용된다. 아래 3종을 새로 추가한다.

- `defect_verdict` 블록 producer 정의가 `agents/defect-reviewer.md`에 존재하는지 (기존 `spec_verdict`·`quality_verdict` 검사 `:74-79`와 동일 방식)
- `gx-cross-review` SKILL.md의 `allowed-tools`에 `Bash(ocr *)`가 포함되는지
- SKILL.md에 `--scope`·`DIFF_FILE` 잔존 기술이 없는지

## 7. 유지되는 것 (회귀 금지)

- **자동 수정 금지.** Step 5의 항목별 사용자 승인 게이트는 그대로다. Pass 1이 낸 Critical도 즉시 coder를 호출하지 않는다.
- **한국어 강제.** delegate 모드는 OCR이 텍스트를 생성하지 않으므로 모든 출력이 Claude 작성분이다. 기존 한국어 규칙이 그대로 적용된다.
- **단발 호출 전용.** `--resume` 미지원.
- **`gx-tdd` 내부 호출 금지 예외 유지.** cross-review는 파이프라인 완료 후 독립 스킬이다.
- **`--advisor`, `--dev-dir`, `--base` 플래그 유지.** `--scope`만 폐기한다.

## 8. 영향 범위

| 파일 | 변경 |
|---|---|
| `.claude/skills/gx-cross-review/SKILL.md` | Step 0/2/3/4 개편, fallback 섹션 삭제, `--scope`·`DIFF_FILE` 폐기 및 공유 변수 섹션 갱신, 심각도 4단계 통일(advisor 계약·Step 5 문구 포함), `allowed-tools`에 `Bash(ocr *)` 추가 |
| `agents/defect-reviewer.md` | 신규 |
| `.claude/config.json` | `contextLimits`에 `defect-reviewer` 항목 추가 |
| `tests/golden-scenarios.md` | S18~S23 추가 (기록 문구의 총 개수도 17 → 23으로 갱신) |
| `scripts/lint-consistency.sh` | 불변식 3종 추가 |
| `.claude-plugin/plugin.json` · `marketplace.json` | version → 1.22.0 |
| `CHANGELOG.md` | v1.22.0 섹션 |
| `docs/guide.md` | gx-cross-review 절 갱신 (ocr 설치 요구 명시) |

`gx-dev`·`gx-tdd`의 phase 파일은 건드리지 않는다.

## 9. 출처

- alibaba/open-code-review (Apache-2.0) — https://github.com/alibaba/open-code-review
- 이식 대상: delegate 모드 CLI 연동, 리뷰 프롬프트 규율(탐색·코멘트 분리, precision > recall, 보고 제외 케이스), 반증 기반 오탐 필터 원칙, 코멘트 스키마(category/severity)
