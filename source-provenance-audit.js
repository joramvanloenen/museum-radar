/* Source provenance audit: distinguish recorded links, independent hosts, and unverified claims. */
(function(){
 const previous=window.renderModal,esc=s=>escapeHtml(s??'');
 const domain=u=>{try{return new URL(u).hostname.toLowerCase().replace(/^www\./,'')}catch{return ''}};
 const url=x=>typeof x==='string'?x:x?.url||x?.source_url||'';
 const canonical=u=>{try{const x=new URL(u);x.hash='';return x.href.replace(/\/$/,'')}catch{return ''}};
 function audit(o){
  const candidates=[o.source_url,...(o.documents||[]).map(url),...(o.evidence||[]).map(url),...(o.sources||[]).map(url)];
  const unique=[...new Set(candidates.map(canonical).filter(Boolean))];
  const domains=[...new Set(unique.map(domain).filter(Boolean))];
  const evidence=(o.evidence||[]).filter(e=>e&&(e.title||e.detail||e.source_url));
  const claimed=Number(o.prediction?.source_diversity||0);
  const mismatched=claimed>domains.length;
  const predicted=o.source_key==='research_agent';
  return {unique,domains,evidence,claimed,mismatched,predicted,verified:!!o.verified};
 }
 window.renderModal=function(){
  const result=previous.apply(this,arguments);
  if(state.modal!=='detail'||!state.selected)return result;
  const o=state.selected,a=audit(o),section=document.querySelector('.detailModal .sourcesSection');
  if(!section)return result;
  const box=document.createElement('div');box.className='sourceAudit';
  const provenance=a.verified?'Record marked verified; links not rechecked live':a.predicted?'Predicted lead; source claims not independently checked':'Source links recorded; live verification not performed';
  box.innerHTML='<h4>Source provenance audit</h4><div class="sourceAuditStats"><span><b>'+a.unique.length+'</b> unique links</span><span><b>'+a.domains.length+'</b> linked domains</span><span><b>'+a.evidence.length+'</b> evidence notes</span></div><p>'+esc(provenance)+'</p>'+
  (a.mismatched?'<p class="sourceAuditWarning">⚠ Prediction metadata claims '+a.claimed+' independent source domains, but only '+a.domains.length+' domain'+(a.domains.length===1?' is':'s are')+' linked in this record. Additional sources must be supplied before this claim can be verified.</p>':'')+
  (a.domains.length===1?'<p>Multiple links on the same domain are not independent sources.</p>':'')+
  (!a.unique.length?'<p class="sourceAuditWarning">No source URLs attached. Do not treat this as a verified opportunity.</p>':'')+
  '<p class="sourceAuditFoot">This is a record-level provenance check, not a live HTTP test or confirmation of the procurement status.</p>';
  section.appendChild(box);
  return result;
 };
 const style=document.createElement('style');style.textContent='.sourceAudit{margin:18px 0;padding:14px;background:#f0efe9;border:1px solid #d4d1c7;border-radius:9px}.sourceAudit h4{font-size:13px;text-transform:uppercase;letter-spacing:.04em;margin:0 0 12px}.sourceAuditStats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.sourceAuditStats span{background:#fffefa;border-radius:6px;padding:9px 5px;font-size:11px;text-align:center}.sourceAuditStats b{display:block;font-size:21px}.sourceAudit p{font-size:12px!important;line-height:1.5!important;margin:10px 0 0!important}.sourceAuditWarning{background:#fff1dc;padding:10px;border-left:3px solid #b4741c}.sourceAuditFoot{color:#686868}@media(max-width:700px){.sourceAudit{padding:12px}.sourceAuditStats b{font-size:19px}}';document.head.appendChild(style);
})();
