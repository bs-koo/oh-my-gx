# Changelog

## v1.13.3 (2026-07-07) — 스킬 전수 정합성 감사 P0·P1 반영

### Features
- **gx-research 병렬 수집 + 교차 검증 (P3)**: 꼼꼼 모드에서 키워드를 웹/문서 두 그룹으로 나눠 general-purpose 서브에이전트 2개를 병렬 디스패치해 수집(주제 인용 블록 인젝션 방어, 에이전트당 Jina 상한 2회, 실패 그룹은 순차 폴백). Step 3에 교차 검증 절차 신설 — 주요 발견은 독립 출처 2개 이상 확인, 단일 출처는 `(단일 출처)` 표기, 상충 출처는 병기. 빠르게 모드·Task 불가 환경은 기존 순차 흐름 유지
- **정합성 린트 CI (P2)**: `scripts/lint-consistency.sh` 신설 — 감사에서 도출된 불변식 7종(버전 3중 일치, Task 도구명 통일 회귀, refactor 금지 목록 3파일 일치·green 재호출 상한·프로젝트 루트 전달, verify 판별식 키 6파일 존재, 디스패치 이름↔agents/ 대조, 셸 스크립트 CRLF 금지, 훅 문법)을 기계 검사한다. `.github/workflows/lint.yml`로 PR·main push마다 자동 실행. gx-tdd 드리프트 주의 섹션에 기계 검증 범위를 명시
- **훅 기반 verify 게이트 (P1)**: `pre-tool-guard.sh`에 G3 신설 — 현재 브랜치의 `.dev/{branch-slug}/state.md`가 gx-tdd 진행 중 + `verify-status` 미통과이면 `git commit` 시점에 `permissionDecision: "ask"`로 사용자 확인을 요구. 프롬프트 규율(라우팅·스킬 층)과 무관하게 항상 동작하는 결정론적 최종 방어선이며, deny가 아닌 ask라서 문서화된 위험 수용 경로는 유지된다. G2(svn commit 차단)는 실행 주체를 명확화하고 `.dev/trunk/state.md` verify 미통과 시 경고를 덧붙인다. git-workflow·skill-routing의 방어선 서술을 훅 동작과 정합 (시나리오 7종 테스트 통과)

### Fixes
- **서브에이전트 도구명 통일**: gx-lens·gx-tech-debt가 `Agent(...)` 표기로 선언·호출하던 서브에이전트 도구를 플러그인 주류 컨벤션인 `Task(...)`로 통일 (allowed-tools 포함, 나머지 13개 스킬과 정합)
- **RGR 보조 스킬 드리프트 봉합**: gx-red/gx-green/gx-refactor 디스패치 프롬프트에 phase-implement에만 있던 `[프로젝트 루트]` 전달을 추가(에이전트 정의의 필수 입력이나 단독 호출 경로에서 누락), gx-green 재호출 상한(최대 2회) 명시로 단독 호출 무한 재시도 방지, refactor 금지 목록 3중 불일치 통합 — "성능 최적화"를 phase-implement [수행 불가능한 정리]에, "인터페이스 시그니처 변경(프로덕션 호출자 0인 테스트 전용 메서드 제거 예외)"을 gx-refactor 비대상 목록과 Task 프롬프트에 추가하여 agents/refactor-coder.md와 3곳 모두 일치. gx-red의 tdd-iron-law 참조 경로에 플러그인 설치 환경 주석 보강
- **--resume 교차 파이프라인 오인 방지**: gx-dev resume/자동 감지가 `pipeline` 필드 있는 state.md(gx-tdd 산출물)를 후보에서 제외하고 해당 파이프라인 재개 명령을 안내, gx-tdd resume/자동 감지는 `pipeline: gx-tdd` 검증 후에만 재개. 양쪽 phase-setup Step 7에 교차 파이프라인 state.md 덮어쓰기 확인 게이트 신설 (verify 게이트 상태 유실 방지)
- **문서-실체 불일치 정리**: gx-tdd Phase 표의 G-W-T 게이트 오기 정정(Skill gx-context 게이트 → 오케스트레이터 직접 검증), skill-routing "공유 스킬" 문구 정밀화(gx-context는 파이프라인이 호출하지 않는 독립 스킬), git-workflow 보호 브랜치 3종(main/master/develop) 명시 + svn commit 실행 주체(사용자)를 훅 동작과 정합하게 명확화, gx-cross-review에 gx-tdd 관계 명시(description·관계 섹션 — qa-manager 사용이 파이프라인 외부 호출임을 문서화), gx-setup 퀵스타트에 gx-tdd 추가, README 시작 명령 `/oh-my-gx:gx-setup` 정정

## v1.13.2 (2026-07-06) — 2차 리뷰 상한 밖 잔여 항목 정리

### Fixes
- **SVN 경로 verify 우회 방지**: skill-routing 판별에 svn 경로(`.dev/trunk/state.md`) 추가 + "svn은 스킬 층 재확인이 없어 라우팅 분기가 유일한 방어" 명시. git-workflow SVN 커밋 규칙에 gx-tdd 진행 중 `svn commit` 전 verify 게이트 확인 의무 추가
- **phase-complete 쌍둥이 차단 블록 중복 제거**: Step 1의 build/test 실패 처리를 Step -1 차단 처리 포인터로 축소 (동일 절차 이중 서술 해소)
- **드리프트 노트 3건 추가 등재**: state.md 초기화 필드(setup Step 7 정본 ↔ 부트스트랩 골격 부분집합), 무결성 기준선 규약(porcelain·hash·count 3중 위치 + gx-green 의도적 경량판 명시), "수동 수정 재주입" 기록 문구 산재

## v1.13.1 (2026-07-06) — gx-tdd 재감사 반영: 본선 밖 우회로 봉합

