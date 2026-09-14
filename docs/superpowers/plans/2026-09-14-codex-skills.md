# Codex 역할·설치 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 소비 프로젝트가 저장소 루트 규칙에 의존하지 않고 17개 GX 스킬의 역할·설정·도구 매핑을 사용할 수 있게 한다.

**Architecture:** 역할과 config는 기존 원본에서 스킬 내부 리소스로 생성한다. 공통 Codex 실행 지침을 모든 GX 스킬이 읽으며, setup은 생성 성공과 실제 권한 준비를 구분한다.

**Tech Stack:** Python 3.10+ 표준 라이브러리, Markdown, 기존 Bash 린트.

**Spec:** `docs/superpowers/specs/2026-09-14-codex-native-compat-design.md` B1~B3.

## Global Constraints

- 지원 검증 기준은 Codex CLI 0.154.0이다. 더 낮은 버전은 호환을 보증하지 않는다.
- Python 3.10 이상 표준 라이브러리와 기존 Bash/Git/Node를 사용한다. 새 런타임 패키지는 추가하지 않는다.
- `.claude/skills/`의 17개 GX 스킬과 `agents/*.md`를 편집 원본으로 유지한다. Codex 역할 복사본과 config 템플릿은 생성 산출물이다.
- `.claude/config.json`은 하네스 공통 프로젝트 데이터로 유지한다. 이름 변경이나 설정 마이그레이션은 하지 않는다.
- 소비 프로젝트의 AGENTS.md/CLAUDE.md와 명시적 사용자 지시가 플러그인 일반 지침보다 우선한다.
- 구현 브랜치에서 작업하고 기존 미커밋 변경을 임의로 스테이징·되돌리기·삭제하지 않는다. 커밋은 gx-commit 절차를 따른다.
- 문서와 커밋 메시지는 한국어로 작성한다. 이모지는 새로 추가하지 않는다.

## Task 1: 역할·config 리소스 생성과 바이트 드리프트 검사

**Files:**
- Create: `scripts/sync-codex-resources.py`, `tests/test_codex_resources.py`
- Create generated: `.claude/skills/gx-dev/references/codex-roles/*.md`, `index.json`
- Create generated: `.claude/skills/gx-setup/references/config.template.json`
- Modify: `.github/workflows/lint.yml` 생성 결과 검사

**Interfaces:**
- Consumes: `agents/*.md`의 YAML frontmatter(`name`, `model`)와 본문, `.claude/config.json`, A Task 1의 `tests/codex_test_support.py` 로더.
- Produces: `expected_files(root: Path) -> dict[Path, bytes]`; `--check` exit 0 동일/1 드리프트/2 잘못된 입력. `index.json`은 `{role: {tier: high|mid, file: role.md}}`.

- [x] **Step 1: 생성될 리소스의 실제 내용을 검사하는 테스트를 작성한다.**

```python
import json
from pathlib import Path
import tempfile
import unittest
from codex_test_support import load
sync = load('gx_sync', 'scripts/sync-codex-resources.py')

class ResourceTests(unittest.TestCase):
    def test_role_body_and_template_survive_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'agents').mkdir()
            (root / '.claude').mkdir()
            (root / 'agents/reviewer.md').write_text(
                '---\nname: reviewer\nmodel: opus\n---\n'
                '# 역할\n코드를 수정하지 않는다.\n', encoding='utf-8')
            config = b'{"vcs":"git"}\n'
            (root / '.claude/config.json').write_bytes(config)
            files = sync.expected_files(root)
            base = root / '.claude/skills/gx-dev/references/codex-roles'
            self.assertEqual(files[base / 'reviewer.md'].decode(),
                             '# 역할\n코드를 수정하지 않는다.\n')
            self.assertEqual(json.loads(files[base / 'index.json'])['reviewer']['tier'], 'high')
            template = root / '.claude/skills/gx-setup/references/config.template.json'
            self.assertEqual(files[template], config)
```

