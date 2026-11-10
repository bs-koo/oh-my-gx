# gx-work 전수조사 보고서 (2026-11-09)

- 기준: main `6ef7517` (v3.0.0 태그 + #102). 줄 번호는 이 커밋 기준이다.
- 범위: gx-work 스킬과 helper(`scripts/gx-work.py`), gx-tdd·gx-context·gx-commit·gx-pull-request와의 연결, 사용자 문서.
- 방법: 세 갈래 정적 대조(helper 코드, 인계 계약, 트리거·문서), 자동 검사, 실세션 관측(kreb-grep-2026-web W118, 설치 캐시 3.0.0).
- 증거 표기: [실측] 직접 재현·관측, [문서] 원문 대조로 확인, [추정] 해석 여지 있음.

## 자동 검사 (main 기준)

- `sync-codex-resources.py --check` 통과
- unittest: gx-work 64개, Codex 284개, context 50개 통과
- 정합성 린트 36항목 통과
- 훅 회귀: 부하 중 1회 실패([6/6] 렌더링 자체검증 35초), 단독 재실행 통과 → F45

## 실세션 관측 (kreb W118, 설치 3.0.0)

gx-work → gx-context(W118 행 추가) → 워크트리 생성 → 진입·종료점 질문(한 번의 질문 호출) → handoff → gx-tdd setup → requirements까지 정상 진행했다. 도중에 모델이 스스로 우회한 문제:

- work-id `W118`을 helper가 거절 → work-id를 빼고 목표 문장에만 남김 (F01)
- handoff 오류 JSON이 stdout 리다이렉트로 파일에 들어가 화면에는 "인계 형식 오류"만 보임 → 소스 grep으로 원인 확인 (F30)
- question-set-id에 고정 id(`gx_work_tdd_entry`)를 전달, helper가 임의 문자열을 수용 (F11, F24)
- 미커밋 `.dev/plan.md`가 있었지만 "방금 만든 워크트리"라고 판단해 자동 stash를 생략 (F03)
- 목표 문장에 RESUME 키워드 "이어서"가 있었으나 모델 판단으로 오판 회피 (F22)
- 참고: document-pre 검사가 프로젝트 고유 형식(context/status.md, plan.md)에 구조 오류 7건을 내 예외로 기록

## 항목 목록

| ID | 등급 | 증거 | 요약 | 담당 |
|---|---|---|---|---|
| F01 | P1 | 실측 | W ID가 `W`+두 자리로 고정 | G1·G2·G3·G4 |
| F02 | P1 | 문서/추정 | 자연어 요청이 gx-work로 들어온다는 보장 없음 | G2·G3 |
| F03 | P1 | 문서/실측 | setup 자동 stash가 run 입력을 치우고 다른 run 변경을 옮김 | G2 |
| F04 | P1 | 문서/재현 | 인계 재검증 실패 시 출구 없음(종료점 변경·경로 이동·덮어쓰기) | G1·G2·G3 |
| F05 | P1 | 실측 | #102가 버전·CHANGELOG 없이 머지 | 부모 |
| F06 | P2 | 재현 | route가 git 오류·detached HEAD를 state 없음으로 처리 | G1 |
| F07 | P2 | 재현 | 완료 state의 pending이 옛 run을 복원, gx-dev pending이 migration보다 먼저 | G1 |
| F08 | P2 | 재현 | 다른 목표+다른 종료점이 범위 검토 대신 stop-at 오류 | G1 |
| F09 | P2 | 재현 | Ralph 실행 판별이 설명·파일명·삭제 요청까지 막음 | G1 |
| F10 | P2 | 재현 | BOM·여러 줄 `.active`/config/state 오판, JSON BOM·UTF-16 거절 | G1 |
| F11 | P2 | 재현 | 진입 승인이 질문 기록(pending/answered)과 연결되지 않음 | G1 |
| F12 | P2 | 재현 | validate-plan과 `handoff --plan` 판정 불일치, 중복 키·전각 숫자 | G1 |
| F13 | P2 | 재현 | state.md 파싱 취약, stop-at 값 미검증 | G1 |
| F14 | P2 | 재현 | 요청 인계가 차단 미결정·결정 충돌을 허용 | G1·G3 |
| F15 | P2 | 재현 | CLI 오류가 JSON이 아닌 경로(argparse usage, RecursionError) | G1 |
| F16 | P2 | 재현 | project-root·VCS 판별이 gx-tdd와 다름 | G1·G3 |
| F17 | P2 | 문서/재현 | 미응답 질문의 수명 관리(대조·폐기)가 없음 | G1·G3·G2 |
| F18 | P2 | 문서 | run 입력 저장 위치가 흩어지고 `.dev/main/`에 쌓임 | G3·G2·G4 |
| F19 | P2 | 문서 | "계획만" 경로의 약속과 실제가 다름 | G3·G2 |
| F20 | P2 | 문서 | 테스트 러너 부재 시 막다른 안내(gx-work로 별도 수행, gx-dev) | G2 |
| F21 | P2 | 문서 | phase-setup이 호출할 수 없는 gx-setup을 Skill로 호출 | G2 |
| F22 | P2 | 문서/실측 | `--handoff`가 있어도 목표 문장이 키워드 판정을 거침 | G2 |
| F23 | P2 | 문서 | PR 단계에서 베이스 브랜치 재질문 | G2·G4 |
| F24 | P2 | 문서/실측 | Claude Code 경로의 플러그인 루트·질문 기록 규칙 공백 | G3 |
| F25 | P2 | 문서 | work-id·실행 방식·모델이 인계로 전달되지 않음 | G1·G2·G3 |
| F26 | P2 | 문서 | 같은 브랜치명 새 실행이 진행 중 state를 덮어씀 | G2 |
| F27 | P2 | 문서 | gx-context 직접 호출 시 "개발까지" 의도 소실 | G3 |
| F28 | P2 | 문서 | "커밋만/PR만"이 저장된 stop-at에 막힘 | G2·G3 |
| F29 | P3 | 정적 | gx-work SKILL.md 밀도·중복 | G3 |
| F30 | P3 | 실측 | route 결과값 미문서화, helper 오류 메시지 불충분 | G1·G3 |
| F31 | P3 | 정적 | 결정 기록 훅이 python3만 찾음 | G4 |
| F32 | P3 | 정적 | 현행 스킬·에이전트·문서의 gx-dev 잔재 | G2·G3·G4 |
| F33 | P3 | 문서 | 같은 결정을 다시 묻는 지점 4곳 | G2·G3·G4 |
| F34 | P3 | 문서 | 사용자 문서와 실제 동작 불일치 | G4 |
| F35 | P3 | 정적 | gx-work 문서의 python 실행 파일 규칙 누락 | G3 |
| F36 | P3 | 문서 | 레거시(Ralph·gx-dev) state에서 빠져나오는 절차 없음 | G1·G2·G3 |
| F37 | P3 | 문서 | gx-work 경유 조사가 파일 저장·.gitignore 수정 | G3 |
| F38 | P3 | 문서 | gx-context 재질문·자동 확장, 임시 인계 디렉토리 공유 | G3 |
| F39 | P3 | 문서 | gx-work가 아는 연결 대상과 W 조회 절차 부족 | G3 |
| F40 | P3 | 문서 | 커밋→PR 체이닝 미배포, PR 스킬의 검사 순서 | G4 |
| F41 | P3 | 문서 | 낡은 참조 | G2·G3 |
| F42 | P3 | 문서 | 인계 문서의 지문·run-id·인코딩·project-root 설명 | G3·G2 |
| F43 | P3 | 문서 | 승인 근거·계획 종료 재개의 모호성 | G2 |
| F44 | P3 | 정적 | 린트 [18/36] `.active` 소비자 목록에 gx-work.py 없음 | 부모 |
| F45 | — | 관찰 | 훅 회귀 [6/6] 부하 시 시간 초과 | 조치 없음 |
| F46 | — | 관측 | 하네스 스킬 목록에서 일부 설명 누락 | F02로 완화 |
| F47 | — | 설계 유지 | 명시 요청을 진입 답변으로 치지 않음 | G3(문구만) |

## 상세

### P1

**F01. W ID가 두 자리로 고정** [실측]
- 위치: `scripts/gx-work.py:345`, `gx-context/scripts/development.py:150-151`, `gx-context/scripts/plan.py:70`, `gx-context/modes/plan.md:219`, `gx-tdd/references/intent-routing.md:30,57,61`, README·현행 문서. 반대 서술: `gx-work/references/decision-history.md:7`("자릿수를 제한하지 않는다").
- 시나리오: kreb는 W118까지 왔다. 인계 생성이 `work-id 형식 오류`로 실패하고, `--work` 연결과 plan.md 착수·완료 자동 기록이 모두 불가하다.
- 수정: `W[0-9]{2,}`(ASCII 숫자만, 기존 `W01` 유지)로 통일한다. 문장 속 토큰은 `(?<![A-Za-z0-9_-])W[0-9]{2,}(?![A-Za-z0-9_-])`. W118·W1000 허용, `W1`·`W０１`·`W-01` 거절을 회귀로 둔다. 과거 설계 기록(docs/specs, docs/superpowers)은 고치지 않는다.

**F02. 자연어 단일 진입 비보장** [문서/추정]
- 위치: `.claude/rules/skill-routing.md:27-43`(개발 저장소 전용, 미배포), `gx-tdd/SKILL.md:3`, `gx-work/SKILL.md:3`, `gx-context/SKILL.md:3`. gx-setup은 소비 프로젝트에 라우팅을 쓰지 않는다.
- 시나리오: "버그 고쳐줘"·"이어서 해줘"는 gx-tdd 설명과 더 잘 맞아 gx-work의 조사·문서 연결·진입 확인을 건너뛴다.
- 수정: gx-work 설명 앞부분에 "기능 구현·버그 수정·PR까지·작업 재개·W01 시작·계획만"을 두고, gx-tdd는 "TDD를 명시했거나 gx-work에서 인계된 실행·TDD 재개"로 좁히며, gx-context에는 "개발까지 요청은 gx-work"를 넣는다. gx-work 트리거 eval 세트를 추가한다(실행은 NOT_RUN으로 기록).

**F03. setup 자동 stash** [문서/실측]
- 위치: `gx-tdd/phases/phase-setup.md:70-97`(2.1~2.3).
- 시나리오: (a) gx-context가 만든 미커밋 plan.md, `.dev`를 공유하는 프로젝트의 intake·handoff가 Step 2.1~5 동안 사라져 3.0.4·3.0.5가 실패하거나 pop이 충돌한다. (b) 다른 run이 진행 중인 브랜치에서 새 run을 시작하면 그 run의 미커밋 코드가 새 브랜치로 옮겨진다. (c) Codex 질문 대기 중 stash된 채 세션이 끝난다.
- 수정: 베이스 브랜치 위(또는 HEAD가 베이스와 같음)이고 미커밋 변경이 이번 run 입력뿐이면 stash 없이 작업 브랜치를 만든다. 다른 진행 중 run의 브랜치에서 미커밋 변경이 있으면 stash하지 않고 중단해 별도 워크트리를 안내한다. stash가 필요하면 ref를 state 생성 전에도 남길 위치를 정한다.

**F04. 인계 재검증 실패 시 출구 없음** [문서/재현]
- 위치: `gx-work/references/handoff.md:53`, `gx-tdd/phases/setup-resume.md:38`, `phase-complete.md:27`, `references/plan-handoff.md:8`, `pipeline-state.md:84,95,164`, `scripts/gx-work.py:309-320`.
- 시나리오: (a) verify로 진행 중인 run에 "이어서 PR까지" → state를 갱신해도 handoff의 종료점이 달라 재개가 진입 확인에서 멈춘다. (b) 지문에 절대경로가 들어가 브랜치 이름 변경·다른 PC·다른 워크트리에서 재개하면 실패한다. (c) 고정 이름 handoff.json이 다음 run에 덮어써진다.
- 수정: helper `reissue`(같은 run-id, 종료점 변경은 실제 사용자 결정 근거 필수), handoff schema v2(프로젝트 상대경로 지문, v1 검증 호환), run 입력은 `.dev/<run-id>/`에 저장, gx-tdd 재개의 실패 분기에 재발급 절차를 연결한다.

**F05. #102가 버전 없이 머지** [실측]
- `6ef7517`(#102)이 v3.0.0 태그 뒤인데 버전이 3.0.0이고 CHANGELOG가 없다. 설치 캐시 3.0.0과 gx-tdd 12개 파일이 다르고 `core-planning.md`·`core-replanning.md`가 없다.
- 수정: 3.1.0과 CHANGELOG, 린트 [1/36]에 "태그 이후 배포 경로 변경 시 버전 동일 금지" 검사, `.claude/rules/release.md`에 규칙 추가.

### P2

- **F06** [재현] `gx-work.py:91-94`: git 오류·detached HEAD → state 없음. 수정: "not a git repository"만 state 없음, 그 밖의 git 오류는 JSON 오류(exit 2), detached HEAD는 읽기 전용 결과, Codex용 `--git-safe-directory <확인된 프로젝트 경로>`(명령별 `-c safe.directory=`, 전역 설정 금지).
- **F07** [재현] `gx-work.py:116-142`: 완료 gx-tdd state + pending → 옛 run-id·목표·종료점 반환. gx-dev in_progress/completed + pending → migration보다 먼저 awaiting-decision. 수정: awaiting-decision은 진행 중 gx-tdd run의 pending이나 state 없는 pending만, 완료 run의 pending은 `stale-pending` 정보만, 구버전 판정 우선.
- **F08** [재현] `gx-work.py:156-171`: 범위 검토보다 stop-at 충돌 검사가 먼저 → 새 작업이 "기존 stop-at 변경" 오류. 수정: 범위 검토를 먼저, 모든 결과에 `requested-stop-at` 보존.
- **F09** [재현] `gx-work.py:22-38,121,340`: understand·status·파일명·삭제·전환 요청도 unsupported-request. 수정: understand/plan/status는 읽기 전용 안내만, 경로·파일명 토큰 제외, 절 분할에서 `.` 제외, 제거·설명·전환 표현 확대, `루프\s+돌려` 오탐 축소.
- **F10** [재현] `gx-work.py:42,53,60,134,335,388,451`: BOM·여러 줄 `.active` → 잠금 검사 누락, config BOM → SVN을 git으로, JSON BOM·UTF-16 거절. 수정: 공통 `utf-8-sig` 읽기, `.active`는 첫 줄 + slug 정규식(`capture_decision.py:63`과 동일), UTF-16은 명확한 오류.
- **F11** [재현] `gx-work.py:323-420,129-131`: pending 중인 qsid·임의 qsid로도 ready true, 답변 기록 후 route가 다시 결정 요구. 수정: 현재 pending의 qsid면 거절(미응답), answered 기록이 있으면 같은 질문을 재요구하지 않음, 완료 run의 handoff 재사용 거절.
- **F12** [재현] `gx-work.py:179-306` vs `340-346`: sources 문자열·requirements 객체·work-id 형식을 validate-plan은 통과, handoff는 거절. 중복 키는 마지막 값 채택. 수정: 공통 검증, 중복 키 거절, `[0-9]`.
- **F13** [재현] `gx-work.py:41-43,158,171`: 주석·따옴표·블록 리스트 flags·본문 줄 오인, stop-at 빈 값·미정의 값 통과. 수정: 첫 YAML 블록만 파싱, 주석·인용 처리, 허용값 검증.
- **F14** [재현] `gx-work.py:337,342-344`: request 인계는 blocking unresolved·충돌 결정이 있어도 ready·execution-authorized true(plan은 거절). 수정: 같은 규칙으로 ready false와 이유 목록, handoff.md에 request 규칙 명시.
- **F15** [재현] `--request`·`--plan` 동시/누락 → stderr usage, 깊은 중첩 JSON → traceback. 수정: 모든 오류를 stdout JSON으로.
- **F16** [재현] `gx-work.py:48,58,91-95`: git 하위 디렉토리를 root로 주면 no-active-run, config 없는 SVN(.svn만) 미인식. 수정: git toplevel 정규화(다르면 결과에 표시), `.svn`·`svn info` 폴백. 문서에 project-root 규칙.
- **F17** [문서/재현] `gx-work/SKILL.md:16`, `tdd-entry.md:30,32,42`, `codex-questions.md:13,28`, `scripts/codex-question.py:162-165`: state 없는 pending을 목표·run 대조 없이 복원, 취소 경로 없음, helper가 새 질문 등록을 거부. 수정: route가 pending의 목표·run·phase를 반환, `codex-question.py discard`(실제 사용자 결정 근거 필수, 보관 후 decisions.md 기록), gx-work에 "이전 질문에 답하기 / 폐기하고 새 작업" 처리.
- **F18** [문서] `tdd-entry.md:30`, `handoff.md:21,59`, `gx-context/references/intake.md:28`, `development-sync.md:18`, `gx-tdd/references/document-lifecycle.md:26`, `gx-commit/SKILL.md:120`, `.claude/hooks/capture_decision.py:213`: 진입 답변 `.dev/main/`, intake `.dev/<run-id>/`, 사전대조 `.dev/planning/<run>/`, handoff `.dev/task/` 등으로 흩어진다. 수정: gx-work 실행 입력은 `.dev/<run-id>/`, state 포인터는 프로젝트 상대경로, gx-commit은 현재 state가 가리키는 run 디렉토리와 보호 브랜치 capture 파일을 "다른 작업 잔재" 질문에서 제외한다(스테이징 제외 + 한 줄 안내).
- **F19** [문서] `gx-work/SKILL.md:22,29`, `tdd-entry.md:9,12,16`, `handoff.md:57,59`, `planning.md:67`, `gx-tdd/SKILL.md:56,81-84`: gx-work는 T계획을 약속하지만 gx-tdd 읽기 전용은 PRD·설계만, 인계는 파일 필요. 수정: 계획만 요청은 gx-work가 planning.md 필드로 대화에 제시(파일·인계 없음). PRD·설계 문서 저장을 원하면 그때 gx-tdd 읽기 전용 인계. 진입 질문 문구를 계획 전용과 개발용으로 분리.
- **F20** [문서] `gx-tdd/phases/phase-implement.md:87,96`, `references/frontend-testing.md:237-238`. 수정: 러너 준비는 파이프라인 밖(`docs/test-harness-guide.md`, gx-setup 타입 등록) 후 `--resume`, gx-dev 안내 제거.
- **F21** [문서] `gx-tdd/phases/phase-setup.md:122`: `Skill("oh-my-gx:gx-setup")`은 `disable-model-invocation: true`라 호출 불가, 실패 안내의 템플릿 경로도 확인 필요. 수정: `/oh-my-gx:gx-setup` 실행 안내 후 중단, 재실행 시 재개.
- **F22** [문서/실측] `gx-tdd/references/intent-routing.md:20-42`: 플래그 분리 뒤 목표 문장이 STATUS/RESUME/CORE 키워드 판정을 거친다. 수정: `origin: gx-work` 인계는 handoff의 intent·stop-at·read-only가 모드를 정하고 목표 문장 키워드 판정을 생략(명시 플래그만 반영).
- **F23** [문서] `gx-tdd/phases/phase-complete.md:224`, `gx-pull-request/SKILL.md:47-62`: 베이스 미전달 → main·develop 공존 시 재질문. 수정: state의 base를 ARGS[0]로 전달.
- **F24** [문서/실측] `gx-work/SKILL.md:11`, `tdd-entry.md:28-30`: Claude Code의 플러그인 루트 유도법 없음(Codex 문서에만), 진입 질문의 helper 등록 여부 불명. 수정: Claude Code 플러그인 루트 = 이 SKILL.md 디렉토리의 `../../..`(`scripts/gx-work.py` 존재 확인), Claude Code 진입 질문은 AskUserQuestion으로 묻고 helper 등록 없이 run 디렉토리의 decisions.md에 기록, question-set-id는 Codex helper 반환값일 때만.
- **F25** [문서] `gx-tdd/references/plan-handoff.md:7`(work-id 미소비), `gx-context/references/intake.md:40`(work-id 미반환), 실행 방식·모델 필드 없음(`tdd-entry.md:40`, `intent-routing.md:28`, `phase-implement.md:187`). 수정: handoff 선택 필드 `work-id`·`execution-method`·`model-profile`, gx-tdd 소비(실행 방식은 Step 1.2의 기본 선택으로만, 계획 승인은 유지), intake 반환에 work-id.
- **F26** [문서] `gx-tdd/phases/phase-setup.md:25,186,221`: 다른 run-id의 진행 중 gx-tdd state를 Step 7에서 덮어씀. 수정: 덮어쓰기 전 확인, 다른 브랜치명 제안.
- **F27** [문서] `gx-context/SKILL.md:67,126`, `references/intake.md:12,42`, `modes/plan.md:246,249`: 직접 호출에도 "gx-work에 인계합니다" 출력, 상위가 없음. 수정: 상위 gx-work가 없으면 "`/oh-my-gx:gx-work <목표>`로 이어서 진행" 안내.
- **F28** [문서] `gx-work/SKILL.md:27`, `gx-tdd/references/intent-routing.md:48`, `phase-complete.md:173,187`, `gx-tdd/SKILL.md:187`: verify로 끝난 run에 "PR만" → 커밋·PR 건너뛰고 completed. 수정: 명시 요청을 종료점 변경 결정으로 기록 → state 갱신 → gx-work 인계면 reissue → 진행.

### P3

- **F29** [정적] `gx-work/SKILL.md:15-16`에 한 문단 10여 규칙. "최초 요청은 진입 승인이 아니다"가 SKILL.md:15,45, tdd-entry.md:22, handoff.md:41,71, planning.md:65에 반복. 수정: 번호 단계·표로 재구성, 정본 한 곳 + 포인터, 테스트·린트가 검사하는 문구 보존.
- **F30** [실측] route 결과값(`awaiting-decision`·`scope-review-required`·`no-active-run`·`resume-selection-required`)과 필드가 gx-work 문서에 없음, 오류 메시지에 필드·값·기대 형식 없음. 수정: 결과값별 처리표, 오류 메시지 보강.
- **F31** [정적] `.claude/hooks/capture-decision.sh`가 python3만 사용. 수정: python3 → python 순서로 3.10+ 확인(`scripts/codex-install-hooks.sh`와 동일).
- **F32** [정적] 현행 gx-dev 잔재: `gx-setup/SKILL.md:189`, `gx-setup/references/project-type-registration.md:83`, `gx-cross-review/SKILL.md:96,152`, `gx-visualize/SKILL.md:126`, `gx-visualize/references/archify-adapter.md:57`, `gx-visualize/references/codex-runtime.md:5`, `gx-tdd`(phase-complete·phase-setup·setup-resume·frontend-testing·maintenance-notes), `gx-commit`·`gx-pull-request` 각 1곳, `agents/coder.md`·`qa-manager.md`·`researcher.md`, 현행 docs, `.claude/rules/skill-routing.md`, `tests/golden-scenarios.md`, `tests/codex-smoke.md`. 수정: 레거시 처리 문맥(마이그레이션 안내)은 유지, "gx-dev를 사용/로" 현행 안내만 제거·대체. gx-dev 전용 에이전트는 호출처가 없을 때만 제거하고, 남기면 설명을 현행화한다.
- **F33** [문서] 재질문: (a) W 착수 진행 여부 `tdd-entry.md:16` ↔ `gx-tdd/phases/setup-work.md:17-22`, (b) `.dev` 무시 확인 gx-context P-8 ↔ gx-tdd Step 6, (c) 커밋 후 context 동기화 `gx-commit/SKILL.md:141-163` ↔ `phase-complete.md:91-108,156`, (d) `setup-work.md:14`(type 질문) ↔ `:43`(표시만). 수정: 같은 run에서 확인한 결과 재사용, phase-complete가 gx-commit에 `--skip-context-sync` 전달.
- **F34** [문서] `README.md:91`(`--work W01`, "W01을 진행해줘"), `index.html:802,1169,1215,1235,1238-1239`, `docs/guide.md:10,12,16`, `docs/codex-guide.md:65,69`, `docs/prompt-examples.md:7`, `gx-setup/SKILL.md:228`("/gx-work → PRD~PR"), `docs/onboarding-guide.md:5`(Ralph 이관 안내 없음), `docs/tdd-guide.md:409-411`.
- **F35** [정적] `gx-work/references/handoff.md:82-86`이 `python`만. 수정: Windows `python`, POSIX `python3`(decision-history.md와 동일).
- **F36** [문서] Ralph in_progress 브랜치(`gx-work.py:120-121`, `intent-routing.md:12-18`, CHANGELOG 3.0.0)와 gx-dev 전환 안내 순환(`setup-resume.md:16,28` ↔ `gx-work.py:156-157`). 수정: "새 브랜치·워크트리에서 새 범위로 시작" 절차를 route reason과 문서에 명시, 순환 제거.
- **F37** [문서] `gx-research/SKILL.md:36,64,70-71`: 조사마다 `.research/` 파일과 `.gitignore` 수정. 수정: gx-work 경유나 "저장하지 마" 요청은 대화 출력, 저장 요청 시에만 파일·.gitignore.
- **F38** [문서] `gx-context/SKILL.md:47,71,76,85-104,120,134-152`, `modes/update.md:14-28`, `modes/sync.md:9-23`, `references/intake.md:28-31`: 이미 말한 도메인·의도를 다시 묻고, context 없는 프로젝트에서 스캔 강제(취소 없음), 직접 호출마다 `.dev/context-<시각>/` 생성(공유 제외 없음). 수정: 요청에 있는 정보는 재질문하지 않음, 스캔에 취소 선택지, 임시 디렉토리 공유 제외.
- **F39** [문서] gx-work 연결 대상 6개뿐(verify·cross-review·visualize·tech-debt·humanizer 0건), "지금 할 수 있는 작업"·`--work` 처리 절차 없음(`tdd-entry.md:8`). 수정: 전문 스킬 안내표, 준비된 W 조회 절차(gx-context `scripts/plan.py` 읽기 전용).
- **F40** [문서] 커밋→PR 체이닝은 개발 저장소 규칙에만 있음, `gx-pull-request/SKILL.md:103-104`가 커밋 유무를 미커밋 확인보다 먼저 검사. 수정: 미커밋 확인을 먼저 하고 gx-commit 선행을 안내.
- **F41** [문서] `gx-tdd/references/pipeline-state.md:24`("Step 0.4"), `gx-work/references/dev-ignore-check.md:5`("gx-work가 실행"), `gx-context/modes/create.md:141`("/gx-work가 PRD 작성"), `tests/golden-scenarios.md:46`(S29 기대가 stop-at 규칙과 모순).
- **F42** [문서] `handoff.md:22,28`(input-sha256·scope-sha256 설명이 같음), run-id 생성 주체 불일치(`gx-tdd/SKILL.md:64` ↔ `handoff.md:7,84`), 저장 인코딩 규칙·project-root 규칙 없음.
- **F43** [문서] `gx-tdd/phases/phase-requirements.md:56`(진입 승인으로 AC 확정을 대체할 수 있는지 모호), `setup-resume.md:43`(계획 문서 종료 상태에서 재개 시 실행 경로 없음).
- **F44** [정적] 린트 [18/36] `.active` 소비자 목록에 `scripts/gx-work.py` 없음.
- **F45** [관찰] 훅 회귀 [6/6]의 35초 자체검증이 부하 시 실패. 제품 결함 아님, 조치 없음.
- **F46** [관측] 이 세션 스킬 목록에서 `oh-my-gx:gx-lens`·`gx-red`·`gx-green`·`gx-visualize` 설명이 빠짐(설치 플러그인 다수). F02의 설명 앞부분 배치로 완화.
- **F47** [설계 유지] 최초 요청을 진입 답변으로 치지 않는 원칙은 유지한다. 진입 질문과 종료점 질문을 한 번의 질문 호출로 함께 묻는 방식을 정본에 명시해 마찰을 줄인다.
