# gx-tdd 편입 설계 (확정)

tddak 플러그인의 TDD 시스템(dev·리뷰 단계)을 oh-my-gx에 별도 갈래로 편입한다.
일반 개발(gx-dev)은 그대로 두고, TDD 강제 갈래(gx-tdd)를 신설한다.

## 확정된 결정 (brainstorming + 사용자 답변 a~e)

| 키 | 결정 |
|----|------|
| 편입 형태 | 별도 스킬 `/gx-tdd` 신설 (gx-dev 무수정) |
| 강도 | 풀 세트 (tddak의 모든 강제 장치) |
| a) 격리 | `tdd-iron-law.md` → `gx-tdd/references/` (`.claude/rules` 미오염) |
| b) verify 게이트 | 공유 `gx-commit`/`gx-pull-request` 무수정. gx-tdd의 phase-complete가 `gx-verify → gx-commit → gx-pull-request` 직접 조립 |
| c) 명시적 키워드 | `gx-red`/`gx-green`/`gx-refactor`/`gx-verify` + 명시적 트리거. ttutak 충돌용 3중 식별 메커니즘은 미편입 |
| d) hotfix | tddak hotfix 경로 그대로 (design·정식 review 생략, RGR·verify 유지) |
| e) 라우팅 | `skill-routing.md`에 gx-tdd/gx-dev 분기 추가 |
| 버전 | v1.10.0 → v1.11.0 |

## 변경/추가 파일

### 신규 에이전트 (agents/)
red-writer, green-coder, refactor-coder, test-architect, spec-reviewer, quality-reviewer, verifier

### 신규 스킬 (.claude/skills/)
- gx-tdd/ (SKILL.md + phases/ 6개 + references/tdd-iron-law.md)
- gx-red/, gx-green/, gx-refactor/, gx-verify/ (SKILL.md)

### 수정
- .claude/rules/skill-routing.md (라우팅 추가)
- .claude-plugin/plugin.json, marketplace.json (버전)
- CHANGELOG.md (v1.11.0 섹션)

## 치환 규칙 (tddak → oh-my-gx)
- 스킬 호출: `tddak:dev`→`oh-my-gx:gx-tdd`, `tddak:commit`→`oh-my-gx:gx-commit`, `tddak:verify`→`oh-my-gx:gx-verify` 등
- 경로: `.claude/skills/dev/`→`.claude/skills/gx-tdd/`
- 정체성: `ttutak`→`gx-dev`(일반 개발 지칭), 3중 식별 헤더 블록 제거
- frontmatter name: 디렉토리명과 일치(gx-tdd/gx-red/gx-green/gx-refactor/gx-verify)
