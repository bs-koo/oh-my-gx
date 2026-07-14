# 골든 시나리오 체크리스트

릴리스 전 수동 점검용 행동 회귀 시나리오. `scripts/lint-consistency.sh`(정적 불변식)가 잡지 못하는 **모델 행동 계층**의 회귀를 검증한다.

사용법: 스테이징 프로젝트(또는 임시 저장소)에서 각 시나리오의 픽스처를 만들고, Claude Code 세션에서 트리거를 입력해 기대 동작을 확인한다. ★는 자동화 후보 — 회귀가 반복 관찰되면 headless(`claude -p`) CI로 승격한다.

## 픽스처 준비 (S1·S2·S3·S8 공통)

verify 미통과 gx-tdd 상태:

```bash
mkdir -p .dev/{branch-slug}    # branch-slug = 브랜치명의 '/'를 '-'로 치환. svn은 .dev/trunk
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
| S7 | gx-tdd 파이프라인 진행 중 | "설계는 건너뛰고 구현부터 해줘" | Phase 스킵 거부 (`--hotfix`/`--phase`만 예외) | tdd-iron-law Iron Law 2 |
| S8 ★ | vcs=svn + `.dev/trunk` verify 미통과 | Claude가 `svn commit` 실행 시도 | 훅 deny + "verify 게이트 미통과" 경고 문구 포함 | 훅 G2 |
| S9 | gx-tdd implement/review 진행 관찰 | (관찰 항목) | deprecated 에이전트(coder/qa-manager) 미호출 — red/green/refactor-coder·spec/quality-reviewer만 디스패치 | gx-tdd Agent 팀 강제 |
| S10 | spec/quality/security 리뷰 각 1회 완료 | (관찰 항목) | 각 출력 마지막에 `spec_verdict`·`quality_verdict`·`security_verdict` YAML 블록 존재 + verdict/집계가 산문과 일치 | phase-review Step 2.1/4.0 |
| S11 ★ | 일반 프로젝트 | `/gx-dev {소형 변경}, 구현만 해줘` | LIGHT 모드 라우팅 — ac.md 작성 + AC 확인 질문 1회 → 구현 → **빌드·테스트 Gate 실행** → summary.md 기록 → 커밋/PR. Gate 없이 complete 진입하면 회귀 | gx-dev 의도 파싱 → phase-light Step 2 |
| S12 | 일반 프로젝트 | `/gx-dev {버그} 긴급 수정해줘` | LIGHT 긴급 프리셋 — AC 확인 질문 **생략**(ac.md 기록은 유지), Gate는 생략 없이 실행. product-owner 디스패치 0회 | gx-dev 의도 파싱 → phase-light Step 0.5 |
| S13 | 구 모드 state.md(`mode: hotfix`, in_progress) | `/gx-dev --resume` | "구 모드 세션을 라이트 모드로 전환하여 재개" 안내 + prd.md를 ac.md 대용으로 사용 (재작성 없음) | phase-setup Step 0 레거시 마이그레이션 |

## 기록

점검 결과는 릴리스 PR 본문에 `골든 시나리오: N/13 통과 (미통과: ID)` 형식으로 기록한다. 미통과 시나리오는 원인(문서 회귀/모델 행동/환경)을 구분해 이슈로 남긴다.
