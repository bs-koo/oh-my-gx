"""보고서의 정적 지시문 크기 표를 현재 worktree에서 재생성한다."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = "43acaee"
REPORT = Path(__file__).with_name("token-efficiency.md")


def contents(path, old=False):
    if old:
        result = subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=ROOT, capture_output=True)
        return result.stdout.decode("utf-8").replace("\r\n", "\n") if result.returncode == 0 else None
    target = ROOT / path
    return target.read_text(encoding="utf-8").replace("\r\n", "\n") if target.exists() else None


def measure(value):
    if value is None:
        return None
    prose = re.sub(r"```[\s\S]*?```", "", value)
    return {"bytes": len(value.encode("utf-8")), "chars": len(value), "lines": len(value.splitlines()),
            "sentences": len(re.findall(r"[.!?。！？](?:\s|$)", prose))}


paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT, text=True).splitlines()
paths = sorted(set(p for p in paths if p.startswith(".claude/skills/") and p.endswith("/SKILL.md")) |
               set(p.relative_to(ROOT).as_posix() for p in (ROOT / ".claude/skills").glob("gx-*/SKILL.md")))
rows = [{"path": path, "before": measure(contents(path, True)), "after": measure(contents(path))} for path in paths]
Path(__file__).with_name("token-metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
table = ["| SKILL | 43acaee: byte / 문자 / 행 / 문장≈ | 현재: byte / 문자 / 행 / 문장≈ |", "|---|---:|---:|"]


def display(value):
    return "없음" if value is None else " / ".join(f"{n:,}" for n in value.values())


for row in rows:
    table.append(f"| {Path(row['path']).parent.name} | {display(row['before'])} | {display(row['after'])} |")


def names(skill, *files):
    return [f".claude/skills/{skill}/{file}" for file in files]


tdd = names("gx-tdd", "SKILL.md", "references/intent-routing.md", "references/pipeline-state.md", "references/interaction-contract.md")
cross = names("gx-cross-review", "SKILL.md")
human = names("gx-humanizer", "SKILL.md")
setup = names("gx-setup", "SKILL.md")
visualize = names("gx-visualize", "SKILL.md")
verify = names("gx-verify", "SKILL.md")
routes = [
    ("gx-tdd 직접 진입 필수 계약", tdd, tdd + names("gx-tdd", "references/roles-and-phases.md")),
    ("cross-review codex, 산출물 있음·수정 처리 없음", cross, cross + names("gx-cross-review", "references/codex-preflight.md", "references/advisor-codex.md", "references/result-format.md")),
    ("cross-review native, 산출물 있음·수정 처리 없음", cross, cross + names("gx-cross-review", "references/advisor-native.md", "references/result-format.md")),
    ("humanizer 한국어 audit/rewrite·기술문서", human, human + names("gx-humanizer", "references/quick-ko.md")),
    ("humanizer 한국어 strict·기술문서", human, human + names("gx-humanizer", "references/quick-ko.md", "references/strict.md")),
    ("setup git·기존 Chat 설정 있음", setup, setup + names("gx-setup", "references/project-type-registration.md", "references/authentication-git.md")),
    ("setup SVN", setup, setup + names("gx-setup", "references/project-type-registration.md", "references/authentication-svn.md")),
    ("visualize trace/progress/impact/sequence 진입문", visualize, visualize),
    ("visualize service 진입문+service 설명", visualize, visualize + names("gx-visualize", "references/service-map.md")),
    ("verify git 통과 main+필수 지문 계산", verify, verify + names("gx-verify", "references/fingerprint.md")),
]
route_table = ["| 소비 경로의 해당 지시문 부분합 | 이전 byte / 문자 | 현재 byte / 문자 |", "|---|---:|---:|"]
route_rows = []
for label, before_files, after_files in routes:
    def total(files, old):
        values = [measure(contents(path, old)) for path in files]
        if any(v is None for v in values):
            raise ValueError(f"필수 경로 누락: {files}")
        return [sum(v[key] for v in values) for key in ("bytes", "chars")]
    before, after = total(before_files, True), total(after_files, False)
    route_rows.append({"route": label, "before-files": before_files, "after-files": after_files, "before": before, "after": after})
    route_table.append(f"| {label} | {before[0]:,} / {before[1]:,} | {after[0]:,} / {after[1]:,} |")
Path(__file__).with_name("token-path-metrics.json").write_text(json.dumps(route_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
text = REPORT.read_text(encoding="utf-8")
for marker, lines in (("SKILLS", table), ("PATHS", route_table)):
    text = re.sub(f"<!-- {marker} START -->[\\s\\S]*?<!-- {marker} END -->",
                  f"<!-- {marker} START -->\n" + "\n".join(lines) + f"\n<!-- {marker} END -->", text)
REPORT.write_text(text, encoding="utf-8")
print(f"{len(rows)}개 SKILL과 {len(routes)}개 조건부 경로 표 갱신")
