# 공통 패턴 + 전체 예시

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
