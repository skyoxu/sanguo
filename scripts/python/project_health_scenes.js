'use strict';
const el = id => document.getElementById(id);
let graphState = null;
let activeView = 'graph';

const dictionaryDescription = (path, fallback = '') => graphState?.data_dictionary?.entries?.[path]?.description || fallback;
const nodeCategory = type => {
  const groups = {
    'Containers': ['Container', 'BoxContainer', 'MarginContainer', 'CenterContainer', 'GridContainer', 'FlowContainer', 'ScrollContainer', 'PanelContainer', 'SplitContainer', 'TabContainer'],
    'Display': ['Label', 'RichTextLabel', 'TextureRect', 'ColorRect', 'ProgressBar', 'TextureProgressBar', 'Line2D'],
    'Interaction': ['Button', 'TextureButton', 'OptionButton', 'MenuButton', 'ItemList', 'Tree', 'CodeEdit', 'Slider'],
    'Dialogs and menus': ['Popup', 'Dialog', 'FileDialog', 'Window'],
    'Audio and timing': ['AudioStream', 'Timer'],
    'Base and layout': ['Node', 'Control', 'CanvasLayer']
  };
  return Object.entries(groups).find(([, names]) => names.some(name => type === name || type.includes(name)))?.[0] || 'Other';
};

function nodeButton(path, classification, click) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `scene-node ${classification === 'confirmed-reachable' ? 'scene-effective' : 'scene-possible'}`;
  button.textContent = path.split('/').pop();
  button.title = path;
  button.dataset.scenePath = path;
  button.setAttribute('aria-label', path);
  button.addEventListener('click', click);
  return button;
}

function resourceLink(path) {
  const link = document.createElement('a');
  link.textContent = path;
  link.title = path;
  link.target = '_blank';
  link.rel = 'noopener';
  if (/\.(png|jpe?g|webp|svg|gif)$/i.test(path)) {
    link.href = `/api/knowledge/image?path=${encodeURIComponent(path)}&revision=${encodeURIComponent(graphState?.revision || '')}`;
  } else {
    link.href = `/api/knowledge/source?path=${encodeURIComponent(path)}`;
  }
  return link;
}

function referenceKind(reference) {
  const target = reference.target || '';
  const suffix = target.split('.').pop()?.toLowerCase();
  if (reference.kind === 'config-reference') return 'Configuration files';
  if (suffix === 'tscn') return 'Scene files';
  if (['gd', 'cs'].includes(suffix)) return 'Dispatched scripts';
  if (['png', 'jpg', 'jpeg', 'webp', 'svg', 'gif', 'wav', 'ogg', 'mp3'].includes(suffix)) return 'Assets';
  return 'Other referenced files';
}

function appendReferenceTree(host, source, depth = 0, visited = new Set()) {
  if (visited.has(source)) return;
  if (depth > 2) {
    const truncated = document.createElement('p');
    truncated.className = 'scene-reference-truncated';
    truncated.textContent = 'More dependencies not expanded.';
    truncated.title = source;
    host.append(truncated);
    return;
  }
  const nextVisited = new Set(visited); nextVisited.add(source);
  const references = [...(graphState?.edges || []), ...(graphState?.code_references || [])]
    .filter(edge => edge.source === source && edge.target)
    .reduce((map, edge) => map.set(edge.target, edge), new Map());
  if (!references.size) return;
  const groups = new Map();
  for (const [target, reference] of references) {
    const kind = referenceKind(reference);
    if (!groups.has(kind)) groups.set(kind, []);
    groups.get(kind).push([target, reference]);
  }
  for (const [kind, entries] of groups) {
    const group = document.createElement('details');
    group.open = kind !== 'Assets';
    const summary = document.createElement('summary'); summary.textContent = `${kind} (${entries.length})`; group.append(summary);
    for (const [target, reference] of entries) {
      const item = document.createElement('p'); item.append(resourceLink(target)); item.title = target; group.append(item);
      const description = dictionaryDescription(target, '') || reference.dictionary?.description;
      if (description) {
        const note = document.createElement('p'); note.className = 'scene-dictionary-description'; note.textContent = `Data dictionary: ${description}`; group.append(note);
      }
      if (['.gd', '.cs'].includes(target.slice(target.lastIndexOf('.')).toLowerCase())) {
        const nested = document.createElement('details'); nested.open = true;
        const nestedSummary = document.createElement('summary'); nestedSummary.textContent = `Dispatches from ${target.split('/').pop()}`; nested.append(nestedSummary);
        appendReferenceTree(nested, target, depth + 1, nextVisited);
        group.append(nested);
      }
    }
    host.append(group);
  }
}

