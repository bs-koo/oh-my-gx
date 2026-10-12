# gx-tdd 단위테스트계획서(DE-13) 연동 설계

작성일: 2026-10-12
상태: 설계 확정 — 사용자 검토 대기
기준 커밋: `e807c65` (main)

## 목표

gx-pm이 산출한 DE-13 단위테스트계획서(xlsx)를 gx-tdd와 잇는다. 테스트 설계의 주도권은 gx-tdd에 남긴다. 계획서는 두 가지 역할만 한다.

1. **하한선**: 이번 작업 범위에 해당하는 계획서 케이스는 최소한 테스트로 존재해야 한다.
2. **결과 회신**: 계획서 케이스에 대응하는 테스트를 실행해 통과했으면 계획서의 `결과`·`수행일`·`테스트담당자` 열에 기입할 수 있게 한다.

계획서가 레포에 없으면 연동 전체가 꺼지고 gx-tdd는 현재와 같이 동작한다.

## 확정한 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| 연동 관계 | gx-tdd가 AC·테스트를 설계하고, DE-13은 하한선이다. AC가 계획서를 대체하지 않는다 | 사용자 결정 |
| 전달 형태 | 개발자는 gx-pm 산출물 xlsx 6종만 받는다. md 원본은 PM에게만 있다 | 사용자 결정 |
| 범위 선정 | 요청에 기능ID가 있으면 그 기능의 UT 행 전체. 없으면 기능명 매칭 후보를 보여주고 확인받으며, 선택지에 "연동 안 함"을 항상 둔다 | 사용자 결정 |
| 결과 기입 방식 | 텍스트 원장(기능별 md)을 커밋하고, 별도 스킬이 원장을 xlsx **사본**에 반영한다 | 사용자 결정 (아래 기각 대안 참조) |
| 테이블 사후조건 | 모의 검증을 허용한다. 저장 대상과 건수를 단언하고, `변화 없음`이면 저장 호출 0회를 단언한다 | 사용자 결정 |
| 화면 문구 | 서버 응답·예외가 문구를 담으면 계획서 원문 그대로 단언한다. 화면이 문구를 정하면 오류코드를 단언하고 원장 비고에 `문구는 화면 책임`을 남긴다 | 사용자 결정 |
| 테스트담당자 | 원장에는 git `user.name`을 기록한다. 반영 시 처음 보는 이름은 실명을 묻고 매핑 파일에 저장한다 | 사용자 결정 |
| 활성 조건 | 계획서가 없으면 꺼짐. 있고 기능ID가 있으면 켜짐. 있고 ID가 없으면 후보 질문(연동 안 함 포함) | 사용자 결정 |
| 적용 파이프라인 | gx-tdd(전체·핵심 모드)만. gx-dev와 gx-ralph 루프 내부는 범위 밖 | 범위 최소화 |

### 기각한 대안

- **xlsx 직접 기입**: 바이너리라 여러 브랜치가 같은 파일에 기입하면 머지 충돌을 사람이 풀어야 한다. PM이 gx-pm에서 계획서를 개정해 xlsx를 다시 내보내면 기입한 결과가 사라진다. 결과가 머지 전 브랜치에서 파일에 들어가는 점도 어색하다.
- **gx-pm 쪽 결과 가져오기**: md 원본·xlsx·추적매트릭스(AN-05)를 한 번에 맞출 수 있지만 두 플러그인을 함께 바꿔야 한다. 이 설계의 원장 형식을 그대로 읽을 수 있도록 남겨 두고 후속 과제로 둔다.

## 실측 근거 — REB 계획서 (`pm-test/건물에너지 데이터 통합관리 시스템`)

