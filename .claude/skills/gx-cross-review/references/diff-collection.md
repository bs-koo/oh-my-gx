# 교차 리뷰 diff 수집

gx-cross-review Step 2-2에서 양 하네스 모두 읽는다. SKILL.md에서 확인한 설치 루트 `GX_PLUGIN_ROOT`와 소비 프로젝트 `PROJECT_ROOT`를 유지한다.

설치 루트의 [../../../../scripts/gx-review-diff.py](../../../../scripts/gx-review-diff.py)를 확인하고 Python 3.10+로 실행한다. Bash는 `python3 "$GX_PLUGIN_ROOT/scripts/gx-review-diff.py"`, Windows PowerShell은 확인한 Python/helper 절대경로와 UTF-8 stdin을 사용한다 (`[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $OutputEncoding = [System.Text.UTF8Encoding]::new($false)`). 입력 JSON은 `{"cwd":"<PROJECT_ROOT 절대경로>","base":"<BASE_BRANCH>","scope":"diff","output":"<DIFF_FILE 절대경로>"}`이며 scope는 `${SCOPE}`를 그대로 전달한다. 소비 cwd를 플러그인 설치 루트로 사용하지 않는다.

helper가 diff를 `output` 경로에 원 바이트 그대로 직접 저장하므로 diff를 모델이 옮겨 적지 않는다. exit 0과 stdout 요약 JSON의 `files`·`untracked`·`scope`·`reduced`(500줄 이상 stat 전환 여부)·`bytes`·`lines`를 확인한다. helper는 merge-base 대비 committed/staged/unstaged와 untracked를 합산하며 index를 변경하지 않는다. **명시 stat 또는 500줄 이상 전환에도 untracked의 경로와 통계를 보존**한다. `.dev/` 산출물과 `output` 파일 자신은 제외하여 이전 diff가 다음 diff에 섞이지 않게 한다.

`files`가 비었으면 변경 없음으로 종료한다. helper 실패/잘못된 JSON은 `${DIFF_FILE}`을 재사용하지 않고 중단한다(실패 시 기존 파일은 덮어쓰지 않는다). `${DIFF_FILE}` 끝의 전체 변경 파일 목록을 advisor에 그대로 전달하며 통계 모드에서는 **그 목록의 모든 파일**을 직접 Read하도록 지시한다. tracked-only `git diff --stat`으로 다시 덮어쓰지 않는다.
