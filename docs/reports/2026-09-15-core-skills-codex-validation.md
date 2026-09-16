# 1.33.0 핵심 스킬 Codex 실제 세션 검증

- 실행: 2026-09-16, Windows PowerShell, Codex CLI `0.154.0`
- 후보: `release/core-skills-hardening`, Git marketplace snapshot HEAD `4926a050e9c7add7e554a321cdc0408d1e85a7f5`
- 임시 소비 프로젝트: `D:\Temp\gx-core-skills-1330-task4`, 브랜치 `feat/smoke`, HEAD `c244ef90e28e056c43efd110eb74a12bcf6c0c82`
- 인증된 Codex 홈: `C:\Users\SQI\.codex\gx-validation-20260914` (`codex.cmd login status`: `Logged in using ChatGPT`)
- 설치 cache: `C:\Users\SQI\.codex\gx-validation-20260914\plugins\cache\oh-my-gx\oh-my-gx\1.33.0`
- 설치 명령: `codex.cmd plugin marketplace add bs-koo/oh-my-gx --ref release/core-skills-hardening --json` → `codex.cmd plugin add oh-my-gx@oh-my-gx --json`
- 설치 결과: `plugin list --json`의 `oh-my-gx@oh-my-gx`는 `version: 1.33.0`, `installed: true`, `enabled: true`, marketplace source `https://github.com/bs-koo/oh-my-gx.git`이었다. 설치 cache의 `.claude/skills/` 디렉터리는 17개였다.

인증과 설치는 확인했다. 다음 표의 `미실행`은 **해당 시나리오의 필수 행동과 증거가 완료되지 않았음**을 뜻한다. 세션 시작이나 스킬 파일 읽기를 시나리오 PASS로 취급하지 않는다.

| 시나리오 | 상태 | 실제 세션과 차단 지점 |
|---|---|---|
| S45: 중첩 cwd gx-tdd `--phase design` | 미실행 | `src/service`에서 `codex.cmd exec --json -s workspace-write`로 thread `01a0a783-6cc7-7373-a505-744b65149920`가 시작됐다. 스킬 파일을 읽으려는 `exec_command`가 두 차례 `helper_unknown_error: setup refresh had errors`로 실패했다. setup·requirements·design 및 루트 `.dev` 생성 증거가 없다. 시간 제한으로 세션을 중단했다. |
| S46: gx-context 문서 분석 질문 | 미실행 | 1.33.0 후보 `gx-context/SKILL.md`와 `codex-runtime.md`를 읽은 실제 세션은 있었다. 첫 입력은 중첩 cwd에서 `requirements/order.md`를 찾지 못했다. `../../requirements/order.md`로 고친 두 번째 입력은 문서를 찾았지만 중첩 cwd에서 `context/`를 찾지 못해 새 도메인 자동/수동 생성 선택을 자연어로 묻고 답을 기다리며 종료했다. 문제·규모 질문의 stable id, 사용자 답변, 결정 기록은 없다. 프로젝트 루트 cwd 본시험은 실행하지 못했다. |
| Q2: UI Other와 결정 capture | 미실행 | Codex 입력 UI의 Other 답변과 동일 snake_case id의 `codex_hook.py capture` 기록이 없다. gx-dev 모드·프로파일 선택 세션도 없다. 따라서 질문 개수·선택지 개수·Other 처리 계약은 실제 UI에서 검증되지 않았다. |

## 실제 trace와 관찰

실행 입력은 모두 `$env:CODEX_HOME='C:/Users/SQI/.codex/gx-validation-20260914'`를 먼저 설정했다. TDD는 `codex.cmd exec --json -C D:/Temp/gx-core-skills-1330-task4/src/service -s workspace-write '$oh-my-gx:gx-tdd 주문 검증 --phase design'`, 도구 진단은 같은 `-C`에서 `-s danger-full-access`로 설치된 gx-context SKILL.md 읽기만 요청했다. gx-context 첫 시도는 같은 중첩 `-C`에서 `'$oh-my-gx:gx-context 주문 --from requirements/order.md'`, 두 번째는 `'$oh-my-gx:gx-context 주문 --from ../../requirements/order.md'`였다. 두 gx-context prompt에는 후보 1.33.0 cache의 `gx-context/SKILL.md` 절대경로와 이전 1.32.0 cache를 사용하지 말라는 지시를 함께 넣었다. 프로젝트 루트 `-C`에서의 Q2 본시험은 시작하지 않았다.

