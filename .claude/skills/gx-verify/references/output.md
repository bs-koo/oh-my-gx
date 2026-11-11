> gx-verify Step 5-A에서 통과를 알리기 전에 읽는다. 기준점은 ../SKILL.md다.

# verify 통과 출력

통과 출력은 **사용자 줄**과 **기록용 블록**으로 나눈다. 진입·진행 배너는 출력하지 않는다.

## 사용자 줄

결과·테스트 수·범위를 한 줄로 말한다. 코드 지문, entry id, run-id, state 필드명 같은 내부 식별자와 state 기록 지시는 넣지 않는다.

```
검증 통과 — 테스트 47건 통과 (범위: 관련 테스트 3개 파일), 빌드 성공
```

- 범위는 `관련 테스트 N개 파일` 또는 `전체`로 쓴다. 프로젝트가 여럿이면 `backend 전체 · frontend 관련 2개 파일`처럼 잇는다.
- 기존 실패가 있으면 `, 기존 실패 2건 제외 (이번 변경과 무관)`를 붙인다. 목록 안 테스트가 이번에 통과했으면 다음 줄에 `기존 실패 해소: {테스트 ID}`를 둔다.
- 위험 수용, 경고 측정 노이즈, 남은 중요한 미검증 조건이 있으면 한 줄씩 덧붙인다.

## 기록용 블록

호출한 오케스트레이터가 state를 갱신하는 데 쓰는 값이다. 사용자 메시지로 출력하지 않고, 같은 세션의 오케스트레이터가 바로 기록한다.

```yaml
verify-result:
  status: passed
  verify-fingerprint: 7c9e814:3ca970cc12ab   # svn은 "해당 없음"
  tests: 47
  scope: ["src/test/LoginTest.java"]         # 전체면 ["*"]
  known-failures-seen: []                    # 목록 안 실패 ID
  evidence: [{cwd: ".", command: "./gradlew test --tests LoginTest", log: ".dev/feat-login/evidence/{entry.id}.log"}]
  executed-at: 2026-05-16T15:00:00
```

오케스트레이터 조치: state.md에 `verify-status: passed`와 위 `verify-fingerprint`를 기록한다. 이후 commit·PR 등 다음 단계로 진행할 수 있다.

단독 호출이라 기록할 오케스트레이터가 없어도, SKILL.md Step 0.5의 `${DEV_DIR}/state.md`가 `pipeline: gx-tdd`·`status: in_progress`이면 메인 세션이 그 파일에 직접 기록한다. `verify-status:` 줄을 `verify-status: passed`로, `verify-fingerprint:` 줄을 위 값으로 한 줄씩 덮어쓴다(같은 키가 여러 줄이면 모두 같은 값으로, 키가 없으면 한 줄 추가, svn은 `verify-status`만). 다른 필드와 다른 state 파일은 바꾸지 않는다. 기록하지 않으면 훅·gx-commit·gx-pull-request가 계속 미통과로 보고, "gx-verify를 다시 통과시킨 뒤 커밋" 안내가 풀리지 않는다. 그런 state가 없으면 사용자 줄만 남긴다. 사용자가 지문이나 증거 위치를 물으면 그때 이 블록의 값을 보여 준다.
