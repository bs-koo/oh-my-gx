> 호출 전제: gx-context/SKILL.md가 인자 파싱·모드 선택·하네스 적응을 완료했다. 이 파일의 상대경로는 gx-context/SKILL.md 위치를 기준으로 해석한다.

## 모드 D: 갱신

기존 도메인의 context를 갱신한다.

### D-1. 기존 문서 읽기

`context/{도메인}/`의 README.md, glossary.md, architecture.md를 Read한다.

### D-2. 변경 소스 파악

- `--from` 파일이 있으면: 파일 내용과 기존 context를 비교하여 변경 항목을 식별한다.
- `--from` 없으면:
  ```
  AskUserQuestion(
    questions: [{
      header: "갱신 항목",
      question: "어떤 내용을 갱신하시겠습니까?",
      multiSelect: true,
      options: [
        { label: "용어 추가", description: "glossary.md에 새 용어를 추가합니다" },
        { label: "아키텍처 변경", description: "architecture.md를 갱신합니다" },
        { label: "담당자 변경", description: "README.md의 담당자 정보를 갱신합니다" }
      ]
    }]
  )
  ```

### D-3. 변경 제안

변경 항목을 구체적으로 제안한다:
- "glossary.md에 '{용어}' 추가를 제안합니다."
- "README.md의 '배경' 섹션에 다음 내용 추가를 제안합니다: ..."
- "architecture.md에 '{컴포넌트}' 추가를 제안합니다."

### D-4. 사용자 확인 후 반영

사용자가 승인한 변경만 Edit으로 반영한다. 문서 수정 시 수정일을 갱신한다.

---

## 주제 문서 헤더 템플릿

아래는 `/gx-dev` 환류 등으로 주제 문서를 생성할 때 사용하는 헤더 형식이다. `/gx-context` 실행 시에는 생성하지 않는다.

```markdown
# {제목}

- 작성일: YYYY-MM-DD
- 수정일: YYYY-MM-DD
- 관련 레포: {org/repo}
```
