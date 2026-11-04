# 2.0.0 로컬 검증 기록

기준 `43acaee`, 브랜치 `codex/gx-work-unified`. 원래 checkout의 미커밋 시각화 작업과 분리한 worktree에서 확인했다. 이 문서는 커밋 직전 로컬 결과이며 원격 CI 결과는 PR의 checks를 따른다.

## 실행 범위와 결과

| 검사 | 결과와 재실행 범위 |
|---|---|
| Codex 오프라인 계약 248개 | 통합 집합을 1회 실행했다(460.297초). 처음에는 3개 메서드의 4개 실패 기록이 있었다. phase 선택을 배열/반복 계약으로 검사하도록 바꾸고, verify 증거 재사용과 Q2 종료점 계약에 맞춰 기대값을 수정한 뒤 실패 메서드가 모두 통과했다. 단일 248개 실행의 0 fail로 표현하지 않는다. |
| 후속 TDD 실행 연결 | focused 절 수정 중 IMPLEMENT 절차/격리 prompt 손실을 추출 검사로 발견해 복원했다. pipeline 파일 26개가 모두 통과했다(20.451초). 이어 하위 프로젝트의 command/cwd 보존을 prompt·report·직접 재실행·Ralph에 연결하고 해당 계약 1개와 Q2 1개가 다시 통과했다. |
| gx-work·배포 검사 28개 | 27개 통과 후 새 구현에 읽기 전용 종료점을 지정하는 오류 1개를 RED→GREEN으로 추가 확인했다. 실제 파일 바이트·브랜치·state 보존, plan 충돌/의존성/범위, 승인 출처·run-id·종료점과 설치 참조를 검사한다. migration 4개는 후속 단계에서도 통과했다. |
| gx-context·작업계획 21개 | 21개 통과. blocking 미정/충돌 보존, 근거 있는 응답, 인계, 요구사항 배정·누락·중복·폐기·완료 후보·의존성에 따른 ready/blocked를 확인했다. |
| 테스트 계획·증거·focused 31개 | 처음 25개 중 24개 통과. Vitest 양성 fixture가 runner 설정 변경까지 포함해 전체로 확장되는 것이 원인이어서, 설정을 기준 커밋에 포함한 뒤 실패 1개만 재실행해 통과했다(11.128초). 이어 현재 태스크 focused CLI 6개가 RED→GREEN으로 통과했다(19.623초). 코드·config·명령·cwd·범위·run-id·로그 변조, 실패/0건, 실제 Git diff 누락, TS config·Kotlin·독립 프로젝트와 미지원 runner를 확인한다. |
| Ralph | Bash 러너 48 pass/0 fail. Python 22개 중 2개 Windows 경합 timeout은 fixture 대기만 Windows 90초로 조정하고 해당 2개를 재실행해 통과했다(25.820초). 제품 timeout/반복 상한은 유지했다. |
| 보호·공유 | hook 회귀 통과, `.dev` 공유/제외 검사 14개 통과. 기존 보호 브랜치·verify 지문·강제 push·테스트 불변 조건을 유지했다. |
| 배포·정합성 | `sync-codex-resources.py --check`, 정합성 린트 36항목, behavior mock 30 pass/0 fail, `git diff --check` 통과. 실제 설치를 복사한 참조 검사와 현재 18개 SKILL의 UTF8 LF 기준 20KB 미만 예산을 확인했다. |

원시 로컬 출력은 같은 작업의 `logs/`에 보관하며 커밋하지 않는다. 새 검사 총수 80개와 기존 Codex 248개는 개별·통합·실패 재검사 결과의 합성 근거다. 작업 중 매 수정마다 저장소 전체 검사를 반복하지 않았다. 공통 실행 규약·배포·hook을 바꾼 통합 시점의 넓은 검사와 이후 변경한 계약만의 재검사를 구분한다.

