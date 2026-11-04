> gx-cross-review에서 ADVISOR=codex가 선택됐을 때만 읽는다. 설치된 SKILL.md로 확인한 GX_PLUGIN_ROOT와 소비 프로젝트 PROJECT_ROOT를 유지한다.

### 1-1. codex 환경 사전 점검 (codex 선택 시)

다음 순서로 검증한다:

1. **CLI 존재 확인**:
   ```bash
   which codex
   ```
   실패 시 안내 후 종료:
   ```
   codex CLI가 설치되어 있지 않습니다.

   설치:
     npm install -g @openai/codex

   인증:
     codex login
     또는 /codex:setup

   설치/인증 완료 후 /gx-cross-review를 다시 호출해주세요.
   ```
   자동 설치/인증은 수행하지 않는다 — 사용자 환경 침해 방지.

2. **GX 네이티브 helper 확인**: 이 SKILL.md가 설치된 GX 루트의 절대경로를 `${GX_PLUGIN_ROOT}`로 확정하고 `scripts/codex-run.py` 존재를 확인한다. 없으면 "GX 배포가 불완전합니다: {경로}"를 보고하고 중단한다. 소비 프로젝트나 Claude plugin cache에서 companion을 찾지 않는다.
3. **인증 상태**: helper 실행 시 Codex CLI가 검사한다. 설치/인증 문제가 나오면 오류를 보고하고 종료한다. 자동 설치/인증은 하지 않는다.

Codex CLI가 설치·인증되어 있어도 **부모 Codex의 workspace-write 세션 안에서 다시 Codex CLI를 실행하면** `CODEX_HOME` 임시 파일이나 앱 서버 초기화에 필요한 쓰기/네트워크가 차단될 수 있다. 이 경우 오류를 그대로 보고하고, 현재 하네스의 역할 리뷰를 원하면 `--advisor native`로 별도 실행한다. 대화형 호스트에서는 필요한 CLI 권한을 기존 승인 절차로 처리한다. 인증 파일 복사, 권한 변경, 자동 우회 재시도는 하지 않는다. 헤드리스 부모가 승인할 수 없는 작업은 성공으로 취급하지 않는다.

`--advisor native`는 현재 하네스의 역할 에이전트 리뷰다. `--advisor claude`는 Claude Code 호스트에서만 기존 역할 리뷰를 수행한다. **Codex 호스트에서 claude를 선택하면 Claude 실행 경로 미지원으로 종료하고 native 또는 codex를 명시적으로 선택하도록 안내한다.** 이름만 자동으로 바꾸지 않는다. 둘 다 codex 환경 사전 점검은 건너뛴다.

---
