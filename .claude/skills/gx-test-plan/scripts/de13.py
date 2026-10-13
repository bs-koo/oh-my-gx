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
LEDGER_HEADER = ["테스트ID", "상태", "수행일", "담당자", "테스트 위치", "행 지문", "비고"]


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


def changed_files(diff_text: str) -> list[str]:
    """unified diff의 새 쪽 경로 (git `+++ b/x`, svn `+++ x\\t(working copy)`). 삭제 파일은 뺀다."""
    git = "diff --git " in diff_text
    out: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+++ "):
            continue
        path = line[4:].split("\t")[0].strip()
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


def locate_test(root: Path, location: str) -> dict | None:
    """`경로:줄`이 테스트(머리 또는 본문)를 가리키면 skip 여부를, 아니면 None을 돌려준다."""
    rel, _, num = location.strip().rpartition(":")
    path = Path(root) / rel
    if not rel or not num.isdigit() or not _is_test_file(rel) or not path.is_file():
        return None
    lines, module_skip = _load_source(path)
    i = int(num) - 1
    if not 0 <= i < len(lines):
        return None
    start, _, end = _test_header(lines, i)
    if not any(DECL_RE.search(l) for l in lines[start:end + 1]):
        return None
    return {"path": rel, "line": i + 1, "skipped": module_skip or _is_skipped(lines, i)}

# ---------- 결과 원장 ----------

VERDICT_RE = re.compile(r"^(대상|제외\((?P<reason>.+)\)|이관\((?P<work>W\d{2,})\))$")


def _ledger_path(ledger_dir: Path, fn: str) -> Path:
    return Path(ledger_dir) / f"{fn}.md"


