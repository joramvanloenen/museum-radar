#!/usr/bin/env python3
import json, re, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET, time
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
UA='MuseumRadarResearchAgent/0.4 (+GitHub Actions)'
MAX_PAGE_BYTES=300000

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def fp(*xs): return hashlib.sha1('|'.join(str(x or '').lower().strip() for x in xs).encode()).hexdigest()[:18]
def clean_html(s):
    s=re.sub(r'(?is)<(script|style).*?>.*?</\\1>',' ',s or '')
    s=re.sub(r'<[^>]+>',' ',s)
    s=s.replace('&amp;','&').replace('&quot;','"').replace('&#39;',"'")
    return re.sub(r'\\s+',' ',s).strip()
def load_json(path, default):
    try: return json.loads(path.read_text(encoding='utf8'))
    except Exception: return default
def hostname(url):
    try: return (urllib.parse.urlparse(url).hostname or '').lower()
    except Exception: return ''
def canonical_url(url):
    try:
        p=urllib.parse.urlparse(url)
        q=[(k,v) for k,v in urllib.parse.parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_')]
        return urllib.parse.urlunparse((p.scheme,p.netloc,p.path,p.params,urllib.parse.urlencode(q),''))
    except Exception: return url
def get_text(url, timeout=18):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html, application/rss+xml, text/xml, */*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read(MAX_PAGE_BYTES)
        return raw.decode('utf-8','replace')

def get_json_url(url, timeout=25):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)
def parse_xml(raw):
    try: return ET.fromstring(raw)
    except ET.ParseError:
        fixed=re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\\d+;|#x[0-9a-fA-F]+;)','&amp;',raw)
        return ET.fromstring(fixed)

def unwrap_search_url(url):
    try:
        p=urllib.parse.urlparse(url)
        qs=urllib.parse.parse_qs(p.query)
        if 'url' in qs and qs['url']:
            return canonical_url(urllib.parse.unquote(qs['url'][0]))
        if hostname(url).endswith('bing.com'):
            req=urllib.request.Request(url,headers={'User-Agent':UA},method='GET')
            with urllib.request.urlopen(req,timeout=8) as r:
                final=r.geturl()
                if final and not hostname(final).endswith('bing.com'):
                    return canonical_url(final)
    except Exception:
        pass
    return canonical_url(url)

def bing_search(query, limit=20, news=True):
    base='https://www.bing.com/news/search' if news else 'https://www.bing.com/search'
    url=base+'?'+urllib.parse.urlencode({'q':query,'format':'rss'})
    root=parse_xml(get_text(url,20))
    rows=[]
    for i in root.findall('.//item')[:limit]:
        rows.append({
            'title':clean_html(i.findtext('title') or ''),
            'description':clean_html(i.findtext('description') or ''),
            'url':unwrap_search_url((i.findtext('link') or '').strip()),
            'date':(i.findtext('pubDate') or '').strip()
        })
    return rows

def bing_html_search(query, limit=15):
    url='https://www.bing.com/search?'+urllib.parse.urlencode({'q':query,'count':limit})
    raw=get_text(url,20)
    out=[]
    for block in re.findall(r'<li[^>]+class=["\\'][^"\\']*b_algo[^"\\']*["\\'][^>]*>.*?</li>',raw,re.I|re.S):
        m=re.search(r'<h2[^>]*>\\s*<a[^>]+href=["\\']([^"\\']+)["\\'][^>]*>(.*?)</a>',block,re.I|re.S)
        if not m: continue
        href=unwrap_search_url(m.group(1))
        title=clean_html(m.group(2))
        sm=re.search(r'<p[^>]*>(.*?)</p>',block,re.I|re.S)
        desc=clean_html(sm.group(1)) if sm else ''
        if href and title: out.append({'title':title,'description':desc,'url':href,'date':''})
        if len(out)>=limit: break
    return out

def ddg_search(query, limit=15):
    url='https://html.duckduckgo.com/html/?'+urllib.parse.urlencode({'q':query})
    raw=get_text(url,20)
    out=[]
    for m in re.finditer(r'<a[^>]+class=["\\']result__a["\\'][^>]+href=["\\']([^"\\']+)["\\'][^>]*>(.*?)</a>',raw,re.I|re.S):
        href=m.group(1).replace('&amp;','&')
        try:
            p=urllib.parse.urlparse(href)
            qs=urllib.parse.parse_qs(p.query)
            if 'uddg' in qs and qs['uddg']: href=urllib.parse.unquote(qs['uddg'][0])
        except Exception: pass
        href=canonical_url(href)
        title=clean_html(m.group(2))
        if href and title: out.append({'title':title,'description':'','url':href,'date':''})
        if len(out)>=limit: break
    return out

def gdelt_search(query, limit=40, timespan='3months'):
    params={'query':query,'mode':'artlist','format':'json','maxrecords':min(limit,250),'timespan':timespan,'sort':'datedesc'}
    url='https://api.gdeltproject.org/api/v2/doc/doc?'+urllib.parse.urlencode(params)
    raw=get_json_url(url,30)
    out=[]
    for x in raw.get('articles',[])[:limit]:
        u=canonical_url(x.get('url',''))
        if not u: continue
        out.append({
            'title':clean_html(x.get('title','')),
            'description':'',
            'url':u,
            'date':x.get('seendate',''),
            'gdelt_domain':x.get('domain',''),
            'gdelt_language':x.get('language',''),
            'gdelt_country':x.get('sourcecountry','')
        })
    return out
def parse_date(value):
    if not value: return None
    try:
        d=parsedate_to_datetime(value)
        return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception: return None
def age_days(value):
    d=parse_date(value)
    if not d: return 90
    return max(0,(datetime.now(timezone.utc)-d).days)

history=load_json(HIST,{})
existing_opps=load_json(OPPS,[])
existing_sources=load_json(SOURCES,[])
existing_discovered=load_json(DISCOVERED,[])
learned=[x.lower() for x in history.get('learned_terms',[])]
negative=[x.lower() for x in history.get('negative_terms',[])]
buyer_history={x.get('buyer','').strip().lower():x for x in history.get('top_buyers',[]) if x.get('buyer')}

museum_terms=['museum','museums','gallery','galleries','science centre','science center','visitor centre','visitor center','heritage centre','heritage center','interpretation centre','interpretive center','aquarium','zoo','historic site','national park']
high_fit_terms=['interactive','interactives','immersive','multimedia','audiovisual','audio visual','projection','projection mapping','digital exhibition','digital interactive','media production','media design','media station','visitor guide','museum app','augmented reality','virtual reality','software development','hands-on','exhibit design','exhibition design','interpretive exhibit','visitor experience','exhibition build','scenography','museographic']
signal_terms={
    'funding':['funding approved','funding secured','grant awarded','investment approved','capital funding','heritage fund','lottery funding','funded by','investment of'],
    'design':['architect appointed','design team appointed','exhibition designer appointed','masterplan','master plan','concept design','design development','design competition','designer appointed'],
    'project':['new gallery','new museum','museum expansion','museum renovation','museum redevelopment','permanent exhibition','new exhibition','visitor centre','visitor center','new science centre','new science center','reopening'],
    'procurement':['market engagement','market consultation','prior information notice','procurement planned','tender expected','request for information','supplier engagement','pre-market','procurement pipeline'],
    'delivery':['construction starts','work begins','fit-out','fit out','installation','fabrication','delivery phase'],
    'opening':['opening in','opens in','reopening in','completion in','complete by','scheduled to open']
}
GENERIC_ORGS={'unknown organisation','web source','web discovery','museum','gallery','news','bing'}

STOP=set('the a an and or for of to in on at from with by new museum museums gallery galleries exhibition exhibitions project projects centre center visitor heritage redevelopment renovation expansion funding design tender procurement rfp contract permanent planned plan plans'.split())
def tokens(text):
    return {x for x in re.findall(r'[a-z0-9]{3,}',(text or '').lower()) if x not in STOP}
def similarity(a,b):
    aa=tokens(a); bb=tokens(b)
    return len(aa&bb)/max(1,len(aa|bb))
def normalize_org(org):
    s=re.sub(r'[^a-z0-9 ]+',' ',(org or '').lower())
    s=re.sub(r'\\b(the|city of|municipality of|council of|department of|office of)\\b',' ',s)
    return re.sub(r'\\s+',' ',s).strip()
def org_from_result(title,url):
    m=re.search(r"\\b((?:[A-Z][A-Za-z0-9&'’.-]+\\s+){0,6}(?:Museum|Museums|Gallery|Galleries|Science Centre|Science Center|Visitor Centre|Visitor Center|Aquarium|Zoo))\\b",title or '')
    if m and 3<len(m.group(1))<120: return m.group(1).strip()
    if ':' in title:
        p=title.split(':',1)[0].strip()
        if 3<len(p)<120: return p
    dom=hostname(url).replace('www.','')
    return dom or 'Unknown organisation'
def source_quality(url):
    dom=hostname(url)
    if not dom: return 35
    if dom.endswith('.gov') or '.gov.' in dom or dom.endswith('.gov.uk') or dom.endswith('.gouv.fr') or dom.endswith('.bund.de') or dom.endswith('.europa.eu'):
        return 96
    if any(x in dom for x in ['tender','procure','contractsfinder','find-tender','ted.europa','etenders','evergabe','simap','boamp','gebiz','doffin','udbud']):
        return 92
    if any(x in dom for x in ['museum','gallery','heritage','sciencecentre','sciencecenter','nationalpark','zoo']):
        return 84
    if any(x in dom for x in ['bbc.','reuters.','apnews.','theguardian.','architectsjournal.','museumsassociation.','blooloop.']):
        return 76
    return 58

def detect_signals(text):
    low=(text or '').lower()
    tags=[]
    for tag,terms in signal_terms.items():
        if any(t in low for t in terms): tags.append(tag)
    fit=[t for t in high_fit_terms if t in low]
    years=[int(y) for y in re.findall(r'\\b(202[6-9]|203[0-5])\\b',low)]
    money=re.findall(r'(?:€|£|\\$)\\s?\\d[\\d,.]*(?:\\s?(?:m|million|bn|billion))?',text or '',re.I)
    return tags,fit,sorted(set(years)),money[:3]

def base_score(title,desc,org=''):
    text=(title+' '+desc+' '+org).lower()
    museum_context=any(x in text for x in museum_terms) or (org or '').lower().strip() in buyer_history
    if not museum_context: return 0,[],[]
    tags,fit,years,money=detect_signals(text)
    score=24
    score+=min(30,10*len(set(fit)))
    for tag in tags:
        score += {'funding':14,'design':15,'project':12,'procurement':24,'delivery':8,'opening':7}.get(tag,0)
    score += min(12,3*sum(t in text for t in learned[:100]))
    score -= min(35,7*sum(t in text for t in negative))
    bh=buyer_history.get((org or '').lower().strip())
    if bh: score+=min(12,2*bh.get('high',0)+bh.get('adjacent',0))
    return max(0,min(96,score)),tags,fit

def predict(tags,fit,source_count,quality,years):
    tags=set(tags); source_bonus=min(12,max(0,source_count-1)*5)
    if 'procurement' in tags:
        stage,window,base='Expected','0–4 months',80
        why='Pre-procurement or supplier-engagement language is visible; a formal competition may be close.'
    elif {'funding','design'} <= tags:
        stage,window,base='Expected','2–9 months',76
        why='Funding and design/masterplan activity are both visible, a strong precursor to specialist exhibition and media packages.'
    elif 'design' in tags and ('project' in tags or 'delivery' in tags):
        stage,window,base='Lead','2–10 months',70
        why='A defined project plus active design work suggests specialist packages are beginning to form.'
    elif 'funding' in tags and 'project' in tags:
        stage,window,base='Lead','3–12 months',68
        why='A funded museum project is moving beyond aspiration; consultant and delivery procurement often follows.'
    elif 'design' in tags:
        stage,window,base='Lead','3–12 months',65
        why='Design-team or masterplan activity often comes before exhibition, AV and interactive procurement.'
    elif 'funding' in tags:
        stage,window,base='Lead','4–15 months',62
        why='Confirmed funding is an upstream indicator for later design and delivery packages.'
    elif 'opening' in tags and 'project' in tags:
        stage,window,base='Pitch','2–12 months',58
        why='A dated museum project gives a useful window for early outreach before specialist procurement appears.'
    else:
        stage,window,base='Signal','6–18 months',50
        why='This is an early project signal; more procurement breadcrumbs are needed.'
    if years:
        y=min(years)
        if y<=datetime.now(timezone.utc).year+1 and stage in ('Signal','Lead'):
            window='1–9 months'; base+=5
    if len(fit)>=2: base+=6
    confidence=max(35,min(94,base+source_bonus+round((quality-55)/5)))
    next_signals=[]
    if 'funding' not in tags: next_signals.append('funding or capital approval')
    if 'design' not in tags: next_signals.append('architect / exhibition designer appointment')
    if 'procurement' not in tags: next_signals.append('market engagement / procurement notice')
    if stage in ('Expected','Pitch'): next_signals.append('formal tender or supplier brief')
    return stage,window,confidence,why,next_signals[:3]

lead_queries=[
    ('Capital projects','museum renovation funding approved architect appointed exhibition'),
    ('New galleries','"new gallery" museum funding architect exhibition'),
    ('Masterplans','museum expansion masterplan exhibition designer visitor experience'),
    ('Permanent exhibitions','"permanent exhibition" museum redevelopment funding interactive'),
    ('Visitor centres','"visitor centre" heritage funding architect interpretation'),
    ('Science centres','"science centre" expansion gallery interactive funding'),
    ('Pre-market','museum "market engagement" exhibition interactive AV'),
    ('Procurement pipelines','museum "procurement planned" exhibition multimedia'),
    ('Digital experiences','museum immersive digital interactive project funding'),
    ('France','musée rénovation financement scénographie multimédia architecte'),
    ('Germany','Museum Sanierung Förderung Ausstellungsgestaltung Medientechnik Architekt'),
    ('Netherlands','museum verbouwing financiering tentoonstelling interactieve media architect'),
    ('Nordics','museum science centre new exhibition funding interactive Scandinavia')
]
platform_queries=[
    '"museum" tender portal procurement exhibition',
    '"museum exhibition" procurement platform AV interactive',
    '"science centre" tender procurement portal interactive',
    '"visitor centre" procurement exhibition tender',
    '"museum" RFP platform exhibition design multimedia',
    '"heritage" procurement portal interpretive exhibit'
]
gdelt_queries=[
    'museum (renovation OR redevelopment OR expansion) (funding OR architect OR masterplan)',
    'museum ("new gallery" OR "permanent exhibition") (funding OR design OR architect)',
    '("science centre" OR "science center") (expansion OR exhibition OR interactive)',
    '("visitor centre" OR "visitor center") (heritage OR museum) (funding OR design OR interpretation)',
    'museum ("market engagement" OR "supplier engagement" OR procurement)',
    '(museum OR gallery) (immersive OR interactive OR multimedia OR audiovisual) (exhibition OR renovation OR redevelopment)'
]

# Recurring buyers get their own searches, making the agent proactive instead of purely keyword-driven.
watch_buyers=[]
for b in history.get('top_buyers',[])[:12]:
    if b.get('buyer'): watch_buyers.append(b['buyer'])
for o in sorted(existing_opps,key=lambda x:x.get('score',0),reverse=True):
    org=o.get('organization','')
    if org and org not in watch_buyers and o.get('score',0)>=85:
        watch_buyers.append(org)
    if len(watch_buyers)>=18: break

raw=[]
errors=[]
seen_urls=set()
def ingest(rows,query_name,buyer_override=None):
    added=0
    for r in rows:
        u=r.get('url','')
        if not u or u in seen_urls: continue
        org=buyer_override or org_from_result(r.get('title',''),u)
        score,tags,fit=base_score(r.get('title',''),r.get('description',''),org)
        if buyer_override and not any(x in (r.get('title','')+' '+r.get('description','')).lower() for x in ['exhibition','gallery','interactive','immersive','multimedia','digital','renovation','redevelopment','funding','procurement','tender','visitor','experience','masterplan']):
            continue
        if score<40: continue
        seen_urls.add(u)
        raw.append({**r,'organization':org,'base_score':score,'signals':tags,'fit_terms':fit,'query':query_name,'quality':source_quality(u)})
        added+=1
    return added

for i,q in enumerate(gdelt_queries):
    try:
        ingest(gdelt_search(q,45,'3months'),f'GDELT {i+1}')
    except Exception as e:
        errors.append(f'gdelt:{i+1}: {e}')
    time.sleep(1.05)

for name,q in lead_queries:
    n=0
    try: n+=ingest(bing_search(q,18,True),name+' news')
    except Exception as e: errors.append(f'lead-news:{name}: {e}')
    try: n+=ingest(bing_search(q,14,False),name+' web')
    except Exception as e: errors.append(f'lead-web:{name}: {e}')
    if n<3:
        try: n+=ingest(bing_html_search(q,12),name+' web html')
        except Exception as e: errors.append(f'lead-html:{name}: {e}')
    if n<2:
        try: ingest(ddg_search(q,10),name+' ddg')
        except Exception as e: errors.append(f'lead-ddg:{name}: {e}')
for buyer in watch_buyers[:12]:
    try:
        ingest(gdelt_search(f'"{buyer}" (exhibition OR gallery OR interactive OR multimedia OR renovation OR funding OR procurement)',20,'3months'),'Buyer watch GDELT',buyer)
    except Exception as e:
        errors.append(f'buyer-gdelt:{buyer}: {e}')
    time.sleep(1.05)

for buyer in watch_buyers[:18]:
    q=f'"{buyer}" (exhibition OR gallery OR interactive OR multimedia OR renovation OR funding OR procurement)'
    n=0
    try: n+=ingest(bing_search(q,10,True),'Buyer watch',buyer)
    except Exception as e: errors.append(f'buyer-news:{buyer}: {e}')
    if n<2:
        try: n+=ingest(bing_html_search(q,8),'Buyer watch',buyer)
        except Exception as e: errors.append(f'buyer-html:{buyer}: {e}')

# Enrich the strongest candidates with their source page text when accessible.
for r in sorted(raw,key=lambda x:(x['base_score'],x['quality']),reverse=True)[:14]:
    if not r['url'].lower().endswith('.pdf'):
        try:
            page=clean_html(get_text(r['url'],10))[:7000]
            if page:
                r['page_text']=page
                score,tags,fit=base_score(r['title'],r['description']+' '+page,r['organization'])
                r['base_score']=max(r['base_score'],score)
                r['signals']=sorted(set(r['signals']+tags))
                r['fit_terms']=sorted(set(r['fit_terms']+fit))
        except Exception:
            pass

# Cluster multiple breadcrumbs into evolving projects.
clusters=[]
for r in sorted(raw,key=lambda x:x['base_score'],reverse=True):
    orgn=normalize_org(r['organization'])
    best=None; best_sim=0
    for c in clusters:
        sim=similarity(r['title'],c['title_seed'])
        same_org=orgn and orgn==c['org_norm'] and orgn not in GENERIC_ORGS
        if sim>=0.42 or (same_org and sim>=0.20):
            if sim+(0.25 if same_org else 0)>best_sim:
                best,best_sim=c,sim+(0.25 if same_org else 0)
    if best is None:
        clusters.append({'org_norm':orgn,'organization':r['organization'],'title_seed':r['title'],'items':[r]})
    else:
        best['items'].append(r)

old_agent={o.get('project_id') or o.get('id'):o for o in existing_opps if o.get('source_key')=='research_agent'}
new_projects=[]
for c in clusters:
    items=sorted(c['items'],key=lambda x:(x['base_score'],x['quality']),reverse=True)
    domains=sorted({hostname(x['url']).replace('www.','') for x in items if x.get('url')})
    urls=[]
    for x in items:
        if x['url'] not in urls: urls.append(x['url'])
    all_text=' '.join(x['title']+' '+x['description']+' '+x.get('page_text','')[:2500] for x in items)
    tags,fit,years,money=detect_signals(all_text)
    avg_quality=round(sum(x['quality'] for x in items)/len(items))
    stage,window,conf,why,next_signals=predict(tags,fit,len(domains),avg_quality,years)
    top=items[0]
    score=min(97,round(max(x['base_score'] for x in items)*0.72+conf*0.28+min(6,(len(domains)-1)*2)))
    project_id='project-'+fp(normalize_org(c['organization']),*sorted(tokens(c['title_seed']))[:8])
    evidence=[]
    for x in items[:8]:
        evidence.append({
            'date':x.get('date','')[:16],
            'kind':'Project signal',
            'title':x['title'][:220],
            'detail':x['description'][:500] or why,
            'source_url':x['url'],
            'source_label':hostname(x['url']).replace('www.','') or 'Web source',
            'strength':min(95,round((x['quality']+conf)/2))
        })
    verified_domains=[d for d in domains if source_quality('https://'+d)>=84]
    risk=[]
    if len(domains)==1: risk.append('single-source signal')
    if not verified_domains: risk.append('no first-party/official source yet')
    if not fit: risk.append('specialist interactive/AV scope not explicit yet')
    title=top['title'][:240]
    summary=(top['description'] or f'Potential museum project detected from {len(domains)} source domain(s).')[:900]
    prediction={
        'window':window,'reason':why,'signals':sorted(set(tags)),'fit_terms':sorted(set(fit))[:12],
        'source_count':len(evidence),'source_domains':domains,'source_diversity':len(domains),
        'source_quality':avg_quality,'expected_next_signals':next_signals,'risk_flags':risk,
        'opening_years':years[:3],'investment_signals':money,'why_now':why
    }
    obj={
        'id':'agent-'+project_id,'project_id':project_id,'title':title,'organization':c['organization'],
        'country':'','city':'','stage':stage,'score':score,'confidence':conf,'currency':'EUR',
        'deadline':None,'procurement_window':window,'summary':summary,
        'fit_rationale':'Upstream project intelligence matches museum/visitor-experience patterns associated with later exhibition, AV, interactive or interpretation procurement.',
        'pitch_angle':'Investigate before procurement: map the project owner, funding, design team and likely specialist packages; approach only when the evidence supports useful early contact.',
        'next_action':('Verify the strongest first-party source and watch for '+', '.join(next_signals[:2])+'.') if next_signals else 'Verify the project and procurement route.',
        'sample':False,'verified':False,'source_key':'research_agent','external_id':project_id,
        'source_url':top['url'],'source_label':hostname(top['url']).replace('www.','') or 'Web source',
        'documents':[{'title':x['title'][:160],'url':x['url'],'kind':'Source article'} for x in items[:5]],
        'updated_at':now(),'prediction':prediction,'evidence':evidence
    }
    # Avoid noisy churn: keep the old record unchanged when no new evidence or assessment appeared.
    old=old_agent.get(project_id) or old_agent.get(obj['id'])
    if old:
        old_urls={e.get('source_url') for e in old.get('evidence',[])}
        new_urls={e.get('source_url') for e in evidence}
        materially_changed=(new_urls-old_urls) or old.get('stage')!=stage or old.get('score')!=score or old.get('confidence')!=conf
        if not materially_changed:
            obj=old
    new_projects.append(obj)

new_projects=sorted(new_projects,key=lambda x:(x['score'],x['confidence'],x.get('prediction',{}).get('source_diversity',0)),reverse=True)[:80]

# Replace the previous Research Agent slice while keeping verified tenders and manual/static records.
non_agent=[o for o in existing_opps if o.get('source_key')!='research_agent']
OPPS.write_text(json.dumps(non_agent+new_projects,indent=2,ensure_ascii=False),encoding='utf8')

# Source discovery uses general web search and accumulates evidence over time.
known_domains={hostname(x.get('url','')).replace('www.','') for x in existing_sources if x.get('url')}
cand_by={hostname(x.get('url','')).replace('www.',''):x for x in existing_discovered if x.get('url')}
for q in platform_queries:
    rows=[]
    try: rows.extend(bing_search(q,18,False))
    except Exception as e: errors.append(f'platform-rss:{q}: {e}')
    if len(rows)<5:
        try: rows.extend(bing_html_search(q,12))
        except Exception as e: errors.append(f'platform-html:{q}: {e}')
    if len(rows)<3:
        try: rows.extend(ddg_search(q,10))
        except Exception as e: errors.append(f'platform-ddg:{q}: {e}')
    for r in rows:
        dom=hostname(r['url']).replace('www.','')
        if not dom or dom in known_domains or dom.endswith('museuminsider.co.uk'): continue
        text=(r['title']+' '+r['description']).lower()
        if not any(x in text for x in ['tender','procurement','rfp','contract','bid','framework','supplier']): continue
        if not any(x in text for x in ['museum','exhibition','gallery','heritage','visitor centre','visitor center','science centre','science center']): continue
        c=cand_by.get(dom) or {
            'name':dom,'region':'Unknown','type':'Discovered source candidate','status':'Needs verification',
            'url':'https://'+dom,'notes':'Autonomously discovered while searching for museum/exhibition procurement sources.',
            'confidence':40,'examples':[]
        }
        ex_urls={x.get('url') for x in c.get('examples',[])}
        if r['url'] not in ex_urls:
            c.setdefault('examples',[]).append({'title':r['title'][:180],'url':r['url']})
            c['examples']=c['examples'][-5:]
            c['confidence']=min(88,int(c.get('confidence',40))+8)
        cand_by[dom]=c

discovered=sorted(cand_by.values(),key=lambda x:(x.get('confidence',0),len(x.get('examples',[]))),reverse=True)[:40]
DISCOVERED.write_text(json.dumps(discovered,indent=2,ensure_ascii=False),encoding='utf8')

GRAPH.write_text(json.dumps({
    'generated_at':now(),
    'project_count':len(new_projects),
    'high_conviction':sum(1 for x in new_projects if x.get('confidence',0)>=75 and x.get('score',0)>=75),
    'projects':[{
        'project_id':x.get('project_id'),'title':x.get('title'),'organization':x.get('organization'),
        'stage':x.get('stage'),'score':x.get('score'),'confidence':x.get('confidence'),
        'procurement_window':x.get('procurement_window'),'prediction':x.get('prediction',{}),
        'source_url':x.get('source_url')
    } for x in new_projects]
},indent=2,ensure_ascii=False),encoding='utf8')

META.write_text(json.dumps({
    'last_run':now(),'lead_queries':len(lead_queries),'gdelt_queries':len(gdelt_queries),'buyer_watch_queries':len(watch_buyers[:18]),
    'platform_queries':len(platform_queries),'raw_signals':len(raw),'project_clusters':len(new_projects),
    'predicted_leads_added':len(new_projects),'high_conviction':sum(1 for x in new_projects if x.get('confidence',0)>=75 and x.get('score',0)>=75),
    'candidate_sources_found':len(discovered),'errors':errors[:30]
},indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'raw_signals':len(raw),'projects':len(new_projects),'high_conviction':sum(1 for x in new_projects if x.get('confidence',0)>=75 and x.get('score',0)>=75),'candidate_sources':len(discovered),'errors':len(errors)}))