function showDetail(path) {
  const scene = graphState?.nodes?.[path];
  if (!scene) return;
  el('scene-detail-title').textContent = path.split('/').pop();
  el('scene-detail-title').title = path;
  const body = el('scene-detail-body'); body.replaceChildren();
  const summary = document.createElement('p');
  summary.textContent = `${scene.description || 'Godot scene'} · ${scene.classification || 'unknown'}`;
  body.append(summary);
  const meaning = document.createElement('p');
  meaning.className = 'scene-dictionary-description';
  meaning.textContent = `Data dictionary: ${dictionaryDescription(path, 'No dictionary description available.')}`;
  body.append(meaning);
  const functional = scene.functional_summary || {};
  if (functional.scripts?.length) {
    const heading = document.createElement('h3'); heading.textContent = `Attached scripts (${functional.scripts.length})`; body.append(heading);
    functional.scripts.forEach(script => {
      const details = document.createElement('details'); details.open = true;
      const title = document.createElement('summary'); title.textContent = script; title.title = script; details.append(title);
      const note = document.createElement('p'); note.className = 'scene-dictionary-description'; note.textContent = dictionaryDescription(script, 'No dictionary description available.'); details.append(note);
      appendReferenceTree(details, script);
      body.append(details);
    });
  }
  if (functional.events?.length) {
    const heading = document.createElement('h3'); heading.textContent = 'Published events'; body.append(heading);
    functional.events.forEach(event => {
      const p = document.createElement('p'); p.textContent = event; body.append(p);
      const description = functional.event_descriptions?.[event];
      if (description) { const note = document.createElement('p'); note.className = 'scene-dictionary-description'; note.textContent = `Data dictionary: ${description}`; body.append(note); }
    });
  }
  if (functional.functions?.length) {
    const details = document.createElement('details'); const heading = document.createElement('summary');
    heading.textContent = `Functions (${functional.functions.length})`; details.append(heading);
    functional.functions.forEach(name => {
      const p = document.createElement('p'); p.textContent = name; details.append(p);
      const description = functional.function_descriptions?.[name];
      if (description) { const note = document.createElement('p'); note.className = 'scene-dictionary-description'; note.textContent = `Data dictionary: ${description}`; details.append(note); }
    });
    body.append(details);
  }
  if (scene.knowledge_context?.length) {
    const heading = document.createElement('h3'); heading.textContent = 'Knowledge task links'; body.append(heading);
    const verified = scene.knowledge_context.filter(item => item.level === 'verified');
    const candidates = scene.knowledge_context.filter(item => item.level !== 'verified');
    [...verified, ...candidates.slice(0, 10)].forEach(item => {
      const p = document.createElement('p');
      p.className = item.level === 'verified' ? 'scene-evidence-effective' : 'scene-evidence-possible';
      p.textContent = `Task ${item.task_id}: ${item.title} · ${item.level}`;
      p.title = item.witness || item.source || item.evidence || '';
      body.append(p);
    });
    if (candidates.length > 10) { const note = document.createElement('p'); note.textContent = `${candidates.length - 10} additional candidate task links are hidden.`; body.append(note); }
  }
  if (scene.nodes?.length) {
    const heading = document.createElement('h3'); heading.textContent = `Nodes (${scene.nodes.length})`; body.append(heading);
    const grouped = new Map();
    scene.nodes.forEach(node => { const key = nodeCategory(node.type || ''); if (!grouped.has(key)) grouped.set(key, []); grouped.get(key).push(node); });
    for (const [category, nodes] of grouped) {
      const group = document.createElement('details'); group.className = 'scene-node-category';
      const groupTitle = document.createElement('summary'); groupTitle.textContent = `${category} (${nodes.length})`; group.append(groupTitle);
      nodes.forEach(node => {
        const details = document.createElement('details'); const label = document.createElement('summary');
        label.textContent = `${node.parent || '.'}/${node.name || '(unnamed)'} (${node.type || 'inherited'})`; details.append(label);
        const nodeKey = `${path}::${node.parent || '.'}/${node.name || '(unnamed)'}`;
        const nodeMeaning = document.createElement('p'); nodeMeaning.className = 'scene-dictionary-description'; nodeMeaning.textContent = dictionaryDescription(nodeKey, 'No dictionary description available.'); details.append(nodeMeaning);
        if (node.instance) { const p = document.createElement('p'); p.textContent = 'Instanced scene: '; p.append(resourceLink(node.instance)); details.append(p); }
        [...new Set(node.resources || [])].filter(item => !item.startsWith('SubResource(')).forEach(resource => {
          const p = document.createElement('p'); p.append(resourceLink(resource)); details.append(p);
          const description = dictionaryDescription(resource, '');
          if (description) { const note = document.createElement('p'); note.className = 'scene-dictionary-description'; note.textContent = `Data dictionary: ${description}`; details.append(note); }
        });
        if (node.parse_error) { const p = document.createElement('p'); p.textContent = `Parse issue: ${node.parse_error}`; details.append(p); }
        group.append(details);
      });
      body.append(group);
    }
  }
  const outgoing = (graphState.edges || []).filter(edge => edge.source === path);
  if (outgoing.length) {
    const heading = document.createElement('h3'); heading.textContent = 'Scene relations'; body.append(heading);
    outgoing.forEach(edge => {
      const p = document.createElement('p');
      p.className = edge.evidence_level === 'effective' ? 'scene-evidence-effective' : 'scene-evidence-possible';
      p.textContent = `${edge.target.split('/').pop()} · ${edge.evidence_level || 'possible'} · ${edge.kind || 'reference'}`;
      p.title = edge.evidence || edge.target;
      body.append(p);
    });
  }
  el('scene-detail').showModal();
}