- [x] **Step 2: RED를 확인한다.** `python -m unittest discover -s tests -p 'test_codex_resources.py' -v`; 생성기 부재로 실패.
- [x] **Step 3: 생성기의 순수 함수를 구현한다.**

```python
import json
from pathlib import Path
import re

def expected_files(root):
    target = root / '.claude/skills/gx-dev/references/codex-roles'
    files, index = {}, {}
    for source in sorted((root / 'agents').glob('*.md')):
        text = source.read_text(encoding='utf-8')
        match = re.fullmatch(r'---\n(.*?)\n---\n(.*)', text, flags=re.S)
        if not match:
            raise ValueError(f'역할 frontmatter 오류: {source}')
        header, body = match.groups()
        model = re.search(r'^model:\s*(opus|sonnet)\s*$', header, flags=re.M)
        if not model:
            raise ValueError(f'역할 티어를 결정할 수 없습니다: {source}')
        files[target / source.name] = body.encode('utf-8')
        index[source.stem] = {'tier': 'high' if model[1] == 'opus' else 'mid',
                              'file': source.name}
    if not index:
        raise ValueError('역할 원본이 없습니다.')
    files[target / 'index.json'] = (json.dumps(index, ensure_ascii=False,
        indent=2, sort_keys=True) + '\n').encode('utf-8')
    config = (root / '.claude/config.json').read_bytes()
    json.loads(config)
    files[root / '.claude/skills/gx-setup/references/config.template.json'] = config
    return files
```

CLI는 `argparse --check`만 받는다. root는 `Path(__file__).resolve().parents[1]`다. check 모드는 모든 기대 경로의 바이트 일치와 `codex-roles`의 추가 `.md` 부재를 확인한다. 생성 모드는 대상 부모 생성 후 `write_bytes`한다. 잔여 역할 파일은 자동 삭제하지 않고 명시적 오류로 보고한다. 사용자가 역할을 제거한 변경에서는 해당 생성 파일 삭제도 함께 검토한다.

- [x] **Step 4: 실제 생성·export를 검사한다.**

```bash
python scripts/sync-codex-resources.py
python scripts/sync-codex-resources.py --check
python -m unittest discover -s tests -p 'test_codex_resources.py' -v
```

테스트에 sonnet→mid, CRLF 원본, 지원하지 않는 model 오류, 역할 파일 변경 후 --check 실패, 템플릿 변경 후 --check 실패를 추가한다. 임시 폴더에 GX 스킬 17개만 복사하고 원본 agents/config 없이 생성 리소스를 읽어 같은 바이트임을 검사한다. 원본에 없는 개발용 junction은 복사하지 않는다.

CI에 `python3 scripts/sync-codex-resources.py --check`를 넣는다. 릴리스 생성물은 커밋해서 Git source 설치에도 포함시킨다.
- [ ] **Step 5: gx-commit.** `feat: Codex 스킬에 역할과 설정 리소스를 함께 배포한다`.

## Task 2: 도구·역할·모델 매핑을 한 곳에서 실행한다

**Files:**
- Create: `.claude/skills/gx-dev/references/codex-runtime.md`
- Modify: `.claude/skills/gx-{commit,context,cross-review,dev,green,humanizer,lens,pull-request,ralph,ralph-iterate,red,refactor,research,setup,tdd,tech-debt,verify}/SKILL.md`
- Modify: `.claude/skills/gx-tdd/references/harness-adaptation.md`
- Modify: `.claude/skills/gx-dev/phases/phase-design.md`
- Modify: `.claude/skills/gx-tdd/phases/phase-implement.md`, `phase-review.md`
- Modify: `scripts/lint-consistency.sh` [24/36], [30/36]
- Modify: `tests/codex-smoke.md` 역할·질문 시나리오

