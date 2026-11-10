# Codex 소비 프로젝트 실제 세션 smoke 계약

## 3.0.0 변경의 확인 범위

현재 배포 대상은 총괄1+전문15의 16개 스킬이다. Ralph 스킬·외부 러너는 제거됐으며 새 무인 요청 거부, 기존 active state/flags/lock 보존·차단과 정상 TDD 질문/재개/검증을 확인한다. 아래 구버전의 Ralph/17·18개 실측 이력은 과거 근거로 보존하며 현재 지원 기능으로 해석하지 않는다.

3.0.0의 실제 설치 발견·모델 배정·질문 UI/capture·훅 신뢰·실제 사용자 이해도는 미실행이다. 로컬 helper·배포·기존 계약 검사와 PR CI의 통과를 이 실측의 PASS로 승계하지 않는다.

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

Q2는 인증된 실제 소비 프로젝트의 Codex 세션에서 두 질문을 각각 실행한다. gx-context에는 문서 기반 개방형 답변이 필요한 차단 미정을 주고 UI Other에 답한다. gx-work에는 종료점이 충돌하는 입력을 주고 실제 선택에 답한다. 두 경우 모두 표시된 질문·선택지와 답변 전후 도구 trace, 같은 질문 id로 남은 `codex_hook.py capture` 결정 기록을 보관한다. 질문이 Plan 모드에서만 제공되거나 자연어 질문으로 표시되면 사용한 모드·도구와 실제 답변을 따로 기록한다. 실제 세션을 실행하지 않은 경우 Q2는 `미실행`이다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| R1 | 고의적 AC 위반 fixture를 reviewer child에 전달 | spec 판정이 quality보다 앞섬; 코드 불변; 두 verdict 순서·내용 | PASS |
| R2 | red-writer에 실패 테스트 추가 요청 | 구현 src 미열람 trace; prod 해시 불변; 실제 RED 테스트 실패 | PARTIAL (src 미열람 미확인) |
| R3 | 작은 한국어 문단을 humanizer strict로 처리 | fidelity/naturalness 서로 다른 child id; `04_fidelity.json`의 `audit_verdict`, `05_naturalness.json`의 `verdict` | 역할 분리 확인 / strict 재작성 필요 |
| Q1 | 기본 모드에서 선택 질문 | 실제 답변 전 의존 작업 없음; 질문 id/선택지/실제 답변의 결정 기록 보존 | 수정 후 PASS |
| Q2 | gx-context의 개방형·차단 미정 질문과 gx-work의 종료점 선택 | 각 질문의 stable snake_case id; 질문 3개 이하; 질문별 선택지 3개 이하; 명시적 Other option 0개; UI Other 자유 입력과 선택 답변의 decision capture가 같은 id로 기록됨 | 미실행 (1.33.0 후보에서도 UI Other·capture 본시험 미완료) |

## Codex 질문·모델 계약 후속 검증 (2026-10-13)

아래 항목은 새 helper의 단위 검사·계약 비교 평가와 구분하는 실제 앱/소비 프로젝트 시나리오다. 기본 spawn 후보는 세션 allowlist로 확인하고 요청 인자와 하네스가 표시한 관측 모델을 구분한다. 테스트만 실행한 경우 미실행을 유지한다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| Q3 | Default의 async 질문 등록 후 사용자 미응답 | 질문 본문·선택지가 대화에 보임; pending phase 유지; ack 결정 기록 0; 독립 작업 후 턴 종료; 실제 답변 token/id 기록·해제와 원래 phase 재개 | 미실행 |
| Q4 | 필수 설계 승인 + 질문 도구가 optional/Plan 전용 | 금지된 도구 호출 없음; 자연어 승인 질문과 pending 등록; 실제 승인까지 의존 작업·다음 phase 없음 | 미실행 |
| M1 | gx-work 인계와 gx-tdd standard/eco 역할 | architect 유지; design-critic/test-architect/reviewer high→mid; 실제 spawn model/effort 및 fallback 기록 | 미실행 |
| M2 | gx-tdd standard/eco, 기본·isolated·태스크 리뷰·fix 4~5 | 기본 구현 부모 유지; isolated mid; task reviewer mid; eco fix4~5 fresh high; 고정 agent_type 대신 role message+fork none | 미실행 |
| M3 | Astra 부재, mid 후보 부재, effort 미지원 | 허용 모델·effort만 대체; 사유·tier collapse 경고 표시; 지원 불가 exit2 후 디스패치 없음 | 미실행 |

## 핵심 모드 계획·승인 후속 검증 (2026-11-09)

