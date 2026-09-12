// Museum Radar decision layer
// Separates project attractiveness from the practical route for YIPP, a specialist interactive studio.
(function(){
  const clean=s=>String(s||'').toLowerCase();
  const clamp=n=>Math.max(0,Math.min(100,Math.round(n)));
  const words=(o)=>clean([o.title,o.summary,o.fit_rationale,o.pitch_angle,o.next_action,(o.prediction?.signals||[]).join(' '),(o.prediction?.fit_terms||[]).join(' ')].join(' '));
  const has=(t,re)=>re.test(t);

  function decision(o){
    const t=words(o), base=Number(o.score)||50, conf=Number(o.confidence)||50;
    const interactive=has(t,/interactive|interactiv|immersive|multimedia|digital experience|realtime|real-time|projection|sensor|software|game|av\b|audio visual|audiovisual|media design|exhibit maker|hands-on|visitor experience/);
    const specialist=has(t,/interactive (design|production|exhibit|installation)|digital experience|immersive|multimedia|software|projection mapping|exhibit maker|media production/);
    const main=has(t,/main contractor|principal contractor|single supplier|single contractor|turnkey|design\s*(?:&|and)\s*build|full fit.?out|general contractor|complete exhibition|exhibition build/);
    const sub=has(t,/subcontract|sub-contractor|specialist contractor|specialist supplier|supply chain|nominated subcontract/);
    const lots=has(t,/\blot\b|\blots\b|separate package|specialist package|work package/);
    const construction=has(t,/construction|building works|architectural services|structural|m&e\b|mechanical and electrical|civil works/);
    const framework=has(t,/framework/);
    const directLanguage=has(t,/interactive(s)? makers|interactive exhibit|digital experience|multimedia (design|production)|software development|av integrator|audiovisual integrator|media design/);

    let capability=base;
    if(interactive) capability+=8;
    if(specialist) capability+=8;
    if(!interactive) capability-=20;
    if(construction&&!specialist) capability-=18;
    capability=clamp(capability);

    let access=70;
    if(directLanguage||lots) access+=20;
    if(main) access-=30;
    if(main&&construction) access-=15;
    if(sub) access+=10;
    if(o.stage==='Live Tender') access+=5;
    if(o.expired) access-=25;
    access=clamp(access);

    let commercial=60;
    if(specialist) commercial+=18;
    if(directLanguage) commercial+=12;
    if(main&&!lots) commercial-=22;
    if(construction&&!lots) commercial-=15;
    if(framework) commercial-=5;
    commercial=clamp(commercial);

    const strategic=clamp(base*.65+conf*.35+(interactive?5:0));
    let route='WATCH / RESEARCH';
    if(o.expired&&main) route='CONTACT WINNER';
    else if(main&&(interactive||specialist)) route=sub?'SUBCONTRACT':'FIND MAIN CONTRACTOR';
    else if((directLanguage||lots)&&interactive) route='DIRECT BID';
    else if(o.stage==='Pitch'&&interactive) route='PITCH NOW';
    else if(o.stage==='Live Tender'&&interactive) route='DIRECT BID';
    else if(!interactive&&capability<50) route='LOW FIT';

    let action=o.next_action||'Research the opportunity';
    if(route==='FIND MAIN CONTRACTOR') action='Do not treat the full tender as a direct YIPP bid. Identify the exhibition/main contractor and approach them for the interactive package.';
    if(route==='SUBCONTRACT') action='Identify or contact the lead bidder/main contractor and position YIPP as the specialist interactive partner.';
    if(route==='CONTACT WINNER') action='Find the awarded main contractor and contact them about unassigned interactive/digital packages.';
    if(route==='DIRECT BID') action='Review eligibility and tender requirements now; this appears structured for a specialist supplier like YIPP.';
    if(route==='PITCH NOW') action='Approach the client/design team before specialist packages are fixed.';
    if(route==='LOW FIT') action='Low specialist-interactive fit. Keep only if it exposes a useful downstream partner or package.';

    const urgency=o.expired?20:(o.stage==='Live Tender'?95:['Pre-market','Expected'].includes(o.stage)?75:o.stage==='Pitch'?70:50);
    const overall=clamp(capability*.34+access*.24+commercial*.18+strategic*.14+urgency*.10);
    return {overall,capability,access,commercial,strategic,urgency,route,action,main,interactive};
  }

  const previousMerged=window.mergedOpps;
  if(typeof previousMerged==='function'){
    window.mergedOpps=function(){return previousMerged().map(o=>{const d=decision(o);return {...o,decision:d,score:d.overall,original_score:o.original_score??o.score,next_action:d.action};}).sort((a,b)=>b.score-a.score)};
  }

  const baseModal=window.renderModal;
  if(typeof baseModal==='function'){
    window.renderModal=function(){
      baseModal();
      if(state.modal!=='detail'||!state.selected)return;
      const modal=document.querySelector('.detailModal'); if(!modal)return;
      const o=getOpp(state.selected.id),d=o?.decision||decision(o||state.selected);
      const main=modal.querySelector('.detailMain');
      const facts=modal.querySelector('.detailFacts');
      if(main){
        const box=document.createElement('section'); box.className='decisionBox';
        box.innerHTML=`<div class="decisionHead"><span class="routeBadge">${escapeHtml(d.route)}</span><strong>${d.overall} opportunity</strong></div><div class="decisionGrid"><div><b>${d.capability}</b><span>Package fit</span></div><div><b>${d.access}</b><span>Access</span></div><div><b>${d.commercial}</b><span>Commercial</span></div><div><b>${d.strategic}</b><span>Strategic</span></div></div><p><b>Recommended action:</b> ${escapeHtml(d.action)}</p>`;
        const h1=main.querySelector('h1'); h1?.insertAdjacentElement('afterend',box);
      }
      if(facts){const label=facts.querySelector('.scoreLabel');if(label)label.textContent='YIPP opportunity score';}
    };
  }

  const css=document.createElement('style');
  css.textContent=`.decisionBox{margin:18px 0;padding:18px;border:1px solid var(--line,#283241);border-radius:14px;background:rgba(255,255,255,.025)}.decisionHead{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.routeBadge{font-size:12px;font-weight:800;letter-spacing:.07em;padding:7px 10px;border-radius:8px;background:#fff;color:#111}.decisionGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.decisionGrid>div{padding:10px;border-radius:9px;background:rgba(255,255,255,.04)}.decisionGrid b{display:block;font-size:20px}.decisionGrid span{font-size:11px;opacity:.65}.decisionBox p{margin:14px 0 0;line-height:1.45}@media(max-width:700px){.decisionGrid{grid-template-columns:repeat(2,1fr)}}`;
  document.head.appendChild(css);
})();
