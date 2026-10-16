# Codex 모델 정책

이 파일은 [공통 실행 규약](codex-runtime.md)에서 읽는다. Claude의 `Task`·frontmatter 모델과 eco 규칙은 유지한다. 아래는 Codex 디스패치에만 적용한다.

## 선택과 설정

설치된 [모델 helper](../../../../scripts/codex-model-policy.py)는 같은 설치 루트의 `codex-roles/index.json`을 읽는다. 소비 프로젝트 `.claude/config.json`의 `modelProfile`은 기존 프로파일 우선순위로 확정한다. 기본 high는 최신 허용 Astra/low, mid는 최신 허용 Sol/medium이다. 버전 번호를 고정하지 않고 실행 시점의 모델 목록에서 요청 effort를 지원하는 `gpt-<숫자 버전>-astra|sol` 이름을 숫자로 비교한다. 6.10은 6.9보다 높게 해석한다. 이름만으로 날짜 snapshot·preview·latest 별칭의 출시 순서를 추측하지 않는다.

`high`/`mid`는 역할의 모델 티어이며 추론 강도 이름이 아니다. 기본 high 티어의 Astra는 `low`로 실행한다. architect와 TDD fix 4~5 격상에도 같은 기본값을 적용한다. 명시적 프로젝트 effort override와 현재 부모 세션 effort는 유지한다.

빈 설정이면 자동 최신 정책을 쓴다. 선택적 `codex.modelTiers`의 `family`로 계열·effort를 지정할 수 있다:

```json
{"codex":{"modelTiers":{"high":{"family":"astra","reasoning_effort":"low"},"mid":{"family":"sol","reasoning_effort":"medium"}}}}
```

특정 모델을 유지하려면 `family` 대신 `model`을 지정한다. 예를 들어 `{"mid":{"model":"gpt-6.1-sol","reasoning_effort":"medium"}}`은 더 높은 Sol 버전이 허용돼도 지정한 지원 모델을 유지한다. model과 family를 동시에 넣지 않는다. 최신 정책은 자식 배정에만 적용하고 메인 세션 모델을 자동 교체하지 않는다.

모델명은 불변 API가 아니다. 실행 전 노출된 spawn allowlist와 각 모델의 허용 effort를 `capabilities.json`에 새로 적는다. 과거 세션의 파일을 재사용하거나 API 모델 목록·config 모델명으로 spawn 사용 가능 여부를 추측하지 않는다. 이 파일은 실행 입력이며 사용자 전역 Codex 설정을 바꾸지 않는다. 새로운 계열 이름이나 모델 명명 규칙이 생기면 정책 지원을 확인하며, 모든 미래 모델의 출시 순서·별칭 지원을 보장한다고 설명하지 않는다.

```json
{"models":{"gpt-6-astra":["low","medium","high","xhigh"],"gpt-6.1-sol":["low","medium","high","xhigh"]},"parent_model":"gpt-6.1-sol","parent_reasoning_effort":"high"}
```

Windows PowerShell에서 `$pluginRoot`는 codex-runtime에서 확인한 설치 루트다. 프로젝트 위치와 입력 파일은 절대경로를 사용한다.

```powershell
python "$pluginRoot/scripts/codex-model-policy.py" --cwd '<PROJECT_ROOT>' --capabilities '<capabilities.json>' --pipeline gx-tdd --profile eco --role reviewer --scope phase --execution agent
```

exit 0과 JSON의 `model`·`reasoning_effort`·`effective_tier`를 확인한 후 디스패치한다. exit 2이면 지원 제한을 보고하고 중단한다. 모델과 effort가 모두 허용돼야 선택된다. 후보가 없으면 helper가 반환한 대체 사유와 `warnings`를 사용자에게 표시한다. 같은 모델의 서로 다른 effort로 대체된 경우 모델 간 비용 절감으로 설명하지 않는다. 사용자 override도 allowlist 검사를 통과해야 한다. 미지원 override는 같은 effort를 지원하는 허용 후보로 대체하며, 형식이 잘못된 설정은 exit 2다. high/mid가 같은 모델·effort로 합쳐진 경고를 숨기지 않는다.

