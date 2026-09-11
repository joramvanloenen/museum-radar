#!/usr/bin/env python3
import json, re, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
OPPS=DATA/'opportunities.json'; META=DATA/'meta.json'; CFG=DATA/'scout-config.json'
UA='MuseumRadar/0.3 (+GitHub Pages scout)'

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def get_json(url, method='GET', body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(url,data=data,method=method,headers={'User-Agent':UA,'Accept':'application/json','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)
def get_text(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/atom+xml, text/xml, */*'})
    with urllib.request.urlopen(req,timeout=30) as r: return r.read().decode('utf-8','replace')
def fp(*xs): return hashlib.sha1('|'.join(str(x or '').strip().lower() for x in xs).encode()).hexdigest()[:18]
def flat(x):
    if isinstance(x,dict): return ' '.join(flat(v) for v in x.values())
    if isinstance(x,list): return ' '.join(flat(v) for v in x)
    return str(x or '')

def relevance(title, desc='', org=''):
    text=(title+' '+desc+' '+org).lower()
    strong=['museum','visitor centre','visitor center','science centre','science center','heritage','exhibition','gallery']
    interactive=['interactive','multimedia','digital','immersive','interpretation','experience','projection','audiovisual','audio visual','av ','media installation']
    procurement=['tender','procurement','framework','rfp','request for proposal','market engagement','market consultation','contract']
    hits=[w for w in strong+interactive+procurement if w in text]
    score=min(98,20*sum(w in text for w in strong)+10*sum(w in text for w in interactive)+5*sum(w in text for w in procurement))
    if not any(w in text for w in strong): score//=2
    return score, hits

def stage_from(text, mode='auto'):
    t=text.lower()
    if any(x in t for x in ['market engagement','market consultation','prior information','pre-market']): return 'Pre-market'
    if any(x in t for x in ['tender','procurement','request for proposal','rfp','rfq','contract notice','call for tenders','appel d\'offres','aanbesteding','ausschreibung','vergabe']): return 'Live Tender'
    if mode=='pitch' and any(x in t for x in ['funding','funded','renovation','expansion','new gallery','new museum','visitor centre','visitor center','appointed','masterplan','master plan','architect','exhibition designer','scenography','new permanent exhibition','neue dauerausstellung','verbouwing','rénovation']): return 'Pitch'
    if any(x in t for x in ['funding approved','funding secured','appointed','masterplan','master plan','renovation','expansion']): return 'Lead'
    return 'Signal'

def classify_document(title='', url='', kind=''):
    text=(' '.join([str(title or ''),str(url or ''),str(kind or '')])).lower()
    if any(x in text for x in ['market consultation','market engagement','prior information','pin notice']): return 'Market consultation'
    if any(x in text for x in ['design brief','creative brief','exhibition brief','interpretation brief']): return 'Design brief'
    if any(x in text for x in ['requirement','qualification','selection criteria','scope of work','statement of work']): return 'Requirements'
    if any(x in text for x in ['technical spec','specification','technical requirement']): return 'Technical specs'
    if any(x in text for x in ['drawing','floor plan','floorplan','architectural plan','layout']): return 'Drawings / plans'
    if any(x in text for x in ['budget','funding','grant','finance','business case']): return 'Budget / funding'
    if any(x in text for x in ['council','municipal','committee','decision','resolution','minutes']): return 'Council decision'
    if any(x in text for x in ['contract notice','procurement notice','tender notice']): return 'Contract notice'
    if str(url or '').lower().split('?')[0].endswith('.pdf') or 'tender pdf' in text or 'brief pdf' in text: return 'Tender PDF'
    if any(x in text for x in ['article','news','press release','announcement']): return 'Source article'
    return str(kind or 'Document') if str(kind or '').lower() != 'document' else 'Document'

def ted(limit=100):
    q='FT=(museum OR exhibition OR interactive OR multimedia OR heritage OR "visitor centre" OR "visitor center")'
    body={'query':q,'fields':['publication-number','notice-title','buyer-name','publication-date','deadline','estimated-value-procurement','place-of-performance'],'page':1,'limit':min(limit,100),'scope':'ACTIVE','checkQuerySyntax':False,'paginationMode':'PAGE_NUMBER'}
    raw=get_json('https://api.ted.europa.eu/v3/notices/search','POST',body)
    rows=raw.get('notices') or raw.get('results') or []
    out=[]
    for r in rows:
        def val(k,d=''):
            v=r.get(k,d)
            if isinstance(v,list): return v[0] if v else d
            if isinstance(v,dict): return next(iter(v.values()),d)
            return v
        title=str(val('notice-title','EU procurement notice')); org=str(val('buyer-name','Unknown buyer'))
        score,hits=relevance(title,flat(r),org)
        if score<25: continue
        pub=str(val('publication-number',''))
        source_url=f'https://ted.europa.eu/en/notice/-/detail/{pub}' if pub else ''
        out.append({'id':'ted-'+(pub or fp(title,org)), 'title':title,'organization':org,'country':'','city':'','stage':'Live Tender','score':score,'confidence':86,'currency':'EUR','deadline':str(val('deadline',''))[:10] or None,'procurement_window':None,'summary':'Relevant EU procurement notice detected by the automated TED scout.','fit_rationale':'Matched museum / exhibition / interactive procurement language.','pitch_angle':'Review the source notice before deciding whether to bid.','next_action':'Open the TED notice and verify scope, eligibility, budget and deadline.','sample':False,'source_key':'ted','external_id':pub,'source_url':source_url,'source_label':'TED notice','documents':[{'title':'TED notice','url':source_url,'kind':classify_document('TED notice',source_url,'Procurement notice')}] if source_url else [],'updated_at':now(),'evidence':[{'date':str(val('publication-date',''))[:10],'kind':'Procurement','title':'TED notice detected','detail':'Automated discovery. Verify the complete notice at the source.','source_url':source_url,'source_label':'TED notice','strength':86}]})
    return out

def contracts_finder(limit=100,days=21):
    start=(datetime.now(timezone.utc)-timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z')
    body={'searchCriteria':{'publishedFrom':start,'stages':['tender','planning']},'orderBy':'publishedDate','order':'DESC','size':min(limit,100),'page':1}
    raw=get_json('https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search','POST',body)
    rows=[]
    if isinstance(raw,list): rows=raw
    elif isinstance(raw,dict):
        for k in ('releases','results','noticeOCDS','items'):
            if isinstance(raw.get(k),list): rows=raw[k]; break
        if not rows and isinstance(raw.get('releasePackage'),dict): rows=raw['releasePackage'].get('releases',[])
    out=[]
    for r in rows:
        t=r.get('tender') or {}; buyer=r.get('buyer') or {}; title=t.get('title') or 'UK procurement notice'; desc=t.get('description') or ''; org=buyer.get('name') or 'Unknown buyer'
        score,hits=relevance(title,desc,org)
        if score<25: continue
        period=t.get('tenderPeriod') or {}; ext=r.get('ocid') or r.get('id') or fp(title,org)
        docs=[]
        for d in t.get('documents') or []:
            if not d.get('url'): continue
            doc_title=d.get('title') or d.get('description') or 'Tender document'
            doc_url=d.get('url')
            docs.append({'title':doc_title,'url':doc_url,'kind':classify_document(doc_title,doc_url,d.get('documentType') or 'Document')})
        url=docs[0]['url'] if docs else ''
        out.append({'id':'cf-'+fp(ext),'title':title,'organization':org,'country':'United Kingdom','city':'','stage':stage_from(title+' '+desc),'score':score,'confidence':82,'currency':'GBP','deadline':(period.get('endDate') or '')[:10] or None,'procurement_window':None,'summary':re.sub('<[^>]+>',' ',desc)[:900] or 'Relevant UK procurement notice detected by Contracts Finder.','fit_rationale':'Matched museum / exhibition / visitor-experience language.','pitch_angle':'Review the procurement notice and qualification requirements.','next_action':'Open source and triage scope, budget, deadline and bidder requirements.','sample':False,'source_key':'contracts_finder','external_id':ext,'source_url':url,'source_label':'Contracts Finder notice','documents':docs,'updated_at':now(),'evidence':[{'date':(r.get('date') or '')[:10],'kind':'Procurement','title':'Contracts Finder notice detected','detail':'Automated discovery. Verify against the original procurement notice.','source_url':url,'source_label':'Contracts Finder notice','strength':82}]})
    return out

def rss(url,name='',country='',limit=100):
    root=ET.fromstring(get_text(url)); rows=[]; items=root.findall('.//item')
    if items:
        for i in items[:limit]: rows.append(((i.findtext('title') or '').strip(),(i.findtext('description') or '').strip(),(i.findtext('link') or '').strip(),(i.findtext('pubDate') or '').strip()))
    else:
        ns={'a':'http://www.w3.org/2005/Atom'}
        for i in root.findall('.//a:entry',ns)[:limit]:
            le=i.find('a:link',ns); rows.append(((i.findtext('a:title',default='',namespaces=ns) or '').strip(),(i.findtext('a:summary',default='',namespaces=ns) or '').strip(),le.attrib.get('href','') if le is not None else '',(i.findtext('a:updated',default='',namespaces=ns) or '').strip()))
    out=[]
    for title,desc,url,pub in rows:
        clean=re.sub('<[^>]+>',' ',desc); score,hits=relevance(title,clean,name)
        if score<25: continue
        out.append({'id':'rss-'+fp(url or title,pub),'title':title,'organization':name or 'Web signal','country':country,'city':'','stage':stage_from(title+' '+clean),'score':min(score,78),'confidence':58,'currency':'EUR','deadline':None,'procurement_window':'Unknown — investigate','summary':clean[:900],'fit_rationale':'Early web signal matching museum / exhibition / interactive project language.','pitch_angle':'Investigate before contacting; this may be upstream of formal procurement.','next_action':'Follow the source, identify project owner, funding, design team and expected opening date.','sample':False,'source_key':'rss','external_id':url or fp(title,pub),'source_url':url,'source_label':name or 'Original article','documents':[{'title':'Original article','url':url,'kind':classify_document('Original article',url,'Source article')}] if url else [],'updated_at':now(),'evidence':[{'date':pub[:10],'kind':'Web signal','title':'Relevant project signal detected','detail':clean[:500],'source_url':url,'source_label':name or 'Original article','strength':58}]})
    return out

def search_feed(query, name='', country='', mode='pitch', limit=40):
    encoded=urllib.parse.quote_plus(query)
    url=f'https://www.bing.com/news/search?q={encoded}&format=rss'
    root=ET.fromstring(get_text(url))
    out=[]
    for i in root.findall('.//item')[:limit]:
        title=(i.findtext('title') or '').strip()
        desc=re.sub('<[^>]+>',' ',(i.findtext('description') or '')).strip()
        link=(i.findtext('link') or '').strip()
        pub=(i.findtext('pubDate') or '').strip()
        if not link: 
            continue
        score,hits=relevance(title,desc,name)
        if mode=='pitch':
            early=['funding','renovation','expansion','new museum','new gallery','new permanent exhibition','visitor centre','visitor center','architect','appointed','masterplan','exhibition designer','scenography','redevelopment','redevelop','verbouwing','sanierung','rénovation']
            score=min(92,score+8*sum(x in (title+' '+desc).lower() for x in early))
        if score<25:
            continue
        stage=stage_from(title+' '+desc,'pitch')
        if mode=='tender':
            # Generic news/web search is discovery only. It may point us toward a real tender,
            # but must never publish a formal tender without a trusted procurement-source record.
            continue
        if stage=='Live Tender':
            stage='Pitch'
        out.append({
            'id':'search-'+fp(link,title),
            'title':title or 'Museum opportunity',
            'organization':name or 'Web discovery',
            'country':country,
            'city':'',
            'stage':stage,
            'score':min(score,92 if mode=='pitch' else 96),
            'confidence':62 if mode=='pitch' else 72,
            'currency':'EUR',
            'deadline':None,
            'procurement_window':'Investigate' if mode=='pitch' else None,
            'summary':desc[:900] or 'Relevant opportunity discovered by autonomous search.',
            'fit_rationale':'Autonomous search matched museum / exhibition / interactive opportunity language.',
            'pitch_angle':'Investigate the project owner, design team, funding and procurement route before outreach.' if mode=='pitch' else 'Review the formal notice and participation requirements.',
            'next_action':'Open the source and verify the project, owner and timing.' if mode=='pitch' else 'Open the source and verify scope, deadline and bidder requirements.',
            'sample':False,
            'verified':True,
            'source_key':'search_'+mode,
            'external_id':link,
            'source_url':link,
            'source_label':name or 'Search result',
            'documents':[{'title':title or 'Source article','url':link,'kind':classify_document(title,link,'Source article')}],
            'updated_at':now(),
            'evidence':[{'date':pub[:16],'kind':'Web source','title':title or 'Search result','detail':desc[:500],'source_url':link,'source_label':name or 'Search result','strength':62 if mode=='pitch' else 72}]
        })
    return out

def merge(existing,incoming):
    bykey={}
    for o in existing:
        key=(o.get('source_key'),o.get('external_id')) if o.get('source_key') and o.get('external_id') else ('id',o.get('id'))
        bykey[key]=o
    created=0
    for o in incoming:
        key=(o.get('source_key'),o.get('external_id'))
        if key in bykey:
            old=bykey[key]; o['watched']=old.get('watched',False); bykey[key]=o
        else:
            bykey[key]=o; created+=1
    vals=list(bykey.values())
    verified=[]
    for o in vals:
        if o.get('sample'):
            continue
        has_source=bool(o.get('source_url')) or any((e or {}).get('source_url') for e in (o.get('evidence') or []))
        if not has_source:
            continue
        trusted_tender_sources={'ted','contracts_finder','evergabe'}
        if o.get('stage') in ['Live Tender','Pre-market'] and o.get('source_key') not in trusted_tender_sources:
            continue
        o['verified']=True
        verified.append(o)
    live=sorted(verified,key=lambda x:(x.get('score',0),x.get('updated_at','')),reverse=True)[:500]
    return live,created

def main():
    cfg=json.loads(CFG.read_text(encoding='utf8')); existing=json.loads(OPPS.read_text(encoding='utf8')); found=[]; errors=[]
    for name,fn in [('TED',lambda:ted(cfg.get('max_items_per_source',100))),('Contracts Finder',lambda:contracts_finder(cfg.get('max_items_per_source',100),21))]:
        try: found.extend(fn())
        except Exception as e: errors.append(f'{name}: {e}')
    for feed in cfg.get('rss_feeds',[]):
        try: found.extend(rss(feed['url'],feed.get('name',''),feed.get('country',''),cfg.get('max_items_per_source',100)))
        except Exception as e: errors.append(f"RSS {feed.get('name',feed.get('url',''))}: {e}")
    for search in cfg.get('search_queries',[]):
        try:
            found.extend(search_feed(search.get('query',''),search.get('name',''),search.get('country',''),search.get('mode','pitch'),40))
        except Exception as e:
            errors.append(f"Search {search.get('name',search.get('query',''))}: {e}")
    min_score=int(cfg.get('minimum_score',35))
    found=[o for o in found if o.get('score',0)>=min_score and o.get('source_url')]
    merged,created=merge(existing,found)
    OPPS.write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf8')
    meta=json.loads(META.read_text(encoding='utf8'))
    meta.update({'status':'GitHub Actions scout','generated_at':now(),'last_scan_at':now(),'last_scan_found':len(found),'last_scan_relevant':len(found),'total_opportunities':len(merged),'last_error':' | '.join(errors) if errors else ''})
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'found':len(found),'created':created,'errors':errors,'total':len(merged)}))

if __name__=='__main__': main()
