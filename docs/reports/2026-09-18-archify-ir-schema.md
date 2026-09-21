# Archify IR 스키마 실측 보고

측정일: 2026-09-18
측정 방법: `npx -y skills add tt-a1i/archify -g` 설치 후 디스크의 스키마·예제·CLI를 직접 확인
archify 버전: `2.17.0-dev.1` (`package.json`), MIT
설치 경로: `~/.agents/skills/archify` (`~/.claude/skills/archify`는 이 디렉터리로의 심링크)

이 문서는 계획서 Task 5 Step 1("Archify를 설치하고 실제 IR 스키마를 실측한다")의 산출물이다. 오케스트레이터가 직접 수행했으므로 T5 구현자는 이 문서를 근거로 변환기를 작성한다.

## 1. 설치와 실행

`npx -y skills add tt-a1i/archify -g`는 exit 0으로 끝나지만 출력에 실패 2건이 섞인다.

```
✓ ~\.agents\skills\archify
✓ ~\.agents\skills\archify-review
✗ archify → PromptScript: PromptScript does not support global skill installation
✗ archify-review → PromptScript: ...
```

이 두 실패는 **무해하다** — PromptScript라는 다른 하네스용 설치만 건너뛴 것이고 우리가 쓰는 스킬·렌더러는 정상 설치된다. 따라서 탐지 로직은 **exit code나 이 경고로 성공을 판정하지 말고** 실제 산출물 존재와 `doctor` 결과로 판정해야 한다.

**PATH에 `archify` 바이너리는 없다.** `package.json`이 `"private": true`이고 npm 배포본이 아니다. 호출은 항상 경로 기반이다.

```bash
node ~/.agents/skills/archify/bin/archify.mjs doctor
```

`doctor`는 15개 항목 전부 `[ok]`와 `Archify is ready`를 반환했다 (Node v22.14.0). `dependencies`가 비어 있고 `devDependencies`(ajv·parse5·saxes·simple-icons)만 있으므로 **렌더링에 `npm install`이 불필요하다** — 스키마 검증기는 생성된 standalone validator로 번들되어 있다.

## 2. CLI 계약 (실측)

```
archify render   <type> <input.json> [output.html] [--quality standard|showcase] [--repo-root path]
archify deliver  <type> <input.json> [output.html] [--json] [--open] [--quality ...] [--repo-root path]
archify validate <type> <input.json> [--json] [--layout-json] [--quality ...] [--repo-root path]
archify compare  architecture <base.json> <head.json> [output.html] [--receipt path] [--json] ...
archify inspect  <type> <input.json>
archify check    <output.html>
archify visual-check <output.html> [--json]
archify examples | doctor | demo [output-dir] | guide | brands | migrate
```

`type` ∈ `architecture, workflow, sequence, dataflow, lifecycle`

**계획서 Task 4의 argv 가정은 옳다** — `validate <type> <input>` 과 `deliver <type> <input> <output.html>` 형태가 맞고, `--output` 플래그는 존재하지 않는다. `--repo-root`는 architecture에만 적용된다.

추가로 쓸 수 있는 검증 표면: `check <output.html>`과 `visual-check <output.html> --json`.

## 3. architecture IR 구조 (실측)

최상위는 `additionalProperties: false`이고 필수는 `schema_version`, `diagram_type`, `meta`, `components`다.

```json
{
  "schema_version": 1,
  "diagram_type": "architecture",
  "meta": { "title": "...", "output": "...", "quality_profile": "showcase", "views": [...] },
  "layout": { "mode": "grid", "cols": 5, "gapX": 80, "gapY": 40, "cellW": 130, "cellH": 60 },
  "components": [ { "id": "...", "type": "backend", "label": "...", "row": 0, "col": 1 } ],
  "boundaries": [ { "kind": "region", "label": "...", "wraps": ["id", ...] } ],
  "connections": [ { "from": "a", "to": "b", "label": "...", "variant": "emphasis" } ],
  "cards": [ { "dot": "cyan", "title": "...", "items": ["..."] } ]
}
```

**우리 GX IR과 이름이 전혀 다르다** — `nodes`가 아니라 `components`, `edges`가 아니라 `connections`. 최상위가 `additionalProperties: false`이므로 GX IR을 그대로 넘기면 반드시 검증 실패한다.

### 3.1 components

- 필수: `id`, `type`, `label`
- 선택: `sublabel`, `tag`, `brand`, `sources`, `row`, `col`, `pos`, `size`
- `type` enum: `frontend | backend | database | cloud | security | messagebus | external`

