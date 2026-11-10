# 단독 GREEN의 테스트 보존

이 참조 파일 위치 기준 `../../../../scripts/gx-test-integrity.py`가 helper다(SKILL.md 위치 기준은 `../../../scripts/gx-test-integrity.py`). Codex는 공통 runtime으로 확정한 설치 플러그인 루트의 `scripts/gx-test-integrity.py`를 사용한다. 소비 프로젝트나 개발 소스 경로로 대체하지 않는다. Python 3.10+ 표준 라이브러리만 필요하며 Git/SVN 모두 같은 파일 내용 검사를 사용한다. 테스트·빌드·Git 상태를 변경하지 않는다.

RED를 직접 재현한 뒤 구현 **이전**에 부모가 실행별 새 `.dev/standalone-green-{고유실행ID}/tests.json` 경로를 확정한다. 같은 실행의 재시도·재개는 이 기준선과 부모가 기록한 `baseline_sha256`을 복원한다. 기록이 없으면 구현을 계속하지 않는다. 새 캡처는 새 RED 인계 이후 별도 실행에서만 허용한다.

Git Bash/POSIX shell:

```bash
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-integrity.py" capture --cwd "$PROJECT_ROOT" --baseline "$BASELINE"
python3 "$GX_PLUGIN_ROOT/scripts/gx-test-integrity.py" verify --cwd "$PROJECT_ROOT" --baseline "$BASELINE" --baseline-sha256 "$BASELINE_SHA256"
```

Windows PowerShell에서는 같은 helper를 `python`으로 호출한다. 한글 입출력을 위해 `$env:PYTHONUTF8='1'`을 설정하고 `--cwd`, `--baseline`, `--baseline-sha256` 인자는 각각 따옴표로 감싼다. 캡처 JSON의 `baseline_sha256`을 부모가 실행 기록/대화에 보관하고, 자식은 `.dev/standalone-green-*` 기준선을 수정하지 않는다. 자식에게 기준선·프로젝트 설정·다른 테스트를 변경해서 통과시키는 권한을 주지 않는다.

`capture`는 `.claude/config.json`(명시 설정은 `--config`)과 기본 테스트 이름/디렉터리 및 프로젝트 `testSelection.tests` glob의 **합집합**을 탐색한다. 추적 여부와 무관하게 이미 수정된 파일·미추적 파일의 현재 내용을 보존한다. runner 설정도 보호한다. 일반 이름이나 설정에 포함되지 않는 테스트가 있으면 구현 전에 실제 테스트 경로를 설정에 등록하고 다시 RED를 확인한다. symlink 범위·설정·테스트 목록이 불명확하면 조용히 생략하지 않고 차단한다.

실행 설정 판정은 같은 번들의 `gx-test-plan.py`가 제공하는 `configuration_path`를 재사용한다. Babel·SWC·TypeScript/JavaScript·browserslist·Gradle wrapper·의존성/lock 설정 변경도 포함한다. 하위 폴더 접근 거부 등 탐색 오류는 불완전 목록으로 계속하지 않고 capture/verify 모두 차단하며, capture 실패 시 기준선을 발행하지 않는다.

- capture exit 0: 불변 기준선과 그 SHA-256을 반환. 기존 경로는 덮어쓰지 않는다.
- verify exit 0: 전체 파일 목록·내용·설정이 동일하다. 프로덕션 수정만 허용한다.
- verify exit 1: `added`/`removed`/`changed` 또는 설정 변경. 전체 테스트 GREEN이어도 통과가 아니다.
- exit 2: 잘못된 입력·누락·읽기 오류·기준선 지문 불일치. 중단하고 근거를 복원한다.
- exit 3: 테스트·러너 설정은 그대로지만 `dependency_changed`에 의존성 파일(락 파일, `package.json`의 dependencies 계열, `requirements.txt`, `go.mod`, `Cargo.*` 등)이 있다. 테스트 변조로 보지 않지만 통과로 간주하지 말고 "의존성 변경 — 사용자 확인 필요"로 보고해 승인을 받는다. 승인 전에는 완료로 표시하지 않는다. `package.json`의 scripts, `pom.xml`·`build.gradle`·`pyproject.toml`은 러너 설정이라 변경 시 exit 1이다(사용자 확인 후 새 실행으로 진행).
- helper 오류(exit 2, JSON 파싱 실패, 수집 실패)는 통과가 아니다. 중단하고 `reason`을 그대로 사용자에게 보고하며 기준선을 재생성하거나 verify를 건너뛰지 않는다.

`.gitignore` 대상과 `target/`·`build/`·`out/`·`.pytest_cache/`·`test-results/`·`coverage/`·`venv/` 등 러너 캐시·산출물은 지문하지 않는다. 테스트 판정은 `test/`·`tests/`·`__tests__/` 디렉터리와 `*Test(s).java`·`*IT.java`·`test_*.py`·`*_test.py`·`*.test|spec|cy.*` 파일명 관례이며, `app|next|tailwind|postcss.config.*` 같은 앱 설정은 보호하지 않는다. 그 밖의 테스트 경로는 `testSelection.tests`에 등록한다.

runner 실행 수·실제 assertion 통과는 별도 기존 GREEN 검증으로 확인한다. 이 helper는 그 실행 증거나 모델의 지시 준수를 대신하지 않는다.
