# Codex 소비 프로젝트 실제 세션 smoke 계약

기준: Codex CLI 0.154.0, Windows PowerShell + Git Bash 및 Linux Bash. 이 문서는 **실행 절차와 증거 양식**이다. 2026-09-14 Windows 실제 결과는 아래 상태와 [실측 보고서](../docs/reports/2026-09-14-codex-validation.md)에 기록했다. Linux는 오프라인 회귀만 실행했다. 후속 검증에서는 인증된 실제 소비 프로젝트 세션을 돌리기 전까지 `미실행`으로 둔다. 단위 테스트·mock·문구 확인을 PASS로 대체하지 않는다. 각 실행에서 CLI 버전, OS, 설치 cache 절대경로, 사용자 홈과 subprocess 홈, 실제 세션의 모델/effort(도구 trace에 표시된 경우만), 훅 신뢰 상태, 작업 전후 HEAD/index/source 해시를 기록한다. 임시 소비 프로젝트에는 이 저장소의 `AGENTS.md`를 복사하지 않는다. 개발 폴더의 `skill-creator` junction이 설치 스킬 17개에 포함되지 않았는지 확인한다.

## 설치·setup

Windows 예시: `codex.cmd plugin marketplace add bs-koo/oh-my-gx`, `codex.cmd plugin add oh-my-gx@oh-my-gx`, `codex.cmd plugin list --json`. Codex 입력창의 `/skills`에서 GX 스킬을, `/hooks`에서 훅 정의와 사용자 신뢰를 확인한다. Git source(`source:url,url:./`)로 깨끗하게 설치한 cache와 개발용 local source(`source:local,path:./`)를 구분한다. Python/Bash/Git 실행 가능 여부를 확인한다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| S1 | 새 임시 Git 프로젝트, 깨끗한 설치 cache, gx-setup | GX 스킬 17개 발견; 생성된 `.claude/config.json` JSON 파싱 성공; 설치 cache·홈 경로 | PASS (2회차) |
| S2 | `config.template.json`을 제거한 임시 배포 복사본 | setup 중단·실패 경로 보고; `config.json 생성 완료` 미표시; 후속 Edit 없음 | PASS (누락 시 중단) |
| S3 | 기존 프로젝트 config와 Claude permissions가 존재 | 기존 config 값 보존; `.claude/settings.local.json` 바이트 불변; 허위 권한 완료 표시 없음 | 수정 후 PASS (final-3) |

## 역할·질문

R2는 상세 tool trace가 없으면 `src 미열람`을 **미확인**으로 기록한다. prod 해시 불변만으로 읽기 격리를 입증하지 않는다. 모델/effort 티어도 하네스 이벤트가 제공한 값만 실측으로 적는다. 결과 보고서 파일을 쓰지 못하는 읽기 전용 역할은 자식 반환을 부모가 저장한다.

Q2는 인증된 실제 소비 프로젝트의 Codex 세션에서 두 질문을 각각 실행한다. gx-context에는 문서 기반 개방형 답변이 필요한 입력을 주고 UI Other에 답한다. gx-dev에는 모드·프로파일 선택이 필요한 입력을 주고 실제 선택에 답한다. 두 경우 모두 표시된 질문·선택지와 답변 전후 도구 trace, 같은 질문 id로 남은 `codex_hook.py capture` 결정 기록을 보관한다. 질문이 Plan 모드에서만 제공되거나 자연어 질문으로 표시되면 사용한 모드·도구와 실제 답변을 따로 기록한다. 실제 세션을 실행하지 않은 경우 Q2는 `미실행`이다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| R1 | 고의적 AC 위반 fixture를 reviewer child에 전달 | spec 판정이 quality보다 앞섬; 코드 불변; 두 verdict 순서·내용 | PASS |
| R2 | red-writer에 실패 테스트 추가 요청 | 구현 src 미열람 trace; prod 해시 불변; 실제 RED 테스트 실패 | PARTIAL (src 미열람 미확인) |
| R3 | 작은 한국어 문단을 humanizer strict로 처리 | fidelity/naturalness 서로 다른 child id; `04_fidelity.json`의 `audit_verdict`, `05_naturalness.json`의 `verdict` | 역할 분리 확인 / strict 재작성 필요 |
| Q1 | 기본 모드에서 선택 질문 | 실제 답변 전 의존 작업 없음; 질문 id/선택지/실제 답변의 결정 기록 보존 | 수정 후 PASS |
| Q2 | gx-context 문서 기반 개방형 질문과 gx-dev 모드·프로파일 질문 | 각 질문의 stable snake_case id; 질문 3개 이하; 질문별 선택지 3개 이하; 명시적 Other option 0개; UI Other 자유 입력과 선택 답변의 decision capture가 같은 id로 기록됨 | 미실행 (1.33.0 후보에서도 UI Other·capture 본시험 미완료) |