### 3.2 배치 — pos/size는 선택, row/col 권장

`pos`/`size`는 **필수가 아니다.** 대신 top-level `layout: {mode: "grid", origin, cols(1-12), gapX, gapY, cellW(≥40), cellH(≥24)}`와 component별 `row`/`col`(정수 ≥0)로 그리드 배치가 가능하다.

우리 IR은 고정 5계층 사슬이므로 픽셀 계산 없이 그대로 매핑된다.

| GX kind | archify type | col |
|---|---|---|
| `screen` | `frontend` | 0 |
| `api` | `backend` | 1 |
| `service` | `backend` | 2 |
| `repository` | `backend` | 3 |
| `table` | `database` | 4 |

`row`는 사슬 순서로 부여한다. `cols`는 12가 상한이므로 5계층은 여유가 있다.

### 3.3 근거(evidence)는 버리지 않고 매핑한다

`component.sources`가 존재한다.

```json
"sources": [{ "path": "...", "line": 1, "end_line": 10, "label": "..." }]
```

- 배열, `minItems: 1`, `maxItems: 3`
- 항목 필수: `path` (≤240자). 선택: `line`, `end_line`, `label` (≤48자)

**계획서 T5의 "evidence는 Archify 문서에 싣지 않는다"는 지시를 정정한다.** archify가 소스 근거를 1급으로 지원하므로 GX IR의 `evidence[{kind:"code", file, line}]`를 `sources[{path, line}]`으로 **매핑해야 한다.** 다만 상한이 3개이므로 초과분은 잘라내고, `kind: "inferred"` 근거는 `path`가 없으므로 넘기지 않는다.

`meta.repository`를 쓰면 소스 링크가 웹으로 연결되지만 `revision`이 40자 hex SHA를 요구한다. 1차 범위에서는 `link_mode: "local-only"`로 두거나 `repository` 자체를 생략한다.

### 3.4 connections

- 필수: `from`, `to`
- 선택: `id`, `label`, `variant`, `fromSide`, `toSide`, `route`, `via`, `labelAt`, `labelDx`, `labelDy`, `labelSegment`, `width`

GX `relation` → `label`로 옮기고, `variant`는 주 경로 강조에만 제한적으로 쓴다. 라우팅 힌트(`via` 등)는 1차 범위에서 쓰지 않는다 — 좌표를 손으로 계산해야 하고 그리드 배치의 이점을 잃는다.

## 4. 한국어 제약 — 확인된 한계

```json
"locale": { "enum": ["en", "zh-CN"] }
```

**`meta.locale`은 한국어를 지원하지 않는다.** `ko`/`ko-KR`이 enum에 없고 최상위가 `additionalProperties: false`이므로 우회할 수 없다.

영향 범위:

- **노드 라벨·부라벨·카드 텍스트는 자유 문자열이므로 한국어가 그대로 들어간다.** 내용은 한국어로 표시된다.
- **archify가 생성하는 UI 크롬**(범례 제목, 자동 생성 캡션 등)은 `en` 또는 `zh-CN`만 가능하다. `en`을 쓰면 한국어 내용이 영어 크롬 안에 담긴다.

이 플러그인이 한국어 우선이고 대상 독자가 GX 사업본부인 점을 고려하면 사용자 판단이 필요한 지점이다. 폰트 렌더링 가능 여부는 실제 HTML을 생성해 눈으로 확인해야 하며, 이 문서는 그것까지 검증하지 않았다.

## 5. T5 작업에 미치는 결론

1. 변환기는 `{schema_version, diagram_type, meta, components, connections}` 형태를 생성한다. `layout.mode: "grid"` + `row`/`col`을 쓰고 `pos`/`size`는 쓰지 않는다.
2. `kind` → `type` 매핑과 `col` 배정은 §3.2 표를 따른다.
3. `evidence` → `sources` 매핑을 **구현한다** (계획서의 "싣지 않는다"는 정정됨). 최대 3개.
4. GX IR의 나머지 필드(`status`, `technical_label`, `view`, `locale: ko-KR`)는 archify 문서에 넘기지 않는다 — `additionalProperties: false`가 거부한다. `technical_label`은 `sublabel`로, `status`는 `tag`로 옮길 수 있는지 검토한다.
5. `meta.locale`은 `en`으로 둔다. 한국어 크롬은 불가하다.
6. 검증은 `validate architecture <file> --json`으로 하고, 결과 HTML은 `check <output.html>`로 한 번 더 확인할 수 있다.