| 항목 | 값 | 설계에 미친 영향 |
|---|---|---|
| 전체 행 | 169 (기능 142, 비기능 27) | 비기능 행(연계기능ID 공란)은 하한선 대상 외 |
| 열 | 11개, `요구사항명` 없음. gx-pm 4.1 템플릿은 12열 | 열을 머리글 이름으로 찾는다 |
| 문자열 저장 | 셀 안 문자열(inlineStr)만 있음, 공유 문자열 없음 | 엑셀 재저장본(공유 문자열)도 읽어야 한다 |
| `결과` 열 데이터 검증 | `K2:K170`, 목록 `Pass,Fail` | 반영 시 정확히 `Pass`만 쓴다 |
| 기능당 UT 수 | 최대 7 (FN-001·004·037), 최소 2 | core의 AC 3~5 상한과 충돌 |
| `〃` | 16행 | 같은 기능의 바로 위 행일 때만 풀린다 |
| 떨어진 ID | FN-027(UT-080, 168), FN-028(UT-081, 169) | ID 범위가 아니라 연계기능ID로 추출 |
| 다른 기능에 의존 | 28행 (예: FN-005의 UT-021 → FN-004의 UT-014) | 의존은 실행 순서가 아니라 Given 준비 데이터 |
| 사후조건에 테이블 건수 | 기능 행 45건 | 모의 검증 허용 결정 |
| 따옴표 화면 문구 | 48행 | 문구 단언 결정 |
| 대용량·시간 조건 | 기능 행 8건 (1,000MB, 100만 건, 30분, 일 990건 등) | design 단계에서 대역(크기 추상화·Clock 주입) 설계 |
| `[미확정]` | 3행 (모두 비기능) | 대상 외 |
| `[가정:…]` | 1행 (UT-048) | 표식 `가정`, AC에 가정 기반임을 표시 |

## 구성요소

### 1. 헬퍼 `.claude/skills/gx-test-plan/scripts/de13.py`

표준 라이브러리(`zipfile`, `xml.etree`, `hashlib`, `json`, `argparse`)만 사용한다. 파일 입출력은 `encoding="utf-8"`로 명시한다. 큰 출력은 stdout이 아니라 파일로 쓴다(Windows 콘솔 인코딩 회피). gx-tdd는 `../gx-test-plan/scripts/de13.py`로, gx-test-plan은 `scripts/de13.py`로 호출한다.

| 명령 | 인자 | 출력 | 종료 코드 |
|---|---|---|---|
| `scope` | `--plan <xlsx> --out <파일> [--fn <ID,…>] [--spec <기능명세서.xlsx>]` | `--fn`이 있으면 `ut-floor.md`. 없으면 기능 목록 JSON(`기능ID`, `UT 수`, `기능명`) | 0 성공 · 2 입력 오류(파일·머리글 없음, 계획서에 없는 기능ID) |
| `check` | `--floor <ut-floor.md> --root <PROJECT_ROOT> --out <check.json>` | UT ID별 `found` / `missing` / `skipped` + 위치 | 0 전부 found · 1 missing 또는 skipped 존재 · 2 입력 오류 |
| `record` | `--floor <ut-floor.md> --check <check.json> --ledger-dir <dir> --date <YYYY.MM.DD> --tester <이름>` | `{ledger-dir}/{기능ID}.md` 갱신 | 0 · 2 |
| `apply` | `--plan <xlsx> --ledger-dir <dir> --testers <testers.md> --out <xlsx> --report <json>` | 결과를 채운 사본 + 요약 JSON | 0 · 2 · 3 매핑 없는 담당자 존재(요약에 목록) |

**읽기 규칙**

- **시트**: 이름이 `단위테스트계획`인 시트를 먼저 쓰고, 없으면 머리글 행에 `테스트ID`와 `연계기능ID`가 함께 있는 첫 시트를 쓴다.
- **머리글 행**: 위에서부터 `테스트ID`·`연계기능ID`가 함께 있는 첫 행이다. 제목 행이 끼어 있어도 찾는다.
- **필수 열**: `테스트ID`, `연계기능ID`, `사전조건`, `입력`, `기대결과`, `사후조건`, `의존성`, `테스트담당자`, `수행일`, `결과`. 하나라도 없으면 종료 코드 2.
- **선택 열**: `연계요구사항ID`, `요구사항명`.
- **문자열 형식**: inlineStr, 공유 문자열(`xl/sharedStrings.xml`), 서식 런(`<r><t>`)을 모두 읽는다.
- **`〃`**: 셀 값이 `〃`이면 바로 위 행이 같은 `연계기능ID`일 때만 그 행의 같은 열 값으로 푼다. 아니면 원문을 두고 표식에 `〃미해결`을 단다.
- **대상 외**: `연계기능ID`가 비어 있는 행(비기능), 셀 어디에든 `[미확정`이 있는 행.
- **표식**: `[가정` → `가정`. `의존성`에 다른 기능의 UT가 있음 → `타기능 의존`.
- **행 지문**: `〃`를 푼 뒤 `사전조건`·`입력`·`기대결과`·`사후조건` 각 값의 앞뒤 공백을 지우고 연속 공백을 하나로 줄인다. `\x1f`로 이어 SHA-256을 구하고 앞 8자를 쓴다. `테스트ID`는 넣지 않는다. 그래야 개정판에서 같은 ID의 내용이 바뀌면 지문이 달라진다.

