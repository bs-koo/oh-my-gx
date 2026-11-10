# 핵심 모드 구현계획·승인 공통 계약

gx-tdd 핵심 모드의 정본이다. 순서는 **필요한 문답 → AC 작성 → 대상 코드 Read → 경량 구현계획 작성 → AC와 계획을 함께 단일 승인 → 승인된 태스크의 순차 RGR → 기존 Gate**다. `Read("requirements-dialogue.md")`로 중요한 미정이 해소됐는지 확인하고 오케스트레이터가 직접 문답한다. 인터뷰 전용 에이전트·별도 종료 승인은 추가하지 않는다. 긴급·1파일 변경도 계획과 실제 승인을 생략하지 않는다. 전체 모드의 PRD·설계·테스트 전략과 [gx-work 인계 계약](plan-handoff.md)은 유지한다. 이 파일의 상대경로는 이 파일 기준이다.

## 실행 범위와 모드 복원 정책

`mode`는 산출물·승인 계약, `requested_phase`는 이번 실행 범위다. 기존 실행은 state를 읽기 전용으로 복원한 뒤 `restore_mode`로 정규화한다. 명시 `all`/`core`가 저장 flags보다 우선하고, **mode 필드 부재일 때만** 문자열/목록 flags의 독립 `--core` 토큰으로 core를 복원한다. 필드가 존재하지만 null·빈 값·구버전 값이면 기존 구 버전 세션 방어로 중단한다. 함수의 `None`은 필드 부재다. `--core-extra`는 core가 아니다. 별도 boolean은 `is_core`를 사용하고 phase 이름 문자열 `core`를 덮어쓰지 않는다. 신규 작업은 현재 요청의 mode(기본 all)를 사용하고 실행 setup을 수행한다.

아래는 라우팅을 검증하는 순수 Python 예제다. 별도 helper나 실행 엔진을 추가하지 않는다:

```python
import shlex


def restore_mode(saved_mode, saved_flags):
    if saved_mode is not None:
        if saved_mode not in ("all", "core"):
            raise ValueError("지원하지 않는 저장 mode")
        return saved_mode
    tokens = shlex.split(saved_flags) if isinstance(saved_flags, str) else list(saved_flags or ())
    return "core" if "--core" in tokens else "all"


def full_mode_phases(pipeline):
    if pipeline != "gx-tdd":
        raise ValueError("지원하지 않는 pipeline")
    return ["requirements", "design", "implement", "review", "complete"]


def needs_boundary_regression(phases):
    phases = list(phases)
    if "implement" not in phases:
        return False
    return "complete" not in phases[phases.index("implement") + 1:]


def select_phases(mode, requested_phase, handoff_read_only=False):
    if handoff_read_only:
        if requested_phase not in (None, "requirements", "design"):
            raise ValueError("계획 전용 인계로 실행 phase를 시작할 수 없음")
        return ["explore", requested_phase or "requirements"]
    if requested_phase in ("requirements", "design"):
        return ["explore", requested_phase]
    if requested_phase in ("implement", "review", "complete"):
        return [requested_phase]
    if requested_phase is not None:
        raise ValueError("지원하지 않는 phase")
    if mode == "core":
        return ["setup", "requirements", "implement", "complete"]
    if mode != "all":
        raise ValueError("지원하지 않는 mode")
    return ["setup"] + full_mode_phases("gx-tdd")
```

검증된 `HANDOFF_READ_ONLY`는 state 없이 먼저 처리한다. 탐색과 요청한 requirements/design 계획 내용만 수행하고 실행 setup·pipeline/state 초기화·브랜치·코드·테스트·complete 변경 없이 종료한다. 저장 요청이 없으면 대화에만 제시한다. 이 경로의 `ready-for-tdd`는 구현 허가가 아니다.

일반 기존 실행의 순서는 **state 복원 → 요청 범위 결정 → PHASES 생성 → resume 커서 적용**이다. `current_requested_phase`는 복원 전에 캡처한 이번 명시 `--phase`다. 새 명시 phase가 저장 mode·`requested-phase`·`execution-phases`·과거 커서보다 우선한다. requirements/design은 항상 `[explore, 요청phase]`이며 저장 core를 all로 바꾸거나 구현까지 넓히지 않는다. 충돌은 이번 사용자 인자끼리만 검사하고 과거 `saved_flags`를 합치지 않는다.

