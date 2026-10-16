#!/usr/bin/env python3
"""Extract entrypoint chains (screen -> api -> service -> repository -> table)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = frozenset(
    {".git", ".dev", ".superpowers", "__pycache__", "node_modules", "build", "target", "out", "dist"}
)

MAPPING_ANNOTATIONS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "ANY",
}

_SERVLET_RE = re.compile(r"\bextends\s+HttpServlet\b")
_WEBSERVLET_RE = re.compile(r'@WebServlet\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
_DO_METHOD_RE = re.compile(r"\b(?:protected|public)\s+void\s+(doGet|doPost)\s*\(")
_FORM_ACTION_RE = re.compile(r'<form[^>]*\saction\s*=\s*"([^"]+)"', re.IGNORECASE)
_STATEMENT_RE = re.compile(r"<(select|insert|update|delete)\b[^>]*>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
_MAPPER_NAMESPACE_RE = re.compile(r"<(?:mapper|sqlMap)\b[^>]*\bnamespace\s*=\s*[\'\"]([^\'\"]+)[\'\"]")

_CLASS_RE = re.compile(r"\b(?:class|interface)\s+(\w+)")
_COMMENT_OR_STRING_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/', re.DOTALL)

_FALLBACK_ENCODING = "cp949"


def node_id(kind: str, rel_path: str, symbol: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", rel_path).strip("-")
    return f"gx-{kind}-{slug}--{symbol}"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_excluded(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts[:-1]
    return (any(part in EXCLUDED_DIRS for part in parts)
            or any(parent in {".claude", ".codex"} and child == "worktrees" for parent, child in zip(parts, parts[1:])))


def _read_source(path: Path) -> str | None:
    """Read a scanned source file, falling back to cp949 for legacy Korean sources.

    오래된 한국어 JSP·Java 코드베이스에는 CP949로 저장된 파일이 섞여 있는 경우가 흔하다
    (실측: GSEED Gseed_Web_Renew, JSP 81개 중 2개). utf-8을 먼저 시도하고 실패하면
    cp949로 재시도한다. 둘 다 실패하면 errors="replace"로 문자를 조용히 뭉개는 대신
    None을 반환해, 호출자가 그 파일을 건너뛰고 기록하게 한다.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return path.read_text(encoding=_FALLBACK_ENCODING)
    except UnicodeDecodeError:
        return None


def _node(kind: str, rel_path: str, symbol: str, label: str, line: int, technical: str | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id(kind, rel_path, symbol),
        "kind": kind,
        "symbol": symbol,
        "label": label,
        "status": "unknown",
        "evidence": [{"kind": "code", "file": rel_path, "line": line}],
    }
    if technical:
        node["technical_label"] = technical
    return node


def _diagnostic(items: list[dict[str, Any]], code: str, file: str, line: int, reason: str, **extra: Any) -> None:
    items.append({"code": code, "file": file, "line": line, "reason": reason, **extra})


def _strip_xml_comments(text: str) -> str:
    """CDATA의 SQL 텍스트는 그대로 두고 XML 주석만 위치 보존 공백으로 바꾼다."""
    return re.sub(r"<!\[CDATA\[[\s\S]*?\]\]>|<!--[\s\S]*?-->",
                  lambda match: match.group() if match.group().startswith("<![CDATA[") else re.sub(r"[^\n]", " ", match.group()), text)


def _xml_structure(text: str) -> str:
    """태그 탐색용 사본에서는 CDATA를 가리고 본문은 원문 위치에서 읽는다."""
    return re.sub(r"<!\[CDATA\[[\s\S]*?\]\]>", lambda match: re.sub(r"[^\n]", " ", match.group()), text)