**`check` 규칙**

- **테스트 소스**:
  - 빌드 산출물(`node_modules`, `build`, `dist`, `target`, `.gradle`, `out`)과 `.git`, `.dev`는 뺀다.
  - 경로에 `test`·`tests`·`__tests__`·`spec` 디렉터리가 있거나, 파일명이 `*Test.*`·`*Tests.*`·`*.test.*`·`*.spec.*`·`test_*.py`·`*_test.*`인 소스 파일이 대상이다.
  - 대상 확장자: `.java .kt .kts .groovy .scala .js .jsx .ts .tsx .mjs .cjs .py .go .cs .rb .php .rs .c .cc .cpp .swift`
- **ID 인식**: 원문 `REB-UT-002`와 하이픈을 밑줄로 바꾼 `REB_UT_002`. 앞뒤가 영숫자·하이픈이 아닐 때만 일치로 본다. 그래야 `REB-UT-0021`은 `REB-UT-002`로 잡히지 않는다.
- **skip 휴리스틱**:
  - ID가 나온 줄에서 위로 올라가 가장 가까운 테스트 선언까지 사이에 skip 표식이 있으면 `skipped`로 본다.
  - 테스트 선언: `@Test`, `@ParameterizedTest`, `@RepeatedTest`, `it(`, `test(`, `def test_`, `func Test`, `[Fact`, `[Test`
  - skip 표식: `@Disabled`, `@Ignore`, `.skip(`, `xit(`, `xtest(`, `xdescribe(`, `@pytest.mark.skip`, `@unittest.skip`, `t.Skip(`, `Skip =`
  - 파일 안 첫 테스트 선언보다 앞에 `@Disabled`·`@Ignore`가 있으면 그 파일의 모든 ID를 `skipped`로 본다.
  - 이 판정은 휴리스틱이다. 놓친 경우는 reviewer 대조가 막는다.
- **위치**: `파일경로:줄`. 같은 ID가 여러 곳이면 모두 기록하고, 하나라도 skip이 아니면 `found`.

**`record` 규칙**

- `판정`이 `대상`이고 `found`인 행 → `Pass`, 수행일, 담당자, 위치, 행 지문
- `판정`이 `제외(사유)` → `제외`, 비고에 사유
- `판정`이 `이관(Wnn)` → `이관(Wnn)`
- 범위 밖 기존 행은 건드리지 않는다. 같은 ID의 기존 행은 이번 값으로 덮어쓴다.
- `missing`·`skipped`가 남아 있으면 기록하지 않고 종료 코드 2를 낸다. 하한선 게이트를 통과하지 않은 상태에서 호출된 것이기 때문이다.

**`apply` 규칙**

- `--out`이 `--plan`과 같은 경로면 거부한다. 원본은 읽기만 한다.
- 원장의 `Pass` 행 중 계획서에 같은 테스트ID가 있고 **현재 행 지문이 원장 지문과 같은 행만** `결과=Pass`, `수행일`, `테스트담당자`(매핑한 실명)를 쓴다.
- 지문이 다르면 쓰지 않고 요약의 `재확인 필요`에 넣는다. 계획서에서 사라진 ID는 `계획서에 없음`에 넣는다.
- **쓰기 방식**:
  - 데이터 시트 XML에서 대상 `<row>` 요소의 문자열만 교체한다. 다른 zip 항목과 다른 행은 바이트 그대로 복사한다.
  - 대상 셀은 기존 `s`(스타일) 속성을 유지한 inlineStr로 쓴다. 셀이 없으면 열 순서에 맞춰 넣는다.
  - 데이터 검증·병합·서식은 건드리지 않는다.
- 요약에는 기능별 Pass / 제외 / 이관 / 미착수(계획서 기능 행 중 원장에 없음) / 재확인 필요 / 계획서에 없음 건수를 담는다.