현재 명시 phase가 없는 재개만 저장 `requested-phase`(없으면 saved_flags의 `--phase` 값)·`execution-phases`·phase/step을 복원한다. 완료한 setup·phase를 반복하지 않고 중단 Step부터 계속한다. 목록·커서 모순은 임의 전체 초기화 대신 보고한다. 정규화한 mode와 이번 실행 목록·범위를 저장하되 기존 승인·RED·테스트·기준선을 보존한다. 단독 implement는 core 결합 승인 또는 all PRD·설계 게이트를 적용한다. core 단독 complete도 같은 승인을 먼저 검사한다. 누락된 선행 승인은 필요한 계획/승인 Step만 보완하며 setup·완료 RGR 전체를 반복하지 않는다. implement 뒤 complete가 실제 후속 목록에 없을 때만 `needs_boundary_regression(PHASES)`로 Step 3.5 전체 회귀를 수행한다.

## 1. 실제 코드 확인과 계획 작성

오케스트레이터가 `${DEV_DIR}/ac.md`와 코드 맵을 읽고 **변경할 기존 파일의 본문, 관련 호출부·설정·테스트를 실제 Read**한다. 코드 맵의 경로·시그니처나 이전 대화만으로 계획하지 않는다. 신규 파일은 가장 가까운 기존 구현·테스트·통합 지점을 읽어 생성 위치를 확인한다. 확인한 파일과 현재 동작을 계획 및 코드 맵에 기록한다.

기본 작성자는 오케스트레이터다. `${DEV_DIR}/plan.md`는 브랜치/작업별 구현계획이며 프로젝트 작업 원장 **`.dev/plan.md`와 별개**다. 원장·과거 AC 단독 승인·gx-work 진입 응답은 이 계획의 승인이 아니다. 다음 필수 절을 모두 작성한다:

```markdown
# 구현계획: {작업 제목}

## 확인한 코드
- {실제로 Read한 경로: 관련 함수/라인, 현재 동작과 적용할 기존 패턴}

## 변경 파일과 내용
| 파일 | 신규/수정 | 변경 내용 | AC |
|------|----------|----------|----|
| {실제 경로} | {유형} | {무엇을 어떻게 변경하는가} | AC-1 |

## 작업 순서와 의존관계
1. {변경/테스트 작업과 담당 파일} (의존: 없음, AC-1)
2. {다음 작업과 담당 파일} (의존: 1, AC-2)

## AC별 검증 방법
| AC | 검증 파일/대상 | 명령 또는 재현 절차 | 기대결과 |
|----|---------------|--------------------|----------|
| AC-1 | {실제 테스트 경로/대상} | {실행 가능한 명령 또는 구체적 절차} | {판정 가능한 결과} |

## 영향 범위와 가정
- 영향 범위: {호출부·인터페이스·데이터·기존 동작과 회귀 확인 범위}
- 가정: {근거를 확인한 가정, 미해결 사항이 없으면 없음}

## 자체 점검
- 모든 AC가 변경 파일·작업·검증에 연결되는가: {결과}
- 기존 파일·통합 지점을 실제로 읽었고 경로가 존재하는가: {결과}
- 검증 명령/절차와 기대결과로 성공·실패를 구별할 수 있는가: {결과}
- 구현을 막는 불확실한 가정과 중요한 미정이 공통 문답 계약에 따라 해소되었는가: {결과}
```

G-W-T AC별 테스트 파일·focused 명령을 연결하고 작업 순서·의존관계를 순차 RGR 태스크로 옮길 수 있게 한다. 같은 파일(특히 테스트 파일)을 고치는 AC는 한 태스크에 묶어 소유권 중복을 없앤다. 계획의 검증 목록은 Mechanical Gate·RGR·verify·보안 감사·테스트 무결성을 대체하지 않는다. 명령이 미정이면 실제 설정을 조사하고 필요한 답을 받는다. 부족한 버그 재현 정보도 가정으로 덮지 않는다.

### 조건부 architect 1회

