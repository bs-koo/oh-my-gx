---
name: humanizer
version: 3.2.0
argument-hint: "<파일 경로 또는 텍스트>"
description: |
  AI가 쓴 티를 제거하는 글쓰기 편집 스킬. 한국어 텍스트를 주력으로, 영어도 지원.
  Wikipedia의 "Signs of AI writing" 가이드와 한국어 AI 글쓰기 패턴 연구를 기반으로
  40+ 가지 패턴을 감지하고 교정한다. 감지 전용(audit) 모드와 직접 수정(rewrite) 모드를 지원.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Humanizer v3.2: AI 글쓰기 패턴 감지 및 교정

AI가 생성한 텍스트의 흔적을 찾아내어 자연스러운 사람의 글로 바꾸는 편집 도구.

## 빠른 참조 치트시트

스캔할 때 이 목록을 먼저 훑는다. 자세한 설명은 아래 카탈로그 참조.

### 한국어 즉시 수정 (P1)
| 코드 | 감지 키워드 |
|------|-------------|
| K1 | "오늘날", "알아보겠습니다", "살펴보겠습니다", "이번 글에서는" |
| K2 | "혁신적인", "획기적인", "체계적인", "효과적인", "다양한"(과용), "탁월한" |
| K3 | "~라고 할 수 있습니다", "~라고 해도 과언이 아닙니다" |
| K4 | "이를 통해", "이를 바탕으로", "이를 활용하여" |
| K5 | "중요성은 아무리 강조해도", "핵심적인 역할", "관심이 높아지고" |
| K10 | "결론적으로", "지금까지 ~에 대해", "발전이 기대됩니다" |
| K11 | "도움이 되셨길", "궁금한 점이 있으시면", "좋은 질문입니다!" |

### 한국어 맥락 판단 (P2)
| 코드 | 감지 키워드 |
|------|-------------|
| K6 | "~뿐만 아니라 ~도", "단순히 ~하는 것을 넘어" |
| K7 | "그렇다면 왜 ~일까요?", "그렇다면 어떻게 해야 할까요?" |
| K8 | "첫째... 둘째... 셋째..." (억지 3개 묶음) |
| K9 | "~에 있어서", "~하겠습니다" (과도한 격식체) |
| K12 | "또한"(과용), "더불어", "아울러", "나아가" |
| K13 | "장점으로는... 단점으로는...", "한편으로는... 다른 한편으로는..." |
| K14 | "~되어지다" (이중 피동) |
| K15 | "~를 위해" (한 문단 2회 이상) |
| K17 | "~하는 것이 좋습니다", "~하는 것을 권장합니다" |
| K18 | "기존의 방법 대신", "기존 시스템을 개선하여" |