### 2. 파일 형식

**`.dev/{branch-slug}/ut-floor.md`** — 브랜치별 하한선. 재개·단계 단독 실행도 이 파일로 복원한다.

```markdown
# UT 하한선
- 출처: references/REB-단위테스트계획서.xlsx (시트: 단위테스트계획, sha256 앞 12자: 1a2b3c4d5e6f)
- 범위: REB-FN-001
- 생성: 2026-10-12

| 테스트ID | 기능ID | 사전조건 | 입력 | 기대결과 | 사후조건 | 의존성 | 표식 | 판정 | 행 지문 |
|---|---|---|---|---|---|---|---|---|---|
| REB-UT-004 | REB-FN-001 | 신규 프로젝트, 회차 없음 | 필수 헤더 컬럼 1개 누락된 파일 | "헤더 형식 오류" 안내 후 처리 중단 | 해당 파일만 실패기록 | REB-UT-001 | | 대상 | 5e21a0c9 |
```

`판정` 값은 `대상`, `제외(사유)`, `이관(Wnn)` 셋이다. 바꾸는 쪽은 오케스트레이터이고, 사용자 확인을 받은 뒤에만 바꾼다. 셀 안의 `|`는 `\|`, 줄바꿈은 `<br>`로 저장한다.

**`.dev/ut-results/{기능ID}.md`** — 기능별 결과 원장. 기능 커밋에 함께 들어간다.

```markdown
# REB-FN-001 단위테스트 결과 원장

| 테스트ID | 상태 | 수행일 | 담당자 | 테스트 위치 | 행 지문 | 비고 |
|---|---|---|---|---|---|---|
| REB-UT-001 | Pass | 2026.10.12 | bs.koo | src/test/java/.../SourceFileServiceTest.java:42 | a3f9c021 | |
| REB-UT-006 | 이관(W03) | | | | 0b2d77e1 | 태스크 수 가드로 분할 |
```

**`.dev/ut-results/testers.md`** — `| git 이름 | 실명 |` 두 열. gx-test-plan만 갱신한다.

**`.dev/ut-results/export/`** — 반영 사본 출력 위치. 커밋 대상이 아니다.

원장을 `.dev` 아래에 두는 이유가 있다. verify 지문(`codex-fingerprint.py`)은 `.dev`만 인덱스에서 빼고 트리를 계산한다. 그래서 verify 통과 뒤 `.dev` 밖에 원장을 쓰면 트리 지문이 바뀌어 gx-commit·훅 G3·gx-pull-request가 재검증을 요구하고, Codex에서는 커밋이 중단된다.

### 3. gx-tdd 삽입 지점