### Fixes
- **[HIGH] review 진입 게이트 오중단 수정**: SKILL.md 실행 루프 2a의 "변경 없음" 판정이 unstaged(`git diff --stat`)만 확인해 implement Step 5의 스테이징 이후 **모든 정상 실행이 review 문턱에서 오중단**되던 사전 존재 결함을 staged+unstaged 동시 확인(+svn 분기)으로 수정
- **[HIGH] gx-verify 0개 테스트 통과 차단**: 판정 기준에 "테스트 1건 이상 실행" 추가. "No tests found"류 0개 실행은 통과가 아니라 차단(위험 수용 선택 시 기록)
- **[HIGH] `--phase complete` TDD 이행 게이트**: RGR·리뷰 완료 기록 없는 단독 complete 실행 시 위험 수용 확인 + trust-ledger "TDD 미이행 완료 실행" 기록 의무화. tdd-iron-law의 Iron Law 2 문면도 `--phase` 탈출구를 인정하도록 정합화
- **[MED] 자연어 "커밋" verify 우회 방지**: skill-routing에 gx-tdd 진행 중(verify-gate 미통과) 커밋/PR 의도를 `--phase complete`로 안내하는 분기 추가 + gx-commit에 조건부 verify 경고 게이트 신설 (verify-gate 항목 없는 gx-dev state.md에는 미적용)
- **[MED] porcelain 스냅샷 영속화**: 저장 위치를 `${DEV_DIR}/rgr-t{N}-porcelain.txt` 파일로 확정 (--resume 재개 시 기준선 유지, svn은 `svn status` 사용)
- **[MED] `--phase implement` state.md 부트스트랩**: 환경 감지에 최소 골격 생성 규칙 추가 (기준선 게이트 기록 → 이후 `--phase complete` verify가 로드 가능)
- **[MED] 위험 수용 기록 공백 봉합**: 미해결 Critical "현재 상태로 진행"·"수동 수정" 재주입 경로에 기록 의무 추가, Step 4.1이 quality-reviewer Critical/Important 요약도 trust-ledger에 영속화
- **[LOW] 기타**: verify_refactor에 테스트 수 감소 감지(삭제 방지), hotfix에도 G-W-T 기계 검증 게이트 적용, G-W-T 위험 수용 의미 명확화(구현 제외이지 무테스트 구현 아님), gx-verify 로그 디렉토리 mkdir 보장·차단 시 복귀 경로의 파이프라인/단독 분리, spec-reviewer의 deprecated qa-manager 위임 잔재 제거, 프로젝트 타입명 정합(kotlin-gradle→java-spring), phase-setup 번호 중복·옛 Step 번호 잔재 정리
- **[LOW] gx-dev 동일 결함 동시 수정**: review 진입 "변경 없음" 게이트의 unstaged-only 오판(gx-dev도 implement Step 4가 스테이징을 유지하므로 동일 오중단)과 kotlin-gradle 타입명 표기를 gx-tdd와 같은 방식으로 정합
- **2차 코드리뷰(xhigh 15건) 반영**: ①verify 게이트 키를 state.md 최상위 `pipeline`/`verify-status` 필드로 승격 — 전이 주체(phase-complete Step -1 통과 시 passed, 재진입 시 pending 리셋)와 부트스트랩·setup 초기화를 명시해 "기록 주체 부재로 인한 매 실행 오경보"와 "골격 누락으로 인한 게이트 자기 비활성화"를 해소. ②TDD 이행 게이트를 phase-complete 진입부(Step -2)로 이동 — 모든 진입 경로 커버, hotfix 모드 인지(review 스킵은 정상), pipeline 필드로 gx-dev 이력 구분. ③review 진입 판정을 `git status --porcelain` + `base..HEAD` 커밋 존재로 확장(커밋된 변경·untracked 오중단 해소, gx-dev 동시 수정). ④gx-verify 판정을 단일 순서 결정 목록으로 통합 — gradle 실행 수 확인 수단(test-results XML·UP-TO-DATE 시 --rerun-tasks) 정의, Step 1 위험 수용과의 이중 차단 해소. ⑤gx-pull-request에도 verify 경고 게이트 신설 + skill-routing에 사용자 발화 경계·체이닝 커버·minimal-path 안내(gx-verify→커밋). ⑥test-count를 state.md 태스크 필드로 영속화(resume 복원) + 이전 태스크 test-file-hash 재검증(기존-dirty 테스트 수정 감지). ⑦G-W-T 위험 수용 제외를 prd.md에 표시·유일 AC 제외 시 중단, --phase review 단독은 체이닝 없이 종료(골격 status: completed 갱신). ⑧위험 수용 기록 규약(`### 위험 수용` 섹션) 신설, hotfix 수정 요청 시 게이트 재수행·재승인, 수동 수정 기록 누락 2곳 보완, gx-verify 잔존 문장·"무수정 스킬" 선언 정정, 드리프트 노트 3건 등재

## v1.13.0 (2026-07-06) — gx-tdd 테스트 품질 축 보강 (superpowers 원본 대조 이식)

### Features
- **testing-anti-patterns 이식**: superpowers 원본의 모의(mock) 4대 anti-pattern(모의 동작 테스트·프로덕션 테스트 전용 메서드·이해 없는 모킹·불완전 모킹)을 `gx-tdd/references/testing-anti-patterns.md`로 한국어 이식. red-writer(작성 시 게이트)·quality-reviewer(Important 평가 영역, `[동작불변]` 라우팅)에 연결. red-writer 격리 특화 규칙 추가 — 모의 근거는 설계서 testability 인터페이스가 유일하며, 부족하면 "설계서 인터페이스 불충분"으로 보고
- **신규 경고 차단 게이트**: phase-review mechanical gate가 경고 수를 `warnings-baseline`으로 기록(java-spring/node 추출법 정의, 그 외 타입은 미지원 명시·조용한 0 기록 금지)하고, gx-verify가 Step 0.5(DEV_DIR 자체 계산)로 로드하여 baseline 대비 증가 시 게이트 차단(수정 재실행/위험 수용 선택). baseline 없는 단독 호출은 보고만(기존 동작 유지)

