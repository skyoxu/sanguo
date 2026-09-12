'use strict';
const el = id => document.getElementById(id);
const pretty = value => JSON.stringify(value, null, 2);
let token = '', currentPage = 1, operationPoll = null;
const selectedTasks = new Set();
let visibleTaskIds = [];
let activeFilter = null;
let activeTaskDetail = null;
let configLoaded = false;
async function api(path, body) {
  const response = await fetch('/api/knowledge/' + path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Project-Health-Token': token}, body: JSON.stringify(body)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.reason || 'Request failed');
  return result;
}
async function run(action) {
  setPageLocked(true, 'Starting operation…');
  el('message').textContent = 'Working… runtime verification may take several minutes.';
  try { await action(); el('message').textContent = 'Ready. Results are bound to the displayed main snapshot.'; }
  catch(error) { el('message').textContent = error.message; }
  finally { await refreshOperation(); }
}
function configLines(value) {
  return String(value || '').split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
}
const sourcePathRequirements = [
  {key:'tasks',reason:'任务定义与任务视图：用于关联任务编号、验收条件和 Gameplay 范围。',path:'.taskmaster/tasks'},
  {key:'product_requirements',reason:'产品需求：用于理解功能目标、用户价值和需求边界。',path:'docs/prd'},
  {key:'architecture_decisions',reason:'架构决策：用于解释关键技术选择、约束及其演进原因。',path:'docs/adr'},
  {key:'architecture',reason:'架构与功能设计：用于定位基础架构、Overlay 和契约说明。',path:'docs/architecture'},
  {key:'agent_rules',reason:'代理规则：用于约束自动化实施和仓库操作。',path:'docs/agents'},
  {key:'workflows',reason:'工作流：用于定位章节流程、执行协议和操作指南。',path:'docs/workflows'},
  {key:'domain_code',reason:'领域代码与契约：用于分析玩法规则和可调参数的读取链。',path:'Game.Core'},
  {key:'engine_code',reason:'引擎实现：用于关联 Godot 场景、脚本、资源和素材。',path:'Game.Godot'},
  {key:'domain_tests',reason:'领域测试：用于定位不依赖引擎的 xUnit 验收证据。',path:'Game.Core.Tests'},
  {key:'engine_tests',reason:'引擎测试：用于定位场景和引擎集成的 GdUnit4 证据。',path:'Tests.Godot'},
  {key:'project_entry',reason:'项目入口：用于了解环境要求和常用命令。',path:'README.md'},
  {key:'repository_rules',reason:'仓库路由规则：用于定位权威来源和不可协商约束。',path:'AGENTS.md'},
  {key:'delivery_profile',reason:'交付配置：用于识别当前交付模式和安全策略。',path:'DELIVERY_PROFILE.md'},
  {key:'root_workflow',reason:'完整工作流：用于理解从初始化到交付的章节关系。',path:'workflow.md'},
  {key:'testing_rules',reason:'测试规范：用于解释测试分层和质量门禁。',path:'docs/testing-framework.md'}
];
function renderSourcePathRequirements(config={}) {
  const container=el('config-source-requirements');
  container.replaceChildren(...sourcePathRequirements.map(item=>{
    const row=document.createElement('div');
    const reason=document.createElement('span'); reason.textContent=item.reason;
    const input=document.createElement('input'); input.dataset.sourceKey=item.key;
    input.value=config.source_path_bindings?.[item.key] ?? ((config.source_paths || []).includes(item.path) ? item.path : '');
    input.placeholder=item.path; input.setAttribute('aria-label',item.reason);
    input.addEventListener('input',updateConfigPreview);
    row.append(reason,input); return row;
  }));
}
function renderConfigEditor(config) {
  renderSourcePathRequirements(config);
  el('config-gdd-paths').value=(config.gdd_paths || []).join('\n');
  el('config-task-scene-bindings').value=pretty(config.task_scene_bindings || []);
  el('config-query-aliases').value=pretty(config.query_aliases || {});
  configLoaded=true; updateConfigPreview();
}
function collectConfigEditor() {
  const source_path_bindings=Object.fromEntries([...document.querySelectorAll('[data-source-key]')].map(input=>[input.dataset.sourceKey,input.value.trim()]));
  return {
    source_paths: Object.values(source_path_bindings).filter(Boolean),
    source_path_bindings,
    gdd_paths: configLines(el('config-gdd-paths').value),
    task_scene_bindings: JSON.parse(el('config-task-scene-bindings').value || '[]'),
    query_aliases: JSON.parse(el('config-query-aliases').value || '{}')
  };
}
function updateConfigPreview() {
  if(configLoaded) el('config-advanced').value=pretty(collectConfigEditor());
}
function setPageLocked(locked, message='The page is locked until the active operation finishes.') {
  el('app-main').inert = locked;
  el('operation-lock').hidden = !locked;
  el('operation-lock-message').textContent = message;
}
async function refreshOperation() {
  try {
    const state = await api('operation');
    const scope = state.task_ids?.length ? ` for task${state.task_ids.length === 1 ? '' : 's'} ${state.task_ids.join(', ')}` : '';
    setPageLocked(state.active, state.active ? `${state.action}${state.verification_mode ? ' ('+state.verification_mode+')' : ''} is running${scope}. Started ${state.started_at}.` : undefined);
    return state;
  } catch (_) { return null; }
}
function updateSelection() {
  el('selection-count').textContent = `${selectedTasks.size} task${selectedTasks.size === 1 ? '' : 's'} selected`;
  el('runtime-selected').textContent = `Verify selected on main (${selectedTasks.size})`;
  el('runtime-selected').disabled = selectedTasks.size === 0;
}
function setFilter(kind, value) {
  activeFilter = !kind || (activeFilter?.kind === kind && activeFilter?.value === value) ? null : {kind, value};
  currentPage = 1;
  el('active-filter').textContent = activeFilter ? `Filter: ${activeFilter.kind} = ${activeFilter.value}` : 'Showing all tasks';
  el('clear-filter').disabled = !activeFilter;
  return loadStatus();
}
function button(text, action) { const b = document.createElement('button'); b.type = 'button'; b.textContent = text; b.onclick = () => run(action); return b; }
function sourceLink(path, taskDetail=null) {
  const a = document.createElement('a'); a.href = '/api/knowledge/source?path=' + encodeURIComponent(path); a.textContent = path;
  a.onclick = event => {event.preventDefault(); run(async () => {
    if(!taskDetail) activeTaskDetail=null;
    const s = await api('source?path=' + encodeURIComponent(path));
    if(taskDetail && s.revision !== taskDetail.navigation.revision) throw new Error('Source snapshot changed. Reopen the task before inspecting its sources.');
    const config = taskDetail?.navigation?.configs?.find(item=>item.path===path);
    show(path + ' @ ' + s.revision.slice(0,12), config ? renderSourceContent(s.content, config) : s.content);
    if(taskDetail) el('detail-links').append(button('Back to task navigation',async()=>renderTaskDetail(taskDetail)));
  });};
  return a;
}
function renderSourceContent(content, config) {
  const lines = String(content).split('\n');
  const marked = new Set((config.confirmed_fields || config.focused_fields || []).map(field=>Number(field.line)).filter(Number.isFinite));
  const pointers = new Set((config.semantic?.parameters || []).map(p=>p.pointer || p.key).filter(p=>typeof p==='string' && p.startsWith('/')));
  const suggested = new Set((config.fields || []).filter(f=>pointers.has(f.pointer)).map(f=>Number(f.line)).filter(Number.isFinite));
  const semantic = config.semantic;
  const pre = document.createElement('pre');
  lines.forEach((line, index) => {
    const row=document.createElement('span'); row.className=marked.has(index+1)?'source-line source-line-related':suggested.has(index+1)?'source-line source-line-suggested':'source-line';
    const number=document.createElement('span'); number.className='source-line-number'; number.textContent=String(index+1).padStart(4,' ')+'  ';
    row.append(number,document.createTextNode(line)); pre.append(row,'\n');
  });
  if(semantic){const note=document.createElement('div');note.className='source-semantic-note';note.textContent=`黄色：直接关联字段（${marked.size} 行）；蓝色：模型建议且 JSON 路径精确匹配（${suggested.size} 行）。路径匹配不代表已证明任务使用该字段。`;pre.prepend(note);}
  return pre;
}
function show(title, body) { el('detail-title').textContent = title; el('detail-body').hidden=false; el('detail-body').replaceChildren(); if(body instanceof Node) el('detail-body').append(body); else el('detail-body').textContent = typeof body === 'string' ? body : pretty(body); el('detail-links').replaceChildren(); if (!el('detail').open) el('detail').showModal(); }
function imageLink(path, revision) {
  const wrapper=document.createElement('span');wrapper.className='image-reference';
  const link=document.createElement('a');link.textContent=path;
  link.href='/api/knowledge/image?path='+encodeURIComponent(path)+'&revision='+encodeURIComponent(revision);
  link.target='_blank';link.rel='noopener';link.title='Preview image';
  const preview=document.createElement('span');preview.className='image-preview';preview.hidden=true;
  const img=document.createElement('img');img.alt=path;
  const error=document.createElement('span');error.textContent='Loading image...';
  preview.append(img,error);wrapper.append(link,preview);
  const open=()=>{preview.hidden=false;if(!img.getAttribute('src')) img.src=link.href;};
  img.onload=()=>{error.hidden=true;};img.onerror=()=>{error.textContent='Preview unavailable. Check the snapshot or image size.';img.hidden=true;};
  wrapper.onmouseenter=open;wrapper.onmouseleave=()=>{preview.hidden=true;};link.onfocus=open;wrapper.onfocusout=()=>{preview.hidden=true;};
  return wrapper;
}
function configAssociationGroup(item) {
  if (item.confirmed_fields?.length || item.focused_fields?.length) return 'confirmed';
  const pointers = new Set((item.fields || []).map(field=>field.pointer));
  if ((item.semantic?.parameters || []).some(param=>pointers.has(param.pointer || param.key))) return 'suggested';
  return 'indirect';
}
function renderNavigation(nav, box=el('detail-links'), related=false) {
  const textSources = new Set(nav.text_sources || []);
  const paragraph = (parent, value) => {const p=document.createElement('p');p.textContent=value;parent.append(p);};
  const linkedPath = path => textSources.has(path) ? sourceLink(path, activeTaskDetail) : document.createTextNode(path);
  const reference = (parent, label, path, line, suffix) => {const p=document.createElement('p');p.append(label,linkedPath(path),line ? ':'+line : '',suffix);parent.append(p);};
  for (const [key, title] of [['configs','配置文件'],['code','代码'],['scenes','场景与节点'],['assets','素材'],['tests','建议验证']]) {
    const items=(nav[key] || []).filter(item=>related ? key!=='tests' && key!=='configs' && item.focus!=='core' : key==='tests' || key==='configs' || item.focus==='core');
    if(!items.length) continue;
    const section=document.createElement('div');section.className='navigation-group'; const heading=document.createElement('h3');heading.textContent=title+' ('+items.length+')';section.append(heading);box.append(section);
    const configGroups = {};
    if(key==='configs') {
      for(const [id,label,description] of [
        ['confirmed','已确认字段','存在记录 ID 直连，或同时具备语义重建与配置读取代码键链证据。'],
        ['suggested','语义建议字段','字段在文件中真实存在，任务相关性由模型推断。'],
        ['indirect','仅间接关联','已发现资源关联，但尚未确认任务专属字段；不代表已证明无关。有解析错误时请先检查错误。']
      ]) {
        const group=document.createElement('details');group.open=id!=='indirect';
        const labelNode=document.createElement('summary');
        labelNode.textContent=`${label} (${items.filter(item=>configAssociationGroup(item)===id).length})`;
        group.append(labelNode);paragraph(group,description);section.append(group);configGroups[id]=group;
      }
    }
    for (const item of items) {
      const entry=document.createElement('details');const summary=document.createElement('summary');
      if(key==='assets' && /\.(png|jpe?g|webp)$/i.test(item.path)) summary.append(imageLink(item.path,nav.revision),' · '+item.evidence_kind);
      else summary.textContent=item.path+' · '+item.evidence_kind;
      entry.append(summary);(key==='configs'?configGroups[configAssociationGroup(item)]:section).append(entry);
      if(textSources.has(item.path)) entry.append(sourceLink(item.path, activeTaskDetail));
      if(key==='configs' && configAssociationGroup(item)==='indirect') paragraph(entry,'已发现资源关联，但未确认该文件中与本任务直接相关的可调字段。');
      if(item.semantic){paragraph(entry,'功能说明（模型原文）: '+(item.semantic.explanation||''));paragraph(entry,`${key==='configs'?'调参建议':'修改建议'}（模型原文）: `+(item.semantic.modification_guidance||item.semantic.parameter_guidance||''));paragraph(entry,'修改影响（模型原文）: '+(item.semantic.modification_impact||''));
        const params=item.semantic.parameters||[]; if(params.length){paragraph(entry,'语义字段:'); for(const param of params){const pointer=String(param.pointer||param.key||''); const matched=(item.fields||[]).some(field=>String(field.pointer||'')===pointer); paragraph(entry,`${pointer} = ${pretty(param.value)} — ${param.meaning||param.description||''} · ${matched?'字段存在，任务相关性由模型推断':'未匹配字段'}`);}}
        const bindings=item.semantic.bindings||[]; if(bindings.length){paragraph(entry,key==='assets'?'素材使用位置:':'任务相关节点:');for(const binding of bindings){if(key==='assets')paragraph(entry,`${binding.source}:${binding.line} — ${binding.meaning||''} · 静态绑定已确认`);else paragraph(entry,`${binding.node_path}:${binding.line} (${binding.type||'Node'}) — ${binding.meaning||''} · 静态绑定已确认`);}}
      }
      for(const field of item.confirmed_fields || []) paragraph(entry,`${field.pointer} = ${pretty(field.value)} · line ${field.line} · ${field.confirmation==='static_record_identity'?'记录 ID 静态确认':'语义重建 + 读取代码键链确认'}`);
      if(!item.confirmed_fields) for(const field of item.focused_fields || []) paragraph(entry,`${field.pointer} = ${pretty(field.value)} · line ${field.line}`);
      if(item.parse_error) paragraph(entry,'Parse error: '+item.parse_error);
      for(const node of item.nodes || []) {
        const nodeDetails=document.createElement('details');const nodeTitle=document.createElement('summary');nodeTitle.textContent=`${node.node_path} (${node.type})`;nodeDetails.append(nodeTitle);entry.append(nodeDetails);
        if(node.instance.length) paragraph(nodeDetails,'Instance: '+pretty(node.instance));
        for(const property of node.properties) paragraph(nodeDetails,`${property.name} = ${property.value} · line ${property.line}`+(property.resources.length ? ' · '+pretty(property.resources) : ''));
      }
      if(item.command) paragraph(entry,item.command_status+': '+item.command);
      const evidence=document.createElement('details');const evidenceTitle=document.createElement('summary');evidenceTitle.textContent='证据链';evidence.append(evidenceTitle);entry.append(evidence);
      for(const step of item.chain || []) reference(evidence,step.kind+': ',step.from || step.path,step.line,'');
      for(const reader of item.readers || []) reference(evidence,'Literal reference ',reader.reader,reader.line,' · '+reader.evidence);
      for(const user of item.users || []) reference(evidence,'Source clue ',user.source,user.line,' · '+user.evidence);
    }
  }
}
function renderTaskDetail(detail) {
  activeTaskDetail = detail;
  show('Task ' + detail.task.id, detail);
  el('detail-body').hidden=true;
  el('detail-body').textContent='';
  const overview=document.createElement('p');overview.textContent=detail.task.title;el('detail-links').append(overview);
  const evidence=detail.godot.runtime_evidence;
  const status=document.createElement('p');
  status.textContent=`${detail.godot.status} | main ${detail.navigation?.revision || ''}`;
  if(evidence){const counts=evidence.test_results||{}; if(counts.tests) status.textContent+=` | Tests: ${counts.tests}, passed: ${counts.tests-(counts.failures||0)-(counts.errors||0)}, failed: ${(counts.failures||0)+(counts.errors||0)}`;}
  el('detail-links').append(status);
  if(evidence?.reason){const reason=document.createElement('p');reason.className='runtime-reason';reason.textContent=evidence.reason.replace(/GDUNIT_DONE[\s\S]*$/,'').trim();el('detail-links').append(reason);}
  if(detail.godot.workspace_evidence){const result=detail.godot.workspace_evidence;const p=document.createElement('p');p.textContent=`Last workspace snapshot: ${result.status} | ${result.finished_at} | ${result.source_revision}`+(result.reason ? ' | '+result.reason : '');el('detail-links').append(p);}
  if(detail.godot.runtime_eligible) {
    el('detail-links').append(button('Verify local main',async()=>{await api('runtime',{task_id:detail.task.id,mode:'main'});await loadStatus();}));
    el('detail-links').append(button('Verify workspace',async()=>{const result=await api('runtime',{task_id:detail.task.id,mode:'workspace'});show('Workspace verification - task '+detail.task.id,result);}));
  }
  if(detail.navigation) {
    if(!['configs','code','scenes','assets'].some(k=>(detail.navigation[k] || []).some(i=>i.focus==='core'))){const empty=document.createElement('p');empty.textContent='No confirmed core association. See related candidates below.';el('detail-links').append(empty);}
    renderNavigation(detail.navigation);
    const more=document.createElement('details');more.id='more-associations';const label=document.createElement('summary');
    const count=['configs','code','scenes','assets'].reduce((n,k)=>n+(detail.navigation[k] || []).filter(i=>i.focus!=='core').length,0);
    label.textContent=`More associations (${count})`;more.append(label);el('detail-links').append(more);
    more.addEventListener('toggle',()=>{if(more.open && !more.dataset.loaded){more.dataset.loaded='true';renderNavigation(detail.navigation,more,true);}});
  }
  if(detail.resource_knowledge?.length){const box=document.createElement('details');const summary=document.createElement('summary');summary.textContent=`资源知识（按类型，共 ${detail.resource_knowledge.length} 条）`;box.append(summary);for(const [kind,title] of [['config','配置文件'],['asset','素材'],['scene','场景'],['code','代码'],['test','测试']]){const items=detail.resource_knowledge.filter(x=>x.kind===kind);if(!items.length)continue;const group=document.createElement('details');const label=document.createElement('summary');label.textContent=`${title}（${items.length}）`;group.append(label);for(const item of items){const p=document.createElement('p');p.textContent=`${item.path} — 证据置信度：${item.confidence}`;group.append(p);}box.append(group);}el('detail-links').append(box);}
  const raw=document.createElement('details');raw.id='raw-evidence';const label=document.createElement('summary');label.textContent='Original task and evidence';raw.append(label);el('detail-links').append(raw);
  raw.addEventListener('toggle',()=>{if(raw.open && !raw.dataset.loaded){raw.dataset.loaded='true';const pre=document.createElement('pre');pre.textContent=pretty(detail);raw.append(pre);}});
}
function pager(id, page) {
  const box = el(id); box.replaceChildren();
  for (const [label, destination] of [['First',1],['Previous',page.page-1],['Next',page.page+1],['Last',page.pages]]) {
    const b = button(label, () => loadTasks(destination));
    b.dataset.disabled = String(destination < 1 || destination > page.pages || destination === page.page); b.disabled = b.dataset.disabled === 'true'; box.append(b);
  }
  const label = document.createElement('span'); label.textContent = `Page ${page.page} / ${page.pages} · ${page.total} tasks · 20 per page`; box.append(label);
  const input = document.createElement('input'); input.type = 'number'; input.min = '1'; input.max = String(page.pages); input.value = String(page.page); input.setAttribute('aria-label','Jump to page');
  const jump = () => {const p = Number(input.value); if (!Number.isInteger(p) || p < 1 || p > page.pages) throw new Error('Page is out of range'); return loadTasks(p);};
  input.onkeydown = e => {if(e.key === 'Enter') run(jump);}; box.append(input,button('Go',jump));
}
async function loadTasks(page=1) {
  const filter = activeFilter ? `&filter_kind=${encodeURIComponent(activeFilter.kind)}&filter_value=${encodeURIComponent(activeFilter.value)}` : '';
  const result = await api('tasks?page=' + page + filter); currentPage = result.page; el('tasks').replaceChildren();
  visibleTaskIds = result.items.filter(task => task.godot.runtime_eligible).map(task => String(task.id));
  for (const task of result.items) {
    const row = document.createElement('tr');
    const selection = document.createElement('td'); selection.className = 'selection';
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.disabled = !task.godot.runtime_eligible; checkbox.checked = selectedTasks.has(String(task.id));
    checkbox.setAttribute('aria-label', `Select task ${task.id}`);
    checkbox.onchange = () => { if (checkbox.checked) selectedTasks.add(String(task.id)); else selectedTasks.delete(String(task.id)); updateSelection(); };
    selection.append(checkbox); row.append(selection);
    for (const key of ['id','title','status','dependencies','recommendedSubtasks','godot']) {
      const td = document.createElement('td');
      if (key === 'id') td.append(button(String(task.id),async () => {
        renderTaskDetail(await api('task?id=' + encodeURIComponent(task.id)));
      }));
      else if (key === 'godot') {
        const evidence = task.godot.runtime_evidence;
        const counts = evidence?.test_results;
        const summary = counts?.tests ? ` · ${counts.tests} tests · ${(counts.failures||0)+(counts.errors||0)} failed` : '';
        td.textContent = task.godot.status + (task.godot.runtime_status ? ` · ${task.godot.runtime_status}` : '') + summary;
      } else td.textContent = typeof task[key] === 'object' ? pretty(task[key]) : String(task[key] ?? '—');
      row.append(td);
    }
    el('tasks').append(row);
  }
  updateSelection();
  pager('pager-top',result); pager('pager-bottom',result);
}
async function loadStatus() {
  const state = await api('status'); el('revision').textContent = state.revision ? `${state.branch} @ ${state.revision} | scanned ${state.scanned_at}` : 'No successful local scan yet.';
  el('publication').textContent = `Published KCP pointer matches scan: ${state.publication.matches_scan}. ${state.publication.note}`;
  if (!configLoaded) renderConfigEditor(await api('config')); el('summary').replaceChildren();
  const addMetric = (key,value,kind=null) => {
    const d=document.createElement(kind ? 'button' : 'div');d.className=kind ? 'metric metric-button' : 'metric';
    d.textContent=key+': '+value;
    if(kind){d.type='button';d.setAttribute('aria-pressed',String(activeFilter?.kind===kind&&activeFilter?.value===key));d.onclick=()=>run(()=>setFilter(kind,key));}
    el('summary').append(d);
  };
  addMetric('total',state.summary.total);
  for(const [key,value] of Object.entries(state.summary.statuses)) addMetric(key,value,'task_status');
  for(const [key,value] of Object.entries(state.summary.godot)) addMetric(key,value,'godot_status');
  const runtime = state.runtime || {};
  for(const [key,value] of Object.entries({runtime_batch_total:runtime.total || 0,
    runtime_verified:runtime.runtime_verified || 0,runtime_failed:runtime.runtime_failed || 0,
    runtime_unverified:runtime.runtime_unverified || 0})) addMetric(key,value);
  el('gdds').replaceChildren();
  for(const file of state.gdd_files) {const p=document.createElement('p'); if(file.available) p.append(sourceLink(file.path)); else p.textContent=file.path+' — missing or unsupported at main';el('gdds').append(p);}
  await loadTasks(currentPage);
}
function actionEntry(item) {
  const row=document.createElement('p');row.className='action-entry';
  if(item.kind==='task') {
    row.append(button(`Task ${item.task_id} · ${item.title}`,async()=>renderTaskDetail(await api('task?id='+encodeURIComponent(item.task_id)))));
  } else {
    row.append(sourceLink(item.path));
  }
  const evidence=document.createElement('span');evidence.textContent=`${item.evidence_strength} · ${item.reason}`;
  row.append(evidence);return row;
}
function renderActionable(result) {
  const data=result.actionable_results;
  const secondary=el('secondary-actionable');secondary.replaceChildren();let secondaryCount=0;
  for(const [group,id] of [['tasks','action-tasks'],['configs','action-configs'],['code','action-code'],['tests','action-tests']]) {
    const target=el(id);target.replaceChildren();
    const primary=data[group].items.filter(item=>item.evidence_strength!=='inferred');
    const weak=data[group].items.filter(item=>item.evidence_strength==='inferred');
    if(primary.length) primary.forEach(item=>target.append(actionEntry(item)));
    else {const empty=document.createElement('p');empty.className='empty-result';empty.textContent='No evidenced result in this group.';target.append(empty);}
    weak.forEach(item=>{const wrapper=document.createElement('div');wrapper.className='secondary-entry';wrapper.append(actionEntry(item));secondary.append(wrapper);secondaryCount++;});
    el(id+'-count').textContent=`${data[group].total} found · ${data[group].truncated} not shown`;
  }
  el('secondary-summary').textContent=`Lower-confidence results (${secondaryCount})`;
  el('secondary-actionable').hidden=secondaryCount===0;
}
async function search(target) {
  const result = await api('query',{query:el('query').value,consumer:el('consumer').value,...(target ? {target} : {})});
  el('results').hidden=false; el('queries').textContent='Executed queries: '+result.queries.join(' | ');
  const freshness=result.snapshot_freshness;el('snapshot-warning').hidden=!freshness.stale;
  el('snapshot-warning').textContent=freshness.stale?`Snapshot is stale. Results describe ${freshness.snapshot_revision}; current HEAD is ${freshness.current_revision}.`:'';
  renderActionable(result);
  el('knowledge').replaceChildren(); for(const hit of result.knowledge) {const p=document.createElement('p');p.append(sourceLink(hit.path),` · line ${hit.line_start} · ${hit.matched_query}`);el('knowledge').append(p);}
  el('supplements').replaceChildren();for(const hit of result.gdd_supplements) el('supplements').append(sourceLink(hit.path));
  el('targets').replaceChildren();el('target-count').textContent=`${result.impact_target_total} candidate targets; showing at most 80. ${result.impact_skipped_methods.length} unsupported method signatures omitted (details in evidence JSON). Narrow the query if needed. Select one to analyze.`;
  for(const hit of result.impact_targets) el('targets').append(button(hit.type+' · '+hit.id,()=>search({type:hit.type,id:hit.id})));
  el('preview').textContent=pretty(result);
}
const consumerHelp = {
  'repository-session': '综合查找：范围最广，适合不确定信息位于何处时查找仓库文档、代码和任务上下文。',
  chapter4: '架构与契约：优先查找架构设计、功能切面、ADR 和契约边界。',
  chapter5: '验收与规则：优先查找验收标准、语义约束、测试要求和历史决策。',
  chapter6: '任务实施：优先查找任务实现涉及的代码、配置、场景、素材、测试和运行证据。',
  review: '审查与交付：优先查找代码审查、安全、质量门禁和发布证据。'
};
function updateConsumerHelp() {
  el('consumer-help').textContent=consumerHelp[el('consumer').value] || '';
}
el('consumer').addEventListener('change',updateConsumerHelp);
updateConsumerHelp();
el('close-detail').onclick=()=>el('detail').close();
el('detail').onclose=()=>{activeTaskDetail=null;};
el('open-config').onclick=()=>el('config-dialog').showModal();
el('close-config').onclick=()=>el('config-dialog').close();
for(const id of ['config-gdd-paths','config-task-scene-bindings','config-query-aliases']) el(id).addEventListener('input',()=>{try{updateConfigPreview();}catch(_){el('config-advanced').value='当前分区包含无效 JSON。';}});
el('scan').onclick=()=>run(async()=>{activeTaskDetail=null;await api('config',collectConfigEditor());await api('scan',{});currentPage=1;await loadStatus();});
el('runtime').textContent='Verify eligible tasks on main';
el('runtime-all').textContent='Audit all gameplay on main';
el('runtime').onclick=()=>run(async()=>{await api('runtime',{mode:'main'});await loadStatus();});
el('runtime-all').onclick=()=>run(async()=>{await api('runtime',{all_gameplay:true});await loadStatus();});
el('runtime-selected').onclick=()=>run(async()=>{await api('runtime',{task_ids:[...selectedTasks]});await loadStatus();});
el('select-page').onclick=()=>{visibleTaskIds.forEach(id=>selectedTasks.add(id));loadTasks(currentPage);};
el('clear-selection').onclick=()=>{selectedTasks.clear();loadTasks(currentPage);};
el('clear-filter').onclick=()=>run(()=>setFilter(null,null));
el('save-config').onclick=()=>run(async()=>{await api('config',collectConfigEditor());el('publication').textContent='配置已保存。请重新扫描本地 main；当前结果仍使用上一次扫描配置。';});
el('query-form').onsubmit=e=>{e.preventDefault();run(()=>search());};
run(async()=>{token=(await api('session')).token;await refreshOperation();await loadStatus();operationPoll=setInterval(refreshOperation,1000);});
