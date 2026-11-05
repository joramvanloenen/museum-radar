/* Trust gate: do not promote unverified leads as ready to bid or pitch. */
(function(){
 const base=window.mergedOpps;
 function actualUrl(raw){
  try{
   const u=new URL(raw);
   if(/(^|\.)bing\.com$/i.test(u.hostname)&&u.pathname.includes('/news/apiclick')){
    const target=u.searchParams.get('url');
    if(target&&/^https?:\/\//i.test(target))return target;
   }
   return raw;
  }catch{return raw}
 }
 window.mergedOpps=function(){
  return base().map(o=>{
   const source=actualUrl(o.source_url||'');
   const wasRedirect=/^https?:\/\/(www\.)?bing\.com\/news\/apiclick/i.test(o.source_url||'');
   const cancelled=o.project_id==='project-pendine-through-time';
   const past=!!(o.deadline&&/^\d{4}-\d{2}-\d{2}$/.test(o.deadline)&&new Date(o.deadline+'T23:59:59').getTime()<Date.now());
   const unverified=o.source_key==='search_pitch'||wasRedirect||o.source_key==='research_agent';
   let status=cancelled?'CANCELLED':past?'DEADLINE PASSED':unverified?'RESEARCH ONLY':o.verified?'RECORD VERIFIED':'CHECK SOURCE';
   const route=o.decision?.route;
   const blocked=cancelled||past||unverified;
   const action=cancelled?'Official notice confirms the open competition was cancelled on 23 October 2026. Buyer intends a framework call-off; identify framework supplier before pursuing subcontract work.':past?'Submission deadline has passed. Check the official notice for extension, award or cancellation before taking action.':unverified?'Validate project scope, buyer, current timing and a direct source before approaching anyone.':o.next_action;
   const decision=o.decision?{...o.decision,route:blocked?(cancelled?'CANCELLED':past?'CLOSED / CHECK':'VERIFY FIRST'):route,action,urgency:blocked?0:o.decision.urgency}:o.decision;
   return {...o,source_url:source,source_label:wasRedirect?'Original publisher link':o.source_label,verification_gate:status,decision,next_action:action, ...(cancelled?{stage:'Cancelled',expired:true,verified:true,deadline:'2026-09-07'}:{})};
  });
 };
 const prior=window.renderModal;
 window.renderModal=function(){
  const result=prior.apply(this,arguments);
  if(state.modal!=='detail'||!state.selected)return result;
  const o=window.mergedOpps().find(x=>String(x.id)===String(state.selected.id));if(!o)return result;
  const main=document.querySelector('.detailModal .detailMain');if(!main)return result;
  const note=document.createElement('div');note.className='trustGate';
  note.innerHTML='<strong>'+escapeHtml(o.verification_gate)+'</strong><span>'+escapeHtml(o.decision?.action||'Check source and status before action.')+'</span>';
  main.querySelector('h1')?.insertAdjacentElement('afterend',note);
  const decision=document.querySelector('.detailModal .decisionBox');
  if(decision&&o.decision){const badge=decision.querySelector('.routeBadge');if(badge)badge.textContent=o.decision.route;const para=decision.querySelector('p');if(para)para.innerHTML='<b>Recommended action:</b> '+escapeHtml(o.decision.action)}
  return result;
 };
 const style=document.createElement('style');style.textContent='.trustGate{padding:12px 14px;margin:12px 0;background:#fff1d7;border-left:4px solid #b97719;color:#28231a;border-radius:5px;display:grid;gap:5px}.trustGate strong{font-size:11px;letter-spacing:.07em}.trustGate span{font-size:13px;line-height:1.5}.routeBadge{max-width:100%}';document.head.append(style);
})();