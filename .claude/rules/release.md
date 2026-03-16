# 릴리스 규칙

## 릴리스 체크리스트

버전을 올릴 때 아래 파일의 `version` 필드를 반드시 함께 갱신한다:

| 파일 | 필드 |
|------|------|
| `.claude-plugin/plugin.json` | `version` |
| `.claude-plugin/marketplace.json` | `plugins[0].version` |
| `CHANGELOG.md` | 새 버전 섹션 추가 |

세 곳의 버전이 일치하지 않으면 플러그인 UI에 이전 버전이 표시된다.

## 릴리스 순서

1. `CHANGELOG.md`에 새 버전 섹션 작성
2. `.claude-plugin/plugin.json`과 `marketplace.json`의 version 갱신
3. 커밋 → PR → 머지
4. GitHub Release는 **자동 생성**됨 (`.github/workflows/release.yml`)
   - PR이 main에 머지되면 `plugin.json`에서 버전을 추출
   - 해당 버전의 태그(`v{version}`)가 없으면 CHANGELOG.md에서 내용을 파싱하여 Release 생성
   - 이미 태그가 있으면 스킵 (중복 방지)
