# 진입점 체인 추출 규칙

`service` 뷰의 코드 근거 노드는 `scripts/scan_entrypoints.py`가 진입점 체인(화면 → API → 서비스 → 저장소 → 테이블)을 정적으로 추출한 결과다. `sequence`의 실제 순서를 알려면 별도의 순서 근거가 필요하다.

## 언어별 kind 판정

| kind | Java Spring | JSP·Servlet |
|---|---|---|
| `screen` | — | `**/*.jsp` 파일 |
| `api` | `@RequestMapping`·`@GetMapping`·`@PostMapping`·`@PutMapping`·`@DeleteMapping`·`@PatchMapping`이 붙은 메서드 | `HttpServlet` 상속 클래스의 `doGet`·`doPost` |
| `service` | `@Service` 클래스, `service` 경로·패키지의 `@Component` 지원 클래스, 이름이 `*Facade`·`*FacadeImpl`인 클래스 | `*Service`·`*ServiceImpl`·`*Facade`·`*FacadeImpl` 클래스 |
| `repository` | `@Repository`·`@Mapper` 클래스·인터페이스 | `*DAO`·`*Dao` 클래스 |
| `table` | MyBatis XML의 `<select>`·`<insert>`·`<update>`·`<delete>` 본문에서 추출한 테이블명 | 동일 |

**Facade와 서비스 지원 클래스.** 컨트롤러와 여러 서비스 사이에 `@Component` Facade를 두는 구조가 있다(kereb reb: `RebController → RebFacade → 서비스들`). 서비스 구현 안에서 Reader·Executor·Linker에게 처리를 위임하기도 한다. 이런 클래스가 빠지면 Mapper·DB로 이어지는 체인이 끊기므로, 프로젝트 상대 경로나 Java package에 정확한 `service` 세그먼트가 있는 `@Component`를 서비스 계층으로 포함한다. `service/impl`도 해당하며 이름의 접미사는 제한하지 않는다. 그 경계 밖의 `@Component` 유틸(예: `support/ExcelSupport`)과 어노테이션 없는 지원 클래스는 이 조건으로 추가하지 않는다. 경계 밖에서도 이름이 `Facade`·`FacadeImpl`이면 기존 규칙으로 서비스 계층에 포함한다. 인터페이스 `XFacade` + 구현 `XFacadeImpl`도 기존 Impl 병합이 한 노드로 합친다. `facade` 폴더는 `controller`·`service`처럼 계층 폴더로 취급한다 — 도메인은 그 앞 세그먼트다.

## edge relation 값

- `requests`: screen → api
- `calls`: 해당 메서드 본문에서 확인한 협력자 호출. 같은 계층 안의 호출도 근거가 있으면 남긴다. 필드를 주입받았다는 이유만으로 모든 API에 호출을 연결하지 않는다.
- `depends_on`: 주입된 필드·생성자 타입의 의존 관계. 실제 호출과 구분하며 primitive·String 같은 값 필드는 협력자로 취급하지 않는다.
- `reads`·`writes`: repository → table. SQL 절별로 FROM·JOIN 등의 원본은 읽기, INSERT/UPDATE/DELETE의 대상은 쓰기로 구분한다. 한 쓰기 문장에도 읽는 테이블이 있을 수 있다.

