# 공통 용어 사전

> 도메인을 가리지 않고 프로젝트 전체에서 쓰이는 용어입니다.
> 도메인별 용어는 `context/{도메인}/glossary.md`를 참조하세요.

| 용어 | 설명 |
|------|------|
| oh-my-gx | Java Spring Boot 및 풀스택 프로젝트용 AI 개발 플러그인 |
| GH | GitHub (github.com) |
| PRD | Product Requirements Document. 제품 요구사항 문서 |
| context/ | 도메인별 아키텍처·용어·구현 상태를 정리하는 디렉토리 |
| 4계층 아키텍처 | interfaces → application → domain → infrastructure 패키지 구조 |
| Facade 패턴 | Controller에서 호출하는 유스케이스 오케스트레이터. Service를 조합 |
| BaseEntity | 모든 JPA 엔티티의 부모. id, createdAt, updatedAt, deletedAt 자동 관리 |
| ApiResponse | 통합 API 응답 래퍼. meta(result, errorCode, message) + data |
| Spotless | Gradle 코드 포맷터 플러그인. 네이버 코딩 컨벤션 적용 |
| 전체/핵심 모드 (all/core) | gx-dev·gx-tdd 공통 2모드 체계. 전체 모드(all)는 전 Phase 진행, 핵심 모드(core)는 소형 변경용 경량 경로 — 오케스트레이터가 AC를 직접 작성(ac.md)하고 각 파이프라인의 필수 게이트는 유지한다 (dev: Mechanical Gate, tdd: RGR·verify·G-W-T·긴급 감사). 긴급 버그 수정도 핵심 모드로 라우팅 (AC를 재현 조건 관점으로) |
| 표준/에코 프로파일 (standard/eco) | 모드와 직교하는 모델 축. 에코 모드(eco)는 architect를 제외한 opus 에이전트를 sonnet으로 하향 디스패치해 토큰을 절약한다 (Task model 파라미터 오버라이드 — 절차·게이트 무변경, 설계는 게이트가 방어하지 못해 opus 유지). 결정: `--eco`/`--standard` 플래그 > 자연어 "에코 모드/에코로" > 모드 확인 질문의 답변(질문 시 모드·프로파일을 한 창에서 함께 선택 — 단 무인 루프 opt-in이 살아 있으면 모드는 all로 확정되어 프로파일 질문만 단독 제시) > config.json `modelProfile`(gx-setup 1회 설정) > 표준 |
| 무인 루프 opt-in (`--ralph`) | 모드·프로파일과 별개인 세 번째 축. 전체 모드 implement 진입 시 구현을 gx-ralph 무인 루프로 전환한다. 진입은 `--ralph` 플래그 또는 자연어 "랄프로/ralph로/무인 루프로 …"뿐이며 기본 경로에서는 묻지 않는다(v1.23.0). 우선순위: svn 프로젝트는 무시(모드 질문 정상), 자연어 opt-in은 선판정 모드(STATUS/RESUME/CORE/PHASE)에 밀려 안내만, 플래그 opt-in이 자연어 모드 트리거와 충돌하면 에러 후 중단. 살아남은 opt-in만 state.md `flags`에 `--ralph`로 기록되고 `--resume`으로 재개해도 유지된다 |

## 네이밍 규칙

### 도메인 엔티티

도메인 엔티티 클래스는 **도메인 이름 그대로** 짓는다. `Model`, `Entity` 등의 접미사를 붙이지 않는다.

| O (올바른 예) | X (잘못된 예) |
|--------------|-------------|
| `User` | `UserModel`, `UserEntity` |
| `Order` | `OrderModel`, `OrderEntity` |
| `Payment` | `PaymentModel`, `PaymentEntity` |

### 레이어별 클래스 네이밍

| 레이어 | 패턴 | 예시 |
|--------|------|------|
| domain | `{이름}` | `User`, `Order` |
| domain (repository) | `{이름}Repository` | `UserRepository` |
| application (service) | `{이름}Service` | `UserService` |
| application (facade) | `{이름}Facade` | `UserFacade` |
| interfaces (controller) | `{이름}Controller` | `UserController` |
| interfaces (DTO) | `{이름}Request`, `{이름}Response` | `UserCreateRequest`, `UserResponse` |
