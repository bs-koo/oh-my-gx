#!/usr/bin/env python3
"""외부 명령을 실행하지 않고 의존성 JSON의 완전성과 분석 점수를 판정한다."""

import argparse
import json
import sys


TOOLS = ("npm-outdated", "npm-audit", "pip-outdated", "pip-audit", "cargo-audit")
WEIGHTS = {"CRITICAL": 15, "HIGH": 5, "MEDIUM": 2, "LOW": 1}


def result(status, reason, findings=None):
    return {"status": status, "findings": findings, "reason": reason}


def require(condition):
    if not condition:
        raise ValueError("정상 결과 스키마가 아니거나 결과가 불완전합니다")


def strings(item, *fields):
    return isinstance(item, dict) and all(isinstance(item.get(field), str) and item[field]
                                          for field in fields)


def error_detail(value):
    return ((isinstance(value, str) and bool(value.strip())) or
            (isinstance(value, dict) and any(strings(value, field)
                                            for field in ("code", "message", "summary", "detail"))))


def classify(tool, stdout, exit_code, timed_out=False):
    if timed_out:
        return result("timeout", "시간초과로 수집된 결과는 확정하지 않습니다")
    try:
        payload = json.loads(stdout, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except ValueError:
        return result("error", "stdout가 비었거나 완전한 JSON이 아닙니다")
    outdated_packages = (tool == "npm-outdated" and isinstance(payload, dict) and
                         all(strings(item, "wanted", "latest") for item in payload.values()))
    if isinstance(payload, dict) and not outdated_packages:
        if payload.get("error"):
            return result("error", json.dumps(payload["error"], ensure_ascii=False))
        errors = payload.get("errors")
        partial_errors = (error_detail(errors) or
                          (isinstance(errors, list) and bool(errors) and all(error_detail(item) for item in errors)))
        if partial_errors or payload.get("partial") is True:
            return result("partial", "도구가 일부 조회 실패 또는 부분 결과를 보고했습니다")
        partial = payload.get("partial")
        if (errors is not None and errors != []) or (partial is not None and partial is not False):
            return result("error", "알 수 없는 오류/부분 결과 객체 형상입니다")
    if exit_code not in (0, 1):
        return result("error", f"분석 결과로 인정하지 않는 종료코드: {exit_code}")
    try:
        if tool == "npm-outdated":
            require(isinstance(payload, dict))
            require(all(strings(item, "wanted", "latest") for item in payload.values()))
            count = len(payload)
        elif tool == "npm-audit":
            require(isinstance(payload, dict))
            if payload.get("auditReportVersion") not in (None, 2):
                return result("unsupported", "npm auditReportVersion 2만 검증합니다")
            require(payload.get("auditReportVersion") == 2)
            entries = payload.get("vulnerabilities")
            metadata = payload.get("metadata", {}).get("vulnerabilities", {})
            require(isinstance(entries, dict) and isinstance(metadata, dict))
            require(type(metadata.get("total")) is int and metadata["total"] == len(entries))
            require(all(strings(item, "name", "severity") and isinstance(item.get("via"), list)
                        and isinstance(item.get("nodes"), list) for item in entries.values()))
            count = len(entries)
        elif tool == "pip-outdated":
            require(isinstance(payload, list))
            require(all(strings(item, "name", "version", "latest_version") for item in payload))
            count = len(payload)
        elif tool == "pip-audit":
            require(isinstance(payload, dict) and isinstance(payload.get("dependencies"), list))
            entries = payload["dependencies"]
            if any(isinstance(item, dict) and item.get("skip_reason") for item in entries):
                return result("partial", "감사에서 제외된 의존성이 있습니다")
            require(all(strings(item, "name", "version") and isinstance(item.get("vulns"), list)
                        and all(strings(vuln, "id") for vuln in item["vulns"]) for item in entries))
            count = sum(len(item["vulns"]) for item in entries)
        elif tool == "cargo-audit":
            require(isinstance(payload, dict) and isinstance(payload.get("vulnerabilities"), dict))
            entries = payload["vulnerabilities"]
            count = entries.get("count")
            require(type(count) is int and count >= 0 and isinstance(entries.get("list"), list))
            require(count == len(entries["list"]) and type(entries.get("found")) is bool)
            require(entries["found"] == (count > 0))
            require(all(isinstance(item, dict) and strings(item.get("advisory"), "id")
                        and strings(item.get("package"), "name", "version") for item in entries["list"]))
        else:
            return result("unsupported", "검증하지 않는 도구입니다")
        if exit_code and (not count or tool == "pip-outdated"):
            return result("error", "발견 없는 비정상 종료를 정상 빈 결과로 취급하지 않습니다")
        return result("complete", "검증된 스키마 안에서 정상 결과", count)
    except (ValueError, TypeError, AttributeError):
        return result("error", "정상 결과 스키마가 아니거나 결과가 불완전합니다")


def health(payload):
    require(isinstance(payload, dict) and isinstance(payload.get("statuses"), dict)
            and isinstance(payload.get("severities"), list))
    statuses = payload["statuses"]
    require(all(isinstance(name, str) and isinstance(status, str) for name, status in statuses.items()))
    require(all(severity in WEIGHTS for severity in payload["severities"]))
    unassessed = sorted(name for name, status in statuses.items() if status != "complete")
    if not statuses or unassessed:
        return {"status": "incomplete", "score": None, "grade": None, "unassessed": unassessed}
    score = max(0, 100 - sum(WEIGHTS[severity] for severity in payload["severities"]))
    grade = next(grade for minimum, grade in ((90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "F"))
                 if score >= minimum)
    return {"status": "complete", "score": score, "grade": grade, "unassessed": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("classify")
    check.add_argument("--tool", choices=TOOLS, required=True)
    check.add_argument("--exit-code", type=int, required=True)
    check.add_argument("--timed-out", action="store_true")
    commands.add_parser("health")
    args = parser.parse_args()
    try:
        text = sys.stdin.buffer.read().decode("utf-8-sig")
        output = classify(args.tool, text, args.exit_code, args.timed_out) if args.command == "classify" else health(json.loads(text))
    except (ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(output, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
