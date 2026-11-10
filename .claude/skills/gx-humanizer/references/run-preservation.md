# 실행 예약과 안전본 보존

helper는 이 파일 위치 기준 `../../../../scripts/gx-humanizer-run.py`다(SKILL.md 기준 `../../../scripts/gx-humanizer-run.py`). 설치 루트·helper 존재를 확인하고 사용한다. Codex는 설치된 공통 runtime의 루트 확인 규칙을 따른다. Python 3.10+ 표준 라이브러리만 사용하며 외부 명령·모델·Git을 실행하지 않는다.

스킬 입력 `--history [run-id]`와 `history [run-id]`는 모두 helper의 `history --cwd <project> [--run-id <id>] [--limit 20]`로 옮긴다. 실행 메타와 파일 존재 상태만 읽고 새 디렉터리·예약·보고서·.gitignore·state를 만들지 않는다. 최신 순으로 mode·genre·final_path·summary_path를 반환하고, 메타 없는 옛 결과는 `legacy_unverified`, 깨진 메타·일부 결과만 있으면 `incomplete`로 표시한다. `outputs_present`는 산출물 존재만 뜻하며 검증 통과는 `unverified`다. 원문·윤문·요약 본문은 읽거나 출력하지 않는다. 이력이 없으면 `runs: []`다.

모드·장르·톤·수정 범위가 확정된 뒤, **각 입력 문서마다** 새 실행을 예약한다. 감사만 요청해도 별도 실행을 쓴다. 확정된 문자열을 shell에 맞게 인자로 인용하며 입력 본문을 명령 문자열에 보간하지 않는다. `--source`는 원본 파일의 식별 경로, 직접 입력이면 `inline`이다.

Git Bash/POSIX shell 예:

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-humanizer-run.py" reserve --cwd "$PROJECT_ROOT" --mode strict --genre '학술/리포트' --tone '원문 격식체 유지' --scope '3장만' --source '보고서.md'
python3 "$GX_PLUGIN_ROOT/scripts/gx-humanizer-run.py" freeze-input --cwd "$PROJECT_ROOT" --run-id "$RUN_ID" --input-file "$INPUT_FILE"
```

Windows PowerShell에서는 `$env:PYTHONUTF8='1'`을 설정하고 같은 인자를 `python`으로 호출한다. JSON 파일은 `Get-Content -Encoding UTF8`로 읽는다. 직접 제공된 텍스트는 예약된 실행의 `input.pending.txt`에 UTF-8로 저장해 `freeze-input --input-file`로 읽거나 UTF-8 표준입력을 사용한다. 원문 전체를 동결하고 수정 허용 영역은 `scope`에 둔다. 부분 문서만 따로 입력으로 제공됐다면 그 제공 범위가 원문이다.

`reserve`는 summary 존재와 무관하게 이미 존재하는 모든 날짜별 이름을 소비된 ID로 간주한다. 동시 실행은 배타 mkdir로 서로 다른 ID를 얻는다. 중간 실패 디렉터리·예약 메타 저장 실패 디렉터리는 지우거나 재사용하지 않는다. 999 이후에도 최소 3자리 형식을 유지하며 1000, 1001로 증가한다. 원문·메타를 변경하려면 새 실행을 예약한다.

`freeze-input`은 `01_input.txt`와 `input.json`을 덮어쓰지 않고 저장한다. `run.json`에는 `metadata.mode/genre/tone/scope/sources`가 있고, `input.json`은 원문과 메타 SHA-256을 결합한다. 자식은 이 파일을 읽기만 한다. 불명확한 메타·원문 누락·symlink 범위 탈출·쓰기 실패는 정상 빈 실행이 아니라 차단이다.

strict의 최초 윤문은 라운드 0, 재윤문은 1~2다. fidelity 호출 **직전** 부모가 `03_rewrite.md`의 SHA-256을 직접 구해 기록하고, 태스크 입력에 `run-id`, `round`, `rewrite_sha256`, 실행 메타 경로를 전달한다. PowerShell의 `(Get-FileHash -Algorithm SHA256 -LiteralPath "$RUN_DIR/03_rewrite.md").Hash.ToLowerInvariant()` 또는 확인된 읽기 전용 SHA-256 명령을 사용한다. verifier가 같은 run·라운드·지문을 출력하는지 확인한다. 미반환·오래된 report·누락·불일치는 진행하지 않는다.

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-humanizer-run.py" archive-round --cwd "$PROJECT_ROOT" --run-id "$RUN_ID" --round 0 --rewrite-sha256 "$REWRITE_SHA256"
python3 "$GX_PLUGIN_ROOT/scripts/gx-humanizer-run.py" archive-naturalness --cwd "$PROJECT_ROOT" --run-id "$RUN_ID" --round 0 --rewrite-sha256 "$REWRITE_SHA256"
python3 "$GX_PLUGIN_ROOT/scripts/gx-humanizer-run.py" safe --cwd "$PROJECT_ROOT" --run-id "$RUN_ID"
python3 "$GX_PLUGIN_ROOT/scripts/gx-humanizer-run.py" safe --cwd "$PROJECT_ROOT" --run-id "$RUN_ID" --require-naturalness --round 0 --rewrite-sha256 "$REWRITE_SHA256"
```

