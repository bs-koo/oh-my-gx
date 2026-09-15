---
name: gx-context
description: 도메인 컨텍스트를 생성·갱신·동기화한다. "컨텍스트", "도메인 등록", "용어 정리" 시 사용.
argument-hint: "[도메인명] [--from <파일경로>] [--sync]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(git *)
  - Bash(svn *)
  - Bash(gh *)
  - Bash(test *)
  - Bash(mkdir *)
  - AskUserQuestion
---

# context

도메인 컨텍스트를 관리한다. 상황에 따라 자동으로 적절한 모드를 선택한다.

**하네스 적응**: 이 문서는 Claude Code 도구명으로 서술한다. 다른 하네스에서 실행 중이면 아래 대응으로 옮겨 수행한다.

Codex에서는 먼저 `Read("../gx-dev/references/codex-runtime.md")`로 공통 실행 규약을 읽고, 이 스킬의 절차·게이트를 유지한다. 상대경로는 이 SKILL.md 위치 기준이다.
Codex on Windows: read this SKILL.md and referenced files as UTF-8; use `Get-Content -Encoding UTF8`.

- `AskUserQuestion` → `request_user_input`. 그 도구를 쓸 수 없으면 자연어로 묻되, **승인 없이 다음 단계로 넘어가지 않는다**는 계약은 그대로 지킨다.

질문은 한 번에 1~3개, 질문마다 선택지는 2~3개로 제한한다. 추천 답변은 첫 번째에 놓고 label 끝에 `(Recommended)`를 붙인다. UI가 자유 입력을 제공하므로 Other를 option으로 직접 추가하지 않는다. Codex 변환에서는 `../gx-dev/references/codex-runtime.md`와 실제 도구 스키마를 우선한다.

도구 이름이 다르다는 이유로 게이트를 건너뛰지 않는다. 확인·검증 단계는 하네스와 무관하게 유지한다.

## 인자 파싱

Arguments 문자열에서 아래 규칙으로 파싱한다:
- `--from <경로>`: `--from` 다음 토큰을 파일 경로로 사용. 경로에 공백이 있으면 따옴표로 감싸진 것으로 간주.
- `--sync`: 진행도 동기화 모드. git 히스토리 기반으로 status.md 갱신.
- `--from`과 `--sync`를 제외한 나머지 토큰: 도메인명으로 사용.
- `--sync`와 `--from`은 동시 사용 불가. 동시 지정 시 "`--sync`와 `--from`은 동시에 사용할 수 없습니다." 안내 후 중단.
- 인자 없음: 도메인명과 `--from`, `--sync` 모두 없음.

예시:
- `결제` → 도메인명=결제, from=없음, sync=없음
- `정산 --from docs/req.md` → 도메인명=정산, from=docs/req.md
- `--from docs/req.md` → 도메인명=없음, from=docs/req.md
- `결제 --sync` → 도메인명=결제, sync=true
- (빈 인자) → 도메인명=없음, from=없음, sync=없음

## 수칙

- **모호하고 일반적인 표현을 허용하지 않는다.** 답변이 "효율화", "개선" 같은 추상어로만 구성되면 구체화를 요청한다.
- **누락된 데이터를 가정하지 않는다.** 사용자가 모르는 항목은 ❓로 남기되, 빈칸이 있다는 것을 명시한다.
- **정량화를 요구한다.** "많이", "자주" 대신 숫자를 묻는다. 정확하지 않아도 추정치라도 기록한다.
- **충분한 정보가 모일 때까지 산출물로 넘어가지 않는다.** 모호한 답변에는 그 자리에서 파고들기 질문으로 구체화를 요청하고, 충분한 정보가 모인 후에만 다음 단계로 진행한다.
- **모든 질문에 권장 답변을 제시한다.** 사용자가 결정 부담을 덜 수 있도록, 현재 맥락에서 가장 가능성 높은 답 또는 합리적 추정을 options 첫 번째에 `(Recommended)` 라벨로 반드시 제시한다.

## 모드 자동 판단