Spring 매핑은 `value`·`path`, 배열, 줄바꿈, 무인자 형태를 처리한다. 클래스와 메서드의 HTTP 메서드 조건은 Spring의 합집합 규칙을 적용한다. 클래스 `GET` + 메서드 미지정은 `GET`, 클래스 `GET` + 메서드 `POST`는 `GET`·`POST`로 표시한다. 둘 다 미지정이면 `ANY`다. 이는 선언 조건이며 자동 HEAD/OPTIONS 처리까지 펼친 목록은 아니다. [Spring RequestMethodsRequestCondition 소스](https://github.com/spring-projects/spring-framework/blob/main/spring-webmvc/src/main/java/org/springframework/web/servlet/mvc/condition/RequestMethodsRequestCondition.java)의 `combine`을 따른다. 선언을 발견했지만 해석하지 못한 매핑은 진단에 남긴다. private 이외 가시성과 final 필드도 확인한다. 동명 타입을 하나로 좁힐 수 없으면 `unresolved_edges`로 보고한다.

SQL 주석·문자열·CTE 이름·테이블 함수·XML 태그를 실제 테이블로 만들지 않는다. 함수 내부의 FROM과 `IS [NOT] DISTINCT FROM` 비교식도 테이블 절과 구분한다. 스키마가 다른 동명 테이블은 ID에서 구분하고 짧은 표시명은 마지막 테이블명을 사용한다. include·동적 SQL에서 정적으로 결정할 수 없는 이름은 진단을 확인한다. SQL 본문이나 값을 IR에 복사하지 않는다.

### MyBatis include 정적 확장

`<include refid="..."/>`와 자식 `<property name="..." value="..."/>`가 있는 형태를 XML 노드로 읽는다. 문자열·CDATA 안에 적힌 include 태그는 실행하지 않고 XML 주석도 무시한다. CDATA의 SQL 자체와 XML 문자 엔티티는 정상 분석한다. 다음 스코프 규칙은 [MyBatis XMLIncludeTransformer 소스](https://mybatis.org/mybatis-3/xref/org/apache/ibatis/builder/xml/XMLIncludeTransformer.html)를 따른다.

- `refid`와 각 property 값은 부모 include에서 상속받은 값으로 해석한다. 같은 include의 property가 자기 `refid` 또는 형제 property를 순차적으로 정의하지 않는다.
- 로컬 property는 포함되는 조각 안에서 상속값을 덮어쓰며, 형제 include나 호출 바깥으로 유출되지 않는다. 포함된 SQL 텍스트·CDATA와 중첩 include의 참조에서 정적으로 확정된 값만 치환한다.
- 외부 namespace 조각 안의 짧은 `refid`도 최초 호출 mapper의 namespace로 해석한다. 조각 파일의 namespace로 임의 전환하지 않는다.
- 같은 include에 중복 property가 있으면 `duplicate-sql-include-property`, 지원하지 않는 자식 형식은 `unsupported-sql-include`, 손상된 XML 조각은 `unsupported-sql-xml`로 기록하고 해당 조각을 추측하지 않는다.
- 미해소·순환 참조와 깊이 16 이상의 include는 `unresolved-sql-include`로 남긴다. 한 SQL 문장의 확장이 256회 또는 누적 100만 문자를 넘으면 `sql-include-limit` 진단과 함께 나머지 확장을 중단한다.

외부 MyBatis 설정의 properties, 런타임 치환값, 설정으로 켜는 placeholder 기본값 기능은 읽지 않는다. `${...}`가 남으면 `dynamic-sql-identifier` 또는 미해소 include 진단을 확인한다.

SQL 노드는 [MyBatis DynamicContext](https://github.com/mybatis/mybatis-3/blob/master/src/main/java/org/apache/ibatis/scripting/xmltags/DynamicContext.java)처럼 공백으로 결합하고 `where`·`set`의 절 경계를 보존한다. `<if>` 안의 명시적인 JOIN 등은 정적 후보로 남기되 조건을 실행했다고 해석하지 않는다. [ChooseSqlNode](https://github.com/mybatis/mybatis-3/blob/master/src/main/java/org/apache/ibatis/scripting/xmltags/ChooseSqlNode.java)가 실행 시 하나를 선택하는 `choose`·`when`·`otherwise` 조각은 서로 이어 붙이지 않는다. 해당 조각은 미확정 표식으로 대체하고 `dynamic-sql-branch` 진단을 남긴다. 따라서 분기 안에서만 나타나는 테이블은 맵에 누락될 수 있으며 원본 확인이 필요하다.

`foreach`는 반복을 실행하지 않고 구분 괄호만 보존한다. 단순 파라미터 값 목록 밖에 동적 이름이나 테이블 절이 있으면 `dynamic-sql-loop`로 기록한다. 결과는 정적으로 확인한 후보이며 실행 시 접근 테이블의 확정 목록은 아니다.

빌드·의존성 디렉터리와 프로젝트 안의 `.claude/worktrees`·`.codex/worktrees` 복제본은 탐색에서 제외한다. 복제 작업 폴더 자체를 프로젝트 루트로 지정하면 그 루트의 소스는 정상 분석한다.

## 서비스 인터페이스·구현체 병합

eGov·Spring 관례상 컨트롤러는 인터페이스를 주입받고 실제 로직은 `{X}Impl`에 있다. 스캐너는 파일 단위로 노드를 만들기 때문에 병합하지 않으면 인터페이스 노드는 컨트롤러에서만 닿는 막다른 길이 되고, 구현체가 호출하는 저장소 쪽은 별개의 덩어리로 남아 체인이 끊긴다(모든 GX 프로젝트에서 발생).

- 선언된 `implements`와 기존 `{X}Impl` 관례를 확인해 인터페이스와 구현체가 유일하게 대응할 때만 합친다. 여러 구현체 중 하나를 임의로 선택하지 않는다.
- 살아남는 노드는 인터페이스(`{X}`)다 — 컨트롤러가 필드 타입으로 가리키는 대상이라 ID가 안정적이다.
- 구현체의 나가는·들어오는 엣지는 인터페이스로 옮긴다. 합친 뒤 자기 자신을 가리키게 된 엣지는 버린다.
- 구현체의 `evidence`는 인터페이스의 `evidence`에 정렬해서 합친다 — 어느 파일에서 왔는지 잃지 않는다.
- 짝이 되는 인터페이스가 없거나, 같은 이름의 서비스 노드가 여럿이라 하나로 못 좁히면(패키지가 다른 동명 클래스) **합치지 않고 그대로 둔다** — 없는 인터페이스를 지어내지 않는다.

## 제약

체인 밖 클래스는 노드로 만들지 않는다. Java Spring·JSP/Servlet·MyBatis/iBATIS XML을 대상으로 하며 완전한 Java/SQL 파서는 아니다. JavaScript·Python·다른 ORM의 전체 호출망, 리플렉션, 런타임 DI 선택, 동적 SQL 실행 결과는 보장하지 않는다. `calls`도 정적 근거이지 실행 순서·빈도의 증명이 아니다.

UTF-8 읽기가 실패하면 CP949로 재시도한다. 읽지 못한 파일은 `skipped`, 대상이 해소되지 않은 관계는 `unresolved_edges`에 남긴다. 진단의 이유·파일·라인·대상을 따라 원본을 확인한다. 이미 확인된 도메인 간 관계는 누락이 아니며 전체 IR과 외부 도메인 노드로 보존한다.