## 보호 훅·커밋

실제 hook 로드는 임시 테스트 hook에서 무해한 `Write-Output GX_HOOK_SENTINEL` 또는 `printf GX_HOOK_SENTINEL`을 **deny**하는 것으로 확인한다. 배포 hook에는 sentinel 규칙을 넣지 않는다. `/hooks`에서 테스트 정의를 확인·신뢰한 후 무해한 명령만 실행한다. 강제 push는 JSON fixture로만 테스트한다. 각 시나리오는 격리된 임시 프로젝트에서 HEAD/index 해시를 기록한다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| H1 | main 브랜치, hook 비활성, gx-commit 요청 | HEAD/index 불변; 보호 브랜치 안내; 빌드·스테이징 없음 | PASS |
| H2 | feat/t, pending verify, 신뢰된 GX hook, 빈 로컬 commit 시도 | deny event와 이유; HEAD 불변 | PASS (deny) |
| H3 | feat/t, 테스트 통과 + 현재 코드 지문, 로컬 commit | 정상 완료; HEAD 변경; 실제 테스트 증거 | PASS (일반 1회 승인) |
| H4 | H3 검증 후 코드 변경, 재커밋 | stale fingerprint deny; HEAD 불변 | PASS (stale deny) |

## 교차 리뷰·네이티브 러너

Claude companion을 설치하지 않은 임시 소비 프로젝트에서 `--advisor codex`를 실행한다. Codex CLI review 모드가 read-only인지 source/index/HEAD 해시로 확인하고, 결과의 AC 매트릭스·신규 위험·총평 및 실행 하네스/확인 가능한 실제 모델을 기록한다. Codex 호스트의 `--advisor claude`는 미지원 안내로 끝나며 native 성공처럼 표시되지 않아야 한다. `--advisor native`는 현재 하네스의 내부 역할 리뷰로 수행한다. Codex 인증이 없거나 실제 세션을 실행하지 않으면 모두 `미실행`으로 남긴다.

## 2026-09-14 추가 결과

외부 Codex runner는 호스트에서 실제 read-only 리뷰에 성공했다. 부모 Codex 샌드박스의 중첩 CLI는 홈 임시 파일 권한으로 실패했으며, 전체 흐름 2·3회차는 명시한 `--advisor native`를 사용했다. Ralph final-3는 구현·테스트·build·유효 지문 뒤 커밋 권한 오류를 BLOCKED(exit 2)로 반환했다. 최종 산출물 제외 보완은 임시 Git 스테이징으로 별도 검증했다. 전체 흐름 3회의 실패·수정 이력, 역할·토큰·시간 및 미측정 항목은 실측 보고서를 따른다.

## 1.33.0 후보 후속 검증 (2026-09-16)

