---
name: gx-test-plan
version: 1.1.0
description: "gx-tdd가 남긴 단위테스트 원장으로 gx-pm 단위테스트계획서(DE-13) xlsx를 갱신한다 — 결과·기대결과 보강, 신규 케이스 추가, 개정이력. '단위테스트 계획서 반영', '계획서 갱신', '단위테스트 결과 반영' 시 사용."
argument-hint: "[계획서 경로]"
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "AskUserQuestion", "Bash(python *)", "Bash(python3 *)", "Bash(git *)", "Bash(svn *)", "Bash(ls *)", "Bash(test *)", "Bash(mkdir *)", "Bash(mktemp *)"]
---

# gx-test-plan

> **이 스킬**: gx-test-plan — 단위테스트 원장을 계획서에 반영하고 개정이력을 남긴다
> **혼동 주의**: 원장은 gx-tdd 완료 단계가 만든다. 이 스킬은 테스트를 실행하지 않는다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. Codex에서는 먼저 `Read("../gx-dev/references/codex-runtime.md")`로 공통 실행 규약을 읽는다. 상대경로는 이 SKILL.md 위치 기준이다. `AskUserQuestion`은 현재 모드에서 제공된 질문 도구로 옮기고 실제 답변을 기다린다. 질문은 한 번에 1~3개, 질문마다 선택지는 2~3개이며 Other를 option으로 직접 추가하지 않는다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → `request_user_input`. 그 도구를 쓸 수 없으면 자연어로 묻되, **실제 답변 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다.

헬퍼는 [scripts/de13.py](scripts/de13.py)다. 이 SKILL.md 위치 기준 절대경로를 `DE13`으로 두고 `python3 "<DE13>" …`(Windows는 `python`)로 실행한다. 둘 다 없으면 "Python 3.10 이상이 필요합니다"를 안내하고 종료한다.

## 절차

1. **프로젝트 루트**: `git rev-parse --show-toplevel`(svn은 `svn info --show-item wc-root`), 둘 다 아니면 현재 디렉터리.
2. **계획서**: ARGS[0]에 경로가 있으면 그 파일, 없으면 `.claude/config.json`의 `testPlan.path`. 둘 다 없으면 "단위테스트계획서가 등록되지 않았습니다. `/gx-setup`에서 등록하거나 경로를 함께 적어 주세요"를 안내하고 종료한다.
3. **원장 확인**: `.dev/ut-results/`에 `testers.md`를 뺀 `*.md`가 없으면 "기록된 단위테스트 원장이 없습니다. 계획서를 등록한 뒤 gx-tdd를 완료하면 원장이 생깁니다"를 안내하고 종료한다.
4. **미커밋 수정 확인**: git은 `git status --porcelain -- "<계획서>"`, svn은 `svn status "<계획서>"` 출력이 비어 있지 않으면 "계획서에 커밋되지 않은 수정이 있습니다. 먼저 커밋하거나 되돌린 뒤 다시 실행하세요"를 안내하고 종료한다 (PM 수정분과 반영분이 한 변경에 섞이지 않게 한다).
5. **작성자**: `git config user.name`(svn은 OS 사용자명)이 `.dev/ut-results/testers.md`(`| git 이름 | 실명 |` 표)에 없으면 실명을 묻고 실제 답변을 기다린 뒤 행을 추가한다(파일이 없으면 만든다). 그 실명이 `AUTHOR`다.
6. **반영**: `python3 "<DE13>" apply --plan "<계획서>" --ledger-dir ".dev/ut-results" --testers ".dev/ut-results/testers.md" --author "<AUTHOR>" --report "<임시 디렉터리>/report.json"` (임시 디렉터리는 `mktemp -d`로 프로젝트 밖에 만든다).
7. **종료 코드 3** (매핑 없는 담당자): `report.json`의 `매핑 없는 담당자`마다 실명을 묻고(한 번에 3명까지) 실제 답변을 기다린 뒤 `testers.md`에 행을 추가하고 6을 다시 실행한다.
8. **종료 코드 2**: 메시지를 그대로 보고하고 종료한다. 버전을 해석할 수 없다는 메시지면 새 버전 번호를 묻고 `--version`을 붙여 6을 다시 실행한다. "엑셀에서 닫고" 메시지면 계획서를 닫은 뒤 다시 실행하도록 안내한다.
9. **보고**: `report.json`으로 표를 보여준다 — 버전, 결과 기입, 기대결과 보강, 신규 ID 범위, 개정이력 내용. `재확인 필요`가 있으면 "PM이 계획서에서 해당 케이스를 고쳤습니다. 원장 행을 확인하고 필요하면 그 기능을 gx-tdd로 다시 완료하세요"를, `계획서에 없음`·`기능 미지정`이 있으면 그 수와 원장의 해당 행을 고쳐 다시 실행하라는 안내를 한다. 마지막에 "계획서와 원장(`.dev/ut-results/`)이 바뀌었습니다. `/gx-commit`으로 함께 커밋하세요"를 안내한다.

## 하지 않는 것

- 커밋하지 않는다. 계획서와 원장 반영 표시는 사용자가 함께 커밋한다.
- `Fail`을 기록하지 않는다. 원장에는 verify를 통과한 `Pass`만 있다.
- 비기능 행(연계기능ID 공란)은 건드리지 않는다. 신규 행은 데이터 시트 끝에 추가한다.
