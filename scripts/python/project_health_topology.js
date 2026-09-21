'use strict';
const byId = id => document.getElementById(id);
let topology = null;

function endpoint(edge, side) {
  const nested = edge && edge[side];
  if (nested && typeof nested === 'object') return {kind: nested.type || nested.kind || '', id: nested.id};
  return {
    kind: (edge && (edge[side + '_type'] || edge[side + '_kind'])) || '',
    id: edge && (edge[side + '_id'] !== undefined ? edge[side + '_id'] : edge[side])
  };
}

function nodeRows(state) {
  const nodes = (state && state.nodes) || {};
  return []
    .concat((nodes.source_blocks || []).map(x => Object.assign({kind: 'source_block'}, x)))
    .concat((nodes.requirements || []).map(x => Object.assign({kind: 'requirement'}, x)))
    .concat((nodes.capabilities || []).map(x => Object.assign({kind: 'capability'}, x)))
    .concat((nodes.tasks || []).map(x => Object.assign({kind: 'task'}, x)))
    .concat((nodes.acceptance || []).map(x => Object.assign({kind: 'acceptance'}, x)));
}

function nodeId(row) {
  return row.block_id || row.source_block_id || row.requirement_id || row.semantic_id ||
    row.capability_id || row.acceptance_id || row.task_id || row.taskmaster_id || row.id || '(unnamed)';
}

function currentMode() {
  return byId('topology-identity').value || 'main';
}

function currentWorkspaceView() {
  return byId('workspace-view')?.value || 'attempt';
}

function syncWorkspaceControls() {
  const label = byId('workspace-view-label');
  if (label) label.hidden = currentMode() !== 'workspace';
}

function focusTarget() {
  const value = new URLSearchParams(window.location.search).get('focus') || '';
  const split = value.indexOf(':');
  if (split <= 0) return null;
  return {kind: value.slice(0, split), id: value.slice(split + 1)};
}

function topologyHref(kind, id) {
  const params = new URLSearchParams({mode: currentMode(), focus: kind + ':' + id});
  if (currentMode() === 'workspace') params.set('view', currentWorkspaceView());
  return '/knowledge/topology?' + params.toString();
}

function makeTopologyLink(kind, id, label) {
  const link = document.createElement('a');
  link.href = topologyHref(kind, id);
  link.textContent = label || (kind + ':' + id);
  link.dataset.topologyKind = kind;
  link.dataset.topologyId = id;
  return link;
}

function matches(row) {
  const kind = byId('filter-kind').value;
  const state = byId('filter-state').value.toLowerCase();
  const taskStatus = byId('filter-task-status').value.toLowerCase();
  const capability = byId('filter-capability').value.toLowerCase();
  const chapter = byId('filter-chapter').value.toLowerCase();
  const source = byId('filter-source').value.toLowerCase();
  if (kind && row.kind !== kind) return false;
  const blob = JSON.stringify(row).toLowerCase();
  if (taskStatus && String(row.status || '').toLowerCase() !== taskStatus) return false;
  if (capability && !blob.includes(capability)) return false;
  if (chapter && !blob.includes(chapter)) return false;
  if (source && !blob.includes(source)) return false;
  if (state === 'unresolved' && !(row.topology_states || []).includes('unresolved')) return false;
  if (state === 'stale' && topology && topology.fresh !== false && !blob.includes('stale')) return false;
  if (state === 'orphan' && !(row.kind === 'requirement' && row.sink_resolved === false)) return false;
  return true;
}

async function openSource(row) {
  if (!topology || topology.identity?.kind !== 'main') return;
  const path = row.source_path;
  const response = await fetch('/api/knowledge/source?path=' + encodeURIComponent(path), {cache: 'no-store'});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.reason || 'Source request failed');
  if (payload.revision !== topology.identity.revision) throw new Error('Source snapshot changed; refresh topology before reading source.');
  const start = Number(row.start_line || row.line_start || row.line || 1);
  const end = Number(row.end_line || row.line_end || start);
  const lines = String(payload.content || '').split(/\r?\n/);
  byId('topology-source-title').textContent = path + ':' + start + '-' + end;
  byId('topology-source-body').textContent = lines.slice(Math.max(0, start - 1), Math.max(start, end)).join('\n');
  byId('topology-source-preview').showModal();
}

function relatedNodes(row) {
  const id = nodeId(row);
  const result = [];
  const add = (kind, value) => {
    if (value == null) return;
    const key = kind + ':' + value;
    if (!result.some(item => item.key === key)) result.push({key, kind, id: String(value)});
  };
  if (row.kind === 'requirement') {
    (row.source_block_ids || []).forEach(value => add('source_block', value));
    (row.capability_ids || []).forEach(value => add('capability', value));
  } else if (row.kind === 'capability') {
    (row.requirement_ids || row.covers || []).forEach(value => add('requirement', value));
  } else if (row.kind === 'task') {
    const trace = topology?.task_trace?.[String(id)] || {};
    (trace.source_blocks || []).forEach(value => add('source_block', value));
    (trace.requirements || []).forEach(value => add('requirement', value));
    (trace.capabilities || []).forEach(value => add('capability', value));
    (trace.acceptance || []).forEach(value => add('acceptance', value));
  } else if (row.kind === 'acceptance') {
    add('task', row.task_id);
  } else if (row.kind === 'source_block') {
    (topology?.nodes?.requirements || [])
      .filter(req => (req.source_block_ids || []).map(String).includes(String(id)))
      .forEach(req => add('requirement', nodeId(Object.assign({kind: 'requirement'}, req))));
  }
  (topology?.edges || []).forEach(edge => {
    const source = endpoint(edge, 'source');
    const target = endpoint(edge, 'target');
    if (String(source.id) === String(id) && source.kind === row.kind) add(target.kind, target.id);
    if (String(target.id) === String(id) && target.kind === row.kind) add(source.kind, source.id);
  });
  return result.filter(item => item.id && item.id !== '(unnamed)');
}