실제 코드를 읽어도 구현 위치 또는 의존관계가 불명확한 경우에만 기존 `architect`를 **1회** 호출한다. 파일 개수만으로 호출하지 않는다. `design-critic`·`test-architect`를 core에 자동 추가하지 않는다. architect는 읽기 전용 초안을 반환하고 오케스트레이터가 확인·저장·자체 점검한다. 재호출 루프를 만들지 않는다.

Claude Code는 `Task(subagent_type="oh-my-gx:architect")`에 아래 커스텀 prompt 전문을 전달한다. 기본 전체 설계 형식만 경량 계획으로 바꾸고 역할 페르소나·읽기 전용 경계·프로젝트 컨벤션은 유지한다:

```text
핵심 모드의 경량 구현계획을 작성하라. 구현 코드를 수정하거나 파일을 저장하지 말고 결과를 반환하라.
기본 전체 설계 프로세스 대신 아래 절차·출력 형식을 따르되 역할 페르소나와 읽기 전용 제약은 유지한다.
AC가 이번 태스크의 요구사항 입력이다. PRD 폴백을 읽거나 요구사항·정책을 재정의하지 않는다.

프로젝트 루트: {PROJECT_ROOT}
프로젝트 타입/구조/컨벤션: {확인한 정보와 프로젝트 지침}
AC 전문: {현재 ac.md 전체, G-W-T 포함}
코드 맵: {현재 코드 맵}
이미 확인한 파일과 불확실한 지점: {실제 Read 결과와 구현 위치/의존관계 질문}
도메인 컨텍스트: {있으면 DOMAIN_CONTEXT의 용어·아키텍처만}
외부 규격: {있으면 REFERENCES 테이블; 관련 문서를 Read하여 준수}
출력 템플릿: {위 plan.md 템플릿 전문을 여기 삽입}

1. 대상 기존 코드·호출부·테스트를 Read하고 기존 패턴과 실제 의존관계를 확인하라.
2. 변경 파일과 내용, 작업 순서와 의존관계, AC별 검증 방법(명령/절차와 기대결과), 영향 범위와 가정을 작성하라.
3. 확인한 코드와 자체 점검(AC 전체 커버·실제 파일·검증 가능성·가정 해소)을 포함하라.
4. G-W-T AC를 테스트 파일·focused 명령과 연결하고 순차 RGR의 작업 의존관계를 적어라.
5. 구현을 막는 질문과 탐색 추가 항목을 별도로 반환하라. 새 구조·핵심 인터페이스 설계·중요한 기술 선택이 필요하면
   전체 모드 전환 근거를 보고하고 임의로 결정하거나 구현하지 않는다.
출력은 위 core-planning.md의 plan.md 템플릿 전체와 확인이 필요한 사항이다. 필수 절을 생략하지 않는다.
```

Codex는 먼저 [codex-runtime.md](../../gx-work/references/codex-runtime.md)·[codex-models.md](../../gx-work/references/codex-models.md)를 읽는다. 설치된 `codex-roles/index.json`의 architect `tier`·`file`·`tools`, 역할 본문·읽기/검색 제약·소비 프로젝트 지침과 위 prompt 전문을 `spawn_agent` message에 전달한다. 설치된 `scripts/codex-model-policy.py` helper로 pipeline `gx-tdd`, MODEL_PROFILE, `--role architect --scope phase --execution agent`와 현재 allowlist를 함께 해석한다. architect는 eco에서도 high를 유지한다. helper가 허용한 spawn_args와 `fork_turns: "none"`을 쓰고 고정 모델 하네스 역할로 대체하지 않는다. 요청 모델·실제 인자·관측값을 구분해 기록한다. Write가 없는 역할의 계획은 부모가 저장한다.

### 핵심 모드로 처리할 수 없는 경우

새 구조·핵심 인터페이스 설계·중요한 기술 선택 또는 해소되지 않는 의존 결정이 필요하면 **전체 모드 전환을 제안하고 실제 사용자 결정 전 구현하지 않는다**. 기존 구조 안의 확정된 작은 정책값·조건 변경은 경량 계획으로 처리할 수 있다. core 유지 선택만으로 미해결 사항이 해소되지는 않는다. 범위를 줄이거나 필요한 답을 받아 계획을 완성하고 결합 승인을 받는다. 모드 선택 자체는 PRD·설계·AC+계획 승인이 아니다.