**Interfaces:**
- Consumes: Task 1의 `codex-roles/index.json`과 역할 본문, 계획 A의 decision capture schema.
- Produces: 역할 프롬프트 조립 규칙, 현재 API 매핑, child 결과의 기존 JSON/YAML 계약 보존. API 이름을 바꾸는 실행 라이브러리는 새로 만들지 않는다.

- [x] **Step 1: 공통 지침 본문을 작성한다.** 다음 규약을 그대로 포함한다.

```markdown
# Codex 실행 규약

이 파일과 아래 역할 경로는 현재 파일의 위치를 기준으로 해석한다.
실행 전 실제 도구 스키마와 모델 allowlist를 확인한다.

1. 역할 위임: codex-roles/index.json과 해당 .md를 읽는다.
   역할 본문 + 소비 프로젝트 지침 + 현재 태스크의 전체 prompt를 자식에게 전달한다.
   구현 파일을 볼 수 없는 RED 역할에는 구현 코드나 부모 대화 전체를 넘기지 않는다.
2. 현재 API는 spawn_agent(task_name, message, fork_turns, model, reasoning_effort)다.
   격리는 fork_turns: none을 쓴다. agent_type은 실제 스키마에 있을 때만 사용한다.
   전체 이력 fork와 모델 override를 함께 요구하지 않는다.
3. 역할 high/mid는 index에서 읽는다. 현재 후보는 high= gpt-6-astra/high,
   mid= gpt-5.6-sol/medium이다. allowlist에 없는 모델은 호출하지 않는다.
   후보 부재 시 같은 허용 모델의 high/medium으로 구분한다.
   태스크가 명시한 티어 예외와 eco architect 유지 규칙을 우선한다.
4. 자식 결과는 wait_agent로 받고 수정 라운드는 followup_task로 재개한다.
   도구 수 제한이나 agent_type 부재를 역할 전달 생략의 이유로 삼지 않는다.
5. 질문은 제공된 async 도구 또는 해당 모드에서 허용된 동기 도구를 사용한다.
   동기 질문에는 id를 넣고 UI가 제공하는 Other를 직접 옵션으로 추가하지 않는다.
   응답 전에는 독립 작업만 수행한다. 자연어 fallback도 실제 답변을 기다린다.
   확정된 자연어/async 결정은 계획 A의 capture payload로 기록한다.
6. Skill 호출은 설치 목록의 해당 SKILL.md를 읽고 절차를 실행한다.
   verify/commit/pull-request의 검사와 중단 조건을 생략하지 않는다.
7. Bash 코드는 Git Bash 또는 Bash를 명시해서 실행한다.
   PowerShell 명령은 PowerShell로 실행하고 작업 위치는 workdir로 지정한다.
   timeout 인자를 추측하지 않는다. session_id가 나오면 write_stdin으로 완료를 기다린다.
8. allowed-tools는 Codex의 권한 설정이 아니다. 역할 지침과 실제 도구 권한을 구분한다.
```

역할 전달 규약을 같은 문서에 넣는다. 오케스트레이터는 읽은 역할 본문·프로젝트 지침·태스크 전문을 합쳐 실제 `collaboration.spawn_agent` 도구의 message에 전달한다. 아래 함수는 인자 조립 예시이며 셸이나 functions.exec에서 collaboration을 호출하는 라이브러리가 아니다. 모델과 effort는 위 allowlist 검사에서 선택한 값을 받는다.

```javascript
function reviewArguments({roleBody, projectInstructions, taskPrompt, model, effort}) {
  return {
    task_name: 'review_task_1',
    message: [roleBody, projectInstructions, taskPrompt].join('\n\n'),
    fork_turns: 'none',
    model,
    reasoning_effort: effort
  };
}
```

- [x] **Step 2: 모든 진입점이 공통 파일을 읽도록 연결한다.** GX SKILL.md의 Codex 노트에 `../gx-dev/references/codex-runtime.md`를 넣는다. gx-dev 자신은 `references/codex-runtime.md`, gx-tdd의 adaptation 파일은 `../../gx-dev/references/codex-runtime.md`를 사용한다. 문서에서 Read 상대경로는 셸 cwd가 아니라 해당 문서의 위치라는 설명을 유지한다.

