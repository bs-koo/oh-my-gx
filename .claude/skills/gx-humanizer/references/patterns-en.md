# 영어 AI 패턴 카탈로그

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