| 파일 · 절 | 현재 | 변경 |
|---|---|---|
| `phases/phase-setup.md` · 3.1 병렬 수집 | 5개 작업 | 6번째 항목으로 `Read("setup-testplan.md")` 포인터 한 줄. 예산(22,000B, 현재 21,997B)을 맞추려고 같은 파일의 기존 문장을 줄인다 |
| `phases/setup-testplan.md` (신규) | — | ① 계획서 탐지(아래 규칙) ② 기능ID 추출과 ARGS 정리 ③ ID가 없으면 후보 질문 ④ `scope` 실행 ⑤ 연동이 켜졌을 때만 ignore 보강(git `.gitignore`, svn `svn:ignore`: `~$*.xlsx`, `.dev/ut-results/export/`) ⑥ state.md에 `ut-scope` 기록 ⑦ 단계 단독 진입용 절 |
| `phases/phase-setup.md` · Step 7 | state.md 초기화 | `ut-scope` 필드 (연동이 꺼지면 생략) |
| `phases/setup-resume.md` · 0.1 재개 정합성 체크 | 산출물 복원 | `ut-scope`가 있으면 `ut-floor.md`도 복원 대상 |
| `SKILL.md` · 환경 감지 | `--phase` 단독 진입 시 1~7 | 8: `ut-scope`가 있으면 `ut-floor.md`를 쓰고, 없는데 계획서가 탐지되면 `setup-testplan.md`의 단독 진입 절을 따른다 |
| `references/pipeline-state.md` · 진행 상태 추적 | state.md 필드 정본 | `ut-scope: <기능ID,…>` 정의 |
| `phases/phase-requirements.md` · 핵심 모드 분기 | ac.md, AC 3~5개 | 연동이 켜지면 ut-floor의 `대상` 행을 입력으로 쓰고 AC 상한을 하한선을 담는 데 필요한 수까지 완화 |
| `phases/phase-requirements.md` · Step 1 | product-owner 프롬프트 | ut-floor 행과 태그 규칙 주입 |
| `phases/phase-requirements.md` · G-W-T 검증 게이트 | 형식 검사 | UT 태그 검사 추가 (아래 게이트 1) |
| `phases/phase-design.md` · 각 반복 | test-architect 평가 | UT 행의 대용량·시간 조건과 테이블 사후조건을 전달하고, 대역·모의 전략을 testability 평가에 포함시킨다 |
| `phases/phase-implement.md` · Step 0 문서 로드 | design·prd 로드 | `ut-floor.md` 로드 |
| `phases/phase-implement.md` · 1.1 태스크 표 | `AC 매핑` 열 | UT ID를 함께 적음 |
| `phases/phase-implement.md` · 1.15 태스크 수 가드 | 작업 계획으로 분할 | 뒤로 넘긴 AC의 UT는 ut-floor `판정`을 `이관(Wnn)`으로 |
| `phases/phase-implement.md` · Step 2-R | red-writer 프롬프트 | 태스크 AC의 UT 행 원문, 명명 규칙, 의존성 처리 규칙, 문구·사후조건 단언 규칙 |
| `phases/phase-implement.md` · Step 2-V | 태스크 리뷰 | reviewer 프롬프트에 해당 UT 행 |
| `phases/phase-review.md` · Task A | reviewer Part 1 | UT 대조표 요구 |
| `phases/phase-complete.md` · Step -2 다음 | — | **Step -1.5 하한선 게이트** (아래 게이트 2) |
| `phases/phase-complete.md` · Step 0 (핵심 모드) | AC 자가 검증 | UT 행 대조 추가 |
| `phases/phase-complete.md` · Step 0 다음 | — | **Step 0.5 원장 기록**: `record` 실행(`--date`는 실행 시점의 로컬 날짜, `--tester`는 `git config user.name`이고 svn이면 `svn info`의 마지막 작성자가 아니라 사용자에게 1회 확인한 이름). svn이면 Step 1 안내에 원장 파일을 포함 |
| `agents/product-owner.md` | `AC-N → [FR-N]` | 태그 규칙 (아래) |
| `agents/red-writer.md` | 이름은 동작을 설명 | UT 태그가 있으면 이름에 UT ID |
| `agents/test-architect.md` | testability 평가 | UT 조건을 대역 전략에 반영 |
| `agents/reviewer.md` | Part 1은 전달된 AC만 | UT 대조표, 이름 정리 권고 시 UT ID 제거 금지 |

**계획서 탐지**

- 대상: `PROJECT_ROOT` 아래 `*단위테스트계획서*.xlsx`.
- 제외: `~$`로 시작하는 파일, `_결과반영_`이 들어간 파일, `.dev/ut-results/export/`, 빌드 산출물 디렉터리.
- 0개면 연동이 꺼진다. 안내 문구는 내지 않는다(`references/` 부재와 같은 정책).
- 2개 이상이면 어느 파일인지 묻는다. 선택지는 후보 파일들과 "연동 안 함"이다.
- 같은 폴더에 `*기능명세서*.xlsx`가 하나 있으면 기능명 매칭에 쓴다.

**기능ID 추출**

