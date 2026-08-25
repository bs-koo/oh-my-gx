# 프론트엔드 테스트 규약

**참조 시점**: UI 컴포넌트·화면 로직의 실패 테스트를 작성할 때, 프론트엔드가 포함된 설계의 testability를 평가할 때, 프론트 테스트 코드의 품질을 판정할 때.

프론트엔드에 TDD가 안 맞는다는 통념이 있는데, 정확히는 **컴포넌트의 "동작"에는 맞고 "생김새"에는 맞지 않는다**. 이 문서는 그 경계를 긋고, 동작만 검증하는 테스트를 쓰는 방법을 정리한다.

> 이 문서는 `testing-anti-patterns.md`(모의 사용 규율)의 프론트엔드 확장이다. 모의 3원칙은 프론트에도 그대로 적용된다.

## 목차

- [§1. 왜 분리가 가능한가](#1-왜-분리가-가능한가)
- [§2. 레이어별 적합도](#2-레이어별-적합도)
- [§3. 무엇을 검증하고 무엇을 검증하지 않는가](#3-무엇을-검증하고-무엇을-검증하지-않는가)
- [§4. 셀렉터 전략 — 이 규약의 핵심](#4-셀렉터-전략--이-규약의-핵심)
- [§5. 프레임워크별 예시](#5-프레임워크별-예시)
- [§6. AC 작성 규칙](#6-ac-작성-규칙)
- [§7. 모노레포 — 한 파이프라인에서 FE·BE 함께](#7-모노레포--한-파이프라인에서-febe-함께)
- [§8. 하네스가 없을 때](#8-하네스가-없을-때)

---

## §1. 왜 분리가 가능한가

컴포넌트가 하는 일은 두 층이다.

```
동작(behavior)   "에러 상태면 메시지가 노출되고 제출 버튼이 잠긴다"
                 결정적이다. 같은 입력에 같은 결과가 나온다. assert할 수 있다.

표현(style)      "메시지는 빨간색, 아래 8px 여백"
                 주관적이다. "맞다/틀리다"가 아니라 "좋다/아쉽다"의 영역이다.
```

TDD는 위층만 다룬다. 아래층은 나중에 얹어도 위층 테스트가 깨지지 않는다 — **단, 테스트가 아래층에 손대지 않았을 때만.** §4가 그 조건을 다룬다.

이 분리는 headless UI 라이브러리(Radix, Reka, Headless UI, shadcn 계열)의 설계 철학과 같다. 그런 라이브러리를 쓰는 프로젝트라면 이미 절반은 되어 있는 셈이다.

---

## §2. 레이어별 적합도

RGR 사이클을 돌릴 대상을 고를 때 쓴다. 위로 갈수록 투자 대비 회수가 크다.

| 레이어 | 예 | 적합도 | 테스트 방법 |
|---|---|---|---|
| 순수 유틸·포맷터 | `lib/`, `utils/`, 통화·날짜 변환, 밸리데이터 | 높음 | 단위 테스트. 프레임워크 불필요 |
| 상태·데이터 로직 | composable, hook, store, 셀렉터 | 높음 | 단위 테스트. 네트워크만 모의 |
| 라우팅·가드 | middleware, route guard, 권한 분기 | 높음 | 단위 테스트. 분기 그 자체 |
| 컴포넌트 동작 | 폼 검증, 조건부 렌더, 이벤트 emit, 로딩·에러 상태 | 중간 | 마운트 테스트 |
| 화면 조립 | page, layout, 여러 컴포넌트 조합 | 낮음 | E2E |
| 순수 표현 | 아이콘, 배지, 스타일 래퍼 | 대상 아님 | 리뷰·비주얼 회귀 도구 |

**첫 도입이면 위 세 줄부터 시작한다.** 프레임워크 렌더링 없이 돌아서 빠르고, 깨질 일이 적고, 로직 버그의 대부분이 거기 있다.

마지막 줄이 "대상 아님"인 것은 게으름이 아니다. 스타일 래퍼에 assert할 동작이 없다. 억지로 테스트를 만들면 §4의 안티패턴으로 직행한다.

---

## §3. 무엇을 검증하고 무엇을 검증하지 않는가

| 검증한다 | 검증하지 않는다 |
|---|---|
| 무엇이 보이는가 — 텍스트, 요소 존재 여부 | CSS 클래스 이름 |
| 무엇이 잠기는가 — `disabled`, `readonly`, `aria-disabled` | 색상·여백·폰트 크기 등 **스타일 값** |
| 무엇이 나가는가 — emit, 콜백 호출, 요청 payload | DOM 트리 전체 스냅샷 |
| 상태 전이 — 로딩 → 성공/실패 | 자식 노드 개수·순서 |
| 접근성 계약 — `role`, `aria-invalid`, `aria-live` | 애니메이션 타이밍·트랜지션 |
| 사용자 입력에 대한 반응 — 입력·클릭·키보드 | 내부 구현 상태 변수 이름 |

오른쪽 칸을 하나라도 건드리면 "디자인은 나중에"가 불가능해진다. 스타일을 바꿀 때마다 테스트가 깨지고, 몇 번 반복되면 팀은 테스트를 고치는 대신 지운다. **테스트가 삭제되는 가장 흔한 경로가 이것이다.**

---

## §4. 셀렉터 전략 — 이 규약의 핵심

무엇으로 요소를 찾느냐가 테스트의 수명을 결정한다.

```
쓴다
  role / accessible name    getByRole('button', { name: '충전' })
                            사용자가 인지하는 방식과 같고, 접근성이 덤으로 따라온다
  화면에 보이는 텍스트        getByText('한도를 초과했습니다')
  라벨                      getByLabelText('충전 금액')
  data-testid               [data-testid="charge-submit"]
                            위 셋으로 안 잡힐 때의 안전한 탈출구

쓰지 않는다
  CSS 클래스                .text-red-500, .btn-primary
                            스타일을 바꾸는 순간 깨진다. Tailwind면 특히 위험하다
  구조 셀렉터                div > div:nth-child(2)
                            마크업을 감싸는 순간 깨진다
  내부 상태 접근             wrapper.vm.isError, instance.state.foo
                            구현 세부사항이다. 리팩터에 결합된다
```

우선순위는 **role → 텍스트 → 라벨 → data-testid** 순이다. 앞쪽일수록 "사용자가 화면을 인지하는 방식"에 가깝고, 그래서 리팩터에 강하다. `data-testid`는 마지막 수단이지만 CSS 클래스보다는 언제나 낫다.

프로젝트에 이미 다른 컨벤션이 있으면 그것을 따른다 — 일관성이 규약보다 중요하다. 프로젝트 CLAUDE.md에 테스트 컨벤션이 적혀 있으면 그것이 이 문서보다 우선한다.

### 게이트 함수

```
테스트에서 요소를 찾는 코드를 쓰기 전에:
  자문 1: "디자이너가 이 컴포넌트를 다시 그려도 이 셀렉터가 살아있는가?"
          아니라면 → STOP. role·텍스트·data-testid로 바꾼다.
  자문 2: "이 assert가 실패하면 '동작이 틀렸다'는 뜻인가, '보기가 달라졌다'는 뜻인가?"
          후자라면 → STOP. 그건 테스트가 아니라 비주얼 회귀의 영역이다.
```

---

## §5. 프레임워크별 예시

### Vue / Nuxt (Vitest + @vue/test-utils)

```ts
// components/charge/ChargeForm.spec.ts
import { mount } from '@vue/test-utils'
import ChargeForm from './ChargeForm.vue'

describe('ChargeForm', () => {
  it('한도_초과_입력시_에러메시지가_노출되고_제출이_차단된다', async () => {
    const wrapper = mount(ChargeForm)

    await wrapper.find('[data-testid="charge-amount"]').setValue(150000)
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('1회 충전 한도는 100,000원입니다')
    expect(wrapper.find('[data-testid="charge-submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('submit')).toBeUndefined()   // 제출이 실제로 나가지 않았다
  })
})
```

마지막 줄이 중요하다. "메시지가 보인다"만 확인하면 **메시지를 띄우면서 제출도 하는** 구현이 통과한다. 차단이 AC라면 차단을 검증한다.

Nuxt의 auto-import나 앱 컨텍스트가 필요한 컴포넌트는 `@nuxt/test-utils`의 설정을 쓴다. 순수 로직(composable, `lib/`)은 그런 것 없이 바로 테스트된다 — 그래서 §2가 거기부터 시작하라고 한다.

### React (Vitest/Jest + Testing Library)

```tsx
it('한도_초과_입력시_에러메시지가_노출되고_제출이_차단된다', async () => {
  render(<ChargeForm onSubmit={onSubmit} />)

  await userEvent.type(screen.getByLabelText('충전 금액'), '150000')
  await userEvent.click(screen.getByRole('button', { name: '충전' }))

  expect(screen.getByText('1회 충전 한도는 100,000원입니다')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '충전' })).toBeDisabled()
  expect(onSubmit).not.toHaveBeenCalled()
})
```

### GREEN 단계의 산출물은 스타일이 없다

RED를 통과시키는 최소 구현에는 클래스도 레이아웃도 없다. 그게 정상이다.

```vue
<form @submit.prevent="onSubmit">
  <input data-testid="charge-amount" v-model.number="amount" />
  <p v-if="error">{{ error }}</p>
  <button data-testid="charge-submit" :disabled="!!error">충전</button>
</form>
```

디자인은 이 위에 얹는다. 셀렉터 규약을 지켰다면 **테스트는 한 줄도 바뀌지 않는다.** 그것이 이 규약의 목적이다.

---

## §6. AC 작성 규칙

이 전략이 성립하려면 AC 자체가 동작 관점이어야 한다. 표현 속성이 Then 절에 들어오면 red-writer가 검증할 수 없는 테스트를 요구받는다.

```
좋음
  Then: "1회 충전 한도는 100,000원입니다" 메시지가 노출되고 제출 버튼이 비활성화된다
  Then: 로딩 중에는 진행 표시가 노출되고 입력이 잠긴다
  Then: 성공하면 /points/history로 이동한다

나쁨
  Then: 에러가 빨간색으로 표시된다            색은 assert 대상이 아니다
  Then: 폼이 보기 좋게 정렬된다                검증 불가. G-W-T 게이트가 막는다
  Then: 모달이 부드럽게 나타난다                비결정적
```

디자인 요구사항이 없어도 된다는 뜻이 아니다. **AC가 아니라 디자인 스펙으로 따로 관리**한다. 섞이면 자동 검증도 안 되고 디자인 리뷰도 흐려진다.

---

## §7. 모노레포 — 한 파이프라인에서 FE·BE 함께

프론트와 백엔드가 한 저장소에 있으면, `config.json`의 `projectTypes`에 **양쪽을 모두 도는 복합 명령**을 등록한다. 파이프라인은 명령 문자열만 보므로 이것으로 충분하다.

```json
"projectTypes": {
  "fullstack": {
    "detect": ["build.gradle.kts", "frontend/package.json"],
    "build": "./gradlew clean build -x test && pnpm --dir frontend build",
    "test":  "./gradlew test && pnpm --dir frontend test",
    "warningPattern": "warn",
    "artifacts": [".gradle/", "build/", "frontend/node_modules/", "frontend/dist/"]
  }
}
```

주의할 점 넷:

1. **`detect`가 없으면 타입 감지가 실패한다.** 감지 실패 시 verify 게이트는 fail-closed로 차단된다 — 조용히 통과하지 않는다.
2. **`&&`로 잇는다.** 한쪽이 실패하면 exit code가 살아서 게이트가 정상 차단된다. `;`로 이으면 뒤 명령의 결과만 남아 앞의 실패를 삼킨다.
3. **`cd A && ...` 대신 도구의 디렉토리 옵션을 쓴다** (`pnpm --dir`, `npm --prefix`, `make -C`). `cd`로 시작하는 명령은 `allowed-tools`의 prefix 패턴과 매칭되지 않아 매번 권한 프롬프트가 뜬다.
4. **`warningPattern`은 하나뿐이다.** `warn`으로 두면 `warning`도 함께 잡히므로 양쪽에 무난하다. 경고 비교는 근사치이며, 차단 전에 로그 원문 대조 단계가 있어 오차단으로 이어지지 않는다.

태스크는 순차 실행되므로 FE·BE 태스크가 한 파이프라인에 모이면 그만큼 오래 걸린다. 태스크가 8개를 넘어가면 백엔드·프론트 파이프라인을 나눠 도는 편이 실질적으로 빠르다.

### 계약으로 잇기

파이프라인을 나누든 합치든, FE와 BE를 잇는 것은 **AC의 Then 절**이다.

```
AC-2 (백엔드 API)
  Then: 400과 body.code = "CHARGE_LIMIT_EXCEEDED"가 반환된다
          ↑ 이 한 문장을
   BE 테스트는 서버에서 검증하고
   FE 테스트는 클라이언트에서 stub으로 재현한다
```

계약이 AC로 고정되어 있으면 프론트는 백엔드 완성을 기다릴 필요가 없다.

---

## §8. 하네스가 없을 때

프론트에 테스트 러너가 없으면 RGR 사이클이 성립하지 않는다. 실패를 목격할 수단이 없기 때문이다. 이때 선택지는 셋이다.

| 선택 | 언제 | 결과 |
|---|---|---|
| 하네스 구축 후 재실행 | 프론트 로직이 이번 변경의 핵심일 때 | 러너 설치는 `oh-my-gx:gx-dev`로 별도 수행 (실패 테스트를 쓸 수단이 아직 없으므로 gx-tdd로는 불가) |
| 프론트 AC 제외 후 백엔드만 진행 | 백엔드가 본체이고 화면은 부수적일 때 | 제외한 AC를 trust-ledger에 기록. 화면은 gx-dev로 별도 작업 |
| 중단 | 범위를 다시 잡아야 할 때 | 요구사항 재정의 |

**하네스 구축을 gx-tdd로 할 수 없는 이유**는 닭과 달걀이다. 테스트 러너가 없으면 실패 테스트를 쓸 수 없고, 실패 테스트가 없으면 gx-tdd가 진입하지 않는다. 이 한 번만 예외로 일반 개발 경로를 쓴다.

첫 하네스는 §2의 위쪽 레이어부터 붙이면 빠르다. 순수 유틸 하나에 테스트 한 건을 통과시키면 러너·설정·CI 연결이 모두 검증된다.

---

## Red Flags

다음이 보이면 이 규약을 위반하는 중이다.

- assert에 색상값·픽셀값·클래스 이름이 등장한다
- 셀렉터가 `nth-child`·`>`·태그 구조에 의존한다
- 전체 DOM 스냅샷을 저장하고 비교한다
- 디자인을 손볼 때마다 테스트를 함께 고치고 있다
- 테스트가 `wrapper.vm`·인스턴스 내부 상태를 들여다본다
- "이 컴포넌트는 그냥 보여주기만 하는데 테스트를 어떻게 쓰지?" — 그런 컴포넌트는 대상이 아니다 (§2)

---

## 이 규약으로 잡히지 않는 것

정직하게 말하면, 이 방식은 **레이아웃이 무너진 것을 잡지 못한다.** 동작 테스트는 화면이 깨져도 초록불이다.

그건 TDD의 실패가 아니라 다른 축의 문제다. 필요하면 비주얼 회귀 도구(스토리북 스냅샷, 브라우저 스크린샷 비교)를 별도로 붙인다. 검증 수단을 축별로 나눠 보면 이렇다.

```
동작    RGR 사이클 (이 문서의 범위)
계약    AC의 Then 절 — FE·BE 공유
시각    사람의 리뷰, 필요하면 비주얼 회귀 도구
접근성  role 기반 셀렉터를 쓰면 부수적으로 따라온다
```
