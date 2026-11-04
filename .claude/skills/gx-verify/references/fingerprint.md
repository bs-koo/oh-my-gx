> gx-verify Step 5-A에서 git 통과 보고 전에 반드시 읽는다. 설치 경로 기준점은 ../SKILL.md이며 helper는 확인한 GX_PLUGIN_ROOT를 유지한다.

# verify 코드 지문

지문 계산 (git 저장소인 경우만 — svn은 "해당 없음"으로 보고):

**Codex 경로**: 이 설치된 스킬의 GX 플러그인 루트에서 `scripts/codex-fingerprint.py`가 실제로 존재하는지 확인한다. 소비 프로젝트 절대경로는 `git rev-parse --show-toplevel`로 확인한다. Windows PowerShell은 확인된 Python 3.10+ 실행 파일로 `python "<GX_PLUGIN_ROOT>/scripts/codex-fingerprint.py" --cwd "<PROJECT_ROOT>"`, Linux Bash는 `python3 "$GX_PLUGIN_ROOT/scripts/codex-fingerprint.py" --cwd "$PROJECT_ROOT"`를 실행한다. **종료 코드 0, 비어 있지 않은 stdout의 정확한 한 줄, `^[0-9a-f]+:[0-9a-f]{12}$` 형식**을 모두 확인한 뒤에만 신선한 지문으로 사용한다. 예를 들어 `8c235d4:notree`는 형식 오류다. helper 부재·실패·빈/잘못된 출력이면 테스트·빌드가 통과했어도 verify 게이트는 실패다. `verify-status: passed`를 기록하거나 이전 passed를 유지하지 말고, 호출한 오케스트레이터가 state.md를 `pending`으로 두고 잘못된/기존 `verify-fingerprint`를 제거한 뒤 차단 사유를 보고한다. 아래 직접 Git 명령은 Codex에서 실행하지 않는다. 임시 인덱스만 바꿔도 `git add`/`write-tree`가 소비 저장소 `.git/objects`에 쓰려 하기 때문이다.

**Claude Code 경로**는 기존 규약을 그대로 실행한다:
```bash
# 임시 인덱스를 써서 실제 인덱스는 건드리지 않는다 (mktemp 빈 파일은 git이 거부하므로 경로만 사용)
IDX="${TMPDIR:-/tmp}/.gxfp.$$"; rm -f "$IDX"
GIT_INDEX_FILE="$IDX" git add -A
GIT_INDEX_FILE="$IDX" git rm -r --cached -q --ignore-unmatch .dev
GIT_INDEX_FILE="$IDX" git write-tree   # 앞 12자만 사용
rm -f "$IDX"
git rev-parse --short HEAD
```
`{HEAD 단축}:{트리해시 앞12자}` 형태로 이어 `verify-fingerprint` 값으로 보고한다 (예: `7c9e814:3ca970cc12ab`). `.dev/` 제외는 파이프라인 산출물이 코드가 아니기 때문이며, 훅·gx-commit·gx-pull-request·라우팅이 같은 규약으로 **트리 성분을** 대조한다 (HEAD 성분은 기록·추적용).
