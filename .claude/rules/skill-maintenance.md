# 스킬 유지보수 규칙

oh-my-gx의 `.claude/skills/gx-*/` 스킬, phase, 참조 파일과 `agents/*.md` 역할 정의를 만들거나 수정할 때 적용한다. Claude Code 동작과 Codex 배포·실행 경로를 한 변경으로 취급한다. 실행 중 도구 대응의 정본은 [Codex 실행 규약](../skills/gx-dev/references/codex-runtime.md)이고, 개발 저장소의 하네스 설명은 [Codex 하네스 어댑터](harness-codex.md)다. 실제 세션의 도구 스키마가 문서와 다르면 실제 스키마를 따른다.

## 수정 전 확인

1. 대상 `SKILL.md`와 함께 호출되는 phase·references·역할 정의를 읽는다. gx-tdd와 공유 파이프라인을 바꿀 때는 [유지보수 노트](../skills/gx-tdd/references/maintenance-notes.md)의 의도적 중복 위치도 확인한다.
2. 사용자 질문, 역할 위임, 다른 스킬 호출, 셸 명령, 보호 게이트 중 무엇이 바뀌는지 표시한다. 같은 계약을 쓰는 gx-dev·gx-tdd·단독 스킬·훅·라우팅 규칙이 있으면 영향을 대조한다.
3. 새 스킬이라면 Claude 매니페스트와 [Codex 매니페스트](../../.codex-plugin/plugin.json)의 스킬 경로가 모두 `.claude/skills/`를 가리키는지 확인한다. 개발용 `.agents/skills/skill-creator`는 배포 스킬에 포함하지 않는다.

## 작성 기준

- 배포 스킬은 이 저장소의 `AGENTS.md`나 `.claude/rules/`를 소비 프로젝트에서 읽을 수 있다고 가정하지 않는다. 각 `SKILL.md`에 하네스 적응 안내를 두고, 길면 해당 스킬의 `references/`로 분리한 뒤 `SKILL.md`에서 연결한다. Codex 경로는 설치되는 `codex-runtime.md`를 참조한다.
- 번들 파일은 **지시가 적힌 파일의 위치 기준 상대경로**로 참조하고 실제 배포 경로에서 존재를 확인한다. 소비 프로젝트 cwd, 개발 소스 경로, `${CLAUDE_PLUGIN_ROOT}`를 설치된 스킬 위치로 가정하지 않는다. Python·셸 helper는 확인된 설치 플러그인 루트를 기준으로 찾는다.
- Claude 전용 `Task`, `AskUserQuestion`, `Skill` 지시를 새로 넣거나 바꾸면 같은 위치의 하네스 적응 안내도 갱신한다. Codex 역할 위임은 배포된 `codex-roles/index.json`과 역할 본문을 사용하고, 질문은 현재 모드에서 제공되는 도구로 묻고 실제 답을 기다리며, 스킬 상호 호출은 대상 `SKILL.md`의 절차와 게이트를 수행한다. `allowed-tools`와 역할의 `tools` 목록을 Codex 권한 강제로 표현하지 않는다.
- 승인·verify·보호 브랜치·커밋/PR 중단 조건은 하네스별 도구명만 바뀌어도 유지한다. 훅이 로드되지 않은 상태를 보호 성공으로 취급하지 않으며, 스킬 자체의 보호 분기도 확인한다. 헤드리스 경로는 응답할 사용자가 없을 때의 중단·기록 규칙을 명시한다.
- `agents/*.md`의 본문·모델 티어·도구 목록을 바꾸면 `python scripts/sync-codex-resources.py`로 배포용 `codex-roles/`와 index를 갱신한다. `.claude/config.json`을 바꿀 때도 같은 명령으로 setup 템플릿을 동기화한다. 생성물은 직접 따로 고쳐 원본과 어긋나게 두지 않는다.
- Windows 예시에는 UTF-8 파일 읽기와 실제 셸을 명시한다. PowerShell에서는 `Get-Content -Encoding UTF8`을 사용하고, Bash 문법은 Bash에서 실행한다. 특정 Codex 모델명·도구 인자를 불변 API처럼 쓰지 않고 현재 세션의 허용 목록과 스키마를 확인하도록 적는다.

## 변경 후 확인

1. 수정한 스킬의 `SKILL.md`에서 하네스 적응 안내와 모든 참조 파일까지 실제로 따라갈 수 있는지 확인한다. 새 도구 호출과 변경된 게이트가 Codex 대응에 빠지지 않았는지 점검한다.
2. `python scripts/sync-codex-resources.py --check`, `bash scripts/lint-consistency.sh`를 실행한다. 역할·설정 변경이 있으면 동기화 명령 실행 후 다시 검사한다.
3. Codex 실행 경로를 바꿨으면 `python -m unittest discover -s tests -p "test_codex_*.py" -v`를 실행한다. 훅·보호 조건을 바꿨으면 `bash scripts/hook-tests.sh`도 실행한다. 해당 동작에 자동 검사가 없다면 게이트와 실패 경로를 확인하는 회귀 사례를 추가한다.
4. 설치 발견, 질문·역할 위임, 훅 신뢰, 커밋 같은 실제 세션 동작을 바꿨다면 [Codex smoke 계약](../../tests/codex-smoke.md)의 관련 시나리오를 소비 프로젝트에서 확인하고 근거를 기록한다. 로컬 린트·mock 결과만으로 설치나 실제 모델·훅 동작을 검증했다고 표시하지 않는다.
