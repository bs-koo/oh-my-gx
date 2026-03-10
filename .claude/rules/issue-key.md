# 이슈 키 규칙

> **참고**: 현재 기본 컨벤션은 `{type}/{description}` 브랜치 + `{type}: 메시지` 커밋 형식을 사용한다.
> 이슈 키는 기본 워크플로우에 포함되지 않으며, 필요 시 아래 규칙을 참조할 수 있다.

이슈 키 관련 공통 규칙. 이슈 트래커 연동이 필요한 프로젝트에서 선택적으로 사용한다.

## 값 참조

이슈 키 정규식 등 구체적인 값은 `.claude/config.json`의 `issueKey` 필드를 참조한다.

## 파싱

- `git branch --show-current`로 브랜치명을 확인한다.
- 브랜치명에서 이슈 키 패턴(`config.json` → `issueKey.pattern`)을 추출한다.
- 예시: `feat/JIRA-123/login` → `JIRA-123`, `AFS-6/local-ddl` → `AFS-6`
