#!/usr/bin/env python3
"""DE-13 단위테스트계획서(xlsx) 연동 헬퍼 — Python 3.10 표준 라이브러리 전용.

scope  : 계획서에서 기능별 UT 행을 뽑아 ut-floor.md를 쓴다 (--fn 생략 시 기능 목록 JSON)
check  : ut-floor의 '대상' UT ID가 테스트 소스에 skip 없이 존재하는지 확인한다
record : check 결과로 기능별 결과 원장을 갱신한다
apply  : 원장을 계획서 xlsx 사본의 결과·수행일·테스트담당자 열에 반영한다
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
FLOOR_HEADER = ["테스트ID", "기능ID", "사전조건", "입력", "기대결과", "사후조건",
                "의존성", "표식", "판정", "행 지문"]
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
    return {"sheet": sheet, "part": part, "cols": cols, "rows": rows, "sha": file_sha(Path(path))}


def row_fingerprint(rec: dict) -> str:
    parts = [re.sub(r"\s+", " ", rec.get(f, "") or "").strip() for f in FIELDS4]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:8]


def _undecided(rec: dict) -> bool:
    return any("[미확정" in (rec.get(h) or "") for h in rec if not h.startswith("_"))


def build_floor(plan: dict, fn_ids: list[str]) -> list[dict]:
    known = {r["연계기능ID"] for r in plan["rows"] if r["연계기능ID"]}
    unknown = [f for f in fn_ids if f not in known]
    if unknown:
        raise InputError(f"계획서에 없는 기능ID: {', '.join(unknown)}")
    fn_of = {r["테스트ID"]: r["연계기능ID"] for r in plan["rows"]}
    floor = []
    for rec in plan["rows"]:
        if rec["연계기능ID"] not in fn_ids:
            continue
        marks = list(rec["_flags"])
        if "[가정" in " ".join(rec.get(f, "") for f in FIELDS4):
            marks.append("가정")
        deps = re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", rec.get("의존성", ""))
        if any(d in fn_of and fn_of[d] != rec["연계기능ID"] for d in deps):
            marks.append("타기능 의존")
        floor.append({
            "테스트ID": rec["테스트ID"], "기능ID": rec["연계기능ID"],
            **{f: rec.get(f, "") for f in FIELDS4}, "의존성": rec.get("의존성", ""),
            "표식": ", ".join(marks),
            "판정": "제외(미확정 행)" if _undecided(rec) else "대상",
            "행 지문": row_fingerprint(rec),
        })
    return floor


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


def write_floor(path: Path, source: str, plan: dict, fn_ids: list[str], rows: list[dict], date: str) -> None:
    head = ("# UT 하한선\n\n"
            f"- 출처: {source} (시트: {plan['sheet']}, sha256: {plan['sha']})\n"
            f"- 범위: {', '.join(fn_ids)}\n"
            f"- 생성: {date}\n\n")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(head + write_md_table(FLOOR_HEADER, rows), encoding="utf-8")


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
    r"|\b[xf]?(?:it|test)\s*(?:\.\s*(?:skip|only|each)\s*)?\("
    r"|\bdef test_|\bfunc Test|\[(?:Fact|Theory|Test)\b")
SKIP_RE = re.compile(
    r"@Disabled\b|@Ignore\b|\.\s*skip\s*\(|\bxit\s*\(|\bxtest\s*\(|\bxdescribe\s*\("
    r"|@pytest\.mark\.skip|@unittest\.skip|\bt\.Skip\(|\bSkip\s*=")
CLASS_RE = re.compile(r"\bclass\s+\w+|\b[x]?describe\s*(?:\.\s*skip\s*)?\(")


def _annotation_block_start(lines: list[str], j: int) -> int:
    k = j
    while k - 1 >= 0 and lines[k - 1].strip().startswith(("@", "[")):
        k -= 1
    return k


def _file_skipped(lines: list[str]) -> bool:
    for k, line in enumerate(lines):
        if CLASS_RE.search(line):
            start = _annotation_block_start(lines, k)
            return any(SKIP_RE.search(l) for l in lines[start:k + 1])
    return False


def _is_skipped(lines: list[str], i: int) -> bool:
    j = i
    while j >= 0 and not DECL_RE.search(lines[j]):
        j -= 1
    if j < 0:
        return False
    start = _annotation_block_start(lines, j)
    return any(SKIP_RE.search(l) for l in lines[start:i + 1])


def iter_test_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        in_test_dir = any(part in TEST_DIRS for part in rel_dir.parts)
        for name in filenames:
            if Path(name).suffix.lower() not in SOURCE_EXT:
                continue
            if in_test_dir or TEST_FILE_RE.search(name):
                yield Path(dirpath) / name, (rel_dir / name).as_posix()


def _id_pattern(test_id: str) -> re.Pattern:
    raw, under = re.escape(test_id), re.escape(test_id.replace("-", "_"))
    return re.compile(rf"(?<![A-Za-z0-9-])(?:{raw}|{under})(?![0-9A-Za-z])")


def check_floor(floor_rows: list[dict], root: Path) -> dict:
    targets = [r["테스트ID"] for r in floor_rows if r.get("판정") == "대상"]
    patterns = {t: _id_pattern(t) for t in targets}
    found: dict[str, list[dict]] = {t: [] for t in targets}
    for path, rel in iter_test_files(Path(root)):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        whole = _file_skipped(lines)
        for i, line in enumerate(lines):
            for t, pat in patterns.items():
                if pat.search(line):
                    found[t].append({"path": rel, "line": i + 1,
                                     "skipped": whole or _is_skipped(lines, i)})
    results, summary = {}, {"found": 0, "missing": 0, "skipped": 0}
    for t in targets:
        locs = sorted(found[t], key=lambda l: (l["path"], l["line"]))
        status = "missing" if not locs else ("found" if any(not l["skipped"] for l in locs) else "skipped")
        summary[status] += 1
        results[t] = {"status": status, "locations": locs}
    return {"results": results, "summary": summary}


def cmd_check(args) -> int:
    floor = Path(args.floor)
    if not floor.is_file():
        raise InputError(f"ut-floor 파일이 없습니다: {floor}")
    result = check_floor(read_md_table(floor), Path(args.root))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    s = result["summary"]
    print(f"found {s['found']} · missing {s['missing']} · skipped {s['skipped']}")
    return 0 if s["missing"] == 0 and s["skipped"] == 0 else 1

# ---------- 명령 ----------

def cmd_scope(args) -> int:
    plan = load_plan(Path(args.plan))
    out = Path(args.out)
    if not args.fn:
        functions = function_list(plan, Path(args.spec) if args.spec else None)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(functions, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"기능 {len(functions)}개 목록을 {out}에 썼습니다")
        return 0
    fn_ids = [f.strip() for f in args.fn.split(",") if f.strip()]
    rows = build_floor(plan, fn_ids)
    write_floor(out, Path(args.plan).as_posix(), plan, fn_ids, rows, args.date)
    target = sum(1 for r in rows if r["판정"] == "대상")
    print(f"하한선 {len(rows)}행(대상 {target})을 {out}에 썼습니다")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="de13", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scope")
    s.add_argument("--plan", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--fn")
    s.add_argument("--spec")
    s.add_argument("--date", default=_dt.date.today().isoformat())
    s.set_defaults(func=cmd_scope)
    c = sub.add_parser("check")
    c.add_argument("--floor", required=True)
    c.add_argument("--root", required=True)
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_check)
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
