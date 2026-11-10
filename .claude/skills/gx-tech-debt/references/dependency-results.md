# 의존성 조회 결과 계약

상대경로는 이 파일 위치 기준이다. 실제 명령을 실행한 경우 stdout 원문·exit code·시간초과·실행 가능 여부를 별도로 보존한다. 표준입력은 셸 문자열에 붙이지 않고 데이터로 전달한다. 결과 분류 helper는 [gx-dependency-result.py](../../../../scripts/gx-dependency-result.py)이며 설치 플러그인 루트에서 찾는다. PowerShell은 공통 UTF-8 입출력 설정을 사용하고 `PYTHONDONTWRITEBYTECODE=1`로 둔다. Bash는 `python3`, Windows는 `python`을 쓴다.

```text
python "<설치 helper 절대경로>" classify --tool npm-audit --exit-code 1
```

위 명령의 stdin에 **감사 명령 stdout 원문**을 전달한다. 시간초과면 `--timed-out`을 추가한다. 분류 helper의 exit 0은 분류 성공일 뿐, 감사 성공이 아니다. 반환 JSON의 `status`를 확인한다.

| status | 의미 | 발견 수 처리 |
|---|---|---|
| complete | 알려진 정상 스키마·일관된 개수·허용 종료코드 | 정상 빈 결과만 0건. 확인한 발견은 유지 |
| error | JSON error 객체, 빈/잘린 출력, 스키마 불일치, 비정상 종료 | 전체 수 미확인 |
| partial | 일부 조회 오류 또는 감사에서 제외된 의존성 | 확인한 항목만 제시, 전체 수 미확인 |
| timeout | 시간초과, 완결성 미확인 | 전체 수 미확인 |
| unsupported | 검증하지 않는 도구·버전·생태계 | 수동 확인 필요 |

CLI 미설치·실행 불가는 `error`, 미지원 생태계/스키마 버전은 `unsupported`, 명시적 정적 분석 범위로 실행하지 않은 조회는 `not_run`으로 대화에 유지한다. stdout가 비어있다는 이유만으로 빈 정상 결과를 만들지 않는다. `errors`·`partial` 표식이나 pip-audit의 `skip_reason`이 있으면 부분 결과다. stderr에 조회 실패·일부 실패가 보고된 경우에도 helper가 보지 못하는 완결성 한계로 반영하여 `partial`/`error`로 낮춘다.

지원하는 제한된 JSON 계약은 다음과 같다. 외부 CLI 버전별 실출력 검증을 했다고 주장하지 않는다. 다른 버전의 출력은 원문을 근거로 수동 대조하고 검증하지 못하면 미지원/미확인으로 남긴다.

- `npm-outdated`: 패키지명 → wanted/latest 문자열 객체. 정상 빈 객체 `{}`와 exit 0, 또는 발견이 있는 정상 객체와 exit 1. 정상 패키지 맵을 먼저 확인하므로 partial/error/errors라는 패키지명도 허용한다. `partial: true`나 구체적인 오류 내용이 담긴 errors는 상태 객체로 구분하며 알 수 없는 객체 형상은 실패로 둔다.
- `npm-audit`: `auditReportVersion: 2`, vulnerabilities 객체, metadata.vulnerabilities.total의 정수 개수 일치. 각 항목은 name/severity와 via/nodes 배열. 다른 보고 버전은 미지원.
- `pip-outdated`: name/version/latest_version 문자열을 가진 배열과 exit 0. 정상 빈 배열 `[]` 지원.
- `pip-audit`: dependencies 배열의 name/version/vulns 배열, 각 취약점 id. skip_reason이 있으면 부분 결과. 발견으로 인한 exit 1은 정상 스키마가 확인된 경우에만 인정.
- `cargo-audit`: vulnerabilities의 found(bool)/count(int)/list 배열이 서로 일치하며 각 항목의 advisory.id와 package.name/version이 존재. 발견으로 인한 exit 1은 정상 스키마일 때 인정.

## 점수 합성

```text
python "<설치 helper 절대경로>" health
```

stdin 예시는 `{"severities":["HIGH"],"statuses":{"code":"complete","deps:npm-outdated":"complete","deps:npm-audit":"error"}}`다. 요청한 모든 유형과 그 안의 필요한 조회를 statuses에 넣는다. 미시도·미지원 유형을 누락하지 않는다. 하나라도 complete가 아니면 score/grade는 null이며 산정을 보류한다. 모든 요청 범위가 complete인 경우에만 기존 감산식을 적용한다. `--type code`처럼 일부 유형만 요청한 경우 해당 유형의 점수라고 명시한다.