역할을 참조하는 phase의 `agents/reviewer.md` 같은 저장소 기준 설명은 ‘Codex에서는 공통 매핑이 주입한 reviewer 역할 본문’으로 명확히 한다. Claude에서는 기존 Task 타입을 유지한다. humanizer의 ‘직접 수행’을 기본 fallback으로 설명하던 문장은 다음으로 교체한다.

```markdown
Codex strict 모드는 codex-roles/humanizer-fidelity.md와
codex-roles/humanizer-naturalness.md 본문을 각각 읽고
격리된 검증 자식에게 전달한다. run-id만으로 역할을 대신하지 않는다.
독립 자식을 실행할 수 없으면 독립 검증 미수행을 표시하고 정상 strict
완료로 보고하지 않는다. 직접 감사 결과는 별도 제한 결과로만 제공한다.
```

- [ ] **Step 3: 참조 정합성과 실제 전달을 검증한다.** lint는 17개 진입점의 참조 경로가 존재하는지 검사한다. 행동 합격은 다음 실제 smoke로 판정한다.

| ID | 작업 | 필수 증거 |
|---|---|---|
| R1 | reviewer child에 고의적 AC 위반 fixture 전달 | spec 판정이 quality보다 앞섬, 코드 불변 |
| R2 | red-writer에 테스트 추가 요청 | src 미열람, prod 해시 불변, 실제 RED |
| R3 | humanizer strict 작은 한국어 문단 | 두 child의 서로 다른 id, 요구 JSON 파일과 필드 |
| Q1 | 기본 모드에서 선택 질문 | 실제 답변 전 의존 작업 없음, 질문/답변 기록 보존 |

시스템이 상세 tool trace를 제공하지 않으면 R2의 미열람은 미확인으로 남긴다. 파일 불변만으로 읽기 격리를 입증하지 않는다. 부모는 하네스가 제공한 이벤트에서 모델/effort를 확인할 수 있을 때만 티어 실측으로 기록한다.
- [x] **Step 4: `bash scripts/lint-consistency.sh`와 resource --check를 통과시킨다.** R1~Q1은 인증된 실제 세션에서 실행하고 미실행을 명시한다.
- [ ] **Step 5: gx-commit.** `feat: Codex 역할과 도구 실행 규약을 공통 리소스로 연결한다`.

## Task 3: setup 성공 판정·설치 안내·깨끗한 배포 검증

**Files:**
- Modify: `.claude/skills/gx-setup/SKILL.md` config 생성/권한 단계
- Modify: `.claude/skills/gx-verify/SKILL.md` tdd 참조 경로
- Modify: `.claude/rules/harness-codex.md`, `README.md`
- Modify: `docs/specs/2026-08-28-codex-harness-compat-design.md` 최신 설계 링크
- Modify: `tests/codex-smoke.md` 설치·setup 섹션
- Modify: `.github/workflows/lint.yml` Windows/Linux 계약 검사

**Interfaces:**
- Consumes: `gx-setup/references/config.template.json`, A의 hook trust/guard/capture.
- Produces: config 생성 성공 확인, 지원 버전·경로·권한 단계 안내, S1~S3 smoke.

- [x] **Step 1: config 생성 단계를 다음 계약으로 수정한다.**

```markdown
기존 .claude/config.json이 있으면 읽고 파싱한다. 자동 덮어쓰지 않는다.
없으면 이 SKILL.md 기준 references/config.template.json을 읽고 JSON을 파싱한다.
로드나 파싱이 실패하면 setup을 중단하고 실패 파일 경로를 보고한다.
정상 템플릿을 소비 프로젝트 .claude/config.json에 기록한 뒤 다시 읽어 파싱한다.
이 단계가 성공했을 때만 'config.json 생성 완료'를 출력한다.
```

