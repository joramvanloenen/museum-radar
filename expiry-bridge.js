// Museum Radar expiry layer.
// Marks opportunities with passed hard deadlines as Expired without mutating source data.
// Also contains narrowly verified closure overrides for records whose graph entry predates
// the formal submission deadline being captured in opportunities.json.
(function(){
  const baseMergedOpps = mergedOpps;
  const verifiedClosed = {
    'project-pendine-through-time': {
      deadline: '2026-09-06',
      reason: 'Submission deadline passed on 6 September 2026.'
    }
  };

  function parseDateOnly(value){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(String(value||''))) return null;
    const d = new Date(value + 'T23:59:59');
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function formatDate(value){
    const d=parseDateOnly(value);
    if(!d) return value || '';
    return new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric'}).format(d);
  }

  function expiryInfo(o){
    const override = verifiedClosed[o.project_id];
    const rawDeadline = override?.deadline || o.deadline;
    const deadline = parseDateOnly(rawDeadline);
    if(!deadline) return null;
    if(deadline.getTime() >= Date.now()) return null;
    return {
      deadline: rawDeadline,
      reason: override?.reason || `Submission deadline passed on ${formatDate(rawDeadline)}.`
    };
  }

  mergedOpps = function(){
    return baseMergedOpps().map(o=>{
      const expired=expiryInfo(o);
      if(!expired) return o;
      return {
        ...o,
        original_stage:o.original_stage||o.stage,
        stage:'Expired',
        expired:true,
        expired_deadline:expired.deadline,
        expiry_reason:expired.reason,
        deadline:`Expired · ${formatDate(expired.deadline)}`
      };
    });
  };

  if(Array.isArray(stages) && !stages.includes('Expired')) stages.push('Expired');

  // Expired records stay searchable, but no longer inflate live/urgent pipeline counts.
  stats = function(){
    const o=mergedOpps().filter(x=>!x.rejected && !x.expired);
    return {
      act_now:o.filter(x=>x.score>=85||x.stage==='Live Tender').length,
      live:o.filter(x=>x.stage==='Live Tender').length,
      expected:o.filter(x=>['Expected','Pre-market'].includes(x.stage)).length,
      signals:o.filter(x=>['Signal','Lead'].includes(x.stage)).length
    };
  };

  const baseOverview = overview;
  overview = function(){
    const s=stats(),all=mergedOpps().filter(x=>!x.rejected),active=all.filter(x=>!x.expired);
    const urgent=active.filter(x=>x.score>=80||x.stage==='Live Tender').slice(0,5);
    const future=active.filter(x=>['Signal','Lead','Expected','Pre-market'].includes(x.stage)).slice(0,4);
    const expiredCount=all.filter(x=>x.expired).length;
    return `${header('Museum Radar','',true,false)}<div class="desktopNotice notice">Shared discoveries refresh automatically. Personal Watch/Reject state stays on this device.${expiredCount?` <b>${expiredCount} expired</b> record${expiredCount===1?' is':'s are'} kept for reference.`:''}</div>
    <div class="mobileSummary"><span><b>${s.live}</b> live</span><span><b>${s.expected}</b> expected</span><span><b>${s.signals}</b> signals</span></div>
    <div class="grid4 overviewMetrics">${[['Act now',s.act_now],['Live',s.live],['Expected',s.expected],['Signals',s.signals]].map(x=>`<div class="metric"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('')}</div>
    <section class="section prioritySection"><div class="sectionhead"><h2>Needs attention</h2><button class="textBtn" data-nav="opportunities">See all</button></div><div class="priorityList">${urgent.map(priorityCard).join('')||'<div class="notice">Nothing urgent right now.</div>'}</div></section>
    <section class="section futureSection"><div class="sectionhead"><h2>Strong future leads</h2><button class="textBtn" data-nav="future">See all</button></div><div class="cards">${future.map(card).join('')}</div></section>`;
  };

  const style=document.createElement('style');
  style.textContent=`
    .badge.Expired{background:rgba(255,255,255,.08)!important;color:rgba(255,255,255,.62)!important;border-color:rgba(255,255,255,.14)!important}
    tr:has(.badge.Expired){opacity:.68}
    .oppcard:has(.badge.Expired),.priorityCard:has(.badge.Expired){opacity:.72}
  `;
  document.head.appendChild(style);
})();
