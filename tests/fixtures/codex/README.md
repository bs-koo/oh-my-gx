# Codex 검증 fixture

이 디렉토리의 mock은 실제 모델을 호출하지 않는다. `codex exec`의 명령 인자, stdin, 이벤트 로그, 최종 응답 파일과 종료 코드 계약을 재현한다. mock 통과를 플러그인 설치나 모델 행동 검증의 합격으로 집계하지 않는다.

저장소 루트에서 오프라인 검사를 실행한다.

```text
python -m unittest discover -s tests -p "test_codex_*.py" -v
```

실제 검증 절차와 결과는 [Codex 설치·행동 스모크](../../codex-smoke.md)에 기록한다. 소비 프로젝트는 기존 Node fixture를 임시 Git 저장소로 복사해 준비하며, 플러그인 저장소의 AGENTS.md를 가져오지 않는다. 원격 push와 PR 게시는 수행하지 않는다.

Windows에서만 실행되는 cmd·프로세스 트리 테스트는 Windows에서 통과해야 한다. Linux에서 표시된 Windows 전용 skip은 해당 항목의 합격 증거가 아니다.