첫 커밋 대상 소스의 canonical `codex-fingerprint.py` 결과는 `43acaee:5462af1fe1a2`다. 로컬 Windows의 최초 객체 저장에서는 30초 timeout이 발생했다. 진단 trace는 작은 Git 객체를 쓰는 디스크 flush에 지연이 집중됨을 보였고, 실제 stage 후 동일 helper가 정상 완료했다. 이 환경 진단을 위해 제품 helper의 timeout이나 알고리즘을 바꾸지 않았다. `.dev` 산출물은 정해진 지문 계약대로 제외된다.

## 리뷰 반영

독립 리뷰가 지적한 setup 단계의 조기 commit/push, TS config 영향 누락, 승인된 design 재생성, 다중 프로젝트 증거 로그 덮어쓰기와 evidence 디렉터리 누락을 수정했다. 마지막 focused 연결 리뷰에서 발견한 하위 프로젝트 cwd 누락도 수정했다. 복원된 내부 RGR 절차·격리 prompt·fixture 치환의 순서를 다시 대조했다.

## PR 97의 Windows CI 후속

첫 원격 검사에서 공통 정합성과 Linux 계약은 통과했고, Windows는 새 gx-work 역할 경로에 이전 gx-dev의 LF 속성이 적용되지 않아 배포 리소스 검사에서 멈췄다. `.gitattributes`의 경로를 수정하고 실제 `git check-attr`로 role/index의 LF를 확인했다. sync 검사는 CRLF쌍만 LF로 정규화하고 writer는 LF를 유지한다. BOM·lone CR·추가 빈줄·본문/설정/잔여 역할 차이는 계속 실패한다. 신규 회귀 2개와 기존 내용 drift 보호 1개가 통과했고 실제 `--check`도 통과했다. 세부 RED→GREEN 근거는 [ci-line-endings.md](ci-line-endings.md)에 있다. CI Python은 UTF-8을 명시한다. 최종 원격 결과는 PR checks를 따른다.

이 보완 뒤 canonical 지문은 `d666372:ac2d9d34f743`이며, 같은 코드의 검증 근거를 보존했다.

## 사용자 요청에 따른 완료 후 재조사

PR의 세 CI가 통과한 뒤 새 임시 입력으로 경계 조사를 다시 수행했다. 8종을 재현하고 회귀 19개를 추가해 수정했으며, 제품 코드 수정이 끝난 뒤 관련 입력을 다시 실행하고 별도 검토자가 최종 diff를 확인했다. 전후 비교, 각 재현과 수정, 실제 실행 범위·미실측 항목은 [before-after.md](before-after.md)에 기록한다. 검사 집합은 250개 Codex 계약과 99개 진입/컨텍스트/테스트 helper 검사로 늘었다. 이전 80개/31개라는 수치는 초기 구현 스냅샷이며 최종 소스의 검사 수와 구분한다. 최신 원격 성공 여부는 PR 97 checks를 따른다.

제품 코드 freeze 뒤 배포 이동/예산 4개·정합성 린트 36항목·생성물 `--check`·diff whitespace가 통과했다. canonical 최종 지문은 `164dc10:81f8f910dd04`다. source 수정 뒤 전체 검사를 매번 재실행하지 않고 영향받은 회귀 집합을 확인했다.

## 확인하지 않은 범위

실제 설치된 2.0.0 소비 세션의 자연어 자동 발견, 실제 model/effort, UI Other와 사용자 응답 capture, hook 신뢰 설치는 **NOT_RUN**이다. helper/mock/정적 계약의 통과를 이 항목의 PASS로 바꾸지 않는다. 실제 소비 프로젝트의 runner/build와 모델 품질·사용 토큰·지연·비용 A/B 실측도 하지 않았다.

연구 원문과 파일·소비 경로별 정적 크기는 [token-efficiency.md](token-efficiency.md)에 있다. 길이 단독의 보편적 성능 법칙이나 GX의 실제 토큰 절감률을 주장하지 않는다. 20KB는 상시 진입 지시문을 제한하는 운영 기준이다.