function renderTree(graph) {
  const host = el('scene-graph'); host.replaceChildren();
  if (!graph.main_scene || !graph.nodes?.[graph.main_scene]) {
    host.textContent = 'No configured main scene is available in the current scan.'; return;
  }
  const children = new Map();
  for (const edge of graph.edges || []) {
    if (!graph.nodes?.[edge.target]) continue;
    if (!children.has(edge.source)) children.set(edge.source, []);
    children.get(edge.source).push(edge);
  }
  const expanded = new Set();
  function draw(path, ancestry = new Set(), edge = null) {
    const row = document.createElement('div'); row.className = 'scene-tree-node';
    const classification = edge?.evidence_level === 'possible' ? 'unreachable-candidate' : graph.nodes[path]?.classification;
    row.append(nodeButton(path, classification, () => showDetail(path)));
    if (ancestry.has(path)) { const cycle = document.createElement('span'); cycle.textContent = ' cycle'; row.append(cycle); return row; }
    if (expanded.has(path)) { const shared = document.createElement('span'); shared.textContent = ' shared'; row.append(shared); return row; }
    expanded.add(path);
    const next = new Set(ancestry); next.add(path);
    const list = [...(children.get(path) || [])].sort((a, b) => (a.evidence_level === 'effective' ? 0 : 1) - (b.evidence_level === 'effective' ? 0 : 1) || a.target.localeCompare(b.target));
    if (list.length) {
      const branch = document.createElement('div'); branch.className = 'scene-tree-children';
      const seen = new Set();
      for (const relation of list) {
        if (seen.has(relation.target)) continue; seen.add(relation.target);
        branch.append(draw(relation.target, next, relation));
      }
      row.append(branch);
    }
    return row;
  }
  host.append(draw(graph.main_scene));
}

