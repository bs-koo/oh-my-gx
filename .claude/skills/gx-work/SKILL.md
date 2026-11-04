---
name: gx-work
description: 프로젝트 파악·작업 계획·기능 개발·버그 수정·진행 상태 조회·작업 재개 요청에 사용한다. 목표·범위·종료점을 정리하고 개발 실행을 gx-tdd로 연결한다.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill]
---

# GX Work — 개발 작업 진행

사용자의 목표·범위·완료점을 정리하고 **이해 → 계획 → gx-tdd 실행**을 연결한다. 이 스킬은 구현 실행기를 만들지 않는다. 한국어로 응답한다.

**하네스 적응**: Claude Code는 `Skill("oh-my-gx:...")`로 호출한다. Codex는 이 파일 위치 기준 [references/codex-runtime.md](references/codex-runtime.md)를 먼저 읽고 대상 스킬의 설치된 `SKILL.md`와 게이트를 수행한다. 도구 이름·모델은 현재 스키마를 따른다. PowerShell 읽기는 `Get-Content -Encoding UTF8`. helper는 확인한 설치 플러그인 루트의 `scripts/gx-work.py`를 사용한다. 소비 프로젝트의 `.claude/rules/`가 설치돼 있다고 가정하지 않는다.

## 진입과 범위

1. **대화의 명시적 요청이 최우선**이다. 원문 목표, 제공 문서, 결정 근거와 종료점을 보존한다. 이미 답한 진행 방식·모델·계획 승인 질문을 반복하지 않는다. 설정·기존 실행 값을 사용하고, 의미 있는 선택이 실제로 미정일 때만 묻는다.
2. 현재 프로젝트 지침과 현재 브랜치의 `.dev/{branch-slug}/state.md`를 읽는다. SVN은 `.dev/.active`를 쓴다. **진행 중 gx-tdd 실행이 있고 구현을 요청했다면 새 파이프라인보다 기존 중단 지점을 먼저 복원**한다. gx-dev 등 다른 pipeline은 `migration-required`로 실행을 멈추고 명시 전환 결정을 받는다. gx-ralph는 `ralph.lock`이 있으면 `loop-active`로 상태만 보고하고, 없어도 `loop-resume-required`로 기존 루프 복귀를 안내하며 두 번째 실행기를 시작하지 않는다. 사용자 목표가 다른 작업이면 혼합하지 말고 별도 작업 여부만 해소한다. `understand`·`plan`·상태 조회는 진행 중 실행이 있어도 읽기 전용으로 종료한다.
3. 새 요청은 아래 결과로 정규화한다. 자연어 의미와 대화의 부정·제한을 함께 읽으며 단어 하나로 라우팅하지 않는다.

| 사용자 목표 | 수행·종료 |
|---|---|
| 프로젝트/도메인 파악, 원인 조사, 상태만 | 관련 코드·context·문서를 읽고 근거·불확실성을 보고한다. 실행·설정 변경 없음 |
| 계획/설계만, 외부 계획 검토 | [계획 계약](references/planning.md)으로 계획하거나 누락·충돌만 검토한 뒤 종료 |
| 기능 구현·버그 수정 | 같은 계획 계약으로 필요한 결정만 보완하고 gx-tdd로 인계. 기본 종료점은 검증된 변경(`verify`) |
| 커밋까지, PR까지 | 명시 요청에 맞춰 `commit` 또는 `pr`까지 인계. 이전 허가는 같은 범위에서 유지 |
| 진행 중 작업 이어서 | 기존 run-id·목표·stop-at·현재 step을 복원하여 gx-tdd 재개 |
| 컨텍스트 등록/동기화만 | `oh-my-gx:gx-context`로 연결하고 종료. 개발로 자동 확장하지 않음 |
| 리뷰만·커밋만·PR만 | 해당 gx-tdd phase 또는 gx-commit/gx-pull-request의 게이트를 수행하고 요청 결과에서 종료 |

이해·계획만 요청한 경우 **stash, checkout, pull, 브랜치/worktree 생성, gx-setup, 빌드·테스트를 실행하지 않는다**. 보고서 저장을 요청하지 않았다면 소비 프로젝트에 계획·state 파일도 만들지 않는다. 계획 작성은 대화 안에서 가능하다. `gx-setup`은 자동 호출하지 않으며 설정의 실제 누락이 필요한 실행을 막을 때만 알려준다.

## 계획과 실행 인계

계획이 필요한 요청에서만 [references/planning.md](references/planning.md)를 읽는다. `--from-plan`은 문서 경로를 가져오는 기능이며 승인 표시가 아니다. 이미 있는 계획을 다시 쓰지 않고 실행에 필요한 부족·충돌만 보완한다. 도메인 context·외부 문서·대화 결정은 출처 포인터로 정규화한다. 사용자가 승인한 범위의 일상적 구현 판단을 추가 승인 단계로 만들지 않는다.

구현 요청이면 [references/handoff.md](references/handoff.md)를 읽고 **한 개의 normalized plan 파일과 handoff 파일**을 만든다. [관련 문서 연결](../gx-context/references/development-sync.md)로 context·요구사항 원장·작업계획의 이번 범위를 대조하고 필요한 최소 연결만 보강한다. 실행 중의 최종 AC 확정·문서 대조·실패 복구는 gx-tdd가 같은 자료를 재사용한다. 전체 context 등록 인터뷰·스캔을 추가하지 않으며, 읽기 전용·명시 문서 금지는 우선한다. 원문·계획 본문을 여러 프롬프트로 복사하지 않고 파일 포인터와 관련 단위 ID만 전달한다:

`Skill("oh-my-gx:gx-tdd", args="--from-plan <정규화 계획.json> --handoff <인계.json>")`

Codex에서는 위 인자와 파일 포인터를 유지하여 gx-tdd의 설치된 절차를 실행한다. 계획 단위의 AC를 gx-tdd가 RGR 태스크로 한 번만 해석한다. 이 스킬에서 RED/GREEN/REFACTOR 단계나 테스트 코드 본문을 미리 작성하지 않는다. 기존 진행 state·pending 질문·verify·보호 브랜치·커밋/PR 게이트는 그대로 유지한다.

자연어 자동 발견은 하네스·설치 상태에 달려 있다. 실제 세션에서 확인하기 전 작동한다고 보고하지 않는다. 발견이 안 되는 환경에서는 `/gx-work <목표>`를 명시 진입점으로 안내한다. 로컬 테스트는 라우팅·계획 데이터 계약만 검증하며 설치 발견·실제 모델·질문 UI의 증거를 대신하지 않는다.
