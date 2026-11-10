#!/usr/bin/env python3
"""리서치 실행별 경로를 확보하고 기존 파일을 덮지 않고 보고서를 저장한다."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


def reserve(cwd, topic, day, output=None):
    root = Path(cwd).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("프로젝트 디렉터리가 없습니다")
    if not re.fullmatch(r"[0-9]{8}", day or ""):
        raise ValueError("--date는 YYYYMMDD 8자리여야 합니다")
    datetime.strptime(day, "%Y%m%d")
    topic = unicodedata.normalize("NFC", topic).lower()
    slug = re.sub(r"[^\w-]+", "-", topic, flags=re.UNICODE).strip("-_")[:80] or "research"
    output_path = (root / output).absolute() if output else None
    if output_path is not None and (output_path.exists() or output_path.is_symlink()):
        raise ValueError(f"기존 결과를 보존합니다. 새 경로를 선택하세요: {output_path}")
    if output_path is not None:
        # 사용자가 정한 경로는 사용자가 관리하는 산출물이다. .research/와 .gitignore를 만들거나 바꾸지 않고
        # 중간 근거(findings)는 작업 메모리에만 둔다.
        return {"run_dir": None, "findings_path": None, "output_path": output_path.as_posix()}
    research = root / ".research"
    if research.is_symlink():
        raise ValueError(".research 링크를 따라가지 않습니다")
    research.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=f"{day}-{slug}-", dir=research))
    return {"run_dir": run.as_posix(), "findings_path": (run / "findings.md").as_posix(),
            "output_path": (output_path or run / "report.md").as_posix()}


def save(output, body):
    if not body.strip():
        raise ValueError("빈 보고서는 저장하지 않습니다")
    target = Path(output)
    if not target.is_absolute():
        raise ValueError("reserve가 반환한 절대 OUTPUT_PATH를 사용하세요")
    target.parent.mkdir(parents=True, exist_ok=True)
    # x는 예약 후 다른 실행이 같은 이름을 만들었어도 원본을 덮지 않는다.
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(body)
    path = target.as_posix()
    return {"output_path": path,
            "context_command": '/gx-context <도메인명> --from ' + json.dumps(path, ensure_ascii=False)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("reserve")
    prepare.add_argument("--cwd", required=True)
    prepare.add_argument("--topic", required=True)
    prepare.add_argument("--date", required=True)
    prepare.add_argument("--output")
    finish = commands.add_parser("save")
    finish.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = reserve(args.cwd, args.topic, args.date, args.output) if args.command == "reserve" else save(
            args.output, sys.stdin.buffer.read().decode("utf-8-sig"))
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
