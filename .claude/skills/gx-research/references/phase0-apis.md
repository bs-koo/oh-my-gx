# gx-research Phase 0 공식 API 카탈로그

gx-research SKILL.md Step 2의 2-2a에서 읽는다. 주제와 키워드를 **lowercase + Unicode NFC 정규화** 후 아래 신호 단어를 **substring** 검사한다 (단어 경계 미요구). URL의 `{키워드}` 자리는 **URL-encode**한다 (한국어·공백·특수문자 안전 처리). 응답 실패 정책은 SKILL.md가 정본이다.

## 카탈로그

| 카테고리 | 신호 단어 | API 엔드포인트 | 응답 처리 힌트 |
|----------|----------|---------------|---------------|
| 학술 논문 | `arxiv`, `논문`, `paper`, `preprint` | `http://export.arxiv.org/api/query?search_query=all:{키워드}&max_results=10` | Atom XML → entry별 title·summary·author·published 추출 |
| 오픈소스 저장소 | `github`, `repo`, `오픈소스`, `라이브러리` | `https://api.github.com/search/repositories?q={키워드}&per_page=10` | JSON items → full_name·description·stargazers_count·language |
| Hacker News | `hacker news`, `hn`, `해커뉴스` | `https://hn.algolia.com/api/v1/search?query={키워드}&hitsPerPage=10` | hits → title·url·points·num_comments |
| 프로그래밍 Q&A | `stackoverflow`, `스택오버플로우` | `https://api.stackexchange.com/2.3/search?intitle={키워드}&site=stackoverflow&order=desc&sort=votes` | items → title·link·score·answer_count |
| npm 패키지 | `npm`, `노드 패키지`, `node package` | `https://registry.npmjs.org/-/v1/search?text={키워드}&size=10` | objects[].package → name·description·version·links.repository |
| PyPI 패키지 | `pypi`, `파이썬 패키지`, `python package` | `https://pypi.org/pypi/{정확한 패키지명}/json` | info → name·summary·version·project_url. 404면 결과 없음으로 기록 |
| 백과사전 | `wikipedia`, `위키`, `정의`, `용어` | `https://ko.wikipedia.org/api/rest_v1/page/summary/{topic}` | title·extract·content_urls.desktop.page. 404 시 영어 fallback 1회: `https://en.wikipedia.org/api/rest_v1/page/summary/{topic}` |
| 한국 종합 뉴스 | "최근/최신/뉴스/보도" 중 1개 + 정치/사회/경제/IT 도메인 키워드 (단순 기술 키워드만 있으면 미매칭) | `https://news.google.com/rss/search?q={키워드}&hl=ko&gl=KR&ceid=KR:ko` | RSS item별 title·link·pubDate·source. 최근 10건 |

## 모드 차등


- 꼼꼼: 매칭된 모든 카테고리 호출
- 빠르게: 매칭된 카테고리 중 **최대 2개** 호출 (관련도 순: 긴 신호어 우선 → 주제 등장 위치 우선)
