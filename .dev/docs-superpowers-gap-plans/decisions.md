# 의사결정 기록

AskUserQuestion으로 오간 질문과 선택을 자동 기록한다. 고른 것뿐 아니라 버린 선택지도 남으므로 왜 그렇게 정했는지가 추적된다.

## 2026-09-09 11:20 · 커밋 범위

**Q.** 커밋 대상을 골라주세요. 목록에 현재 브랜치와 무관한 `.dev/{다른-slug}/` 8개(decisions.md 등 이전 작업 잔재)와 `bash.exe.stackdump`가 있습니다.

선택지:

- 계획 파일 5개만 (Recommended) — docs/specs 스펙 1건 + docs/superpowers/plans 계획 4건만 스테이징합니다. .dev/ 잔재와 stackdump는 그대로 둡니다
**→** .dev/ 잔재도 포함 — .dev/는 협업 공유 대상이므로 decisions.md 8개도 함께 커밋합니다. stackdump는 제외

**A.** .dev/ 잔재도 포함