### core → all 전환과 중단 후 재개

실제 전체 모드 선택은 현재 단독 phase 범위도 전체 후속 과정으로 넓힌다는 결정이다. 기존 단독 범위·해제 이유와 `transition-requested-phase: null`을 기록한다. 원래 gx-work run·원문 포인터·진입 승인·종료점은 보존한다. 전환으로 commit/pr 권한을 만들지 않는다. 원래 승인 범위·동작·위험 또는 종료점도 달라졌다면 해당 차이의 실제 진입 결정을 먼저 확인한다.

1. 실제 전체 모드 선택 응답·원래 phase/step을 `decisions.md`에 먼저 기록한다. Codex는 answer·pending 해제도 확인한다. 응답 전에는 전환하지 않는다.
2. state에 `mode-transition: core-to-all`, `mode-transition-status: pending`, `transition-requested-phase: null`과 결정 기록 위치를 저장한다. 이후 기존 core 루프는 실행하지 않는다. pending 저장 전에 중단됐어도 미적용 실제 전환 결정 기록이 있으면 재개에서 pending을 복구한다.
3. pending을 멱등 적용한다: `mode: all`, `is_core = False`, flags의 독립 `--core`와 이전 단독 `--phase {name}` 제거, `requested-phase: null`, `requested_phase = None`, `core-plan-status: pending`, `core-plan-approved-digest: null`. `PHASES = full_mode_phases("gx-tdd")`, `execution-phases: [requirements, design, implement, review, complete]`, `phase: requirements`, `current-step: null`을 저장한다. 과거 완료 표시는 이력으로 보존하고 **새 전체 실행 세대**의 다섯 phase는 pending으로 둔다. 내부 plan-approved/method의 과거 해시를 새 계획의 승인으로 쓰지 않으며 새 계획과 동일한 실제 방법 선택만 검증해 연결한다. `verify-status: pending`·`verify-fingerprint: null`로 무효화한다. setup·DEV_DIR·브랜치를 재생성하지 않는다.
4. 3의 상태를 모두 저장한 뒤에만 `mode-transition-status: applied`를 기록한다. caller에게 `return "mode-transition"`을 반환해 core phase를 즉시 종료한다. 부모는 core requirements 완료를 새 세대에 쓰지 않고 과거 core implement/complete로 진행하지 않는다. 새 전체 목록 requirements부터 각각의 게이트를 수행한다.
5. mode 해석·승인 검사·과거 커서 복원 전에 미적용 결정/pending 전이를 처리한다. applied 일반 재개는 새 mode·전체 목록·현재 커서를 복원하며 **커서를 requirements로 다시 초기화하지 않는다**. 완료 phase를 건너뛰고 중단 Step을 계속한다. 이후 새 명시 `--phase`는 그 범위가 과거 목록·커서보다 우선한다.

기존 ac.md·plan.md·코드·테스트·RED 보고·테스트 해시·기준선을 보존한다. requirements에 기존 AC 전체와 승인된 추가/삭제/수정 내역을 인계하고 AC ID별 PRD 매핑/승인된 은퇴를 기록한다. requirements와 design은 각각 전체 모드 게이트·실제 승인을 받는다. 이미 구현한 AC를 PRD로 옮겼다는 이유로 전부 다시 RED로 만들지 않는다. [core-replanning.md](core-replanning.md)의 delta RED·기존 GREEN·승인된 은퇴·기준선 세대를 적용한다. 전체 선택 자체는 코드 삭제나 테스트 은퇴 승인도 아니다.

## 2. 승인 대상과 상태

상태/문서/실제 승인 근거가 없으면 기본은 pending이다:

```yaml
core-plan-status: pending         # pending | approved
core-plan-approved-digest: null   # approved일 때 결합 SHA-256 64자리 hex
```

지문은 **ac.md 원시 바이트 + NUL 바이트 1개 + plan.md 원시 바이트의 SHA-256**이다. 개행·인코딩을 정규화하거나 지문을 두 입력 문서 안에 넣지 않는다. 다음 Python 표준 라이브러리 예제의 첫 인수는 ac.md, 둘째는 plan.md의 실제 경로다:

