/* GX IR의 방향성 관계만 투영한다. 클래스 단위 서비스/저장소를 메서드 호출 경로로 해석하지 않는다. */
(() => {
  'use strict';
  const confirmedRelations = new Set(['calls', 'requests', 'reads', 'writes']);
  const entryKinds = new Set(['api', 'screen']);
  const validId = id => typeof id === 'string' && id.length > 0;
  const sorted = values => [...values].sort();

  function project(nodes, edges, startId, includeDependencies = false) {
    const empty = () => ({nodeIds: [], edgeIds: [], directNodeIds: [], dependencyNodeIds: []});
    const byId = new Map((Array.isArray(nodes) ? nodes : [])
      .filter(node => node && validId(node.id)).map(node => [node.id, node]));
    if (!byId.has(startId)) return empty();

    const outgoing = new Map();
    for (const edge of Array.isArray(edges) ? edges : []) {
      // ID가 없거나 끝점이 끊긴 관계는 투영/하이라이트 대상을 식별할 수 없어 제외한다.
      if (!edge || !validId(edge.id) || !byId.has(edge.source) || !byId.has(edge.target)) continue;
      if (!confirmedRelations.has(edge.relation) && edge.relation !== 'depends_on') continue;
      if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
      outgoing.get(edge.source).push(edge);
    }

    const walk = withDependencies => {
      const nodeIds = new Set([startId]), edgeIds = new Set(), queue = [startId];
      for (let cursor = 0; cursor < queue.length; cursor++) {
        const source = queue[cursor], node = byId.get(source);
        // 공유 테이블과 다른 도메인의 경계 노드에서 멈춘다. 역방향 관계는 탐색하지 않는다.
        if (node.kind === 'table' || node.external_domain) continue;
        for (const edge of outgoing.get(source) || []) {
          if (edge.relation === 'depends_on' && !withDependencies) continue;
          const target = byId.get(edge.target);
          // 화면을 선택했을 때 그 화면의 직접 요청 API는 기능의 진입점으로 포함한다.
          const screenRequest = source === startId && node.kind === 'screen'
            && edge.relation === 'requests' && target.kind === 'api';
          if (target.id !== startId && entryKinds.has(target.kind) && !screenRequest) continue;
          edgeIds.add(edge.id);
          if (!nodeIds.has(target.id)) {
            nodeIds.add(target.id);
            queue.push(target.id);
          }
        }
      }
      return {nodeIds, edgeIds};
    };

    // 'direct'는 한 단계 이웃이 아니라 타입 의존을 거치지 않은 전체 도달 집합이다.
    const direct = walk(false);
    const selected = includeDependencies === true ? walk(true) : direct;
    const dependencies = [...selected.nodeIds].filter(id => !direct.nodeIds.has(id));
    return {
      nodeIds: sorted(selected.nodeIds),
      edgeIds: sorted(selected.edgeIds),
      directNodeIds: sorted(direct.nodeIds),
      dependencyNodeIds: sorted(dependencies),
    };
  }

  globalThis.GXFeatureGraph = Object.freeze({project});
})();