def _read_ledger(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    return {r["테스트ID"]: r for r in read_md_table(path) if r.get("테스트ID")}


def _write_ledger(path: Path, fn: str, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [rows[k] for k in sorted(rows)]
    path.write_text(f"# {fn} 단위테스트 결과 원장\n\n" + write_md_table(LEDGER_HEADER, ordered), encoding="utf-8")


def record(floor_rows: list[dict], check: dict, ledger_dir: Path, date: str, tester: str) -> list[Path]:
    results = check.get("results", {})
    entries: dict[str, list[dict]] = {}
    problems = []
    for r in floor_rows:
        m = VERDICT_RE.match(r.get("판정", ""))
        if not m:
            raise InputError(f"알 수 없는 판정 '{r.get('판정', '')}' ({r.get('테스트ID')})")
        base = {"테스트ID": r["테스트ID"], "상태": "", "수행일": "", "담당자": "",
                "테스트 위치": "", "행 지문": r.get("행 지문", ""), "비고": ""}
        if m.group(1) == "대상":
            res = results.get(r["테스트ID"], {"status": "missing", "locations": []})
            if res["status"] != "found":
                problems.append(f"{r['테스트ID']}({res['status']})")
                continue
            loc = next(l for l in res["locations"] if not l["skipped"])
            base.update({"상태": "Pass", "수행일": date, "담당자": tester,
                         "테스트 위치": f"{loc['path']}:{loc['line']}"})
        elif m.group("reason"):
            base.update({"상태": "제외", "비고": m.group("reason")})
        else:
            base.update({"상태": f"이관({m.group('work')})"})
        entries.setdefault(r["기능ID"], []).append(base)
    if problems:
        raise InputError("하한선 미충족 상태에서는 기록하지 않습니다: " + ", ".join(problems))
    written = []
    for fn, rows in entries.items():
        path = _ledger_path(ledger_dir, fn)
        merged = _read_ledger(path)
        for row in rows:
            if merged.get(row["테스트ID"], {}).get("상태") == "Pass" and row["상태"] != "Pass":
                continue  # 이전 작업의 Pass를 후속 작업의 제외·이관으로 낮추지 않는다
            merged[row["테스트ID"]] = row
        _write_ledger(path, fn, merged)
        written.append(path)
    return written


def cmd_record(args) -> int:
    floor, check = Path(args.floor), Path(args.check)
    for p in (floor, check):
        if not p.is_file():
            raise InputError(f"파일이 없습니다: {p}")
    paths = record(read_md_table(floor), json.loads(check.read_text(encoding="utf-8")),
                   Path(args.ledger_dir), args.date, args.tester)
    print("원장 갱신: " + ", ".join(p.name for p in paths))
    return 0

# ---------- 사본 반영 ----------

TESTERS_HEADER = ["git 이름", "실명"]


def read_testers(path: Path) -> dict[str, str]:
    if not path or not Path(path).is_file():
        return {}
    return {r["git 이름"]: r["실명"] for r in read_md_table(Path(path)) if r.get("git 이름")}


def _ledger_rows(ledger_dir: Path) -> list[dict]:
    rows = []
    for p in sorted(Path(ledger_dir).glob("*.md")):
        if p.name == "testers.md":
            continue
        rows.extend(r for r in read_md_table(p) if r.get("테스트ID"))
    return rows


def _cell_xml(ref: str, value: str, style: str | None) -> str:
    s = f' s="{style}"' if style else ""
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


_CELL_RE = re.compile(r'<c\b(?P<attrs>[^>]*?)(?:/>|>.*?</c>)', re.S)


def _patch_row(row_xml: str, rnum: int, values: dict[int, str]) -> str:
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
            cells.append([col, _cell_xml(ref, value, None)])
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


def apply(plan_path: Path, ledger_dir: Path, testers: dict[str, str], out: Path) -> dict:
    plan_path, out = Path(plan_path), Path(out)
    if out.resolve() == plan_path.resolve():
        raise InputError("반영 사본 경로가 원본 계획서와 같습니다 — 원본은 덮어쓰지 않습니다")
    plan = load_plan(plan_path)
    by_id = {r["테스트ID"]: r for r in plan["rows"]}
    cols = plan["cols"]
    ledger = _ledger_rows(Path(ledger_dir))
    in_ledger = {r["테스트ID"] for r in ledger}
    per_fn: dict[str, dict[str, int]] = {}
    for r in plan["rows"]:
        if r["연계기능ID"]:
            per_fn.setdefault(r["연계기능ID"], {"Pass": 0, "제외": 0, "이관": 0, "미착수": 0, "재확인 필요": 0})
            if r["테스트ID"] not in in_ledger:
                per_fn[r["연계기능ID"]]["미착수"] += 1

    def bump(fn: str, key: str) -> None:
        if fn in per_fn:
            per_fn[fn][key] += 1

    recheck, not_in_plan, unknown, updates = [], [], [], {}
    for row in ledger:
        tid, state = row["테스트ID"], row.get("상태", "")
        rec = by_id.get(tid)
        if rec is None:
            not_in_plan.append(tid)
            continue
        fn = rec["연계기능ID"]
        if state.startswith("이관"):
            bump(fn, "이관")
            continue
        if state == "제외":
            bump(fn, "제외")
            continue
        if state != "Pass":
            continue
        if row.get("행 지문") != row_fingerprint(rec):
            recheck.append(tid)
            bump(fn, "재확인 필요")
            continue
        git_name = row.get("담당자", "")
        name = testers.get(git_name)
        if name is None:
            if git_name not in unknown:
                unknown.append(git_name)
            continue
        updates[rec["_row"]] = {cols["결과"]: "Pass", cols["수행일"]: row.get("수행일", ""),
                                cols["테스트담당자"]: name}
        bump(fn, "Pass")
    summary = {"output": out.as_posix(), "기능별": per_fn, "재확인 필요": recheck,
               "계획서에 없음": not_in_plan, "매핑 없는 담당자": unknown}
    if unknown:
        return summary
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(plan_path) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == plan["part"] and updates:
                data = _patch_sheet(data.decode("utf-8"), updates).encode("utf-8")
            dst.writestr(info, data)
    return summary


def cmd_apply(args) -> int:
    summary = apply(Path(args.plan), Path(args.ledger_dir), read_testers(Path(args.testers)), Path(args.out))
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if summary["매핑 없는 담당자"]:
        print("매핑 없는 담당자: " + ", ".join(summary["매핑 없는 담당자"]))
        return 3
    print(f"반영 사본: {summary['output']}")
    return 0

# ---------- 명령 ----------

def _write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_tests(args) -> int:
    diff = Path(args.diff)
    if not diff.is_file():
        raise InputError(f"diff 파일이 없습니다: {diff}")
    tests = list_tests(Path(args.root), changed_files(diff.read_text(encoding="utf-8", errors="replace")))
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
    t.add_argument("--diff", required=True)
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
    r.add_argument("--floor", required=True)
    r.add_argument("--check", required=True)
    r.add_argument("--ledger-dir", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--tester", required=True)
    r.set_defaults(func=cmd_record)
    a = sub.add_parser("apply")
    a.add_argument("--plan", required=True)
    a.add_argument("--ledger-dir", required=True)
    a.add_argument("--testers", required=True)
    a.add_argument("--out", required=True)
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
