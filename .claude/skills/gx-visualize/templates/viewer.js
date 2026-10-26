(() => {
  const root = document.documentElement;
  let theme = 'light';
  try { theme = localStorage.getItem('archify-theme') || 'light'; } catch (_) {}
  const requestedTheme = new URLSearchParams(location.search).get('theme');
  if (requestedTheme === 'light' || requestedTheme === 'dark') theme = requestedTheme;
  root.dataset.theme = theme === 'dark' ? 'dark' : 'light';
  const updateTheme = () => {
    document.querySelectorAll('[data-gx-theme]').forEach(button => {
      button.textContent = root.dataset.theme === 'dark' ? '밝은 테마로' : '어두운 테마로';
      button.setAttribute('aria-label', button.textContent);
    });
    try { localStorage.setItem('archify-theme', root.dataset.theme); } catch (_) {}
  };
  document.querySelectorAll('[data-gx-theme]').forEach(button => button.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; updateTheme();
  }));
  new MutationObserver(updateTheme).observe(root, {attributes: true, attributeFilter: ['data-theme']});
  updateTheme();
  const search = document.querySelector('#gx-node-search');
  const rows = [...document.querySelectorAll('[data-gx-search]')];
  const filter = () => {
    const query = search.value.trim().toLocaleLowerCase();
    rows.forEach(row => { row.hidden = !row.textContent.toLocaleLowerCase().includes(query); });
    const count = rows.filter(row => !row.hidden).length;
    document.querySelector('[data-gx-result]').textContent = `${count}개 구성 요소`;
    document.querySelector('[data-gx-empty]').hidden = count !== 0;
  };
  if (search) search.addEventListener('input', filter);
  const detailPrefix = 'gx-detail-';
  const detailTarget = id => {
    const target = document.getElementById(id);
    return target?.matches('article.node-card') ? target : null;
  };
  const reveal = () => {
    let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    // 이전 공유 링크도 상세로 연결한다. 같은 ID의 Archify SVG를 대상으로 잡지 않는다.
    if (id.startsWith('node-')) {
      const canonical = detailPrefix + id.slice('node-'.length);
      if (detailTarget(canonical)) {
        id = canonical;
        history.replaceState(null, '', location.pathname + location.search + '#' + encodeURIComponent(id));
      }
    }
    if (!id.startsWith(detailPrefix)) return;
    const target = detailTarget(id);
    if (!target) return;
    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    if (search) { search.value = ''; filter(); }
    target.scrollIntoView({block: 'start'}); target.focus({preventScroll: true});
  };
  window.addEventListener('hashchange', reveal); reveal();
  // 기존 Archify 캔버스의 탐색 기능은 유지하며 노드 더블클릭으로 동일한 근거 목록에 연결한다.
  document.querySelectorAll('[data-node-id]').forEach(node => node.addEventListener('dblclick', () => {
    const id = detailPrefix + node.dataset.nodeId;
    if (detailTarget(id)) {
      location.hash = encodeURIComponent(id);
      reveal();
    }
  }));
  let scale = 1;
  document.querySelectorAll('[data-gx-zoom]').forEach(button => button.addEventListener('click', () => {
    const svg = document.querySelector('.gx-diagram-scroll svg');
    if (!svg) return;
    scale = button.dataset.gxZoom === 'reset' ? 1 : Math.max(.75, Math.min(3, scale + Number(button.dataset.gxZoom)));
    const width = Number(svg.getAttribute('viewBox')?.split(/\s+/)[2]) || 640;
    svg.style.width = `${Math.max(640, width) * scale}px`;
    document.querySelector('[data-gx-scale]').textContent = `${Math.round(scale * 100)}%`;
  }));

  const featureRoot = document.getElementById('gx-features');
  const dataElement = document.getElementById('gx-feature-data');
  if (!featureRoot || !dataElement || !globalThis.GXFeatureGraph) return;
  let data;
  try { data = JSON.parse(dataElement.textContent); } catch (_) { return; }
  const nodes = new Map(data.nodes.map(node => [node.id, node]));
  const edges = new Map(data.edges.map(edge => [edge.id, edge]));
  const featureButtons = [...featureRoot.querySelectorAll('[data-gx-feature]')];
  const featureSearch = featureRoot.querySelector('#gx-feature-search');
  const dependencies = featureRoot.querySelector('#gx-feature-dependencies');
  const flow = featureRoot.querySelector('.gx-feature-flow');
  const inspector = featureRoot.querySelector('[data-gx-feature-detail]');
  const relations = {calls:'호출', requests:'요청', reads:'조회', writes:'저장', depends_on:'타입 의존'};
  const kinds = [['api','API·화면'], ['service','서비스'], ['repository','저장소·매퍼'], ['table','테이블']];
  let selectedFeature = null;
  let selectedNode = null;
  let projection = null;
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const label = node => node.label || node.symbol || node.id;
  const projectedEdges = () => projection.edgeIds.map(id => edges.get(id)).filter(Boolean);
  const appendEvidence = (parent, html) => {
    // evidence_html은 프로젝트 경로 검증과 HTML 이스케이프를 거친 생성기 출력이다.
    const template = document.createElement('template');
    template.innerHTML = html;
    parent.append(template.content.cloneNode(true));
  };
  const focusButton = (node, text) => {
    const button = element('button', 'gx-code-link', text || label(node));
    button.type = 'button'; button.dataset.gxFocus = node.id;
    button.addEventListener('click', () => showNode(node.id));
    return button;
  };
  const edgeRow = edge => {
    const row = element('li');
    row.append(focusButton(nodes.get(edge.source)), document.createTextNode(' → '),
      focusButton(nodes.get(edge.target)), document.createTextNode(' · ' + (relations[edge.relation] || edge.relation)));
    if (edge.evidence_html) {
      const detail = element('details');
      detail.append(element('summary', '', '연결의 코드 근거'));
      appendEvidence(detail, edge.evidence_html); row.append(detail);
    }
    return row;
  };
  function showNode(id) {
    if (!projection.nodeIds.includes(id) || !nodes.has(id)) return;
    selectedNode = id;
    flow.querySelectorAll('[data-gx-focus]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.gxFocus === id)));
    inspector.replaceChildren();
    const original = detailTarget(detailPrefix + id);
    if (original) {
      const copy = original.cloneNode(true);
      copy.removeAttribute('id');
      copy.querySelectorAll('[id]').forEach(node => node.removeAttribute('id'));
      copy.querySelectorAll('h4').forEach(heading => {
        if (heading.nextElementSibling?.tagName === 'UL') heading.nextElementSibling.remove();
        heading.remove();
      });
      copy.querySelectorAll('details').forEach(detail => {
        if (detail.querySelector(':scope > summary')?.textContent === '내부 ID') detail.remove();
        else detail.open = true;
      });
      inspector.append(copy);
    } else inspector.append(element('h4', '', label(nodes.get(id))));
    const neighbors = projectedEdges().filter(edge => edge.source === id || edge.target === id);
    if (neighbors.length) {
      inspector.append(element('h4', '', '선택 범위 안의 연결'));
      const list = element('ul', 'gx-feature-edge-list');
      neighbors.forEach(edge => list.append(edgeRow(edge))); inspector.append(list);
    }
    featureRoot.dispatchEvent(new CustomEvent('gx:code-selected', {detail:{id}}));
  }
  function renderFlow() {
    flow.replaceChildren();
    const dependencyIds = new Set(projection.dependencyNodeIds);
    const firstTargets = new Set(projectedEdges().filter(edge => edge.source === selectedFeature).map(edge => edge.target));
    const visibleNodes = projection.nodeIds.map(id => nodes.get(id));
    kinds.forEach(([kind, title]) => {
      const lane = element('div', 'gx-feature-lane');
      const members = visibleNodes.filter(node => kind === 'api' ? ['api','screen'].includes(node.kind) : node.kind === kind)
        .sort((a,b) => label(a).localeCompare(label(b)));
      lane.append(element('h4', '', `${title} · ${members.length}`));
      if (!members.length) lane.append(element('p', 'gx-feature-lane-empty', '추출된 연결 없음'));
      const list = element('ul');
      members.forEach((node, index) => {
        const row = element('li');
        if (index >= 5) row.hidden = true;
        const button = focusButton(node);
        button.className = 'gx-feature-node gx-kind-' + (kinds.some(([value]) => value === node.kind) ? node.kind : 'api');
        button.setAttribute('aria-pressed', String(node.id === selectedNode));
        if (dependencyIds.has(node.id)) button.append(element('small', '', '타입 의존 후보'));
        else if (node.id !== selectedFeature && !firstTargets.has(node.id)) button.append(element('small', '', '클래스 단위 연결'));
        if (node.external_domain) button.append(element('small', '', '다른 도메인 · ' + node.external_domain));
        if (kind === 'table') {
          const operations = new Set(projectedEdges().filter(edge => edge.target === node.id).map(edge => relations[edge.relation]).filter(Boolean));
          if (operations.size) button.append(element('small', '', [...operations].join(' · ')));
        }
        row.append(button); list.append(row);
      });
      lane.append(list);
      if (members.length > 5) {
        const more = element('button', 'gx-feature-more', `나머지 ${members.length - 5}개 보기`);
        more.type = 'button'; more.setAttribute('aria-expanded','false');
        more.addEventListener('click', () => {
          const expand = more.getAttribute('aria-expanded') !== 'true';
          [...list.children].slice(5).forEach(row => { row.hidden = !expand; });
          more.setAttribute('aria-expanded', String(expand));
          more.textContent = expand ? '접기' : `나머지 ${members.length - 5}개 보기`;
        });
        lane.append(more);
      }
      flow.append(lane);
    });
  }
  function selectFeature(id, share = true) {
    if (!data.features.includes(id)) return false;
    selectedFeature = id;
    projection = globalThis.GXFeatureGraph.project(data.nodes, data.edges, id, dependencies.checked);
    const candidates = dependencies.checked ? projection.dependencyNodeIds.length
      : globalThis.GXFeatureGraph.project(data.nodes, data.edges, id, true).dependencyNodeIds.length;
    featureRoot.querySelector('[data-gx-feature-dependency-label]').textContent = candidates
      ? `타입 의존성 후보도 포함 · 추가 ${candidates}개` : '타입 의존성 후보도 포함';
    featureButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.gxFeature === id)));
    const node = nodes.get(id);
    featureRoot.querySelector('[data-gx-feature-title]').textContent = label(node);
    featureRoot.querySelector('[data-gx-feature-route]').textContent = [...new Set([node.technical_label, ...(node.routes || [])].filter(Boolean))].join(' · ');
    featureRoot.querySelector('[data-gx-feature-count]').textContent = projection.edgeIds.length
      ? `관련 구성 요소 ${projection.nodeIds.length}개 · 추출된 연결 ${projection.edgeIds.length}개`
      : '추출된 후속 연결이 없습니다. 아래 코드 근거를 확인하세요.';
    selectedNode = projection.nodeIds.includes(selectedNode) ? selectedNode : id;
    renderFlow();
    const list = element('ul', 'gx-feature-edge-list');
    projectedEdges().forEach(edge => list.append(edgeRow(edge)));
    featureRoot.querySelector('[data-gx-feature-connections]').replaceChildren(list);
    showNode(selectedNode);
    if (share) history.replaceState(null, '', location.pathname + location.search + '#' + encodeURIComponent('gx-feature-' + id));
    return true;
  }
  const selectHash = () => {
    let hash; try { hash = decodeURIComponent(location.hash.slice(1)); } catch (_) { return false; }
    return hash.startsWith('gx-feature-') && selectFeature(hash.slice('gx-feature-'.length), false);
  };
  featureButtons.forEach(button => button.addEventListener('click', () => { selectedNode = null; selectFeature(button.dataset.gxFeature); }));
  featureSearch.addEventListener('input', () => {
    const query = featureSearch.value.trim().toLocaleLowerCase();
    featureButtons.forEach(button => {
      const node = nodes.get(button.dataset.gxFeature);
      const text = [button.textContent, node.symbol, ...(node.routes || [])].filter(Boolean).join(' ').toLocaleLowerCase();
      button.closest('li').hidden = !text.includes(query);
    });
    const count = featureButtons.filter(button => !button.closest('li').hidden).length;
    featureRoot.querySelector('[data-gx-feature-search-count]').textContent = `${count}개 API·화면`;
    featureRoot.querySelector('[data-gx-feature-empty]').hidden = count !== 0;
  });
  dependencies.addEventListener('change', () => selectFeature(selectedFeature));
  window.addEventListener('hashchange', selectHash);
  if (!selectHash()) selectFeature(data.features[0], false);
  document.querySelectorAll('a[href="#gx-full-map"]').forEach(link => link.addEventListener('click', () => {
    const map = document.getElementById('gx-full-map'); if (map) map.open = true;
  }));
  document.querySelectorAll('.gx-full-map').forEach(map => map.addEventListener('toggle', () => {
    if (map.open) requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
  }));
  const collapseMaps = () => requestAnimationFrame(() => requestAnimationFrame(() => {
    let target; try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) {}
    document.querySelectorAll('[data-gx-collapse-on-ready]').forEach(map => {
      if (!target || !map.contains(target)) map.open = false;
    });
  }));
  if (document.readyState === 'complete') collapseMaps();
  else window.addEventListener('load', collapseMaps, {once:true});
})();
