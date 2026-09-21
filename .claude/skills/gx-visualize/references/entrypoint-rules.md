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

## 서비스 인터페이스·구현체 병합

eGov·Spring 관례상 컨트롤러는 인터페이스를 주입받고 실제 로직은 `{X}Impl`에 있다. 스캐너는 파일 단위로 노드를 만들기 때문에 병합하지 않으면 인터페이스 노드는 컨트롤러에서만 닿는 막다른 길이 되고, 구현체가 호출하는 저장소 쪽은 별개의 덩어리로 남아 체인이 끊긴다(모든 GX 프로젝트에서 발생).

- `service` kind 노드 중 라벨이 `{X}Impl`이고, 같은 이름의 `{X}` 노드가 **정확히 하나** 존재할 때만 합친다.
- 살아남는 노드는 인터페이스(`{X}`)다 — 컨트롤러가 필드 타입으로 가리키는 대상이라 ID가 안정적이다.
- 구현체의 나가는·들어오는 엣지는 인터페이스로 옮긴다. 합친 뒤 자기 자신을 가리키게 된 엣지는 버린다.
- 구현체의 `evidence`는 인터페이스의 `evidence`에 정렬해서 합친다 — 어느 파일에서 왔는지 잃지 않는다.
- 짝이 되는 인터페이스가 없거나, 같은 이름의 서비스 노드가 여럿이라 하나로 못 좁히면(패키지가 다른 동명 클래스) **합치지 않고 그대로 둔다** — 없는 인터페이스를 지어내지 않는다.

## 제약

체인 밖 클래스는 노드로 만들지 않는다. 호출 관계는 **같은 파일 안의 타입 참조**로만 판정한다 — 런타임 주입 경로를 추론하지 않는다.