### Fixes
- **green-coder 테스트 수정 금지 (superpowers "Fix code, not test" 이식 누락)**: 절대 규칙·금지 사항에 "테스트가 실패하면 코드를 고치고, 테스트를 고치지 않는다" 추가 + "테스트 결함 의심" 보고 필드 신설. verify_red가 `git hash-object`로 테스트 파일 해시를 기록하고 verify_green이 재해시 비교로 무단 수정을 기계적으로 감지 — 무단 수정은 원복+green-coder 재호출, 결함 보고는 red-writer 재작성으로 라우팅
- **테스트 명령 감지 공백 봉합**: phase-review Step 0-2의 "없으면 건너뛴다"(조용한 스킵)를 AskUserQuestion 폴백 + trust-ledger 위험 수용 기록으로 교체. gx-verify에 "감지 실패 = 게이트 차단이 기본값, 조용한 통과는 Iron Law 3 위반" 절차 신설
- **Good Tests 3기준 주입**: red-writer에 superpowers 원본의 테스트 품질 기준(하나의 동작만·이름이 검증 동작을 설명·실제 코드 우선, 모의는 불가피할 때만) 이식
- **디스패치 이름 접두사 통일**: gx-tdd phase 5종 + gx-red/gx-green/gx-refactor의 `subagent_type` 17곳을 `oh-my-gx:` 접두사 정식 이름으로 통일하고 SKILL.md에 디스패치 이름 규칙 명문화 (접두사형 해석은 dry-run으로 검증 완료). gx-dev·gx-cross-review·gx-lens·gx-tech-debt의 bare 이름은 후속 이슈
- **red-writer 격리 표현 정직화**: "진짜 격리" → "지시 기반 격리"(도구 레벨 차단이 아님을 명시). 출력에 "참조한 파일" 자기신고 필드를 추가하고 verify_red가 프로덕션 소스 참조(오염된 RED)를 검증 후 폐기·재호출
- **코드리뷰(xhigh 15건) 반영**: ①경고 baseline을 phase-implement Step 0.5 "기준선 게이트"(RGR 시작 전 기준 GREEN 확인 + state.md 최상위 필드 기록)로 이동 — 구현 유입 경고가 차단 범위에 포함되고, phase-review Step 0-2가 신설 Step을 건너뛰던 라우팅 단절도 해소(Step 0-3 삭제). ②경고 측정 규약을 gx-verify Step 2로 SSOT화(리다이렉트 캡처·동일 명령·증가 시 로그 원문 대조로 노이즈/캐시 오탐 방지). ③verify_green을 저비용 우선 순서로 재구성 — "테스트 결함 의심" 보고를 해시와 독립 분기로 red-writer 라우팅, `git status --porcelain` 스냅샷 대조로 타 테스트 파일 무단 수정도 감지, 재차 위반 시 사용자 보고. ④테스트 코드 품질 결함의 refactor-coder 처리 근거 신설(검증 강도 유지 조건, 호출자 0 테스트 전용 메서드 제거 허용). ⑤gx-verify에 감지 실패 위험 수용 경로·stale baseline 차단(`status: in_progress` 조건)·detached HEAD 처리 추가, 위험 수용 기록은 오케스트레이터 책임으로 명시. ⑥phase-review Step 0-1/0-2 수정 경로에 테스트 무단 수정 검사 + 테스트 컴파일 에러의 red-writer 라우팅. ⑦hotfix 모드 모의 근거 조건화(AC·기존 테스트 스타일) + "설계서 인터페이스 불충분" 처리 분기 신설. ⑧testing-anti-patterns 참조를 전달 경로(`ANTI_PATTERNS_PATH`)+인라인 폴백으로 변경(플러그인 설치 환경 대응). ⑨allowed-tools에 `Bash(grep *)` 등재. ⑩state.md 스키마에 `warnings-baseline`·`test-file-hash` 반영(--resume 복원 포함). ⑪trust-ledger Write/Append 명시(위험 수용 기록 보존). ⑫gx-green 화이트리스트에 gx-red 등재, 모의 3원칙 명명 충돌 해소

## v1.12.2 (2026-06-23) — gx-tdd TDD 정합성·모호점 정리

