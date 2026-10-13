#!/usr/bin/env python3
"""DE-13 단위테스트계획서(xlsx) 역보강 헬퍼 — Python 3.10 표준 라이브러리 전용.

tests     : diff의 변경 테스트 파일에서 테스트 선언 목록을 뽑는다
functions : 계획서 기능 목록(기능ID·기능명·UT 수)
rows      : 지정 기능의 UT 행과 행 지문
record    : gx-tdd가 쓴 짝짓기 초안을 검증해 원장에 병합한다
apply     : 원장을 계획서에 반영하고(결과·보강·신규 행) 개정이력을 남긴다
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
M = "{%s}" % NS_MAIN

DATA_SHEET = "단위테스트계획"
REQUIRED = ("테스트ID", "연계기능ID", "사전조건", "입력", "기대결과", "사후조건",
            "의존성", "테스트담당자", "수행일", "결과")
FIELDS4 = ("사전조건", "입력", "기대결과", "사후조건")
DITTO = "〃"


class InputError(Exception):
    """입력 파일·인자 오류 (종료 코드 2)."""


# ---------- xlsx 읽기 ----------

def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _col_letters(idx: int) -> str:
    idx += 1
    out = ""
    while idx:
        idx, r = divmod(idx - 1, 26)
        out = chr(65 + r) + out
    return out


def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(M + "t"))


class Workbook:
    def __init__(self, path: Path):
        try:
            self.zip = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise InputError(f"xlsx를 열 수 없습니다: {path} ({exc})") from exc
        names = set(self.zip.namelist())
        self.shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            sst = ET.fromstring(self.zip.read("xl/sharedStrings.xml"))
            self.shared = [_text(si) for si in sst.findall(M + "si")]
        wb = ET.fromstring(self.zip.read("xl/workbook.xml"))
        rels = ET.fromstring(self.zip.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        self.sheets: list[tuple[str, str]] = []
        for s in wb.find(M + "sheets"):
            target = targets[s.get("{%s}id" % NS_REL)]
            part = target.lstrip("/") if target.startswith("/") else "xl/" + target
            self.sheets.append((s.get("name"), part))

    def close(self) -> None:
        self.zip.close()

    def rows(self, part: str) -> list[tuple[int, dict[int, str]]]:
        root = ET.fromstring(self.zip.read(part))
        out = []
        for n, row in enumerate(root.iter(M + "row"), start=1):
            rnum = int(row.get("r") or n)
            cells: dict[int, str] = {}
            for pos, c in enumerate(row.findall(M + "c")):
                idx = _col_index(c.get("r")) if c.get("r") else pos
                t = c.get("t")
                if t == "inlineStr":
                    is_ = c.find(M + "is")
                    value = _text(is_) if is_ is not None else ""
                elif t == "s":
                    v = c.find(M + "v")
                    value = self.shared[int(v.text)] if v is not None and v.text else ""
                else:
                    v = c.find(M + "v")
                    value = v.text if v is not None and v.text else ""
                cells[idx] = value
            out.append((rnum, cells))
        return out


def _find_table(wb: Workbook, must: tuple[str, ...]):
    order = sorted(wb.sheets, key=lambda s: s[0] != DATA_SHEET)
    for name, part in order:
        rows = wb.rows(part)
        for i, (_, cells) in enumerate(rows):
            heads = {v.strip(): k for k, v in cells.items() if v and v.strip()}
            if all(h in heads for h in must[:2]):
                missing = [h for h in must if h not in heads]
                if missing:
                    raise InputError(f"필수 열 없음: {', '.join(missing)} (시트: {name})")
                return name, part, heads, rows[i + 1:]
    raise InputError(f"머리글({', '.join(must[:2])})을 찾을 수 없습니다")


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def load_plan(path: Path) -> dict:
    wb = Workbook(Path(path))
    try:
        sheet, part, cols, body = _find_table(wb, REQUIRED)
        index = [name for name, _ in wb.sheets].index(sheet)
    finally:
        wb.close()  # Windows에서 핸들이 남으면 임시 폴더 정리·덮어쓰기가 실패한다
    rows: list[dict] = []
    prev: dict | None = None
    for rnum, cells in body:
        rec = {h: (cells.get(i, "") or "").strip() for h, i in cols.items()}
        if not rec.get("테스트ID"):
            continue
        rec["_row"] = rnum
        rec["_flags"] = []
        rec["_ditto"] = {h for h in cols if rec[h] == DITTO}  # 원본 셀이 〃였던 열
        for h in cols:
            if rec[h] == DITTO and prev and rec["연계기능ID"] and prev["연계기능ID"] == rec["연계기능ID"]:
                rec[h] = prev[h]
            if rec[h] == DITTO and "〃미해결" not in rec["_flags"]:
                rec["_flags"].append("〃미해결")
        rows.append(rec)
        prev = rec
    return {"sheet": sheet, "part": part, "index": index, "cols": cols, "rows": rows, "sha": file_sha(Path(path))}


def row_fingerprint(rec: dict) -> str:
    parts = [re.sub(r"\s+", " ", rec.get(f, "") or "").strip() for f in FIELDS4]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:8]


ROWS_HEADER = ["테스트ID", "연계기능ID", *FIELDS4, "결과", "행 지문"]


def plan_rows(plan: dict, fn_ids: list[str]) -> list[dict]:
    known = {r["연계기능ID"] for r in plan["rows"] if r["연계기능ID"]}
    unknown = [f for f in fn_ids if f not in known]
    if unknown:
        raise InputError(f"계획서에 없는 기능ID: {', '.join(unknown)}")
    return [{"테스트ID": r["테스트ID"], "연계기능ID": r["연계기능ID"], **{f: r.get(f, "") for f in FIELDS4},
             "결과": r.get("결과", ""), "행 지문": row_fingerprint(r)}
            for r in plan["rows"] if r["연계기능ID"] in fn_ids]


# ---------- 마크다운 표 ----------

def _md_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def write_md_table(header: list[str], rows: list[dict]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        lines.append("| " + " | ".join(_md_cell(r.get(h, "")) for h in header) + " |")
    return "\n".join(lines) + "\n"


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, i = [], [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if s[i] == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(s[i])
        i += 1
    cells.append("".join(cur).strip())
    return [c.replace("<br>", "\n") for c in cells]


def read_md_table(path: Path) -> list[dict[str, str]]:
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            if header is not None:
                break
            continue
        cells = _split_row(line)
        if header is None:
            header = cells
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def function_list(plan: dict, spec: Path | None) -> list[dict]:
    names: dict[str, str] = {}
    if spec:
        try:
            wb = Workbook(Path(spec))
            try:
                _, _, cols, body = _find_table(wb, ("기능ID", "기능명"))
            finally:
                wb.close()
            for _, cells in body:
                fid = (cells.get(cols["기능ID"], "") or "").strip()
                if fid:
                    names[fid] = (cells.get(cols["기능명"], "") or "").strip()
        except InputError:
            names = {}
    counts: dict[str, int] = {}
    for r in plan["rows"]:
        if r["연계기능ID"]:
            counts[r["연계기능ID"]] = counts.get(r["연계기능ID"], 0) + 1
    return [{"기능ID": f, "UT수": n, "기능명": names.get(f, "")} for f, n in counts.items()]


# ---------- 테스트 소스 검사 ----------

SKIP_DIRS = {"node_modules", "build", "dist", "target", ".gradle", "out", ".git", ".dev",
             ".idea", ".venv", "venv", "__pycache__", ".next", ".nuxt"}
TEST_DIRS = {"test", "tests", "__tests__", "spec"}
SOURCE_EXT = {".java", ".kt", ".kts", ".groovy", ".scala", ".js", ".jsx", ".ts", ".tsx", ".mjs",
              ".cjs", ".py", ".go", ".cs", ".rb", ".php", ".rs", ".c", ".cc", ".cpp", ".swift"}
TEST_FILE_RE = re.compile(r"(Tests?\.[^.]+$)|(\.(test|spec)\.[^.]+$)|(^test_.*\.py$)|(_test\.[^.]+$)")
DECL_RE = re.compile(
    r"@Test\b|@ParameterizedTest\b|@RepeatedTest\b|@TestFactory\b"
    r"|\b[xf]?(?:it|test)(?:\s*\.\s*(?:skip|only|each|todo|concurrent))*\s*\("
    r"|\bdef test_|\bfunc Test|\[(?:Fact|Theory|Test)\b")
SKIP_RE = re.compile(
    r"@Disabled\b|@Ignore\b|\[Ignore\b|\b(?:it|test|describe)(?:\s*\.\s*(?:only|each|concurrent))*\s*\.\s*(?:skip|todo)\b"
    r"|\bxit\s*\(|\bxtest\s*\(|\bxdescribe\s*\("
    r"|@pytest\.mark\.(?:skip|xfail)|@unittest\.skip|\bt\.Skip\(|\bSkip\s*=")
CLASS_RE = re.compile(r"\bclass\s+\w+|\b[x]?describe\s*(?:\.\s*skip\s*)?\(")
PY_MODULE_SKIP_RE = re.compile(r"^pytestmark\s*=.*\b(?:skip|xfail)\b")
PY_BODY_SKIP_RE = re.compile(r"^\s*(?:pytest\.skip|self\.skipTest)\s*\(")
PY_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s")
HEADER_SCAN_LIMIT = 40


def _strip_comments(text: str, hash_comments: bool) -> list[str]:
    """문자열은 남기고 주석만 공백으로 지운다 (줄 수·열 위치 보존)."""
    out, i, n, state = [], 0, len(text), None
    while i < n:
        ch, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if state == "block":
            if ch == "*" and nxt == "/":
                out.append("  ")
                state, i = None, i + 2
                continue
            out.append("\n" if ch == "\n" else " ")
        elif state:
            if ch == "\\" and nxt and nxt != "\n":
                out.append(ch + nxt)
                i += 2
                continue
            out.append(ch)
            if ch == state or (ch == "\n" and state != "`"):
                state = None
        elif ch == "/" and nxt == "*":
            out.append("  ")
            state, i = "block", i + 2
            continue
        elif (ch == "/" and nxt == "/") or (hash_comments and ch == "#"):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        else:
            if ch in "'\"`":
                state = ch
            out.append(ch)
        i += 1
    return "".join(out).split("\n")


def _skip_balanced(s: str, i: int, open_ch: str, close_ch: str) -> int:
    depth, quote = 0, None
    while i < len(s):
        ch = s[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(s)


def _after_annotations(line: str) -> str:
    """줄 앞의 어노테이션·속성을 걷어 낸 나머지 — 한 줄에 선언까지 있는지 보려고 쓴다."""
    s = line.strip()
    while s:
        if s.startswith("@"):
            m = re.match(r"@[\w.]+\s*", s)
            if not m:
                break
            i = m.end()
            if i < len(s) and s[i] == "(":
                i = _skip_balanced(s, i, "(", ")")
            s = s[i:].lstrip()
        elif s.startswith("["):
            s = s[_skip_balanced(s, 0, "[", "]"):].lstrip()
        else:
            break
    return s


def _is_annotation(line: str) -> bool:
    return line.strip().startswith(("@", "["))


def _opens_body(line: str) -> bool:
    s = _after_annotations(line)
    return bool(s) and ("{" in s or "=>" in s or s.endswith(":"))


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _has_skip(lines: list[str]) -> bool:
    return any(SKIP_RE.search(l) for l in lines)


def _test_header(lines: list[str], i: int) -> tuple[int, int, int]:
    """줄 i의 ID가 속한 테스트 머리 (시작, 기준 선언, 끝) — 위아래 어노테이션 묶음 + 선언 + 본문을 여는 줄.
    빈 줄은 경계로 쓰지 않는다. 앞 테스트의 끝(`}`·`;`·본문 시작·선언)에서 멈춘다."""
    anchor = i
    if not (_is_annotation(lines[i]) or DECL_RE.search(lines[i])):
        # 메서드 이름·인자·본문에 ID가 있으면 바로 위 어노테이션·선언을 기준으로 삼는다
        k = i - 1
        while k >= 0 and i - k <= HEADER_SCAN_LIMIT and not (_is_annotation(lines[k]) or DECL_RE.search(lines[k])):
            k -= 1
        if k >= 0 and i - k <= HEADER_SCAN_LIMIT:
            anchor = k
    start, k = anchor, anchor - 1
    while k >= 0 and anchor - k <= HEADER_SCAN_LIMIT:
        prev, s = lines[k], lines[k].strip()
        if s and not (_is_annotation(prev) and not _opens_body(prev)):
            if DECL_RE.search(prev) or _opens_body(prev) or s.endswith(("}", "})", ";")):
                break
        if s:
            start = k
        k -= 1
    end = anchor
    while not _opens_body(lines[end]) and end + 1 < len(lines) and end - anchor < HEADER_SCAN_LIMIT:
        nxt = lines[end + 1]
        if nxt.strip() and DECL_RE.search(nxt) and not _is_annotation(nxt):
            break
        end += 1
    return start, anchor, max(end, i)


def _py_body_skipped(lines: list[str], end: int) -> bool:
    """파이썬 테스트 본문 첫 들여쓰기 수준의 무조건 skip (조건문 안의 skip은 보지 않는다)."""
    if not PY_DEF_RE.match(lines[end]) or not lines[end].rstrip().endswith(":"):
        return False
    body = None
    for line in lines[end + 1:]:
        if not line.strip():
            continue
        ind = _indent(line)
        if body is None:
            if ind <= _indent(lines[end]):
                return False
            body = ind
        if ind < body:
            return False
        if ind == body and PY_BODY_SKIP_RE.match(line):
            return True
    return False


def _enclosing_skipped(lines: list[str], anchor: int) -> bool:
    """선언 줄의 들여쓰기로 감싸는 class·describe 머리를 찾아 skip 표식을 본다."""
    threshold = _indent(lines[anchor])
    for k in range(anchor - 1, -1, -1):
        line = lines[k]
        if not line.strip() or _indent(line) >= threshold or not CLASS_RE.search(line):
            continue
        s = k
        while s - 1 >= 0 and k - s < HEADER_SCAN_LIMIT and (_is_annotation(lines[s - 1]) or not lines[s - 1].strip()):
            s -= 1
        if _has_skip(lines[s:k + 1]):
            return True
        threshold = _indent(line)
    return False


def _is_skipped(lines: list[str], i: int) -> bool:
    start, anchor, end = _test_header(lines, i)
    return (_has_skip(lines[start:end + 1]) or _py_body_skipped(lines, end)
            or _enclosing_skipped(lines, anchor))


def _is_test_file(rel: str) -> bool:
    p = Path(rel)
    if p.suffix.lower() not in SOURCE_EXT or any(part in SKIP_DIRS for part in p.parts[:-1]):
        return False
    return any(part in TEST_DIRS for part in p.parts[:-1]) or bool(TEST_FILE_RE.search(p.name))


def _load_source(path: Path) -> tuple[list[str], bool]:
    text = Path(path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    suffix = Path(path).suffix.lower()
    lines = _strip_comments(text, hash_comments=suffix in {".py", ".rb"})  # 주석 속 선언·표식은 테스트가 아니다
    return lines, suffix == ".py" and any(PY_MODULE_SKIP_RE.match(l) for l in lines)


def _git_unquote(path: str) -> str:
    """git core.quotePath 인용(`"b/\\353\\251\\224.py"`)을 풀어 UTF-8 경로로 돌려준다."""
    if not (len(path) >= 2 and path.startswith('"') and path.endswith('"')):
        return path
    raw = path[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape")
    return raw.encode("latin-1").decode("utf-8", errors="replace")


def changed_files(diff_text: str) -> list[str]:
    """unified diff의 새 쪽 경로 (git `+++ b/x`, svn `+++ x\\t(working copy)`). 삭제 파일은 뺀다."""
    git = "diff --git " in diff_text
    out: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+++ "):
            continue
        path = _git_unquote(line[4:].split("\t")[0].strip())
        if path == "/dev/null":
            continue
        if git and path.startswith("b/"):
            path = path[2:]
        if path not in out:
            out.append(path)
    return out


def list_tests(root: Path, files: list[str]) -> list[dict]:
    out = []
    for rel in files:
        path = Path(root) / rel
        if not _is_test_file(rel) or not path.is_file():
            continue
        lines, module_skip = _load_source(path)
        seen: set[tuple[int, int]] = set()
        for i, line in enumerate(lines):
            if not DECL_RE.search(line):
                continue
            start, anchor, end = _test_header(lines, i)
            if (start, end) in seen:
                continue
            seen.add((start, end))
            decl = " ".join(l.strip() for l in lines[start:end + 1] if l.strip())
            out.append({"path": rel, "line": anchor + 1, "decl": decl[:300],
                        "skipped": module_skip or _is_skipped(lines, i)})
    return out


def _body_end(lines: list[str], opener: int) -> int:
    """본문을 여는 줄에서 본문 끝 줄 — 파이썬은 들여쓰기, 그 밖은 중괄호 짝으로 찾는다."""
    if PY_DEF_RE.match(lines[opener]) and lines[opener].rstrip().endswith(":"):
        base, last = _indent(lines[opener]), opener
        for k in range(opener + 1, len(lines)):
            if lines[k].strip():
                if _indent(lines[k]) <= base:
                    break
                last = k
        return last
    depth, seen = 0, False
    for k in range(opener, len(lines)):
        for ch in lines[k]:
            if ch == "{":
                depth, seen = depth + 1, True
            elif ch == "}":
                depth -= 1
            if seen and depth <= 0:
                return k
    return opener if not seen else len(lines) - 1


def locate_test(root: Path, location: str) -> dict | None:
    """`경로:줄`이 테스트(머리 또는 본문)를 가리키면 skip 여부와 선언을, 아니면 None을 돌려준다.
    skip은 가리킨 줄이 아니라 그 테스트 전체로 판정한다."""
    rel, _, num = location.strip().rpartition(":")
    path = Path(root) / rel
    if not rel or not num.isdigit() or not _is_test_file(rel) or not path.is_file():
        return None
    lines, module_skip = _load_source(path)
    i = int(num) - 1
    if not 0 <= i < len(lines):
        return None
    _, anchor, _ = _test_header(lines, i)
    start, _, opener = _test_header(lines, anchor)
    if not any(DECL_RE.search(l) for l in lines[start:opener + 1]):
        return None
    if not start <= i <= _body_end(lines, opener):
        return None
    decl = " ".join(l.strip() for l in lines[start:opener + 1] if l.strip())
    return {"path": rel, "line": i + 1, "skipped": module_skip or _is_skipped(lines, anchor), "decl": decl[:300]}

# ---------- 결과 원장 ----------

LEDGER_HEADER = ["구분", "테스트ID", "연계기능ID", *FIELDS4, "결과", "수행일", "담당자",
                 "테스트 위치", "행 지문", "근거", "반영", "선언"]
DRAFT_HEADER = ["구분", "테스트ID", "연계기능ID", *FIELDS4, "테스트 위치", "근거"]
UNASSIGNED = "미지정"


def _write_ledger(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {path.stem} 단위테스트 원장\n\n" + write_md_table(LEDGER_HEADER, rows), encoding="utf-8")


def _check_locations(root: Path, raw: str) -> tuple[list[str], list[str], list[str]]:
    """위치 목록, 문제 목록, 선언 키(`경로::선언` — 줄 번호가 바뀌어도 같은 테스트를 가리킨다)."""
    locs = [s.strip() for s in (raw or "").split(",") if s.strip()]
    bad, keys = [], []
    for loc in locs:
        hit = locate_test(root, loc)
        if hit is None:
            bad.append(f"{loc}(테스트 아님)")
        elif hit["skipped"]:
            bad.append(f"{loc}(skip)")
        else:
            keys.append(f"{hit['path']}::{hit['decl']}")
    return locs, bad, keys


def _applied_ids(kept: list[dict], known: set[str]) -> dict[str, str]:
    """반영된 원장 행의 선언 키 → 계획서 테스트ID (신규 행은 반영 때 발급된 ID)."""
    out = {}
    for r in kept:
        tid = r.get("테스트ID") if r.get("구분") == "기존" else (r.get("반영", "").split() or [""])[-1]
        if tid in known:
            out.update({k: tid for k in (r.get("선언") or "").split("\n") if k})
    return out


def record(draft_rows: list[dict], plan: dict, root: Path, ledger_path: Path, date: str, tester: str) -> dict:
    """초안을 검증해 원장에 병합한다. 반영(`반영` 값 있음)된 행은 보존하고 나머지는 이번 초안으로 바꾼다."""
    by_id = {r["테스트ID"]: r for r in plan["rows"]}
    functions = {r["연계기능ID"] for r in plan["rows"] if r["연계기능ID"]}
    ledger_path = Path(ledger_path)
    kept = [r for r in read_md_table(ledger_path) if r.get("반영")] if ledger_path.is_file() else []
    applied = _applied_ids(kept, set(by_id))
    errors, rows, seen = [], [], set()
    for n, d in enumerate(draft_rows, start=1):
        kind = d.get("구분", "")
        where = f"{n}행({d.get('테스트ID') or kind or '?'})"
        locs, bad, keys = _check_locations(Path(root), d.get("테스트 위치", ""))
        if not locs:
            errors.append(f"{where}: 테스트 위치 없음")
            continue
        if bad:
            errors.append(f"{where}: " + ", ".join(bad))
            continue
        row = {h: "" for h in LEDGER_HEADER}
        row.update({"구분": kind, "결과": "Pass", "수행일": date, "담당자": tester,
                    "테스트 위치": ", ".join(locs), "근거": d.get("근거", ""), "선언": "\n".join(keys)})
        inherited = next((applied[k] for k in keys if k in applied), "")
        if kind == "신규" and inherited:
            # 이미 반영된 테스트를 다시 신규로 적으면 같은 케이스가 두 번 추가된다 — 발급된 ID를 이어받는다
            d = {**d, "구분": "기존", "테스트ID": inherited, "기대결과": ""}
            kind = "기존"
            row.update({"구분": kind, "근거": f"{row['근거']} (반영된 {inherited} 승계)".strip()})
        if kind == "기존":
            rec = by_id.get(d.get("테스트ID", ""))
            if rec is None:
                errors.append(f"{where}: 계획서에 없는 테스트ID")
                continue
            if rec["테스트ID"] in seen:
                errors.append(f"{where}: 같은 테스트ID 중복 — 한 행으로 묶으세요")
                continue
            seen.add(rec["테스트ID"])
            row.update({"테스트ID": rec["테스트ID"], "연계기능ID": rec["연계기능ID"],
                        "기대결과": d.get("기대결과", ""), "행 지문": row_fingerprint(rec)})
        elif kind == "신규":
            fn = d.get("연계기능ID", "") or UNASSIGNED
            if fn != UNASSIGNED and fn not in functions:
                errors.append(f"{where}: 계획서에 없는 연계기능ID {fn}")
                continue
            if not d.get("입력") or not d.get("기대결과"):
                errors.append(f"{where}: 신규 행은 입력·기대결과가 필요합니다")
                continue
            row.update({"연계기능ID": fn, **{f: d.get(f, "") for f in FIELDS4}})
        else:
            errors.append(f"{where}: 구분은 기존/신규")
            continue
        rows.append(row)
    if errors:
        raise InputError("초안 오류 — " + "; ".join(errors))
    _write_ledger(ledger_path, kept + rows)
    old = [r for r in rows if r["구분"] == "기존"]
    new = [r for r in rows if r["구분"] == "신규"]
    return {"기존": len(old), "보강": sum(1 for r in old if r["기대결과"]), "신규": len(new),
            "미지정": sum(1 for r in new if r["연계기능ID"] == UNASSIGNED)}


def cmd_record(args) -> int:
    draft = Path(args.draft)
    if not draft.is_file():
        raise InputError(f"초안 파일이 없습니다: {draft}")
    s = record(read_md_table(draft), load_plan(Path(args.plan)), Path(args.root), Path(args.ledger),
               args.date, args.tester)
    tail = f" · 기능 미지정 {s['미지정']}" if s["미지정"] else ""
    print(f"원장 {Path(args.ledger).name}: 기존 {s['기존']}(보강 {s['보강']}) · 신규 {s['신규']}{tail}")
    return 0

# ---------- 계획서 반영 ----------

TESTERS_HEADER = ["git 이름", "실명"]


def read_testers(path: Path) -> dict[str, str]:
    if not path or not Path(path).is_file():
        return {}
    return {r["git 이름"]: r["실명"] for r in read_md_table(Path(path)) if r.get("git 이름")}


def _cell_xml(ref: str, value: str, style: str | None) -> str:
    s = f' s="{style}"' if style else ""
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


_CELL_RE = re.compile(r'<c\b(?P<attrs>[^>]*?)(?:/>|>.*?</c>)', re.S)


def _patch_row(row_xml: str, rnum: int, values: dict[int, str], defaults: dict[int, str] | None = None) -> str:
    """values 셀을 바꾼다. 없는 셀은 defaults(열→서식)의 서식으로 새로 만든다."""
    defaults = defaults or {}
    if row_xml.endswith("/>"):
        row_xml = row_xml[:-2].rstrip() + "></row>"
    open_end = row_xml.index(">") + 1
    head, inner, tail = row_xml[:open_end], row_xml[open_end:-len("</row>")], "</row>"
    cells = []
    for m in _CELL_RE.finditer(inner):
        ref = re.search(r'\br="([A-Z]+)\d+"', m.group("attrs"))
        cells.append([_col_index(ref.group(1)) if ref else -1, m.group(0)])
    for col, value in sorted(values.items()):
        ref = f"{_col_letters(col)}{rnum}"
        existing = next((c for c in cells if c[0] == col), None)
        if existing:
            style = re.search(r'\bs="(\d+)"', existing[1])
            existing[1] = _cell_xml(ref, value, style.group(1) if style else None)
        else:
            cells.append([col, _cell_xml(ref, value, defaults.get(col))])
    cells.sort(key=lambda c: c[0])
    return head + "".join(c[1] for c in cells) + tail


def _patch_sheet(xml: str, updates: dict[int, dict[int, str]]) -> str:
    if re.search(r"<\w+:worksheet\b", xml):
        raise InputError("지원하지 않는 시트 XML 형식입니다 (접두사 네임스페이스)")
    for rnum, values in updates.items():
        m = re.search(rf'<row\b[^>]*\br="{rnum}"[^>]*?(?:/>|>.*?</row>)', xml, re.S)
        if not m:
            raise InputError(f"계획서에서 {rnum}행을 찾을 수 없습니다")
        xml = xml[:m.start()] + _patch_row(m.group(0), rnum, values) + xml[m.end():]
    return xml


REVISION_HEAD = ("버전", "개정일", "개정 사유", "개정 내용", "작성자")
REVISION_SOURCE = " (gx-tdd)"


def next_version(last: str) -> str:
    """gx-pm 개정이력 규칙: 개정마다 +1.0, 소수점 둘째 자리는 쓰지 않는다."""
    m = re.fullmatch(r"\s*(\d+)\.(\d)\s*", last or "")
    if not m:
        raise InputError(f"개정이력 마지막 버전 '{last}'을 해석할 수 없습니다 — --version으로 지정하세요")
    return f"{int(m.group(1)) + 1}.{m.group(2)}"


def revision_text(new_ids: list[str], refined: int, passed: int) -> str:
    parts = []
    if new_ids:
        span = new_ids[0] if len(new_ids) == 1 else f"{new_ids[0]}~{new_ids[-1]}"
        parts.append(f"단위테스트 신규 {len(new_ids)}건 추가({span})")
    if refined:
        parts.append(f"기대결과 보강 {refined}건")
    parts.append(f"결과 기입 Pass {passed}건")
    return "·".join(parts) + REVISION_SOURCE


def load_revision(path: Path) -> dict | None:
    wb = Workbook(Path(path))
    try:
        try:
            name, part, cols, body = _find_table(wb, REVISION_HEAD)
        except InputError:
            return None
        names = [n for n, _ in wb.sheets]
    finally:
        wb.close()
    entries = [(rnum, cells) for rnum, cells in body if (cells.get(cols["버전"], "") or "").strip()]
    if not entries:
        return None
    rnum, cells = entries[-1]
    return {"sheet": name, "part": part, "index": names.index(name), "cols": cols,
            "last_rnum": rnum, "last_version": cells.get(cols["버전"], "").strip()}


ID_RE = re.compile(r"^(.*?)(\d+)$")
RANGE_RE = re.compile(r"(\$?[A-Z]+\$?)(\d+):(\$?[A-Z]+\$?)(\d+)")
_ROW_NUM_RE = re.compile(r'<row\b[^>]*\br="(\d+)"')


def _ledger_files(ledger_dir: Path) -> list[Path]:
    return [p for p in sorted(Path(ledger_dir).glob("*.md")) if p.name != "testers.md"]


def _id_scheme(rows: list[dict]) -> tuple[str, int, int]:
    found: dict[str, list[str]] = {}
    for r in rows:
        m = ID_RE.match(r["테스트ID"])
        if m:
            found.setdefault(m.group(1), []).append(m.group(2))
    if not found:
        raise InputError("테스트ID 번호 규칙을 찾을 수 없습니다")
    prefix = max(found, key=lambda k: len(found[k]))
    return prefix, max(len(n) for n in found[prefix]), max(int(n) for n in found[prefix])


def _row_styles(xml: str, rnum: int) -> dict[int, str]:
    m = re.search(rf'<row\b[^>]*\br="{rnum}"[^>]*?(?:/>|>.*?</row>)', xml, re.S)
    styles: dict[int, str] = {}
    for c in _CELL_RE.finditer(m.group(0) if m else ""):
        ref = re.search(r'\br="([A-Z]+)\d+"', c.group("attrs"))
        style = re.search(r'\bs="(\d+)"', c.group("attrs"))
        if ref and style:
            styles[_col_index(ref.group(1))] = style.group(1)
    return styles


def _put_rows(xml: str, rows: list[tuple[int, dict[int, str]]], style_rnum: int) -> str:
    """행 번호 자리에 값을 쓴다. 그 행이 이미 있으면(서식만 남은 빈 행) 채우고, 없으면 순서에 맞게 끼운다.
    셀 서식은 style_rnum 행의 같은 열을 따른다."""
    if "</sheetData>" not in xml:
        raise InputError("시트에 행을 추가할 수 없습니다 (sheetData 없음)")
    styles = _row_styles(xml, style_rnum)
    for rnum, values in rows:
        m = re.search(rf'<row\b[^>]*\br="{rnum}"[^>]*?(?:/>|>.*?</row>)', xml, re.S)
        if m:
            xml = xml[:m.start()] + _patch_row(m.group(0), rnum, values, styles) + xml[m.end():]
            continue
        cols = sorted(set(values) | set(styles))
        cells = "".join(_cell_xml(f"{_col_letters(c)}{rnum}", values.get(c, ""), styles.get(c)) for c in cols)
        new = f'<row r="{rnum}">{cells}</row>'
        later = next((n for n in _ROW_NUM_RE.finditer(xml) if int(n.group(1)) > rnum), None)
        at = later.start() if later else xml.index("</sheetData>")
        xml = xml[:at] + new + xml[at:]
    return xml


def _extend_range_text(text: str, old: int, new: int) -> str:
    """끝 행이 old(기존 데이터 끝) 이상 new 미만인 범위를 new까지 늘린다. 이미 new를 덮는 범위는 그대로 둔다."""
    return RANGE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}:{m.group(3)}{new}" if old <= int(m.group(4)) < new
                        else m.group(0), text)


def _extend_sheet_ranges(xml: str, old: int, new: int) -> str:
    """기존 데이터 끝(old) 이후에서 끝나는 dimension·autoFilter·데이터 검증·조건부 서식 범위를 new까지 늘린다."""
    return re.sub(r'(<(?:dimension|autoFilter|dataValidation|conditionalFormatting)\b[^>]*?\b(?:ref|sqref)=")([^"]*)(")',
                  lambda m: m.group(1) + _extend_range_text(m.group(2), old, new) + m.group(3), xml)


def _extend_defined_names(xml: str, index: int, old: int, new: int) -> str:
    return re.sub(rf'(<definedName\b[^>]*\blocalSheetId="{index}"[^>]*>)([^<]*)(</definedName>)',
                  lambda m: m.group(1) + _extend_range_text(m.group(2), old, new) + m.group(3), xml)


def _replace_xlsx(path: Path, parts: dict[str, bytes]) -> None:
    """같은 폴더 임시 파일에 쓰고 다시 읽어 확인한 뒤 원본과 바꾼다. 실패하면 원본은 그대로다."""
    path = Path(path)
    tmp = path.with_name(path.name + ".gx-tmp")
    try:
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w") as dst:
            for info in src.infolist():
                dst.writestr(info, parts[info.filename] if info.filename in parts else src.read(info))
        load_plan(tmp)
        os.replace(tmp, path)
    except PermissionError as exc:
        raise InputError(f"계획서를 바꿀 수 없습니다 — 엑셀에서 닫고 다시 실행하세요 ({exc})") from exc
    finally:
        if tmp.exists():
            tmp.unlink()


def apply(plan_path: Path, ledger_dir: Path, testers: dict[str, str], author: str, date: str,
          version: str | None = None) -> dict:
    plan_path = Path(plan_path)
    plan = load_plan(plan_path)
    by_id = {r["테스트ID"]: r for r in plan["rows"]}
    cols = plan["cols"]
    tables = {p: read_md_table(p) for p in _ledger_files(Path(ledger_dir))}
    pending = [(p, i, r) for p, rows in tables.items() for i, r in enumerate(rows)
               if not r.get("반영") and r.get("구분") in ("기존", "신규")]
    summary = {"계획서": plan_path.as_posix(), "버전": "", "결과 기입": 0, "보강": 0, "신규": [],
               "재확인 필요": [], "계획서에 없음": [], "기능 미지정": 0, "개정이력": "",
               "매핑 없는 담당자": sorted({r.get("담당자", "") for _, _, r in pending} - set(testers))}
    if summary["매핑 없는 담당자"]:
        return summary
    groups: dict[str, list[tuple[Path, int, dict]]] = {}
    for p, i, r in pending:
        if r["구분"] != "기존":
            continue
        rec = by_id.get(r.get("테스트ID", ""))
        if rec is None:
            summary["계획서에 없음"].append(r.get("테스트ID", ""))
        elif r.get("행 지문") != row_fingerprint(rec):
            summary["재확인 필요"].append(rec["테스트ID"])  # PM이 그 사이 행을 고쳤다
        else:
            groups.setdefault(rec["테스트ID"], []).append((p, i, r))
    updates: dict[int, dict[int, str]] = {}
    marks: dict[tuple[Path, int], str] = {}
    for tid, items in groups.items():
        items.sort(key=lambda it: it[2].get("수행일", ""))
        last = items[-1][2]
        values = {cols["결과"]: "Pass", cols["수행일"]: last.get("수행일", ""),
                  cols["테스트담당자"]: testers[last["담당자"]]}
        refined = next((it[2]["기대결과"] for it in reversed(items) if it[2].get("기대결과")), "")
        if refined:
            values[cols["기대결과"]] = refined
            summary["보강"] += 1
        updates.setdefault(by_id[tid]["_row"], {}).update(values)
        summary["결과 기입"] += 1
        marks.update({(p, i): "" for p, i, _ in items})
    refined_rows = {r for r, v in updates.items() if cols["기대결과"] in v}
    order = plan["rows"]
    for n, rec in enumerate(order):
        if rec["_row"] not in refined_rows:
            continue
        for nxt in order[n + 1:]:  # 보강한 셀을 〃로 가리키던 아래 행은 원래 뜻을 명시해 둔다
            if "기대결과" not in nxt["_ditto"] or nxt["연계기능ID"] != rec["연계기능ID"] or nxt["_row"] in refined_rows:
                break
            updates.setdefault(nxt["_row"], {})[cols["기대결과"]] = nxt["기대결과"]
    prefix, width, last_no = _id_scheme(plan["rows"])
    appended: list[dict[int, str]] = []
    for p, i, r in pending:
        if r["구분"] != "신규":
            continue
        siblings = [x for x in plan["rows"] if x["연계기능ID"] == r.get("연계기능ID")]
        if r.get("연계기능ID") == UNASSIGNED or not siblings:
            summary["기능 미지정"] += 1
            continue
        last_no += 1
        tid = f"{prefix}{last_no:0{width}d}"
        values = {c: siblings[-1].get(h, "") for h, c in cols.items()}  # 연계요구사항ID 등은 같은 기능 행을 따른다
        values.update({cols[f]: r.get(f, "") for f in FIELDS4})
        values.update({cols["테스트ID"]: tid, cols["연계기능ID"]: r["연계기능ID"], cols["의존성"]: "없음",
                       cols["결과"]: "Pass", cols["수행일"]: r.get("수행일", ""),
                       cols["테스트담당자"]: testers[r["담당자"]]})
        appended.append(values)
        summary["신규"].append(tid)
        marks[(p, i)] = tid
    if not updates and not appended:
        return summary
    revision = load_revision(plan_path)
    if revision:
        summary["버전"] = version or next_version(revision["last_version"])  # 쓰기 전에 실패해야 원본이 안전하다
    elif version:
        summary["버전"] = version
    with zipfile.ZipFile(plan_path) as z:
        sheet = z.read(plan["part"]).decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
        rev_xml = z.read(revision["part"]).decode("utf-8") if revision else ""
    if appended and "<tablePart" in sheet:
        raise InputError("엑셀 표(Table) 서식이 있는 계획서에는 행을 추가할 수 없습니다")
    sheet = _patch_sheet(sheet, updates)
    if appended:
        old = max(r["_row"] for r in plan["rows"])  # 값이 있는 마지막 행 — 뒤의 빈 서식 행은 채운다
        sheet = _put_rows(sheet, [(old + n, v) for n, v in enumerate(appended, start=1)], old)
        sheet = _extend_sheet_ranges(sheet, old, old + len(appended))
        workbook = _extend_defined_names(workbook, plan["index"], old, old + len(appended))
    parts = {plan["part"]: sheet.encode("utf-8")}
    if revision:
        rc = revision["cols"]
        text = revision_text(summary["신규"], summary["보강"], summary["결과 기입"] + len(summary["신규"]))
        values = {rc["버전"]: summary["버전"], rc["개정일"]: date, rc["개정 사유"]: "추가" if summary["신규"] else "보완",
                  rc["개정 내용"]: text, rc["작성자"]: author}
        old = revision["last_rnum"]
        rev_xml = _extend_sheet_ranges(_put_rows(rev_xml, [(old + 1, values)], old), old, old + 1)
        workbook = _extend_defined_names(workbook, revision["index"], old, old + 1)
        parts[revision["part"]] = rev_xml.encode("utf-8")
        summary["개정이력"] = f"{summary['버전']} {text}"
    else:
        summary["개정이력"] = "개정이력 시트 없음"
    parts["xl/workbook.xml"] = workbook.encode("utf-8")
    for p in {p for p, _ in marks}:  # 계획서만 바뀌고 반영 표시를 못 쓰면 재실행 때 중복 추가된다
        try:
            Path(p).open("r+b").close()
        except OSError as exc:
            raise InputError(f"원장 파일에 쓸 수 없습니다 — 계획서를 바꾸지 않았습니다: {p} ({exc})") from exc
    _replace_xlsx(plan_path, parts)
    tag = f"v{summary['버전']}" if summary["버전"] else date
    for (p, i), tid in marks.items():
        tables[p][i]["반영"] = f"{tag} {tid}".strip()
    for p in {p for p, _ in marks}:
        _write_ledger(p, tables[p])
    return summary


def cmd_apply(args) -> int:
    summary = apply(Path(args.plan), Path(args.ledger_dir), read_testers(Path(args.testers)),
                    args.author, args.date, args.version)
    _write_json(Path(args.report), summary)
    if summary["매핑 없는 담당자"]:
        print("매핑 없는 담당자: " + ", ".join(summary["매핑 없는 담당자"]))
        return 3
    if not summary["결과 기입"] and not summary["신규"]:
        print("반영할 원장 항목이 없습니다")
        return 0
    head = f"계획서 v{summary['버전']}" if summary["버전"] else "계획서"
    print(f"{head} 반영: 결과 {summary['결과 기입']} · 보강 {summary['보강']} · 신규 {len(summary['신규'])}")
    return 0

# ---------- 명령 ----------

def _write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_tests(args) -> int:
    source = Path(args.files_from or args.diff)
    if not source.is_file():
        raise InputError(f"입력 파일이 없습니다: {source}")
    text = source.read_text(encoding="utf-8", errors="replace")
    if args.files_from:
        files = list(dict.fromkeys(l.strip().replace("\\", "/") for l in text.splitlines() if l.strip()))
    else:
        files = changed_files(text)
    tests = list_tests(Path(args.root), files)
    _write_json(Path(args.out), tests)
    print(f"테스트 {len(tests)}개 (skip {sum(t['skipped'] for t in tests)})")
    return 0


def cmd_functions(args) -> int:
    functions = function_list(load_plan(Path(args.plan)), Path(args.spec) if args.spec else None)
    _write_json(Path(args.out), functions)
    print(f"기능 {len(functions)}개")
    return 0


def cmd_rows(args) -> int:
    fn_ids = [f.strip() for f in args.fn.split(",") if f.strip()]
    rows = plan_rows(load_plan(Path(args.plan)), fn_ids)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(write_md_table(ROWS_HEADER, rows), encoding="utf-8")
    print(f"UT {len(rows)}행")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="de13", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tests")
    src = t.add_mutually_exclusive_group(required=True)
    src.add_argument("--diff")
    src.add_argument("--files-from")
    t.add_argument("--root", required=True)
    t.add_argument("--out", required=True)
    t.set_defaults(func=cmd_tests)
    f = sub.add_parser("functions")
    f.add_argument("--plan", required=True)
    f.add_argument("--spec")
    f.add_argument("--out", required=True)
    f.set_defaults(func=cmd_functions)
    w = sub.add_parser("rows")
    w.add_argument("--plan", required=True)
    w.add_argument("--fn", required=True)
    w.add_argument("--out", required=True)
    w.set_defaults(func=cmd_rows)
    r = sub.add_parser("record")
    r.add_argument("--draft", required=True)
    r.add_argument("--plan", required=True)
    r.add_argument("--root", required=True)
    r.add_argument("--ledger", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--tester", required=True)
    r.set_defaults(func=cmd_record)
    a = sub.add_parser("apply")
    a.add_argument("--plan", required=True)
    a.add_argument("--ledger-dir", required=True)
    a.add_argument("--testers", required=True)
    a.add_argument("--author", required=True)
    a.add_argument("--date", default=_dt.date.today().strftime("%Y.%m.%d"))
    a.add_argument("--version")
    a.add_argument("--report", required=True)
    a.set_defaults(func=cmd_apply)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"de13: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
