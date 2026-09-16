> 호출 전제: gx-context/SKILL.md가 인자 파싱·모드 선택·하네스 적응을 완료했다. 이 파일의 상대경로는 gx-context/SKILL.md 위치를 기준으로 해석한다.

## 모드 E: 동기화 (--sync)

`/gx-dev`를 거치지 않고 개발한 내용을 git 히스토리에서 분석하여 status.md를 갱신한다.

`--sync` 사용 시 도메인명은 필수. 없으면 `context/` 하위 도메인 목록을 수집하여 다음과 같이 선택을 요청한다:

```
AskUserQuestion(
  questions: [{
    header: "도메인 선택",
    question: "동기화할 도메인을 선택해주세요.",
    multiSelect: false,
    options: [
      { label: "<도메인1>", description: "context/<도메인1>/" },
      { label: "<도메인2>", description: "context/<도메인2>/" }
    ]
  }]
)
```

### E-1. 사전 확인

1. `context/{도메인}/status.md` Read
2. ⬜ 항목이 0개면 → "갱신할 미반영 항목이 없습니다." 출력 후 종료
3. ⬜ 항목 목록을 파싱하여 `PENDING_ITEMS` 배열로 저장
4. 현재 작업 복사본의 VCS를 판별하여 `ACTIVE_VCS`를 `git` 또는 `svn`으로 고정한다. `git rev-parse --show-toplevel`이 성공하면 git, 그렇지 않고 `svn info --show-item wc-root`가 성공하면 svn이다. 둘 다 아니면 동기화할 이력을 정할 수 없으므로 종료한다.
5. `<!-- gx-sync ... -->`에서 `SYNC_GIT_HEAD`, `SYNC_SVN_REVISION`, `SYNC_PR_MERGED_AT`을 읽는다. 블록이나 값이 없으면 `-`로 둔다.
6. `ACTIVE_VCS = git`이고 gh를 사용할 수 있을 때만 `PR_SOURCE_ACTIVE = true`로 둔다. 그 밖에는 false이며, 특히 SVN 작업 복사본에서는 gh 설치 여부와 관계없이 PR source를 활성화하지 않는다.
7. 활성 source의 영속 cursor를 명령 인자로 넣기 전에 다음 형식과 실제 값을 엄격히 검증한다. 비활성 source의 cursor는 검증·조회하지 않고 기존 값을 유지한다.
   - git은 `-` 또는 40자리 hexadecimal만 허용한다. 40자리 값은 `git cat-file -e "${SYNC_GIT_HEAD}^{commit}"`도 성공해야 한다.
   - svn은 `-` 또는 부호 없는 10진수 숫자만 허용한다.
   - PR은 `-` 또는 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$`에 맞는 엄격한 UTC ISO 8601 값만 허용하고, 정규식 통과 후에도 실제 UTC 날짜·시각으로 파싱되는지 확인한다.
   - 형식·객체·파싱 검증 실패는 해당 소스의 `분석 실패`다. 검증 실패한 cursor를 명령 인자로 사용하지 않는다.
8. 검증 후 조회가 시작되기 전에 활성 VCS의 상한을 한 번만 캡처한다. git의 `git rev-parse HEAD`는 `CANDIDATE_GIT_HEAD`, svn의 `svn info --show-item revision`은 `CANDIDATE_SVN_REVISION`에 저장한다. `PR_SOURCE_ACTIVE = true`일 때만 `CANDIDATE_PR_SYNC_AT`에 현재 UTC 시각을 저장한다. 각 후보 캡처 명령과 후보 값 검증이 성공해야 하며, 아직 status.md에는 쓰지 않는다. 이후 모든 조회는 이 후보 상한을 사용한다.
9. 후보 캡처 뒤 활성 source의 저장 cursor와 상한의 순서를 검증한다.
   - SVN cursor가 `-`가 아니면 `SYNC_SVN_REVISION <= CANDIDATE_SVN_REVISION`이어야 한다. 더 크면 `SVN cursor 역전`으로 명시한 `분석 실패`이며 기존 cursor를 보존한다.
   - PR cursor가 `-`가 아니면 `SYNC_PR_MERGED_AT <= CANDIDATE_PR_SYNC_AT`이어야 한다. 더 크면 `PR cursor 역전`으로 명시한 `분석 실패`이며 기존 cursor를 보존한다.
   - 두 값이 같은 경우만 변경 없음에 해당하는 정상 빈 범위다. cursor가 후보보다 큰 역전은 정상 빈 범위로 처리하지 않는다.

### E-2. git 히스토리 분석

1. **git cursor 조회**: `SYNC_GIT_HEAD`가 `-`가 아니면 `git merge-base --is-ancestor ${SYNC_GIT_HEAD} ${CANDIDATE_GIT_HEAD}`를 실행하고 종료 코드를 보존한다. 종료 코드 `0`만 증분 조회로 인정하여 `git log --format='%H%x00%B%x00' ${SYNC_GIT_HEAD}..${CANDIDATE_GIT_HEAD}`를 실행한다. 종료 코드 `1`은 branch/rewrite로 cursor가 현재 계보에 없다고 보고 2번의 full-ID fallback으로 전환한다. 종료 코드 `2` 이상은 명령 실행 오류이므로 git `분석 실패`이며 fallback하지 않는다.
2. **git 초기·fallback 조회**: 각 pending FR/NFR/AC ID를 전체 이력, 즉 `CANDIDATE_GIT_HEAD`에서 도달 가능한 전체 커밋에서 `git log --format='%H%x00%B%x00' ${CANDIDATE_GIT_HEAD} --regexp-ignore-case --grep=<ID>`로 검색한다. `--grep` 결과도 커밋 제목과 본문 전체인 `%B`에서 5번의 exact token을 재검증한다. 설명 키워드는 최근 100건 `git log --format='%H%x00%B%x00' -100 ${CANDIDATE_GIT_HEAD}`에서 보조 검색한다.
3. **svn 조회**: `SYNC_SVN_REVISION`이 `-`가 아니면 E-1의 순서 검증을 통과한 뒤 `SVN_FROM_REVISION = SYNC_SVN_REVISION + 1`로 계산하여 `svn log --xml -r ${SVN_FROM_REVISION}:${CANDIDATE_SVN_REVISION}`을 조회한다. cursor와 후보가 같아 하한이 상한보다 1 큰 경우만 성공한 빈 범위로 처리한다. 초기 조회는 각 pending ID로 `svn log --xml -r 1:${CANDIDATE_SVN_REVISION} --search <ID>`를 수행하고, 반환된 각 logentry의 메시지에서 exact token을 재검증한다. 설명 키워드는 `svn log --xml -l 100 -r ${CANDIDATE_SVN_REVISION}:1`에서 보조 검색한다.
4. **PR 조회**: `PR_SOURCE_ACTIVE = true`일 때만 PR을 조회한다. 저장소를 확인한 뒤 `gh api --paginate`로 `repos/{owner}/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=100`의 모든 page를 끝까지 읽는다. 각 응답에서 number·title·body·html_url·merged_at을 읽고, merged_at이 null이 아닌 PR만 남긴다. cursor가 있으면 `start = SYNC_PR_MERGED_AT`, 초기 조회면 하한 없음으로 두고 `start <= merged_at < candidate` (`candidate = CANDIDATE_PR_SYNC_AT`) 범위만 분석한다. 모든 page의 명령·JSON 파싱·필드 처리가 성공해야 PR 분석 성공이며, 한 page라도 실패하면 PR `분석 실패`다. `ACTIVE_VCS = svn`이면 결과에 `svn: 건너뜀 (PR 개념 없음)`을 기록하고 SVN 분석과 cursor 처리는 정상적으로 계속한다.
5. **case-insensitive exact ID 매칭**: Git/SVN/PR 모두 pending ID와 입력 텍스트를 ASCII 대문자로 동일하게 정규화한 뒤, git `%B`, SVN 메시지, PR 제목·본문에서 `(^|[^A-Za-z0-9-])<ID>($|[^A-Za-z0-9-])` 경계를 재검증한다. 따라서 `fr-1`은 `FR-1`과 일치하지만 `NFR-1`이나 `FR-10`과 일치하지 않는다. exact ID를 우선 매칭하고, ID가 없을 때만 설명 키워드 일치를 후보로 제시한다.
6. 명령 실패, cursor·후보 검증 실패, 출력 파싱 실패는 해당 소스의 `분석 실패`로 표시한다. 분석·명령 실패 시 cursor를 갱신하지 않는다.

### E-3. 매칭 결과 제시

```
status.md 동기화 분석 결과:

  1. ✅ AC-1 (FR-1): 로그인 기능 — 커밋 a1b2c3d "feat: 로그인 기능 추가"
  2. ✅ AC-4 (FR-16): 비밀번호 변경 — PR #125 "FEATURE: 비밀번호 변경"
  3. ⬜ AC-2 (FR-2): 회원가입 — 매칭되는 커밋/PR 없음