### Fixes
- **보조 스킬 호출 관계 명확화 (A)**: gx-red의 부정확한 description("gx-tdd 파이프라인 내부 자동 호출")을 정정. phase-implement는 보조 스킬(gx-red/gx-green/gx-refactor)을 거치지 않고 `red-writer`/`green-coder`/`refactor-coder` 에이전트를 직접 `Task` 디스패치한다는 사실을 gx-tdd SKILL.md "스킬 참조 경로"에 명시. 디스패치 프롬프트가 phase-implement와 보조 스킬 양쪽에 중복 정의되어 있어 발생하는 드리프트 주의 추가
- **비-gradle 프로젝트 검증 권한 갭 (B)**: gx-tdd·gx-dev의 `allowed-tools`에 `npm`/`bun`/`npx`/`pnpm`/`yarn`/`pytest`/`go` 추가. 오케스트레이터 직접 검증(verify_green/refactor, mechanical gate)이 gradle만 화이트리스트에 있어 node·java(gradle) 경로의 권한 프롬프트를 해소(python·go는 config.json projectTypes에 아직 정의되지 않아 mechanical gate가 트리거하지 않으므로 권한만 선반영). 더불어 공유 규칙의 명령 실행 방식을 "PROJECT_ROOT=`./`이면 bare 명령(prefix 매칭) / 비-`./`만 서브셸(매칭 안 되는 기존 한계)"로 정정하여, 서브셸 래핑 시 권한이 매칭되지 않던 잠재 갭을 명시
- **리뷰 결함 처리 경로 통일 (C)**: quality-reviewer 출력("refactor/green 재호출")과 phase-review Step 4 처리("새 AC로 RGR")의 서술 불일치를 해소. 결함을 `[동작결함]`/`[동작불변]`으로 표기하여 일관 라우팅
- **품질 결함의 불필요한 RED 강제 제거 (D)**: 동작 불변 품질 결함(DRY/네이밍/매직넘버/추상화 정리)은 `refactor-coder` 단독(기존 테스트 GREEN 유지, 새 RED 불필요)으로, 동작 결함만 RGR 사이클(RED 선행)로 분기. mechanical gate의 빌드/테스트 실패 처리도 "새 RED-GREEN 사이클"이라는 모순을 "진행 중 GREEN의 연장 / 깨진 기존 테스트가 RED 역할"로 정정. green-coder의 "격리" 용어를 "입력 범위 제한"으로 명확화(red-writer의 코드 차단과 구분)
- **코드리뷰 반영 (critic·Gemini)**: (C 보강) quality-reviewer 출력 형식과 phase-review Task A 프롬프트에 `[동작결함|동작불변]` 마커 슬롯을 추가하여, Step4 라우팅이 실제로 동작하도록 producer↔consumer를 일치시킴(지시만 있고 출력 예시엔 마커가 없던 자기모순 해소). 무표기 Important는 동작결함으로 안전 fallback. (#3) phase-review Step4b의 refactor-coder 단독 호출에 입력(정리 대상=동작불변 항목의 파일:라인+권고) 명시. quality-reviewer의 Minor 분류와 게이팅(비차단) 문구 정리
- **멀티 finder 리뷰 후속 정합 (xhigh)**: security-auditor 출력에 라우팅 마커가 없어 Step4가 보안 결함을 분류 못 하던 갭(동작 변경 여부 분류 규칙 추가, 4c MEDIUM 포함), gx-red 본문의 'gx-tdd가 호출하면 green 진입' 잔존 서술과 gx-green/gx-refactor의 '단독 호출 금지' 정책을 skill-routing과 정합, gx-tdd SKILL.md 요약표·EXECUTION 헤더의 '격리 3에이전트'를 '순차; red-writer만 코드 격리'로 정정(green-coder는 진짜 격리가 아님), phase-review Step4b refactor-coder의 GREEN 선행·입력 전제 명시, Hotfix H3의 green-coder 역할 모순을 RGR(red-writer 선행)로 정정, 드리프트 경고에 SSOT·Step4b 포인터 참조 보완, Step4c 죽은 경로 정리

## v1.12.1 (2026-06-17) — gx-tdd 정합성 수정 및 dev/tdd 문서 명확화

### Fixes
- **gx-tdd 깨진 "구현만" 경량 모드 제거**: phase-implement에 처리 분기가 없어 실동작이 불가능했고, Iron Law 1(실패 테스트 우선)과도 충돌. 설계를 건너뛰는 빠른 경로는 hotfix(경량 PRD + RGR + verify)로 대체
- **gx-tdd SVN 지원 추가**: gx-dev의 svn 분기를 이식 — phase-setup(VCS 확인·베이스 브랜치·작업환경·ignore), phase-implement·review(변경 수집), phase-complete(commit/PR/status.md), 공유 규칙(VCS_TYPE/GIT_PREFIX/DEV_DIR). SVN은 commit/PR을 건너뛰고 `svn commit` 안내로 처리
- **deprecated 에이전트 라벨링**: `coder`·`qa-manager` 설명에 "gx-dev 전용" 명시 (gx-tdd는 red/green/refactor-coder, spec/quality-reviewer 사용)

### Docs
- **dev vs tdd 설명 개편**: README·GitHub Pages에서 "같은 골격"이 아니라 "정반대 접근(설계 우선 vs 테스트 우선)"으로 재프레이밍. 비교표 확장(접근·요구사항·테스트·언제 쓰나), 선택 기준("정답을 자동 테스트로 표현할 수 있고 그래야 하는가") 명문화, FAQ 보강

## v1.12.0 (2026-06-16) — gx-humanizer v4.0: humanize-korean 우수 요소 흡수

### Features
- **gx-humanizer 3모드 체계**: 기존 audit/rewrite에 `strict` 모드 신설. "정밀/꼼꼼히/--strict" 명시 또는 입력 8,000자 초과 시 자동 승급(1줄 고지). audit/rewrite 기본 경량 동작은 그대로 유지
- **strict 검증 에이전트 2종 신설** (opus, 한/영 양국어): `humanizer-fidelity`(의미 보존 감사 — 사실·수치·고유명사·직접인용·인과관계·순서 훼손 탐지, edit 단위 pass/rollback), `humanizer-naturalness`(과윤문·AI티 잔존·장르 이탈 검토, accept/rewrite_round/rollback)
- **strict 오케스트레이션**: 탐지·윤문 → fidelity 감사 → naturalness 검토 순차 파이프라인. 재윤문 루프 최대 2회 후 사람 개입 보고
- **안전장치 흡수**: 변경률 30% 경고 / 50% 강제 중단(어절 기준), Write/Edit 경로 가드(`.humanize/` 하위 제한), 입력=데이터 프롬프트 인젝션 방어
- **산출물·이력 관리**: `.humanize/{run-id}/`(run-id=`YYYY-MM-DD-NNN`) 모드 연동 — 기본은 final.md+summary.md, strict는 단계별 7파일(01_input~05_naturalness+final+summary)
- **patterns-ko 보강**: 장르별 치환 처방표 + 주요 K 패턴 학술 근거 추가 (taxonomy 전수 이식은 후속 과제)
- **유지(회귀 없음)**: 한/영 양국어 패턴(K/E/C), 콘텐츠 6유형 기준, "글에 숨결 불어넣기", audit/rewrite 경량 동작

## v1.11.0 (2026-06-15) — gx-tdd TDD 강제 파이프라인 편입

### Features
- **gx-tdd 스킬 신설**: 기존 `gx-dev`(일반 개발)와 별개로 RED-GREEN-REFACTOR 사이클을 강제하는 TDD 개발 파이프라인을 추가. 6-Phase 구조(setup → requirements → design → implement → review → complete)는 gx-dev와 동일하되 각 단계에 TDD 게이트를 추가
  - requirements: AC를 Given-When-Then 형식으로 강제 (자동 테스트 변환 가능성 검증)
  - design: `test-architect`가 testability score(1-10) 산정, 7 미만이면 재설계
  - implement: 단일 coder 대신 `red-writer → green-coder → refactor-coder` 격리 순차 사이클
  - review: `spec-reviewer`(AC 충족) → `quality-reviewer`(코드 품질) + `security-auditor` 순차 게이트
  - complete: `gx-verify` 게이트(신선한 테스트 실행 증거) 통과 후에만 commit/PR 진입
  - hotfix 경로(`--hotfix`): design·정식 review는 생략하되 RGR 사이클과 verify 게이트는 유지 (급해도 회귀 테스트 선행)
- **TDD 전용 에이전트 6종 추가**: `red-writer`, `green-coder`, `refactor-coder`(구현 RGR), `test-architect`(testability), `spec-reviewer`·`quality-reviewer`(리뷰 2단계). 완료 검증은 `gx-verify` 스킬이 담당
- **TDD 보조 스킬 4종 추가**: `gx-red`, `gx-green`, `gx-refactor`, `gx-verify` (파이프라인 내부 자동 호출 + 명시적 키워드 단독 호출)
- **Iron Law 격리**: `tdd-iron-law.md`를 `.claude/rules`가 아닌 `gx-tdd/references/`에 격리하여 일반 gx-dev 갈래는 TDD 강제의 영향을 받지 않음
- **verify 게이트는 gx-tdd가 조립**: 공유 스킬(`gx-commit`/`gx-pull-request`)은 무수정 유지. gx-tdd의 phase-complete가 `gx-verify → gx-commit → gx-pull-request` 순서를 직접 조립
- **라우팅 추가**: `skill-routing.md`에 "TDD로 개발/테스트 먼저" → `gx-tdd`, "개발해줘" → `gx-dev` 분기 명시

## v1.10.0 (2026-05-14) — gx-research에 insane-search 정수 도입

### Features
- **Phase 0 공식 API 우선 인덱스**: 키워드에 기술/학술/한국 뉴스 신호 단어(`arxiv`, `github`, `hacker news`, `stackoverflow`, `npm`, `pypi`, `wikipedia`, `최근/뉴스` 등)가 포함되면 WebSearch와 **병행** 공식 API를 호출하여 1차 결과 품질을 보강
  - 8개 카탈로그: arXiv Atom, GitHub Search, HN Algolia, Stack Exchange, npm Registry, PyPI JSON, Wikipedia REST(한→영 fallback 1회), Google News RSS
  - 키워드 매칭: lowercase + Unicode NFC 정규화 후 substring 검사 (단어 경계 미요구)
  - 모드 차등: 꼼꼼은 매칭된 모든 카테고리, 빠르게는 최대 2개 (관련도 순)
  - 키워드 URL-encode 필수, Phase 0 응답 실패 시 graceful degrade (Jina 재시도 안 함, ❓로 기록 후 WebSearch 흐름 계속)
- **Jina Reader 재시도 (`r.jina.ai`)**: WebFetch 응답이 차단 판정되면 무인증 Jina Reader로 재시도하여 한국 블로그·기술 매체·일부 SPA 사이트 커버리지 향상
  - 검증 신호: HTTP 4xx/5xx, 응답 < 500자, 차단 시그니처 키워드 7종(`checking your browser`, `ray id`, `captcha`, `access denied`, `verify you are human`, `attention required`, `request blocked`)
  - `cloudflare` 단독 키워드는 검사에서 제외 (정상 페이지 오탐 방지)
  - 호출 상한: 꼼꼼 5회 / 빠르게 3회 per 리서치
  - 429 응답 또는 본문에 `rate limit` 포함 시 서킷 브레이커 작동 (이번 리서치에서 추가 Jina 호출 중단)
  - URL 형식: `https://r.jina.ai/{원본 URL}` (원본 URL을 URL-encode 하지 않고 그대로 path로 붙임)
- **findings.md 템플릿 확장**: "Phase 0 결과" 섹션 추가. 매 실행 덮어쓰기 정책 명시

## v1.9.0 (2026-05-14) — gx-dev·gx-context Q&A를 순차 인터뷰로 전환

### Features
- **순차 질문 루프 도입**: gx-dev(phase-requirements/phase-design)와 gx-context(모드 B·C)의 Q&A를 "배치 변환"에서 "1문 1답 + 무제한 파고들기" 방식으로 전환
  - 에이전트가 출력한 "확인이 필요한 사항"을 질문 큐로 구성하여 1개씩 `AskUserQuestion(questions: [질문 1개])`로 제시
  - 답변마다 명확/모호/결정 의존성/코드 탐색 가능 4분기 평가
  - 모호한 답변은 그 자리에서 파고들기 질문을 큐 앞에 삽입, 큐가 비워질 때까지 무제한 반복
  - 기존 "최대 1라운드 심화 질문" 같은 고정 라운드 제한 제거
- **grill-me 정수 흡수** (mattpocock/skills 참고):
  - **권장 답변 의무화**: 모든 질문에 권장 답변을 options 첫 번째에 `(Recommended)` 라벨로 반드시 제시. 권장 답변 산출이 어려운 주관 영역(gx-context B-2의 Q1·Q3 등, phase-* 일부)은 `예: ...` 후보로 발상 기준점 제공
  - **결정 트리 의존성 처리**: 답변이 후속 질문의 전제·형태를 바꾸면 큐/프레임을 재구성하거나 종속 질문 추가
  - **공유 이해 확인(align) 단계**: 큐/프레임이 모두 해소되면 에이전트 재호출 전에 "Q→A" 요약을 사용자에게 보여주는 정리 확인 단계 삽입. "수정 필요" 시 `Q번호: 새 답변` 패턴 파싱, 패턴 불일치 시 선택형 재질문 fallback
- **파고들기 가이드**: phase-requirements/phase-design에 단계별 파고들기 예시 추가(사용자 규모·비즈니스 목표·대상·정책 vs 기술 선택·트레이드오프·경계·실패 처리)
- **gx-context 모드 C UX 정리**: 문서에서 추출된 확인형(`맞습니다 / 수정 필요`)과 누락된 개방형(`예: ... / Other / 모르겠음`) options를 분리

### Fixes
- gx-context 수칙 섹션의 "필수 질문 답변이 모두 모호하면 1라운드 더 진행한다" 구식 표현 제거
- C-3-2의 "수정 필요" 분기를 개방형 평가 규칙과 통합하여 평가 일관성 확보
- align 단계 표기 통일: `Q1: 문제 → ...` / `Q번호: 새 답변` (phase-* / gx-context 모두 동일)

## v1.8.0 (2026-05-04) — gx-cross-review 스킬 추가

### Features
- **gx-cross-review**: dev 산출물 기반 교차 검증 리뷰 스킬 추가
  - `/gx-dev` 완료 후 단발 호출 전용. PRD/설계서/Trust Ledger/self-check/codemap을 컨텍스트로 주입하여 "약속 대비 충실도"를 검증
  - 기본 `/codex:review`와 차별점: 일반 코드 품질이 아닌 AC 충족 매트릭스 + 설계 범위 이탈 + 신규 위험만 보고. trust-ledger·self-check 기반 중복 차단
  - **advisor 2종 선택**: codex(GPT-5.4 다른 모델 관점) / claude(oh-my-gx 자체 qa-manager + security-auditor를 cross-review 미션으로 호출, omc 의존 없음)
  - **codex 미설치 시**: 자동 설치/인증 없이 안내만 (`npm install -g @openai/codex` + `/codex:setup`)
  - **산출물 부재 fallback**: prd.md/design.md 둘 다 없으면 일반 모드(diff-only)로 graceful degrade
  - **한국어 강제**: prompt에 `<language>` 블록 + 영어 응답 시 한국어 정규화 후처리
  - **자동 수정 금지**: 발견 항목별 AskUserQuestion으로 수정 위임 옵션 제공 (전부 / 일부 선택 / 직접 입력 / 전부 건너뛰기). 승인된 항목만 coder 위임
  - **컨텍스트 폭발 방지**: 우선순위 슬라이싱 규칙 (PRD 수용기준+설계 변경범위+diff 1순위, trust-ledger 2순위, codemap 3순위, references 4순위)
  - 결과는 `${DEV_DIR}/cross-review.md` + 원시 응답 `${DEV_DIR}/cross-review.raw.md` 보존
  - 자연어 트리거: "교차 리뷰", "교차 검증", "cross review", "크로스 리뷰"

## v1.7.0 (2026-04-16) — gx-tech-debt 스킬 추가

### Features
- **gx-tech-debt**: 코드베이스 기술 부채 분석 스킬 추가 (ttutak 플러그인 `tech-debt` 이식)
  - 4가지 유형별 부채 감지: 코드(복잡도·중복·dead code·네이밍) / 아키텍처(순환 의존성·레이어 위반·책임 분리) / 의존성(EOL·outdated·취약점) / 테스트(커버리지·품질·구조)
  - Health Score (100점 만점, A~F 등급) 산출
  - 심각도 × 수정 용이성 × 영향 범위 3축 기반 우선순위 로드맵
  - Java/Kotlin(Gradle), Node(npm), Python(pip) 의존성 분석 + 범용 모드
  - `context/{도메인}/architecture.md`와 연계한 "의도된 구조 vs 실제 구조" 비교
  - `references/` 외부 규격 문서 연동 (시큐어코딩·eGovFrame·API 표준 등)
  - 읽기 전용, `gx-lens`와 역할 분리 (기술 부채 vs 비즈니스 정책)
  - SVN 프로젝트 루트 감지 지원 (`svn info`)
  - 자연어 트리거: "기술 부채", "부채 분석", "부채 확인"

## v1.6.5 (2026-04-13) — gx-dev Phase 완료 요약에 전문 확인 안내 추가

### Fixes
- **Phase 완료 요약에 산출물 전문 경로 명시**: gx-dev 파이프라인의 각 Phase 완료 요약이 `저장: ${DEV_DIR}/*.md`처럼 저장 사실만 알려주어, 사용자가 생성된 산출물을 어디서 확인해야 하는지 안내가 부족하던 문제 해결. phase-requirements(PRD), phase-design(설계서), phase-review(Trust Ledger), phase-implement(자기점검) 네 곳의 요약 출력에 `전문 확인: ${DEV_DIR}/*.md` 문구를 추가하여 사용자가 즉시 원본을 열어볼 수 있도록 개선

## v1.6.4 (2026-04-10) — AskUserQuestion 전수 구조화 및 스킬 강제 강화

### Fixes
- **커밋/PR 스킬 강제 3중 방어**: gx-dev 파이프라인이 길어져 컨텍스트 압축 후 오케스트레이터가 `git commit`/`gh pr create`를 직접 실행하는 문제를 방지. `phase-complete.md` 상단 CRITICAL 경고, `gx-dev/SKILL.md` "커밋/PR 스킬 강제" 섹션, `skill-routing.md` "내부 파이프라인에서도 동일 적용" 섹션 3곳에 명시
- **AskUserQuestion 비구조화 호출 일소**: 플러그인 전체에서 서술형/인라인/YAML 형태로 남아있던 AskUserQuestion 호출을 모두 JSON 스키마(`questions: [{header, question, multiSelect, options}]`)로 변환 (gx-commit, gx-context, gx-setup, gx-research, gx-humanizer, gx-pull-request, gx-lens, gx-dev phases 전반)
- **자유 입력 Other 유도 패턴 통일**: 사용자가 자유 입력해야 하는 질문에서 `"직접 입력"`/`"답변 입력"`/`"주제 입력"` 같은 모호한 메타 라벨을 `"Other로 입력"` + `"Other로 이동해서 ~을 자연어로 입력해주세요"` description으로 통일. 사용자가 라벨을 실제 입력 버튼으로 오인하던 UX 문제 해결
- **모드/VCS 선택 매핑 정합성**: gx-dev 모드 선택(`normal`→`"전체 파이프라인"`)과 gx-setup VCS 선택(`git`→`"Git"`)의 후속 처리 텍스트를 새 label과 일치시킴
- **SVN 비밀번호 수집 제거**: gx-setup에서 SVN 사용자명/비밀번호를 AskUserQuestion으로 수집하던 보안 이슈 제거. 대신 사용자에게 터미널에서 `svn info <URL>`로 사전 캐시하도록 안내
- **중복 규칙 통합**: agents/*.md 9개 파일에 중복 정의된 한국어/이모지/사과 규칙을 `.claude/rules/behavior.md`의 "8. 소통 원칙" 섹션으로 통합. `git-workflow.md`의 커밋 규칙은 `skill-routing.md` 참조로 축약

### Added
- **AskUserQuestion 스키마 규칙 확장**: `questions` 배열 한계를 `1~4개`에서 `1~5개`로 확장 (gx-context B-2 검증 질문 5개 일괄 호출 지원). 자유 입력 가이드 라벨 패턴 명문화

## v1.6.3 (2026-04-08) — AskUserQuestion 스키마 수정

### Fixes
- **AskUserQuestion "invalid tool parameter" 에러 수정**: gx-dev 스킬의 모든 AskUserQuestion 호출 패턴을 실제 도구 스키마(`questions` 배열, `header`, `multiSelect`, `{ label, description }`)에 맞게 수정. 설계/PRD 단계에서 마크다운이 렌더링되지 않고 에러가 발생하던 문제 해결
- **승인 패턴 options 최소 2개 준수**: 기존 "승인" 단일 옵션 → "승인" + "수정 요청" 2개로 변경 (스키마 `minItems: 2` 준수)
- **"직접 입력" 중복 옵션 제거**: UI가 자동 제공하는 "Other"와 중복되던 "직접 입력" 선택지를 모든 phase에서 제거

### Added
- **AskUserQuestion 스키마 규칙 섹션**: SKILL.md에 `questions` 배열 필수, `header` 최대 12자, `options` 2~4개, `preview` 선택 등 스키마 규칙을 명문화

## v1.6.2 (2026-04-03) — Skill 도구 누락 수정 및 코드 미리보기 제거

### Fixes
- **phase-complete Skill 호출 불가 수정**: gx-dev SKILL.md의 `allowed-tools`에 `Skill` 도구가 누락되어 phase-complete에서 `/gx-commit`, `/gx-pull-request` 스킬 호출이 차단되던 버그 수정

### Removed
- **코드 미리보기 기능 제거**: phase-design의 미리보기 선택지, phase-implement의 Step 1-preview 전체, preview-written 분기를 제거. coder agent가 Write/Edit 도구에 접근 가능하여 미리보기 모드에서도 실제 파일 수정을 방지할 수 없는 구조적 한계로 삭제

## v1.6.1 (2026-03-31) — 모든 모드에서 context 동기화 지원

### Features
- **context 최신화 (Step 3-0)**: phase-setup에서 베이스 브랜치 기준으로 context/를 자동 최신화. 작업 브랜치 변경 감지 시 사용자 확인 후 덮어쓰기
- **커밋 기반 status.md 갱신 (경로 B)**: HOTFIX/IMPLEMENT 모드에서 커밋 메시지 ↔ status.md 항목을 대조하여 사용자 확인 후 갱신
- **diff 기반 context 환류**: HOTFIX(diff+경량PRD), IMPLEMENT(diff only)에서도 glossary/architecture 갱신 후보를 추출하여 제안
- **context 자동 커밋 + 조건부 push**: status.md 갱신/환류 반영 시 별도 커밋 생성, context 커밋이 1건 이상일 때만 추가 push

### Fixes
- **HOTFIX+REJECT 보호**: HOTFIX 모드에서 인수검증 REJECT 시 status.md 갱신을 건너뛰도록 분기 규칙 추가
- **--resume context 복원**: 재개 시 context 최신화(Step 3-0) + DOMAIN_CONTEXT 탐색을 독립적으로 재실행
- **SVN 가드**: phase-complete Step 3에 SVN 건너뛰기 명시 (브랜치 기반 커밋 로그 비교 불가)
- **BASE_BRANCH 변수 등록**: SKILL.md 공유 변수 목록에 BASE_BRANCH 추가
- **git diff 명령 수정**: Step 3-0에서 `diff HEAD` → `diff BASE_BRANCH HEAD`로 변경하여 커밋된 context 변경도 감지
- **매칭 알고리즘 명시**: 경로 B에서 FR/BR ID 직접 매칭(우선) + 키워드 매칭(보조) 규칙 추가
- **Step 참조 통일**: --resume의 "Step 3.5" → "Step 3의 5번 항목"으로 정정

## v1.6.0 (2026-03-30) — 병렬 배치 설계 도입 및 승인 UX 개선

### Features
- **architect 의존성 힌트 기반 병렬 배치**: 구현 순서에 `(의존: N, M)` 표기를 도입하여 독립 단계를 병렬 실행 가능하게 함. 기존 레이어 순서 맹목 추종 문제 해결
- **3계층 의존성 분석**: 설계서 힌트(1차) → 파일 잠금(오버라이드) → import 검증(오버라이드) 구조로 안전한 병렬 배치 구성
- **예비 배치 미리보기**: 구현 계획 승인 시 간이 위상 정렬로 배치 구성을 사용자에게 미리 표시

### Improvements
- **승인 UX 간소화**: PRD/설계/구현계획 승인의 AskUserQuestion에서 중복 '직접 입력' 옵션 제거, Other(자동 제공)로 통합하여 2단계 → 1단계로 단축 (4곳)
- **구현 계획 재시도 무제한**: 2회 제한 제거, 사용자가 승인할 때까지 반복하도록 다른 Phase와 통일
- **구현 순서 테이블 정합성**: 헤더를 3컬럼(배치/단계·설명/대상 파일)으로 예시와 일치시킴
- **기존 설계서 폴백**: `(의존:)` 표기가 없는 기존 설계서는 이전 단계에 순차 의존으로 간주하여 --resume 호환 보장

## v1.5.1 (2026-03-25) — gx-dev 구동 안정성 및 브랜치별 산출물 분리

### Features
- **.dev/ 브랜치별 폴더 분리**: `DEV_DIR` 변수 도입으로 `.dev/{branch-slug}/` 형식으로 브랜치별 산출물 격리. 여러 기능을 번갈아 개발해도 PRD/설계서/state가 유실되지 않음
- **복수 작업 resume 선택**: `--resume` 시 `in_progress` 상태 작업이 여러 개면 AskUserQuestion으로 선택 가능

### Fixes
- **implement(경량 구현) 모드 보강**: 산출물 게이트에 implement 모드 예외 추가, phase-implement에 경량 구현 분기 신규 추가, Context Slicing에 coder/qa-manager implement 분기 반영
- **hotfix 인수검증 모순 수정**: phase-complete에서 hotfix가 인수검증을 건너뛴다는 잘못된 노트 제거 (hotfix는 경량 PRD를 생성하므로 인수검증 실행이 맞음)
- **SVN VCS_TYPE 설정 누락**: phase-setup SVN 분기에서 `VCS_TYPE = "svn"` 명시 추가
- **Step 번호 참조 정합성**: SKILL.md의 phase-setup Step 참조를 실제 번호 체계(Step 0~7)와 일치시킴
- **Phase 진행 표현 통일**: Phase 파일의 "phase-X로 진행"을 "다음 Phase로 진행"으로 통일하여 루프 기반 실행과 일관성 확보
- **diff 갱신 독립 Step 분리**: phase-complete의 diff 갱신을 인수검증 블록에서 분리하여 PRD 부재 시에도 실행
- **SELF_CHECK 변수 복원**: phase-review 문서 로드에 self-check.md Read 절차 추가
- **코드 미리보기 연계**: phase-design 승인 후 `preview-written` 플래그로 phase-implement Step 건너뛰기 분기 추가
- **--resume implement 모드 복원**: phase-implement에서 mode 필드 확인 후 Step 1/1.5 건너뛰기 로직 추가

### Improvements
- **AskUserQuestion 구조화**: 전 파일의 평문 AskUserQuestion 11건을 JSON 구조화 형식(question/options/description)으로 변환
- **승인/수정 패턴 통일**: value 네이밍을 `modify` → `input`으로 일관되게 통일
- **PR 머지 규칙 완화**: 머지 금지 규칙 제거, force push 금지만 유지하여 사용자 자율성 확보

## v1.5.0 (2026-03-24) — 스킬 네임스페이스 gx- prefix 추가

### Breaking Changes
- **모든 스킬명에 `gx-` prefix 추가**: `/commit`→`/gx-commit`, `/context`→`/gx-context`, `/dev`→`/gx-dev`, `/humanizer`→`/gx-humanizer`, `/lens`→`/gx-lens`, `/pull-request`→`/gx-pull-request`, `/research`→`/gx-research`, `/setup`→`/gx-setup`
- `/gx` 입력 시 전체 스킬 목록이 자동완성되어 사용성 향상

### Improvements
- **스킬 description 간결화**: 각 스킬의 설명을 한 줄로 정리하여 터미널 표시 가독성 개선
- **네임스페이스 충돌 해결**: oh-my-claudecode, Claude 기본 명령어 등 다른 플러그인과의 스킬명 충돌 방지

## v1.4.1 (2026-03-24) — setup VCS 감지 및 CLI 자동 설치 개선

### Fixes
- **VCS 감지 단순화**: `svn info` 감지를 제거하고 `git rev-parse` 성공/실패로 분기. 실패 시 사용자에게 Git/SVN/없음 선택지 제시. Git 선택 시 `git init` 자동 실행
- **gh CLI 자동 설치**: svn과 동일한 패키지 매니저 자동 설치 패턴 적용. 기존 안내 링크만 표시하던 방식에서 개선
- **winget 최우선 감지**: Windows 10/11 기본 내장 winget을 최우선 패키지 매니저로 추가. 별도 패키지 매니저 없이 gh/svn CLI 자동 설치 가능
- **SVN 인증 단계 추가**: 2단계(인증)에서 `svn info`로 캐시된 자격 증명 확인 후, 실패 시 사용자에게 아이디/비밀번호 입력 요청
- **allowed-tools 보강**: setup 스킬에 winget, choco, scoop, brew, sudo, test 명령 허용 추가

## v1.4.0 (2026-03-23) — SVN 프로젝트 지원

### Features
- **SVN 프로젝트에서도 사용 가능**: `/gx-setup`에서 VCS(Git/SVN)를 자동 감지하고 `config.json`에 저장. 이후 모든 스킬이 VCS 타입에 맞게 동작
  - `/gx-dev`: PRD → 설계 → 구현 → 리뷰까지 동일하게 동작. diff 수집은 `svn diff` 사용
  - `/gx-context`: 레포명 추출과 동기화 모드가 SVN 명령어로 분기
  - `/gx-lens`: 프로젝트 루트 감지가 `svn info`로 폴백
  - `/gx-commit`, `/gx-pull-request`: SVN에서는 미지원 안내 후 조기 종료
- **setup 스킬 VCS 분기**: SVN 프로젝트에서는 gh CLI 대신 svn CLI를 확인하고, GH 인증과 Google Chat 연동을 건너뜀
- **pre-tool-guard SVN 가드**: Claude가 `svn commit`을 대신 실행하지 않도록 훅에서 차단
- **VCS 워크플로우 규칙 분리**: `git-workflow.md`를 Git/SVN 섹션으로 분리

## v1.3.5 (2026-03-23) — dev 파이프라인 스킬 호출 정규화

### Fixes
- **phase-complete 스킬 호출 방식 전환**: commit/PR 생성을 Read 방식에서 `Skill(skill: "oh-my-gx:commit")`, `Skill(skill: "oh-my-gx:pull-request")` 호출로 변경
  - 스킬의 절차, 포맷, allowed-tools를 우회하지 않고 반드시 스킬을 통해 실행
  - pull-request 스킬에 `--background`, `--extra-section` optional args 추가로 dev 컨텍스트 전달 지원

## v1.3.4 (2026-03-19) — Q&A 루프 사용자 승인 방식으로 전환

### Fixes
- **PRD/설계 Q&A 무한 반복 지원**: requirements(max 1), design(max 2) 고정 횟수 제한을 제거하고, 사용자가 "승인"할 때까지 반복하도록 변경
  - 사용자가 충분히 티키타카한 후 확정할 수 있어 PRD/설계 품질 향상
  - "수정 요청" 선택 시 에이전트가 다시 호출되어 처음부터 반복

## v1.3.3 (2026-03-19) — 에이전트 네임스페이스 분리

### Fixes
- **에이전트 프리픽스 충돌 해결**: `.claude/agents/` → `.claude-plugin/agents/`로 이동하여 `oh-my-gx:` 네임스페이스로 인식
  - `oh-my-claudecode:architect` 등 다른 플러그인 에이전트와의 이름 충돌 방지
  - plugin.json에 `agents` 경로 등록

## v1.3.2 (2026-03-18) — PR 알림 중복 발송 방지

### Fixes
- **Google Chat 알림 중복 방지**: `/gx-pull-request` 스킬에서 기존 PR 업데이트(`gh pr edit`) 시에도 알림이 발송되던 문제 수정
  - 신규 PR 생성(`gh pr create`) 시에만 알림을 발송하도록 선행 조건 가드 추가

## v1.3.1 (2026-03-17) — /gx-dev Phase 스킵 방지

### Fixes
- **Phase 스킵 방지**: LLM이 "요구사항이 명확하다", "범위가 작다" 등의 이유로 Phase를 임의 스킵하는 문제를 구조적으로 방지
  - Phase 라우팅을 서술형에서 기계적 for-loop 의사코드로 교체
  - CRITICAL 경고 + 산출물 게이트 (`.dev/prd.md`, `.dev/design.md` 존재 검증) 추가
  - 모드 미결정 시 AskUserQuestion으로 사용자에게 모드 선택 강제
  - Agent 팀 강제 — 외부 Agent(sisyphus-junior 등) 대체 금지

### Features
- **경량 구현 모드**: "구현만" 선택 시 `setup → implement → complete` 경로 (설계/리뷰 생략, 커밋/PR 포함)
- **모드 선택 UX**: 자연어 패턴 미매칭 시 3개 선택지 제시 (전체 파이프라인 / 긴급 수정 / 구현만)

## v1.3.0 (2026-03-16) — references/ 외부 규격 참조 기능

### Features
- **references/ 외부 규격 참조**: `references/` 디렉토리에 외부 규격/표준 문서를 넣으면 dev 파이프라인이 자동 참조
  - Setup: 5번째 병렬 작업으로 `references/` 탐색 + REFERENCES 변수 생성
  - Design: architect가 규격을 반영하여 설계서에 "준수 규격" 섹션 추가
  - Implement: coder가 규격을 준수하며 구현 (전체/배치/hotfix 모드)
  - Review: qa-manager가 규격 위반을 CERTAIN으로 보고, security-auditor가 보안 규격 감사
  - `references/` 없으면 기존과 동일하게 동작 (토큰 소모 없음)
  - `--resume` 시 REFERENCES 자동 복원

### Docs
- CLAUDE.md에 references/ 디렉토리 안내 섹션 추가
- README references/ 사용법 추가
- GitHub Pages references/ 설명 추가

## v1.2.0 (2026-03-16) — research 리서치 스킬

### Features
- **research 스킬 신설**: 웹 검색/문서 분석 기반 도메인 리서치 스킬
  - 인터뷰(주제/결과물/깊이) → 검색 → 검증 → 결과물 생성 워크플로우
  - 종합 리포트 / 비교표 / 핵심 요약 3가지 결과물 형태 지원
  - `/gx-context --from` 연동으로 리서치 결과를 context 문서에 반영 가능
  - `.research/` 디렉토리에 중간 산출물 및 최종 결과물 저장

### Docs
- GitHub Pages research 스킬 섹션 추가
- README research 스킬 사용법 추가
- GitHub Pages UI/UX 개선 및 설명 통일

## v1.1.0 (2026-03-13) — coder 배치 병렬화

### Features
- **coder 배치 병렬화**: 독립적인 구현 단계를 배치로 묶어 병렬 coder Task로 호출
  - 의존성 분석 (파일 잠금 + import 참조) → 위상 정렬 → 배치 배정
  - 배치 모드 coder: 담당 파일만 수정, 개별 빌드 생략, 오케스트레이터가 통합 빌드
  - 배치 간 빌드 검증 + 에러 원인 특정 후 자동 수정
  - state.md 배치 추적 + --resume 호환
- dev 스킬 버전: 1.0.0 → 1.1.0

### Docs
- GitHub Pages 상세 문서 페이지 (index.html) 신규 생성
- README 간결화 + GitHub Pages 배지 링크 추가

### Migration
별도 마이그레이션 불필요. 기존 단일 coder 경로는 동일하게 동작한다.

## v1.0.0 (2026-03-12) — 첫 정식 릴리즈

첫 정식 릴리즈. 7개 스킬 + 9개 에이전트 팀 기반 개발 자동화 플러그인.
