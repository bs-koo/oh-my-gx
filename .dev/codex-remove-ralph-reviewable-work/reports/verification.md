# 3.0.0 변경 검증

기준 main 686da85, branch codex/remove-ralph-reviewable-work. 원래 checkout의 별도 미커밋 작업을 편집하지 않고 분리된 worktree에서 진행했다.

## 실행 근거

- 통합 Codex 계약 238개를 로컬에서 한 번 실행해 모두 통과했다(340.671초). 삭제된 Ralph 전용 검사와 원장 지문 경로 검사만 제거했으며 generic Codex runner의 10개 검사는 유지했다.
- gx-work/helper·배포 집합 61개 통과 후 마지막 분류 수정에 해당하는 4개를 재검사해 통과했다. 새 사례는 구버전 pending 승인 승격, active flags, 고아 잠금, 실행/부정/옵션 삭제/인명/혼합 요청을 포함한다. 신규 배포 검사는 빈 제거 폴더가 남은 실패를 재현한 뒤 정리해 통과했다.
- 새 공통 참조는 소스 저장소가 없는 임시 설치 경로로 복사해 gx-work/context/TDD/verify 소비 위치에서 같은 파일로 해석되는지 확인했다. 배포 집합 6개 통과에 포함된다.
- 공개 문서·HTML·매니페스트4개, 시각화 라우팅7개, 완료 파이프라인9개, 커밋 시각화 산출물 제외3개가 통과했다. 일반 완료·헤드리스·SVN·독립 호출 경로를 유지했다.
- 정합성 린트36절, 배포 생성물 --check와 공백 검사 통과. hook-tests는 동결된 소스에서 최종 전체 통과했다. 앞선 실행 중 파일 수정으로 생긴 파싱 실패는 source freeze 후 문법 검사와 재실행으로 구분했다.

원시 출력은 이 작업 logs/codex-integration.log 및 로컬 D:/Temp/remove-ralph-work-final.log, remove-ralph-runner.log, remove-ralph-hooks-final.log, gx-remove-ralph-lint.log에 있다. 원시 로그는 커밋하지 않는다. 마지막 경계 검토 및 보완 결과는 아래에 추가한다.

## 정적 크기와 미실측 범위

배포 SKILL.md 전체 정적 합계는 18개/257,532 bytes에서 16개/224,015 bytes로 바뀌었다. 새 조건부 reviewability 참조는 2,311 bytes다. 이는 파일 크기 비교이며 모든 스킬 본문이 상시 로드되거나 실제 토큰이 같은 비율로 줄었다는 뜻이 아니다. 실제 모델·사용자 이해도·시간·비용 A/B는 하지 않았다.

새 설치의 자동 발견·모델 배정·질문 UI/capture·훅 신뢰는 NOT_RUN이다. 테스트와 로컬 계약의 통과를 설치·사용자 학습 효과로 표현하지 않는다. 첨부 연구의 검증/한계는 article-review.md에 있다. 최종 플랫폼별 CI는 이 변경을 push한 PR checks를 따른다.

## 완료 후 경계 검토와 보완

별도 읽기 전용 검토자가 소스66개를 한 번 검토해 P2 네 건을 찾았다. (1) 명시 /gx-ralph*·루프 실행 표현의 route/handoff 분류 누락, (2) 지원 여부 설명·명시 부정의 오탐, (3) 훅 미신뢰 단독 commit/PR에서 활성 flags 검사 누락, (4) state 없는 lock의 Git 직접 commit/SVN 후보 탐색 누락이다.

네 항목을 각각 보완했다. 분류는 2개 메서드의 RED8건→GREEN, standalone 스킬은 verify 전 활성 flags 중단을 추가했다. lock은 state/완료 여부와 독립 검사하며 SVN의 단일/복수 후보와 심볼릭 링크의 실제 잠금 위치를 보존한다. SVN 새 회귀2개가 통과했고 최종 hook 전체도 통과했다(D:/Temp/remove-ralph-hooks-audit.log). 수정 후 Codex hook 계약15개가 통과했으며 reviewer가 같은 네 지적과 기존 probe만 재확인해 미해결 없음으로 보고했다. 두 번째 전체 감사나 전체 Codex 반복은 하지 않았다.

source freeze 후 생성물·공백·lint 결과와 PR의 최신 CI를 최종 근거로 사용한다. 초기 통과가 발견하지 못했던 경계와 마지막 보완을 구분해 기록한다.

최초 PR 소스의 canonical 지문은 `686da85:6025d567f8d6`다. 원래 staged index와 독립적으로 helper가 계산했고 같은 코드 트리를 commit/PR 게이트에서 사용한다. 마지막 수정 뒤 정합성 린트36절·생성물·공백 검사를 다시 확인했다. 제품 timeout이나 테스트 상한은 완화하지 않았다.

PR 작성 중 main에 e9c3b13의 전체 플러그인 소개 문구 변경이 병합되어 충돌을 해소했다. 새 소개 문구·관계도·gx-work 배치를 보존하고 버전3.0.0/스킬16개만 통합했다. 실행 소스는 바뀌지 않아 전체 Codex를 반복하지 않고 공개 문서/메타데이터4개·생성물·공백을 재검사했다. 통합 후 canonical 지문은 `63b99c9:4d5c05d1d1da`다.
