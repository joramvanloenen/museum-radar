#!/usr/bin/env python3
import json, re, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OPPS=DATA/'opportunities.json'
SOURCES=DATA/'sources.json'
DISCOVERED=DATA/'discovered-sources.json'
META=DATA/'research-agent-meta.json'
HIST=DATA/'historical-intelligence.json'
UA='MuseumRadarResearchAgent/0.1 (+GitHub Actions)'

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def fp(*xs): return hashlib.sha1('|'.join(str(x or '').lower().strip() for x in xs).encode()).hexdigest()[:18]
def clean_html(s): return re.sub(r'<[^>]+>',' ',s or '').replace('&amp;','&').strip()

def get_text(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, text/xml, */*'})
    with urllib.request.urlopen(req,timeout=25) as r:
        return r.read().decode('utf-8','replace')

def bing_news(query, limit=20):
    url='https://www.bing.com/news/search?'+urllib.parse.urlencode({'q':query,'format':'rss'})
    root=ET.fromstring(get_text(url))
    rows=[]
    for i in root.findall('.//item')[:limit]:
        rows.append({
            'title':clean_html(i.findtext('title') or ''),
            'description':clean_html(i.findtext('description') or ''),
            'url':(i.findtext('link') or '').strip(),
            'date':(i.findtext('pubDate') or '').strip()
        })
    return rows

def hostname(url):
    try: return urllib.parse.urlparse(url).hostname or ''
    except Exception: return ''

def load_json(path, default):
    try: return json.loads(path.read_text(encoding='utf8'))
    except Exception: return default

history=load_json(HIST,{})
learned=[x.lower() for x in history.get('learned_terms',[])]
negative=[x.lower() for x in history.get('negative_terms',[])]

museum_terms=['museum','museums','gallery','galleries','science centre','science center','visitor centre','visitor center','heritage centre','heritage center','interpretation centre','interpretive center','aquarium','zoo']
signal_terms={
    'funding':['funding approved','funding secured','grant awarded','investment approved','capital funding','heritage fund','lottery funding'],
    'design':['architect appointed','design team appointed','exhibition designer appointed','masterplan','master plan','concept design','design development'],
    'project':['new gallery','new museum','museum expansion','museum renovation','museum redevelopment','permanent exhibition','new exhibition','visitor centre','visitor center'],
    'procurement':['market engagement','market consultation','prior information notice','procurement planned','tender expected','request for information','supplier engagement'],
    'opening':['opening in','opens in','reopening in','completion in','construction starts','work begins']
}

def signal_score(title,desc):
    text=(title+' '+desc).lower()
    if not any(x in text for x in museum_terms): return 0,[]
    score=28
    tags=[]
    for tag,terms in signal_terms.items():
        n=sum(t in text for t in terms)
        if n:
            score += {'funding':18,'design':18,'project':14,'procurement':24,'opening':8}[tag]*min(n,2)
            tags.append(tag)
    score += 4*sum(t in text for t in learned[:80])
    score -= 7*sum(t in text for t in negative)
    return max(0,min(96,score)),tags

def predict(tags,text):
    t=text.lower()
    if 'procurement' in tags:
        return 'Expected','0–6 months',82,'Procurement language is already visible; formal competition may be near.'
    if 'design' in tags and 'funding' in tags:
        return 'Expected','2–9 months',78,'Funding plus a design/masterplan appointment often precedes exhibition or technical procurement.'
    if 'design' in tags:
        return 'Lead','3–12 months',70,'Design-team or masterplan activity often precedes specialist exhibition and media packages.'
    if 'funding' in tags:
        return 'Lead','3–15 months',68,'Confirmed capital funding commonly precedes consultant, exhibition and technical procurement.'
    if 'opening' in tags and 'project' in tags:
        return 'Pitch','2–12 months',62,'A dated project/opening signal suggests delivery packages may be forming.'
    return 'Signal','6–18 months',55,'Early project signal; timing still uncertain.'

lead_queries=[
    'museum renovation funding approved architect appointed',
    '"new gallery" museum funding architect appointed',
    'museum expansion masterplan exhibition designer',
    '"permanent exhibition" museum redevelopment funding',
    '"visitor centre" heritage funding architect appointed',
    '"science centre" expansion new gallery funding',
    'museum market engagement exhibition interactive',
    'museum procurement planned exhibition multimedia',
    'musée rénovation financement scénographie architecte',
    'Museum Sanierung Förderung Ausstellungsgestaltung Architekt',
    'museum verbouwing financiering tentoonstelling architect'
]
platform_queries=[
    '"museum" tender portal procurement exhibition',
    '"museum exhibition" procurement portal',
    '"science centre" tender procurement portal',
    '"visitor centre" procurement exhibition tender',
    '"museum" RFP platform exhibition design',
    '"museum" AV tender procurement'
]

opps=load_json(OPPS,[])
seen={(o.get('source_url') or '').strip() for o in opps if o.get('source_url')}
new_leads=[]
errors=[]
for q in lead_queries:
    try:
        rows=bing_news(q,18)
    except Exception as e:
        errors.append(f'lead:{q}: {e}')
        continue
    for r in rows:
        if not r['url'] or r['url'] in seen: continue
        score,tags=signal_score(r['title'],r['description'])
        if score<48: continue
        stage,window,conf,why=predict(tags,r['title']+' '+r['description'])
        org=(r['title'].split(':',1)[0] if ':' in r['title'] else hostname(r['url']).replace('www.',''))[:120]
        new_leads.append({
            'id':'agent-'+fp(r['url'],r['title']),
            'title':r['title'][:240],
            'organization':org or 'Unknown organisation',
            'country':'',
            'city':'',
            'stage':stage,
            'score':score,
            'confidence':conf,
            'currency':'EUR',
            'deadline':None,
            'procurement_window':window,
            'summary':r['description'][:900] or 'Potential future museum opportunity detected by the Research Agent.',
            'fit_rationale':'Potential upstream museum/visitor-experience signal matching historical high-fit patterns.',
            'pitch_angle':'Investigate early: identify project owner, funding, design team and likely specialist packages before formal procurement.',
            'next_action':'Follow the source and verify project status, budget, decision-makers and procurement route.',
            'sample':False,
            'verified':False,
            'source_key':'research_agent',
            'external_id':r['url'],
            'source_url':r['url'],
            'source_label':hostname(r['url']) or 'Web source',
            'documents':[{'title':'Source article','url':r['url'],'kind':'Source article'}],
            'updated_at':now(),
            'prediction':{'window':window,'reason':why,'signals':tags},
            'evidence':[{
                'date':r['date'][:16],
                'kind':'Predicted lead',
                'title':'Research Agent signal',
                'detail':why,
                'source_url':r['url'],
                'source_label':hostname(r['url']) or 'Web source',
                'strength':conf
            }]
        })
        seen.add(r['url'])

# Keep only the strongest predictions to avoid flooding the UI.
new_leads=sorted(new_leads,key=lambda x:(x['score'],x['confidence']),reverse=True)[:40]
by={o.get('id'):o for o in opps}
for o in new_leads: by[o['id']]=o
OPPS.write_text(json.dumps(list(by.values()),indent=2,ensure_ascii=False),encoding='utf8')

known=load_json(SOURCES,[])
known_domains={hostname(x.get('url','')).replace('www.','') for x in known if x.get('url')}
candidates={}
for q in platform_queries:
    try:
        rows=bing_news(q,15)
    except Exception as e:
        errors.append(f'platform:{q}: {e}')
        continue
    for r in rows:
        dom=hostname(r['url']).replace('www.','')
        if not dom or dom in known_domains or dom.endswith('museuminsider.co.uk'): continue
        text=(r['title']+' '+r['description']).lower()
        if not any(x in text for x in ['tender','procurement','rfp','contract','bid','framework']): continue
        if not any(x in text for x in ['museum','exhibition','gallery','heritage','visitor centre','visitor center','science centre','science center']): continue
        c=candidates.setdefault(dom,{
            'name':dom,
            'region':'Unknown',
            'type':'Discovered source candidate',
            'status':'Needs verification',
            'url':'https://'+dom,
            'notes':'Autonomously discovered while searching for museum/exhibition procurement sources.',
            'confidence':45,
            'examples':[]
        })
        c['confidence']=min(80,c['confidence']+8)
        if len(c['examples'])<3:
            c['examples'].append({'title':r['title'],'url':r['url']})

DISCOVERED.write_text(json.dumps(sorted(candidates.values(),key=lambda x:x['confidence'],reverse=True)[:30],indent=2,ensure_ascii=False),encoding='utf8')
META.write_text(json.dumps({
    'last_run':now(),
    'lead_queries':len(lead_queries),
    'platform_queries':len(platform_queries),
    'predicted_leads_added':len(new_leads),
    'candidate_sources_found':len(candidates),
    'errors':errors[:20]
},indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'predicted_leads':len(new_leads),'candidate_sources':len(candidates),'errors':len(errors)}))
