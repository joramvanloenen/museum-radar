const state={page:'overview',opps:[],sources:[],discoveredSources:[],meta:{},researchMeta:{},projectGraph:{},history:{},settings:{},selected:null,modal:null};
const stages=['Signal','Lead','Expected','Pre-market','Live Tender','Pitch','Submitted','Won','Lost'];
const $=s=>document.querySelector(s);
const store={get:(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}},set:(k,v)=>localStorage.setItem(k,JSON.stringify(v))};
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const safeUrl=u=>{try{const x=new URL(String(u||''),location.href);return ['http:','https:'].includes(x.protocol)?x.href:''}catch{return ''}};
function inferResourceKind(label='',url='',kind=''){
  const text=(label+' '+url+' '+kind).toLowerCase();
  if(/market consultation|market engagement|prior information|pin\b/.test(text))return 'Market consultation';
  if(/design brief|creative brief|exhibition brief|interpretation brief/.test(text))return 'Design brief';
  if(/requirement|qualification|selection criteria|scope of work|statement of work|sow\b/.test(text))return 'Requirements';
  if(/technical spec|specification|technical requirement/.test(text))return 'Technical specs';
  if(/drawing|plan set|floor plan|floorplan|architectural plan|layout/.test(text))return 'Drawings / plans';
  if(/budget|funding|grant|finance|business case/.test(text))return 'Budget / funding';
  if(/council|municipal|committee|decision|resolution|minutes/.test(text))return 'Council decision';
  if(/contract notice|procurement notice|tender notice/.test(text))return 'Contract notice';
  if(/\.pdf($|\?)/.test(url.toLowerCase())||/tender pdf|brief pdf/.test(text))return 'Tender PDF';
  if(/article|news|press release|announcement/.test(text))return 'Source article';
  if(kind && !/^document$/i.test(kind))return kind;
  return 'Document';
}
function resourceLinks(o){
  const seen=new Set(),links=[];
  const add=(url,label,kind='Source')=>{const u=safeUrl(url);if(!u||seen.has(u))return;seen.add(u);links.push({url:u,label:label||u,kind:inferResourceKind(label,u,kind)})};
  add(o.source_url,o.source_label||'Original source','Source');
  (o.evidence||[]).forEach(e=>add(e.source_url,e.source_label||e.title||'Sources source','Sources'));
  (o.documents||[]).forEach((d,i)=>typeof d==='string'?add(d,'Document '+(i+1),'Document'):add(d.url,d.title||d.name||('Document '+(i+1)),d.kind||'Document'));
  return links;
}
function resourceSection(o){
  const links=resourceLinks(o);
  if(!links.length)return o.sample?'<div class="resourceEmpty">Sample opportunity — no live source link.</div>':'<div class="resourceEmpty">No source links captured yet.</div>';
  return '<div class="resourceList">'+links.map(l=>`<a class="resourceLink" href="${escapeHtml(l.url)}" target="_blank" rel="noopener noreferrer"><span><small>${escapeHtml(l.kind)}</small><b>${escapeHtml(l.label)}</b></span><span class="resourceArrow">↗</span></a>`).join('')+'</div>';
}
function fmtMoney(o){if(!o.budget_min&&!o.budget_max)return '—';let f=n=>new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(n);return `${o.currency||'EUR'} ${f(o.budget_min||0)}–${f(o.budget_max||0)}`}
function sc(s){return s>=80?'good':'mid'}
function localPrefs(){return store.get('radarPrefs',{})}
function mergedOpps(){const prefs=localPrefs();const manual=store.get('radarManual',[]);return [...state.opps,...manual].map(o=>({...o,...(prefs[o.id]||{})})).sort((a,b)=>(b.score||0)-(a.score||0))}
function stats(){const o=mergedOpps().filter(x=>!x.rejected);return {act_now:o.filter(x=>x.score>=85||x.stage==='Live Tender').length,live:o.filter(x=>x.stage==='Live Tender').length,expected:o.filter(x=>['Expected','Pre-market'].includes(x.stage)).length,signals:o.filter(x=>['Signal','Lead'].includes(x.stage)).length}}
function scrubLegacyBranding(v){
  if(typeof v==='string')return v.replace(/YIPP/gi,'Museum Radar');
  if(Array.isArray(v))return v.map(scrubLegacyBranding);
  if(v&&typeof v==='object'){const out={};for(const [k,val] of Object.entries(v))out[k]=scrubLegacyBranding(val);return out}
  return v;
}
function migrateLocalData(){
  for(const key of ['radarSettings','radarManual','radarPrefs']){
    const current=store.get(key,null);
    if(current!==null){
      const clean=scrubLegacyBranding(current);
      if(JSON.stringify(clean)!==JSON.stringify(current))store.set(key,clean);
    }
  }
}
async function load(){migrateLocalData();const [opps,sources,meta,history,discovered,researchMeta,projectGraph]=await Promise.all([fetch('./data/opportunities.json').then(r=>r.json()),fetch('./data/sources.json').then(r=>r.json()),fetch('./data/meta.json').then(r=>r.json()),fetch('./data/historical-intelligence.json').then(r=>r.json()).catch(()=>({})),fetch('./data/discovered-sources.json').then(r=>r.json()).catch(()=>[]),fetch('./data/research-agent-meta.json').then(r=>r.json()).catch(()=>({})),fetch('./data/project-graph.json').then(r=>r.json()).catch(()=>({}))]);state.opps=opps;state.sources=sources;state.meta=meta;state.history=history;state.discoveredSources=discovered;state.researchMeta=researchMeta;state.projectGraph=projectGraph;state.settings=store.get('radarSettings',{company_name:'Museum Radar',capability_profile:'Interactive museum experiences, physical-digital installations, projection, realtime 3D, sensors, playful learning.',weight_fit:25,weight_budget:10,weight_geo:10,weight_timing:15,weight_confidence:15,weight_strategy:25});render()}
function nav(){
  const desktop=[['overview','Overview'],['opportunities','Opportunities'],['future','Future Radar'],['pitch','Pitch Opportunities'],['organizations','Organizations'],['sources','Sources'],['scout','Scout'],['activity','Intelligence'],['settings','Settings']];
  return `<div class="sidebar"><div class="brand"><span class="brandword">Museum Radar</span></div><div class="nav">${desktop.map(([id,n])=>`<button class="${state.page===id?'active':''}" data-nav="${id}" aria-label="${n}" aria-current="${state.page===id?'page':'false'}">${n}</button>`).join('')}</div><div class="sidefoot">GitHub Pages edition<br><span class="status">● ${escapeHtml(state.meta.status||'Static')}</span></div></div>
  <nav class="mobileNav" aria-label="Primary">
    <button data-nav="overview" class="${state.page==='overview'?'active':''}"><span class="mIcon">⌂</span><span>Home</span></button>
    <button data-nav="opportunities" class="${state.page==='opportunities'?'active':''}"><span class="mIcon">◎</span><span>Leads</span></button>
    <button data-nav="future" class="${state.page==='future'?'active':''}"><span class="mIcon">◌</span><span>Future</span></button>
    <button data-nav="activity" class="${state.page==='activity'?'active':''}"><span class="mIcon">↻</span><span>Updates</span></button>
    <button id="mobileMore" aria-label="More sections"><span class="mIcon">•••</span><span>More</span></button>
  </nav>`;
}
function header(title,sub,action=true,showEyebrow=true){return `<div class="topbar"><div>${showEyebrow?'<div class="eyebrow">Museum Radar</div>':''}<div class="title">${title}</div><div class="sub">${sub}</div></div>${action?`<div class="actions"><button class="btn secondaryAction" id="importBtn" aria-label="Import local Museum Radar data">Import</button><button class="btn secondaryAction" id="exportBtn" aria-label="Export local Museum Radar data">Export</button><button class="btn primary" id="newOpp" aria-label="Add opportunity">Add</button></div>`:''}</div>`}
function table(opps){if(!opps.length)return `<div class="card empty">No opportunities match these filters.</div>`;return `<div class="card tablewrap"><table class="oppTable"><thead><tr><th>Score</th><th>Opportunity</th><th>Stage</th><th>Location</th><th>Value</th><th>Timing</th></tr></thead><tbody>${opps.map(o=>`<tr data-open="${escapeHtml(o.id)}"><td><span class="score ${sc(o.score)}">${o.score}</span></td><td><div class="name">${escapeHtml(o.title)}</div><div class="muted">${escapeHtml(o.organization)}</div></td><td><span class="badge ${escapeHtml(o.stage)}">${escapeHtml(o.stage)}</span></td><td>${escapeHtml([o.city,o.country].filter(Boolean).join(', ')||'—')}</td><td>${fmtMoney(o)}</td><td>${escapeHtml(o.deadline||o.procurement_window||'—')}</td></tr>`).join('')}</tbody></table></div>`}
function card(o){const p=o.prediction||{},src=p.source_diversity||((o.evidence||[]).length);return `<div class="card oppcard" data-open="${escapeHtml(o.id)}" tabindex="0" role="button" aria-label="Open ${escapeHtml(o.title)}"><div class="top"><span class="badge ${escapeHtml(o.stage)}">${escapeHtml(o.stage)}</span><span class="score ${sc(o.score)}">${o.score}</span></div><h3>${escapeHtml(o.title)}</h3><div class="muted">${escapeHtml(o.organization)} · ${escapeHtml(o.country||'')}</div><p>${escapeHtml(o.summary||'')}</p><div class="meta"><span class="timing">${escapeHtml(o.deadline||o.procurement_window||'Timing unknown')}</span><span class="confidence">${o.confidence||0}% confidence</span>${o.source_key==='research_agent'?`<span class="confidence">${src} source${src===1?'':'s'}</span>`:''}</div><div class="next">${escapeHtml(o.next_action||'Review opportunity')}</div></div>`}
function priorityCard(o){return `<article class="priorityCard" data-open="${escapeHtml(o.id)}" tabindex="0" role="button"><div class="priorityScore ${sc(o.score)}">${o.score}</div><div class="priorityBody"><div class="priorityTop"><span class="badge ${escapeHtml(o.stage)}">${escapeHtml(o.stage)}</span><span class="priorityTime">${escapeHtml(o.deadline||o.procurement_window||'Timing unknown')}</span></div><h3>${escapeHtml(o.title)}</h3><div class="priorityOrg">${escapeHtml(o.organization)} · ${escapeHtml(o.country||'')}</div><div class="priorityAction">${escapeHtml(o.next_action||'Review opportunity')}</div></div><span class="chev" aria-hidden="true">›</span></article>`}
function overview(){const s=stats(),o=mergedOpps().filter(x=>!x.rejected);const urgent=o.filter(x=>x.score>=80||x.stage==='Live Tender').slice(0,5);const future=o.filter(x=>['Signal','Lead','Expected','Pre-market'].includes(x.stage)).slice(0,4);return `${header('Museum Radar','',true,false)}<div class="desktopNotice notice">Shared discoveries refresh automatically. Personal Watch/Reject state stays on this device.</div>
<div class="mobileSummary"><span><b>${s.live}</b> live</span><span><b>${s.expected}</b> expected</span><span><b>${s.signals}</b> signals</span></div>
<div class="grid4 overviewMetrics">${[['Act now',s.act_now],['Live',s.live],['Expected',s.expected],['Signals',s.signals]].map(x=>`<div class="metric"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('')}</div>
<section class="section prioritySection"><div class="sectionhead"><h2>Needs attention</h2><button class="textBtn" data-nav="opportunities">See all</button></div><div class="priorityList">${urgent.map(priorityCard).join('')||'<div class="notice">Nothing urgent right now.</div>'}</div></section>
<section class="section futureSection"><div class="sectionhead"><h2>Strong future leads</h2><button class="textBtn" data-nav="future">See all</button></div><div class="cards">${future.map(card).join('')}</div></section>`}
function opportunities(){return `${header('Opportunities','Search, filter and rank the full opportunity pipeline.')}<div class="filters" role="search"><input id="q" aria-label="Search opportunities" placeholder="Search opportunities…"><select id="stageFilter" aria-label="Filter by stage"><option value="">All stages</option>${stages.map(s=>`<option>${s}</option>`).join('')}</select><select id="scoreFilter" aria-label="Filter by minimum score"><option value="0">Any score</option><option value="60">60+</option><option value="75">75+</option><option value="85">85+</option></select><label class="row muted watchToggle"><input type="checkbox" id="watchFilter"> Watched only</label></div><div id="oppResults">${table(mergedOpps().filter(o=>!o.rejected))}</div>`}
function future(){return `${header('Future Radar','Projects likely to produce an interactive tender or pitch before formal procurement.')}<div class="cards">${mergedOpps().filter(x=>['Signal','Lead','Expected','Pre-market'].includes(x.stage)&&!x.rejected).map(card).join('')}</div>`}
function pitches(){return `${header('Pitch Opportunities','Organizations worth approaching before procurement exists.')}<div class="cards">${mergedOpps().filter(x=>x.stage==='Pitch'&&!x.rejected).map(card).join('')}</div>`}
function organizations(){const m=new Map();mergedOpps().forEach(o=>{if(!m.has(o.organization))m.set(o.organization,{name:o.organization,country:o.country,city:o.city,count:0,best:0});let x=m.get(o.organization);x.count++;x.best=Math.max(x.best,o.score||0)});return `${header('Organizations','Clients and institutions connected to discovered opportunities.')}<div class="cards">${[...m.values()].map(o=>`<div class="card source"><div class="kicker">Museum / cultural institution</div><h3>${escapeHtml(o.name)}</h3><div class="muted">${escapeHtml([o.city,o.country].filter(Boolean).join(', '))}</div><p>${o.count} opportunity${o.count===1?'':'ies'} · best score ${o.best}</p></div>`).join('')}</div>`}
function sources(){
  const all=[...state.sources,...state.discoveredSources];
  return `${header('Sources','Automated public-source coverage plus newly discovered candidate platforms.')}<div class="cards">${all.map(s=>`<div class="card source"><div class="row space"><span class="badge">${escapeHtml(s.type)}</span><span class="status">${escapeHtml(s.status)}</span></div><h3>${escapeHtml(s.name)}</h3><div class="muted">${escapeHtml(s.region||'Unknown')}</div><p>${escapeHtml(s.notes||'')}</p>${s.confidence?`<div class="muted">Discovery confidence ${s.confidence}%</div>`:''}${s.url?`<a class="muted" href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:''}</div>`).join('')}</div>`;
}
function scout(){
  const r=state.researchMeta||{};
  const researchStatus=escapeHtml(r.status||'unknown');
  return `${header('Scout','Two independent agents keep Radar current.',false)}
  <div class="grid4">
    <div class="metric"><b>${state.meta.last_scan_found||0}</b><span>Verified Scout matches</span></div>
    <div class="metric"><b>${state.meta.total_opportunities||mergedOpps().length}</b><span>Total opportunities</span></div>
    <div class="metric"><b>${r.project_clusters||0}</b><span>Predicted projects</span></div>
    <div class="metric"><b>${r.high_conviction||0}</b><span>High-confidence predictions</span></div>
  </div>
  <div class="cards" style="margin-top:18px">
    <div class="card source">
      <div class="row space"><span class="badge">Verified Tender Scout</span><span class="status">● Active</span></div>
      <h3>Official procurement</h3>
      <p>GitHub Actions checks structured and official procurement sources every 6 hours. It can verify Live Tender and Pre-market records but does not invent predicted tenders.</p>
      <div class="muted">Last scan: ${escapeHtml(state.meta.last_scan_at||'not yet')}</div>
      ${state.meta.last_error?`<div class="notice">${escapeHtml(state.meta.last_error)}</div>`:''}
    </div>
    <div class="card source">
      <div class="row space"><span class="badge">Research Agent</span><span class="status">● ${researchStatus}</span></div>
      <h3>Web intelligence & prediction</h3>
      <p>ChatGPT searches the wider web every 6 hours, correlates project breadcrumbs, predicts likely procurement windows, discovers new source platforms and writes meaningful changes back to Radar.</p>
      <div class="muted">Last research: ${escapeHtml((r.last_run||'not yet').replace('T',' '))}</div>
      ${(r.errors||[]).length?`<div class="notice">${escapeHtml(r.errors.slice(0,3).join(' · '))}</div>`:''}
    </div>
  </div>`;
}
function activity(){
  const h=state.history||{},fc=h.fit_counts||{},r=state.researchMeta||{},g=state.projectGraph||{};
  const buyers=(h.top_buyers||[]).slice(0,6);
  const types=(h.project_types||[]).filter(x=>(x.high||0)+(x.adjacent||0)>0).slice(0,6);
  const predicted=mergedOpps().filter(o=>o.source_key==='research_agent').sort((a,b)=>(b.confidence||0)-(a.confidence||0)||(b.score||0)-(a.score||0)).slice(0,6);
  return `${header('Intelligence','Predicted projects, evidence and historical patterns that help us act before a tender appears.')}
  <div class="grid4">
    <div class="metric"><b>${r.project_clusters||r.predicted_leads_added||0}</b><span>Predicted projects</span></div>
    <div class="metric"><b>${r.high_conviction||g.high_conviction||0}</b><span>High-confidence leads</span></div>
    <div class="metric"><b>${r.candidate_sources_found||0}</b><span>Source candidates</span></div>
    <div class="metric"><b>${fc.high||0}</b><span>Strong-fit history</span></div>
  </div>
  <section class="section">
    <div class="sectionhead"><h2>Research Agent</h2><span class="status">● ${escapeHtml(r.status||'unknown')}</span></div>
    <div class="card source">
      <p><b>Last research:</b> ${escapeHtml((r.last_run||'Not run yet').replace('T',' '))}</p>
      <p>The Research Agent searches outside procurement portals for funding, design appointments, masterplans, renovations, new galleries and other breadcrumbs. Multiple sources are combined into one evolving project prediction. General web research can never promote itself to Live Tender.</p>
      ${(r.errors||[]).length?`<div class="notice"><b>Agent issues:</b> ${escapeHtml(r.errors.slice(0,4).join(' · '))}</div>`:''}
    </div>
  </section>
  <section class="section"><div class="sectionhead"><h2>Highest-confidence predictions</h2></div><div class="cards">${predicted.map(card).join('')||'<div class="notice">No predicted projects yet.</div>'}</div></section>
  <section class="section"><div class="sectionhead"><h2>Recurring useful buyers</h2></div><div class="cards">${buyers.map(b=>`<div class="card source"><h3>${escapeHtml(b.buyer)}</h3><p><b>${b.high||0}</b> strong-fit · ${b.adjacent||0} adjacent · ${b.total||0} total records</p></div>`).join('')}</div></section>
  <section class="section"><div class="sectionhead"><h2>What the history says to look for</h2></div><div class="cards">${types.map(t=>`<div class="card source"><h3>${escapeHtml(t.name)}</h3><p>${t.high||0} strong-fit · ${t.adjacent||0} adjacent examples</p></div>`).join('')}</div></section>`;
}
function settings(){const s=state.settings;return `${header('Scoring Settings','Local scoring preferences for this browser.',false)}<div class="card detail settings"><div class="formgrid"><div class="field"><label>Company name</label><input id="company_name" value="${escapeHtml(s.company_name)}"></div><div class="field full"><label>Capability profile</label><textarea id="capability_profile">${escapeHtml(s.capability_profile)}</textarea></div>${[['weight_fit','Capability fit'],['weight_budget','Budget'],['weight_geo','Geography'],['weight_timing','Timing'],['weight_confidence','Sources confidence'],['weight_strategy','Strategic value']].map(([k,n])=>`<div class="field"><label>${n} weight</label><input type="number" id="${k}" value="${s[k]}"></div>`).join('')}<div class="field full"><button class="btn primary" id="saveSettings">Save locally</button></div></div></div>`}
function render(){const fn={overview,opportunities,future,pitch:pitches,organizations,sources,scout,activity,settings}[state.page];$('#app').innerHTML=`<div class="layout">${nav()}<main class="main">${fn()}</main></div>`;bind()}
function getOpp(id){return mergedOpps().find(o=>String(o.id)===String(id))}
function openDetail(id){state.selected=getOpp(id);state.modal='detail';renderModal()}
function renderModal(){document.querySelectorAll('.modalback').forEach(x=>x.remove());document.body.classList.remove('modal-open');if(!state.modal)return;document.body.classList.add('modal-open');const wrap=document.createElement('div');wrap.className='modalback';if(state.modal==='more'){wrap.innerHTML=`<div class="modal moreSheet"><div class="sheetHandle"></div><div class="row space"><h2>More</h2><button class="btn iconBtn" data-close aria-label="Close">×</button></div><div class="moreGrid">${[['pitch','Pitch opportunities'],['organizations','Organizations'],['sources','Sources'],['scout','Scout'],['settings','Settings']].map(([id,n])=>`<button class="moreItem" data-more-nav="${id}">${n}<span>›</span></button>`).join('')}</div></div>`;wrap.querySelectorAll('[data-more-nav]').forEach(b=>b.onclick=()=>{state.page=b.dataset.moreNav;wrap.remove();document.body.classList.remove('modal-open');state.modal=null;render()})}
else if(state.modal==='detail'){const o=state.selected,p=o.prediction||{};const signals=[...(p.signals||[]),...(p.fit_terms||[])].slice(0,10);wrap.innerHTML=`<div class="modal detailModal"><div class="detailModalTop"><div class="row" style="gap:8px"><span class="badge ${escapeHtml(o.stage)}">${escapeHtml(o.stage)}</span>${o.source_key==='research_agent'?'<span class="badge intelBadge">Predicted lead</span>':o.verified?'<span class="badge verifiedBadge">Verified source</span>':''}</div><button class="btn detailClose" data-close aria-label="Close">×</button></div><div class="detailgrid"><article class="detail detailMain"><div class="kicker">${escapeHtml(o.organization)} · ${escapeHtml(o.country||'')}</div><h1>${escapeHtml(o.title)}</h1><p class="sub">${escapeHtml(o.summary||'')}</p>${o.source_key==='research_agent'?`<section class="predictionBox"><h3>Research Agent assessment</h3><p>${escapeHtml(p.reason||p.why_now||'Potential upstream opportunity detected.')}</p>${signals.length?`<div class="signalPills">${signals.map(x=>`<span>${escapeHtml(x)}</span>`).join('')}</div>`:''}${(p.expected_next_signals||[]).length?`<div class="predictionNext"><b>Watch next:</b> ${escapeHtml(p.expected_next_signals.join(' · '))}</div>`:''}${(p.risk_flags||[]).length?`<div class="predictionRisk"><b>Uncertainty:</b> ${escapeHtml(p.risk_flags.join(' · '))}</div>`:''}</section>`:''}<section class="detailSection"><h3>Why it fits</h3><p>${escapeHtml(o.fit_rationale||'No fit rationale yet.')}</p></section><section class="detailSection"><h3>Pitch / approach</h3><p>${escapeHtml(o.pitch_angle||'No pitch angle yet.')}</p></section><section class="detailSection"><h3>Found here / documents</h3>${resourceSection(o)}</section><section class="detailSection sourcesSection"><h3>Sources</h3>${(o.evidence||[]).map(e=>`<div class="evidence"><div class="evidenceItem"><b>${escapeHtml(e.title)}</b><small>${escapeHtml(e.date||'')} · ${escapeHtml(e.kind||'Source')} · confidence ${e.strength||0}%</small><div>${escapeHtml(e.detail||'')}</div>${safeUrl(e.source_url)?`<a class="muted evidenceSource" href="${escapeHtml(safeUrl(e.source_url))}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:''}</div></div>`).join('')||'<div class="notice">No sources recorded yet.</div>'}</section></article><aside class="detail detailFacts"><div class="scoreBlock"><div class="bigscore ${sc(o.score)}">${o.score}</div><div class="scoreLabel">Opportunity score</div></div><div class="factList"><div class="fact"><h3>Confidence</h3><div>${o.confidence||0}%</div></div>${o.source_key==='research_agent'?`<div class="fact"><h3>Independent sources</h3><div>${p.source_diversity||1}</div></div><div class="fact"><h3>Source quality</h3><div>${p.source_quality||'—'}%</div></div>`:''}<div class="fact"><h3>Estimated value</h3><div>${fmtMoney(o)}</div></div><div class="fact"><h3>Timing</h3><div>${escapeHtml(o.deadline||o.procurement_window||'Unknown')}</div></div><div class="fact nextFact"><h3>Next action</h3><div>${escapeHtml(o.next_action||'—')}</div></div></div><div class="detailActions"><button class="btn" id="watch">${o.watched?'★ Watched':'☆ Watch'}</button><button class="btn" id="reject">${o.rejected?'Restore':'Reject'}</button></div></aside></div></div>`}
else if(state.modal==='new'){wrap.innerHTML=`<div class="modal"><div class="row space"><h2>Add local opportunity</h2><button class="btn" data-close>×</button></div><div class="formgrid"><div class="field full"><label>Title</label><input id="n_title"></div><div class="field"><label>Organization</label><input id="n_org"></div><div class="field"><label>Country</label><input id="n_country"></div><div class="field"><label>Stage</label><select id="n_stage">${stages.map(s=>`<option>${s}</option>`).join('')}</select></div><div class="field"><label>Score</label><input id="n_score" type="number" value="60"></div><div class="field full"><label>Summary</label><textarea id="n_summary"></textarea></div><div class="field full"><label>Found at / source URL</label><input id="n_source" type="url" placeholder="https://…"></div><div class="field full"><label>Document links <span class="muted">(one per line)</span></label><textarea id="n_documents" placeholder="https://…/brief.pdf&#10;https://…/project-page"></textarea></div><div class="field full"><button class="btn primary" id="createOpp">Create locally</button></div></div></div>`}
document.body.appendChild(wrap);const closeModal=()=>{wrap.remove();document.body.classList.remove('modal-open');state.modal=null};wrap.querySelectorAll('[data-close]').forEach(b=>b.onclick=closeModal);wrap.onclick=e=>{if(e.target===wrap)closeModal()};if($('#watch'))$('#watch').onclick=()=>{const p=localPrefs(),id=state.selected.id;p[id]={...(p[id]||{}),watched:!state.selected.watched};store.set('radarPrefs',p);wrap.remove();render()};if($('#reject'))$('#reject').onclick=()=>{const p=localPrefs(),id=state.selected.id;p[id]={...(p[id]||{}),rejected:!state.selected.rejected};store.set('radarPrefs',p);wrap.remove();render()};if($('#createOpp'))$('#createOpp').onclick=()=>{const m=store.get('radarManual',[]);m.push({id:'local-'+Date.now(),title:$('#n_title').value||'Untitled opportunity',organization:$('#n_org').value||'Unknown',country:$('#n_country').value,stage:$('#n_stage').value,score:+$('#n_score').value||60,confidence:50,summary:$('#n_summary').value,source_url:safeUrl($('#n_source')?.value||''),source_label:'Original source',documents:($('#n_documents')?.value||'').split(/\n+/).map(x=>x.trim()).filter(x=>safeUrl(x)).map((url,i)=>({title:'Document '+(i+1),url:safeUrl(url),kind:inferResourceKind('Document '+(i+1),safeUrl(url),'Document')})),sample:false,updated_at:new Date().toISOString(),evidence:[]});store.set('radarManual',m);wrap.remove();render()}}
function bind(){document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>{state.page=b.dataset.nav;render()});document.querySelectorAll('[data-open]').forEach(x=>{x.onclick=()=>openDetail(x.dataset.open);x.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openDetail(x.dataset.open)}}});if($('#newOpp'))$('#newOpp').onclick=()=>{state.modal='new';renderModal()};if($('#mobileMore'))$('#mobileMore').onclick=()=>{state.modal='more';renderModal()};if(state.page==='opportunities'){['q','stageFilter','scoreFilter','watchFilter'].forEach(id=>$('#'+id).oninput=filterOpps)}if($('#saveSettings'))$('#saveSettings').onclick=()=>{['company_name','capability_profile','weight_fit','weight_budget','weight_geo','weight_timing','weight_confidence','weight_strategy'].forEach(k=>state.settings[k]=$('#'+k).value);store.set('radarSettings',state.settings);alert('Saved locally.')};if($('#exportBtn'))$('#exportBtn').onclick=exportData;if($('#importBtn'))$('#importBtn').onclick=importData}
function filterOpps(){const q=$('#q').value.toLowerCase(),st=$('#stageFilter').value,min=+$('#scoreFilter').value,w=$('#watchFilter').checked;const o=mergedOpps().filter(x=>!x.rejected&&(!q||[x.title,x.organization,x.country,x.city,x.summary].join(' ').toLowerCase().includes(q))&&(!st||x.stage===st)&&x.score>=min&&(!w||x.watched));$('#oppResults').innerHTML=table(o);document.querySelectorAll('[data-open]').forEach(x=>x.onclick=()=>openDetail(x.dataset.open))}
function exportData(){const blob=new Blob([JSON.stringify({prefs:localPrefs(),manual:store.get('radarManual',[]),settings:state.settings},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='museum-radar-local-backup.json';a.click();URL.revokeObjectURL(a.href)}
function importData(){const i=document.createElement('input');i.type='file';i.accept='application/json';i.onchange=()=>{const r=new FileReader();r.onload=()=>{try{const d=JSON.parse(r.result);if(d.prefs)store.set('radarPrefs',d.prefs);if(d.manual)store.set('radarManual',d.manual);if(d.settings)store.set('radarSettings',d.settings);location.reload()}catch(e){alert('Invalid backup file')}};r.readAsText(i.files[0])};i.click()}
const AUTH_KEY='museumRadarAuthUntil';
const AUTH_DAYS=30;
const AUTH_HASH='8d2d60b662ab63b0db7eb631d0f0cc8f4da456ea791dd66eb6f16c8309fc914c';

function authValid(){
  const until=Number(localStorage.getItem(AUTH_KEY)||0);
  return until>Date.now();
}
async function sha256(text){
  const bytes=new TextEncoder().encode(text);
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
function showLogin(){
  const app=document.querySelector('#app');
  app.innerHTML=`<main class="loginPage">
    <section class="loginCard" aria-labelledby="loginTitle">
      <div class="loginBrand">Museum Radar</div>
      <h1 id="loginTitle">Enter password</h1>
      <p>Access is remembered on this browser for 30 days.</p>
      <form id="loginForm">
        <label for="loginPassword">Password</label>
        <input id="loginPassword" type="password" autocomplete="current-password" autofocus>
        <div id="loginError" class="loginError" role="alert" aria-live="polite"></div>
        <button class="btn primary loginButton" type="submit">Enter</button>
      </form>
    </section>
  </main>`;
  const form=document.querySelector('#loginForm');
  const input=document.querySelector('#loginPassword');
  const error=document.querySelector('#loginError');
  form.onsubmit=async e=>{
    e.preventDefault();
    const hash=await sha256(input.value);
    if(hash!==AUTH_HASH){
      error.textContent='Incorrect password.';
      input.select();
      return;
    }
    localStorage.setItem(AUTH_KEY,String(Date.now()+AUTH_DAYS*24*60*60*1000));
    app.innerHTML='<div class="empty">Loading Radar…</div>';
    load().catch(err=>{app.innerHTML=`<div class="empty">Could not load Radar: ${escapeHtml(err.message)}</div>`});
  };
}
function bootstrap(){
  if(authValid()){
    load().catch(e=>{$('#app').innerHTML=`<div class="empty">Could not load Radar: ${escapeHtml(e.message)}</div>`});
  }else{
    showLogin();
  }
}
bootstrap();
