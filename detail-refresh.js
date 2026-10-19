(function(){
const old=window.renderModal;
window.renderModal=function(){
 old.apply(this,arguments);
 if(state.modal!=='detail')return;
 const modal=document.querySelector('.detailModal'),main=modal?.querySelector('.detailMain'),box=main?.querySelector('.decisionBox'),facts=modal?.querySelector('.detailFacts');
 if(!main||!box)return;
 modal.classList.add('detailRefined');
 const title=main.querySelector('h1'),summary=main.querySelector('p.sub'),org=main.querySelector('.kicker');
 const o=state.selected||{};
 const info=document.createElement('div');info.className='detailQuickInfo';
 const deadline=o.deadline?new Date(o.deadline):null;
 const date=deadline&&!isNaN(deadline)?deadline.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):o.procurement_window||'Not confirmed';
 info.innerHTML='<span><b>Deadline</b> '+escapeHtml(date)+'</span><span><b>Score</b> '+escapeHtml(o.score||'—')+'</span><span><b>Budget</b> '+escapeHtml(typeof fmtMoney==='function'?fmtMoney(o):'—')+'</span>';
 title?.insertAdjacentElement('afterend',info);
 if(summary){const details=document.createElement('details');details.className='detailSummary';details.innerHTML='<summary>Project description</summary>';summary.replaceWith(details);details.append(summary)}
 const grid=box.querySelector('.decisionGrid');
 if(grid){const details=document.createElement('details');details.className='detailScoreDetails';details.innerHTML='<summary>Why this score? <span>▾</span></summary>';grid.replaceWith(details);details.append(grid)}
 const action=box.querySelector('p');if(action){action.classList.add('detailRecommended');box.prepend(action)}
 const head=box.querySelector('.decisionHead');if(head)head.querySelector('strong')?.remove();
 const actions=facts?.querySelector('.detailActions');
 if(actions){actions.classList.add('detailQuickActions');box.append(actions)}
 const resources=main.querySelector('.resourceList');
 if(resources){const first=resources.querySelector('a');if(first){const a=first.cloneNode(true);a.className='detailPrimarySource';a.textContent='Open original source ↗';box.append(a)}}
 if(org)org.classList.add('detailOrg');
};
})();