후보 브랜치 `release/core-skills-hardening`을 `--ref`로 지정해 Git marketplace를 추가하고, 인증된 Codex 검증 홈에 `oh-my-gx@oh-my-gx` 1.33.0을 설치했다. 설치 cache와 후보 snapshot HEAD는 [실측 보고서](../docs/reports/2026-09-15-core-skills-codex-validation.md)에 기록했다. 임시 소비 프로젝트의 `AGENTS.md`는 복사하지 않았다.

| ID | 실제 시도 | 결과 |
|---|---|---|
| S45 | `src/service`에서 gx-tdd `--phase design` | 미실행: 실제 세션은 시작했으나 스킬 파일 읽기 전 Codex `exec_command` 도구 초기화가 반복 실패해 setup·design 증거가 없다. |
| S46 | gx-context `--from` 질문 | 미실행: 1.33.0 스킬 읽기는 확인했으나 중첩 cwd의 경로·`context/` 모드 전제가 맞지 않아 본시험 질문·결정까지 진행하지 못했다. |
| Q2 | gx-context UI Other·id capture와 gx-dev 선택 답변 | 미실행: UI Other 입력, 동일 id의 `codex_hook.py capture`, gx-dev 질문 세션이 없다. |

`gx-context`는 현재 caller cwd의 `context/`와 `--from` 상대경로를 사용한다. 임시 프로젝트의 `context/`와 `requirements/order.md`가 루트에 있으면 gx-context smoke는 프로젝트 루트에서 시작한다. gx-tdd의 중첩 cwd 검증은 별도 시나리오로 유지한다. 이 후보의 런타임 차단과 중첩 경로 관찰은 단위 테스트 PASS로 대체하지 않는다.

## 시각화

`gx-visualize`(1.34.0에서 추가된 18번째 스킬)와 gx-dev·gx-tdd phase-complete의 구조 시각화 제안 게이트(Step 5.5)의 실제 Codex 세션 검증이다. 로컬 단위 테스트나 mock 결과를 PASS 근거로 대체하지 않는다. V1~V3은 기능 표면, V4~V5는 Codex에서만 드러나는 위험이다. 인증된 실제 소비 프로젝트 세션을 실행하지 않은 항목은 `미실행`으로 남긴다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| V1 | Codex `/skills`에서 gx-visualize 발견 후, 임의 Git 프로젝트에서 `gx-visualize service --scope all` 실행 | `.dev/architecture/`에 도메인별 `{domain}.ir.json`·`{domain}.html` 생성(프로젝트 전체를 매 실행 재스캔, 증분·매니페스트 없음, 커밋하지 않음); 도메인마다 개별 판정(일부 Archify 통과·일부 폴백 공존이 정상) | 미실행 |
| V2 | Archify가 설치되지 않았거나 자동 설치가 실패하는 격리 환경에서 `gx-visualize --backend auto` 실행 | 실패한 Archify 시도가 receipt의 attempts에 기록됨; Mermaid → 정적 HTML로 폴백해 표가 생성됨; report에 그림(다이어그램) 부재가 명시됨 | 미실행 |
| V3 | Archify·Mermaid·static 백엔드가 모두 실패하는 환경에서 실행 | `html_path: null`; `visualization_status: failed`; 재실행 명령 반환; 이전 stale HTML이 남지 않음 | 미실행 |
| V4 | gx-dev 또는 gx-tdd phase-complete 대화형 세션이 Step 5.5(구조 시각화 제안)에 도달 | `AskUserQuestion` 자리에 실제 제공되는 질문 도구로 대응했는지, 실제 사용자 응답을 기다렸는지 기록; 동기 질문 도구가 현재 모드에 없을 때의 처리 방식(자연어 질문 등)을 기록 | 미실행 |
| V5 | Archify 자동 설치의 `npx` 실행이 Codex 승인·샌드박스로 차단되는 환경에서 `--backend auto` 실행 | 차단이 예외가 아니라 폴백으로 처리됨; 설치 시도 기록이 receipt에 남음; 이어서 Mermaid → static 폴백까지 진행됨 | 미실행 |
