'use strict';
const status = document.getElementById('unreachable-status');
const host = document.getElementById('unreachable-items');
fetch('/api/knowledge/godot/unreachable').then(async response => {
  const result = await response.json();
  if (!response.ok) throw new Error(result.reason || 'Unable to load unconfirmed scenes');
  status.textContent = `${result.items?.length || 0} unconfirmed scenes · revision ${result.revision || 'snapshot'}`;
  host.replaceChildren();
  for (const item of result.items || []) {
    const row = document.createElement('p');
    const link = document.createElement('a');
    link.href = `/knowledge/scenes?scene=${encodeURIComponent(item.path)}`;
    link.textContent = item.path;
    link.title = item.description || item.path;
    row.append(link, document.createTextNode(` · ${item.description || 'static scene candidate'}`));
    host.append(row);
  }
  if (!result.items?.length) host.textContent = 'No unconfirmed scenes.';
}).catch(error => { status.textContent = error.message; });
