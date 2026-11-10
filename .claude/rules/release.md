# 릴리스 규칙

## 릴리스 체크리스트

버전을 올릴 때 아래 파일의 `version` 필드를 반드시 함께 갱신한다:

| 파일 | 필드 |
|------|------|
| `.claude-plugin/plugin.json` | `version` |
| `.claude-plugin/marketplace.json` | `plugins[0].version` |
| `.codex-plugin/plugin.json` | `version` (Codex 매니페스트) |
| `CHANGELOG.md` | 새 버전 섹션 추가 |

**배포 동작을 바꾸는 PR은 같은 PR에서 버전과 CHANGELOG를 올린다.** 스킬(`.claude/skills/`)·훅·에이전트·helper 스크립트·설정 템플릿을 바꾸고 버전을 그대로 두면, 이미 설치한 사용자는 같은 버전으로 보여 업데이트를 받지 못한다(v3.0.0 태그 뒤 #102가 버전 없이 머지되어 설치본과 main이 갈린 이력). 정합성 린트 [1/36]이 최근 버전 태그 이후 이 경로들이 바뀌었는데 버전이 태그와 같으면 실패한다. 린트·문서만 바꾸는 PR은 해당하지 않는다.

네 곳의 버전이 일치하지 않으면 플러그인 UI에 이전 버전이 표시된다. 정합성 린트 `[1/36]`이 네 값을 대조한다.

## 릴리스 순서

1. `CHANGELOG.md`에 새 버전 섹션 작성
2. `.claude-plugin/plugin.json`·`marketplace.json`·`.codex-plugin/plugin.json`의 version 갱신
3. 커밋 → PR → 머지
4. GitHub Release는 **자동 생성**됨 (`.github/workflows/release.yml`)
   - PR이 main에 머지되면 `plugin.json`에서 버전을 추출
   - 해당 버전의 태그(`v{version}`)가 없으면 CHANGELOG.md에서 내용을 파싱하여 Release 생성
   - 이미 태그가 있으면 스킵 (중복 방지)
