# Codex 플러그인 구현·실측 보고

검증일: 2026-09-14. Windows Codex CLI 0.154.0에서 **설치된 플러그인으로 setup → TDD → native 교차 리뷰 → verify를 실제 수행했다.** 보호 훅, 질문 기록, 설정 보존도 확인했다. Claude와 모든 동작이 동일하거나 모든 작업이 무인 완료된다는 판정은 내리지 않는다.

기존 미커밋 작업을 포함한 기준을 별도 worktree에 보존해 구현했다. 이 실측 단계에서는 사용자 소스의 커밋·스테이징·push·PR·릴리스를 하지 않았고 커밋 검증에는 외부 임시 프로젝트만 사용했다. 이후 사용자의 PR 요청에 따라 `feat/codex-native-validation` 브랜치에 이번 구현과 필요한 Codex 기반 파일만 모았다. 기존 버전/CHANGELOG 갱신 작업은 포함하지 않아 PR의 매니페스트 버전은 main의 1.31.0을 유지한다. 실측 export의 1.32.0 표기는 당시 검증 설치본의 식별자다.

## 환경과 증거

| 항목 | 실제 조건 |
|---|---|
| Windows | Windows 11, PowerShell 5.1, Git Bash, Python 3.10, Node 22.14 |
| Codex | CLI 0.154.0, ChatGPT 인증, 부모 모델 `gpt-5.6-sol` / low |
| 설치 | 별도 CODEX_HOME, local source marketplace의 실제 `plugin/install`, GX 스킬 17개 |
| 실제 모델 검증 설치본 | 검증 export `1.32.0+codex.validation-final-3`; 제품 버전은 올리지 않음 |
| 훅 | 실제 `/hooks` 화면에서 신뢰; `hooks/list`로 두 훅의 신뢰와 Windows 명령 확인 |
| 소비 프로젝트 | 외부 Node fixture; 이 저장소의 AGENTS.md·개발 역할 디렉터리는 복사하지 않음 |
| Linux | Docker Alpine 3.20, Python 3.11, Node 22, Bash/Git에서 오프라인 계약·프로세스 회귀 |

원본 로그는 로컬 `D:/Temp/gx-codex-e2e-20260914/`에 있다. 이하 증거 경로는 이 디렉터리 기준이다. 분리된 Codex 홈은 `C:/Users/SQI/.codex/gx-validation-20260914`이며, 설치 캐시는 그 아래 `plugins/cache/gx-final-validation/oh-my-gx/`에 있다. 요약과 원본 파일의 SHA-256은 [증거 JSON](evidence/2026-09-14-codex.json)에 보존한다. 인증 내용·암호화된 내부 메시지는 포함하지 않는다.

## 제품 변경

| 변경 | 해결한 문제 |
|---|---|
| Codex 훅 어댑터 | canonical Bash 매칭, ask→deny, 가드 실패 시 차단, Windows Git Bash 탐색 |
| 훅 설치기 | 기존 훅 보존·멱등 병합·원자적 저장·백업, 경로 인용, 생성된 명령의 실제 실행 확인 |
| 역할·설정 생성기 | 역할 본문 17개와 tools/tier 인덱스, config 템플릿 동봉·드리프트 검사 |
| 공통 Codex 지침 | 실제 도구 스키마·모델 목록, 독립 역할 프롬프트, 질문 응답 대기, 부모 보고서 저장, UTF-8·설치 경로 규칙 |
| 결정 기록 | 질문 ID·복수 선택·자유 입력 보존; Git 소유권 오류 때 해당 저장소만 한정해 브랜치 재조회 |
| `codex-fingerprint.py` | 임시 인덱스·객체 DB로 실제 `.git` 쓰기 없이 코드 지문 생성; 실패/잘못된 지문이면 verify 차단 |
| `codex-project-config.py` | 명시된 JSON 패치만 재귀 병합해 사용자 설정 보존; 무변경 바이트 보존·검증 후 원자적 교체 |
| `codex-run.py` | UTF-8 stdin, 최종 응답·이벤트·stderr 분리, read-only 리뷰, 시간 초과·자식 프로세스 정리 |
| Ralph | Claude/Codex 분기, 설치 스킬·헬퍼·프로젝트 절대경로 전달, 마지막 계약 줄·AC 원장 확인 |
| cross-review | native와 외부 codex 제공자 구분, 결과·이벤트 보존, Codex의 claude 제공자 미지원 명시 |
| 회귀·CI·문서 | Windows/Linux 계약 검사, Claude 회귀 유지, CRLF·pipefail 테스트 오판 수정, 지원 범위·사용법 안내 |

## 전체 흐름 3회 실측

모든 회차에서 설치 캐시의 스킬을 읽었고 실제 RED 자식 호출과 실패 후 구현을 진행했다. 초기 요청에 필요한 선택을 명시했으며 세 회차 도중 추가 사용자 개입은 없었다. 시간은 실행기 벽시계 기준이다.

