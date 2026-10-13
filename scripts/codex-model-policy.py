#!/usr/bin/env python3
"""실제 Codex 세션 capabilities에서 GX 모델 배정 계획을 계산한다."""

import argparse
import json
from pathlib import Path
import re
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ROLE_INDEX = Path(".claude/skills/gx-dev/references/codex-roles/index.json")
DEFAULT_TIERS = {
    "high": {"family": "astra", "reasoning_effort": "high"},
    "mid": {"family": "sol", "reasoning_effort": "medium"},
}
ECO_ROLES = {
    "gx-dev": {"design-critic", "coder"},
    "gx-tdd": {"design-critic", "test-architect", "reviewer"},
    "standalone": set(),
}
FAMILY_ORDER = {"high": ("astra", "sol"), "mid": ("sol", "astra")}
VERSIONED_MODEL = re.compile(r"gpt-([0-9]+(?:\.[0-9]+)*)-(astra|sol)")


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"error": message}, ensure_ascii=False))
        raise SystemExit(2)


def read_object(path: Path) -> dict:
    """BOM을 허용하되 잘못된 파일을 기본 설정으로 숨기지 않는다."""
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 객체가 필요합니다: {path}")
    return value


def nonempty_string(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label}에는 공백 없는 유효한 문자열이 필요합니다.")
    return value


def model_tiers(cwd: Path) -> tuple[dict, set[str]]:
    """소비 프로젝트의 선택적 override를 기본 티어와 합친다."""
    tiers = {tier: dict(candidate) for tier, candidate in DEFAULT_TIERS.items()}
    path = Path(cwd) / ".claude/config.json"
    if not path.exists():
        return tiers, set()
    config = read_object(path)
    codex = config.get("codex", {})
    if not isinstance(codex, dict):
        raise ValueError("config.codex는 객체여야 합니다.")
    overrides = codex.get("modelTiers", {})
    if not isinstance(overrides, dict) or set(overrides) - set(tiers):
        raise ValueError("codex.modelTiers는 high/mid 선택적 객체여야 합니다.")
    for tier, candidate in overrides.items():
        if not isinstance(candidate, dict) or set(candidate) not in (
                {"model", "reasoning_effort"}, {"family", "reasoning_effort"}):
            raise ValueError(f"codex.modelTiers.{tier}에는 model 또는 family 하나와 reasoning_effort가 필요합니다.")
        tiers[tier] = {key: nonempty_string(value, f"codex.modelTiers.{tier}.{key}")
                       for key, value in candidate.items()}
        if "family" in candidate and candidate["family"] not in {"astra", "sol"}:
            raise ValueError(f"codex.modelTiers.{tier}.family는 astra 또는 sol이어야 합니다.")
    return tiers, set(overrides)


def allowed_models(capabilities: dict) -> dict[str, list[str]]:
    models = capabilities.get("models")
    if not isinstance(models, dict):
        raise ValueError("capabilities.models는 모델명 → 허용 effort 목록 객체여야 합니다.")
    for model, efforts in models.items():
        nonempty_string(model, "capabilities 모델명")
        if not isinstance(efforts, list):
            raise ValueError(f"{model}의 허용 effort는 목록이어야 합니다.")
        for effort in efforts:
            nonempty_string(effort, f"{model} effort")
    return models


def family_candidates(family: str, models: dict, effort: str) -> list[str]:
    """실제로 허용되고 해당 effort를 지원하는 정식 계열 이름을 숫자로 정렬한다."""
    candidates = []
    for name, efforts in models.items():
        match = VERSIONED_MODEL.fullmatch(name)
        if match and match[2] == family and effort in efforts:
            version = tuple(int(part) for part in match[1].split("."))
            candidates.append((version, name))
    return [name for _, name in sorted(candidates, reverse=True)]


def select_candidate(tier: str, tiers: dict, overridden: set[str], models: dict,
                     parent_model) -> tuple[str, str, str, str]:
    """한 티어의 모델/effort 쌍을 지원 목록에서 선택한다."""
    candidate = tiers[tier]
    effort = candidate["reasoning_effort"]
    source = "project-config" if tier in overridden else "default"
    model = candidate.get("model")
    if model is not None and effort in models.get(model, []):
        return model, effort, source, f"{source} 후보 {model}/{effort}가 세션 allowlist에서 지원됨"
    family = candidate.get("family")
    if family:
        matching = family_candidates(family, models, effort)
        if matching:
            return matching[0], effort, source, f"{source} 계열 {family}의 최신 허용 모델 {matching[0]}/{effort} 선택"
    preferred = [name for fallback_family in FAMILY_ORDER[tier]
                 for name in family_candidates(fallback_family, models, effort)]
    preferred.extend([parent_model, *sorted(models)])
    replacement = next((name for name in preferred
                        if isinstance(name, str) and effort in models.get(name, [])), None)
    if replacement is None:
        raise ValueError(f"티어 {tier}의 요청 effort '{effort}'를 지원하는 허용 모델이 없습니다.")
    requested = model if model is not None else f"family:{family}"
    reason = f"{source} 후보 {requested}/{effort} 미지원: 허용 모델 {replacement}/{effort}로 대체"
    return replacement, effort, "fallback", reason