인자와 현재 상태를 기반으로 모드를 결정한다:

| 조건 | 모드 | 동작 |
|------|------|------|
| `context/` 폴더 없음 + 인자 없음 | **스캔** | 코드베이스 분석 → context 초안 자동 생성 |
| `context/` 폴더 없음 + 도메인명 지정 | **스캔+신규** | 코드베이스 스캔 후 해당 도메인 우선 생성 |
| `context/` 있음 + 도메인명 지정 + `--from` 없음 | **신규** | Q&A 기반 새 도메인 생성 |
| `context/` 있음 + 도메인명 지정 + `--from <파일>` | **문서 기반** | 파일 읽고 → 내용 기반으로 context 생성/갱신 |
| `context/` 있음 + `--from <파일>` + 도메인명 없음 | **문서 기반** | 파일에서 도메인명을 추론하여 생성/갱신 |
| `context/` 있음 + 인자 없음 | **선택** | 사용자에게 질문: 새 도메인 추가 / 기존 도메인 갱신 / 코드베이스 재스캔 |
| `context/{도메인}/` 이미 존재 + `--from <파일>` | **갱신** | 파일 읽고 기존 context와 비교 → 변경 제안 |
| `context/{도메인}/` 이미 존재 + `--from` 없음 | **갱신** | 사용자에게 갱신 대상 확인 후 Q&A |
| `context/{도메인}/` 존재 + `--sync` | **동기화** | git log/PR 분석 → status.md 갱신 |

## 모드 실행

모드를 결정한 직후 아래 해당 파일 하나만 Read하고 그 절차를 실행한다. 선택한 모드의 절차가 끝나면 종료한다. 상대경로는 이 SKILL.md 위치 기준이다.

- `신규` → `Read("modes/create.md")`
- `문서 기반` → `Read("modes/from-document.md")`
- `갱신` → `Read("modes/update.md")`
- `동기화` → `Read("modes/sync.md")`

`스캔`은 아래 모드 A를 이 SKILL.md에서 계속 실행한다. 스캔 중 수동 생성으로 전환하거나 A-3에서 루트 README.md·glossary.md 초기화에 B-0 템플릿이 필요할 때 또는 새 도메인의 status.md에 B-9-1 템플릿이 필요할 때, 문서 기반 모드가 내부에서 신규·갱신 절차를 호출할 때만 해당 mode 파일을 추가로 Read한다.

---

## 모드 A: 스캔 (코드베이스 분석)

`context/` 폴더가 없거나 사용자가 재스캔을 선택한 경우 실행한다.

### A-0. 사용자 확인

```
AskUserQuestion(
  questions: [{
    header: "context 생성",
    question: "context/ 디렉토리가 없습니다. 코드베이스를 분석하여 도메인 구조를 자동 생성할까요?",
    multiSelect: false,
    options: [
      { label: "자동 생성", description: "코드베이스 스캔으로 도메인 구조를 자동 생성합니다" },
      { label: "수동 생성", description: "질문에 답하며 도메인을 수동으로 생성합니다" }
    ]
  }]
)
```
- "자동 생성" → A-1로 진행
- "수동 생성" → `Read("modes/create.md")` 후 모드 B(신규)로 전환하여 수동 생성

### A-1. 프로젝트 구조 스캔

아래 항목을 병렬로 탐색한다:

1. **디렉토리 구조**: 소스 루트 하위 최상위 2레벨을 스캔하여 도메인 후보를 추론한다. 언어 무관 휴리스틱:
   - 파일 확장자 클러스터로 소스 루트를 판별한다 (`.java`/`.kt`/`.ts`/`.py`/`.c`/`.h`/`.go`/`.rs` 등)
   - 업무 명사 디렉토리명 군집을 도메인 후보로 본다 (payment/, order/, sensor/, protocol/ 등)
   - 언어별 예시: Java `src/main/java/{base-package}/` 하위 패키지, Node `src/` 하위 modules/·features/·domains/, C `src/`·`include/` 하위 모듈 디렉토리
