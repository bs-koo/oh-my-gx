> gx-setup/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 4단계: Google Chat 알림 연동 (선택)

**svn인 경우** → 건너뛴다. `Google Chat 연동 : 건너뜀 (SVN — PR 기반 알림 미지원)` 출력.

**git인 경우:**

1. `.claude/config.json`의 `notifications.googleChat` 확인:
   - `webhookUrl`이 이미 채워져 있으면 →
     `Google Chat 연동 : 완료 ✅ (기존 설정 사용)` 출력. 건너뜀.
   - `webhookUrl`이 비어있으면 → 2번으로. `declined: true`(이전에 거절)여도 gx-setup에서는 다시 묻는다. 이 값은 다른 스킬의 미설정 안내만 막는다.

2. 사용자에게 연동 여부를 묻는다:
   ```
   AskUserQuestion(
     questions: [{
       header: "Chat 연동",
       question: "Google Chat 웹훅 알림을 연동하시겠습니까? (PR 생성 시 Chat Space에 알림)",
       multiSelect: false,
       options: [
         { label: "연동", description: "웹훅 URL을 입력받아 연동합니다" },
         { label: "건너뛰기", description: "연동하지 않고 진행합니다" }
       ]
     }]
   )
   ```
   - "건너뛰기" → `notifications.googleChat.declined`를 `true`로 기록한다(Codex는 위 helper에 `{"notifications":{"googleChat":{"declined":true}}}` updates만 전달, Claude Code는 기존 Edit). `Google Chat 연동 : 건너뜀 (거절 기록 — PR마다 연동 안내를 반복하지 않음, 바꾸려면 /gx-setup 재실행)` 출력.
   - "연동" → 3번으로

3. 웹훅 URL 생성 가이드를 표시한 후 AskUserQuestion으로 URL을 받는다:

   ```
   📋 Google Chat 웹훅 URL 생성 방법

   1. Google Chat에서 알림을 받을 스페이스를 엽니다.
      (스페이스가 없으면 '+ 새 스페이스'로 먼저 생성하세요)
   2. 스페이스 상단의 스페이스 이름을 클릭합니다.
   3. '앱 및 통합' 탭을 선택합니다.
   4. '+ 웹훅 추가'를 클릭합니다.
   5. 웹훅 이름(예: 'Claude Code')을 입력하고 '저장'을 누릅니다.
   6. 생성된 웹훅 URL을 복사합니다.
   ```

   ```
   AskUserQuestion(
     questions: [{
       header: "웹훅 URL 입력",
       question: "위 방법으로 생성한 Google Chat 웹훅 URL을 입력해주세요.",
       multiSelect: false,
       options: [
         { label: "Other로 입력", description: "Other로 이동해서 웹훅 URL을 붙여넣어주세요" },
         { label: "건너뛰기", description: "나중에 설정합니다" }
       ]
     }]
   )
   ```

   - 건너뛰기 → 건너뜀
   - URL 입력 → `https://chat.googleapis.com/` 시작 여부 검증
   - 유효하지 않으면 1회 재입력 요청. 재입력도 유효하지 않으면 건너뜀.
   - 유효하면 → config.json 갱신 (`enabled: true`, `webhookUrl: URL`, `declined: false`). Codex에서는 위 helper에 `{"notifications":{"googleChat":{"enabled":true,"webhookUrl":"{확정 URL}","declined":false}}}` updates만 전달한다. Claude Code는 기존 Edit를 사용한다.
     `Google Chat 연동 : 완료 ✅` 출력
