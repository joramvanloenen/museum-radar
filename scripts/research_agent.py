#!/usr/bin/env python3
import json, re, hashlib, urllib.request, urllib.parse, html as htmlmod, time
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OPPS=DATA/'opportunities.json'
SOURCES=DATA/'sources.json'
DISCOVERED=DATA/'discovered-sources.json'
META=DATA/'research-agent-meta.json'
GRAPH=DATA/'project-graph.json'
HIST=DATA/'historical-intelligence.json'
UA='MuseumRadarResearchAgent/0.6 (+GitHub Actions)'
MAX_BYTES=350000

def utcnow(): return datetime.now(timezone.utc)
def now(): return utcnow().isoformat(timespec='seconds')
def fp(*xs): return hashlib.sha1('|'.join(str(x or '').lower().strip() for x in xs).encode()).hexdigest()[:18]
def load_json(path, default):
    try: return json.loads(path.read_text(encoding='utf8'))
    except Exception: return default
def hostname(url):
    try: return (urllib.parse.urlparse(url).hostname or '').lower().replace('www.','')
    except Exception: return ''
def canonical_url(url):
    try:
        p=urllib.parse.urlparse(url)
        q=[(k,v) for k,v in urllib.parse.parse_qsl(p.query,keep_blank_values=True)
           if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
        return urllib.parse.urlunparse((p.scheme,p.netloc,p.path,p.params,urllib.parse.urlencode(q),''))
    except Exception: return url
def clean_html(s):
    s=htmlmod.unescape(str(s or ''))
    s=re.sub(r'(?is)<(script|style).*?>.*?</\\1>',' ',s)
    s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\\s+',' ',s).strip()
def request(url, accept='application/json', timeout=18):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':accept})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(MAX_BYTES)
def get_json(url, timeout=18):
    return json.loads(request(url,'application/json',timeout).decode('utf-8','replace'))
def get_text(url, timeout=15):
    return request(url,'text/html, application/xhtml+xml, */*',timeout).decode('utf-8','replace')

history=load_json(HIST,{})
existing=load_json(OPPS,[])
known_sources=load_json(SOURCES,[])
old_candidates=load_json(DISCOVERED,[])
learned=[x.lower() for x in history.get('learned_terms',[])]
negative=[x.lower() for x in history.get('negative_terms',[])]
buyer_history={x.get('buyer','').strip().lower():x for x in history.get('top_buyers',[]) if x.get('buyer')}

MUSEUM_TERMS=['museum','gallery','science centre','science center','visitor centre','visitor center','heritage centre','heritage center','aquarium','zoo','historic site']
FIT_TERMS=['interactive','interactives','immersive','multimedia','audiovisual','audio visual','projection','projection mapping','digital exhibition','digital interactive','media production','media design','visitor guide','museum app','augmented reality','virtual reality','software development','hands-on','exhibit design','exhibition design','interpretive exhibit','visitor experience','exhibition build','scenography','museographic','interpretation']
SIGNALS={
 'funding':['funding approved','funding secured','grant awarded','capital funding','heritage fund','lottery funding','investment approved','funded by','million investment'],
 'design':['architect appointed','design team appointed','exhibition designer appointed','masterplan','master plan','concept design','design development','designer appointed','design competition'],
 'project':['new gallery','new museum','museum expansion','museum renovation','museum redevelopment','permanent exhibition','new exhibition','visitor centre','visitor center','science centre','science center','redevelopment','renovation'],
 'procurement':['market engagement','market consultation','prior information notice','supplier engagement','procurement planned','procurement pipeline','tender expected','request for information','pre-market'],
 'delivery':['construction starts','work begins','fit-out','fit out','installation phase','fabrication'],
 'opening':['opening in','opens in','reopening in','completion in','scheduled to open','complete by']
}
NOISE=['now open','opens today','on display','tickets on sale','review:','what to see','things to do','best museums','museum deploys technology','museums deploy technology']
STOP=set('the a an and or for of to in on at from with by new museum museums gallery galleries exhibition exhibitions project projects centre center visitor heritage redevelopment renovation expansion funding design tender procurement permanent planned plan plans'.split())

def words(text):
    return {x for x in re.findall(r'[a-z0-9]{3,}',(text or '').lower()) if x not in STOP}
def sim(a,b):
    aa,bb=words(a),words(b)
    return len(aa&bb)/max(1,len(aa|bb))
def normalize_org(s):
    s=re.sub(r'[^a-z0-9 ]+',' ',(s or '').lower())
    return re.sub(r'\\s+',' ',s).strip()
def source_quality(url):
    d=hostname(url)
    if not d: return 35
    if d.endswith('.gov') or '.gov.' in d or d.endswith('.gov.uk') or d.endswith('.europa.eu'): return 96
    if any(x in d for x in ['procure','tender','etender','ted.europa','boamp','simap','doffin','gebiz','udbud','evergabe']): return 93
    if any(x in d for x in ['museum','gallery','heritage','sciencecentre','sciencecenter','nationalpark']): return 86
    if any(x in d for x in ['reuters','bbc.','theguardian.','museumsassociation.','blooloop.','architectsjournal.']): return 78
    return 58
def org_from_title(title,url):
    patterns=[
      r"((?:[A-Z][A-Za-z0-9&'’.-]+\\s+){0,7}(?:Museum|Museums|Gallery|Galleries|Science Centre|Science Center|Visitor Centre|Visitor Center|Aquarium|Zoo))",
      r"((?:Royal|National|Imperial|Natural History|Science)\\s+(?:[A-Z][A-Za-z&'’.-]+\\s+){0,4}(?:Museum|Gallery|Centre|Center))"
    ]
    for p in patterns:
        m=re.search(p,title or '')
        if m and 4<len(m.group(1))<130: return m.group(1).strip()
    if ':' in (title or ''):
        p=title.split(':',1)[0].strip()
        if 4<len(p)<110: return p
    return hostname(url) or 'Unknown organisation'
def detect(text):
    low=(text or '').lower()
    tags=[tag for tag,terms in SIGNALS.items() if any(t in low for t in terms)]
    fits=sorted({t for t in FIT_TERMS if t in low})
    years=sorted({int(x) for x in re.findall(r'\\b(202[6-9]|203[0-5])\\b',low)})
    money=re.findall(r'(?:€|£|\\$)\\s?\\d[\\d,.]*(?:\\s?(?:m|million|bn|billion))?',text or '',re.I)[:3]
    return tags,fits,years,money
def score_item(title,desc,org=''):
    text=(title+' '+desc+' '+org).lower()
    if any(n in text for n in NOISE): return 0,[],[]
    museum=any(x in text for x in MUSEUM_TERMS) or org.lower().strip() in buyer_history
    if not museum: return 0,[],[]
    tags,fits,_,_=detect(text)
    # Generic technology/editorial stories are not leads.
    if not tags and org.lower().strip() not in buyer_history: return 0,tags,fits
    score=22 + min(25,len(fits)*7)
    for tag in tags:
        score += {'funding':15,'design':16,'project':12,'procurement':25,'delivery':8,'opening':7}.get(tag,0)
    score += min(10,2*sum(t in text for t in learned[:100]))
    score -= min(30,6*sum(t in text for t in negative))
    bh=buyer_history.get(org.lower().strip())
    if bh: score += min(12,2*bh.get('high',0)+bh.get('adjacent',0))
    return max(0,min(96,score)),tags,fits

def gdelt_search(query, limit=60):
    params={'query':query,'mode':'artlist','format':'json','maxrecords':min(limit,250),'timespan':'6months','sort':'datedesc'}
    url='https://api.gdeltproject.org/api/v2/doc/doc?'+urllib.parse.urlencode(params)
    last=None
    for attempt in range(2):
        try:
            raw=get_json(url,20)
            out=[]
            for x in raw.get('articles',[])[:limit]:
                u=canonical_url(x.get('url',''))
                if u and x.get('title'):
                    out.append({'title':clean_html(x.get('title')),'description':'','url':u,'date':x.get('seendate',''),'engine':'GDELT'})
            return out
        except Exception as e:
            last=e
            time.sleep(1.5*(attempt+1))
    raise last

def bing_html_search(query, limit=12):
    url='https://www.bing.com/search?'+urllib.parse.urlencode({'q':query,'count':limit})
    raw=get_text(url,15)
    out=[]
    for block in re.findall("<li[^>]+class=[\"'][^\"']*b_algo[^\"']*[\"'][^>]*>.*?</li>",raw,re.I|re.S):
        m=re.search("<h2[^>]*>\\s*<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",block,re.I|re.S)
        if not m: continue
        u=canonical_url(htmlmod.unescape(m.group(1)))
        sm=re.search(r'<p[^>]*>(.*?)</p>',block,re.I|re.S)
        out.append({'title':clean_html(m.group(2)),'description':clean_html(sm.group(1)) if sm else '','url':u,'date':'','engine':'Bing'})
        if len(out)>=limit: break
    return out

queries=[
 ('museum','museum'),
 ('science centre','"science centre"'),
 ('science center','"science center"'),
 ('visitor centre','"visitor centre"'),
 ('visitor center','"visitor center"')
]
watch_buyers=[]
started=time.monotonic()
errors=[]
raw=[]
seen=set()
queries_ok=0
queries_failed=0

def ingest(rows,label,buyer=None):
    added=0
    for r in rows:
        u=r.get('url','')
        if not u or u in seen: continue
        org=buyer or org_from_title(r.get('title',''),u)
        score,tags,fits=score_item(r.get('title',''),r.get('description',''),org)
        if buyer and score<38:
            text=(r.get('title','')+' '+r.get('description','')).lower()
            if any(k in text for k in ['exhibition','gallery','interactive','immersive','multimedia','renovation','redevelopment','funding','procurement','masterplan']):
                score=max(score,42)
        if score<40: continue
        seen.add(u); added+=1
        raw.append({**r,'organization':org,'score':score,'signals':tags,'fit_terms':fits,'quality':source_quality(u),'query':label})
    return added

for label,q in queries:
    try:
        rows=gdelt_search(q,200); queries_ok+=1; ingest(rows,label)
    except Exception as e:
        queries_failed+=1; errors.append(f'GDELT {label}: {e}')

# Tiny fallback only if the global feed is unavailable or unusually thin.
if len(raw)<8:
    for label,q in [('museum projects','museum renovation funding exhibition'),('museum procurement','museum exhibition procurement')]:
        try:
            queries_ok+=1; ingest(bing_html_search(q,12),label+' fallback')
        except Exception as e:
            queries_failed+=1; errors.append(f'Bing {label}: {e}')

# Enrich only the most promising few pages.
for r in sorted(raw,key=lambda x:(x['score'],x['quality']),reverse=True)[:10]:
    if r['url'].lower().endswith('.pdf'): continue
    try:
        txt=clean_html(get_text(r['url'],8))[:6500]
        if txt:
            sc,tags,fits=score_item(r['title'],r['description']+' '+txt,r['organization'])
            r['score']=max(r['score'],sc)
            r['signals']=sorted(set(r['signals']+tags))
            r['fit_terms']=sorted(set(r['fit_terms']+fits))
    except Exception:
        pass

# Cluster breadcrumbs into projects.
clusters=[]
for r in sorted(raw,key=lambda x:x['score'],reverse=True):
    orgn=normalize_org(r['organization'])
    best=None; strength=0
    for c in clusters:
        same=orgn and orgn==c['orgn'] and '.' not in orgn
        s=sim(r['title'],c['seed']) + (0.35 if same else 0)
        if (same and s>=0.45) or s>=0.52:
            if s>strength: best,strength=c,s
    if best: best['items'].append(r)
    else: clusters.append({'orgn':orgn,'organization':r['organization'],'seed':r['title'],'items':[r]})

def predict(tags,fits,domains,quality,years):
    t=set(tags)
    if 'procurement' in t:
        stage,window,base,why='Expected','0–4 months',82,'Pre-procurement language is already visible; formal procurement may be close.'
    elif {'funding','design'}<=t:
        stage,window,base,why='Expected','2–9 months',78,'Funding and active design work are both visible, a strong precursor to specialist exhibition/media packages.'
    elif 'design' in t and 'project' in t:
        stage,window,base,why='Lead','2–10 months',72,'A defined project and active design phase suggest specialist packages are beginning to form.'
    elif 'funding' in t and 'project' in t:
        stage,window,base,why='Lead','3–12 months',69,'A funded museum project is moving beyond aspiration; specialist procurement often follows.'
    elif 'design' in t:
        stage,window,base,why='Lead','3–12 months',66,'Design-team/masterplan activity commonly precedes exhibition, AV and interactive procurement.'
    elif 'funding' in t:
        stage,window,base,why='Lead','4–15 months',63,'Confirmed funding is an upstream indicator for later exhibition and technical packages.'
    elif 'project' in t and fits:
        stage,window,base,why='Pitch','3–15 months',59,'A real museum project plus relevant experience/media language makes this worth early qualification.'
    else:
        stage,window,base,why='Signal','6–18 months',52,'A project signal exists, but stronger procurement breadcrumbs are still needed.'
    conf=base+min(12,max(0,domains-1)*5)+max(-3,min(8,round((quality-60)/5)))
    if len(fits)>=2: conf+=4
    if years and min(years)<=utcnow().year+1: conf+=4
    return stage,window,max(40,min(94,conf)),why

projects=[]
for c in clusters:
    items=sorted(c['items'],key=lambda x:(x['score'],x['quality']),reverse=True)
    text=' '.join(x['title']+' '+x.get('description','') for x in items)
    tags,fits,years,money=detect(text)
    domains=sorted({hostname(x['url']) for x in items if x.get('url')})
    quality=round(sum(x['quality'] for x in items)/len(items))
    stage,window,confidence,why=predict(tags,fits,len(domains),quality,years)
    top=items[0]
    opportunity_score=min(97,round(max(x['score'] for x in items)*.68+confidence*.32+min(6,max(0,len(domains)-1)*2)))
    risks=[]
    if len(domains)<2: risks.append('single-source signal')
    if not any(source_quality('https://'+d)>=84 for d in domains): risks.append('no first-party/official source yet')
    if not fits: risks.append('interactive/AV scope not explicit yet')
    nexts=[]
    if 'funding' not in tags: nexts.append('funding / capital approval')
    if 'design' not in tags: nexts.append('architect or exhibition-designer appointment')
    if 'procurement' not in tags: nexts.append('market engagement / procurement notice')
    project_id='project-'+fp(c['orgn'],*sorted(words(c['seed']))[:8])
    evidence=[{
      'date':x.get('date','')[:16],'kind':'Project signal','title':x['title'][:220],
      'detail':x.get('description','')[:500] or why,'source_url':x['url'],
      'source_label':hostname(x['url']) or x.get('engine','Web'),'strength':min(95,round((x['quality']+confidence)/2))
    } for x in items[:8]]
    projects.append({
      'id':'agent-'+project_id,'project_id':project_id,'title':top['title'][:240],'organization':c['organization'],
      'country':'','city':'','stage':stage,'score':opportunity_score,'confidence':confidence,'currency':'EUR',
      'deadline':None,'procurement_window':window,'summary':top.get('description','')[:900] or f'Potential museum project detected from {len(domains)} source domain(s).',
      'fit_rationale':'Upstream project intelligence matches patterns that historically precede museum exhibition, interactive, AV or interpretation procurement.',
      'pitch_angle':'Qualify early: map project owner, funding, design team and likely specialist packages before formal procurement.',
      'next_action':'Verify the strongest first-party source and watch for '+', '.join(nexts[:2])+'.',
      'sample':False,'verified':False,'source_key':'research_agent','external_id':project_id,
      'source_url':top['url'],'source_label':hostname(top['url']) or 'Web source',
      'documents':[{'title':x['title'][:160],'url':x['url'],'kind':'Source article'} for x in items[:5]],
      'updated_at':now(),
      'prediction':{'window':window,'reason':why,'signals':sorted(set(tags)),'fit_terms':fits[:12],
        'source_count':len(evidence),'source_domains':domains,'source_diversity':len(domains),'source_quality':quality,
        'expected_next_signals':nexts[:3],'risk_flags':risks,'opening_years':years[:3],'investment_signals':money},
      'evidence':evidence
    })

projects=sorted(projects,key=lambda x:(x['confidence'],x['score'],x['prediction']['source_diversity']),reverse=True)[:60]
non_agent=[o for o in existing if o.get('source_key')!='research_agent']
OPPS.write_text(json.dumps(non_agent+projects,ensure_ascii=False,indent=2),encoding='utf8')

# Lightweight autonomous source discovery once per UTC day around midnight.
known_domains={hostname(x.get('url','')) for x in known_sources if x.get('url')}
cand={hostname(x.get('url','')):x for x in old_candidates if x.get('url')}
if utcnow().hour<3 or not cand:
    source_queries=['museum exhibition procurement portal','museum interactive tender platform','science centre procurement tender','heritage exhibition tender portal']
    for q in source_queries:
        try:
            rows=bing_html_search(q,10); queries_ok+=1
        except Exception as e:
            queries_failed+=1; errors.append(f'Source discovery {q}: {e}'); continue
        for r in rows:
            d=hostname(r['url'])
            text=(r['title']+' '+r.get('description','')).lower()
            if not d or d in known_domains or d=='museuminsider.co.uk': continue
            if not any(x in text for x in ['tender','procurement','rfp','contract','supplier','bid']): continue
            if not any(x in text for x in ['museum','gallery','exhibition','heritage','science centre','visitor centre']): continue
            c=cand.get(d) or {'name':d,'region':'Unknown','type':'Discovered source candidate','status':'Needs verification',
              'url':'https://'+d,'notes':'Autonomously discovered while searching for museum/exhibition procurement sources.',
              'confidence':40,'examples':[]}
            urls={e.get('url') for e in c.get('examples',[])}
            if r['url'] not in urls:
                c['examples']=(c.get('examples',[])+[{'title':r['title'][:180],'url':r['url']}])[-5:]
                c['confidence']=min(88,int(c.get('confidence',40))+8)
            cand[d]=c

candidates=sorted(cand.values(),key=lambda x:(x.get('confidence',0),len(x.get('examples',[]))),reverse=True)[:40]
DISCOVERED.write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding='utf8')
high=sum(1 for x in projects if x['confidence']>=75 and x['score']>=75)
duration=round(time.monotonic()-started,1)
status='healthy' if queries_ok>=8 and queries_failed<=max(3,queries_ok//3) else ('degraded' if queries_ok else 'failed')
GRAPH.write_text(json.dumps({'generated_at':now(),'project_count':len(projects),'high_conviction':high,
 'projects':[{'project_id':x['project_id'],'title':x['title'],'organization':x['organization'],'stage':x['stage'],
 'score':x['score'],'confidence':x['confidence'],'procurement_window':x['procurement_window'],
 'prediction':x['prediction'],'source_url':x['source_url']} for x in projects]},ensure_ascii=False,indent=2),encoding='utf8')
META.write_text(json.dumps({'status':status,'last_run':now(),'duration_seconds':duration,'queries_ok':queries_ok,
 'queries_failed':queries_failed,'raw_signals':len(raw),'project_clusters':len(projects),'predicted_leads_added':len(projects),
 'high_conviction':high,'candidate_sources_found':len(candidates),'errors':errors[:20]},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':status,'duration_seconds':duration,'queries_ok':queries_ok,'queries_failed':queries_failed,
 'raw_signals':len(raw),'projects':len(projects),'high_conviction':high,'candidate_sources':len(candidates),'errors':len(errors)}))