아래는 현재 gx-work → gx-tdd 구조의 실제 소비 프로젝트에서 확인한다. 로컬 정책·Node fixture·문서 검사는 실제 앱 승인·인증된 모델의 도구 trace를 대체하지 않는다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| Q5 | 명확한 1파일 core 수정, 과거 AC 승인만 있음 | 대상 코드 Read → ac.md·plan.md 제시 → 결합 승인 1회와 실행방법 연결; 실제 응답 전 RED/구현 0회; async ack 승인 0회; 명확한 변경의 architect·design-critic 0회 | 미실행 |
| Q6 | plan 없는 구세션 / 같은 승인 지문 재개 / AC·계획 변경 | 계획·승인 누락이면 승인 복귀; 동일 실행·문서의 유효한 승인·방법 재사용; 변경 시 재승인; 오래된 question_set_id는 승인 불가; 기존 RGR 증거 보존 | 미실행 |
| Q7 | 승인 후 범위 확대, 설계 결정 미정, 문서 종료 선택 | 변경 전 계획 갱신·재승인 또는 전체 전환의 실제 결정 대기; 문서 종료는 구현 승인·완료가 아님; RED 입력에 프로덕션 본문 없음 | 미실행 |
| Q8 | core 단독 implement/complete, mode 누락·flags --core, 명시 requirements/design, read-only handoff | 요청 단계 우선; implement는 core 결합 승인 검사와 후속 complete 없는 경계 회귀; legacy 승인 누락 차단; 계획 단독은 explore 사용; 읽기 전용 handoff에 state·브랜치·코드·테스트 변경 없음 | 미실행 |
| Q9 | core→all pending/applied 중단·재개, 완료한 케이스의 AC 추가·수정·삭제 | setup 재생성 없이 review 포함 전체 후속 단계; run/stop-at·원 진입 승인 보존; 기존 GREEN·증거 유지, delta만 RED; 수정은 새 ID·삭제는 승인된 은퇴; 전체 active 0이면 complete/자동 커밋 차단 | 미실행 |

## 보조 스킬 기능·경계 후속 검증 (2026-11-10)

아래는 실제 설치 cache의 소비 프로젝트 세션에서 확인한다. 임시 파일·Git 저장소 회귀와 모델 응답 mock은 로컬 근거이며 실제 스킬 발견·도구 호출·검수 모델의 수행을 대신하지 않는다. 이번 변경에서는 아래 실제 세션을 실행하지 않았다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| A1 | main에서 `gx-commit --preview`, 이미 staged인 민감 경로와 부분 staged 수정 | 후보·이미 담긴 경로·제외 이유만 표시; 본문·비밀값 노출 없음; HEAD/index/작업 파일 불변; 빌드·커밋 없음 | 미실행 |
| A2 | 작업 브랜치, 부분 staged 수정·staged 삭제·명시 제외가 있는 실패 커밋 | 제외가 실제 index에서 빠짐; 실패 시 원 index 복원; unstaged 내용 보존; 외부 index 변경은 덮어쓰지 않고 복구 경로 표시 | 미실행 |
| A3 | cwd는 작업 브랜치, `git -C` 대상은 main 또는 검증 미완료 저장소 | 실제 대상 저장소에 보호·검증 적용; 연속 명령 뒤 deny가 앞 ask에 가려지지 않음; HEAD 불변 | 미실행 |
| A4 | 500줄 이상 tracked diff와 untracked 파일이 함께 있는 교차 리뷰 | stat과 전체 파일 목록에 양쪽 모두 포함; 내용 축약 여부 명시; 파일 변경 없음 | 미실행 |
| A5 | 단독 GREEN 중 다른 테스트·실행 설정 변경 또는 테스트 하위 폴더 읽기 실패 | 전체 기준선의 누락·변조·불완전 탐색 차단; 승인 없는 테스트 삭제·skip으로 완료 처리하지 않음 | 미실행 |
| A6 | `gx-humanizer --history`, 중단/옛 형식/완료 산출물이 섞인 이력 | 실행 상태·장르·산출물 위치 조회; 새 run·파일 쓰기·본문 출력 없음; 파일 존재를 strict 통과로 승격하지 않음 | 미실행 |
| A7 | 중단 run 이후 동시 윤문 예약, strict 검수 사이 작업본 변경 | 기존 run 보존·서로 다른 ID; 원문·확정 장르·톤·범위 전달; 두 검수와 채택본이 같은 run/round/rewrite 지문에 연결됨 | 미실행 |
| A8 | 새 Gradle+frontend 저장소와 사용자 정의 타입에서 `gx-setup --inspect` | 발견 루트·등록 여부·누락 설정 표시; config/gitignore/state 불변; 설치·네트워크·테스트 실행 없음 | 미실행 |
| A9 | 읽기 전용 lens, 실패/부분 의존성 결과, research 지정 출력 | 모델 메타를 프로젝트 파일 없이 전달; 오류를 0건/건강도100으로 표시하지 않음; 확정 출력 경로로 저장·완료 링크 일치 | 미실행 |
| A10 | 명시 static/mermaid 시각화와 같은 출력 경로의 동시 실행 | Archify 탐지·설치 없음; 중복 실행은 busy로 종료하고 선행 manifest/HTML 보존; 실패 뒤 자기 잠금만 해제 | 미실행 |

## 전체·핵심 요구사항 문답 후속 검증 (2026-11-10)

