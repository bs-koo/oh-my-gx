# gx-tdd 유지보수 노트 — 의도적 중복 목록

아래는 무엇이 어디에 중복돼 있고 무엇이 SSOT인지의 목록이다. 스킬·phase·에이전트 정의를 **수정할 때** 읽는다. 파이프라인 실행 중에는 읽지 않는다.

**드리프트 주의**: 아래 정의들이 여러 파일에 **의도적으로 중복**되어 있다(에이전트 자기완결성·라우팅 강제력 목적 — 단일 출처화하면 에이전트/프롬프트가 정의를 못 받아 라우팅이 깨진다). 한쪽을 수정하면 나머지도 함께 갱신해 어긋나지 않게 한다.
이 중 기계 검증 가능한 불변식(refactor 금지 목록 3파일 일치, green 재호출 상한, 프로젝트 루트 전달, verify 판별식 키, 디스패치 이름↔agents/ 대조)은 `scripts/lint-consistency.sh`가 CI(`.github/workflows/lint.yml`)에서 자동 검사한다. 나머지는 여전히 수동 동기화 대상이다.
- **디스패치 프롬프트**(red-writer/implementer — green/refactor 트리오는 단독 스킬 전용): phase-implement.md(Step 2-R/2-I)와 각 보조 스킬(gx-red/gx-green/gx-refactor) SKILL.md에 정의. phase-review Step 4b는 implementer 정리 모드를 디스패치한다.
- **세션 IMPLEMENT 계약**(절대 규칙 5항·수행 불가능한 정리 5항·report 형식 5절): phase-implement.md Step 2-I "세션 IMPLEMENT 절차" ↔ `agents/implementer.md`(`--isolated`·fix 4~5·ralph 경로에서 디스패치되는 절대 규칙·REFACTOR 범위·report 파일 형식)에 중복. 린트 [3/36]이 금지 5항목을 양쪽에서 검사하고, [33/36]이 절차 블록 존재를 검사한다.
- **태스크 리뷰 프롬프트·재리뷰 계약**: phase-implement.md Step 2-V의 reviewer 디스패치 프롬프트(Iron Law·커버리지·불신뢰 문단은 phase-review Task A의 **축약본** — 핵심 문장 `NO QUALITY VERDICT UNTIL SPEC VERDICT IS RENDERED`·`발견 단계의 목표는 커버리지다`는 동일) ↔ `agents/reviewer.md` "태스크 범위 모드" 절(재리뷰 판정 표 형식이 SSOT) ↔ phase-review Task A의 `[태스크 리뷰 유예 Minor]` 절(소비)에 중복. 린트 [34/36]가 세 곳과 핵심 문장 2개·절 순서를 검사한다.
- **마커 분류**(`[동작결함]`/`[동작불변]`): `agents/reviewer.md`가 SSOT이며, phase-review의 Task A 프롬프트·Step 4.4 의사코드에 라우팅 강제를 위해 재명시된다.
- **기계 판정 블록**(`spec_verdict`/`quality_verdict`/`security_verdict` YAML): spec·quality는 `agents/reviewer.md`가 SSOT이며 phase-review 프롬프트에 재명시. security는 공유 에이전트(gx-dev·gx-lens 등도 호출)라 **phase-review Task B 프롬프트가 producer**이고 에이전트 정의는 무수정. 소비는 Step 4.0/SPEC FAIL 처리 (블록 우선 → 산문 폴백 → 상충 시 보수적 판정). 개별 항목 라우팅 마커는 기존 산문 계약 유지. 린트가 쌍 존재를 검사. security는 여기에 더해 **블록·산문 집계가 모두 부재하면 재호출 → 위험 수용(원장 기록)·중단** 계층을 갖는다 (린트 [27/36]).
- **리뷰 발견 단계 커버리지 계약**: 발견은 넓게·필터는 하류에서. `agents/reviewer.md`와 `agents/qa-manager.md` **양쪽 모두**가 커버리지 문단을 갖는다. Codex는 `agents/*.md`를 배포하지 않으므로 gx-tdd·gx-dev의 phase-review 디스패치 프롬프트에도 같은 계약을 재명시한다 — 린트 [28/36]가 4곳을 함께 검사한다.
- **테스트 무결성 규칙**("테스트 파일 수정 금지" + "테스트 결함 의심" 보고 필드): `agents/green-coder.md`·`agents/implementer.md` ↔ phase-implement.md(Step 2-I, verify_red/verify_implement) ↔ gx-green SKILL.md(Step 1~3)에 중복 (4중).
- **테스트 품질 가드**(anti-pattern 요약 + Good Tests 3기준): `agents/red-writer.md` ↔ phase-implement.md(Step 2-R) ↔ gx-red SKILL.md(Step 2)에 중복. 상세 기준의 SSOT는 `references/testing-anti-patterns.md`.
- **UI 가드**(셀렉터 우선순위 + 스타일 assert 금지 + 스냅샷 금지): 위와 같은 3파일에 중복. 상세 기준의 SSOT는 `references/frontend-testing.md`이며, 레이어 분류(동작/표현)는 phase-design의 test-architect 프롬프트가, 하네스 게이트는 phase-implement Step 0.5가 소비한다. 린트 [23/36]이 3중 동기와 소비 지점을 검사한다.
- **참조 파일 자기신고 + 격리 오염 검증**: `agents/red-writer.md`(출력 형식) ↔ phase-implement.md(Step 2-R 출력·verify_red) ↔ gx-red SKILL.md(Step 2 출력·Step 3)에 중복.
- **경고 측정 규약**: `gx-verify` SKILL.md Step 2가 SSOT. phase-implement Step 0.5(baseline 기록)는 포인터 참조만 하므로 gx-verify만 고치면 따라온다.
- **verify 경고 게이트 조건**(`pipeline`/`verify-status`/`verify-fingerprint` 판별): `.claude/hooks/pre-tool-guard.sh`(G3) ↔ `.claude/rules/skill-routing.md` ↔ gx-commit SKILL.md ↔ gx-pull-request SKILL.md에 중복. 판별 키의 SSOT는 이 파일의 state.md 스키마이며, 지문 계산 규약의 SSOT는 이 파일의 "verify 지문" 섹션.
- **도메인 컨텍스트 4요소**(용어·README 핵심·미반영 항목·아키텍처 + 우선순위): gx-tdd/gx-dev phase-setup 3.1이 쌍둥이 producer, phase-requirements(product-owner — 4요소 전부 + FR 인용)·phase-design(architect — 용어·아키텍처만)·phase-complete Step 3(인용 FR 행 매칭)이 쌍둥이 consumer. 각 SKILL.md Context Slicing 표는 파생 사본. 린트 [36/36]이 8파일을 검사한다.
- **review 진입 '변경 없음' 판정**: 이 파일(실행 루프 2a) ↔ gx-dev SKILL.md에 쌍둥이 — 한쪽 보수 시 함께 갱신.
- **프로젝트 타입 폴백 표**: SSOT는 `.claude/config.json`의 projectTypes. gx-verify Step 1·gx-tdd/gx-dev phase-review의 표는 파생 사본(예시)이다. 힌트 카탈로그(`gx-setup/references/project-type-hints.md`)는 제안용으로 config에 종속되며, 경고 카운트(`warningPattern` — gx-verify Step 2 폴백 포함)와 ignore 보강(`artifacts` — phase-setup Step 6)도 이 SSOT를 따른다. agents/architect.md·coder.md의 타입 감지 표와 gx-commit의 아티팩트 패턴 합집합 규칙도 이 SSOT의 파생 소비자다.
- **state.md 초기화 필드**: phase-setup Step 7이 정본이며, `--phase` 부트스트랩 골격(환경 감지 5항)은 그 부분집합 사본.
- **무결성 기준선 규약**(`rgr-t{N}-porcelain.txt`·`test-file-hash`·`test-count`): phase-implement.md(verify_red/verify_implement — porcelain 대조는 테스트 파일 라인 필터, test-count는 오케스트레이터의 focused 직접 실행 결과) ↔ 이 파일(state.md 스키마·--resume 규칙)에 중복. 단독 gx-green SKILL.md는 해시 단독 비교의 **의도적 경량판**(스냅샷·카운트 없음).
- **판정 기록 규약**(Ruling 블록 형식·기본값 표·노출): SSOT는 phase-implement.md "판정 기록 (Rulings)" 절. phase-review 4b/4c(판정 지시)·phase-complete Step 2-1(pr-rulings.md 조립)·gx-pull-request SKILL.md(`--extra-section`의 Rulings/Deferred 무요약 규칙)이 소비한다. 린트 [35/36]가 규약 절·폐지된 질문 3곳 부재·기록 지시·PR 노출을 검사한다.
- **"수동 수정 재주입" 기록 문구**: phase-review(2곳)·phase-complete(Step -1)에 산재 — 문구 변경 시 함께 동기화.
- **모델 프로파일 규칙**(결정 우선순위 5단계·eco 하향 대상·프로파일 질문 포함 규칙): gx-dev SKILL.md ↔ 이 파일의 "모델 프로파일" 공유 규칙이 쌍둥이 (하향 대상만 파이프라인별로 다름 — dev: design-critic·coder / tdd: design-critic·test-architect·reviewer. architect 유지는 공통 불변) ↔ 각 phase-setup Step 1.5. 파생 사본은 spec·guide·glossary·CHANGELOG. 린트 [14/36]이 키 문구와 opus 집합↔하향 목록 대조를 검사한다.
- **ralph 전환 eco 미지원 경고**(`"ralph 루프는 모델 프로파일(eco)을 아직 지원하지 않습니다 — 반복은 GX_RALPH_MODEL 미지정 시 에이전트 기본 모델(표준)로 실행됩니다."`): gx-dev·gx-tdd phase-implement.md의 gx-ralph 전환 절(--ralph)에 동일 문구 중복 — 한쪽 수정 시 함께 갱신 (린트 미검사, 수동 동기화).
- **gx-ralph opt-in 규칙**(RALPH 추출 트리거·RALPH 우선순위 규칙(svn 우선 배제/자연어 RALPH+선판정 모드/플래그 `--ralph`+자연어 트리거)·Step 3 모드 질문 생략 규칙·`--ralph` 플래그 충돌 검증): gx-dev SKILL.md ↔ 이 파일 쌍둥이. phase-setup Step 7의 `flags` 기록 기준(무시된 RALPH 미기록)과 phase-implement 전환 절(방어 조건 — `--resume`은 비방어)도 dev/tdd 쌍둥이. 린트 [11/36]이 전환 절 헤더·핵심 규칙 문구 존재를 두 파이프라인에서 대조한다.
- **fix 라운드 상한**: 파이프라인 phase-implement `라운드 5` ↔ 단독 gx-green SKILL.md `최대 2회` — **의도적 분기**다 (단독 스킬은 fix loop 없이 현행 상한 유지). 린트 [3/36]이 각각을 검사한다.
