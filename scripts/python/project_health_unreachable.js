'use strict';
const status = document.getElementById('unreachable-status');
const host = document.getElementById('unreachable-items');
const filter = document.getElementById('scene-filter');

function sceneScripts(item) {
  const fromResources = Object.values(item.external_resources || {}).filter(path => /\.(cs|gd)$/i.test(path));
  const fromSummary = item.functional_summary?.scripts || [];
  return [...new Set([...fromResources, ...fromSummary])];
}

function render(items) {
  host.replaceChildren();
  const selected = filter.value;
  const shown = items.filter(item => selected === 'all' || (selected === 'parse-error' && item.parse_error) || (selected === 'with-scripts' && sceneScripts(item).length));
  for (const item of shown) {
    const row = document.createElement('details'); row.className = 'scene-tree-row';
    const summary = document.createElement('summary');
    const link = document.createElement('a');
    link.href = `/knowledge/scenes?scene=${encodeURIComponent(item.path)}`;
    link.textContent = item.path;
    link.title = item.description || 'Static Godot scene';
    summary.append(link); row.append(summary);
    const root = (item.nodes || [])[0];
    const meta = document.createElement('p');
    meta.textContent = `${item.classification || 'unknown'} · ${root ? root.type || 'inherited' : 'no root'} · ${(item.nodes || []).length} nodes${item.parse_error ? ' · ' + item.parse_error : ''}`;
    row.append(meta);
    const scripts = sceneScripts(item);
    if (scripts.length) { const p = document.createElement('p'); p.textContent = 'Scripts: ' + scripts.join(', '); row.append(p); }
    host.append(row);
  }
  if (!shown.length) host.textContent = 'No matching unconfirmed scenes.';
}

fetch('/api/knowledge/godot/unreachable').then(async response => {
  const result = await response.json();
  if (!response.ok) throw new Error(result.reason || 'Unable to load unconfirmed scenes');
  const items = result.items || [];
  status.textContent = `${items.length} unconfirmed scenes · revision ${result.revision || 'snapshot'}`;
  filter.addEventListener('change', () => render(items));
  render(items);
}).catch(error => { status.textContent = error.message; });