def _mask_java(text: str) -> str:
    """문자열·주석의 길이를 보존해 본문의 괄호와 호출 위치만 분석한다."""
    return re.sub(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/',
                  lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def _closing(text: str, start: int, left: str = "(", right: str = ")") -> int:
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == left:
            depth += 1
        elif text[pos] == right:
            depth -= 1
            if depth == 0:
                return pos
    return -1


def _fields(text: str) -> list[tuple[str, str, int]]:
    """최상위 클래스 필드만 수집한다. 지역변수·상수·기본값 타입은 제외한다."""
    masked = _mask_java(text)
    depths: list[int] = []
    depth = 0
    for char in masked:
        depths.append(depth)
        depth += (char == "{") - (char == "}")
    pattern = re.compile(r"\b(?:(?:private|protected|public|final|transient|volatile)\s+)*(?P<type>[\w.]+)(?:\s*<[^;{}]+>)?\s+(?P<name>\w+)\s*(?:=\s*[^;{}]*)?;")
    excluded = {"byte", "short", "int", "long", "float", "double", "boolean", "char", "String", "Object", "Integer", "Long", "Boolean", "Double", "Float", "Character", "Short", "Byte",
                "throws", "throw", "return", "extends", "implements", "package", "import", "assert", "yield"}
    result = []
    for match in pattern.finditer(masked):
        typename = match.group("type").split(".")[-1]
        prefix = masked[max(masked.rfind(";", 0, match.start()), masked.rfind("{", 0, match.start())) + 1:match.start()]
        if depths[match.start()] == 1 and typename not in excluded and not re.search(r"\bstatic\b", prefix):
            result.append((typename, match.group("name"), match.start()))
    return result


def _method_bodies(text: str) -> list[dict[str, Any]]:
    """첫 클래스의 메서드 선언을 찾는다. 중첩 클래스·익명 클래스는 확장하지 않는다."""
    masked = _mask_java(text)
    depths = []
    depth = 0
    for char in masked:
        depths.append(depth)
        depth += (char == "{") - (char == "}")
    methods = []
    for match in re.finditer(r"\b(\w+)\s*\(", masked):
        if depths[match.start()] != 1:
            continue
        closing = _closing(masked, match.end() - 1)
        if closing < 0:
            continue
        tail = re.match(r"\s*(?:throws\s+[\w.,\s]+)?\{", masked[closing + 1:])
        if tail is None:
            continue
        start = closing + 1 + tail.end() - 1
        end = _closing(masked, start, "{", "}")
        if end >= 0:
            methods.append({"name": match.group(1), "start": match.start(), "body_start": start, "body_end": end,
                            "parameters": text[match.end():closing]})
    return methods


def _collaborator_edges(source: str, fields: list[tuple[str, str, int]], body: str, offset: int,
                        text: str, rel_path: str, dependencies: bool = False,
                        parameters: str = "", diagnostics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    edges = []
    masked = _mask_java(body)
    for typename, name, field_pos in fields:
        calls = list(re.finditer(r"\b(?:this\s*\.\s*)?" + re.escape(name) + r"\s*\.\s*(\w+)\s*\(", masked))
        # other.field.method()의 중간 field를 현재 클래스의 필드로 해석하지 않는다.
        calls = [call for call in calls if not masked[:call.start()].rstrip().endswith((".", "$"))]
        if not dependencies:
            # 같은 이름의 인자·지역변수가 있으면 receiver를 주입 필드라고 단정하지 않는다.
            declaration = r"\b[\w.]+(?:\s*<[^;{}]+>)?(?:\[\])?\s+" + re.escape(name) + r"\s*(?=[=,;)]|$)"
            shadowed = re.search(declaration, _mask_java(parameters)) or re.search(declaration, masked)
            if shadowed:
                uncertain = [call for call in calls if not re.match(r"this\s*\.", call.group())]
                calls = [call for call in calls if call not in uncertain]
                if uncertain and diagnostics is not None:
                    _diagnostic(diagnostics, "ambiguous-call-receiver", rel_path, text.count("\n", 0, offset + uncertain[0].start()) + 1,
                                "필드와 같은 이름의 인자·지역변수가 있어 호출 대상을 확정하지 않았습니다.", target=name)
        if not calls and not dependencies:
            continue
        evidence = [{"kind": "code", "file": rel_path, "line": text.count("\n", 0, offset + call.start()) + 1} for call in calls]
        edges.append({"source": source, "target": typename, "relation": "calls" if calls else "depends_on",
                      "evidence": evidence or [{"kind": "code", "file": rel_path, "line": text.count("\n", 0, field_pos) + 1}],
                      "analysis": "static-call" if calls else "field-type"})
    return edges


def _mappings(text: str, diagnostics: list[dict[str, Any]], rel_path: str) -> list[dict[str, Any]]:
    masked = _mask_java(text)
    result = []
    for match in re.finditer(r"@(" + "|".join(MAPPING_ANNOTATIONS) + r")\b", masked):
        end = match.end()
        while end < len(text) and text[end].isspace():
            end += 1
        args = ""
        if end < len(text) and text[end] == "(":
            close = _closing(masked, end)
            if close < 0:
                _diagnostic(diagnostics, "unsupported-mapping", rel_path, text.count("\n", 0, match.start()) + 1, "매핑 괄호를 해석하지 못했습니다.")
                continue
            args, end = text[end + 1:close], close + 1
        # path/value만 읽는다. produces/consumes 문자열을 경로로 오인하지 않는다.
        attr = re.search(r"\b(?:path|value)\s*=\s*(\{[^}]*\}|\"(?:\\.|[^\"\\])*\"|[^,]+)", args, re.DOTALL)
        expression = attr.group(1).strip() if attr else (args.strip() if "=" not in args else "")
        paths = re.findall(r'"((?:\\.|[^"\\])*)"', expression) if expression else [""]
        if expression and re.sub(r'"(?:\\.|[^"\\])*"|[\s{},]', "", expression):
            paths = []
        if not paths:
            _diagnostic(diagnostics, "unsupported-mapping", rel_path, text.count("\n", 0, match.start()) + 1, "상수 또는 계산식 매핑 경로는 정적으로 확인할 수 없습니다.")
            continue
        verbs = re.findall(r"RequestMethod\.(\w+)", args) or [MAPPING_ANNOTATIONS[match.group(1)]]
        result.append({"start": match.start(), "end": end, "paths": paths, "verbs": verbs})
    return result


def _strip_comments(text: str) -> str:
    """Blank out comments and preserve string literals, keeping all offsets and line breaks.

    String literals are returned untouched so that "http://..." is never mistaken for a comment.
    Replaces every non-newline character in comments with a space to preserve line numbers.
    """
    def _blank(match: re.Match[str]) -> str:
        chunk = match.group(0)
        if chunk.startswith('"'):
            return chunk
        return "".join("\n" if ch == "\n" else " " for ch in chunk)

    return _COMMENT_OR_STRING_RE.sub(_blank, text)


def _class_kind(text: str, rel_path: str | None = None) -> str | None:
    if "@RestController" in text or "@Controller" in text:
        return "controller"
    if "@Service" in text:
        return "service"
    if "@Repository" in text or "@Mapper" in text:
        return "repository"
    class_match = _CLASS_RE.search(text)
    if class_match and class_match.group(1).endswith(("DAO", "Dao")):
        return "repository"
    # service 계층의 Reader·Executor·Linker도 실제 협력자다. 계층 밖 유틸은 편입하지 않는다.
    masked = _mask_java(text)
    if re.search(r"@(?:org\.springframework\.stereotype\.)?Component\b", masked):
        package = re.search(r"\bpackage\s+([\w.]+)\s*;", masked)
        service_package = package is not None and "service" in package.group(1).split(".")
        service_path = rel_path is not None and "service" in Path(rel_path).parts[:-1]
        if service_package or service_path:
            return "service"
    if class_match:
        name = class_match.group(1)
        # Facade는 컨트롤러와 여러 서비스 사이의 계층이다(kereb reb: Controller → RebFacade
        # → 서비스들). service 경계 밖의 @Component에는 유틸도 많으므로
        # 그 밖에서는 Facade 이름으로 한정한다(설계서 §5.8.3, D3).
        # 인터페이스 `XFacade` + 구현 `XFacadeImpl`도 기존 Impl 병합(_merge_service_impls
        # 등 _merge_impl 계열)이 한 노드로 합친다(2026-09-28 최종 리뷰 M8).
        if name.endswith(("Service", "ServiceImpl", "Facade", "FacadeImpl")):
            return "service"
    return None


def _scan_jsp(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    text = _read_source(path)
    if text is None:
        return None
    rel_path = _rel(path, root)
    symbol = path.stem
    node = _node("screen", rel_path, symbol, rel_path, 1, rel_path)
    edges = []
    for match in _FORM_ACTION_RE.finditer(text):
        edges.append({"source": node["id"], "target": match.group(1), "relation": "requests"})
    return [node], edges


def _scan_servlet(path: Path, root: Path, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rel_path = _rel(path, root)
    class_match = _CLASS_RE.search(text)
    class_name = class_match.group(1) if class_match else path.stem
    url_match = _WEBSERVLET_RE.search(text)
    url_pattern = url_match.group(1) if url_match else class_name
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    collaborators = _fields(text)
    masked = _mask_java(text)
    for method in _DO_METHOD_RE.finditer(masked):
        verb = "GET" if method.group(1) == "doGet" else "POST"
        node = _node(
            "api", rel_path, method.group(1), f"{class_name}.{method.group(1)}", text.count("\n", 0, method.start()) + 1, f"{verb} {url_pattern}"
        )
        nodes.append(node)
        start = masked.find("{", method.end())
        end = _closing(masked, start, "{", "}") if start >= 0 else -1
        if end >= 0:
            edges.extend(_collaborator_edges(node["id"], collaborators, text[start:end], start, text, rel_path))
    return nodes, edges


def _sql_tables(sql: str) -> list[tuple[str, str]]:
    """SQL 절에서 물리 테이블과 읽기/쓰기 대상을 추출한다(실행 계획 분석은 아님)."""
    sql = re.sub(r"'(?:''|[^'])*'|--[^\n]*|/\*[\s\S]*?\*/|\$\$[\s\S]*?\$\$", " ", sql)
    sql = re.sub(r"(?:[\w]+\.)?\$\{[^}]*\}(?:\.[\w]+)?|#\{[^}]*\}", " __GX_DYNAMIC__ ", sql)
    ident = r'(?:"(?:""|[^"])+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)'
    tokens = re.findall(ident + r'(?:\s*\.\s*' + ident + r')*|[(),;]', sql)
    tokens = [re.sub(r'\s*\.\s*', '.', token).replace('"', '').replace('`', '').replace('[', '').replace(']', '').upper() for token in tokens]
    ctes = set()
    # WITH [RECURSIVE] name [(columns)] AS (...)의 이름을 수집한다.
    for i, token in enumerate(tokens):
        if token != "WITH":
            continue
        pos = i + 1 + (i + 1 < len(tokens) and tokens[i + 1] == "RECURSIVE")
        while pos < len(tokens):
            name = tokens[pos]
            pos += 1
            if pos < len(tokens) and tokens[pos] == "(":
                level = 1
                pos += 1
                while pos < len(tokens) and level:
                    level += (tokens[pos] == "(") - (tokens[pos] == ")")
                    pos += 1
            if pos >= len(tokens) or tokens[pos] != "AS":
                break
            pos += 1
            while pos < len(tokens) and tokens[pos] in {"NOT", "MATERIALIZED"}:
                pos += 1
            if pos >= len(tokens) or tokens[pos] != "(":
                break
            ctes.add(name)
            level = 1
            pos += 1
            while pos < len(tokens) and level:
                level += (tokens[pos] == "(") - (tokens[pos] == ")")
                pos += 1
            if pos >= len(tokens) or tokens[pos] != ",":
                break
            pos += 1
    result = set()
    depth = 0
    from_depths: set[int] = set()
    # 함수 인자의 FROM(EXTRACT/TRIM/SUBSTRING)은 SQL FROM 절이 아니다.
    # 함수 안의 별도 SELECT 하위 쿼리는 해당 괄호 깊이에서 다시 허용한다.
    query_context = [True]
    grouping_keywords = {"IN", "EXISTS", "AS", "FROM", "JOIN", "VALUES", "ONLY", "LATERAL", "SELECT", "WHERE", "AND", "OR", "NOT", "WHEN", "ON"}
    stop = {"WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "OFFSET", "UNION", "EXCEPT", "INTERSECT", "RETURNING", "SET", "VALUES", "ON"}
    ignored = {"SELECT", "SET", "OF", "EXCLUDED", "DUAL", "__GX_DYNAMIC__", "VALUES", "TABLE"}
    for i, token in enumerate(tokens):
        if token == "(":
            previous = tokens[i - 1] if i else ""
            is_function = bool(re.match(r"^[A-Z_]", previous)) and previous not in grouping_keywords
            query_context.append(query_context[-1] and not is_function)
            depth += 1
            continue
        if token == ")":
            from_depths.discard(depth)
            depth -= 1
            if len(query_context) > 1:
                query_context.pop()
            continue
        if token == "SELECT":
            query_context[-1] = True
        if not query_context[-1]:
            continue
        if token in stop or token == ";":
            from_depths.discard(depth)
        relation = None
        if token in {"FROM", "JOIN"}:
            if token == "FROM" and i and tokens[i - 1] == "DISTINCT":
                continue  # IS [NOT] DISTINCT FROM은 테이블 절이 아닌 값 비교다.
            relation = "writes" if token == "FROM" and i and tokens[i - 1] == "DELETE" else "reads"
            from_depths.add(depth)
        elif token == "INTO" and i and tokens[i - 1] in {"INSERT", "MERGE"}:
            relation = "writes"
        elif token == "UPDATE" and i + 1 < len(tokens) and tokens[i + 1] != "SET" and (not i or tokens[i - 1] not in {"KEY", "DO", "FOR"}):
            relation = "writes"
        elif token == "USING" and any(command in tokens[:i] for command in ("DELETE", "MERGE")):
            relation = "reads"
            from_depths.add(depth)
        elif token == "," and depth in from_depths:
            relation = "reads"
        if relation is None:
            continue
        pos = i + 1
        while pos < len(tokens) and tokens[pos] in {"ONLY", "LATERAL"}:
            pos += 1
        if pos >= len(tokens):
            continue
        name = tokens[pos]
        if name in ignored or name in ctes or name in {"(", ")", ",", ";"} or name.startswith(("PG_CATALOG.", "INFORMATION_SCHEMA.")):
            continue
        if relation == "reads" and pos + 1 < len(tokens) and tokens[pos + 1] == "(":
            continue  # 테이블 함수의 인자는 새 테이블이 아니다.
        result.add((name, relation))
    return sorted(result)


def _scan_mapper_xml(path: Path, root: Path, diagnostics: list[dict[str, Any]] | None = None,
                     fragments: dict[str, tuple[str, str, int]] | None = None,
                     text: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    text = text if text is not None else _read_source(path)
    if text is None:
        return None
    rel_path = _rel(path, root)
    diagnostics = diagnostics if diagnostics is not None else []
    fragments = dict(fragments or {})
    text = _strip_xml_comments(text)
    structure = _xml_structure(text)
    namespace_match = _MAPPER_NAMESPACE_RE.search(structure)
    namespace = namespace_match.group(1) if namespace_match else None
    for fragment in re.finditer(r'<sql\b[^>]*\bid\s*=\s*[\'"]([^\'"]+)[\'"][^>]*>(.*?)</sql>', structure, re.DOTALL | re.IGNORECASE):
        fragments[f"{namespace}.{fragment.group(1)}"] = (text[fragment.start(2):fragment.end(2)], rel_path, text.count("\n", 0, fragment.start()) + 1)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for match in _STATEMENT_RE.finditer(structure):
        line = text[: match.start()].count("\n") + 1
        source_evidence = [{"kind": "code", "file": rel_path, "line": line}]
        expansion_count = 0
        expansion_size = 0
        limit_reported = False

        def substitute(value: str, variables: dict[str, str]) -> str:
            # MyBatis는 한 번만 치환한다. 같은 include의 형제 property를 순차 참조하지 않는다.
            return re.sub(r"(?<!\\)\$\{([^}]+)\}", lambda item: variables.get(item.group(1), item.group()), value)

        def expand(body: str, variables: dict[str, str] | None = None, seen: tuple[str, ...] = (),
                   included: bool = False) -> str:
            nonlocal expansion_count, expansion_size, limit_reported
            expansion_count += 1
            expansion_size += len(body)
            if expansion_count > 256 or expansion_size > 1_000_000:
                if not limit_reported:
                    _diagnostic(diagnostics, "sql-include-limit", rel_path, line, "SQL include 확장 한도(256회 또는 누적 100만 문자)에 도달해 나머지를 해석하지 않았습니다.")
                    limit_reported = True
                return " __GX_DYNAMIC__ "
            variables = variables or {}
            try:
                document = ET.fromstring("<gx-fragment>" + body + "</gx-fragment>")
            except ET.ParseError:
                _diagnostic(diagnostics, "unsupported-sql-xml", rel_path, line, "SQL XML 조각을 해석하지 못해 include와 테이블을 추측하지 않았습니다.")
                return " __GX_DYNAMIC__ "

            def visit(element: ET.Element) -> str:
                if element.tag in {"choose", "when", "otherwise"}:
                    _diagnostic(diagnostics, "dynamic-sql-branch", rel_path, line,
                                "배타적인 동적 SQL 분기는 실행 조건을 평가하지 않아 해당 조각의 테이블을 확정하지 않았습니다.")
                    return " __GX_DYNAMIC__ "
                if element.tag == "foreach":
                    loop_text = " ".join(element.itertext())
                    if re.search(r"\$\{|\b(?:FROM|JOIN|INTO|UPDATE|DELETE)\b", loop_text, re.IGNORECASE):
                        _diagnostic(diagnostics, "dynamic-sql-loop", rel_path, line,
                                    "반복 입력에 따라 달라지는 SQL 조각의 테이블을 확정하지 않았습니다.")
                    # 값 목록도 실제 반복 횟수는 실행하지 않고 괄호 경계만 보존한다.
                    return " ".join((element.get("open", ""), "__GX_DYNAMIC__", element.get("close", "")))
                if element.tag == "include":
                    # refid는 자식 property를 적용하기 전, 상속된 문맥에서 해석한다.
                    ref = substitute(element.get("refid", ""), variables)
                    key = ref if "." in ref else f"{namespace}.{ref}"
                    if key not in fragments or key in seen or len(seen) >= 16:
                        _diagnostic(diagnostics, "unresolved-sql-include", rel_path, line, "SQL include를 해소하지 못했습니다(없음·순환·동적 참조).", target=ref)
                        return " __GX_DYNAMIC__ "
                    local: dict[str, str] = {}
                    for child in element:
                        if child.tag != "property" or child.get("name") is None or child.get("value") is None or len(child):
                            _diagnostic(diagnostics, "unsupported-sql-include", rel_path, line, "include 자식이 name/value를 가진 정적 property 형식이 아닙니다.", target=ref)
                            return " __GX_DYNAMIC__ "
                        name = child.get("name")
                        if name in local:
                            _diagnostic(diagnostics, "duplicate-sql-include-property", rel_path, line, "같은 include에 property 이름이 중복되어 확장하지 않았습니다.", target=name)
                            return " __GX_DYNAMIC__ "
                        local[name] = substitute(child.get("value"), variables)
                    fragment_body, fragment_file, fragment_line = fragments[key]
                    evidence = {"kind": "code", "file": fragment_file, "line": fragment_line}
                    if evidence not in source_evidence:
                        source_evidence.append(evidence)
                    # 외부 namespace 조각 안에서도 unqualified refid는 호출 mapper 기준이다.
                    return expand(fragment_body, {**variables, **local}, (*seen, key), included=True)
                chunks = [substitute(element.text or "", variables) if included else (element.text or "")]
                for child in element:
                    chunks.append(visit(child))
                    chunks.append(substitute(child.tail or "", variables) if included else (child.tail or ""))
                # MyBatis DynamicContext도 SQL 노드를 공백으로 결합한다.
                content = " ".join(chunks)
                if element.tag in {"where", "set"}:
                    return " " + element.tag.upper() + " " + content
                if element.tag == "trim":
                    return " ".join((element.get("prefix", ""), content, element.get("suffix", "")))
                return content

            return visit(document)

        body = expand(text[match.start(2):match.end(2)])
        if re.search(r"\$\{", body):
            _diagnostic(diagnostics, "dynamic-sql-identifier", rel_path, line, "동적 SQL 치환의 실제 테이블·조건은 실행 전 확정할 수 없습니다.")
        for name, relation in _sql_tables(body):
            node = _node("table", rel_path, name, name.split(".")[-1], line, name)
            node["evidence"] = source_evidence.copy()
            # A table's identity is the table itself, not the mapper file that mentions it -
            # the same table referenced from another mapper must resolve to this same node.
            node["id"] = f"gx-table--{name}"
            nodes.setdefault(node["id"], node)
            edges.append(
                {"source": rel_path, "target": node["id"], "relation": relation, "resolved": True, "namespace": namespace,
                 "evidence": source_evidence.copy(), "analysis": "sql-clause"}
            )
    return [nodes[key] for key in sorted(nodes)], edges


def _scan_java(path: Path, root: Path, diagnostics: list[dict[str, Any]] | None = None,
               text: str | None = None, service_interfaces: set[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    text = text if text is not None else _read_source(path)
    if text is None:
        return None
    stripped_text = _strip_comments(text)
    diagnostics = diagnostics if diagnostics is not None else []
    rel_path = _rel(path, root)
    kind = _class_kind(stripped_text, rel_path)
    class_match = _CLASS_RE.search(stripped_text)
    if class_match is None:
        return [], []
    class_name = class_match.group(1)
    if kind is None and service_interfaces and class_name in service_interfaces and class_match.group().startswith("interface"):
        kind = "service"
    if kind is None:
        return [], []
    class_line = stripped_text[: class_match.start()].count("\n") + 1

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    fields = _fields(stripped_text)
    masked = _mask_java(stripped_text)
    methods = _method_bodies(stripped_text)

    if kind == "controller":
        mappings = _mappings(stripped_text, diagnostics, rel_path)
        if re.search(r"@RequestMapping\b", masked[:class_match.start()]) and not any(item["start"] < class_match.start() for item in mappings):
            return [], []  # 클래스 경로가 미해소면 하위 경로도 확정하지 않는다.
        class_mapping = next((item for item in mappings if item["start"] < class_match.start()), {})
        prefixes = class_mapping.get("paths", [""])
        for index, mapping in enumerate(mappings):
            if mapping["start"] < class_match.start():
                continue
            limit = mappings[index + 1]["start"] if index + 1 < len(mappings) else len(masked)
            method = next((item for item in methods if mapping["end"] <= item["start"] < limit), None)
            if method is None:
                _diagnostic(diagnostics, "unsupported-mapping", rel_path, text.count("\n", 0, mapping["start"]) + 1, "매핑된 메서드 본문을 확인하지 못했습니다.")
                continue
            method_name = method["name"]
            body_start, body_end = method["body_start"], method["body_end"]
            # Spring RequestMethodsRequestCondition.combine은 명시 메서드의 합집합이다.
            verbs = (set(class_mapping.get("verbs", [])) | set(mapping["verbs"])) - {"ANY"}
            routes = sorted({f"{verb} {(prefix.rstrip('/') + '/' + route.lstrip('/')) if prefix and route else (prefix + route or '/')}"
                             for prefix in prefixes for route in mapping["paths"] for verb in (verbs or {"ANY"})})
            node = _node("api", rel_path, method_name, f"{class_name}.{method_name}", text.count("\n", 0, mapping["start"]) + 1, routes[0])
            node["symbol"] = f"{class_name}.{method_name}"
            node["routes"] = routes
            # 오버로드된 진입점도 별도 노드로 보존한다.
            if any(item["id"] == node["id"] for item in nodes):
                node["id"] += "-" + str(node["evidence"][0]["line"])
            nodes.append(node)
            edges.extend(_collaborator_edges(node["id"], fields, stripped_text[body_start:body_end], body_start, stripped_text, rel_path,
                                            parameters=method["parameters"], diagnostics=diagnostics))
    else:
        nodes.append(_node(kind, rel_path, class_name, class_name, class_line))
        nodes[0]["declaration"] = "interface" if class_match.group().startswith("interface") else "class"
        declaration_end = stripped_text.find("{", class_match.end())
        implemented = re.search(r"\bimplements\s+([\w.,\s]+)", stripped_text[class_match.end():declaration_end])
        nodes[0]["implements"] = [name.strip().split(".")[-1] for name in implemented.group(1).split(",")] if implemented else []
        source = nodes[0]["id"]
        for method in methods:
            start, end = method["body_start"], method["body_end"]
            edges.extend(_collaborator_edges(source, fields, stripped_text[start:end], start, stripped_text, rel_path,
                                            parameters=method["parameters"], diagnostics=diagnostics))
        called_types = {edge["target"] for edge in edges}
        edges.extend(_collaborator_edges(source, [field for field in fields if field[0] not in called_types], "", 0,
                                        stripped_text, rel_path, dependencies=True))

    return nodes, edges


def _merge_service_impls(
    nodes: list[dict[str, Any]], raw_edges: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """서비스 인터페이스와 구현체(`{X}` / `{X}Impl`)를 하나의 노드로 합친다.

    eGov·Spring 관례상 컨트롤러는 인터페이스를 주입받고 실제 로직은 `{X}Impl`에
    있다. 스캐너는 파일 단위로 노드를 만들기 때문에 둘은 원래 서로 다른 노드이고
    그 사이에는 엣지가 없다 - 합치지 않으면 컨트롤러가 가리키는 인터페이스는
    막다른 길이 되고, 구현체가 호출하는 저장소 쪽은 컨트롤러에서 닿지 않는 별개의
    덩어리로 남아 체인이 끊긴다.

    살아남는 노드는 인터페이스(`{X}`)다 - ID가 안정적이고 컨트롤러가 필드 타입으로
    가리키는 대상이다. 라벨이 같은 이름의 서비스 노드가 둘 이상이면(패키지가 다른
    동명 클래스) 어느 쌍인지 확정할 수 없으므로 합치지 않는다 - `_disambiguate`와
    같은 원칙("a missing edge is safe, a wrongly wired one is silent corruption")이다.
    """
    service_nodes = [n for n in nodes if n["kind"] == "service"]
    by_label: dict[str, list[dict[str, Any]]] = {}
    for node in service_nodes:
        by_label.setdefault(node["label"], []).append(node)

    id_map: dict[str, str] = {}
    label_map: dict[str, str] = {}
    implementors: dict[str, list[dict[str, Any]]] = {}
    for node in service_nodes:
        for interface in node.get("implements", []):
            implementors.setdefault(interface, []).append(node)
    for node in sorted(service_nodes, key=lambda n: n["id"]):
        label = node["label"]
        if len(by_label[label]) != 1:
            continue
        declared = [name for name in node.get("implements", []) if name in by_label and len(implementors.get(name, [])) == 1]
        if len(declared) == 1:
            interface_label = declared[0]
        elif not node.get("implements") and label.endswith("Impl"):
            interface_label = label[:-len("Impl")]
        else:
            continue
        candidates = by_label.get(interface_label)
        if not candidates or len(candidates) != 1:
            continue  # 짝이 되는 인터페이스가 없거나 이름이 겹친다 - 지어내지 않는다
        interface_node = candidates[0]
        if interface_node.get("declaration") == "class":
            continue
        interface_node["evidence"] = sorted(
            interface_node["evidence"] + node["evidence"],
            key=lambda e: (e["file"], e["line"]),
        )
        id_map[node["id"]] = interface_node["id"]
        label_map[label] = interface_label

    if not id_map:
        return nodes, id_map

    def _remap(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if value in id_map:
            return id_map[value]
        return label_map.get(value, value)

    for edge in raw_edges:
        edge["source"] = _remap(edge["source"])
        edge["target"] = _remap(edge["target"])

    return [node for node in nodes if node["id"] not in id_map], id_map


def _node_dir(by_id: dict[str, dict[str, Any]], node_id: str) -> str:
    node = by_id.get(node_id)
    if node is None:
        return ""
    file = node["evidence"][0]["file"]
    return file.rsplit("/", 1)[0] if "/" in file else ""


def _disambiguate(by_id: dict[str, dict[str, Any]], candidates: list[str], source: str) -> str | None:
    """Resolve a symbol/path that may name more than one node.

    A single candidate resolves outright. Multiple candidates are narrowed to the one(s)
    sharing the source node's directory; if that still doesn't leave exactly one, the
    reference is ambiguous and must not be guessed - a missing edge is safe, a wrongly
    wired one is silent corruption.
    """
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        source_dir = _node_dir(by_id, source)
        same_dir = [c for c in candidates if _node_dir(by_id, c) == source_dir]
        return same_dir[0] if len(same_dir) == 1 else None
    return None


def _resolve_mapper_source(
    edge: dict[str, Any], dao_by_stem: dict[str, list[str]], dao_by_path: dict[str, str]
) -> str:
    """Resolve a mapper XML's edge source to the repository node it belongs to.

    eGovFrame 관례(`Board_SQL.xml` + `BoardDao.java`)는 파일명 치환만으로는 맞지 않는다 -
    매퍼의 `<mapper namespace="...">`가 실제 DAO의 완전한 클래스명을 담고 있다. 같은
    단순명(stem)의 DAO가 여러 개면(예: `com/sqi/a/BoardDAO.java`·`com/sqi/b/BoardDAO.java`)
    dao_by_stem만으로는 경로 사전순 마지막이 조용히 이긴다 - namespace의 완전한
    클래스명이 그 충돌을 가르는 정답 키다(2026-09-18 최종 리뷰 M5). 앞에서 하나로
    좁혀지면 뒤는 보지 않는다:
    1. namespace 전체를 경로로 바꿔 저장소 경로와 정확히(또는 접미사로) 일치하는 DAO
    2. 기존 `stem.replace("Mapper", "DAO")` 치환 - 후보가 둘 이상이면 고르지 않는다
    3. 원래 stem - 역시 후보가 둘 이상이면 고르지 않는다
    어느 것도 하나로 좁혀지지 않으면 지어내지 않고 원래 경로를 그대로 반환한다 -
    `_disambiguate`와 같은 원칙("a missing edge is safe, a wrongly wired one is silent
    corruption")이다. 뒤에서 `_resolve_edges`가 이를 미해소로 판정해 `unresolved_edges`에
    담는다.
    """
    namespace = edge.get("namespace")
    if namespace:
        suffix = namespace.replace(".", "/") + ".java"
        matches = {node_id for path, node_id in dao_by_path.items() if path == suffix or path.endswith("/" + suffix)}
        if len(matches) == 1:
            return next(iter(matches))
        if len(matches) > 1:
            return edge["source"]
    stem = Path(edge["source"]).stem
    for candidate_stem in (stem.replace("Mapper", "DAO"), stem):
        candidates = dao_by_stem.get(candidate_stem)
        if candidates:
            return candidates[0] if len(candidates) == 1 else edge["source"]
    return edge["source"]


def _resolve_edges(
    nodes: list[dict[str, Any]], raw_edges: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {node["id"]: node for node in nodes}
    by_symbol: dict[str, list[str]] = {}
    for node in nodes:
        by_symbol.setdefault(node["id"].split("--")[-1], []).append(node["id"])
    by_path: dict[str, list[str]] = {}
    for node in nodes:
        if node["kind"] == "api":
            for route in node.get("routes", [node.get("technical_label", "")]):
                path = route.split(" ", 1)[-1]
                if node["id"] not in by_path.setdefault(path, []):
                    by_path[path].append(node["id"])

    resolved: dict[str, dict[str, Any]] = {}
    unresolved: dict[str, dict[str, Any]] = {}
    for edge in raw_edges:
        if edge.get("resolved"):
            target = edge["target"]
        else:
            target = _disambiguate(by_id, by_symbol.get(edge["target"], []), edge["source"])
            if target is None:
                target = _disambiguate(by_id, by_path.get(edge["target"], []), edge["source"])
        source = edge["source"]
        if target is None:
            # 심볼·경로 어느 쪽으로도 대상을 찾지 못했다 - "노드가 없다"가 아니라
            # "관계를 해소하지 못했다"는 사실이므로 조용히 버리지 않고 보고한다.
            key = f"{source}->{edge['target']}:{edge['relation']}"
            unresolved[key] = {"source": source, "target": edge["target"], "relation": edge["relation"],
                               "code": "unresolved-target", "reason": "대상 심볼이 없거나 후보가 여러 개입니다.", "evidence": edge.get("evidence", [])}
            continue
        if target == source:
            continue
        # IR invariant: an edge is only emitted when both endpoints are real nodes. A
        # dangling reference (e.g. a raw file path left over from an unmatched
        # mapper-to-DAO correction) must be dropped from `edges`, but still reported.
        if source not in by_id or target not in by_id:
            key = f"{source}->{target}:{edge['relation']}"
            unresolved[key] = {"source": source, "target": target, "relation": edge["relation"],
                               "code": "unresolved-mapper-source", "reason": "SQL 매퍼에 대응하는 저장소를 확인하지 못했습니다.", "evidence": edge.get("evidence", [])}
            continue
        edge_id = f"{source}->{target}:{edge['relation']}"
        existing_evidence = resolved.get(edge_id, {}).get("evidence", [])
        evidence = existing_evidence + [item for item in edge.get("evidence", []) if item not in existing_evidence]
        resolved[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "relation": edge["relation"],
            "evidence": evidence,
            "analysis": edge.get("analysis", "static-reference"),
        }
    return [resolved[key] for key in sorted(resolved)], [unresolved[key] for key in sorted(unresolved)]


def scan(project_root: Path | str, changed_files: list[str] | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    suffixes = (".java", ".jsp", ".xml")
    if changed_files is None:
        candidates = []
        for directory, dirs, filenames in os.walk(root):
            dirs[:] = sorted(name for name in dirs if name not in EXCLUDED_DIRS
                             and not (Path(directory).name in {".claude", ".codex"} and name == "worktrees"))
            candidates.extend(Path(directory) / name for name in filenames if Path(name).suffix in suffixes)
        candidates.sort()
    else:
        candidates = [root / name for name in sorted(changed_files) if (root / name).suffix in suffixes]

    nodes: list[dict[str, Any]] = []
    node_ids_seen: set[str] = set()
    raw_edges: list[dict[str, Any]] = []
    files: dict[str, list[str]] = {}
    skipped: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    # 같은 파일을 반복해서 읽지 않고, include와 선언된 서비스 인터페이스를 먼저 색인한다.
    source_texts = {path: _read_source(path) for path in candidates if path.is_file() and not _is_excluded(path, root)}
    fragments: dict[str, tuple[str, str, int]] = {}
    service_interfaces: set[str] = set()
    for path, source_text in source_texts.items():
        if source_text is None:
            continue
        if path.suffix == ".xml":
            source_text = _strip_xml_comments(source_text)
            structure = _xml_structure(source_text)
            namespace = _MAPPER_NAMESPACE_RE.search(structure)
            for fragment in re.finditer(r'<sql\b[^>]*\bid\s*=\s*[\'"]([^\'"]+)[\'"][^>]*>(.*?)</sql>', structure, re.DOTALL | re.IGNORECASE):
                key = f"{namespace.group(1) if namespace else None}.{fragment.group(1)}"
                fragments[key] = (source_text[fragment.start(2):fragment.end(2)], _rel(path, root), source_text.count("\n", 0, fragment.start()) + 1)
        elif path.suffix == ".java":
            source_text = _strip_comments(source_text)
            if _class_kind(source_text, _rel(path, root)) == "service":
                implemented = re.search(r"\bimplements\s+([\w.,\s]+)\{", source_text)
                if implemented:
                    service_interfaces.update(name.strip().split(".")[-1] for name in implemented.group(1).split(","))

    for path in candidates:
        if not path.is_file():
            continue
        if _is_excluded(path, root):
            continue
        if path.suffix == ".jsp":
            scanned = _scan_jsp(path, root)
        elif path.suffix == ".xml":
            scanned = _scan_mapper_xml(path, root, diagnostics, fragments, source_texts.get(path))
        else:
            text = source_texts.get(path)
            if text is None:
                scanned = None
            else:
                stripped_text = _strip_comments(text)
                if _SERVLET_RE.search(stripped_text):
                    scanned = _scan_servlet(path, root, stripped_text)
                else:
                    scanned = _scan_java(path, root, diagnostics, text, service_interfaces)
        if scanned is None:
            skipped.append(_rel(path, root))
            _diagnostic(diagnostics, "unsupported-encoding", _rel(path, root), 1, "UTF-8 및 CP949로 읽지 못했습니다.")
            continue
        file_nodes, file_edges = scanned
        if not file_nodes:
            continue
        rel_path = _rel(path, root)
        files[rel_path] = sorted(node["id"] for node in file_nodes)
        # A node id (e.g. a table identified by name alone) can be produced by more than one
        # file - keep the first occurrence as the single node and let later files only add edges.
        for node in file_nodes:
            if node["id"] not in node_ids_seen:
                node_ids_seen.add(node["id"])
                nodes.append(node)
            else:
                existing = next(item for item in nodes if item["id"] == node["id"])
                existing["evidence"].extend(item for item in node["evidence"] if item not in existing["evidence"])
        raw_edges.extend(file_edges)

    nodes.sort(key=lambda node: node["id"])

    nodes, service_merge_map = _merge_service_impls(nodes, raw_edges)
    if service_merge_map:
        for rel_path, ids in files.items():
            files[rel_path] = sorted({service_merge_map.get(nid, nid) for nid in ids})

    dao_by_stem: dict[str, list[str]] = {}
    dao_by_path: dict[str, str] = {}
    for node in nodes:
        if node["kind"] == "repository":
            dao_by_stem.setdefault(node["id"].split("--")[-1], []).append(node["id"])
            dao_by_path[node["evidence"][0]["file"]] = node["id"]
    for edge in raw_edges:
        if isinstance(edge["source"], str) and edge["source"].endswith(".xml"):
            edge["source"] = _resolve_mapper_source(edge, dao_by_stem, dao_by_path)

    edges, unresolved_edges = _resolve_edges(nodes, raw_edges)

    return {
        "nodes": nodes,
        "edges": edges,
        "unresolved_edges": unresolved_edges,
        "files": dict(sorted(files.items())),
        "skipped": sorted(skipped),
        "diagnostics": diagnostics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan entrypoint chains into GX visualization candidates.")
    parser.add_argument("project_root")
    parser.add_argument("--changed-file", action="append", dest="changed_files")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = scan(args.project_root, args.changed_files)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