- `scope --out` 목록 JSON으로 계획서의 기능ID 집합을 얻는다.
- ARGS 안의 토큰 가운데 이 집합에 있는 것을 범위로 삼고, ARGS에서 지운 뒤 Step 5 브랜치명 유도로 넘긴다.
- 지우지 않으면 `REB-FN-001`의 `FN-001`이 이슈 키 패턴(`대문자-숫자`)에 걸려 브랜치가 타입 없는 `FN-001`이 되고, gx-commit 타입 파싱이 깨진다.
- `--work` 사용 시에는 plan.md 해당 행의 `요구사항` 열에서 기능ID를 찾는다.
- **ID가 없을 때의 후보 질문**
  - 기능명(기능명세서가 없으면 해당 기능 UT 행의 입력·기대결과)과 요청 문장이 가장 많이 겹치는 기능을 최대 2개 고른다.
  - 선택지는 "후보 1", "후보 2", "연동 안 함"이다. Codex 질문 계약의 선택지 2~3개에 맞춘 것이다.
  - 다른 기능은 자유 입력(Other)으로 기능ID를 받는다.
  - 겹치는 후보가 하나도 없으면 "연동 안 함" 하나만 두지 않는다. 대신 "기능ID 직접 입력"과 "연동 안 함"을 묻는다.
  - 계획서 파일이 3개 이상일 때도 같은 방식이다. 최근 수정 순으로 2개를 고르고, 나머지는 자유 입력으로 경로를 받는다.

**태그 규칙** (product-owner와 core 모드의 오케스트레이터)

- AC 요약 줄 끝에 `[UT: REB-UT-002]`를 붙인다. AC 형식(AC 하나에 G-W-T 하나)은 바꾸지 않는다.
- 입력값만 다르고 나머지 시나리오가 같은 경계 케이스는 AC 하나에 태그를 여러 개 붙일 수 있다(`[UT: REB-UT-002, REB-UT-003]`). 이때 Then에 케이스별 기대값을 모두 적는다.
- Then은 계획서 원문을 복사하지 않는다. G-W-T 모호어 규칙을 따라 구체화한다. 예: "정상 등록" → "회차 1건이 '등록완료' 상태로 저장된다".
- 계획서에 없는 AC를 추가해도 된다. 태그 없는 AC는 gx-tdd 자체 설계분이다.

**red-writer 규칙**

- 테스트 이름이나 표시 이름에 UT ID 원문을 넣는다(`@DisplayName("REB-UT-002 …")`, `it('REB-UT-002 …')`). 하이픈을 쓸 수 없는 식별자만 쓸 수 있는 경우 `REB_UT_002`로 넣는다.
- 태그가 여러 개인 AC는 UT마다 테스트 케이스 하나다. 파라미터화 테스트라면 케이스별 표시 이름에 각 ID를 넣는다.
- `의존성` 열은 테스트 실행 순서가 아니다. 선행 상태를 Given 준비 데이터로 만들고, 선행 기능이 아직 없으면 모의 객체로 대신한다.
- 사후조건과 화면 문구는 "확정한 결정" 표의 규칙대로 단언한다.

## 게이트와 실패 경로

**게이트 1 — G-W-T 게이트 확장 (phase-requirements)**

- 기존 형식 검사를 모두 통과한 뒤 다음을 본다.
  - ut-floor에서 `판정=대상`인 테스트ID가 모두 어떤 AC 태그에 있는가
  - 태그에 하한선 밖의 ID가 없는가 (오타 방지)
- 위반이면 기존 경로대로 1회 재작성한다.
- 그래도 위반이면 사용자에게 묻는다. 선택지는 "직접 수정", "해당 UT 제외(사유 입력)", "중단"이다. 제외를 고르면 ut-floor `판정`을 `제외(사유)`로 바꾼다.
- Codex에서는 현재 모드의 질문 도구로 묻는다. 응답할 사용자가 없는 헤드리스 경로라면 제외하지 않고 중단한다.

**게이트 2 — 하한선 게이트 (phase-complete Step -1.5)**

- 연동이 켜진 세션에서만 실행한다. 순서는 TDD 이행 게이트 뒤, verify 앞이다. 정적 검사라 싸고, 실패하면 verify 실행을 아낄 수 있다.
- `check` 종료 코드가 1이면 `missing`·`skipped` 목록을 보여주고 묻는다. 선택지는 "phase-implement로 돌아가 RED 추가", "제외(사유 입력)", "중단"이다.
- 0이면 verify로 진행한다.
- Codex·헤드리스 규칙은 게이트 1과 같다.
- ut-floor의 출처 sha256이 현재 계획서 파일과 다르면 경고한다. 브랜치 도중 계획서가 교체된 경우다. 이때 범위를 다시 추출할지 묻는다.

**원장 기록 실패**: `record`가 실패해도 기능 커밋을 막지 않는다. 경고하고 다음 `--phase complete`에서 재시도하도록 안내한다. 원장은 증빙 보조물이고, 코드 품질 게이트는 이미 통과했기 때문이다.

