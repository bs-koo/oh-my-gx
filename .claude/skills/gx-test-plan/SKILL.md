---
name: gx-test-plan
version: 1.0.0
description: "gx-tdd가 남긴 단위테스트 결과 원장을 단위테스트계획서(DE-13) xlsx 사본에 반영한다. '단위테스트 결과 반영', '결과반영 엑셀', '테스트 결과 엑셀로' 시 사용."
argument-hint: "[계획서 경로]"
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "AskUserQuestion", "Bash(python *)", "Bash(python3 *)", "Bash(git *)", "Bash(ls *)", "Bash(test *)", "Bash(mkdir *)"]
---

# gx-test-plan

> **이 스킬**: gx-test-plan — 단위테스트 결과 원장을 계획서 사본에 반영
> **혼동 주의**: 원장은 gx-tdd가 완료 단계에서 만든다. 이 스킬은 테스트를 실행하지 않고 원장을 엑셀에 옮기기만 한다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. Codex에서는 먼저 `Read("../gx-dev/references/codex-runtime.md")`로 공통 실행 규약을 읽는다. 상대경로는 이 SKILL.md 위치 기준이다. `AskUserQuestion`은 현재 모드에서 제공된 질문 도구로 옮기고 실제 답변을 기다린다. 질문은 한 번에 1~3개, 질문마다 선택지는 2~3개이며 Other를 option으로 직접 추가하지 않는다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → `request_user_input`. 그 도구를 쓸 수 없으면 자연어로 묻되, **실제 답변 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다.

헬퍼는 [scripts/de13.py](scripts/de13.py)다. 이 SKILL.md 위치 기준 절대경로를 `DE13`으로 두고 `python3 "<DE13>" …`(Windows는 `python`)로 실행한다. 둘 다 없으면 "Python 3.10 이상이 필요합니다"를 안내하고 종료한다.

## 절차

1. **프로젝트 루트**: `git rev-parse --show-toplevel`(svn은 `svn info --show-item wc-root`), 둘 다 아니면 현재 디렉터리.
2. **원장 확인**: `.dev/ut-results/`에 `testers.md`를 뺀 `*.md`가 없으면 "기록된 단위테스트 결과가 없습니다. gx-tdd를 계획서 연동 상태로 완료하면 원장이 생깁니다"를 안내하고 종료한다.
3. **계획서 탐지**: ARGS[0]에 경로가 있으면 그 파일. 없으면 gx-tdd `setup-testplan.md` "1. 계획서 탐지"와 같은 규칙(`*단위테스트계획서*.xlsx`, `~$`·`_결과반영_`·`.dev/`·빌드 산출물 제외). 0개면 경로를 묻고, 2개 이상이면 최근 수정 순 2개와 "취소"로 묻는다.
4. **반영**: `python3 "<DE13>" apply --plan "<계획서>" --ledger-dir ".dev/ut-results" --testers ".dev/ut-results/testers.md" --out ".dev/ut-results/export/<원본 파일명에서 .xlsx 뺀 것>_결과반영_<YYYYMMDD>.xlsx" --report ".dev/ut-results/export/report.json"`
5. **종료 코드 3** (매핑 없는 담당자): `report.json`의 `매핑 없는 담당자`마다 별도 질문으로 실명을 묻고 실제 답변을 기다린다. `.dev/ut-results/testers.md`(`| git 이름 | 실명 |` 표, 없으면 새로 만듦)에 행을 추가한 뒤 4를 다시 실행한다.
6. **종료 코드 2**: 메시지를 그대로 보고하고 종료한다.
7. **보고**: 사본 경로와 `report.json`의 기능별 `Pass / 제외 / 이관 / 미착수 / 재확인 필요`를 표로 보여준다. `재확인 필요`가 있으면 "계획서가 개정되어 해당 케이스 내용이 바뀌었습니다. 그 기능을 gx-tdd로 다시 확인하세요"를, `계획서에 없음`이 있으면 그 ID 목록을 안내한다.

## 하지 않는 것

- 원본 계획서를 덮어쓰지 않는다 (헬퍼가 같은 경로를 거부한다).
- 반영 사본을 커밋하지 않는다 (`.dev/ut-results/export/`는 gx-commit이 언스테이징한다).
- `Fail`을 기록하지 않는다. 원장에는 verify를 통과한 `Pass`, 사유가 있는 `제외`, 후속 작업으로 넘긴 `이관`만 있다.
- 비기능 행(연계기능ID 공란)은 채우지 않는다.
