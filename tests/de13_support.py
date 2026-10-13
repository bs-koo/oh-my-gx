"""DE-13 헬퍼 테스트용 최소 xlsx 생성기."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from codex_test_support import load

HELPER = ".claude/skills/gx-test-plan/scripts/de13.py"

PLAN_HEADER_11 = ["테스트ID", "연계기능ID", "연계요구사항ID", "사전조건", "입력", "기대결과",
                  "사후조건", "의존성", "테스트담당자", "수행일", "결과"]


def load_de13():
    return load("de13", HELPER)


def sample_rows():
    """REB 계획서의 실제 패턴(〃, 비기능, [미확정], [가정], 떨어진 ID, 타기능 의존)을 담은 행."""
    return [
        ["UT-001", "FN-001", "RE-001", "신규 프로젝트", "파일 4종(각 500MB)", "회차 생성, 상태 '등록완료'", "TB_CYCL 1건", "없음", "", "", ""],
        ["UT-002", "FN-001", "RE-001", "〃", "파일 1,001MB", "\"파일 용량 초과\" 안내", "저장 없음", "없음", "", "", ""],
        ["UT-003", "FN-001", "RE-001", "〃", "파일 정확히 1,000MB", "정상 등록", "TB_SRC_FILE 1건", "UT-001", "", "", ""],
        ["UT-004", "FN-002", "RE-002", "회차 5건", "목록 조회", "등록일 역순 5건", "변화 없음", "UT-001", "", "", ""],
        ["UT-005", "FN-002", "RE-002", "〃", "메모 2,001자", "\"2,000자 이내\" 안내 [가정:2000]", "변화 없음", "없음", "", "", ""],
        ["UT-006", "", "RE-050", "300MB 파일", "응답시간 측정", "30초 이내", "측정 로그", "없음", "", "", ""],
        ["UT-007", "FN-002", "RE-002", "(규격 미정)", "파싱 검증", "[미확정] 규격 없음", "검증 보류", "없음", "", "", ""],
        ["UT-008", "FN-001", "RE-001", "상한 초과", "다운로드", "\"조건을 좁혀\" 안내", "변화 없음", "없음", "", "", ""],
    ]


def _cell(ref: str, value: str, shared_index: dict | None, style: str | None, runs: list | None) -> str:
    s = f' s="{style}"' if style else ""
    if runs is not None:
        rich = "".join(f"<r><t>{escape(t)}</t></r>" for t in runs)
        return f'<c r="{ref}"{s} t="inlineStr"><is>{rich}</is></c>'
    if value == "":
        return f'<c r="{ref}"{s}/>'
    if shared_index is not None:
        idx = shared_index.setdefault(value, len(shared_index))
        return f'<c r="{ref}"{s} t="s"><v>{idx}</v></c>'
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def _col(i: int) -> str:
    i += 1
    out = ""
    while i:
        i, r = divmod(i - 1, 26)
        out = chr(65 + r) + out
    return out


def _abs(rng: str) -> str:
    return re.sub(r"([A-Z]+)(\d+)", r"$\1$\2", rng)


def _sheet_xml(rows, shared_index, validation, style, rich, filter_from=None):
    body = []
    for r, values in enumerate(rows, start=1):
        cells = "".join(
            _cell(f"{_col(c)}{r}", v, shared_index, style, rich.get(f"{_col(c)}{r}"))
            for c, v in enumerate(values))
        body.append(f'<row r="{r}">{cells}</row>')
    last = f"{_col(max((len(r) for r in rows), default=1) - 1)}{len(rows)}"
    dim = f'<dimension ref="A1:{last}"/>' if filter_from else ""
    af = f'<autoFilter ref="{filter_from}:{last}"/>' if filter_from else ""
    dv = ""
    if validation:
        dv = (f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" '
              f'sqref="{validation}"><formula1>"Pass,Fail"</formula1></dataValidation></dataValidations>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{dim}<sheetData>{"".join(body)}</sheetData>{af}{dv}</worksheet>'), last


def make_xlsx(path: Path, sheets, shared=False, validation=None, style=None, rich=None, filters=None):
    """sheets: [(시트명, [[셀값,...],...]), ...].
    shared=True면 공유 문자열(엑셀 재저장 형식), style은 모든 셀의 s 속성.
    validation(결과 열 데이터 검증 범위)과 rich={"D2": ["앞", "뒤"]}(서식 런)는
    '단위테스트계획' 시트(없으면 첫 시트)에 적용한다.
    filters={"시트명": "A1"}이면 그 시트에 dimension·autoFilter·_FilterDatabase 정의 이름을 넣는다."""
    shared_index = {} if shared else None
    filters = filters or {}
    target = next((i for i, (name, _) in enumerate(sheets) if name == "단위테스트계획"), 0)
    sheet_parts, defined = [], []
    for n, (name, rows) in enumerate(sheets):
        xml, last = _sheet_xml(rows, shared_index, validation if n == target else None, style,
                               (rich or {}) if n == target else {}, filters.get(name))
        sheet_parts.append((name, f"xl/worksheets/sheet{n + 1}.xml", xml))
        if name in filters:
            defined.append(f'<definedName name="_xlnm._FilterDatabase" localSheetId="{n}" hidden="1">'
                           f"'{escape(name)}'!{_abs(filters[name] + ':' + last)}</definedName>")
    names = f"<definedNames>{''.join(defined)}</definedNames>" if defined else ""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        sheets_xml = "".join(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _, _) in enumerate(sheet_parts, start=1))
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f'<sheets>{sheets_xml}</sheets>{names}</workbook>')
        rels = "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(sheet_parts) + 1))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'{rels}</Relationships>')
        for _, part, xml in sheet_parts:
            z.writestr(part, xml)
        if shared_index is not None:
            items = "".join(f"<si><t>{escape(v)}</t></si>" for v, _ in sorted(shared_index.items(), key=lambda kv: kv[1]))
            z.writestr("xl/sharedStrings.xml",
                       '<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                       f'count="{len(shared_index)}" uniqueCount="{len(shared_index)}">{items}</sst>')
    return path