프로젝트 타입 등록은 기존 스키마와 흐름을 유지한다. Codex 권한 단계는 `.claude/settings.local.json` 편집을 수행하지 않고 실제 실행 가능한 Python/Bash/Git와 사용자 hook trust 상태를 확인한다. 권한이 필요한 명령은 Codex의 현재 정책에 따라 처리하며 ‘권한 설정 완료’를 허위로 출력하지 않는다.

- [x] **Step 2: 현재 CLI 안내로 교체한다.** Windows 예시는 다음과 같다. 이것은 문서 내용이며 이 태스크에서 사용자 전역 설치를 자동 실행하지 않는다.

```powershell
codex.cmd plugin marketplace add bs-koo/oh-my-gx
codex.cmd plugin add oh-my-gx@oh-my-gx
codex.cmd plugin list --json
```

Codex 입력창에서 `/skills`, `/hooks`를 사용한다고 구분한다. `plugin_hooks` 활성화를 해결책으로 권하지 않는다. `.codex-plugin/plugin.json`은 지원되는 현재 형식으로 유지한다. `source:url,url:./`는 Git source임을 설명하고 개발용 임시 marketplace에는 `source:local,path:./`를 사용한다.

`gx-verify`의 tdd 규약 참조는 현재 SKILL.md 기준 `../gx-tdd/references/tdd-iron-law.md`로 수정한다. 구 설계 상단에 ‘0.130 당시 기록, 현재 실행 기준은 2026-09-14 설계’ 링크를 넣어 역사와 현행을 구분한다.

- [x] **Step 3: CI에 오프라인 계약 검사를 추가한다.** 별도 matrix job을 `ubuntu-latest`, `windows-latest`로 구성하고 checkout→setup-python 3.10→setup-node 22→아래 명령을 수행한다. 실제 Codex 인증이 필요한 smoke는 PR CI에서 실행하지 않는다.

```text
python scripts/sync-codex-resources.py --check
python -m unittest discover -s tests -p "test_codex_*.py" -v
```

- [x] **Step 4: 실제 소비 프로젝트 setup 시나리오를 기록한다.**

| ID | 환경 | 기대 결과 |
|---|---|---|
| S1 | 새로운 임시 Git 프로젝트, 깨끗한 설치 cache | 17 GX 스킬 발견, config 생성·파싱 성공 |
| S2 | config.template.json을 제거한 임시 배포 복사본 | 생성 완료 미표시, 후속 Edit 없음 |
| S3 | 기존 프로젝트 config와 Claude permissions가 있음 | 사용자 값 보존, Codex setup이 Claude permissions 미변경 |

실제 install cache 경로와 사용자 홈을 기록한다. 개발 폴더의 skill-creator junction이 릴리스 스킬로 섞이지 않음을 검사한다. 본 저장소의 AGENTS.md를 임시 소비 프로젝트로 복사해서 결과를 부풀리지 않는다.
- [ ] **Step 5: gx-commit.** `fix: Codex 온보딩과 설치 안내를 실제 성공 조건에 맞춘다`.

## 2026-09-14 실행 판정

구현·회귀·실제 설치 결과는 [실측 보고서](../../reports/2026-09-14-codex-validation.md)를 따른다. 기존 WIP 보존을 위해 태스크별 커밋 대신 파일 스냅샷과 독립 리뷰로 추적했으며 gx-commit 단계는 수행하지 않았다. 코드 예시는 최초 계획이며 최종 인터페이스는 구현 파일을 따른다.

B2 Step 3은 R2의 자식 src 미열람 trace가 없어 부분 확인으로 남긴다. R1/R3/Q1 실제 실행은 기록했다. 실제 setup 실패를 바탕으로 `scripts/codex-project-config.py`와 설치 루트·helper 경로 검증을 추가했다.