const graphHost = el('scene-graph');
const structureHost = document.createElement('div');
structureHost.id = 'scene-structure';
structureHost.hidden = true;
graphHost.parentNode.insertBefore(structureHost, graphHost.nextSibling);
const structureToolbar = document.createElement('div');
structureToolbar.className = 'scene-composition-toolbar';
structureToolbar.hidden = true;
const includeUnreachable = document.createElement('input'); includeUnreachable.type = 'checkbox'; includeUnreachable.id = 'include-unreachable';
const includeUnreachableLabel = document.createElement('label'); includeUnreachableLabel.htmlFor = 'include-unreachable'; includeUnreachableLabel.textContent = ' Include resources not found by route tree';
const includeUnreachableHelp = document.createElement('span'); includeUnreachableHelp.className = 'field-help'; includeUnreachableHelp.textContent = 'Include resources outside the route tree.';
const structureType = document.createElement('select'); structureType.setAttribute('aria-label', 'Resource type');
[['scene','Scenes'],['script','Scripts'],['config','Configuration files'],['image','Images'],['audio','Audio'],['other','Other assets'],['all','All resources']].forEach(([value,label]) => { const option = document.createElement('option'); option.value = value; option.textContent = label; structureType.append(option); });
const firstPage = document.createElement('button'); firstPage.type = 'button'; firstPage.textContent = 'First';
const previousPage = document.createElement('button'); previousPage.type = 'button'; previousPage.textContent = 'Previous';
const nextPage = document.createElement('button'); nextPage.type = 'button'; nextPage.textContent = 'Next';
const lastPage = document.createElement('button'); lastPage.type = 'button'; lastPage.textContent = 'Last';
const pageInput = document.createElement('input'); pageInput.type = 'number'; pageInput.min = '1'; pageInput.value = '1'; pageInput.setAttribute('aria-label', 'Page number'); pageInput.style.width = '5em';
const pageInfo = document.createElement('span'); pageInfo.className = 'scene-composition-page-info';
structureToolbar.append(structureType, includeUnreachable, includeUnreachableLabel, includeUnreachableHelp, firstPage, previousPage, pageInput, nextPage, lastPage, pageInfo);
structureHost.parentNode.insertBefore(structureToolbar, structureHost);
const graphButton = document.createElement('button'); graphButton.type = 'button'; graphButton.textContent = 'Scene route tree'; graphButton.setAttribute('aria-pressed', 'true');
const structureButton = document.createElement('button'); structureButton.type = 'button'; structureButton.textContent = 'Scene composition'; structureButton.setAttribute('aria-pressed', 'false');
el('scene-refresh').parentNode.insertBefore(structureButton, el('scene-refresh'));
el('scene-refresh').parentNode.insertBefore(graphButton, structureButton);
let structurePage = 1;
const structurePageSize = 20;