**Python 부재**: 헬퍼를 실행할 수 없으면 연동을 끄고 1줄 안내한 뒤 gx-tdd를 계속한다. 게이트 1 이후에 Python이 사라진 경우에는 게이트 2에서 중단하고 안내한다. 하한선을 확인하지 못한 채 원장을 쓰지 않기 위해서다.

## gx-test-plan 스킬

- **역할**: 원장 반영 전용이다. 발화 예: "단위테스트 결과 반영", "테스트 결과 엑셀로", "결과반영 엑셀 만들어줘".
- **절차**
  1. 계획서를 탐지한다(gx-tdd와 같은 규칙).
  2. `.dev/ut-results/*.md`가 없으면 "기록된 결과가 없습니다"로 종료한다.
  3. `apply`를 실행한다. 종료 코드 3이면 매핑 없는 git 이름마다 실명을 묻고 `testers.md`에 저장한 뒤 다시 실행한다.
  4. 사본 경로와 기능별 요약을 보고한다. `재확인 필요`가 있으면 해당 기능을 gx-tdd로 다시 확인하라고 안내한다.
- **사본 경로**: `.dev/ut-results/export/{원본 파일명}_결과반영_{YYYYMMDD}.xlsx`
- **하네스 적응**: SKILL.md에 Codex 안내(`../gx-dev/references/codex-runtime.md`, UTF-8 읽기, 질문 도구 대응)를 둔다.
- **SVN**: 원장과 사본 모두 같은 방식이다. 커밋하지 않으므로 VCS 분기가 없다.

## 공유 규칙 변경

| 파일 | 변경 |
|---|---|
| `.claude/skills/gx-commit/SKILL.md` | 다른-slug 확인에서 `.dev/ut-results/`를 예외로 둔다. 언스테이징 목록에 `.dev/ut-results/export` 추가 |
| `.claude/rules/skill-routing.md` | 결과 반영 발화 → `/gx-test-plan` |
| `.claude/rules/harness-codex.md` | 스킬 수 갱신 |
| 사용자 문서·`CLAUDE.md` 시작하기 | 계획서를 레포에 두면 gx-tdd가 자동 연동한다는 안내, 기능ID 요청 예시 |
| `scripts/lint-consistency.sh` | `setup-testplan.md` 포인터 존재 검사, 바이트 예산 유지 |
| 버전 4곳 + `CHANGELOG.md` | 릴리스 단계에서 한 번 |

**PR #92(gx-visualize)와의 겹침**: gx-commit의 다른-slug 확인 문장과 언스테이징 명령을 두 브랜치가 함께 고친다. 스킬 수 문구도 #92가 먼저 머지되면 19, 아니면 18이다. 나중에 머지하는 쪽이 리베이스하면서 두 예외를 모두 남긴다.

## 엣지케이스 처리 요약

| 상황 | 처리 |
|---|---|
| 계획서 개정으로 같은 ID의 내용이 바뀜 | 행 지문 불일치 → 반영 시 `재확인 필요`, 쓰지 않음 |
| 개정으로 ID가 사라짐 | 반영 요약 `계획서에 없음` |
| 엑셀 재저장(공유 문자열, 서식 런), 시트 이름 변경, 제목 행 삽입 | 읽기 규칙이 모두 처리 |
| 한 기능 UT 7건 vs core AC 상한 | 연동 시 상한 완화, 경계 쌍은 한 AC에 다중 태그 |
| 태스크 수 가드로 분할 | `이관(Wnn)`, 하한선에서 제외, 후속 작업이 채움 |
| 한 기능을 여러 브랜치로 개발 | 각 브랜치는 자기 하한선만 책임. 원장 같은 파일 충돌은 텍스트라 해결 가능 |
| 다른 기능에 의존하는 UT | Given 준비 데이터, 선행 기능 부재 시 모의 객체 |
| 대용량·시간 조건 | design에서 대역 설계. 불가능하면 게이트 1에서 제외(사유) |
| skip된 테스트에 ID만 있음 | `check`의 skip 휴리스틱 + reviewer 대조 |
| 이름만 붙고 단언이 없는 테스트 | 전체 모드 reviewer Part 1, 핵심 모드 Step 0 자가 검증 |
| `--resume`, 컨텍스트 압축 | ut-floor.md 파일에서 복원 |
| `--phase implement`·`--phase complete` 단독 진입 | 환경 감지 8 |
| `--ralph` 전환 | 루프 안에서는 원장 기록 안 함. 복귀 후 `--phase complete`에서 게이트 2와 기록 |
| status.md(FR)와 UT 원장 | 서로 갱신하지 않음. 축이 다르다 |
| Fail | 기록하지 않음. 완료는 verify 통과가 전제라 gx-tdd가 쓰는 값은 Pass·제외·이관뿐이다 |
| 엑셀 잠금 파일 `~$*.xlsx` | ignore 보강, 탐지 제외 |

