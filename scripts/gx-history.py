#!/usr/bin/env python3
"""커밋된 .dev 문서의 관련 구절과 Git 출처를 제한된 JSON으로 조회한다."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys


TOTAL_BYTES = 8 * 1024 * 1024
EXCERPT_CHARS = 1200
PATH_CHARS = 4096
EXCLUDED = re.compile(r"^(?:reports?|logs?|evidences?|visuals?|architecture|backups?|salvage)(?:$|[-_. ])", re.I)
DOCUMENT = re.compile(r"(?:^|[-_. ])(?:prd|design|decisions?|trust[-_]ledger|plan|brief|ac)(?:$|[-_. \d])", re.I)
PRIORITY = ("decision", "design", "prd", "trust", "plan", "brief", "ac")


class HistoryError(ValueError):
    pass


def git(root, *args, input_bytes=None):
    """고정 인자 배열을 사용하며 optional index 갱신도 하지 않는다."""
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "--no-lazy-fetch", "--no-replace-objects", "--literal-pathspecs", "-C", str(root), *args],
            input=input_bytes, capture_output=True, shell=False, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HistoryError("Git을 실행할 수 없거나 읽기 제한 시간을 초과했습니다") from error
    if result.returncode:
        # Git stderr에는 경로·URL·개인 정보가 포함될 수 있어 그대로 내보내지 않는다.
        raise HistoryError("Git 조회에 실패했습니다: " + args[0])
    return result.stdout


def eligible(path):
    parts = PurePosixPath(path).parts
    return (len(parts) > 1 and parts[0] == ".dev"
            and not any(EXCLUDED.match(part.lstrip("._")) for part in parts[1:-1])
            and parts[-1].lower().endswith(".md")
            and not re.search(r"(?:^|[-_. ])(?:backup|salvage)(?:$|[-_. ])", parts[-1], re.I)
            and bool(DOCUMENT.search(parts[-1][:-3])))


def document_priority(path):
    name = PurePosixPath(path).name.lower()
    return next((index for index, token in enumerate(PRIORITY) if token in name), len(PRIORITY))


def parse_tree(raw):
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, oid, size = metadata.split()
        if kind == b"blob" and not size.isdigit():
            raise HistoryError("Git 원문 blob이 없거나 크기를 읽을 수 없습니다")
        decoded = path.decode("utf-8", "replace")
        valid_utf8 = decoded.encode("utf-8") == path
        entries.append({"path": decoded, "valid_utf8": valid_utf8, "mode": mode.decode("ascii"),
                        "kind": kind.decode("ascii"), "oid": oid.decode("ascii"),
                        "size": int(size) if size != b"-" else 0})
    return entries


def read_blobs(root, entries):
    if not entries:
        return []
    raw = git(root, "cat-file", "--batch", input_bytes=("\n".join(item["oid"] for item in entries) + "\n").encode("ascii"))
    offset = 0
    blobs = []
    for entry in entries:
        end = raw.find(b"\n", offset)
        header = raw[offset:end].split()
        if len(header) != 3 or header[1] != b"blob" or int(header[2]) != entry["size"]:
            raise HistoryError("Git blob 응답이 조회한 스냅샷과 일치하지 않습니다")
        size = int(header[2])
        blobs.append(raw[end + 1:end + 1 + size])
        offset = end + 1 + size + 1
    return blobs


def excerpt(lines, line, terms):
    start, end = max(0, line - 2), min(len(lines), line + 3)
    value = "\n".join(lines[start:end])
    clipped = len(value) > EXCERPT_CHARS
    if clipped:
        # 긴 단일 행에서도 검색어가 잘림 뒤로 사라지지 않도록 중심을 맞춘다.
        lower = value.casefold()
        positions = [lower.find(term) for term in terms if term in lower]
        anchor = min(positions, default=0)
        left = max(0, anchor - EXCERPT_CHARS // 3)
        value = value[left:left + EXCERPT_CHARS]
    return {"line": line + 1, "line_start": start + 1, "line_end": end,
            "excerpt": value, "excerpt_clipped": clipped}


def contributor(root, revision, path, line):
    raw = git(root, "blame", "--line-porcelain", "-L", f"{line},{line}", revision, "--", path)
    lines = raw.decode("utf-8", "replace").splitlines()
    values = {}
    for value in lines[1:]:
        if value.startswith("\t"):
            break
        key, _, content = value.partition(" ")
        values[key] = content
    def date(key):
        return datetime.fromtimestamp(int(values[key]), timezone.utc).isoformat()
    name = values.get("author", "unknown")
    return {"name": name[:256], "name_clipped": len(name) > 256, "authored_at": date("author-time"),
            "committed_at": date("committer-time"), "commit": lines[0].split()[0],
            "role": "Git line contributor; decision maker unverified"}


def working_comparison(root, path, source_sha256, source_size, max_bytes):
    """Git clean filter를 실행하지 않고, 확인한 정규파일의 bytes만 제한해서 비교한다."""
    def result(differs, status, reason=None):
        value = {"status": status}
        if reason:
            value["reason"] = reason
        return differs, value

    parts = PurePosixPath(path).parts
    if not parts or parts[0] != ".dev" or any(part in (".", "..") for part in parts):
        return result(None, "unknown", "outside_project_path")
    if os.name == "nt" and any("\\" in part or ":" in part for part in parts):
        return result(None, "unknown", "unrepresentable_git_path")
    candidate = root.joinpath(*parts)
    if not candidate.is_relative_to(root):
        return result(None, "unknown", "outside_project_path")
    try:
        current = root
        for part in (None, *parts):
            if part is not None:
                current = current / part
            observed = current.lstat()
            if stat.S_ISLNK(observed.st_mode) or getattr(observed, "st_file_attributes", 0) & 0x400:
                return result(None, "unknown", "symlink_or_reparse_point")
            if current != candidate and not stat.S_ISDIR(observed.st_mode):
                return result(None, "unknown", "non_directory_ancestor")
        if not stat.S_ISREG(observed.st_mode):
            return result(None, "unknown", "not_a_regular_file")
        if observed.st_size != source_size:
            return result(True, "size_differs")
        if observed.st_size > max_bytes:
            return result(None, "unknown", "working_file_exceeds_byte_limit")
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(candidate, flags), "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or identity(before) != identity(observed):
                return result(None, "unknown", "changed_during_comparison")
            body = stream.read(max_bytes)
            after = os.fstat(stream.fileno())
            if identity(before) != identity(after):
                return result(None, "unknown", "changed_during_comparison")
        return result(hashlib.sha256(body).hexdigest() != source_sha256, "compared_bytes")
    except FileNotFoundError:
        return result(True, "missing")
    except OSError:
        return result(None, "unknown", "unreadable_working_path")


def search(project_root, terms, limit=5, max_files=200, max_bytes=131072, ref="HEAD"):
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise HistoryError("프로젝트 디렉터리가 존재하지 않습니다")
    if (root / ".svn").is_dir() and not (root / ".git").exists():
        raise HistoryError("SVN은 이 조회 helper에서 지원하지 않습니다. 커밋된 Git .dev가 필요합니다")
    if not 1 <= limit <= 20 or not 1 <= max_files <= 2000 or not 1 <= max_bytes <= 1048576:
        raise HistoryError("조회 한도 범위를 벗어났습니다 (limit 1..20, max-files 1..2000, max-bytes 1..1048576)")
    if not terms or len(terms) > 12 or any(not term.strip() or len(term) > 256 or "\0" in term for term in terms):
        raise HistoryError("1..12개의 비어 있지 않은 검색어가 필요합니다 (검색어당 최대 256자)")
    if not ref or len(ref) > 1024 or ref.startswith("-") or any(char in ref for char in "\0\r\n"):
        raise HistoryError("유효하지 않은 Git ref입니다")
    top = Path(git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    if top != root:
        raise HistoryError("--project-root는 Git 저장소 최상위 디렉터리여야 합니다")
    revision = git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise HistoryError("Git ref를 단일 커밋으로 고정할 수 없습니다")
    terms = list(dict.fromkeys(term.strip() for term in terms))
    folded = [term.casefold() for term in terms]
    tree = parse_tree(git(root, "ls-tree", "-r", "-l", "-z", "--full-tree", revision, "--", ".dev"))
    candidates = [item for item in tree if eligible(item["path"])]
    candidates.sort(key=lambda item: (not any(term in item["path"].casefold() for term in folded),
                                      document_priority(item["path"]), item["path"]))
    skipped = {"unsupported_path": 0, "non_regular": 0, "oversize": 0,
               "binary_or_non_utf8": 0, "file_limit": 0, "byte_budget": 0}
    selected, total_bytes = [], 0
    for item in candidates:
        if not item["valid_utf8"] or len(item["path"]) > PATH_CHARS:
            skipped["unsupported_path"] += 1
        elif item["mode"] != "100644" and item["mode"] != "100755":
            skipped["non_regular"] += 1
        elif item["size"] > max_bytes:
            skipped["oversize"] += 1
        elif len(selected) >= max_files:
            skipped["file_limit"] += 1
        elif total_bytes + item["size"] > TOTAL_BYTES:
            skipped["byte_budget"] += 1
        else:
            selected.append(item)
            total_bytes += item["size"]
    groups, total_matches, text_files = [], 0, 0
    for item, body in zip(selected, read_blobs(root, selected)):
        try:
            if b"\0" in body:
                raise UnicodeError()
            content = body.decode("utf-8-sig")
        except UnicodeError:
            skipped["binary_or_non_utf8"] += 1
            continue
        text_files += 1
        # Git blame는 LF만 행 경계로 센다. Unicode 줄 구분자나 단독 CR은 본문이다.
        lines = content.replace("\r\n", "\n").split("\n")
        if lines[-1] == "":
            lines.pop()
        hits = [index for index, value in enumerate(lines) if any(term in value.casefold() for term in folded)]
        path_match = any(term in item["path"].casefold() for term in folded)
        if not hits and path_match and lines:
            hits = [0]
        digest = hashlib.sha256(body).hexdigest()
        total_matches += len(hits)
        if hits:
            groups.append({"path": item["path"], "lines": lines, "hits": hits[:limit], "digest": digest, "size": len(body)})
    # 한 파일의 반복 표현이 다른 작업의 근거를 전부 밀어내지 않도록 문서별로 순회한다.
    matches = []
    for index in range(limit):
        for group in groups:
            if index < len(group["hits"]) and len(matches) < limit:
                line = group["hits"][index]
                lines = group["lines"]
                matches.append({"path": group["path"], **excerpt(lines, line, folded), "source_sha256": group["digest"],
                                "match_type": "content" if any(term in lines[line].casefold() for term in folded) else "path",
                                "decision_maker": "unknown", "decision_time": "unknown", "approval": "unknown",
                                "current_validity": "unknown", "conflict": "unknown"})
    sizes = {group["path"]: group["size"] for group in groups}
    comparisons = {}
    for match in matches:
        match["record_contributor"] = contributor(root, revision, match["path"], match["line"])
        path = match["path"]
        if path not in comparisons:
            comparisons[path] = working_comparison(root, path, match["source_sha256"], sizes[path], max_bytes)
        match["working_tree_differs_from_source"], match["working_tree_comparison"] = comparisons[path]
    limited = total_matches > limit or any(skipped.values())
    return {"status": "ok", "source": {"vcs": "git", "requested_ref": ref, "revision": revision,
            "content": "committed .dev snapshot only"},
            "scope": {"terms": terms, "match_operator": "any literal (case insensitive)",
                      "tracked_dev_entries": len(tree), "eligible_files": len(candidates), "scanned_files": text_files,
                      "read_bytes": total_bytes, "matched_lines": total_matches, "returned_matches": len(matches),
                      "skipped": skipped, "truncated": limited,
                      "limits": {"matches": limit, "files": max_files, "bytes_per_file": max_bytes,
                                 "total_read_bytes": TOTAL_BYTES, "excerpt_chars": EXCERPT_CHARS,
                                 "path_chars": PATH_CHARS, "contributor_name_chars": 256},
                      "excluded_directory_groups": ["reports", "logs", "evidence", "visual", "architecture", "backup", "salvage"]},
            "matches": matches,
            "limitations": ["Lexical candidates only; no matches does not establish absence of conflicts.",
                            "Excluded, untracked, ignored, uncommitted-only and earlier-revision-only documents are not searched.",
                            "Git line contributor and Git dates do not identify the decision maker or decision time.",
                            "Working comparison is bounded raw bytes; CRLF or working-tree-encoding may differ without semantic edits. Git filters are never run.",
                            "Working paths are observed independently of the Git snapshot; concurrent changes may race the checks. Null comparison means unobserved, not equal.",
                            "Approval, supersession, validity and semantic conflict require reading the original related records."]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("search")
    command.add_argument("--project-root", required=True)
    command.add_argument("--term", action="append", required=True)
    command.add_argument("--limit", type=int, default=5)
    command.add_argument("--max-files", type=int, default=200)
    command.add_argument("--max-bytes", type=int, default=131072)
    command.add_argument("--ref", default="HEAD")
    args = parser.parse_args()
    try:
        result = search(args.project_root, args.term, args.limit, args.max_files, args.max_bytes, args.ref)
    except (HistoryError, OSError, UnicodeError) as error:
        print(json.dumps({"status": "error", "error": str(error), "matches": None}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
