# gx-work 공통 진입·계획 모듈 구현 근거

## 범위

- `.claude/skills/gx-work/SKILL.md`: 자연어 목표의 공통 진입, 명시 의도·종료점 보존, 진행 중 실행 재개 우선, 읽기 전용 요청 유지, 단일 gx-tdd 구현 경로.
- `references/planning.md`: 문서·대화·context의 근거와 결정을 정규화하고 Spec/Constraints/AC/Files/Consumes/Produces/test intent·boundary·command/Review Focus로 계획한다. 외부 계획은 부족·충돌만 보완하며 승인을 추론하지 않는다.
- `references/handoff.md`: run-id·goal·stop-at·승인 근거·plan-file 및 context 포인터를 보존한다. `--from-plan`/`--handoff`를 gx-tdd에 전달한다.
- `scripts/gx-work.py`: 현재 작업 상태의 읽기 전용 라우팅, 정규화 계획 검증, stdout JSON 인계 생성. 파일 쓰기·Git 변경·테스트 명령 실행 기능이 없다.
- `tests/test_gx_work.py`: 임시 Git 저장소·JSON·설치 경로를 사용하는 23개 테스트.

## 검증

1. helper 구현 전 테스트 작성. 빈 동작 상태에서 누락·충돌·read-only·재개·승인 경계 테스트의 실패를 직접 확인했다(초기 16개에 failures/errors).
2. 초기 구현 후 16개 테스트 통과.
3. 추가 두 사례에서 잘못된 선택 설정의 재개 실패, 이해 전용 인계의 intent/run-id 손실을 RED로 확인했다. 수정 후 18개 테스트를 수행했다.
4. `python -X utf8 C:/Users/SQI/.codex/skills/.system/skill-creator/scripts/quick_validate.py .claude/skills/gx-work`: Skill is valid. 기본 Windows cp949 읽기는 실패하므로 UTF-8 모드를 사용했다. 새 entry의 frontmatter는 validator가 지원하는 키만 썼다.
5. `python scripts/sync-codex-resources.py --check`: 초기 exit 0. 마지막 동시 변경 중 reviewer role/config template drift가 발견되어 부모에게 전달했다. 최종 생성물 동기화·전체 검증은 부모 작업에서 확인한다.
6. 독립 리뷰가 지적한 외부 files 범위 탈출·gx-dev 자동 재개·과거 외부 plan run-id 재사용을 RED로 재현한 뒤 수정했다. Windows/POSIX/UNC/drive-relative/`..` 8종을 거절하고 gx-tdd만 자동 재개하며 gx-ralph lock을 보존한다. 최종 23개 테스트 통과.
7. `test_codex_resources.py` 5개 및 `test_codex_skill_layout.py` 15개 통과. questions의 전환 중 실패 2건은 담당자에게 전달했으며 이 검증 결과를 전체 통합 검증으로 주장하지 않는다.

## 추가 압축 범위

gx-tdd의 역할·phase 소개를 필수 참조 roles-and-phases.md로 추출하고 오래된 dev 비교표를 제거했다. gx-cross-review의 advisor·fallback·결과양식·발견처리, gx-setup의 타입등록·VCS별 인증·알림, gx-humanizer의 언어별 치트시트·strict·voice를 조건부 참조로 추출했다. gx-visualize service 맵은 service 분기만, gx-verify 지문 계산은 git 통과 시 필수로 읽도록 추출했다. 7개 main의 실제 설치 복사본에서 20KB 예산과 Read·script 포인터를 검사한다. visualize 코드·템플릿은 수정하지 않았다. 연구·조건부 경로별 byte/char 차이와 모든 SKILL 목록은 token-efficiency.md·token-metrics.json·token-path-metrics.json을 참조한다. main 추출만으로 전체 소비 토큰이 감소했다고 주장하지 않는다.

읽기 전용 검증은 사용자 미커밋 파일과 활성 state가 있는 임시 Git 저장소의 전체 파일 바이트를 호출 전후 비교했다. understand/plan/status는 파일·브랜치·state를 바꾸지 않으며 활성 구현을 재개하지 않았다. 기존 진행 실행의 run-id·goal·stop-at 보존, 종료점의 조용한 확장 차단, 다른 브랜치 state 미선택, 외부 계획의 자체 승인 무시, 부족·중복 ID·결정 충돌·의존성 순환을 검증했다.

## 경계

- 하네스 자연어 자동 발견·질문 UI·실제 모델 호출·설치 신뢰는 실행하지 않았다. 로컬 데이터 계약 검증으로 이를 입증했다고 보고하지 않는다.
- helper는 자연어를 정규식으로 해석하지 않고 하네스가 확인한 intent/stop-at를 받는다. `--approval-source`의 실제 사용자 근거 확인은 하네스 책임이다.
- helper는 계획의 구조적 부족·충돌을 검증한다. 제품 의미의 완전성·focused 명령의 적합성·보안성을 인증하지 않는다.
- gx-tdd consumer·공통 runtime 배포 이동·gx-dev 제거·전체 lint/회귀 검증은 부모 작업 소유다. 이 담당 범위에서 커밋하지 않았다.

## 컨텍스트 비용

gx-work entry는 약 5.2KB이며 계획과 인계 상세는 필요할 때만 읽는다. 실제 모델 토큰·비용을 측정하지 않았다. 기존 계획/문서 본문을 프롬프트에 반복 복사하지 않고 normalized plan 및 context 파일 포인터로 인계하며 계획 단계에서 RGR 분해를 추가하지 않는다. 정확한 비용 비교는 부모의 전체 경로 정적 크기 분석·실제 실행 기록과 함께 해석해야 한다.