원본 JSONL은 임시 소비 프로젝트의 `.smoke/`에 있다. TDD: `tdd-trace.jsonl`, 도구 진단: `diag-trace.jsonl`, 중첩 gx-context 첫 시도: `context-trace.jsonl`, 경로 수정 시도: `context-fixed-trace.jsonl`. 해당 trace는 PR에 포함하지 않았고 아래 SHA-256과 절대경로로 식별한다.

| trace | SHA-256 |
|---|---|
| `D:\Temp\gx-core-skills-1330-task4\.smoke\tdd-trace.jsonl` | `38B0A15278CA2E3E1ABE2AAD4D6E044B9B90471128CE28B393CB416108FE23A0` |
| `D:\Temp\gx-core-skills-1330-task4\.smoke\diag-trace.jsonl` | `03F99CA41C6B76D308A07E7FC89B7C8743265F506B8742815B89761A303E36A2` |
| `D:\Temp\gx-core-skills-1330-task4\.smoke\context-trace.jsonl` | `4581BD02E2247BDCD6ADFB8F8BE8311351608061B5E42D8430EE1DCA69CFEAC5` |
| `D:\Temp\gx-core-skills-1330-task4\.smoke\context-fixed-trace.jsonl` | `AEE23F753E1B9AC464412A85731C3F9996C65B18DBE65B195A36670CE2A184F2` |

`workspace-write` TDD 세션은 도구 초기화 실패 뒤 종료했다. `danger-full-access`로 파일 하나를 읽는 최소 진단은 도구 호출에 성공했지만, 그 진단은 오래된 `gx-final-validation` **1.32.0** cache를 먼저 선택했다. 그래서 진단 성공을 후보 스킬 성공으로 계산하지 않았다. 이후 gx-context 세션 두 개는 prompt에 1.33.0 cache의 절대 `SKILL.md` 경로를 지정했고 trace에서 그 파일을 실제로 읽은 것을 확인했다.

중첩 gx-context의 두 번째 세션은 `../../requirements/order.md`를 `source: True`, `./context`를 `context: False`로 관찰했다. 루트에는 `context/주문/README.md`와 요구사항 파일이 모두 있다. gx-context는 현재 호출 cwd의 `context/`와 `--from` 상대경로를 사용하며 VCS 루트로 자동 이동한다는 계약이 없다. 따라서 gx-context 본시험은 소비 프로젝트 **루트 cwd**에서 시작해야 한다. 두 번째 세션의 자연어 선택 질문은 실제 답을 기다린 뒤 종료했고, 후속 파일을 만들지 않았다.

실측 가능한 모델/effort와 `/hooks` 신뢰 상태는 이 trace에서 확보하지 못했다. 사용된 질문 도구는 구조화 `request_user_input`이 아니라 자연어였으며 UI Other 응답은 수행되지 않았다. 사용자 홈과 별도 subprocess 홈을 비교할 자료도 없다.

## 임시 프로젝트 불변성

세션 전후 HEAD는 `c244ef90e28e056c43efd110eb74a12bcf6c0c82`로 같다. index의 세 파일 Git blob은 `.claude/config.json` `cb6954e...`, `context/주문/README.md` `f0e3f95...`, `requirements/order.md` `26198bd...`로 유지됐다. `git status --short`에는 trace 보관용 `.smoke/`만 untracked로 보였고, 루트나 중첩 디렉터리에 `.dev`는 생성되지 않았다. fixture 파일 SHA-256은 아래와 같다.

| fixture | SHA-256 |
|---|---|
| `requirements/order.md` | `8945925164F756DAD552B0744435158196B7AC9D755832EE220749C3CF9FD902` |
| `context/주문/README.md` | `3B56FCA20D2AE3F168E98E988FE6D82E2E0D55B1278CE1574333CCF0C2EDE4C8` |
| `.claude/config.json` | `1E5C3A9118ACCCD8044188174D68D610642B2096CF6CA8EBFC2460315E0C2C85` |

후속 실행에서는 인증된 홈에서 후보 1.33.0 경로를 명시하고, gx-tdd만 중첩 cwd로 시작한다. gx-context Q2/S46은 소비 프로젝트 루트에서 시작해 UI Other 답변과 `codex_hook.py capture`의 동일 id를 함께 수집한다.
