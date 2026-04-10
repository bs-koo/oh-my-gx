# Prepare Phase: 준비 & 프로젝트 확정

## 0. 인자 파싱

ARGS에서 파싱:
- `--detail` → `DETAIL_MODE = true`. 기본 `false`.
- `--idea "<텍스트>"` → `IDEA_RAW`. Report Phase 9절에서 사용.
- 나머지 → `RAW_QUERY`.

## 1. 프로젝트 확정

프로젝트 루트를 확인한다. `.claude/config.json`의 `"vcs"` 값에 따라 분기:
- **git** (또는 미설정): `Bash(git rev-parse --show-toplevel)` → 성공 시 `PROJECT_ROOT` = 출력 경로.
- **svn**: `Bash(svn info --show-item wc-root)` → 성공 시 `PROJECT_ROOT` = 출력 경로.
- 실패 → `PROJECT_ROOT` = `pwd`.
- `PROJECT_NAME` = 디렉토리명 (`basename`).

## 2. 쿼리 분석

LLM이 수행 (도구 호출 불필요):

1. `RAW_QUERY` → `QUERY`로 정리.
2. 불용어/조사 제거 → 비즈니스 키워드. shell 특수문자 제거.
3. **의도어 제거**: 사용자가 알고 싶은 "의도"를 나타내는 메타 용어는 코드 검색에 유효하지 않으므로 키워드에서 제외한다. 의도어 목록: `정책, 규칙, 로직, 구현, 코드, 설명, 정리, 점검, 분석, 확인, 조회`.
4. 키워드 0개 →
   ```
   AskUserQuestion(
     questions: [{
       header: "키워드 보강",
       question: "쿼리에서 유효한 검색 키워드를 추출하지 못했습니다. 구체적인 비즈니스 용어로 다시 입력해주세요.",
       multiSelect: false,
       options: [
         { label: "Other로 입력", description: "Other로 이동해서 쿼리를 자연어로 다시 입력해주세요" },
         { label: "중단", description: "영향도 분석을 중단합니다" }
       ]
     }]
   )
   ```
   최대 2회 재시도. "중단" 선택 또는 2회 재시도 실패 시 Prepare Phase를 중단한다.

## 3. 사용자 보고

```
정책 탐지를 시작합니다.

- 프로젝트: <PROJECT_NAME>
- 쿼리: "<QUERY>"
- 검색 키워드: <한국어 키워드 나열>

코드를 탐색합니다.
```

Explore Phase로 진행한다.
