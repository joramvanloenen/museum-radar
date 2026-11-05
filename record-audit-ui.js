/* Static source audit badges. No claim of live HTTP validation. */
(function(){
const original=window.renderModal;let audit=null;
fetch('./data/source-audit.json').then(r=>r.ok?r.json():null).then(x=>{audit=x}).catch(()=>{});
window.renderModal=function(){
 const result=original.apply(this,arguments);
 if(state.modal!=='detail'||!state.selected||!audit)return result;
 const o=state.selected,record=audit.items.find(x=>x.id===(o.id||o.project_id));if(!record)return result;
 const section=document.querySelector('.detailModal .sourcesSection');if(!section)return result;
 const wrap=document.createElement('div');wrap.className='recordAuditFlags';
 const names={past_deadline_labeled_live:'Recorded tender deadline has passed — check amendments and awards',verified_flag_without_verification_record:'Verified label has no explicit verification log',non_https_source:'Source uses unencrypted HTTP',search_engine_redirect_source:'Source is a Bing redirect, not a direct publisher link',no_verified_supporting_evidence:'No independently checked supporting evidence',claimed_independent_sources_not_linked:'Claimed additional source domains lack attached URLs'};
 wrap.innerHTML='<h4>Record integrity checks</h4>'+(record.flags.length?'<ul>'+record.flags.map(f=>'<li>'+escapeHtml(names[f]||f)+'</li>').join('')+'</ul>':'<p>No structural flags found. Source content and live status still require verification.</p>')+'<small>Static inventory audit · 5 Nov 2026 · not a live website check</small>';
 section.prepend(wrap);return result;
};
const style=document.createElement('style');style.textContent='.recordAuditFlags{border:1px solid #d1cdc4;background:#f5f3ed;border-radius:8px;padding:12px;margin:12px 0}.recordAuditFlags h4{font-size:13px;margin:0 0 8px}.recordAuditFlags ul{padding-left:18px;margin:0 0 9px}.recordAuditFlags li{font-size:12px;line-height:1.5;margin:5px 0}.recordAuditFlags small{color:#666;font-size:11px}.recordAuditFlags p{font-size:12px}';document.head.append(style);
})();