### 한국어 스타일 개선 (P3)
| 코드 | 감지 키워드 |
|------|-------------|
| K16 | "활용하다"→쓰다, "수행하다"→하다, "구축하다"→만들다 |
| K19 | 산문에 불필요한 마크다운(##, 번호 목록, 과도한 볼드) |

### 공통 패턴
| 코드 | 감지 키워드 |
|------|-------------|
| C1 | 같은 대상을 다른 단어로 계속 바꿔 부름 (동의어 순환) |
| C2 | "정확한 정보는 확인이 필요합니다", "as of [date]" |
| C3 | "밝은 미래가 기대됩니다", "The future looks bright" |
| C4 | 요청하지 않은 이모지 장식 |
| C5 | 모든 문단이 3-4문장으로 균일 |
| C6 | 짧은 글에도 "도입 → 본론 → 결론" 강제 |

### 영어 즉시 수정 (P1)
| 코드 | 감지 키워드 |
|------|-------------|
| E1 | testament, pivotal, evolving landscape, indelible mark |
| E3 | highlighting..., underscoring..., showcasing..., fostering... |
| E4 | nestled, groundbreaking, vibrant, robust, seamless, leverage |
| E7 | Additionally, delve, tapestry, interplay, intricate |
| E13 | Great question!, I'd be happy to, Let's dive in, Here's the thing |
| E18 | In summary, To summarize, To recap |

### 영어 맥락 판단 (P2)
| 코드 | 감지 키워드 |
|------|-------------|
| E8 | serves as, stands as, marks a, represents a |
| E9 | Not only...but..., It's not just about... |
| E10 | from X to Y (의미 없는 범위) |
| E11 | em dash(—) 과용 (문단당 2개 이상) |
| E12 | "- **Header:** Description" 반복 패턴 |
| E14 | In order to, Due to the fact that, It is important to note |
| E15 | could potentially possibly (과도한 hedging) |
| E19 | 산문이 적절한 곳에서 1. 2. 3. 번호 목록 남발 |

### 영어 스타일 개선 (P3)
| 코드 | 감지 키워드 |
|------|-------------|
| E16 | curly quotes ("\u2026") → straight quotes ("...") |
| E17 | Title Case 제목 → Sentence case |

---

## 실행 프로세스

### Step 0: 모드 결정

사용자가 모드를 명시하지 않으면 AskUserQuestion으로 확인한다.

| 모드 | 설명 |
|------|------|
| **audit** | 패턴을 감지하고 리포트만 출력. 텍스트를 수정하지 않음 |
| **rewrite** | 패턴을 감지하고 직접 수정까지 수행 |

**심각도 임계값 (선택):** 사용자가 "P1만", "P2까지" 등으로 수정 범위를 지정할 수 있다. 미지정 시 기본값은 P2까지 수정, P3은 리포트만.

### Step 1: 입력 확인

- 사용자가 텍스트를 직접 제공하면 그대로 사용
- 파일 경로를 제공하면 Read로 읽기
- 글로브 패턴을 제공하면 Glob → Read로 여러 파일 처리
- **부분 수정:** 사용자가 특정 섹션/범위를 지정하면 해당 부분만 처리. 긴 문서에서 "3장만", "결론 부분만" 등으로 범위를 한정할 수 있다

### Step 2: 콘텐츠 유형 파악

글의 유형에 따라 적용 기준이 다르다. 다음 순서로 판단한다:
1. 사용자가 명시한 경우 → 그대로 따름
2. 파일 확장자/경로로 추론 (예: `README.md` → 기술 문서, `blog/` 하위 → 블로그)
3. 본문 내용으로 추론 (코드 블록 비율, 어조, 형식)
4. 판단이 어려우면 AskUserQuestion으로 확인

| 유형 | 적용 기준 | "숨결 주입" |
|------|-----------|-------------|
| **블로그/에세이** | 모든 패턴 적용 | O — 의견, 1인칭, 개성 적극 권장 |
| **기술 문서** | 명확성 우선. 수식어/filler 제거 | X — 감정/개성 주입 금지. 정확하고 건조하게 |
| **마케팅/카피** | 과장은 줄이되 설득력 유지. 구체적 수치로 대체 | 제한적 — 브랜드 보이스에 맞춰 |
| **학술/리포트** | 정확성과 출처 중심. weasel word 제거 | X — 객관적 톤 유지 |
| **코드 주석** | 간결성 우선. 불필요한 설명 제거 | X |
| **SNS/캐주얼** | 과도한 형식성 제거. 구어체 허용 | O — 자유롭게 |

### Step 3: 패턴 스캔

아래 패턴 카탈로그를 기준으로 전체 텍스트를 스캔한다.
각 감지 항목에 심각도를 부여한다:

- **P1 (확실한 AI 흔적)** — 사람이 거의 쓰지 않는 패턴. 즉시 수정 필요
- **P2 (의심스러운 패턴)** — AI가 자주 쓰지만 사람도 가끔 쓰는 표현. 맥락 판단 필요
- **P3 (스타일 개선)** — AI 흔적이라기보다 글 품질 향상 차원

### Step 4: 수정 (rewrite 모드)

- P1은 무조건 수정
- P2는 맥락에 따라 판단하되, 의심스러우면 수정
- P3는 전체 톤에 맞춰 선택적으로 수정
- 원문의 핵심 의미를 절대 훼손하지 않음
- 글의 기존 톤(격식/비격식)을 유지
- **원문에 없는 사실을 만들어내지 않음.** 구체적 데이터로 대체할 때는 원문에 근거가 있을 때만. 근거가 없으면 빈 수식어를 빼는 것으로 충분

### Step 5: 결과 출력

**audit 모드:**
```
## 감지 리포트

총 감지: N건 (P1: n건, P2: n건, P3: n건)

| # | 위치 | 심각도 | 패턴 | 원문 | 제안 |
|---|------|--------|------|------|------|
| 1 | L3   | P1     | K2 과장 수식어 | "혁신적인 방법론을 통해" | "이 방법으로" |
```

**rewrite 모드:**
수정된 전체 텍스트 + 변경 요약 (적용된 패턴 코드 포함)

---

## 글에 숨결 불어넣기

> **적용 대상: 블로그/에세이, SNS/캐주얼만.** 기술 문서, 학술, 코드 주석에는 이 섹션을 적용하지 않는다.

AI 패턴 제거는 절반. 깨끗하지만 무미건조한 글도 AI처럼 보인다.

### 영혼 없는 글의 징후:
- 모든 문장이 비슷한 길이와 구조
- 의견 없이 사실만 나열
- 불확실함이나 복잡한 감정에 대한 인정 없음
- 적절한 곳에서도 1인칭 회피
- 유머, 날카로움, 개성 부재
- 보도자료나 백과사전처럼 읽힘

### 숨결을 넣는 법:

**의견을 가져라.** 사실을 보고하는 데 그치지 말고 반응하라. "솔직히 이건 좀 애매하다"가 장단점을 중립적으로 나열하는 것보다 낫다.

**리듬을 바꿔라.** 짧은 문장. 그리고 좀 더 천천히 가는 긴 문장. 섞어 써라.

**복잡함을 인정하라.** 사람은 복잡한 감정을 가진다. "인상적인데 동시에 좀 불편하다"가 "인상적이다"보다 사람답다.

**'나'를 쓸 때는 써라.** 1인칭이 비전문적인 게 아니다. "계속 생각나는 건..."이나 "내가 걸리는 부분은..."은 실제로 생각하는 사람의 표현이다.

**약간의 지저분함을 허용하라.** 완벽한 구조는 알고리즘 냄새가 난다. 곁가지, 여담, 반쯤 정리된 생각은 사람의 것이다.

**감정을 구체적으로.** "우려된다"가 아니라 "새벽 3시에 아무도 안 보는데 에이전트가 혼자 돌아가는 거 생각하면 좀 소름 돋는다."

### 수정 전 (깨끗하지만 영혼 없음):
> 이 실험은 흥미로운 결과를 보여주었다. 에이전트가 300만 줄의 코드를 생성했다. 일부 개발자는 감명받았고 다른 개발자는 회의적이었다. 시사점은 아직 불분명하다.

### 수정 후 (숨이 붙은 글):
> 솔직히 이건 어떻게 받아들여야 할지 모르겠다. 300만 줄의 코드, 사람들이 자는 동안 생성됐다. 개발자 절반은 난리가 났고, 절반은 왜 의미 없는지 설명하느라 바쁘다. 진실은 아마 그 중간 어딘가 재미없는 곳에 있겠지만, 밤새 혼자 일하는 에이전트 생각이 자꾸 든다.

---

## 한국어 AI 패턴 카탈로그 (메인)

### K1. 도입부 상투어 [P1]

**감지 표현:** "오늘날", "현대 사회에서", "급변하는 시대에", "디지털 시대에 접어들면서", "4차 산업혁명 시대", "~에 대해 알아보겠습니다", "~에 대해 살펴보겠습니다", "~를 함께 알아볼까요?", "~에 대해 깊이 파헤쳐 보겠습니다", "이번 글에서는"

**문제:** AI가 글을 시작할 때 거의 반사적으로 시대 상황을 설정하거나 메타 설명을 붙인다.

**수정 전:**
> 오늘날 급변하는 디지털 시대에 접어들면서 인공지능 기술은 우리 삶의 다양한 영역에 걸쳐 혁신적인 변화를 가져오고 있습니다. 이번 글에서는 AI 코딩 도구에 대해 자세히 알아보겠습니다.

**수정 후:**
> AI 코딩 도구가 실제로 생산성을 높이는지, 연구 결과를 보면 답이 간단하지 않다.

---

### K2. 과장 수식어 [P1]

**감지 표현:** "혁신적인", "획기적인", "체계적인", "효과적인", "효율적인", "다양한" (한 문단에 2회 이상), "풍부한", "탁월한", "놀라운", "뛰어난", "독보적인", "선도적인", "차별화된", "의미 있는", "가치 있는", "핵심적인", "필수적인", "지속 가능한"

**문제:** 한국어 AI 글에서 가장 빈번한 패턴. 수식어를 빼도 의미가 변하지 않으면 과장이다. 특히 "다양한"은 한국어 AI 텍스트의 최다 빈출 단어 — 구체적으로 뭐가 다양한지 말하지 않는다.

**수정 전:**
> 이 혁신적인 프레임워크는 다양한 기능을 제공하여 다양한 환경에서 다양한 용도로 활용할 수 있는 탁월한 도구입니다.

**수정 후:**
> 이 프레임워크는 빌드, 테스트, 배포를 하나의 설정 파일로 관리한다. Node.js와 브라우저 양쪽에서 쓸 수 있다.

---

### K3. ~라고 할 수 있습니다 류 회피 어미 [P1]

**감지 표현:** "~라고 할 수 있습니다", "~라고 볼 수 있습니다", "~라고 해도 과언이 아닙니다", "~것으로 보입니다", "~것으로 판단됩니다", "~것으로 예상됩니다", "~에 해당한다고 볼 수 있습니다"

**문제:** AI가 단정을 피하려고 모든 문장에 회피 어미를 붙인다. 사실을 서술할 때는 단정해도 된다.

**수정 전:**
> React는 현재 가장 널리 사용되는 프론트엔드 라이브러리라고 할 수 있습니다. 이는 컴포넌트 기반 아키텍처를 채택하고 있기 때문이라고 볼 수 있습니다.

**수정 후:**
> React는 현재 가장 많이 쓰이는 프론트엔드 라이브러리다. 컴포넌트 단위로 UI를 쪼개서 재사용하는 구조 덕분이다.

---

### K4. "이를 통해" 연쇄 [P1]

**감지 표현:** "이를 통해", "이를 바탕으로", "이를 기반으로", "이러한 관점에서", "이러한 측면에서", "이를 활용하여", "이와 같은 방식으로"

**문제:** AI가 문장을 연결할 때 "이를 통해"를 반복적으로 사용해 기계적인 인과관계를 만든다.

**수정 전:**
> 먼저 데이터를 수집합니다. 이를 통해 패턴을 분석할 수 있습니다. 이를 바탕으로 모델을 학습시킵니다. 이를 활용하여 예측을 수행합니다.

**수정 후:**
> 데이터를 수집해서 패턴을 분석하고, 그 결과로 모델을 학습시킨 뒤 예측에 쓴다.

---

### K5. 무의미한 중요성 강조 [P1]

**감지 표현:** "~의 중요성은 아무리 강조해도 지나치지 않습니다", "~은/는 매우 중요합니다", "~에서 핵심적인 역할을 합니다", "~에 있어서 필수적입니다", "~의 중요성이 날로 커지고 있습니다", "~에 대한 관심이 높아지고 있습니다"

**문제:** 왜 중요한지 구체적으로 말하지 않고 중요하다고만 반복한다.

**수정 전:**
> 코드 리뷰의 중요성은 아무리 강조해도 지나치지 않습니다. 소프트웨어 개발에 있어서 코드 리뷰는 핵심적인 역할을 합니다.

**수정 후:**
> 코드 리뷰를 거친 코드는 프로덕션 버그가 적다. 이유 중 하나는 리뷰어가 작성자가 놓친 엣지 케이스를 잡아내기 때문이다.

---

### K6. "~뿐만 아니라 ~도" 과용 [P2]

**감지 표현:** "~뿐만 아니라 ~도", "~뿐 아니라 ~까지", "단순히 ~하는 것을 넘어", "~에 그치지 않고"

**문제:** 영어의 "Not only...but also..." 에 해당. AI가 범위 확장을 표현할 때 기계적으로 사용.

**수정 전:**
> 이 도구는 코드 자동 완성뿐만 아니라 리팩토링, 테스트 생성, 문서화까지 지원합니다. 단순히 코드를 작성하는 것을 넘어 전체 개발 워크플로우를 혁신합니다.

**수정 후:**
> 이 도구는 자동 완성, 리팩토링, 테스트 생성, 문서화를 지원한다.

---

### K7. "그렇다면" 자문자답 [P2]

**감지 표현:** "그렇다면 왜 ~일까요?", "그렇다면 어떻게 해야 할까요?", "그렇다면 ~란 무엇일까요?", "과연 ~일까요?"

**문제:** AI가 구조를 잡기 위해 스스로 질문을 던지고 답하는 패턴. 블로그 글에서 특히 빈번.

**수정 전:**
> 마이크로서비스 아키텍처가 주목받고 있습니다. 그렇다면 왜 마이크로서비스가 필요할까요? 그 이유는 크게 세 가지로 나눌 수 있습니다.

**수정 후:**
> 마이크로서비스로 전환하는 이유는 보통 배포 독립성이다. 한 팀의 변경이 다른 팀을 막지 않는다.

---

### K8. 나열의 셋 법칙 [P2]

**감지 표현:** "A, B, 그리고 C", "첫째... 둘째... 셋째...", "A할 뿐만 아니라 B하며 C합니다"

**문제:** AI가 항목을 세 개 묶어서 포괄적으로 보이게 함. 실제로 세 개면 괜찮지만, 억지로 세 개에 맞추는 게 문제.

**수정 전:**
> 이 프레임워크는 확장성, 유연성, 그리고 안정성을 모두 갖추고 있습니다.

**수정 후:**
> 이 프레임워크는 수평 스케일링을 지원하고, 플러그인 구조로 기능을 추가할 수 있다.

---

### K9. 격식체 과용 및 "~에 있어서" [P2]

**감지 표현:** "~하겠습니다", "~되겠습니다", "~것입니다", "~하시기 바랍니다", "~에 해당합니다", "~에 있어서", "~에 있어", "~함에 있어"

**문제:** AI가 한국어 글을 쓸 때 과도하게 격식체를 사용. "~에 있어서"는 거의 모든 경우 생략하거나 더 직접적인 표현으로 바꿀 수 있다.

**참고:** 콘텐츠 유형에 따라 판단. 공문서나 발표 자료라면 격식체가 적절.

**수정 전:**
> 소프트웨어 개발에 있어서 테스트는 필수적입니다.

**수정 후:**
> 테스트 없이 소프트웨어를 배포하면 문제가 터진다.

---

### K10. 결론부 상투어 [P1]

**감지 표현:** "결론적으로", "요약하자면", "마무리하며", "지금까지 ~에 대해 알아보았습니다", "앞으로 ~이/가 기대됩니다", "~의 발전이 기대됩니다", "함께 만들어 나가야 할 것입니다", "지속적인 관심이 필요합니다"

**문제:** AI가 결론을 쓸 때 내용 없이 희망적인 전망을 덧붙인다.

**수정 전:**
> 지금까지 컨테이너 기술에 대해 알아보았습니다. 앞으로 컨테이너 기술의 발전이 더욱 기대되며, 개발자들의 지속적인 관심이 필요합니다.

**수정 후:**
> 컨테이너를 처음 쓴다면 Docker Desktop으로 시작해서, 프로덕션에서는 Kubernetes를 검토하면 된다.

---

### K11. 대화형 흔적 잔류 [P1]

**감지 표현:** "도움이 되셨길 바랍니다", "궁금한 점이 있으시면", "더 자세한 내용이 필요하시면", "좋은 질문입니다!", "물론입니다!", "말씀하신 것처럼"

**문제:** 챗봇 대화 흔적이 글에 남아 있는 경우. 전부 삭제.

---

### K12. 의미 없는 접속부사 [P2]

**감지 표현:** "또한" (과용), "한편", "더불어", "아울러", "나아가", "특히" (과용), "무엇보다", "이에 따라", "따라서" (문맥 없이)

**문제:** 실제 논리적 연결 없이 접속부사로 문장을 이어붙인다.

**수정 전:**
> Rust는 메모리 안전성을 보장합니다. 또한 성능이 뛰어납니다. 더불어 동시성 처리도 강력합니다. 나아가 생태계도 빠르게 성장하고 있습니다.

**수정 후:**
> Rust는 컴파일 타임에 메모리 안전성을 검증하면서도 C++ 수준의 성능을 낸다. 동시성 모델도 데이터 레이스를 컴파일러가 잡아준다.

---

### K13. 장점/단점 대칭 구조 [P2]

**감지 표현:** "장점으로는... 단점으로는...", "물론... 하지만...", "한편으로는... 다른 한편으로는...", "긍정적인 측면... 부정적인 측면..."

**문제:** AI가 균형 잡힌 시각을 보여주려고 기계적으로 양쪽을 대칭시킴.

**수정 전:**
> 물론 마이크로서비스에는 많은 장점이 있습니다. 하지만 단점도 존재합니다. 장점으로는 독립적 배포, 기술 다양성, 확장성이 있으며, 단점으로는 복잡성 증가, 네트워크 오버헤드, 데이터 일관성 문제가 있습니다.

**수정 후:**
> 마이크로서비스의 최대 이점은 독립 배포다. 대신 서비스 간 통신이 복잡해지고, 분산 트랜잭션 처리가 골치 아파진다. 팀이 5명 이하라면 모놀리스가 거의 항상 낫다.

---

### K14. 불필요한 피동 표현 [P2]

**감지 표현:** "~되어지다" (이중 피동), "작성되어질 수 있습니다", "진행되어지고 있습니다", "사용되어질 수 있는", "변경되어지는"

**문제:** 한국어에서 "~되다"만으로 충분한 피동에 "~어지다"를 덧붙여 이중 피동을 만든다. AI가 공손함을 높이려고 자주 사용.

**수정 전:**
> 데이터가 수집되어지고 분석이 진행되어지면 결과가 도출되어질 수 있습니다.

**수정 후:**
> 데이터를 수집하고 분석하면 결과가 나온다.

---

### K15. "위해" 과용 [P2]

**감지 표현:** "~를 위해", "~하기 위해", "~를 위한" (한 문단에 2회 이상)

**문제:** AI가 목적을 표현할 때 "위해"를 반복적으로 사용.

**수정 전:**
> 성능을 향상시키기 위해 캐시를 도입했으며, 안정성을 확보하기 위해 재시도 로직을 추가했고, 가독성을 높이기 위해 코드를 리팩토링했습니다.

**수정 후:**
> 캐시를 도입해 성능을 높이고, 재시도 로직으로 안정성을 잡았다. 겸사겸사 코드도 정리했다.

---

### K16. 한자어 남용 [P3]

**감지 표현:** "활용하다"→쓰다, "수행하다"→하다, "구축하다"→만들다/세우다, "도입하다"→넣다/쓰기 시작하다, "적용하다"→쓰다/붙이다, "진행하다"→하다, "제공하다"→주다/내놓다

**문제:** AI가 간단한 고유어 대신 한자어를 선호한다. 항상 나쁜 건 아니지만, 기술 문서 밖에서 딱딱함을 만든다.

**참고:** 기술 문서에서는 한자어가 자연스러운 경우가 많다 ("API를 활용하다"는 "API를 쓰다"보다 어색하지 않음). 블로그/에세이에서 주로 적용.

---

### K17. "~하는 것이 좋습니다" 반복 [P2]

**감지 표현:** "~하는 것이 좋습니다", "~하는 것을 권장합니다", "~하는 것을 추천합니다", "~하시는 것이 바람직합니다", "~하시기를 권합니다"

**문제:** AI가 조언할 때 모든 문장에 우회적 권유 어미를 붙인다. 직접 말하면 된다.

**수정 전:**
> 테스트를 먼저 작성하는 것이 좋습니다. 또한 커밋 단위를 작게 유지하는 것을 권장합니다. PR 리뷰는 당일에 처리하는 것이 바람직합니다.

**수정 후:**
> 테스트를 먼저 작성하라. 커밋은 작게 쪼개고, PR 리뷰는 당일에 끝내라.

---

### K18. 불필요한 "기존" 대비 [P2]

**감지 표현:** "기존의 방법 대신", "기존 시스템을 개선하여", "기존에는 ~했지만", "기존의 한계를 극복", "기존 방식과 달리", "기존의 문제점을 해결"

**문제:** AI가 새로운 것을 소개할 때 "기존"과의 대비를 억지로 만든다. 기존이 뭔지 구체적으로 말하지 않으면서 대비 구조만 잡는다.

**수정 전:**
> 기존의 배포 방식과 달리 이 도구는 기존의 한계를 극복하여 기존 시스템을 개선한 혁신적인 솔루션입니다.

**수정 후:**
> 이 도구는 배포 시 수동으로 서버에 접속할 필요 없이 git push만으로 배포를 실행한다.

---

### K19. 마크다운 남용 [P3]

**문제:** 산문으로 충분한 짧은 글에 `##` 제목, 번호 목록, 과도한 볼드를 적용. 마크다운 구조화가 필요한 건 긴 기술 문서나 가이드뿐이다.

**감지 기준:**
- 500자 미만의 글에 `##` 제목이 2개 이상
- 3항목 이하의 내용을 번호 목록으로 나열
- 문단당 볼드가 3개 이상

**원칙:** 구조화가 가독성을 높이는지 판단. 아니면 산문으로 풀어쓴다.

---

## 영어 AI 패턴 카탈로그 (서브)

### E1. 중요성 과장 [P1]

**감지 표현:** stands/serves as, is a testament/reminder, pivotal/crucial/vital role/moment, underscores/highlights its importance, reflects broader, symbolizing its enduring, setting the stage for, marks a shift, key turning point, evolving landscape, indelible mark

**수정 전:**
> The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain.

**수정 후:**
> The Statistical Institute of Catalonia was established in 1989 to collect and publish regional statistics independently from Spain's national statistics office.

---

### E2. 주목도/미디어 언급 과시 [P1]

**감지 표현:** independent coverage, local/regional/national media outlets, leading expert, active social media presence

**수정 전:**
> Her views have been cited in The New York Times, BBC, Financial Times, and The Hindu. She maintains an active social media presence with over 500,000 followers.

**수정 후:**
> In a 2024 New York Times interview, she argued that AI regulation should focus on outcomes rather than methods.

---

### E3. ~ing 접미 분석 [P1]

**감지 표현:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., showcasing...

**수정 전:**
> The temple's color palette resonates with the region's natural beauty, symbolizing Texas bluebonnets, reflecting the community's deep connection to the land.

**수정 후:**
> The temple uses blue, green, and gold. The architect said these reference local bluebonnets and the Gulf coast.

---

### E4. 홍보성 언어 [P1]

**감지 표현:** boasts, vibrant, rich (비유), profound, showcasing, exemplifies, commitment to, nestled, in the heart of, groundbreaking, renowned, breathtaking, must-visit, stunning, robust, leverage, streamline, seamless, cutting-edge, state-of-the-art, game-changing

**수정 전:**
> Nestled within the breathtaking region of Gonder, Alamata stands as a vibrant town with a rich cultural heritage.

**수정 후:**
> Alamata is a town in the Gonder region, known for its weekly market and 18th-century church.

---

### E5. 모호한 출처/Weasel Words [P1]

**감지 표현:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources

**수정 전:**
> Experts believe it plays a crucial role in the regional ecosystem.

**수정 후:**
> The river supports several endemic fish species, according to a 2019 survey by the Chinese Academy of Sciences.

---

### E6. "Challenges and Future Prospects" 공식 [P1]

**감지 표현:** Despite its... faces challenges..., Despite these challenges, Future Outlook

**수정 전:**
> Despite its industrial prosperity, the area faces challenges typical of urban areas. Despite these challenges, it continues to thrive.

**수정 후:**
> Traffic congestion increased after 2015. The corporation began a drainage project in 2022 to address recurring floods.

---

### E7. AI 빈출 어휘 [P1]

**감지 표현:** Additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, interplay, intricate/intricacies, landscape (추상), pivotal, showcase, tapestry (추상), testament, underscore, vibrant, nuanced, multifaceted, realm, paradigm, synergy

**수정 전:**
> Additionally, a distinctive feature is the intricate interplay between tradition and innovation, showcasing the vibrant tapestry of local culture.

**수정 후:**
> Local dishes blend Italian pasta with traditional Somali spices, a leftover from colonization.

---

### E8. 계사 회피 (Copula Avoidance) [P2]

**감지 표현:** serves as [a], stands as [a], marks [a], represents [a], boasts [a], features [a], offers [a]

**수정 전:**
> Gallery 825 serves as LAAA's exhibition space. The gallery features four rooms and boasts 3,000 square feet.

**수정 후:**
> Gallery 825 is LAAA's exhibition space. It has four rooms totaling 3,000 square feet.

---

### E9. 부정 병렬 구조 [P2]

**감지 표현:** Not only...but..., It's not just about..., it's..., It's not merely..., it's...

**수정 전:**
> It's not just about the beat; it's part of the aggression. It's not merely a song, it's a statement.

**수정 후:**
> The heavy beat adds to the aggressive tone.

---

### E10. False Ranges [P2]

**감지 표현:** from X to Y, from A to B (의미 있는 스케일 아닌 경우)

**수정 전:**
> Our journey has taken us from the singularity of the Big Bang to the grand cosmic web, from the birth of stars to the dance of dark matter.

**수정 후:**
> The book covers the Big Bang, star formation, and current dark matter theories.

---

### E11. Em dash 과용 [P2]

**문제:** AI가 em dash(—)를 세일즈 문체처럼 남발.

**원칙:** 한 단락에 em dash 1개 이하. 나머지는 쉼표나 괄호로 교체.

---

### E12. 볼드체 과용 / 인라인 헤더 목록 [P2]

**문제:** 기계적으로 핵심 용어에 볼드를 적용하거나, `- **Header:** Description` 패턴을 반복.

**수정 전:**
> - **User Experience:** Significantly improved with a new interface.
> - **Performance:** Enhanced through optimized algorithms.
> - **Security:** Strengthened with end-to-end encryption.

**수정 후:**
> The update improves the interface, speeds up load times through optimized algorithms, and adds end-to-end encryption.

**원칙:** 볼드는 정말 강조가 필요한 곳에만. 문단당 1-2개 이하.

---

### E13. 대화형 잔류물 / 아첨 어조 / 최신 상투어 [P1]

**감지 표현:** I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., let me know, here is a..., Great question!, That's an excellent point!, Absolutely!, I'd be happy to..., I'd love to help..., "Let's dive in", "Let's break this down", "Here's the thing", "It's worth noting that", "This is where X comes in", "The key takeaway here is", "At the end of the day", "In a world where...", "Here's the reality:", "The bottom line:"

**문제:** 챗봇 대화 흔적과 2024년 이후 급증한 AI 상투어. 전부 삭제.

**수정 전:**
> Great question! Let's dive in. Here's the thing — in a world where AI is rapidly evolving, it's worth noting that the key takeaway here is adaptability. At the end of the day, this is where human creativity comes in. I hope this helps!

**수정 후:**
> AI tools change fast. The useful skill isn't mastering any one tool — it's learning to evaluate new ones quickly.

---

### E14. Filler Phrases [P2]

| 수정 전 | 수정 후 |
|---------|---------|
| In order to | To |
| Due to the fact that | Because |
| At this point in time | Now |
| In the event that | If |
| has the ability to | can |
| It is important to note that | (삭제) |
| It goes without saying that | (삭제) |

---

### E15. 과도한 Hedging [P2]

**수정 전:**
> It could potentially possibly be argued that the policy might have some effect.

**수정 후:**
> The policy may affect outcomes.

---

### E16. Curly 따옴표 [P3]

**문제:** ChatGPT가 curly quotes(\u201c...\u201d)를 사용. 코드나 기술 문서에서 문제 유발.

**원칙:** 모두 straight quotes("...")로 교체.

---

### E17. 제목 Title Case [P3]

**수정 전:** `## Strategic Negotiations And Global Partnerships`

**수정 후:** `## Strategic negotiations and global partnerships`

---

### E18. 불필요한 요약 반복 [P1]

**감지 표현:** "In summary", "To summarize", "To recap", "As we've seen", "As mentioned above", "As discussed earlier", "As we've explored"

**문제:** AI가 글 끝이나 섹션 전환 시 이미 말한 내용을 다시 요약한다. 짧은 글에서는 특히 불필요.

**수정 전:**
> To summarize, we've explored three key approaches to caching: in-memory, Redis, and CDN-based. As we've seen, each has its trade-offs. In summary, the best choice depends on your specific use case.

**수정 후:**
> Pick in-memory caching for single-server apps, Redis when you need shared state, and CDN for static assets.

---

### E19. 과도한 구조화 [P2]

**문제:** 산문이 더 자연스러운 곳에서 번호 목록이나 불릿 포인트로 쪼개는 패턴. 항목 간 관계가 있는 내용을 독립된 목록으로 만들면 맥락이 끊긴다.

**수정 전:**
> Here are the benefits of TypeScript:
> 1. Type safety catches bugs at compile time
> 2. Better IDE support with autocompletion
> 3. Easier refactoring

**수정 후:**
> TypeScript catches type errors at compile time, which also gives IDEs enough information to autocomplete and makes refactoring safer.

**원칙:** 항목이 독립적이고 5개 이상이면 목록이 적절. 3개 이하이고 연결되는 내용이면 산문으로.

---

## 공통 패턴

### C1. 동의어 순환 (Elegant Variation) [P2]

**문제:** AI가 반복 회피를 위해 같은 대상을 다른 단어로 계속 바꿔 부름.

**수정 전:**
> 주인공은 많은 도전에 직면한다. 이 인물은 장애물을 극복해야 한다. 해당 캐릭터는 결국 승리한다. 우리의 영웅은 집으로 돌아간다.

**수정 후:**
> 주인공은 많은 도전에 직면하지만 결국 이겨내고 집으로 돌아간다.

---

### C2. 지식 한계 면책 [P1]

**감지 표현 (한):** "정확한 정보는 확인이 필요합니다", "최신 정보와 다를 수 있습니다"
**감지 표현 (영):** "as of [date]", "Up to my last training update", "based on available information"

**원칙:** 전부 삭제. 정확한 출처를 찾거나, 모르면 모른다고 쓰기.

---

### C3. 긍정적 결론 공식 [P1]

**감지 표현 (한):** "밝은 미래가 기대됩니다", "무한한 가능성이 열려 있습니다", "함께 노력해야 할 것입니다"
**감지 표현 (영):** "The future looks bright", "Exciting times lie ahead", "a major step in the right direction"

**원칙:** 구체적인 다음 단계로 교체하거나 삭제.

---

### C4. 이모지 장식 [P1]

**문제:** 제목이나 목록에 이모지를 붙이는 것.

**원칙:** 사용자가 명시적으로 요청하지 않으면 전부 제거.

---

### C5. 균일한 문단 길이 [P2]

**문제:** AI가 모든 문단을 비슷한 길이(3-4문장)로 맞추는 경향. 사람은 한 문장짜리 문단도 쓰고, 긴 문단도 쓴다.

**원칙:** 문단 길이가 기계적으로 균일하면, 일부를 합치거나 쪼개서 리듬감을 만든다.

---

### C6. 강제 3단 구조 [P2]

**문제:** AI가 글 유형에 관계없이 항상 "도입 → 본론 → 결론"을 강제. 짧은 글이나 메모에도 도입부와 결론을 넣는다.

**원칙:** 글의 길이와 목적에 맞지 않는 도입부/결론은 삭제. 500자 미만의 글에 "결론적으로"는 거의 항상 불필요.

---

## 전체 예시

### 수정 전 (한국어 AI 글):

> 오늘날 급변하는 디지털 시대에 접어들면서, AI 코딩 도구에 대한 관심이 날로 높아지고 있습니다. 이번 글에서는 AI 코딩 도구의 다양한 측면에 대해 자세히 알아보겠습니다.
>
> AI 코딩 도구는 혁신적인 기술을 통해 개발자들의 생산성을 획기적으로 향상시키는 핵심적인 역할을 하고 있다고 할 수 있습니다. 이를 통해 효과적인 코드 작성이 가능해지며, 이를 바탕으로 체계적인 개발 환경을 구축할 수 있습니다.
>
> 그렇다면 왜 AI 코딩 도구가 필요할까요? 그 이유는 크게 세 가지로 나눌 수 있습니다.
>
> - 🚀 **생산성 향상:** AI 코딩 도구는 코드 자동 완성뿐만 아니라 리팩토링, 테스트 생성까지 지원하여 개발 속도를 혁신적으로 높여줍니다.
> - 💡 **품질 개선:** 다양한 코드 분석 기능을 통해 버그를 사전에 탐지하고 효과적으로 해결할 수 있습니다.
> - ✅ **학습 효과:** 초보 개발자들에게 체계적인 학습 경험을 제공하여 빠른 성장을 도울 수 있습니다.
>
> 물론 AI 코딩 도구에는 장점만 있는 것은 아닙니다. 한편으로는 생산성을 높여주지만, 다른 한편으로는 코드의 정확성 문제, 보안 취약점, 저작권 이슈 등 다양한 과제가 존재합니다. 이러한 관점에서 볼 때, AI 코딩 도구의 중요성은 아무리 강조해도 지나치지 않습니다.
>
> 결론적으로, AI 코딩 도구는 소프트웨어 개발의 미래를 밝게 만들어 줄 것으로 기대됩니다. 앞으로 AI 기술의 지속적인 발전과 함께 개발자 커뮤니티의 관심이 더욱 높아질 것입니다. 도움이 되셨길 바랍니다!

### 수정 후 (사람이 쓴 글):

> AI 코딩 도구가 생산성을 올려준다는 건 반쯤 맞다.
>
> 자동 완성이 빨라지는 건 체감된다. 보일러플레이트, 테스트 스캐폴딩, 반복 리팩토링 같은 건 확실히 빠르다. 다만 디버깅이나 설계 판단에서는 차이를 못 느꼈다. 자동 완성이 빨라지는 거지, 사고가 빨라지는 건 아닌 셈이다.
>
> 솔직히 말하면 가장 위험한 순간은 제안을 무비판적으로 수락할 때다. 컴파일 되고 린트 통과하고 그런데 틀린 코드, 나도 몇 번 당했다. 집중력이 떨어질 때 특히 그렇다.
>
> 보안 쪽은 더 걱정된다. AI가 생성한 코드의 취약점을 체계적으로 추적한 연구가 아직 많지 않다.
>
> 쓸 거면 쓰되, 모든 제안을 리뷰하고, 테스트를 먼저 쓰고, AI 제안은 그 테스트를 통과할 때만 수락하라.

### 변경 사항:
- [K1] 도입부 상투어 제거 ("오늘날", "알아보겠습니다")
- [K2] 과장 수식어 제거 ("혁신적인", "획기적인", "체계적인", "효과적인", "핵심적인", "다양한")
- [K3] 회피 어미 제거 ("~라고 할 수 있습니다")
- [K4] "이를 통해/바탕으로" 연쇄 제거
- [K5] 무의미한 중요성 강조 제거
- [K6] "~뿐만 아니라" 제거
- [K7] "그렇다면 왜~" 자문자답 제거
- [K8] 셋 법칙 해체
- [K10] 결론 상투어 제거 → 실용적 조언으로 대체
- [K11] 대화형 흔적 제거 ("도움이 되셨길 바랍니다!")
- [K13] 장단점 대칭 구조 해체 → 구체적 의견으로
- [C4] 이모지 제거
- [C5] 균일한 문단 길이 해체 → 리듬감 추가
- [C6] 강제 결론 삭제
- [E12] 볼드체 과용 / 인라인 헤더 목록 해체
- 영혼 주입: 1인칭 시점, 개인 경험, 솔직한 의견 (블로그/에세이 유형)

---

## 전체 예시 (영어)

### 수정 전 (영어 AI 글):

> In today's rapidly evolving landscape of software development, containerization has emerged as a pivotal technology that is fundamentally transforming the way we build and deploy applications. Let's dive in and explore this groundbreaking approach.
>
> Docker serves as a robust platform that enables seamless containerization. It's worth noting that this technology offers several key advantages:
>
> 1. **Consistency:** Docker ensures consistent environments across development, staging, and production.
> 2. **Scalability:** It provides seamless scalability through orchestration tools like Kubernetes.
> 3. **Efficiency:** Docker leverages OS-level virtualization to deliver enhanced resource efficiency.
>
> Additionally, the intricate interplay between containers and microservices has fostered a vibrant ecosystem of tools and practices. Not only does containerization improve deployment speed, but it also enhances security through isolation.
>
> Despite these challenges, the future of containerization looks bright. As we've seen, this technology represents a paradigm shift in software development. In summary, Docker and containerization are essential tools in every developer's toolkit. I hope this helps!

### 수정 후 (사람이 쓴 글):

> Docker wraps your app and its dependencies into a single image. Same image runs on your laptop and in production — no more "works on my machine."
>
> The real win is deployment speed. Push an image, pull it on the server, done. No provisioning, no dependency conflicts. Kubernetes adds auto-scaling on top, but you don't need it to start.
>
> The downside nobody talks about enough: debugging a container is harder than debugging a process. Logs are scattered, networking is abstracted away, and when something breaks at 3 AM you're SSH-ing into a pod instead of a server. Worth it for most teams, but not free.

### 변경 사항:
- [E1] 중요성 과장 제거 ("pivotal", "fundamentally transforming")
- [E4] 홍보성 언어 제거 ("groundbreaking", "robust", "seamless", "leverages")
- [E7] AI 빈출 어휘 제거 ("Additionally", "intricate", "interplay", "vibrant")
- [E8] 계사 회피 수정 ("serves as" → "is"로 풀림)
- [E9] 부정 병렬 구조 제거 ("Not only...but also")
- [E12] 인라인 헤더 목록 해체 → 산문으로
- [E13] 대화형 잔류물 제거 ("Let's dive in", "I hope this helps!")
- [E18] 불필요한 요약 반복 제거 ("As we've seen", "In summary")
- [E19] 과도한 구조화 해체 → 산문으로
- [C3] 긍정적 결론 삭제 ("the future looks bright")
- 영혼 주입: 솔직한 단점 언급, 구체적 시나리오 (새벽 3시 디버깅)

---

## 레퍼런스

이 스킬은 다음 자료를 기반으로 한다:
- [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — WikiProject AI Cleanup이 유지보수하는 AI 글쓰기 징후 가이드
- 한국어 AI 텍스트 분석에서 관찰된 패턴

핵심 인사이트: "LLM은 통계적 알고리즘으로 다음에 올 내용을 추측한다. 결과는 가장 통계적으로 가능성 높은, 가장 넓은 범위에 적용되는 결과로 수렴한다." 한국어에서도 동일한 원리가 작동하며, "다양한", "혁신적인", "이를 통해" 같은 고빈도 표현으로 나타난다.
