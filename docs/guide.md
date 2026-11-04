# gx-work 사용 가이드

`/gx-work <요청>` 하나로 필요한 논의·계획·TDD 실행을 연결합니다. 직접 `/gx-context`, `/gx-tdd`, `/gx-verify`를 호출하는 숙련자 경로도 유지합니다. `gx-dev` 비TDD 개발 스킬은 제거했습니다.

## 요청 예시

```text
/gx-work 이 기획서로 결제 취소 기능 만들고 PR까지 올려줘
/gx-work 담당자 알림 기능 아이디어만 정리해줘
/gx-work 이 설계에서 빠진 부분을 찾아 실행 계획까지만 만들어줘
/gx-work W01 시작해줘
/gx-work 지금 할 수 있는 작업을 알려줘
/gx-work 아까 하던 작업 이어서 해줘
```

이해·계획 요청은 읽기 전용으로 시작하고 Git 전환·stash·pull·제품 코드 작성·테스트 실행을 하지 않습니다. 개발은 TDD로 수행하며 기본 종료점은 검증입니다. 커밋이나 PR까지 원하면 요청에 적습니다. `core`와 `--ralph`는 명시적으로 선택하는 옵션이며 TDD·검증 게이트는 유지합니다.

## 문서와 계획 재사용

gx-context는 문서·대화에서 근거 있는 사실과 요구사항을 정리하고 `context/<도메인>/status.md` 원장을 보호합니다. `.dev/plan.md`는 도메인별 FR/NFR를 묶은 W작업 목록이며, 기능 내부 실행 계획의 T태스크와 다릅니다. 계획을 다시 생성해도 진행·완료 행과 ID·AC·PR을 임의로 덮어쓰지 않습니다. 다음 작업은 선행 조건이 충족된 대기 행 중에서 안내합니다.

`--from-plan <정규화 JSON>`·`--handoff <JSON>`는 기존 AC·파일·인터페이스·검증 방법을 gx-tdd에 전달합니다. 부족한 부분만 보완하고 이미 승인한 결정을 다시 인터뷰하지 않습니다. 외부 문서에 approved라고 적혀 있다는 이유로 승인됐다고 판단하지 않습니다. 기존 비TDD 상태는 보존하고 전환 범위를 명시적으로 확인합니다.

## 테스트 시간을 줄이는 설정

파이프라인은 언어 중립적입니다. 프론트엔드(JavaScript/TypeScript·Vue·React)도 실행 가능한 테스트 러너와 명령을 등록하면 같은 TDD·검증 계약을 사용합니다. 표시 스타일 대신 사용자에게 보이는 동작을 검증합니다.

예를 들어 web 프로젝트에 Vitest를 사용하고 변경 소스와 테스트 관계를 알고 있다면 설정에 다음 타입을 등록할 수 있습니다. 실제 스택의 명령과 경로로 조정합니다.

```json
{"projectTypes":{"node":{
  "detect":["package.json"],"roots":["web"],
  "test":"npx vitest run","focusedTest":"npx vitest run {files}",
  "buildOnly":"npm run build",
  "testSelection":{"mappings":[{"sources":["src/charge.ts"],"tests":["tests/charge.test.ts"]}]}
}}}
```

Python도 같은 방식으로 등록합니다. 실행 대신 수집만 하는 collect-only 명령은 검증으로 사용하지 않습니다.

```json
{"projectTypes":{"python":{"detect":["pyproject.toml"],"test": "pytest","focusedTest":"pytest {files}","buildOnly":"python -m compileall -q src"}}}
```

태스크 안에서는 해당 테스트만 실행합니다. 경계 검증은 `scripts/gx-test-plan.py`의 영향 계획을 함께 사용하고 같은 실행의 동일 증거만 재사용합니다. 실패·테스트 0건·수 미확정·코드/설정/명령/범위/로그 변경이면 다시 확인합니다. HEAD만 새 커밋으로 바뀌고 트리 내용이 같으면 검증 증거를 유지합니다.

프로젝트 타입에 `roots`, `focusedTest`, `affectedTest`, `testSelection.mappings`와 `buildOnly`를 등록할 수 있습니다. Java/Kotlin의 기본 Gradle buildOnly는 `./gradlew build -x test`입니다. 독립 프로젝트임을 확인한 경우에만 `testSelection.independent: true`로 영향 없는 프로젝트를 제외합니다. 공통 설정·의존성·미소유 경로 변경은 보수적으로 전체 검사합니다. `--full-tests`는 명시적인 전체 회귀를 요청합니다.

빌드가 custom test task까지 실행하면 그 실행을 제외하는 buildOnly를 직접 등록해야 합니다. helper가 명령의 의미를 추측해서 옵션을 덧붙이지 않습니다. SVN은 Git 증거를 재사용하지 않고 보수적인 등록 명령을 실행합니다. 구조 검사·보호 브랜치·verify 지문 게이트는 생략하지 않습니다.

## 지시문과 토큰 예산

스킬은 짧은 진입 계약과 선택 단계의 참조로 나뉩니다. 모든 설명을 한 번에 읽지 않고 현재 태스크의 원문 위치·인터페이스·변경된 결정만 인계합니다. 파일 크기를 줄인 비율이 실제 토큰·비용 절감률을 의미하지는 않습니다. 20KB 진입 예산은 재첨부와 유지보수를 위한 운영 기준이며 모든 모델의 최적 프롬프트 길이라는 연구 결론이 아닙니다.

Claude와 Codex는 같은 스킬·게이트를 사용하지만 도구 호출과 자동 발견 방식은 다릅니다. 실제 설치된 역할·질문 UI·훅 신뢰는 별도 smoke로 확인해야 하며 정적 검사만으로 검증했다고 주장하지 않습니다.