function addNodeActions(detail, row) {
  if (row.kind === 'source_block' && row.source_path) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = topology?.identity?.kind === 'main' ? 'Open source at this revision' : 'Workspace source preview unavailable';
    button.disabled = topology?.identity?.kind !== 'main';
    button.onclick = () => openSource(row).catch(error => byId('topology-status').textContent = error.message);
    detail.append(button);
  }
  const taskId = row.kind === 'task' ? nodeId(row) : row.task_id;
  if (taskId && taskId !== '(unnamed)') {
    const link = document.createElement('a');
    link.href = '/api/knowledge/task?id=' + encodeURIComponent(taskId);
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = row.kind === 'acceptance' ? 'Open owning task detail' : 'Open existing task detail';
    detail.append(link);
  }
  const related = relatedNodes(row);
  if (related.length) {
    const nav = document.createElement('p');
    nav.className = 'topology-related';
    nav.append(document.createTextNode('Related: '));
    related.forEach((item, index) => {
      if (index) nav.append(document.createTextNode(' · '));
      nav.append(makeTopologyLink(item.kind, item.id, item.kind + ':' + item.id));
    });
    detail.append(nav);
  }
}

function render() {
  const status = byId('topology-status');
  const host = byId('topology-nodes');
  const summary = byId('topology-summary');
  const edgeBody = byId('topology-edge-body');
  host.replaceChildren();
  summary.replaceChildren();
  edgeBody.replaceChildren();
  const identity = (topology && topology.identity) || {};
  if (topology && topology.available) {
    const viewLabel = identity.kind === 'workspace' ? ' · ' + (topology.workspace_view || currentWorkspaceView()) : '';
    status.textContent = (identity.kind || 'unknown') + ' · ' + (identity.revision || 'no revision') + viewLabel + ' · ' + (topology.status || '');
  } else {
    status.textContent = (identity.kind || 'unknown') + ' · ' + ((topology && topology.reason) || 'topology unavailable');
  }
  Object.entries((topology && topology.summary) || {}).forEach(([key, value]) => {
    const card = document.createElement('span');
    card.className = 'metric';
    card.textContent = key + ': ' + value;
    summary.append(card);
  });
  const focus = focusTarget();
  let focusElement = null;
  nodeRows(topology).filter(matches).forEach(row => {
    const detail = document.createElement('details');
    const id = nodeId(row);
    detail.dataset.topologyKind = row.kind;
    detail.dataset.topologyId = id;
    const title = document.createElement('summary');
    title.textContent = row.kind + ' · ' + id;
    const pre = document.createElement('pre');
    pre.textContent = JSON.stringify(row, null, 2);
    detail.append(title, pre);
    addNodeActions(detail, row);
    if (focus && focus.kind === row.kind && String(focus.id) === String(id)) {
      detail.open = true;
      detail.classList.add('topology-focus');
      focusElement = detail;
    }
    host.append(detail);
  });
  if (!host.children.length) {
    const p = document.createElement('p');
    p.textContent = topology && topology.available ? 'No nodes match the filters.' : 'No topology artifacts are available for this identity.';
    host.append(p);
  }
  ((topology && topology.edges) || []).forEach(edge => {
    const a = endpoint(edge, 'source');
    const b = endpoint(edge, 'target');
    const tr = document.createElement('tr');
    [a.kind + ':' + a.id, edge.relation || edge.type || '', b.kind + ':' + b.id].forEach(value => {
      const td = document.createElement('td');
      td.textContent = String(value == null ? '' : value);
      tr.append(td);
    });
    edgeBody.append(tr);
  });
  byId('topology-problems').textContent = JSON.stringify((topology && topology.problems) || [], null, 2);
  if (focusElement) focusElement.scrollIntoView({block: 'center'});
}

async function load() {
  const params = new URLSearchParams(window.location.search);
  const requestedMode = params.get('mode');
  if (requestedMode === 'main' || requestedMode === 'workspace') byId('topology-identity').value = requestedMode;
  const requestedView = params.get('view');
  if (requestedView === 'attempt' || requestedView === 'stable' || requestedView === 'stabilized') byId('workspace-view').value = requestedView;
  syncWorkspaceControls();
  const mode = currentMode();
  const view = currentWorkspaceView();
  const query = new URLSearchParams({mode});
  if (mode === 'workspace') query.set('view', view);
  const response = await fetch('/api/knowledge/topology?' + query.toString(), {cache: 'no-store'});
  topology = await response.json();
  if (!response.ok) throw new Error(topology.reason || 'Topology request failed');
  render();
}

['filter-kind','filter-state','filter-task-status','filter-capability','filter-chapter','filter-source']
  .forEach(id => byId(id).addEventListener('input', render));
byId('topology-identity').addEventListener('change', () => {
  syncWorkspaceControls();
  load().catch(e => byId('topology-status').textContent = e.message);
});
byId('workspace-view').addEventListener('change', () => load().catch(e => byId('topology-status').textContent = e.message));
byId('topology-refresh').onclick = () => load().catch(e => byId('topology-status').textContent = e.message);
load().catch(e => byId('topology-status').textContent = e.message);