def resolve_policy(*, capabilities: dict, cwd: Path, pipeline: str, role: str,
                   profile: str = "standard", scope: str = "phase", fix_round: int = 0,
                   execution: str = "agent", plugin_root: Path = PLUGIN_ROOT) -> dict:
    """배정 요청만 반환한다. spawn 호출이나 실제 사용량 기록은 수행하지 않는다."""
    if pipeline not in ECO_ROLES or profile not in {"standard", "eco"}:
        raise ValueError("지원하지 않는 pipeline/profile입니다.")
    if scope not in {"phase", "task"} or execution not in {"agent", "session"}:
        raise ValueError("지원하지 않는 scope/execution입니다.")
    if type(fix_round) is not int or not 0 <= fix_round <= 5:
        raise ValueError("fix-round는 0~5 정수여야 합니다.")
    if not isinstance(capabilities, dict):
        raise ValueError("capabilities는 객체여야 합니다.")
    if not Path(cwd).is_dir():
        raise ValueError(f"소비 프로젝트 디렉토리가 없습니다: {cwd}")
    index = read_object(Path(plugin_root) / ROLE_INDEX)
    entry = index.get(role)
    tier = entry.get("tier") if isinstance(entry, dict) else None
    if not isinstance(tier, str) or tier not in DEFAULT_TIERS:
        raise ValueError(f"설치된 역할 index에 유효한 역할/tier가 없습니다: {role}")
    base_tier = effective_tier = tier
    reasons = [f"역할 index의 기본 티어 {base_tier}"]
    if profile == "eco" and role in ECO_ROLES[pipeline]:
        effective_tier = "mid"
        reasons.append(f"{pipeline} eco 대상 역할을 mid로 배정")
    elif profile == "eco" and role == "architect":
        reasons.append("architect는 eco에서도 high 유지")
    if pipeline == "gx-tdd" and role == "reviewer" and scope == "task":
        effective_tier = "mid"
        reasons.append("TDD 태스크 범위 reviewer는 mid")
    if pipeline == "gx-tdd" and role == "implementer" and fix_round >= 4:
        if execution == "session":
            raise ValueError("TDD implementer fix 4~5회차는 fresh agent high 격상이 필요합니다: --execution agent")
        effective_tier = "high"
        reasons.append(f"TDD implementer fix {fix_round}회차는 프로파일과 독립적으로 high 격상")

    models = allowed_models(capabilities)
    tiers, overridden = model_tiers(cwd)
    result = {
        "role": role, "pipeline": pipeline, "profile": profile, "scope": scope,
        "fix_round": fix_round, "base_tier": base_tier, "effective_tier": effective_tier,
        "execution": execution, "warnings": [],
    }
    if execution == "session":
        # 현재 부모 실행과 새 자식의 허용 모델 목록은 서로 다른 계약이다.
        model = nonempty_string(capabilities.get("parent_model"), "parent_model")
        effort = nonempty_string(capabilities.get("parent_reasoning_effort"), "parent_reasoning_effort")
        source = "parent-session"
        reasons.append("세션 직접 실행은 부모 모델/effort를 사용하며 eco로 변경되지 않음")
        result.update(fork_turns=None, spawn_args=None)
    else:
        model, effort, source, selection_reason = select_candidate(
            effective_tier, tiers, overridden, models, capabilities.get("parent_model"))
        reasons.append(selection_reason)
        other_tier = "mid" if effective_tier == "high" else "high"
        try:
            other_pair = select_candidate(other_tier, tiers, overridden, models,
                                          capabilities.get("parent_model"))[:2]
        except ValueError:
            # 현재 호출과 무관한 다른 티어 미지원은 현재 배정을 막지 않는다.
            other_pair = None
        if (model, effort) == other_pair:
            result["warnings"].append("지원 목록에서 선택된 high/mid 모델과 effort가 동일하여 티어별 모델 구분이 불가능합니다.")
        result.update(fork_turns="none", spawn_args={
            "model": model, "reasoning_effort": effort, "fork_turns": "none",
        })
    result.update(model=model, reasoning_effort=effort, source=source, reason="; ".join(reasons))
    return result


def main() -> int:
    # Windows 기본 콘솔 인코딩과 무관하게 JSON 계약은 UTF-8을 사용한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", type=Path, required=True, help="현재 세션의 실제 지원 모델 JSON")
    parser.add_argument("--cwd", type=Path, required=True, help="소비 프로젝트 루트")
    parser.add_argument("--pipeline", choices=ECO_ROLES, required=True)
    parser.add_argument("--role", required=True, help="설치된 index의 GX 역할 이름")
    parser.add_argument("--profile", choices=("standard", "eco"), default="standard")
    parser.add_argument("--scope", choices=("phase", "task"), default="phase")
    parser.add_argument("--fix-round", type=int, choices=range(6), default=0)
    parser.add_argument("--execution", choices=("agent", "session"), default="agent")
    args = parser.parse_args()
    try:
        result = resolve_policy(capabilities=read_object(args.capabilities), cwd=args.cwd,
                                pipeline=args.pipeline, role=args.role, profile=args.profile,
                                scope=args.scope, fix_round=args.fix_round, execution=args.execution)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
