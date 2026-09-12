// Museum Radar decision layer
// Separates project attractiveness from the practical route for YIPP, a specialist interactive studio.
(function(){
  const clean=s=>String(s||'').toLowerCase();
  const clamp=n=>Math.max(0,Math.min(100,Math.round(n)));
  const words=o=>clean([o.title,o.summary,o.fit_rationale,o.pitch_angle,o.next_action,(o.prediction?.signals||[]).join(' '),(o.prediction?.fit_terms||[]).join(' ')].join(' '));
  const has=(t,re)=>re.test(t);

  function decision(o){
    const t=words(o),base=Number(o.score)||50,conf=Number(o.confidence)||50;
    const interactive=has(t,/interactive|interactiv|immersive|multimedia|digital experience|realtime|real-time|projection|sensor|software|game|av\b|audio visual|audiovisual|media design|exhibit maker|hands-on|visitor experience/);
    const specialist=has(t,/interactive (design|production|exhibit|installation)|digital experience|immersive|multimedia|software|projection mapping|exhibit maker|media production/);
    const main=has(t,/main contractor|principal contractor|single supplier|single contractor|turnkey|design\s*(?:&|and)\s*build|full fit.?out|general contractor|complete exhibition|exhibition build/);
    const sub=has(t,/subcontract|sub-contractor|specialist contractor|specialist supplier|supply chain|nominated subcontract/);
    const lots=has(t,/\blot\b|\blots\b|separate package|specialist package|work package/);
    const construction=has(t,/construction|building works|architectural services|structural|m&e\b|mechanical and electrical|civil works/);
    const framework=has(t,/framework/);
    const directLanguage=has(t,/interactive(s)? makers|interactive exhibit|digital experience|multimedia (design|production)|software development|av integrator|audiovisual integrator|media design/);
    let capability=base+(interactive?8:-20)+(specialist?8:0)-(construction&&!specialist?18:0); capability=clamp(capability);
    let access=70+(directLanguage||lots?20:0)-(main?30:0)-(main&&construction?15:0)+(sub?10:0)+(o.stage==='Live Tender'?5:0)-(o.expired?25:0); access=clamp(access);
    let commercial=60+(specialist?18:0)+(directLanguage?12:0)-(main&&!lots?22:0)-(construction&&!lots?15:0)-(framework?5:0); commercial=clamp(commercial);
    const strategic=clamp(base*.65+conf*.35+(interactive?5:0));
    let route='WATCH / RESEARCH';
    if(o.expired&&main) route='CONTACT WINNER';
    else if(main&&(interactive||specialist)) route=sub?'SUBCONTRACT':'FIND MAIN CONTRACTOR';
    else if((directLanguage||lots)&&interactive) route='DIRECT BID';
    else if(o.stage==='Pitch'&&interactive) route='PITCH NOW';
    else if(o.stage==='Live Tender'&&interactive) route='DIRECT BID';
    else if(!interactive&&capability<50) route='LOW FIT';
    let action=o.next_action||'Research the opportunity';
    if(route==='FIND MAIN CONTRACTOR') action='Identify the exhibition/main contractor and approach them for the interactive package.';
    if(route==='SUBCONTRACT') action='Contact the lead bidder/main contractor and position YIPP as the specialist interactive partner.';
    if(route==='CONTACT WINNER') action='Find the awarded main contractor and contact them about unassigned interactive/digital packages.';
    if(route==='DIRECT BID') action='Review eligibility and tender requirements now; this appears structured for a specialist supplier like YIPP.';
    if(route==='PITCH NOW') action='Approach the client/design team before specialist packages are fixed.';
    if(route==='LOW FIT') action='Low specialist-interactive fit. Keep only if it exposes a useful downstream partner or package.';
    const urgency=o.expired?20:(o.stage==='Live Tender'?95:['Pre-market','Expected'].includes(o.stage)?75:o.stage==='Pitch'?70:50);
    const overall=clamp(capability*.34+access*.24+commercial*.18+strategic*.14+urgency*.10);
    return {overall,capability,access,commercial,strategic,urgency,route,action,main,interactive};
  }

  const previousMerged=window.mergedOpps;
  if(typeof previousMerged==='function') window.mergedOpps=function(){return previousMerged().map(o=>{const d=decision(o);return {...o,decision:d,score:d.overall,original_score:o.original_score??o.score,next_action:d.action};}).sort((a,b)=>b.score-a.score)};

  function routeClass(r){return clean(r).replace(/[^a-z]+/g,'-').replace(/^-|-$/g,'')}
  function actionCard(o){const d=o.decision||decision(o);return `<article class="actionCard" data-open="${escapeHtml(o.id)}" tabindex="0" role="button"><div class="actionTop"><span class="actionRoute ${routeClass(d.route)}">${escapeHtml(d.route)}</span><span class="actionScore">${d.overall}</span></div><h3>${escapeHtml(o.title)}</h3><div class="actionOrg">${escapeHtml(o.organization)}${o.country?' · '+escapeHtml(o.country):''}</div><div class="actionWhy"><span>Package fit <b>${d.capability}</b></span><span>Access <b>${d.access}</b></span>${o.deadline||o.procurement_window?`<span>${escapeHtml(o.deadline||o.procurement_window)}</span>`:''}</div><p>${escapeHtml(d.action)}</p><div class="actionOpen">Open opportunity <span>›</span></div></article>`}

  window.overview=function(){
    const all=mergedOpps().filter(o=>!o.rejected&&!o.expired&&o.decision?.route!=='LOW FIT');
    const direct=all.filter(o=>o.decision?.route==='DIRECT BID');
    const partner=all.filter(o=>['SUBCONTRACT','FIND MAIN CONTRACTOR','CONTACT WINNER'].includes(o.decision?.route));
    const pitch=all.filter(o=>o.decision?.route==='PITCH NOW');
    const watch=all.filter(o=>o.decision?.route==='WATCH / RESEARCH');
    const rank=o=>(o.decision?.urgency||0)*.55+(o.score||0)*.45;
    const act=[...direct,...partner,...pitch].sort((a,b)=>rank(b)-rank(a)).slice(0,6);
    const watched=all.filter(o=>o.watched).sort((a,b)=>b.score-a.score);
    const future=watch.sort((a,b)=>b.score-a.score).slice(0,4);
    const updated=[...all].sort((a,b)=>new Date(b.updated_at||0)-new Date(a.updated_at||0)).slice(0,3);
    return `${header('Museum Radar','What should YIPP act on?',true,false)}
      <div class="homeIntro"><div><span class="homeLiveDot"></span> Opportunity intelligence for interactive museum work</div><small>Ranked by package fit, access, commercial route and timing.</small></div>
      <div class="actionMetrics">
        <button data-nav="opportunities"><b>${direct.length}</b><span>Direct bids</span><small>YIPP can likely bid</small></button>
        <button data-nav="opportunities"><b>${partner.length}</b><span>Partner routes</span><small>Target a lead contractor</small></button>
        <button data-nav="pitch"><b>${pitch.length}</b><span>Pitch now</span><small>Approach before tender</small></button>
        <button data-nav="future"><b>${watch.length}</b><span>Watch</span><small>Promising, not actionable yet</small></button>
      </div>
      <section class="section homeActions"><div class="sectionhead"><div><div class="sectionKicker">PRIORITY</div><h2>What should we do?</h2><p>Best current actions for YIPP — not simply the highest-scoring museum projects.</p></div><button class="textBtn" data-nav="opportunities">All opportunities</button></div><div class="actionList">${act.map(actionCard).join('')||'<div class="notice">No immediate actions. Radar is watching the pipeline.</div>'}</div></section>
      ${watched.length?`<section class="section"><div class="sectionhead"><div><div class="sectionKicker">YOUR LIST</div><h2>Watched</h2></div></div><div class="compactCards">${watched.slice(0,3).map(actionCard).join('')}</div></section>`:''}
      <section class="section"><div class="sectionhead"><div><div class="sectionKicker">EARLY</div><h2>Worth watching</h2><p>Strong projects where the right YIPP route is not ready yet.</p></div><button class="textBtn" data-nav="future">Future Radar</button></div><div class="compactCards">${future.map(actionCard).join('')||'<div class="notice">No strong early-stage leads right now.</div>'}</div></section>
      <section class="section homeUpdates"><div class="sectionhead"><div><div class="sectionKicker">RADAR</div><h2>Recently updated</h2></div></div><div class="updateStrip">${updated.map(o=>`<button data-open="${escapeHtml(o.id)}"><b>${escapeHtml(o.title)}</b><span>${escapeHtml(o.organization)} · ${escapeHtml(o.decision?.route||o.stage)}</span></button>`).join('')}</div></section>`;
  };

  const baseModal=window.renderModal;
  if(typeof baseModal==='function') window.renderModal=function(){baseModal();if(state.modal!=='detail'||!state.selected)return;const modal=document.querySelector('.detailModal');if(!modal)return;const o=getOpp(state.selected.id),d=o?.decision||decision(o||state.selected),main=modal.querySelector('.detailMain'),facts=modal.querySelector('.detailFacts');if(main){const box=document.createElement('section');box.className='decisionBox';box.innerHTML=`<div class="decisionHead"><span class="routeBadge ${routeClass(d.route)}">${escapeHtml(d.route)}</span><strong>${d.overall} opportunity</strong></div><div class="decisionGrid"><div><b>${d.capability}</b><span>Package fit</span></div><div><b>${d.access}</b><span>Access</span></div><div><b>${d.commercial}</b><span>Commercial</span></div><div><b>${d.strategic}</b><span>Strategic</span></div></div><p><b>Recommended action:</b> ${escapeHtml(d.action)}</p>`;main.querySelector('h1')?.insertAdjacentElement('afterend',box)}if(facts){const label=facts.querySelector('.scoreLabel');if(label)label.textContent='YIPP opportunity score'}};

  const css=document.createElement('style');
  css.textContent=`
  .homeIntro{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:4px 0 18px;padding:12px 0;color:var(--muted,#9ca7b5)}.homeIntro>div{font-weight:650;color:var(--text,#eef3f8)}.homeLiveDot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#65d49b;margin-right:8px}.actionMetrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:28px}.actionMetrics button{text-align:left;border:1px solid var(--line,#283241);background:rgba(255,255,255,.025);border-radius:12px;padding:16px;color:inherit;cursor:pointer}.actionMetrics button:hover{background:rgba(255,255,255,.05)}.actionMetrics b{display:block;font-size:28px;line-height:1;margin-bottom:8px}.actionMetrics span{display:block;font-weight:700}.actionMetrics small{display:block;margin-top:4px;opacity:.55}.sectionKicker{font-size:10px;font-weight:800;letter-spacing:.13em;opacity:.48;margin-bottom:4px}.homeActions .sectionhead p,.sectionhead p{margin:5px 0 0;color:var(--muted,#9ca7b5);font-size:13px}.actionList{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.actionCard{border:1px solid var(--line,#283241);border-radius:14px;padding:17px;background:rgba(255,255,255,.025);cursor:pointer;min-width:0}.actionCard:hover{background:rgba(255,255,255,.05);transform:translateY(-1px)}.actionTop{display:flex;align-items:center;justify-content:space-between;gap:8px}.actionRoute,.routeBadge{display:inline-flex;font-size:10px;font-weight:850;letter-spacing:.07em;padding:6px 8px;border-radius:6px;background:rgba(255,255,255,.1)}.actionRoute.direct-bid,.routeBadge.direct-bid{background:rgba(77,205,137,.16);color:#8be4b5}.actionRoute.pitch-now,.routeBadge.pitch-now{background:rgba(116,151,255,.16);color:#a9bdff}.actionRoute.subcontract,.actionRoute.find-main-contractor,.actionRoute.contact-winner,.routeBadge.subcontract,.routeBadge.find-main-contractor,.routeBadge.contact-winner{background:rgba(244,181,76,.14);color:#f5c979}.actionScore{font-size:18px;font-weight:800}.actionCard h3{font-size:16px;line-height:1.25;margin:12px 0 5px}.actionOrg{font-size:12px;color:var(--muted,#9ca7b5)}.actionWhy{display:flex;gap:12px;flex-wrap:wrap;margin:13px 0 0;font-size:11px;color:var(--muted,#9ca7b5)}.actionWhy b{color:var(--text,#eef3f8)}.actionCard p{font-size:13px;line-height:1.45;margin:11px 0;color:var(--text,#eef3f8)}.actionOpen{padding-top:10px;border-top:1px solid var(--line,#283241);font-size:11px;font-weight:700;opacity:.6;display:flex;justify-content:space-between}.compactCards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.compactCards .actionCard p{display:none}.compactCards .actionWhy{margin-bottom:12px}.updateStrip{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.updateStrip button{text-align:left;padding:13px;border:1px solid var(--line,#283241);border-radius:10px;background:transparent;color:inherit;cursor:pointer}.updateStrip b,.updateStrip span{display:block}.updateStrip b{font-size:12px;margin-bottom:4px}.updateStrip span{font-size:10px;opacity:.55}.decisionBox{margin:18px 0;padding:18px;border:1px solid var(--line,#283241);border-radius:14px;background:rgba(255,255,255,.025)}.decisionHead{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.decisionGrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.decisionGrid>div{padding:10px;border-radius:9px;background:rgba(255,255,255,.04)}.decisionGrid b{display:block;font-size:20px}.decisionGrid span{font-size:11px;opacity:.65}.decisionBox p{margin:14px 0 0;line-height:1.45}
  @media(max-width:900px){.actionMetrics{grid-template-columns:repeat(2,1fr)}.actionList{grid-template-columns:1fr}.compactCards{grid-template-columns:1fr}.updateStrip{grid-template-columns:1fr}.homeIntro{align-items:flex-start;flex-direction:column}.homeIntro small{display:none}}
  @media(max-width:520px){.actionMetrics{gap:7px}.actionMetrics button{padding:13px}.actionMetrics b{font-size:23px}.actionMetrics small{display:none}.decisionGrid{grid-template-columns:repeat(2,1fr)}.actionCard{padding:14px}.homeActions .sectionhead{align-items:flex-end}}
  `;
  document.head.appendChild(css);
})();