```python
import hashlib
import sys
from pathlib import Path

ac_bytes = Path(sys.argv[1]).read_bytes()
plan_bytes = Path(sys.argv[2]).read_bytes()
print(hashlib.sha256(ac_bytes + bytes([0]) + plan_bytes).hexdigest())
```

Windows PowerShell(실제 절대경로로 교체; 문서 Read는 `Get-Content -Encoding UTF8`):

```powershell
python -c "import hashlib,sys; from pathlib import Path; print(hashlib.sha256(Path(sys.argv[1]).read_bytes() + bytes([0]) + Path(sys.argv[2]).read_bytes()).hexdigest())" '<PROJECT_ROOT>/.dev/<slug>/ac.md' '<PROJECT_ROOT>/.dev/<slug>/plan.md'
```

POSIX는 같은 인자로 python3를 사용할 수 있다. 파일 누락·읽기/계산 실패는 승인 불가다.

- 문서 **변경 직전에** `core-plan-status: pending`, `core-plan-approved-digest: null`로 무효화한다. 외부 수정·삭제, AC 제외, 테스트/파일 매핑 변경도 같다. plan-approved의 해시도 오래된 승인으로 재사용하지 않는다.
- approved는 **실제로 표시한 두 문서에 대한 사용자의 명시적 결합 승인**과 표시 지문이 일치할 때만 기록한다. decisions.md에 문서 경로·표시 지문·실제 응답·시점을 저장하고 Codex 질문 세트도 연결한다. 과거 AC 승인·작업 시작·모드 선택·도구 ack를 승인으로 승격하지 않는다.
- **RED·IMPLEMENT·Gate 수리·complete 진입·재개·코드 변경 직전** 두 문서를 Read하고 현재 지문을 계산한다. approved·지문 일치·같은 문서 쌍의 실제 승인 근거·미응답 필수 질문 부재가 모두 필요하다. 구 steps 완료나 ac.md 존재로 통과하지 않는다.
- 누락/불일치는 pending으로 돌리고 필요한 G-W-T 점검·코드 Read·계획 보완·결합 승인 Step만 수행한다. 동일 문서 쌍의 유효한 승인은 다시 묻지 않는다. 재계획에도 기존 RED·보고서·테스트·기준선과 완료 태스크 이력을 보존한다.

## 3. AC와 계획을 함께 단일 승인

자체 점검한 **ac.md와 plan.md 실물 전문을 함께 표시**한다. 문서 경로/표시 지문을 내부 승인 대상 기록에 남긴다. 파일 링크만 주거나 미작성 계획을 승인받지 않는다. 신규 core에 AC 단독 승인·태스크 분해 승인을 추가하지 않는다. 내부 T계획은 승인된 `${DEV_DIR}/plan.md`를 그대로 사용하고 같은 내용을 별도 계획으로 다시 만들지 않는다.

실행방법이 미정이면 한 번의 결합 승인 질문으로 계획 검토와 방법을 함께 확정한다:

```text
AskUserQuestion(
  questions: [{
    question: "표시한 AC와 구현계획을 함께 확인해주세요. 이 범위를 어떤 방식으로 구현할까요? 수정할 사항은 직접 입력해주세요.",
    header: "AC·계획 승인",
    options: [
      { label: "현재 세션으로 승인", description: "AC와 계획을 승인하고 현재 세션에서 구현·검증합니다" },
      { label: "서브에이전트로 승인", description: "AC와 계획을 승인하고 구현 서브에이전트에 위임합니다" },
      { label: "계획 문서로 종료", description: "구현을 시작하지 않고 계획 검토를 마칩니다" }
    ],
    multiSelect: false
  }]
)
```

처음 명시한 session/subagents 방법 또는 같은 run·현재 계획에 연결된 유효한 방법이 있으면 그 선택·출처를 보존하고 위 질문 대신 **승인/수정 요청 2선택**으로 두 문서만 확인한다. 제공할 수 없는 방법을 자동 대체하거나 기존 방법/flags 충돌을 덮지 않는다. 수정 선택은 별도 후속 질문으로 구체 내용을 묻고 실제 답변을 기다린다. 원 질문 Other에 직접 입력한 수정 내용은 그 실제 답변을 사용한다.

