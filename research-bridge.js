// Museum Radar research graph -> visible opportunity pipeline bridge.
// Keeps opportunities.json authoritative for verified/manual records while surfacing
// Research Agent projects that only exist in project-graph.json.
(function(){
  const baseMergedOpps = mergedOpps;

  function normalizeText(v){
    return String(v || '').trim().toLowerCase().replace(/\s+/g,' ');
  }

  function graphProjectToOpportunity(p){
    const pred = p.prediction || {};
    const fitTerms = pred.fit_terms || [];
    const nextSignals = pred.expected_next_signals || [];
    return {
      id: 'agent-' + (p.project_id || ('graph-' + Math.random().toString(36).slice(2))),
      project_id: p.project_id || null,
      title: p.title || 'Research Agent project',
      organization: p.organization || 'Unknown',
      country: p.country || '',
      city: p.city || '',
      stage: ['Signal','Lead','Expected','Pre-market','Pitch'].includes(p.stage) ? p.stage : 'Lead',
      score: Number(p.score || 0),
      confidence: Number(p.confidence || 0),
      currency: p.currency || 'EUR',
      budget_min: p.budget_min ?? null,
      budget_max: p.budget_max ?? null,
      deadline: null,
      procurement_window: p.procurement_window || pred.window || null,
      summary: p.summary || pred.reason || 'Research Agent identified this as a potentially relevant future museum project.',
      fit_rationale: p.fit_rationale || (fitTerms.length ? 'Relevant fit signals: ' + fitTerms.join(', ') + '.' : 'Potential fit for interactive museum and visitor-experience work.'),
      pitch_angle: p.pitch_angle || 'Track the project early and position before specialist procurement is published.',
      next_action: p.next_action || (nextSignals.length ? 'Watch next: ' + nextSignals.join(' · ') : 'Monitor for stronger procurement, design or delivery signals.'),
      sample: false,
      verified: false,
      source_key: 'research_agent',
      external_id: p.project_id || null,
      source_url: p.source_url || '',
      source_label: 'Research Agent source',
      documents: p.source_url ? [{title:'Primary project source',url:p.source_url,kind:'Source article'}] : [],
      updated_at: (state.projectGraph && state.projectGraph.generated_at) || null,
      prediction: pred,
      evidence: p.evidence || []
    };
  }

  mergedOpps = function(){
    const existing = baseMergedOpps();
    const projects = Array.isArray(state.projectGraph?.projects) ? state.projectGraph.projects : [];
    if(!projects.length) return existing;

    const existingProjectIds = new Set(existing.map(o=>o.project_id).filter(Boolean));
    const existingKeys = new Set(existing.map(o=>normalizeText(o.organization)+'|'+normalizeText(o.title)));
    const prefs = localPrefs();

    const graphOnly = projects
      .filter(p=>p && p.project_id && !existingProjectIds.has(p.project_id))
      .filter(p=>!existingKeys.has(normalizeText(p.organization)+'|'+normalizeText(p.title)))
      .map(graphProjectToOpportunity)
      .map(o=>({...o,...(prefs[o.id]||{})}));

    return [...existing,...graphOnly].sort((a,b)=>(b.score||0)-(a.score||0));
  };
})();
