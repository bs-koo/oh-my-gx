"""파일 내용은 출력하지 않고 gx-lens 근거 경로·라인·재사용 지문을 확인한다."""

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import stat
import sys


EXCLUDED = frozenset({
    ".git", ".svn", "build", "out", "dist", "target", ".gradle",
    "node_modules", "vendor", "worktrees", ".venv", "venv", "__pycache__",
    ".next", ".nuxt", "coverage",
})
MAX_BYTES = 2 * 1024 * 1024
MAX_LINES = 80


class EvidenceError(ValueError):
    pass


def check_evidence(project_root, path, start, end, expected_sha256=None):
    """유효성만 확인한다. 정책의 의미나 실행 결과를 증명하지 않는다."""
    windows_path = PureWindowsPath(path)
    relative = Path(path.replace("\\", "/"))
    if (windows_path.drive or windows_path.root or relative.is_absolute()
            or ".." in relative.parts or not relative.parts):
        raise EvidenceError("outside_scope")
    if any(part.casefold() in EXCLUDED for part in relative.parts):
        raise EvidenceError("excluded_path")
    if start < 1 or end < start or end - start + 1 > MAX_LINES:
        raise EvidenceError("invalid_lines")
    if expected_sha256 is not None and (len(expected_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in expected_sha256)):
        raise EvidenceError("invalid_digest")

    try:
        root = Path(project_root).resolve(strict=True)
        if not root.is_dir():
            raise EvidenceError("invalid_root")
        candidate = root
        for part in relative.parts:
            candidate = candidate / part
            metadata = candidate.lstat()
            # Windows junction도 reparse point다. 루트 아래의 링크 경유를 제외한다.
            if (stat.S_ISLNK(metadata.st_mode) or
                    getattr(metadata, "st_file_attributes", 0) &
                    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
                raise EvidenceError("linked_path")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise EvidenceError("outside_scope")
        if not resolved.is_file():
            raise EvidenceError("unreadable")
        with resolved.open("rb") as source:
            data = source.read(MAX_BYTES + 1)
    except (OSError, RuntimeError):
        raise EvidenceError("unreadable") from None

    if len(data) > MAX_BYTES:
        raise EvidenceError("file_too_large")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise EvidenceError("not_utf8_text") from None
    if "\x00" in text:
        raise EvidenceError("not_utf8_text")
    if end > len(text.splitlines()):
        raise EvidenceError("invalid_lines")

    digest = hashlib.sha256(data).hexdigest()
    status = "changed" if expected_sha256 and digest != expected_sha256.lower() else "valid"
    return {
        "status": status,
        "path": relative.as_posix(),
        "start": start,
        "end": end,
        "locator": f"{relative.as_posix()}:{start}-{end}",
        "sha256": digest,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--path", required=True, help="프로젝트 루트 상대경로")
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    try:
        result = check_evidence(args.project_root, args.path, args.start, args.end, args.expected_sha256)
    except EvidenceError as error:
        result = {"status": "invalid", "reason": str(error)}
    # ASCII JSON은 PowerShell 기본 코드페이지에서도 경로 문자를 손상시키지 않는다.
    print(json.dumps(result, ensure_ascii=True))
    return {"valid": 0, "changed": 1, "invalid": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