`archive-round`는 판정과 무관하게 현재 윤문본·fidelity 결과를 `rounds/000/` 등에 새로 저장한다. 입력 지문·호출 전 윤문 지문·보고서의 run/round/rewrite_sha256이 맞아야 하며, 최초 다음 라운드부터 직전 기록도 요구한다. 마지막에 `checkpoint.json`을 발행하므로 중간 복사 실패본은 안전본이 아니다. 같은 라운드를 재호출해 덮어쓰지 않는다. 과거 기록은 Write/Edit로 수정하지 않는다.

`safe`는 저장된 지문과 fidelity `full_pass`·rollback 0을 재검증해 가장 최근 안전본의 `source`·`round`·`rewrite_sha256`을 반환한다. 없으면 동결 원문을 반환한다(`round: null`). 최신 작업 파일 `03_rewrite.md`가 덮였어도 이를 자동으로 안전본이라 부르지 않는다. naturalness에는 이 **불변 source**를 rewrite_path로 전달하고 같은 round·SHA를 report meta에 기록하도록 한다. `archive-naturalness`는 report의 run·round·SHA와 fidelity 안전본을 대조하여 판정 파일과 지문 영수증을 불변 저장한다. 다른 SHA의 accept·미반환·불일치·중간 저장 실패는 완료 근거가 아니다.

정상 strict 완료는 `safe --require-naturalness --round <현재라운드> --rewrite-sha256 <검수지문>`으로 두 검수의 동일성 및 보존 naturalness accept/사람 개입 없음까지 재검증한다. 실패하면 이전 통과본으로 조용히 완료하지 않는다. 사람 개입 종료만 일반 safe로 이전 안전본/원문을 선택한다. 반환 source를 Read해 final로 채택하며, 보존 윤문본이면 본문의 `---diff---` 이전만 출력한다. 원문 폴백에는 이 제거를 적용하지 않는다.

중단 후 기존 실행을 이어갈 때는 명시된 run-id의 run.json·input.json·rounds를 읽고 `safe`를 실행한다. 기존 원문·모드/genre/tone/scope·라운드·검증 요청 지문·실제 사용자 응답을 복원할 수 있을 때만 현재 단계를 재개한다. 부분 보존 파일·판정 누락·복구 불가능한 라운드는 중단 사유로 보고한다. 새 입력을 과거 실행에 넣거나 카운트를 0으로 초기화하지 않는다. 새 요청은 새 ID를 예약한다. helper는 승인·50% 변경률·최대 2회·자식 독립 검증을 대신하지 않는다.