위 항목을 반영할까요?
```

다음과 같이 확인한다. 사용자가 항목을 조정할 수 있다 (제외/추가).

```
AskUserQuestion(
  questions: [{
    header: "status.md 갱신",
    question: "위 항목을 status.md에 반영할까요?",
    multiSelect: false,
    options: [
      { label: "전체 반영", description: "제안된 항목을 모두 반영합니다" },
      { label: "조정 후 반영", description: "선택하면 후속 질문에서 제외/추가할 항목을 묻습니다" },
      { label: "건너뛰기", description: "갱신하지 않고 종료합니다" }
    ]
  }]
)
```

"조정 후 반영"을 선택하면 제외/추가할 항목을 후속 질문으로 묻고 답변을 기다린다. 원 질문 UI Other의 조정 내용은 바로 받는다. 조정된 항목을 확인한 뒤 E-4로 진행한다.

### E-4. status.md 갱신

사용자가 승인한 항목만 Edit으로 반영:
- ⬜ → ✅ 변경
- PR 열에 PR 링크 또는 커밋 해시 기입
- 수정일 갱신
- 사용자가 `전체 반영`, `조정 후 반영`, `건너뛰기` 중 하나를 확정하고 모든 활성 source의 분석 명령과, `PR_SOURCE_ACTIVE = true`인 경우 PR의 모든 page 처리가 성공했을 때만 승인한 행 변경과 gx-sync 블록 갱신을 같은 Edit으로 수행한다. 활성 source의 cursor에는 캡처해 둔 `CANDIDATE_GIT_HEAD`, `CANDIDATE_SVN_REVISION`, `CANDIDATE_PR_SYNC_AT`을 기록하고, 사용하지 않은 source의 기존 값을 유지한다.
- 질문 중단, cursor·후보 검증 또는 순서 검증 실패, 파일 Edit 실패, 분석·명령·파싱 실패, PR page 일부 실패 시 기존 cursor를 유지한다.

### E-5. 완료 안내

```
status.md 갱신 완료: ✅ {N}건 반영 (AC-1, AC-4)
남은 미반영: ⬜ {M}건
```

---
