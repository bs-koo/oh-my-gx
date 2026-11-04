"""대화·문서에서 추출한 intake의 질문과 간결한 인계를 정규화한다.

자연어 추출, 승인 판정, 원장 수정은 수행하지 않는다. 호출자가 근거를 읽어
분류한 입력만 받으며, 승인·위임 근거는 실제 사용자 메시지를 가리켜야 한다.
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path


CONSEQUENTIAL = {"scope", "behavior", "architecture", "acceptance", "removal"}


def normalize_intake(payload):
    """누락된 중요 결정만 질문으로 남기고 원문 대신 원장 포인터를 돌려준다."""
    approval = deepcopy(payload.get("approval", {"status": "unconfirmed", "source": None}))
    if approval.get("status") not in {"approved", "unconfirmed"}:
        raise ValueError("approval.status: approved 또는 unconfirmed가 필요합니다")
    if approval["status"] == "approved" and not approval.get("source"):
        raise ValueError("approval.source: 실제 사용자 승인 근거가 필요합니다")

    decisions = deepcopy(payload.get("decisions", []))
    pending = {}
    grounded_answers = {}

    def keep_pending(item):
        topic = item["topic"]
        if topic not in pending:
            pending[topic] = deepcopy(item)
            return
        previous = pending[topic]
        previous["blocking"] = bool(previous.get("blocking") or item.get("blocking"))
        if item.get("impact") in CONSEQUENTIAL:
            previous["impact"] = item["impact"]
        if item.get("reason"):
            previous["reason"] = item["reason"]
        sources = []
        for value in (previous.get("source"), item.get("source")):
            for source in value if isinstance(value, list) else [value]:
                if source is not None and source not in sources:
                    sources.append(source)
        if sources:
            previous["source"] = sources[0] if len(sources) == 1 else sources

    for item in payload.get("unresolved", []):
        candidate = deepcopy(item)
        candidate.setdefault("blocking", candidate.get("impact") in CONSEQUENTIAL)
        keep_pending(candidate)
    for decision in decisions:
        impact = decision.get("impact", "metadata")
        if impact not in CONSEQUENTIAL | {"metadata"}:
            raise ValueError(f"알 수 없는 decision impact: {impact}")
        status = decision.get("status", "unresolved")
        if status not in {"explicit", "inferred", "unresolved"}:
            raise ValueError(f"알 수 없는 decision status: {status}")
        has_value = decision.get("value") not in (None, "", "❓")
        grounded = status == "explicit" and has_value and bool(decision.get("source"))
        delegated = (status == "inferred" and has_value
                     and bool(decision.get("delegation-source")) and impact != "removal")
        if grounded:
            grounded_answers.setdefault(decision["topic"], []).append(decision)
            continue
        if delegated:
            continue
        keep_pending({
            "topic": decision["topic"], "impact": impact,
            "blocking": impact in CONSEQUENTIAL, "source": decision.get("source"),
        })

    for topic, answers in grounded_answers.items():
        if all(answer["value"] == answers[0]["value"] for answer in answers):
            pending.pop(topic, None)
            continue
        impacts = [answer.get("impact", "metadata") for answer in answers]
        keep_pending({
            "topic": topic,
            "impact": next((impact for impact in impacts if impact in CONSEQUENTIAL), "metadata"),
            "blocking": any(impact in CONSEQUENTIAL for impact in impacts),
            "source": [answer["source"] for answer in answers],
            "reason": "conflicting explicit decisions",
        })
    unresolved = list(pending.values())

    requirements = []
    observations = deepcopy(payload.get("observed-facts", []))
    for item in payload.get("requirements", []):
        origin = item.get("origin")
        if origin == "code":
            observations.append(deepcopy(item))
            continue
        if origin not in {"document", "conversation"}:
            raise ValueError("requirement.origin: document, conversation 또는 code가 필요합니다")
        requirements.append({key: deepcopy(item[key]) for key in ("domain", "path", "section", "ids")})

    return {
        "schema-version": 1,
        **{key: deepcopy(payload[key]) for key in ("run-id", "goal", "intent", "stop-at", "sources")},
        "decisions": decisions,
        "approval": approval,
        "unresolved": unresolved,
        "questions": [deepcopy(item) for item in unresolved if item["blocking"]],
        "requirements": requirements,
        "observed-facts": observations,
        "context-paths": deepcopy(payload.get("context-paths", [])),
        "plan-file": payload.get("plan-file"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 intake JSON 파일")
    parser.add_argument("--output", type=Path, help="UTF-8 인계 JSON 파일")
    args = parser.parse_args()
    result = normalize_intake(json.loads(args.input.read_text(encoding="utf-8")))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
