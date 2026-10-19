/* Restore current section and open opportunity after browser refresh. */
(function(){
 const KEY='museumRadarLocationV1';
 const pages=new Set(['overview','opportunities','future','pitch','organizations','sources','scout','activity','settings','recon']);
 const read=()=>{try{return JSON.parse(sessionStorage.getItem(KEY)||'{}')}catch{return {}}};
 const write=x=>{try{sessionStorage.setItem(KEY,JSON.stringify(x))}catch{}};
 const validPage=x=>pages.has(x)?x:'overview';
 const fromHash=()=>{
  const h=location.hash.slice(1);
  if(!h)return null;
  const q=new URLSearchParams(h);
  if(!q.has('page')&&!q.has('opportunity'))return null;
  return {page:validPage(q.get('page')),opportunity:q.get('opportunity')||null};
 };
 const start=fromHash()||read();
 state.page=validPage(start.page);
 let restoreId=typeof start.opportunity==='string'?start.opportunity:null;
 let lastLocation='';
 const sync=()=>{
  const id=state.modal==='detail'&&state.selected?.id?String(state.selected.id):null;
  const page=validPage(state.page);
  const hash='#'+new URLSearchParams({page,...(id?{opportunity:id}:{})}).toString();
  const signature=page+'|'+(id||'');
  if(signature===lastLocation)return;
  lastLocation=signature;
  write({page,opportunity:id});
  if(location.hash!==hash)history.replaceState(null,'',location.pathname+location.search+hash);
 };
 const originalRender=window.render;
 window.render=function(){const result=originalRender.apply(this,arguments);sync();return result};
 const originalModal=window.renderModal;
 window.renderModal=function(){const result=originalModal.apply(this,arguments);sync();return result};
 const originalOpen=window.openDetail;
 window.openDetail=function(id){const result=originalOpen.apply(this,arguments);sync();return result};
 document.addEventListener('click',e=>{
  if(e.target.closest('[data-close]')||e.target.classList.contains('modalback')){
   queueMicrotask(sync);
  }
 },true);
 window.addEventListener('hashchange',()=>{
  const target=fromHash();if(!target)return;
  const page=validPage(target.page);
  if(state.page!==page){state.page=page;window.render()}
  if(target.opportunity&&state.selected?.id!==target.opportunity){
   if(typeof getOpp==='function'&&getOpp(target.opportunity))window.openDetail(target.opportunity);
  }else if(!target.opportunity&&state.modal==='detail'){
   document.querySelectorAll('.modalback').forEach(el=>el.remove());
   document.body.classList.remove('modal-open');state.modal=null;state.selected=null;sync();
  }
 });
 const originalLoad=window.load;
 // load() is invoked from app.js lexical scope; restore the modal after initial data render.
 const observer=new MutationObserver(()=>{
  if(!restoreId||!state.opps?.length||!document.querySelector('.layout'))return;
  const id=restoreId;restoreId=null;
  if(typeof getOpp==='function'&&getOpp(id))queueMicrotask(()=>window.openDetail(id));
 });
 observer.observe(document.querySelector('#app'),{childList:true,subtree:false});
 window.addEventListener('pagehide',()=>{write({page:validPage(state.page),opportunity:state.modal==='detail'?state.selected?.id:null})});
})();
