# Codex 네이티브 호환 보강 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex 소비 프로젝트에서 보호 게이트, 역할 기반 스킬, 네이티브 무인 실행을 검증 가능한 단위로 복구한다.

**Architecture:** 기존 Claude 스킬·역할·가드는 공통 원본으로 유지하고 Codex의 입력/출력/실행 경계만 어댑터로 분리한다. A/B/C의 독립 계획을 순서와 합격 기준으로 연결한다.

**Tech Stack:** Markdown, Bash/Git Bash, Python 3.10+ 표준 라이브러리, Node, Codex CLI 0.154.0.

**Spec:** `docs/superpowers/specs/2026-09-14-codex-native-compat-design.md`

## Global Constraints

- 지원 검증 기준은 Codex CLI 0.154.0이다. 더 낮은 버전은 호환을 보증하지 않는다.
- Windows PowerShell + Git Bash, Linux Bash를 필수 검증 환경으로 둔다. macOS는 추가 검증 전 미측정으로 표시한다.
- Python 3.10 이상 표준 라이브러리와 기존 Bash/Git/Node를 사용한다. 새 런타임 패키지는 추가하지 않는다.
- `.claude/config.json`은 하네스 공통 프로젝트 데이터로 유지한다. 이름 변경이나 설정 마이그레이션은 하지 않는다.
- 구현 브랜치에서 작업하고 기존 미커밋 변경을 임의로 스테이징·되돌리기·삭제하지 않는다. 커밋은 gx-commit 절차를 따른다.
- 전역 설치·훅 신뢰·모델·권한을 진단 명령에서 변경하지 않는다. 신뢰 우회·샌드박스 해제 플래그를 러너에 추가하지 않는다.
- 문서와 커밋 메시지는 한국어로 작성한다. 이모지는 새로 추가하지 않는다.

## 구현 계획 구성

| 순서 | 계획 | 독립 결과 | 의존성 |
|---|---|---|---|
| 1 | [A: 훅·커밋 보호](2026-09-14-codex-hooks.md) | Codex 판정/경로/기록 계약 및 스킬 가드 | 없음 |
| 2 | [B: 역할·설치](2026-09-14-codex-skills.md) | 자기완결적인 스킬 리소스와 setup | A의 기록·게이트 규약 |
| 3 | [C: 네이티브 실행](2026-09-14-codex-runners.md) | Codex Ralph·review 실행 및 종단 검증 | A/B |

현재 브랜치에는 기존 WIP가 있다. 구현 시 기준으로 삼을 WIP를 먼저 확인한다. HEAD만 새 worktree로 옮기면 감사 대상 1.32.0 변경과 미추적 설치 스크립트가 누락될 수 있다. 새 worktree가 필요하면 using-git-worktrees 지침에 따라 승인된 기준 파일을 보존한 뒤 실행한다. 이 계획 작성 단계에서는 브랜치·기존 파일을 바꾸지 않는다.

## 파일 책임

| 새 파일/디렉토리 | 책임 |
|---|---|
| `.claude/hooks/codex_hook.py` | Codex guard/capture 진입, 지원되는 판정 출력 |
| `scripts/codex-install-hooks.py` | 절대경로 JSON 렌더링·비파괴 병합 |
| `scripts/sync-codex-resources.py` | 역할/템플릿 생성과 드리프트 확인 |
| `gx-dev/references/codex-runtime.md` | 실제 도구 매핑·질문·역할·셸 지침 |
| `gx-dev/references/codex-roles/` | 편집하지 않는 역할 본문·티어 인덱스 |
| `gx-setup/references/config.template.json` | 소비 프로젝트의 설정 생성 입력 |
| `scripts/codex-fingerprint.py` | 실제 Git 객체 DB 쓰기 없는 코드 지문 |
| `scripts/codex-project-config.py` | 기존 사용자 필드를 보존하는 구조적 설정 갱신 |
| `scripts/codex-run.py` | Codex 비대화형 프로세스와 최종 응답 분리 |
| `tests/test_codex_*.py` | 네트워크 없는 계약·프로세스 회귀 |
| `tests/codex-smoke.md` | 실제 설치/하네스 검증 절차 및 결과 양식 |

위 두 `gx-*` 경로의 기준은 `.claude/skills/`이다. 구체적인 수정 파일·인터페이스·코드·테스트는 각 하위 계획에 적는다.

## 실행 및 완료 추적

- [x] A Task 1~4 완료, Claude 회귀와 Codex 경계 검증 통과.
- [x] B Task 1~3 완료, clean export의 17개 역할·template·스킬 참조 검증 통과.
- [x] C Task 1~4 완료, 두 러너 mock과 Windows/Linux 프로세스 검증 통과.
- [x] 실제 Codex 소비 프로젝트 smoke 3회 결과 기록. 실패·미측정은 별도로 표시.
- [x] `bash scripts/lint-consistency.sh`, `bash scripts/hook-tests.sh`, `bash scripts/test-gx-ralph.sh`, `bash scripts/test-behavior-tests.sh`, `python -m unittest discover -s tests -p 'test_codex_*.py'` 통과.
- [ ] 릴리스할 때만 CHANGELOG와 세 버전 필드를 함께 변경하고 clean Git source 설치 확인.

구현 완료의 기준은 스킬 인식 수가 아니라 합격 증거다. C의 실제 모델 smoke가 미실행이면 A/B 및 C mock 완료로만 보고하고 Codex 전체 지원으로 표현하지 않는다.

2026-09-14: 위 완료 표시는 구현·지정 회귀와 실제 시도 기록의 완료다. 전체 플랫폼/역할 격리 보증은 아니다. R2 src 미열람, Codex의 claude 제공자 안내 실측, 릴리스 Git source는 하위 계획에서 미확인으로 남긴다. 실제 전체 흐름 3회는 1회 PASS·2회 실패 포함이며 발견한 결함은 수정 후 개별 재검증했다. [실측 보고서](../../reports/2026-09-14-codex-validation.md) 참조.