2. **도메인 모델**: 네이밍 패턴 군집으로 탐색한다 — 접미사형(`*Entity.java`, `*.entity.ts`, `*Model.*`) 또는 C 계열 모듈 쌍(`{이름}.h`/`{이름}.c`)의 구조체(typedef struct) 정의.
3. **진입점/인터페이스**: API 라우팅(`*Controller.java`, `*Router.*`, `routes/`) 또는 C 계열 공개 헤더(include/ 디렉토리, extern 함수 선언이 밀집한 헤더).
4. **설정 파일**: `application.yml`, `application.properties`, `.env`, `package.json`, `Makefile`/`CMakeLists.txt`, `Kconfig` 등을 읽는다.
5. **README/문서**: 프로젝트 루트의 `README.md`, `docs/` 디렉토리를 확인한다.

### A-2. 도메인 분류

스캔 결과에서 도메인을 추론한다:
- 패키지 구조 기반: `com.example.payment` → 결제 도메인
- 엔티티 클러스터 기반: 관련 엔티티를 그룹핑
- API 엔드포인트 기반: `/api/orders/**` → 주문 도메인
- 모듈 접두사 기반 (C 계열): `uart_*.h`/`sensor_*.c` 군집 → 통신/센서 도메인

### A-3. 초안 생성

`context/README.md` 또는 `context/glossary.md`가 없으면 초기화 전에 `Read("modes/create.md")`로 B-0의 해당 루트 파일 템플릿을 읽는다. 새 도메인의 `status.md`를 생성할 때는 두 루트 파일이 모두 있어도 생성 전에 `Read("modes/create.md")`로 B-9-1의 5열 요구사항 원장과 `<!-- gx-sync ... -->` cursor 템플릿을 읽는다. 같은 A-3에서 두 조건이 모두 참이면 한 번만 Read한다.

각 감지된 도메인에 대해:
1. 도메인별 디렉토리 생성: `mkdir -p context/{도메인}/`
2. `context/` 루트 파일 초기화 (필요시):
   - `test -f context/README.md` 가 false인 경우, `Read("modes/create.md")`의 B-0과 동일하게 `context/README.md` 생성
   - `test -f context/glossary.md` 가 false인 경우, `Read("modes/create.md")`의 B-0과 동일하게 `context/glossary.md` 생성
3. 스캔 결과를 기반으로 각 문서 초안 작성:
   - **README.md**: 도메인 개요 (스캔에서 파악한 범위, 주요 기능)
   - **PROJECTS.md**: 현재 레포를 자동 등록한다. git은 `git remote get-url origin`의 레포명을 사용한다. svn은 `svn info --show-item url` 종료 코드 != 0이면 진단 후 중단한다. URL 끝에서 `trunk`, `branches/<name>`, `tags/<name>`을 제거하고 남은 마지막 세그먼트를 `REPOSITORY_ID`로 쓴다. 성공했지만 URL·ID가 비거나 모호하면 경고 후 `basename(PROJECT_ROOT)`를 쓴다.
   - **glossary.md**: 엔티티명, 주요 상수, enum 값 등에서 추출한 용어 초안
   - **architecture.md**: 패키지 구조, 레이어 구조 요약
   - **status.md**: 빈 템플릿

### A-4. 사용자 검토

생성된 초안을 사용자에게 보여주고 확인을 받는다:
- "N개 도메인을 감지했습니다: {목록}. 확인해주세요."
- 사용자가 도메인을 추가/제거/이름 변경할 수 있다.
- 각 도메인의 README.md 초안을 보여주고 수정 사항을 반영한다.
- 담당자 정보를 질문한다: "각 도메인의 담당 PM/PO와 개발 리드를 알려주세요."

### A-5. 확정 및 인덱스 생성

사용자 확인 후:
- 수정 사항을 반영하여 최종 문서를 Write한다.
- `context/README.md` 도메인 테이블을 업데이트한다.
- 완료 안내: 생성된 도메인 수, 파일 수, ❓ 항목 안내.

---