## 단계와 예외

| 역할·실행 | standard | eco |
|---|---|---|
| architect | high | high 유지 |
| dev design-critic·coder | high | mid |
| tdd design-critic·test-architect·최종 reviewer | high | mid |
| PRD·보안·RED·격리 implementer·기타 원래 mid 역할 | mid | mid |
| tdd reviewer의 태스크 범위 리뷰 (`--scope task`) | mid | mid |
| tdd implementer 수정 4~5회차 (`--fix-round 4` 또는 `5`) | high | high |
| setup·complete·핵심 AC·기본 tdd IMPLEMENT 등 session 실행 | 현재 부모 모델 | 현재 부모 모델 |

기본 tdd GREEN·REFACTOR는 메인 세션에서 실행한다. 이를 mid 구현 에이전트가 실행했다고 기록하지 않는다. implementer를 디스패치하는 `--isolated` 경로에만 agent 매핑을 적용한다. 메인 세션 절감을 원하면 사용자가 모델을 선택해야 하며 플러그인이 자동 변경했다고 표시하지 않는다. Ralph의 eco는 아직 미지원이며 러너의 명시적 모델 선택과 이 정책을 혼동하지 않는다.

TDD implementer fix 4~5는 fresh agent 격상이므로 `--execution session`과 조합하면 exit 2다. session 결과에는 현재 부모 모델·effort가 필요하며 누락 시 실패한다. 부모가 신규 자식 allowlist 밖이어도 실제 현재 세션 정보는 그대로 표시한다.

## 호출과 근거

helper는 모델 선택 결과를 계산할 뿐 collaboration 도구를 호출하지 않는다. 반환된 `spawn_args`에 역할 본문·tools 제약·프로젝트 지침·태스크 전문을 합친 `message`와 `task_name`을 더해 실제 `collaboration.spawn_agent`를 직접 호출한다. `fork_turns: "none"`을 유지한다. `agent_type`은 생략하거나 현재 스키마가 허용하는 `default`를 쓰며, `architect`·`code-reviewer` 등 하네스 고정 모델 역할로 바꾸지 않는다. 역할명과 모델 설정의 일치는 서로 다른 문제다.

매 디스패치의 `${DEV_DIR}/model-dispatches.jsonl`에는 `role`, `pipeline`, `profile`, `scope`, `fix_round`, `base_tier`, `effective_tier`, 선택한 `model`·`reasoning_effort`, `source`·`reason`, 실제 도구에 전달한 `spawn_args`, 반환한 `agent_id`를 기록한다. 하네스 이벤트에서 확인한 모델·effort만 `observed_model`·`observed_reasoning_effort`로 추가하고 미확인이면 null로 둔다. 계획 또는 자식의 자기보고를 관측값으로 쓰지 않는다. implementer 등 GX 역할을 세션이 직접 수행할 때는 해당 index 역할과 `--execution session` 결과·`agent_id: null`로 기록한다.

setup·complete·핵심 AC 같은 역할 없는 인라인 단계는 helper의 role 입력으로 보내지 않는다. 오케스트레이터가 현재 세션 정보를 읽어 `phase`, `execution: "session"`, `role: null`, 부모 `model`·`reasoning_effort`, `source: "parent_session"`, `spawn_args: null`, `agent_id: null`로 기록한다. 현재 부모 정보가 확인되지 않으면 모델·effort는 null, 확인 상태는 미확인으로 기록한다. 세션 상속 설명만으로 실제 관측값을 만들어 넣지 않는다.

이 기록은 오케스트레이터의 실행 계약이며 하네스 내부 모델 선택을 강제하거나 토큰·청구 비용을 계측하는 기능이 아니다. 후속 모델 테스트는 실제 spawn 인자와 확인 가능한 하네스 이벤트를 대조한다.
