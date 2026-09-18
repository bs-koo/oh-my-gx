# 진입점 체인 추출 규칙

`service`·`sequence` 뷰의 코드 근거 노드는 `scripts/scan_entrypoints.py`가 진입점 체인(화면 → API → 서비스 → 저장소 → 테이블)만 결정적으로 추출한 결과다. 이 문서는 그 추출 규칙의 정본이다.

## 언어별 kind 판정

| kind | Java Spring | JSP·Servlet |
|---|---|---|
| `screen` | — | `**/*.jsp` 파일 |
| `api` | `@RequestMapping`·`@GetMapping`·`@PostMapping`·`@PutMapping`·`@DeleteMapping`·`@PatchMapping`이 붙은 메서드 | `HttpServlet` 상속 클래스의 `doGet`·`doPost` |
| `service` | `@Service` 클래스 | `*Service`·`*ServiceImpl` 클래스 |
| `repository` | `@Repository`·`@Mapper` 클래스·인터페이스 | `*DAO`·`*Dao` 클래스 |
| `table` | MyBatis XML의 `<select>`·`<insert>`·`<update>`·`<delete>` 본문에서 추출한 테이블명 | 동일 |

## edge relation 값

- `requests`: screen → api
- `calls`: api → service, service → repository. 컬렉터가 필드로 찾은 협력자는 계층을 가리지 않으므로 **같은 계층 안의 호출도 나온다**(`service → service`, `repository → repository`) — 예: 한 서비스가 다른 서비스나 매퍼를 필드로 갖는 경우.
- `reads`·`writes`: repository → table (MyBatis `select`는 `reads`, `insert`·`update`·`delete`는 `writes`)

## 제약

체인 밖 클래스는 노드로 만들지 않는다. 호출 관계는 **같은 파일 안의 타입 참조**로만 판정한다 — 런타임 주입 경로를 추론하지 않는다.
