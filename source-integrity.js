/* Make source reporting evidence-led and internally consistent. */
(function(){
const base=window.renderModal;
const esc=s=>escapeHtml(s??'');
function links(o){
 const found=new Map();
 const add=(url,label,kind)=>{const safe=safeUrl(url);if(!safe)return;const key=safe.replace(/\/$/,'');if(!found.has(key))found.set(key,{url:safe,label:label||new URL(safe).hostname,kind:kind||'Source link'})};
 add(o.source_url,o.source_label==='Research Agent source'?'Project source':o.source_label||'Original source','Primary link');
 for(const d of o.documents||[])if(typeof d==='string')add(d,'Document','Document');else add(d.url,d.title||d.name||'Document',d.kind||'Document');
 for(const e of o.evidence||[])add(e.source_url,e.source_label||e.title||'Supporting evidence',e.kind||'Evidence');
 for(const s of o.sources||[])if(typeof s==='string')add(s,'Additional source','Source');else add(s.url||s.source_url,s.title||s.label||'Additional source',s.kind||'Source');
 return [...found.values()];
}
window.renderModal=function(){
 const result=base.apply(this,arguments);
 if(state.modal!=='detail'||!state.selected)return result;
 const o=state.selected,modal=document.querySelector('.detailModal');if(!modal)return result;
 const sections=[...modal.querySelectorAll('.detailSection')];
 const resources=sections.find(s=>/found here\s*\/\s*documents/i.test(s.querySelector('h3')?.textContent||''));
 const sources=modal.querySelector('.sourcesSection');
 const all=links(o),evidence=(o.evidence||[]).filter(e=>e&&typeof e==='object'&&(e.title||e.detail||e.source_url));
 const item=l=>`<a class="resourceLink" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer"><span><small>${esc(l.kind)}</small><b>${esc(l.label)}</b><small class="sourceDomain">${esc(new URL(l.url).hostname)}</small></span><span class="resourceArrow">↗</span></a>`;
 if(resources){
  resources.innerHTML='<h3>Source links & documents</h3>'+(all.length?'<div class="resourceList">'+all.map(item).join('')+'</div>':'<div class="resourceEmpty">No verifiable source URL is attached to this record. Check the original project before taking action.</div>');
 }
 if(sources){
  const descriptions=evidence.map(e=>`<div class="evidence"><div class="evidenceItem"><b>${esc(e.title||'Supporting evidence')}</b><small>${esc(e.date||'')} ${esc(e.kind||'')}</small><div>${esc(e.detail||'')}</div>${safeUrl(e.source_url)?`<a href="${esc(safeUrl(e.source_url))}" target="_blank" rel="noopener noreferrer">Open evidence ↗</a>`:''}</div></div>`).join('');
  sources.innerHTML='<h3>Evidence & verification</h3><p class="sourceVerification">${all.length} recorded source link${all.length===1?'':'s'} · ${evidence.length} structured evidence entr${evidence.length===1?'y':'ies'}.</p>'+(descriptions||'<p class="sourceVerification">No separate evidence notes are recorded. The source link above is not an independent verification or a second source.</p>');
 }
 const facts=modal.querySelector('.detailFacts .factList');
 if(facts){
  [...facts.querySelectorAll('.fact')].forEach(f=>{
   const h=f.querySelector('h3')?.textContent.trim().toLowerCase();
   if(h==='independent sources'||h==='source quality')f.remove();
  });
  if(o.source_key==='research_agent'){
   const row=document.createElement('div');row.className='fact';row.innerHTML='<h3>Recorded source links</h3><div>'+all.length+'</div>';
   facts.prepend(row);
   const disclaimer=document.createElement('div');disclaimer.className='fact sourceCaveat';disclaimer.innerHTML='<h3>Verification status</h3><div>Research prediction · independently confirm source claims and procurement status.</div>';
   facts.prepend(disclaimer);
  }
 }
 return result;
};
const style=document.createElement('style');style.textContent='.sourceVerification{font-size:13px!important;line-height:1.5!important;color:#555!important;margin:8px 0 13px!important}.sourceDomain{display:block;color:#666;font-size:11px;margin-top:4px}.sourceCaveat div{font-size:12px;line-height:1.5}.sourcesSection .evidence{margin-bottom:9px}';document.head.append(style);
})();