function compositionResources() {
  const resources = new Map();
  const add = (path, type, meta = {}) => {
    if (!path || /^SubResource\(/.test(path) || /^ExtResource\(/.test(path)) return;
    const existing = resources.get(path);
    const mergedTasks = [...(existing?.tasks || []), ...(meta.tasks || [])];
    const origins = [...(existing?.origins || []), ...(meta.origins || [])];
    resources.set(path, {...existing, path, type: existing?.type || type, ...meta, origins: [...new Set(origins)], tasks: [...new Map(mergedTasks.map(task => [task.id + ':' + (task.relation || ''), task])).values()]});
  };
  const dictionary = graphState?.data_dictionary?.entries || {};
  const taskByPath = new Map();
  for (const [script, links] of Object.entries(graphState?.script_task_context || {})) {
    taskByPath.set(script, links.map(link => ({id: String(link.task_id), relation: link.relation, level: link.level, scene: link.scene})));
  }
  for (const scene of Object.values(graphState?.nodes || {})) {
    for (const entry of scene.knowledge_context || []) {
      if (entry.task_id) taskByPath.set(scene.path, [...(taskByPath.get(scene.path) || []), {id: String(entry.task_id), relation: 'direct-scene', level: entry.level}]);
    }
  }
  for (const scene of Object.values(graphState?.nodes || {})) {
    if (!includeUnreachable.checked && scene.classification !== 'confirmed-reachable') continue;
    add(scene.path, 'scene', {nodes: scene.nodes?.length || 0, scripts: scene.functional_summary?.scripts?.length || 0, tasks: taskByPath.get(scene.path) || [], origins: [scene.classification === 'confirmed-reachable' ? 'route tree' : 'unreachable candidate']});
    for (const script of scene.functional_summary?.scripts || []) add(script, 'script', {tasks: taskByPath.get(scene.path) || [], origins: ['attached to scene']});
    for (const config of scene.functional_summary?.config_references || []) add(config, 'config', {tasks: taskByPath.get(scene.path) || [], origins: ['scene script reference']});
    for (const node of scene.nodes || []) {
      for (const resource of node.resources || []) {
        const suffix = resource.split('.').pop()?.toLowerCase();
        const type = ['png','jpg','jpeg','webp','svg','gif'].includes(suffix) ? 'image' : ['wav','ogg','mp3'].includes(suffix) ? 'audio' : ['json','csv','cfg','ini','yaml','yml','tres','res'].includes(suffix) ? 'config' : 'other';
        add(resource, type, {tasks: taskByPath.get(scene.path) || [], origins: ['node resource']});
      }
    }
  }
  const referencesBySource = new Map();
  for (const ref of graphState?.code_references || []) {
    if (!ref.source || !ref.target) continue;
    if (!referencesBySource.has(ref.source)) referencesBySource.set(ref.source, []);
    referencesBySource.get(ref.source).push(ref);
  }
  const pending = [...resources.values()].filter(item => item.type === 'script').map(item => item.path);
  const visitedSources = new Set();
  while (pending.length) {
    const source = pending.shift();
    if (visitedSources.has(source)) continue;
    visitedSources.add(source);
    for (const ref of referencesBySource.get(source) || []) {
      const suffix = ref.target.split('.').pop()?.toLowerCase();
      const type = ['gd','cs'].includes(suffix) ? 'script' : ['json','csv','cfg','ini','yaml','yml','tres','res'].includes(suffix) ? 'config' : ['png','jpg','jpeg','webp','svg','gif'].includes(suffix) ? 'image' : ['wav','ogg','mp3'].includes(suffix) ? 'audio' : 'other';
      add(ref.target, type, {origins: [ref.classification === 'dynamic-candidate' ? 'dynamic candidate' : 'script reference']});
      if (type === 'script') pending.push(ref.target);
    }
  }
  const reachableFiles = new Set(resources.keys());
  for (const path of graphState?.file_manifest || []) {
    const suffix = path.split('.').pop()?.toLowerCase();
    const type = suffix === 'tscn' ? 'scene' : ['gd','cs'].includes(suffix) ? 'script' : ['json','csv','cfg','ini','yaml','yml','tres','res'].includes(suffix) ? 'config' : ['png','jpg','jpeg','webp','svg','gif'].includes(suffix) ? 'image' : ['wav','ogg','mp3'].includes(suffix) ? 'audio' : 'other';
    if (['scene','script','config','image','audio','other'].includes(type) && !/[{}]/.test(path) && !/log/i.test(path) && (includeUnreachable.checked || reachableFiles.has(path))) add(path, type, {origins: ['file manifest']});
  }
  for (const item of resources.values()) {
    item.tasks = item.tasks || taskByPath.get(item.path) || [];
    item.description = dictionary[item.path]?.description || `Indexed ${item.type} resource ${item.path.split('/').pop()}; available from the local project snapshot.`;
    item.confidence = item.origins?.includes('route tree') ? 'confirmed' : item.origins?.includes('dynamic candidate') ? 'candidate' : item.origins?.includes('file manifest') ? 'unconfirmed' : 'inferred';
  }
  return [...resources.values()].sort((a, b) => a.path.localeCompare(b.path));
}

function renderStructure() {
  const all = compositionResources();
  const type = structureType.value;
  const filtered = type === 'all' ? all : all.filter(item => item.type === type);
  const pages = Math.max(1, Math.ceil(filtered.length / structurePageSize));
  structurePage = Math.min(Math.max(1, structurePage), pages);
  pageInput.value = structurePage;
  pageInfo.textContent = `Page ${structurePage} / ${pages} · ${filtered.length} resources`;
  structureHost.replaceChildren();
  const scroll = document.createElement('div'); scroll.className = 'table-scroll';
  const table = document.createElement('table'); table.className = 'scene-composition-table';
  const header = document.createElement('thead'); header.innerHTML = '<tr><th>Name</th><th>Type</th><th>Details</th><th>Source</th><th>Confidence</th><th>Task IDs</th><th>Data dictionary</th></tr>'; table.append(header);
  const tbody = document.createElement('tbody');
  const start = (structurePage - 1) * structurePageSize;
  for (const item of filtered.slice(start, start + structurePageSize)) {
    const row = document.createElement('tr'); row.dataset.resourcePath = item.path; row.dataset.resourceType = item.type; row.title = item.path;
    const name = document.createElement('td'); const label = document.createElement('button'); label.type = 'button'; label.textContent = item.path.split('/').pop(); label.title = item.path;
    if (item.type === 'scene') label.onclick = () => showDetail(item.path);
    else if (item.type === 'image') label.onclick = () => window.open(`/api/knowledge/image?path=${encodeURIComponent(item.path)}&revision=${encodeURIComponent(graphState?.revision || '')}`, '_blank', 'noopener');
    else label.onclick = () => window.open(`/api/knowledge/source?path=${encodeURIComponent(item.path)}`, '_blank', 'noopener');
    name.append(label);
    const kind = document.createElement('td'); kind.textContent = item.type;
    const meta = document.createElement('td'); meta.textContent = item.nodes !== undefined ? `${item.nodes} nodes · ${item.scripts || 0} scripts` : '';
    const origin = document.createElement('td'); origin.textContent = (item.origins || []).join(', ');
    const confidence = document.createElement('td'); confidence.textContent = item.confidence;
    const tasks = document.createElement('td'); const taskLinks = item.tasks || []; const verified = taskLinks.filter(task => task.level === 'verified'); const candidates = taskLinks.filter(task => task.level !== 'verified'); const shown = [...verified, ...candidates.slice(0, 3)];
    tasks.textContent = shown.map(task => `${task.id} (${task.relation === 'scene-inherited' ? 'inherited' : task.level || 'candidate'})`).join(', ') || '-';
    if (candidates.length > 3) tasks.title = `${candidates.length - 3} additional candidate task links are hidden.`;
    const description = document.createElement('td'); description.textContent = item.description;
    row.append(name, kind, meta, origin, confidence, tasks, description); tbody.append(row);
  }
  table.append(tbody); scroll.append(table); structureHost.append(scroll);
  if (!filtered.length) structureHost.textContent = 'No resources in this category.';
  firstPage.disabled = previousPage.disabled = structurePage <= 1;
  nextPage.disabled = lastPage.disabled = structurePage >= pages;
}

function setView(view) {
  activeView = view;
  const graphVisible = view === 'graph';
  graphHost.hidden = !graphVisible;
  structureHost.hidden = graphVisible;
  structureToolbar.hidden = graphVisible;
  graphButton.setAttribute('aria-pressed', String(graphVisible));
  structureButton.setAttribute('aria-pressed', String(!graphVisible));
  if (!graphVisible) renderStructure();
}

async function loadGraph() {
  const response = await fetch('/api/knowledge/scene-graph');
  const graph = await response.json();
  if (!response.ok) throw new Error(graph.reason || 'Unable to load scene graph');
  graphState = graph;
  renderTree(graph);
  if (activeView === 'structure') renderStructure();
  const confirmed = Object.values(graph.nodes || {}).filter(item => item.classification === 'confirmed-reachable').length;
  const possible = (graph.edges || []).filter(item => item.evidence_level === 'possible').length;
  el('scene-status').textContent = `${Object.keys(graph.nodes || {}).length} scenes · ${confirmed} confirmed reachable · ${possible} possible relations · revision ${graph.revision || 'snapshot'}`;
  const requested = new URLSearchParams(location.search).get('scene');
  if (requested && graph.nodes?.[requested]) showDetail(requested);
}

async function restartProbe() {
  el('scene-status').textContent = 'Restarting deterministic main probe…';
  const session = await (await fetch('/api/knowledge/session')).json();
  const response = await fetch('/api/knowledge/scan', {
    method: 'POST', headers: {'Content-Type': 'application/json', 'Origin': location.origin, 'X-Project-Health-Token': session.token}, body: '{}'
  });
  if (!response.ok) throw new Error('Project Health scan failed');
  await loadGraph();
}

graphButton.onclick = () => setView('graph');
structureButton.onclick = () => { structurePage = 1; setView('structure'); };
structureType.onchange = () => { structurePage = 1; renderStructure(); };
firstPage.onclick = () => { structurePage = 1; renderStructure(); };
previousPage.onclick = () => { structurePage -= 1; renderStructure(); };
nextPage.onclick = () => { structurePage += 1; renderStructure(); };
lastPage.onclick = () => { structurePage = Number.MAX_SAFE_INTEGER; renderStructure(); };
pageInput.onchange = () => { structurePage = Math.max(1, Number(pageInput.value) || 1); renderStructure(); };
includeUnreachable.onchange = () => { structurePage = 1; renderStructure(); };
el('scene-refresh').onclick = () => loadGraph().catch(error => { el('scene-status').textContent = error.message; });
el('scene-probe').onclick = () => restartProbe().catch(error => { el('scene-status').textContent = error.message; });
el('scene-detail-close').onclick = () => el('scene-detail').close();
loadGraph().catch(error => { el('scene-status').textContent = error.message; });