## 검증 계획

1. **헬퍼 단위 테스트** — `tests/test_de13_scope.py`, `test_de13_check.py`, `test_de13_record.py`, `test_de13_apply.py`. 표준 unittest를 쓰고, 테스트 xlsx는 테스트 안에서 zipfile로 만든다. 회사 산출물을 레포에 넣지 않는다.
   - scope:
     - inlineStr·공유 문자열·서식 런
     - 11열·12열
     - 제목 행, 시트 이름 변경
     - `〃` 같은 기능일 때만 풀림
     - 비기능·`[미확정]` 제외
     - 떨어진 ID
     - 없는 기능ID → 2
     - 행 지문 안정성(공백 차이 무시)
   - check:
     - 원문·밑줄 형식
     - 경계 일치(`REB-UT-0021`)
     - 메서드·클래스 단위 skip
     - 테스트 경로 밖 ID 무시
     - 빌드 디렉터리 제외
   - record:
     - 상태별 기록
     - 범위 밖 행 보존
     - missing 상태에서 거부
   - apply:
     - 대상 셀만 변경(나머지 zip 항목 바이트 동일)
     - 데이터 검증 보존
     - 스타일 유지
     - 지문 불일치 시 미기입
     - 원본 불변
     - `--out == --plan` 거부
     - 매핑 없는 담당자 → 3
2. **실데이터 확인** — REB 계획서로 `scope --fn REB-FN-001`, `apply`를 실행하고 엑셀에서 열어 결과 열·드롭다운이 정상인지 확인한다. 결과는 작업 보고서에만 남긴다.
3. **기존 검사** — `bash scripts/lint-consistency.sh`, `python scripts/sync-codex-resources.py --check`(에이전트 4종 변경 후 동기화), `python -m unittest discover -s tests -p "test_codex_*.py" -v`, gx-commit 변경에 따른 `bash scripts/hook-tests.sh`.
4. **수동 smoke** — 샘플 Spring 프로젝트에 REB 계획서를 넣고 `REB-FN-014 건물별 메모 관리 TDD로 개발해줘`를 실행한다. ut-floor → AC 태그 → 테스트 이름 → 게이트 2 → 원장 → `/gx-test-plan` 사본까지 확인한다. FN-014는 UT 6건에 경계값과 `[가정:2000]`을 함께 갖고 있다. 결과는 수동 검증으로 기록하고 자동 검증으로 표시하지 않는다.

## 범위 밖

- gx-dev 연동, gx-ralph 루프 내부의 원장 기록
- 비기능 행 검증, Fail 기록, 사람이 수행한 시험 결과 입력
- 테스트 결과 리포트(JUnit XML 등) 기반 판정. `@DisplayName`이 리포트에 실리는지가 빌드 도구·버전·설정마다 다르다(미검증)
- gx-pm 쪽 결과 가져오기와 추적매트릭스(AN-05) 갱신
- status.md의 FR과 계획서 기능ID 매핑, gx-context의 xlsx 입력 지원

## 구현 순서

1. 헬퍼와 단위 테스트(scope → check → record → apply 순으로 RED부터)
2. `setup-testplan.md`, phase-setup 포인터와 예산 조정, 환경 감지 8, state 필드, 재개 복원
3. requirements 태그 규칙과 게이트 1, product-owner
4. design·implement·review 연결, red-writer·test-architect·reviewer, codex-roles 동기화
5. complete 게이트 2와 원장 기록, gx-commit 예외
6. gx-test-plan 스킬, 라우팅, 문서, 린트
7. 실데이터 확인과 수동 smoke