| 회차 / 증거 | 설치본 | 시간 | 결과 | 판정 |
|---|---|---:|---|---|
| `workflow-run-1/` | 초기 1.32.0 | 831.8초 | setup·RED 실패·구현·전체 6/6·build 성공. 중첩 외부 Codex 초기화 실패, verify 지문 notree | FAIL |
| `workflow-run-2/` | final-2 | 977.8초 | 템플릿 setup, RED 실패, 집중 4/4·전체 7/7·build 성공, native 리뷰 AC 4/4, 유효 지문 | PASS |
| `workflow-run-3/` | final-2 | 1011.45초 | RED 실패, 집중 3/3·전체 6/6·build 성공, native 리뷰 AC 3/3, 유효 지문. setup에서 사용자 config 필드 유실 | 기능 흐름 통과 / S3 FAIL |

2회차 지문은 `019b320:6f64a1a2f3de`, 3회차는 `bf423f2:605b4efea60f`다. native 리뷰는 2회차 Critical/Warning 0, 3회차 Critical 0·Warning 1·Info 2를 반환했다. fixture build가 기존 파일만 구문 검사한다는 관찰도 원본 리뷰에 남겼다. 새 함수는 실제 Node 테스트로 검증했다.

2·3회차는 각각 RED writer, core security audit, QA review, security review의 실제 자식 호출 4개를 기록했다. 모두 `gpt-5.6-sol` / medium이다. 부모 이벤트·도구 인자에서 확인한 값이며 자식의 독립 파일 읽기 로그는 확보하지 못했다.

CLI가 제공한 turn usage는 아래와 같다. 입력에는 반복·캐시 입력이 포함된다. 독립 컨텍스트 크기, 전체 자식 합산 사용량, 청구 금액으로 해석하지 않는다. 비용은 NOT_MEASURED다.

| 회차 | input tokens | cached input tokens | output tokens | reasoning output tokens |
|---|---:|---:|---:|---:|
| 1 | 3,633,470 | 3,493,760 | 16,850 | 2,630 |
| 2 | 4,337,689 | 4,204,672 | 16,148 | 2,851 |
| 3 | 5,102,048 | 4,948,864 | 16,978 | 2,303 |

## 개별 시나리오

PASS는 해당 행의 계약 판정이다. 의도된 차단 확인은 작업 자체의 완료와 구분한다.

| ID | 판정 | 실제 증거 |
|---|---|---|
| S1 설치·새 설정 | PASS | 스킬 17개; 2회차 동봉 템플릿으로 JSON 생성·재파싱 |
| S2 템플릿 누락 | PASS | `s2-missing-template/`: 깨진 배포본에서 경로 보고·중단, config 생성 없음 |
| S3 기존 설정 | 수정 후 PASS | 3회차 실패 후 helper 도입. final-3 `s3-final/`: top-level·nested 사용자 필드 유지, settings.local SHA-256 불변 |
| R1 reviewer | PASS | `r1-reviewer/`: 실제 child가 AC 위반에 spec FAIL→quality FAIL 순서로 반환; 부모 저장, 코드 상태 불변 |
| R2 RED 역할 | PARTIAL | 실제 child·RED 실패·부모 구현 확인. 자식의 src 미열람은 독립 trace 부재로 미확인 |
| R3 humanizer strict | 분리 실행 확인 | `r3-humanizer/`: 서로 다른 fidelity/naturalness child, 모두 gpt-6-astra/high. 2라운드 후 fidelity full_pass, naturalness rewrite_round·human_intervention_required=true. 전체 수락 아님 |
| Q1 질문·응답 | 수정 후 PASS | `q1-question/` 응답 전 결과 없음 → 실제 재개 응답 → `q1-recapture/`에서 ID·선택지·답변을 올바른 브랜치에 기록 |
| H1 보호 브랜치 | PASS | `h1-retry/`: hooks 비활성·main에서 중단, build/stage 없음, HEAD·작업 상태 불변 |
| H2 pending verify | PASS | `h2/verified-hook-denials.json`: 실제 commit이 PreToolUse deny, HEAD 불변 |
| H3 정상 verify 후 commit | PASS, 일반 승인 필요 | `h3-evidence.json`: 테스트 3/3·build·지문 확인, TUI 정확한 로컬 commit 1회 승인 후 빈 커밋 생성 |
| H4 stale verify | PASS | `h4-stale/verified-hook-denials.json`: 검증 후 소스 변경, 실제 commit stale deny, HEAD 불변 |
| 외부 runner | 호스트 실행 PASS | `host-review-final.md`·events·stderr: 설치 runner의 read-only 실제 리뷰 성공, AC 3/3 |
| Ralph | 정상 BLOCKED | final-3 `ralph-final-project/.dev/feat-ralph-final-project/`: 구현·테스트 6/6·build·지문 `98b9ab3:19c67e2086d6` 후 index.lock 권한 오류, 최종 BLOCKED·exit 2. 커밋 완료 아님 |

H3 HEAD는 `a2eb28cdb8150eb843a9ade6d212ff24bb304e34` → `6057582a6e1475fa7882c1802f9a031964f551e9`다. 임시 프로젝트에서 일반적인 1회 승인으로 수행했다. 지속 승인·샌드박스 해제는 없었다. Q1 답변은 테스트 진행자가 실제 Codex 재개 입력으로 제공했다.

