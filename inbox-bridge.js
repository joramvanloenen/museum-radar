/* Personal inbox controls: stored on this device, independent of Watch/Reject. */
(function(){
 const KEY='radarInboxV1';
 let data;try{data=JSON.parse(localStorage.getItem(KEY))||{seen:{},hidden:{},showHidden:false}}catch{data={seen:{},hidden:{},showHidden:false}}
 data.seen ||= {};data.hidden ||= {};
 const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(data))}catch(e){console.warn('Inbox preferences could not be saved',e)}};
 const idOf=el=>el?.getAttribute('data-open');
 function decorate(){
  const main=document.querySelector('.main');if(!main)return;
  const home=typeof state!=='undefined'&&state.page==='overview';
  if(home){
   const intro=main.querySelector('.homeIntro')||main.querySelector('.actionMetrics');
   if(intro&&!main.querySelector('.inboxControls')){
    const bar=document.createElement('div');bar.className='inboxControls';
    bar.innerHTML='<div class="inboxLabel"><strong>My inbox</strong><span class="inboxCount" aria-live="polite"></span></div><label class="inboxToggle"><input type="checkbox" id="showHiddenRadar"><span>Show hidden</span></label>';
    intro.before(bar);bar.querySelector('input').checked=!!data.showHidden;
    bar.querySelector('input').addEventListener('change',e=>{data.showHidden=e.target.checked;save();decorate()});
   }
  }
  let fresh=0,hidden=0;
  main.querySelectorAll('.actionCard[data-open]').forEach(card=>{
   const id=idOf(card),isHidden=!!data.hidden[id],seen=!!data.seen[id];
   if(!seen&&!isHidden)fresh++;
   if(isHidden)hidden++;
   card.classList.toggle('inboxHidden',isHidden);
   card.classList.toggle('inboxUnseen',!seen);
   card.hidden=home&&isHidden&&!data.showHidden;
   let top=card.querySelector('.actionTop');
   if(top&&!card.querySelector('.inboxStatus')){
    const status=document.createElement('span');status.className='inboxStatus';top.insertBefore(status,top.firstChild);
    const btn=document.createElement('button');btn.type='button';btn.className='inboxHide';btn.setAttribute('aria-label','Hide opportunity');btn.textContent='Hide';
    btn.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();data.hidden[id]=!data.hidden[id];save();decorate()});
    btn.addEventListener('keydown',e=>e.stopPropagation());
    card.append(btn);
   }
   const status=card.querySelector('.inboxStatus');if(status)status.textContent=isHidden?'HIDDEN':seen?'SEEN':'NEW';
   const btn=card.querySelector('.inboxHide');if(btn){btn.textContent=isHidden?'Unhide':'Hide';btn.setAttribute('aria-label',(isHidden?'Unhide ':'Hide ')+(card.querySelector('h3')?.textContent||'opportunity'))}
  });
  if(home){
   // Keep summary cards visible even when no results remain.
   const count=main.querySelector('.inboxCount');if(count)count.textContent=fresh+' new · '+Object.keys(data.hidden).filter(id=>data.hidden[id]).length+' hidden';
   main.querySelectorAll('.actionList,.compactCards').forEach(list=>{
    let empty=list.querySelector('.inboxEmpty');
    const visible=[...list.querySelectorAll('.actionCard')].some(c=>!c.hidden);
    if(!visible&&!empty){empty=document.createElement('p');empty.className='inboxEmpty';empty.textContent='No visible opportunities here. Turn on Show hidden to review hidden items.';list.append(empty)}
    if(visible&&empty)empty.remove();
   });
   main.querySelectorAll('.updateStrip [data-open]').forEach(el=>{el.hidden=!!data.hidden[idOf(el)]&&!data.showHidden});
  }
 }
 const oldOpen=window.openDetail;
 if(typeof oldOpen==='function')window.openDetail=function(id){
  data.seen[id]=Date.now();save();
  document.querySelectorAll('.actionCard[data-open]').forEach(c=>{if(idOf(c)===String(id)){c.classList.remove('inboxUnseen');const s=c.querySelector('.inboxStatus');if(s)s.textContent='SEEN'}});
  return oldOpen.apply(this,arguments);
 };
 const oldRender=window.render;
 if(typeof oldRender==='function')window.render=function(){const r=oldRender.apply(this,arguments);decorate();return r};
 document.addEventListener('DOMContentLoaded',decorate);
 const style=document.createElement('style');
 style.textContent=`
 .inboxControls{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0 18px;padding:11px 0;border-top:1px solid #c9c3b8;border-bottom:1px solid #c9c3b8}
 .inboxLabel{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.inboxLabel strong{font-size:15px}.inboxCount{font-size:12px;color:#555}
 .inboxToggle{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;white-space:nowrap;cursor:pointer}
 .inboxToggle input{width:15px;height:15px;accent-color:#101010;margin:0}
 .actionCard[hidden],.updateStrip [hidden]{display:none!important}
 .actionCard{position:relative}
 .actionTop{flex-wrap:wrap}
 .inboxStatus{display:inline-flex;font-size:10px;letter-spacing:.05em;font-weight:850;border-radius:5px;padding:4px 7px;background:#e4e0d7;color:#45413a}
 .inboxUnseen .inboxStatus{background:#d9ff3f;color:#101010}
 .inboxHide{position:relative;display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:5px 12px;margin-top:12px;border:1px solid #a6a198;border-radius:8px;background:transparent;color:#333;font-size:12px;font-weight:800;cursor:pointer}
 .inboxHide:hover{background:#eae7df}
 .inboxHidden{opacity:.7}
 .inboxEmpty{font-size:13px;color:#57544d;line-height:1.5}
 @media(max-width:700px){
 .inboxControls{gap:8px;margin:10px 0 16px}
 .inboxLabel{gap:2px 8px}.inboxLabel strong{font-size:14px}.inboxCount{font-size:11px}
 .inboxToggle{font-size:11px}
 .inboxStatus{font-size:10px}
 .inboxHide{min-height:44px;font-size:13px;padding:9px 14px;margin-top:12px}
 .actionCard .actionOpen{margin-top:10px!important}
 }
 `;
 document.head.append(style);
})();
