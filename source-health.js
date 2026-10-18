// Source availability is advisory: cross-origin checks can be blocked even when a site works.
(function(){
 const HOST='www.sell2wales.gov.wales';
 const safe=u=>{try{const x=new URL(u);return /^https?:$/.test(x.protocol)?x:null}catch{return null}};
 const official=o=>{
  const arr=[...(o.documents||[]),...(o.sources||[]),...(o.evidence||[])];
  const links=arr.map(x=>typeof x==='string'?x:x.url||x.source_url).filter(Boolean);
  return [...new Set(links)].filter(u=>{const x=safe(u);return x&&x.hostname!==HOST&&/find-tender.service.gov.uk|contracts-finder.service.gov.uk|ted.europa.eu|op.europa.eu|etenders.gov.ie|publiccontractsscotland.gov.uk/.test(x.hostname)});
 };
 function enhance(){
  const o=window.state?.selected|| (typeof state!=='undefined'?state.selected:null);
  if(!o||!document.querySelector('.detailModal'))return;
  const links=[...document.querySelectorAll('.detailModal a[href]')].filter(a=>safe(a.href)?.hostname===HOST);
  if(!links.length)return;
  const section=document.createElement('div');section.className='sourceHealthPanel';
  const title=document.createElement('strong');title.textContent='Source availability';section.append(title);
  const msg=document.createElement('p');msg.textContent='Checking Sell2Wales…';section.append(msg);
  const backups=official(o);
  if(backups.length){const label=document.createElement('div');label.textContent='Alternative official notices';section.append(label);backups.forEach(u=>{const a=document.createElement('a');a.href=u;a.target='_blank';a.rel='noopener noreferrer';a.textContent=new URL(u).hostname+' ↗';section.append(a)})}
  const search=document.createElement('a');search.href='https://www.find-tender.service.gov.uk/Search/Results?SearchType=1&Keywords='+encodeURIComponent(o.title||o.organization||'');search.target='_blank';search.rel='noopener noreferrer';search.textContent='Search Find a Tender (not a verified match) ↗';section.append(search);
  const parent=links[0].closest('.detailSection')||links[0].parentElement;parent.append(section);
  const ctl=new AbortController(),timeout=setTimeout(()=>ctl.abort(),6500);
  fetch('https://www.sell2wales.gov.wales/',{mode:'no-cors',cache:'no-store',signal:ctl.signal}).then(()=>{msg.textContent='Sell2Wales responded to a connectivity check. Individual notice availability is not confirmed.'}).catch(()=>{msg.textContent='Sell2Wales could not be checked from this browser (offline, unavailable or cross-origin restrictions). Try the original link or alternatives.'}).finally(()=>clearTimeout(timeout));
 }
 const observer=new MutationObserver(()=>{if(document.querySelector('.detailModal')&&!document.querySelector('.sourceHealthPanel'))enhance()});
 observer.observe(document.body,{subtree:true,childList:true});
 const css=document.createElement('style');css.textContent='.sourceHealthPanel{display:flex;flex-direction:column;align-items:flex-start;gap:8px;margin-top:12px;padding:12px;border:1px solid var(--line,#344);border-radius:10px}.sourceHealthPanel p{margin:0;font-size:12px;line-height:1.4;opacity:.8}.sourceHealthPanel a{font-size:12px;text-decoration:underline;text-underline-offset:3px}.sourceHealthPanel>div{font-size:11px;font-weight:700;opacity:.75}';document.head.append(css);
})();