## 실측에서 발견해 수정한 문제

1. **지문 실패의 성공 오인:** 임시 인덱스만 분리한 방식은 `.git/objects` 쓰기가 거부됐다. 객체 DB도 분리하고 exit 0·정확한 지문 한 줄을 요구하도록 수정했다. 후속 전체 흐름·H4·H3·Ralph의 실제 샌드박스에서 성공했다.
2. **설정 전체 덮어쓰기:** 3회차에서 사용자 필드가 유실됐다. 구조적 병합 helper를 필수 경로로 만들고 final-3 실제 setup에서 중첩 필드와 Claude 설정 바이트 보존을 재검증했다.
3. **결정 기록 위치·ID:** Git 소유권 검사로 no-branch에 기록되고 ID가 빠졌다. 저장소 한정 재조회·ID 출력을 추가하고 실제 응답 기록을 재검증했다.
4. **설치 루트 오계산:** 첫 Ralph는 `.claude/scripts/`를 찾아 helper를 놓쳤다. 파일/디렉터리 기준 경로와 runner의 절대경로 제공으로 수정했다. 최종 Ralph에서 helper 실행을 확인했다.
5. **Ralph 실행 산출물 스테이징:** 최종 리뷰에서 새 prompt/final/events/stderr와 보관본이 커밋 제외 목록에 빠진 것을 재현했다. 제외 목록과 잔여 검사로 보완했다. 독립 Git fixture에서 실행 산출물 11개는 제외되고 소스·원장 5개는 staged로 유지됨을 확인했다. 마지막 변경은 실제 Git 검증이며 인증 모델 Ralph 재실행은 아니다.

세 번의 전체 흐름 중 두 실패를 최종 설치본의 3연속 PASS로 치환하지 않았다. final-3에서는 변경된 setup·Ralph를 대상으로 실제 회귀를 실행했고 전체 흐름을 다시 3회 반복하지 않았다.

마지막 산출물 제외 변경까지 담은 final-4 export도 별도 검증 홈에 실제 설치했다. 설치 캐시와 소스 바이트, 17개 스킬, 두 훅의 신뢰 상태를 다시 확인했다. final-3와의 동작 파일 차이는 `gx-ralph-iterate/SKILL.md` 한 파일이다. 사용자 기본 홈의 플러그인을 이 검증용 설치로 교체하지 않았다.

## 오프라인 회귀

| 검사 | Windows | Linux |
|---|---|---|
| `test_codex_*.py` | 84/84 PASS | 79 PASS, Windows 전용 5 skip |
| lint consistency | 36/36 PASS | 36/36 PASS |
| 기존 hook 회귀 | 6개 그룹 PASS | 6개 그룹 PASS |
| Claude Ralph | 36/36 PASS | 36/36 PASS |
| behavior runner | 30/30 PASS | 30/30 PASS |
| 생성기 `--check` | PASS | PASS |

Python 합계에는 Codex Ralph 16개, runner 10개, 설정 병합 8개, 지문 4개 등이 포함된다. 전체 결과는 `windows-release-tests.log`, `linux-release-tests.log`와 도메인 로그에 있다. Windows behavior의 한 실행은 B2에서 일시 exit 2였으나 보존 모드 재실행 30/30에서 재현되지 않았다. 실제 CLI 초기화의 일시 capacity·Windows 프로세스 생성 오류도 재시도로 해소됐으며 최초 실패를 보존했다.

## 사용 범위와 남은 제약

- Codex에서 `oh-my-gx:gx-setup 스킬로 준비해줘`, `oh-my-gx:gx-tdd --core로 구현해줘`, `oh-my-gx:gx-cross-review --advisor native로 검토해줘`처럼 이름과 요청을 함께 입력한다. `/skills`에서 설치 항목을 확인한다.
- 부모 Codex 샌드박스 안의 중첩 `codex exec`는 CODEX_HOME 임시 파일 권한으로 초기화가 막힐 수 있다. 이 환경에서는 `--advisor native`가 실제 통과한 경로다. 외부 runner 자체는 호스트 별도 실행으로 검증했다.
- `.git` 쓰기는 일반 승인 정책의 영향을 받는다. 대화형 승인 후 commit은 확인했지만 무인 Ralph 커밋 완료는 확인하지 못했다. 실제 결과는 올바른 BLOCKED다.
- 역할 도구 목록은 프롬프트 지침이며 독립 권한 경계로 강제된다고 보장하지 않는다. RED 소스 미열람은 추가 trace 검증이 필요하다.
- 가드는 실제 pending/stale commit을 차단했으나 임의의 모든 셸 표현을 다루는 보안 경계는 아니다. H2에서 복합 읽기 명령의 오탐도 관찰했다.
- Linux 실제 인증 모델 세션, macOS, 이전 CLI 버전, 릴리스 커밋/태그의 clean Git source 설치는 NOT_MEASURED다. Windows local export 실측과 Windows/Linux 오프라인 회귀 범위만 보고한다.

별도로 요청한 `~/.codex/config.toml`의 `[tui] alternate_screen = "always"`도 반영하고 CLI 파싱을 확인했다.