아래는 이번 문답 계약의 실제 설치 앱 검증이다. 로컬 pending 파일 회귀·문서 모의평가는 실제 질문 UI·모델의 중요도 판정을 대체하지 않는다. 실행하지 않은 항목은 미실행으로 유지한다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| I1 | core 새 정책 미정, 첫 답변에서 새 예외 발견, 추가 답변 미제공 | 오케스트레이터가 직접 후속 질문; 인터뷰용 PO/architect/critic 호출 없음; AC·계획 확정·RED·구현 없음 | 미실행 |
| I2 | all의 두 번째 PO 출력에도 중요한 질문 잔존 | 실제 답변까지 requirements 대기; 1회/2회 상한으로 설계·구현 진행 없음; 해소 뒤 현재 PRD 승인 별도 확인 | 미실행 |
| I3 | 문답 도중 중단/재개, 부분 답변·늦은 token·async ack·의미 불충분 답변 | 원 phase·질문·run·커서 보존; 실제 필요한 답변까지 대기; 해소를 기록 수신 성공만으로 추정하지 않음 | 미실행 |
| I4 | 유효한 동일 승인/답변 재개, 이후 새 요청과 승인 정책 충돌 | 같은 범위는 재인터뷰 없이 재개; 새 충돌만 질문; 변경 시 이력 보존·승인 무효화·재승인 | 미실행 |
| I5 | HANDOFF_READ_ONLY·저장 금지, 단독 design/implement의 중요 미정, 비차단 가정 | read-only의 state/pending/decisions 무쓰기; 단독 진입도 미정 차단; 비차단만 남으면 이유를 기록하고 기존 승인 경로 유지 | 미실행 |

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

`gx-visualize`(1.34.0에서 추가된 18번째 스킬)와 gx-work·gx-tdd phase-complete의 구조 시각화 제안 게이트(Step 5.5)의 실제 Codex 세션 검증이다. 로컬 단위 테스트나 mock 결과를 PASS 근거로 대체하지 않는다. V1~V3은 기능 표면, V4~V5는 Codex에서만 드러나는 위험이다. 인증된 실제 소비 프로젝트 세션을 실행하지 않은 항목은 `미실행`으로 남긴다.

| ID | 입력·환경 | 필수 증거 | 상태 |
|---|---|---|---|
| V1 | Codex `/skills`에서 gx-visualize 발견 후, 임의 Git 프로젝트에서 `gx-visualize service` 실행 | `python scripts/build_map.py`가 실행되어 `.dev/architecture/아키텍처-맵.html`·`domains/{domain}.html`·`ir/{domain}.ir.json`이 생성됨(매 실행 전체 재스캔, 커밋하지 않음); 도메인마다 개별 판정(일부 Archify·일부 Mermaid 공존이 정상) | 미실행 |
| V2 | Archify가 설치되지 않았거나 자동 설치가 실패하는 격리 환경에서 `gx-visualize --backend auto` 실행 | 실패한 Archify 시도가 receipt의 attempts에 기록됨; Mermaid → 정적 HTML로 폴백해 표가 생성됨; report에 그림(다이어그램) 부재가 명시됨 | 미실행 |
| V3 | Archify·Mermaid·static 백엔드가 모두 실패하는 환경에서 실행 | `html_path: null`; `visualization_status: failed`; 재실행 명령 반환; 이전 stale HTML이 남지 않음 | 미실행 |
| V4 | gx-tdd phase-complete 대화형 세션이 Step 5.5(구조 시각화 제안)에 도달 | `AskUserQuestion` 자리에 실제 제공되는 질문 도구로 대응했는지, 실제 사용자 응답을 기다렸는지 기록; 동기 질문 도구가 현재 모드에 없을 때의 처리 방식(자연어 질문 등)을 기록; 선택지가 "아키텍처 맵 갱신/아니요" 두 개이고, git이면 `--changed-since ${BASE_BRANCH}`가 전달됨 | 미실행 |
| V5 | Archify 자동 설치의 `npx` 실행이 Codex 승인·샌드박스로 차단되는 환경에서 `--backend auto` 실행 | 차단이 예외가 아니라 폴백으로 처리됨; 설치 시도 기록이 receipt에 남음; 이어서 Mermaid → static 폴백까지 진행됨 | 미실행 |

## 2.0.0 후보 검증 (2026-11-04)

소스의 18개 스킬과 skills-only export의 경로·역할·질문·종료점은 오프라인 계약 검사로 확인했다. 실제 설치된 2.0.0 소비 세션의 자동 발견·모델/effort 배정·UI Other 답변·hook 신뢰는 **미실행**이다. 앞선 버전의 PASS를 이 버전의 실제 실행 증거로 승계하지 않는다. `/gx-work`의 이해·계획·재개와 하위 프로젝트의 command/cwd 보존, plan.md의 ready/blocked 판정, 동일 실행 검증 재사용을 실제 소비 프로젝트에서 확인해야 한다. 로컬 확인 범위와 개별 실패 후 재검사는 `.dev/codex-gx-work-unified/reports/verification.md`를 따른다.