- 실행 승인 응답 후 현재 결합지문을 다시 계산하여 표시 지문과 같을 때만 approved·승인 지문을 저장한다. 응답 사이 변경이면 새 문서 전문을 표시해 재승인한다. 수정은 무효화 → 문서 갱신/G-W-T/자체 점검 → 전문 재표시 → 결합 승인 순서다.
- 같은 응답을 `implementation-plan-file: <plan.md 절대경로>`·`implementation-plan-sha256: <plan.md 단독 SHA-256>`·`plan-approved-run/source/sha256`에 연결한다. 새 session/subagents 선택 또는 유효한 초기 명시 선택은 `execution-method`·`execution-method-run/plan-sha256/source`에도 연결한다. 이 **plan.md 단독 SHA-256**과 결합 승인 지문을 혼동하지 않는다. 원래 gx-work request/plan 포인터·진입 승인·해시·run·stop-at는 덮지 않는다.
- session은 --isolated가 없어야 하고 subagents 선택은 최초 실제 선택을 반영할 때 --isolated를 기록한다. 충돌은 실제 결정으로 해소한다. 이후 implement Step 1.2~1.3은 위 근거를 검증해 재사용하고 계획 승인·방법을 반복 질문하지 않는다. 구세션에서 결합 승인만 유효하고 방법이 없으면 Step 1.3에서 **방법만** 보완한다.
- **계획 문서로 종료·미응답·수정 요청은 실행 승인이 아니다**. core-plan을 approved로 만들거나 실행방법을 채우지 않는다. 문서 종료는 `current-step: 계획 문서로 종료`와 pending을 기록하고 미구현을 보고하며 RED·complete·commit/PR로 체이닝하지 않는다. 새 실제 실행 응답 후 게이트를 통과해야 한다.
- Codex는 [codex-runtime.md](../../gx-work/references/codex-runtime.md)·[codex-questions.md](../../gx-work/references/codex-questions.md)의 설치 질문 helper로 필수 질문을 등록한다. 현재 caller phase와 stable id **`core_plan_approval`**을 사용한다. 승인용 도구를 쓸 수 없는 모드에서는 자연어로 표시하고 턴을 종료해 실제 응답을 기다린다. async 반환은 ack일 뿐 승인도 결정도 아니다.
- register가 반환한 `question_set_id`와 문서 지문·경로를 decisions.md의 **승인 대상 기록(미승인)**에 연결한다. 실제 응답의 id·세트·문서 지문 대조 후 answer 성공·pending 해제를 확인한다. 문서 변경 후에는 stable id를 유지하되 **새 question_set_id**를 사용한다. 이전 세트의 늦은 응답을 새 승인으로 재라벨링하지 않는다.
- 미응답 pending을 덮어쓰지 않는다. 수정 응답 기록·해제 후 문서를 바꾸고 새 세트를 등록한다. 외부 변경이 대기 중 발생하면 기존 승인 무효를 표시하고 실제 응답을 받아 기존 세트를 해제하되 변경 문서 승인으로 사용하지 않는다. 후속 수정 질문도 helper 등록·실제 응답을 지킨다. 헤드리스에서 실제 응답이 없으면 질문·원 phase·BLOCKED 사유를 기록하고 종료한다. 시간 경과는 승인이 아니다.

## 4. 승인된 범위의 구현과 변경

RED에는 해당 AC·테스트/대상 경로·검증 방법·시그니처만 전달한다. 계획 전문·프로덕션 구현 본문은 전달하지 않는다. 세션 IMPLEMENT는 해당 태스크 계획을 읽고 isolated 구현자에는 그 승인 계획 발췌만 전달한다. 계획 인계가 RED 구현 비열람·focused 범위를 완화하지 않는다.

구현 위치·외부 인터페이스·범위·AC별 검증 변경이 필요하면 **코드 수정 전에 중단 → 계획(필요하면 AC) 무효화/갱신 → 자체 점검 → 결합 재승인**한다. 담당자만 바꾸는 위임 전환은 범위를 넓히지 않으며 같은 문서 승인 검증만 한다. Gate/verify 회귀 수리도 같은 승인·범위 계약을 따르고 기존 변경·실패 증거를 보존한다. 순차 RGR 태스크의 테스트 소유권·파일 해시·테스트 수·focused 규칙은 그대로 유지한다.
