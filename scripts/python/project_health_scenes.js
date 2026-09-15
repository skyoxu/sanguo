'use strict';
const el = id => document.getElementById(id);
let graphState = null;

function nodeButton(path, classification, click) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `scene-node ${classification === 'confirmed-reachable' ? 'scene-effective' : 'scene-possible'}`;
  button.textContent = path.split('/').pop();
  button.title = path;
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

function showDetail(path) {
  const scene = graphState?.nodes?.[path];
  if (!scene) return;
  el('scene-detail-title').textContent = path.split('/').pop();
  el('scene-detail-title').title = path;
  const body = el('scene-detail-body'); body.replaceChildren();
  const summary = document.createElement('p');
  summary.textContent = `${scene.description || 'Godot scene'} · ${scene.classification || 'unknown'}`;
  body.append(summary);
  const functional = scene.functional_summary || {};
  if (functional.scripts?.length) {
    const heading = document.createElement('h3'); heading.textContent = 'Attached scripts'; body.append(heading);
    functional.scripts.forEach(script => { const p = document.createElement('p'); p.append(resourceLink(script)); body.append(p); });
  }
  if (functional.events?.length) {
    const heading = document.createElement('h3'); heading.textContent = 'Published events'; body.append(heading);
    functional.events.forEach(event => { const p = document.createElement('p'); p.textContent = event; body.append(p); });
  }
  if (functional.functions?.length) {
    const details = document.createElement('details'); const heading = document.createElement('summary');
    heading.textContent = `Functions (${functional.functions.length})`; details.append(heading);
    functional.functions.forEach(name => { const p = document.createElement('p'); p.textContent = name; details.append(p); }); body.append(details);
  }
  if (scene.knowledge_context?.length) {
    const heading = document.createElement('h3'); heading.textContent = 'Knowledge task links'; body.append(heading);
    scene.knowledge_context.forEach(item => {
      const p = document.createElement('p');
      p.className = item.level === 'verified' ? 'scene-evidence-effective' : 'scene-evidence-possible';
      p.textContent = `Task ${item.task_id}: ${item.title} · ${item.level}`;
      p.title = item.witness || item.source || item.evidence || '';
      body.append(p);
    });
  }
  if (scene.nodes?.length) {
    const heading = document.createElement('h3'); heading.textContent = `Nodes (${scene.nodes.length})`; body.append(heading);
    scene.nodes.forEach(node => {
      const details = document.createElement('details'); const label = document.createElement('summary');
      label.textContent = `${node.parent || '.'}/${node.name || '(unnamed)'} (${node.type || 'inherited'})`; details.append(label);
      if (node.instance) { const p = document.createElement('p'); p.textContent = 'Instanced scene: '; p.append(resourceLink(node.instance)); details.append(p); }
      [...new Set(node.resources || [])].filter(path => !path.startsWith('SubResource(')).forEach(path => { const p = document.createElement('p'); p.append(resourceLink(path)); details.append(p); });
      body.append(details);
    });
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
    const key = edge.source;
    if (!children.has(key)) children.set(key, []);
    children.get(key).push(edge);
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

async function loadGraph() {
  const response = await fetch('/api/knowledge/scene-graph');
  const graph = await response.json();
  if (!response.ok) throw new Error(graph.reason || 'Unable to load scene graph');
  graphState = graph;
  renderTree(graph);
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

el('scene-refresh').onclick = () => loadGraph().catch(error => { el('scene-status').textContent = error.message; });
el('scene-probe').onclick = () => restartProbe().catch(error => { el('scene-status').textContent = error.message; });
el('scene-detail-close').onclick = () => el('scene-detail').close();
loadGraph().catch(error => { el('scene-status').textContent = error.message; });
