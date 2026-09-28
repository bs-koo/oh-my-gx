# trace 요청 예시

## 사용자 요청

> 시각화 포함해서 AN-02 요구사항이 기능과 테이블, 단위테스트까지 연결됐는지 보여줘. 현재 작업 산출물을 쓰고 가능한 로컬 백엔드로 만들어줘.

정규화된 호출:

```text
gx-visualize trace --backend auto --project-root .
```

## 입력 수집

예를 들어 현재 작업 디렉터리에 `prd.md`, `design.md`, `DE-13.xlsx`는 있지만 DE-08 산출물이 없다면 수집 결과는 사실 그대로 유지한다.

```json
{
  "files": [
    ".dev/feat-energy/design.md",
    ".dev/feat-energy/prd.md",
    ".dev/feat-energy/DE-13.xlsx"
  ],
  "missing_inputs": ["DE-08"]
}
```

[GX 산출물 매핑](../references/gx-mapping.md)에 따라 확인 가능한 AN-02 → AN-03 → DE-13 관계만 IR에 넣는다. DE-08 노드나 관계를 만들어 빈자리를 감추지 않는다.

`DE-13.xlsx` evidence는 프로젝트 루트 상대 `file`과 셀 locator로 기록하고 바이너리를 텍스트로 읽지 않는다.

```json
{"file":".dev/feat-energy/DE-13.xlsx","kind":"test","locator":{"type":"xlsx","sheet":"단위테스트","cell":"B12"}}
```

## 완료 보고 예

```json
{
  "view": "trace",
  "backend": "static",
  "html_path": ".dev/feat-energy/visual/trace.html",
  "ir_path": ".dev/feat-energy/visual/trace.json",
  "receipt_path": ".dev/feat-energy/visual/trace.receipt.json",
  "validation_status": "fallback",
  "missing_inputs": ["DE-08"]
}
```

`backend`는 요청값 `auto`가 아니라 실제 HTML을 만든 백엔드다. 폴백 이유와 앞선 시도는 receipt에 남긴다.

## 시각화 전용 실패 예

IR 검증 또는 모든 렌더가 실패하면 성공 경로를 반환하지 않는다.

```text
시각화 실패: DE-08 입력이 없고 확인 가능한 requirement → data 관계가 없습니다.
receipt: .dev/feat-energy/visual/trace.receipt.json
재실행 명령: gx-visualize trace --input .dev/feat-energy --backend static --project-root .
```

직접 호출은 실패로 끝내지만, 상위 개발·리뷰 작업에서 선택적으로 요청된 시각화라면 그 작업의 게이트 판정은 변경하지 않는다.
