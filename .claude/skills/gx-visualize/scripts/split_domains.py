#!/usr/bin/env python3
"""Split a GX visualization IR into one IR per domain.

실제 GX 프로젝트(kreb-grep-2025-admin, Java 456개)를 스캔하면 86노드 한 장은
Archify 검증이 109건으로 실패하고, 애초에 사람이 읽을 수도 없다. 도메인 단위로
나누면 보통 규모 모듈은 깨끗해진다(설계서 §5.7). 이 모듈은 그 분할만 담당하고,
성공/실패 판정은 도메인별 IR을 각각 Archify에 넣어보는 호출자의 몫이다.
"""

from __future__ import annotations

from typing import Any

# 계층 폴더 이름. `api`는 계층 이름이자 도메인 이름일 수 있어(예: .../gseed/api/
# controller/ApiController.java) 파일명에 가장 가까운 계층 폴더만 계층으로 소비한다.
LAYER_DIRS = ("controller", "service", "repository", "dao", "mapper", "web", "api")


def domain_of(path: str) -> str | None:
    """실제 저장소 두 곳(SEF·GSEED)에서 측정한 규칙: 계층 폴더 바로 앞 세그먼트가 도메인이다.

    파일명에 가장 가까운 계층 폴더를 찾아 그 앞 세그먼트를 반환한다. 계층 폴더가
    없거나 그 앞에 세그먼트가 없으면 파일명 바로 앞 디렉터리로 폴백한다. 특정
    저장소의 `modules/` 같은 관례에는 의존하지 않는다.
    """
    if not path:
        return None
    segments = path.split("/")
    dir_segments = segments[:-1]
    if not dir_segments:
        return None
    layer_index = None
    for index in range(len(dir_segments) - 1, -1, -1):
        if dir_segments[index] in LAYER_DIRS:
            layer_index = index
            break
    if layer_index is not None and layer_index > 0:
        return dir_segments[layer_index - 1]
    return dir_segments[-1]


def _node_domain(node: dict[str, Any]) -> str | None:
    for item in node.get("evidence", []):
        if item.get("kind") == "code" and isinstance(item.get("file"), str):
            return domain_of(item["file"])
    return None


def split_by_domain(ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """도메인별로 노드·엣지를 나눈 IR을 만든다. 반환값은 `{domain: ir}`이다.

    테이블 노드는 파일 경로가 아니라 MyBatis XML 근거를 가지므로 경로로 도메인을
    판정하면 `mybatis` 같은 가짜 도메인이 생긴다(실측: 86엣지 중 32건이 이 오분류
    때문에 교차 엣지로 잡혔다). 그래서 테이블 노드는 스스로 도메인을 갖지 않고,
    자신을 참조하는 엣지를 따라 그 상대 노드가 속한 모든 도메인에 복제된다.

    한 도메인에 온전히 담기지 않는 엣지(양 끝의 도메인이 다름)는 조용히 지우지
    않는다 — 관련된 각 도메인 IR의 `missing_inputs`에 `"cross-domain-edge"`를
    남겨 호출자가 건수를 셀 수 있게 한다.
    """
    nodes = ir.get("nodes", [])
    edges = ir.get("edges", [])
    nodes_by_id = {node["id"]: node for node in nodes}
    table_ids = {node["id"] for node in nodes if node.get("kind") == "table"}

    node_domain: dict[str, str | None] = {
        node["id"]: _node_domain(node) for node in nodes if node["id"] not in table_ids
    }

    # 테이블마다 자신을 참조하는(읽거나 쓰는) 도메인 집합을 엣지에서 역산한다.
    table_domains: dict[str, set[str]] = {table_id: set() for table_id in table_ids}
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source in table_domains:
            domain = node_domain.get(target)
            if domain:
                table_domains[source].add(domain)
        if target in table_domains:
            domain = node_domain.get(source)
            if domain:
                table_domains[target].add(domain)

    domain_names = {domain for domain in node_domain.values() if domain}
    for domains in table_domains.values():
        domain_names.update(domains)

    members_by_domain = {
        domain: {node_id for node_id, node_domain_name in node_domain.items() if node_domain_name == domain}
        | {table_id for table_id, domains in table_domains.items() if domain in domains}
        for domain in domain_names
    }

    # 테이블 하나를 두 도메인이 함께 참조하면(실측: TB_ROLE을 user·role이 함께 읽는다)
    # 그 테이블은 두 도메인 모두에 복제된다. 이때 한쪽 도메인의 진짜 소유 엣지(예:
    # role -> TB_ROLE)가 다른 도메인(user)의 관점에서도 "한쪽 끝만 있는" 엣지로 보여
    # 실제로는 잃지 않은 엣지를 교차로 오판할 수 있다. 그래서 어느 한 도메인이라도
    # 양 끝을 온전히 담고 있으면 그 엣지는 진짜 도메인 경계를 넘은 것이 아니다.
    fully_contained = {
        edge["id"]
        for members in members_by_domain.values()
        for edge in edges
        if edge.get("source") in members and edge.get("target") in members
    }

    # scan()이 남기는 skipped(읽기 실패 파일)·unresolved_edges(관계 미해소)는 실행 순간의
    # 스캔 결과에만 있고 merge 단계가 없는 이 파이프라인에서는 도메인 IR에 옮기지 않으면
    # 그대로 사라진다 - 나중에 그 도메인 IR만 열어본 사람은 어떤 파일이 빠졌는지, 어떤
    # 관계가 해소되지 않았는지 알 수 없다(2026-09-18 최종 리뷰 M6). 두 값 모두 파일
    # 경로(스킵) 또는 소스 노드(미해소 엣지)로 도메인을 추정할 수 있으므로, 지어내지 않고
    # domain_of()로 실제 관련 있는 도메인에만 배분한다 - 무관한 도메인 IR에 전체 목록을
    # 그대로 복제하면 "이 도메인과 상관없는 진단"이 섞여 오히려 신뢰를 떨어뜨린다.
    skipped = ir.get("skipped", [])
    unresolved_edges = ir.get("unresolved_edges", [])

    def _unresolved_domain(source: Any) -> str | None:
        if not isinstance(source, str):
            return None
        if source in node_domain:
            return node_domain[source]
        return domain_of(source)

    parts: dict[str, dict[str, Any]] = {}
    for domain in sorted(domain_names):
        member_ids = members_by_domain[domain]

        domain_edges = []
        dropped: list[str] = []
        for edge in edges:
            source_in, target_in = edge.get("source") in member_ids, edge.get("target") in member_ids
            if source_in and target_in:
                domain_edges.append(edge)
            elif (source_in or target_in) and edge["id"] not in fully_contained:
                dropped.append("cross-domain-edge")

        part = {
            key: value
            for key, value in ir.items()
            if key not in ("nodes", "edges", "missing_inputs", "skipped", "unresolved_edges")
        }
        part["nodes"] = [nodes_by_id[node_id] for node_id in sorted(member_ids)]
        part["edges"] = sorted(domain_edges, key=lambda edge: edge["id"])
        part["missing_inputs"] = list(ir.get("missing_inputs", [])) + dropped
        domain_skipped = [path for path in skipped if domain_of(path) == domain]
        if domain_skipped:
            part["skipped"] = domain_skipped
        domain_unresolved = [edge for edge in unresolved_edges if _unresolved_domain(edge.get("source")) == domain]
        if domain_unresolved:
            part["unresolved_edges"] = domain_unresolved
        parts[domain] = part

    return parts
