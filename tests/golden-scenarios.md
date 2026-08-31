# 골든 시나리오 체크리스트

릴리스 전 수동 점검용 행동 회귀 시나리오. `scripts/lint-consistency.sh`(정적 불변식)가 잡지 못하는 **모델 행동 계층**의 회귀를 검증한다.

사용법: 스테이징 프로젝트(또는 임시 저장소)에서 각 시나리오의 픽스처를 만들고, Claude Code 세션에서 트리거를 입력해 기대 동작을 확인한다. ★는 자동화 후보 — 회귀가 반복 관찰되면 headless(`claude -p`) CI로 승격한다.

## 픽스처 준비 (S1·S2·S3·S8 공통)

verify 미통과 gx-tdd 상태:

```bash
mkdir -p .dev/{branch-slug}    # branch-slug = 브랜치명의 '/'를 '-'로 치환. svn은 .dev/{slug} (.dev/.active가 가리킴, 없으면 .dev/trunk 폴백)
printf 'pipeline: gx-tdd\nstatus: in_progress\nverify-status: pending\n' > .dev/{branch-slug}/state.md
```

## 시나리오

| ID | 전제 (픽스처) | 트리거 | 기대 동작 | 방어층 |
|----|--------------|--------|----------|--------|
| S1 ★ | verify 미통과 state.md + 작업 브랜치 | "커밋해줘" | 커밋 직행 없이 verify 게이트 안내 (`oh-my-gx:gx-verify` 또는 `--phase complete`). 위험 수용을 명시적으로 고집할 때만 진행 + 결과 보고에 "verify 미통과 커밋" 명시 | skill-routing → gx-commit 내부 게이트 → 훅 G3(ask) |
| S2 | S1과 동일 | "PR 올려줘" | 동일 경고. 진행 시 PR Checklist에 "verify 미통과 PR" 명시 | skill-routing → gx-pull-request 내부 게이트 |
| S3 | gx-tdd state.md(in_progress) 있는 브랜치 | `/gx-dev --resume` | 재개 후보에서 제외 + `/gx-tdd --resume` 안내. 역방향(gx-dev state에서 `/gx-tdd --resume`)은 "gx-tdd 파이프라인이 아닙니다" 안내 | phase-setup Step 0 파이프라인 식별 |
| S4 ★ | main(또는 master/develop) 체크아웃 | `git commit` 실행 | 훅 deny — "작업 브랜치를 먼저 생성하세요" | 훅 G1 |
| S5 | RED 상태 없음 (실패 테스트 없음) | `/gx-green` 단독 호출 | "GREEN 단계는 RED 상태가 선행되어야 합니다" 중단 | gx-green Step 1 |
| S6 | GREEN 상태 | gx-refactor 진행 중 "동작도 조금 바꿔줘" | 거부 + "새 RED 단계로 진입하세요" 안내 | gx-refactor Iron Law |
| S7 | gx-tdd 파이프라인 진행 중 | "설계는 건너뛰고 구현부터 해줘" | Phase 스킵 거부 (core 모드/`--phase`만 예외) | tdd-iron-law Iron Law 2 |
| S8 ★ | vcs=svn + `.dev/.active`가 가리키는 `.dev/{slug}/state.md` verify 미통과 (포인터 없으면 `.dev/trunk` 폴백) | Claude가 `svn commit` 실행 시도 | 훅 deny + "verify 게이트 미통과 (.dev/{slug}/state.md)" 경고 문구 포함 | 훅 G2 |
| S9 | gx-tdd implement/review 진행 관찰 | (관찰 항목) | deprecated 에이전트(coder/qa-manager) 미호출 — red/green/refactor-coder·spec/quality-reviewer만 디스패치 | gx-tdd Agent 팀 강제 |
| S10 | spec/quality/security 리뷰 각 1회 완료 | (관찰 항목) | 각 출력 마지막에 `spec_verdict`·`quality_verdict`·`security_verdict` YAML 블록 존재 + verdict/집계가 산문과 일치 | phase-review Step 2.1/4.0 |
| S11 ★ | 일반 프로젝트 | `/gx-dev {소형 변경}, 구현만 해줘` | 핵심 모드(core) 라우팅 — ac.md 작성 + AC 확인 질문 1회 → 구현 → **빌드·테스트 Gate 실행** → summary.md 기록 → 커밋/PR. Gate 없이 complete 진입하면 회귀 | gx-dev 의도 파싱 → phase-core Step 2 |
| S12 | 일반 프로젝트 | `/gx-dev {버그} 긴급 수정해줘` | 핵심 모드 라우팅 — AC를 재현 조건 형식으로 작성 + **확인 질문 1회 실행**(생략 없음), Gate 필수. product-owner 디스패치 0회 | gx-dev 의도 파싱 → phase-core Step 0/0.5 |
| S13 | 구 버전 세션 state.md(`mode` 필드 존재 + `all`/`core`가 아님 — 예 `mode: hotfix`, in_progress) | `/gx-dev --resume`, `/gx-tdd --resume` | 재개 거부 — "구 버전(v1.18.0 미만)에서 생성되어 재개할 수 없습니다. `/gx-{dev\|tdd} {작업}`으로 새로 시작." 안내 후 종료 (dev·tdd 동일). **단 `mode` 필드가 없는 세션(v1.18.0 `--phase` 골격)은 오탐 거부하지 않고 정상 재개** | phase-setup Step 0 구 버전 세션 방어 |
| S14 | 일반 프로젝트 | `/gx-tdd {버그} 긴급 수정해줘` | 핵심 모드 라우팅 — 오케스트레이터가 ac.md(G-W-T)를 직접 작성 + **G-W-T 게이트 통과** + 확인 1회 → **RGR 사이클 유지** → H1~H4 긴급 감사 → verify → AC 자가 검증. product-owner 디스패치 0회, RGR 생략하면 회귀 | gx-tdd phase-requirements core 분기 → phase-implement |
| S15 | 일반 프로젝트 | `/gx-dev --eco {기능}` (전체 모드 선택) | 에코 프로파일 적용 — state.md `model-profile: eco`, coder 디스패치에 `model: "sonnet"` 오버라이드 관찰 (design-critic은 선택적 단계 — **디스패치된 경우** 동일 오버라이드). **architect는 오버라이드 없이 opus 유지**, sonnet 에이전트 무변경. 게이트·Phase 구성은 표준과 동일 | phase-setup Step 1.5 → SKILL 공유 규칙 "모델 프로파일" |
| S16 | config.json `modelProfile: "eco"` | `/gx-tdd {기능}` (질문 경로) / `--standard` 지정 / `--eco --standard` 동시 지정 | 질문 경로 → 모드·프로파일 질문이 **한 AskUserQuestion 호출**에 함께 제시되고 "에코 (현재 설정)"이 첫 옵션 — 답변이 최종 결정. `--standard` → 프로파일 질문 생략·이번 실행만 표준. `--eco --standard` 동시 → 충돌 에러 후 중단 | Step 3 2질문 + MODEL_PROFILE 결정 우선순위 + 플래그 충돌 검증 |
| S17 | 일반 프로젝트 | `/gx-tdd --eco {기능}` (전체 모드 선택) | 에코 프로파일 적용 — state.md `model-profile: eco`. **design-critic·test-architect·quality-reviewer 디스패치에 `model: "sonnet"` 오버라이드 관찰** (design-critic·test-architect는 design phase, quality-reviewer는 review phase — 디스패치된 경우). **architect는 오버라이드 없이 opus 유지**. spec-reviewer·security-auditor·red/green/refactor-coder는 표준에서도 sonnet이라 무변경. RGR·verify·G-W-T·testability 게이트는 표준과 동일 | phase-setup Step 1.5 → SKILL 공유 규칙 "모델 프로파일" (gx-tdd 하향 3종) |
| S18 | `projectTypes` 등록된 git 프로젝트 | `/gx-tdd 랄프로 알림 임계값 검증 개발해줘` | 모드 질문 생략(all 확정) — 프로파일 질문만 제시(미확정 시) → requirements·design 정상 → Step 0.5 기준선 게이트 통과 후 질문 없이 `Skill("oh-my-gx:gx-ralph")` 호출·파이프라인 종료. state.md `flags`에 `--ralph` 기록. "랄프로 이어서 해줘"는 RESUME이 우선하고 RALPH 무시 안내(flags에 미기록). design 승인 후 세션을 끊고 `--resume`하면 flags의 `--ralph`가 복원되어 Step 0.7에서 그대로 전환(대화형으로 바뀌면 회귀). `/gx-tdd --ralph 긴급 수정해줘`는 에러 후 중단 | 의도 파싱 RALPH 우선순위 규칙 + Step 3 모드 질문 생략 규칙 → phase-setup Step 7 flags → phase-implement Step 0.7 |
| S19 ★ | 동일 | `/gx-tdd 알림 임계값 검증 개발해줘` (전체 모드 선택) | implement 진입 시 AskUserQuestion 없이 Step 1 태스크 분해로 직행 — "구현 방식" 질문이 뜨면 회귀 (v1.23.0 격하). gx-dev 전체 모드도 동일하게 설계 확정 후 바로 구현 | phase-implement Step 0.7 flags 판정 (dev: "gx-ralph 전환" 절) |
| S20 ★ | `.dev/plan.md`에 W01(도메인 재고관리, 의존 없음, 상태 대기) + `context/재고관리/` 존재 | `"W01 시작해줘"` (자연어) | 계획에 W01 행이 있으므로 작업 참조로 확정. plan.md 행에서 도메인·요구사항을 주입 — 도메인을 되묻지 않고, `context/재고관리/`만 로드(레포 매칭으로 다른 도메인을 함께 읽으면 회귀). 브랜치명이 `작업` 열에서 생성되고 **이슈 키 추출을 거치지 않음**(`W01` 브랜치가 생기면 회귀). 착수 시 `작업 위치`·`상태: 진행` 기록 후 베이스 브랜치로 `docs: [plan] W01 착수` push. state.md에 `work-id: W01` | phase-setup 3.0.5 → Step 5 --work 분기 |
| S21 | S20 상태에서 구현·리뷰 완료 | `/gx-tdd --phase complete` | plan.md 행이 `완료`로 갱신되고 `docs: [plan] W01 완료` 커밋 — `--phase complete`는 DOMAIN_CONTEXT가 비어 있으므로, 갱신이 일어나지 않으면 Step 3 종속 회귀 | phase-complete Step 3.5 (독립 판정) |
| S22 | `.dev/plan.md`에 W02(의존 W01, W01은 대기 상태) | `/gx-tdd --work W02` | 선행 미완료 경고 + AskUserQuestion 확인 — 경고 없이 진행하면 회귀 | phase-setup 3.0.5 의존 확인 |
| S23 | vcs=svn + `.dev/.active`가 slug를 가리킴 + plan.md에 그 slug가 `작업 위치`인 행 | 완료 절차 진행 | 브랜치 없이 `.dev/.active` slug로 행을 찾아 `완료` 갱신 + 커밋 대신 사용자 안내 (git 전용 Step 3은 건너뛰어도 plan 갱신은 수행) | phase-complete Step 3.5 svn 분기 |
| S24 | `--work W01 --ralph`로 AC 3건 원장 생성, 1건만 통과 | ralph 반복 1회 종료 | plan.md 행이 **`진행` 유지** — `완료`로 바뀌면 조기 완료 회귀. 3건 모두 통과한 반복에서만 `완료` + 커밋 | gx-ralph-iterate Step 5.5 선행 조건 |
| S25 | `.dev/plan.md` **없는** 프로젝트 | `"W01 화면 정렬 버그 고쳐줘"` | 작업 참조로 오인하지 않고 일반 요청으로 처리 — "작업 계획이 없습니다" 안내가 뜨거나 중단되면 회귀 | SKILL.md WORK 추출 규칙 (plan.md 실존 조건) |
| S26 ★ | `.dev/plan.md`에 W00(완료)·W01(진행)·W02(대기)가 있는 상태 | `/gx-context 재고관리 --from requirements/추가요구사항.md` | 기존 행 보존 — W00은 `완료`, W01은 `진행` 유지, W02만 재조정 대상. 새 작업은 뒤에 추가. **W00·W01 상태가 `대기`로 돌아가거나 행이 사라지면 회귀**(Write로 덮어쓴 것) | gx-context C-5-5 저장 분기 → C-5-6 보존 규칙 |
| S27 | W02(대기, FR-7~9)·W05(대기, FR-25~26)가 있고 추가 요구사항에서 FR-25~26이 삭제되고 FR-31이 W03 범위에 들어감 | `/gx-context {도메인} --from 추가요구사항.md` | 유지/겹침/폐기 판정 제시 — W03은 요구사항 범위 확장(새 행 생성이 아님), W05는 `폐기`(행 삭제가 아님). W05에 의존하는 행이 있으면 함께 경고 | gx-context C-5-6 판정 + C-5-5 저장 후 검증(스크립트 부재 시 인라인 확인) |
| S28 | `.dev/plan.md`에 W05가 `폐기` 상태 | `"W05 시작해줘"` | "폐기된 작업입니다 — 계획을 확인하세요" 경고 + 진행 여부 확인. **경고 없이 그대로 개발이 시작되면 회귀** (`작업 위치`가 `-`라 중복 착수 경고에는 걸리지 않는다) | phase-setup 3.0.5 Step 8 상태 확인 |
| S29 | `--work W01`로 시작해 Step 2.3 stash pop 충돌로 중단 (브랜치는 생성됨, plan.md는 `대기`) | `/gx-tdd --resume` | 착수 기록 보정이 실행되어 행이 `진행`·`작업 위치`가 채워지고 `docs: [plan] W01 착수` 커밋 + push. **`대기`로 남으면 회귀** — 재개 경로는 Step 5를 거치지 않으므로 여기서 못 잡으면 영영 안 남는다 | phase-setup 착수 기록 보정 절 |
| S30 | 원격이 있는 저장소에서 `--work W01`로 신규 브랜치 생성 | Step 5.5 진행 | `git push -u origin {브랜치}`가 실행되어 원격 브랜치가 생성됨. **`-u` 없이 push해 `no upstream branch`로 실패하면 회귀** — 다른 팀원의 `ls-remote` 중복 감지가 무력화된다 | phase-setup Step 5.5-2 |
| S31 | vcs=svn + `work-id`가 있는 `status: completed` state.md에 새 작업으로 재진입 | `/gx-tdd {새 요청}` | plan.md 행이 `완료 → 진행`으로 되돌아가되 **커밋하지 않고 사용자에게 안내**. `svn commit`을 시도하면 훅에 차단되어 되돌림 자체가 실패하므로 회귀 | phase-setup Step 7 되돌림 svn 분기 |
| S32 | `.dev/plan.md`에 W01이 있고 진행 중 state.md 존재 | `"W01 이어서 해줘"` | 중단 없이 재개. "재개는 state.md의 work-id로 문맥을 복원합니다" 안내 후 진행. **`--work`와 `--resume` 충돌 에러로 멈추면 회귀** (자연어는 양보, 명시 플래그는 에러) | SKILL.md 자연어 WORK + RESUME 판정 |
| S33 | `.dev/plan.md`에 W01(진행)이 있고 구현·리뷰가 끝난 상태 | `/gx-tdd --work W01 --phase complete` | state.md에 `work-id: W01`이 기록되고 그 행이 `완료`로 갱신됨. **`--work`가 무시되어 아무 갱신도 없으면 회귀** — 이 경로는 phase-setup을 건너뛰므로 3.0.5가 실행되지 않는다 | SKILL.md 환경 감지 work-id 항목 |

## 기록

점검 결과는 릴리스 PR 본문에 `골든 시나리오: N/27 통과 (미통과: ID)` 형식으로 기록한다. 미통과 시나리오는 원인(문서 회귀/모델 행동/환경)을 구분해 이슈로 남긴다.
