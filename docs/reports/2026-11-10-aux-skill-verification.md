# 보조 스킬 개선·검증 기록

기준 main은 `6ef7517`, 작업 브랜치는 `codex/fix-aux-skill-edges`다. 기존 사용자 변경과 분리한 `D:/SQ/oh-my-gx/.claude/worktrees/gx-aux-skill-edges`에서 수정했다. **최종 로컬 통합 검사와 독립 재리뷰를 완료했다.**

## 승인된 13건의 수정

| 대상 | 변경 |
|---|---|
| gx-commit | 명시 제외를 이미 staged인 파일에도 적용하고 커밋 전 재확인 |
| 보호 훅 | cwd 대신 실제 `git -C` 대상의 브랜치·검증 상태 확인 |
| gx-commit | 실패 시 부분 staging·삭제를 포함한 원 index 복원, 작업 파일 보존 |
| gx-green | 대상 외 테스트·실행 설정까지 목록과 지문 비교 |
| gx-setup | 새 템플릿과 기존 등록 구분, 루트 프로젝트와 하위 스택 함께 탐색 |
| gx-cross-review | 명시 stat·큰 diff 전환에서도 untracked 경로·통계 유지 |
| gx-humanizer | 중단·실패 run을 포함한 배타 예약과 기존 결과 보존 |
| gx-humanizer | 원문·확정 장르·톤·범위를 검수에 전달 |
| gx-lens | 모델 메타를 표준입력·대화로 전달하여 읽기 전용 유지 |
| gx-tech-debt | 정상 빈 결과와 오류·부분·미지원 결과 구분, 불완전 점수 보류 |
| gx-visualize | 명시 backend 전달, static/mermaid에서 Archify 탐지·설치 생략 |
| gx-visualize | 출력 잠금·고유 임시 JSON·원자적 교체로 동시 쓰기 보호 |
| gx-research | 확정 출력 경로를 저장·완료·인계에 공통 사용 |

## 추가 리뷰와 통합 검사에서 보완한 경계

- 테스트 설정 판정은 공통 `gx-test-plan.py`를 재사용한다. Babel·SWC·tsconfig·Gradle wrapper 누락과 탐색 오류의 조용한 생략을 차단했다.
- strict의 fidelity·naturalness·최종 선택을 같은 run/round/rewrite 지문에 결합했다. 작업본이 바뀌어도 검수 대상은 불변 보존본이다.
- 사용자 정의 `detect`와 `partial`·`error`·`errors`라는 정상 npm 패키지명을 지원한다. 실제 오류 형상은 계속 구분한다.
- staging은 임시 index에서 준비하고 실제 반영 직전에 lock·HEAD·기존 index를 재확인한다. 처리 중 외부 변경을 자기 변경으로 채택해 복원하는 경계를 제거했다.
- 여러 Git 대상·따옴표 밖 줄바꿈·뒤의 SVN `ci` deny를 평가한다. 앞의 ask가 뒤의 deny를 가리지 않는다.
- BOM 포함 정상 Windows 설정과 문서의 `--history` 별칭을 연결했다.
- 진입 지시문의 기존 20KB 예산을 유지했다. setup의 진단·JDK 상세와 cross-review의 diff 수집 상세는 조건부 참조로 분리했다. 실제 파일 크기는 각각 18,652·18,832바이트다.

## 기능 개선

`gx-commit --preview`, `gx-humanizer --history`, `gx-setup --inspect`를 추가했다. 조회는 커밋·새 윤문·설정 변경을 시작하지 않는다. 13개 보조 전문 스킬의 기능별 판단과 후속 후보는 [기능 개선 검토](2026-11-10-aux-skill-functional-roadmap.md)에 있다.

## 실행 근거

| 검사 | 결과 |
|---|---|
| 신규 보조 스킬 회귀 전체 | 84건 통과 |
| Codex 오프라인 계약 전체 | 286건 통과 |
| 시각화 기존 orchestration·index·문서·계약 | 85건 통과 |
| 공통 진입·배포 | 64건 중 예산 2건 실패를 확인, 상세 참조 분리 후 해당 2건 통과 |
| 설치 지시문 경로 | 14건 통과 |
| 모델 정책·기존 입력 호환 | 담당 검사 38건 통과 |
| lens 정책·영향 분석 계약 | 전체 15건 통과 |
| config merge | 담당 검사 8건 통과 |
| sync 생성물 검사 | 통과 |
| 정합성 lint | 최종 파일 동결 후 36단계 통과 |
| 보호 훅 전체 | 6개 그룹 통과 |
| 행동 러너 mock | 30 pass, 0 fail |

각 담당은 실제 임시 파일·Git 저장소와 오류 주입으로 RED를 확인한 뒤 수정했다. 독립 리뷰는 구현과 회귀를 읽기 전용으로 대조했다. integrity/윤문/시각화, 분석/설정, delivery의 보완 사항은 재검토에서 해결됐으며 추가 미해결 P1/P2는 없었다. 별도 배포 조사에서도 두 플러그인의 helper·참조 경로 누락을 찾지 못했다.

## 확인 범위와 보존

실제 설치된 앱의 자동 발견·모델 호출·승인 UI·훅 신뢰는 이번에 실행하지 않았다. [실제 세션 시나리오 A1~A10](../../tests/codex-smoke.md)은 미실행으로 남겼다. Windows의 로컬 회귀를 Linux CI나 실제 앱 통과로 표현하지 않는다. 생성 역할만 복사하는 기존 export 검사를 전체 스킬의 독립 실행 검증으로 해석하지 않는다.

split/shared index와 별도 Git 경로 환경변수는 변경 전에 중단한다. 외부 lock·HEAD·index 변경 및 손상된 백업은 강제 복구하지 않고 보존한다. 종료되지 않은 시각화의 남은 lock은 자동 삭제하지 않으며 실행 종료 확인 후 문서의 복구 절차를 따른다. 이력의 산출물 존재를 strict 통과로 취급하지 않고, 의존성 결과는 문서에 명시된 스키마 범위에서 판정한다.

로컬 검증 종료 시 기존 작업 폴더의 보존 지문 48개·HEAD·브랜치가 모두 일치했다. 이 기록은 커밋·PR 이전의 검증 결과이며 실제 설치 cache는 갱신하지 않았다. 이후 사용자의 PR 게시 요청에 따른 전체 개선 보고는 [통합 보고서](2026-11-10-improvement-summary.md)를 따른다.

추가로 요청받은 핵심 모드의 요구사항 문답은 [수정 전 검토](2026-11-10-core-interview-review.md)에 정리했다. 이 보고서의 보조 스킬 범위에서는 분석까지 진행했으며, 이후 별도 보완 요청에 따른 gx-tdd 변경은 [후속 검증 기록](2026-11-10-requirements-dialogue-verification.md)에 구분한다.
