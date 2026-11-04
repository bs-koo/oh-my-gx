> gx-setup/SKILL.md에서 해당 분기에 진입할 때 읽는다. 소비 프로젝트 경로·변수는 원래 스킬의 값을 유지하고, 번들 상대경로는 이 파일 위치 기준이다.

### 2단계: 인증

**git인 경우** → GH 인증을 수행한다:

1. `gh auth status` 로 인증 상태 확인
2. 인증됨 → `GH 인증 : 완료 ✅` 출력
3. 미인증 → 아래 절차로 device flow 인증을 진행한다:

#### 2-1. Device code 발급

```bash
gh auth login --hostname github.com --git-protocol https --web 2>&1
```
- `timeout: 120000` (2분, config.json `timeouts.network` 값) 설정
- 이 명령은 **one-time code**와 인증 URL을 출력한다

#### 2-2. 사용자에게 안내

출력에서 코드와 URL을 파싱하여 아래 형식으로 안내한다:

```
🔐 GitHub 인증이 필요합니다.

1. 브라우저에서 이 URL을 열어주세요: https://github.com/login/device
2. 아래 코드를 입력하세요: XXXX-XXXX
3. GitHub 계정으로 로그인하면 인증이 완료됩니다.

인증을 완료하면 알려주세요.
```

사용자에게 인증 완료 여부를 묻는다:
```
AskUserQuestion(
  questions: [{
    header: "GH 인증",
    question: "GitHub 로그인을 완료하셨나요?",
    multiSelect: false,
    options: [
      { label: "완료", description: "인증을 완료했습니다. 다음 단계로 진행합니다" },
      { label: "재시도", description: "인증 URL을 다시 표시합니다" }
    ]
  }]
)
```

#### 2-3. 인증 확인

사용자가 완료를 알리면 `gh auth status`로 인증 성공 여부를 확인한다.
- 성공 → `GH 인증 : 완료 ✅` 출력
- 실패 → 에러 메시지를 보여주고, 2-1부터 재시도할지 사용자에게 묻는다
