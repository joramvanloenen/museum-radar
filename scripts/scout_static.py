#!/usr/bin/env python3
import json, re, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET, html
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
OPPS=DATA/'opportunities.json'; META=DATA/'meta.json'; CFG=DATA/'scout-config.json'; HIST=DATA/'historical-intelligence.json'
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

def parse_xml(raw):
    try: return ET.fromstring(raw)
    except ET.ParseError:
        fixed=re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\\d+;|#x[0-9a-fA-F]+;)','&amp;',raw)
        return ET.fromstring(fixed)

def history_model():
    try: return json.loads(HIST.read_text(encoding='utf8'))
    except Exception: return {}
HISTORY=history_model()
HISTORY_BUYERS={x.get('buyer','').lower():x for x in HISTORY.get('top_buyers',[])}

def relevance(title, desc='', org=''):
    text=(title+' '+desc+' '+org).lower()
    strong=['museum','visitor centre','visitor center','science centre','science center','heritage','exhibition','gallery']
    interactive=['interactive','multimedia','digital','immersive','interpretation','experience','projection','audiovisual','audio visual','av ','media installation']
    procurement=['tender','procurement','framework','rfp','request for proposal','market engagement','market consultation','contract']
    learned=HISTORY.get('learned_terms',[])
    negatives=HISTORY.get('negative_terms',[])
    hits=[w for w in strong+interactive+procurement if w in text]
    score=20*sum(w in text for w in strong)+10*sum(w in text for w in interactive)+5*sum(w in text for w in procurement)
    score+=8*sum(w in text for w in learned)
    score-=10*sum(w in text for w in negatives)
    b=HISTORY_BUYERS.get(org.lower().strip())
    if b:
        score+=min(12,2*b.get('high',0)+b.get('adjacent',0))
    if not any(w in text for w in strong): score//=2
    return max(0,min(98,score)), hits

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
    body={'query':q,'fields':['publication-number','notice-title','buyer-name','publication-date','deadline','estimated-value-proc','place-of-performance'],'page':1,'limit':min(limit,100),'scope':'ACTIVE','checkQuerySyntax':False,'paginationMode':'PAGE_NUMBER'}
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
    root=parse_xml(get_text(url)); rows=[]; items=root.findall('.//item')
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


def tenderned_search(limit=60):
    queries=[
        'site:tenderned.nl/papi/tenderned-rs-tns/v2/publicaties museum tentoonstelling aanbesteding',
        'site:tenderned.nl/papi/tenderned-rs-tns/v2/publicaties museum multimedia interactief',
        'site:tenderned.nl/papi/tenderned-rs-tns/v2/publicaties bezoekerscentrum tentoonstelling',
        'site:tenderned.nl/papi/tenderned-rs-tns/v2/publicaties scenografie museum'
    ]
    out=[]
    seen=set()
    for q in queries:
        try:
            root=ET.fromstring(get_text('https://www.bing.com/search?q='+urllib.parse.quote_plus(q)+'&format=rss'))
        except Exception:
            continue
        for i in root.findall('.//item')[:limit]:
            title=(i.findtext('title') or '').strip()
            desc=re.sub('<[^>]+>',' ',(i.findtext('description') or '')).strip()
            link=(i.findtext('link') or '').strip()
            if 'tenderned.nl/' not in link.lower():
                continue
            m=re.search(r'/publicaties/(\d+)',link)
            if not m:
                m=re.search(r'/overzicht/(\d+)',link)
            if not m:
                continue
            pub_id=m.group(1)
            if pub_id in seen:
                continue
            seen.add(pub_id)
            score,hits=relevance(title,desc,'TenderNed')
            if score<30:
                continue
            text=(title+' '+desc).lower()
            stage=stage_from(text,'auto')
            if stage not in ['Live Tender','Pre-market']:
                stage='Live Tender'
            canonical=f'https://www.tenderned.nl/aankondigingen/overzicht/{pub_id}'
            pdf=f'https://www.tenderned.nl/papi/tenderned-rs-tns/v2/publicaties/{pub_id}/pdf'
            out.append({
                'id':'tenderned-'+pub_id,
                'title':title or f'TenderNed publicatie {pub_id}',
                'organization':'TenderNed publicatie',
                'country':'Netherlands',
                'city':'',
                'stage':stage,
                'score':min(score,96),
                'confidence':88,
                'currency':'EUR',
                'deadline':None,
                'procurement_window':None,
                'summary':desc[:900] or 'Relevante Nederlandse aanbesteding gevonden via TenderNed.',
                'fit_rationale':'De openbare TenderNed-publicatie matcht op museum-, tentoonstellings- of interactieve ervaringstermen.',
                'pitch_angle':'Controleer de officiële publicatie en aanbestedingsstukken voordat u besluit in te schrijven.',
                'next_action':'Open TenderNed en controleer scope, sluitingsdatum, documenten en geschiktheidseisen.',
                'sample':False,
                'verified':True,
                'source_key':'tenderned',
                'external_id':pub_id,
                'source_url':canonical,
                'source_label':'Officiële TenderNed-publicatie',
                'documents':[
                    {'title':'TenderNed publicatie','url':canonical,'kind':'Contract notice'},
                    {'title':'Officiële publicatie PDF','url':pdf,'kind':'Tender PDF'}
                ],
                'updated_at':now(),
                'evidence':[{
                    'date':'',
                    'kind':'Procurement',
                    'title':'TenderNed publicatie gevonden',
                    'detail':desc[:500],
                    'source_url':canonical,
                    'source_label':'TenderNed',
                    'strength':88
                }]
            })
    return out


def parse_portal_date(value):
    value=(value or '').strip()
    for fmt in ('%d %B %Y','%d %b %Y','%d/%m/%Y','%d-%m-%Y','%d-%b-%y'):
        try: return datetime.strptime(value,fmt).replace(tzinfo=timezone.utc)
        except Exception: pass
    return None

def portal_category_search(base_url, source_key, source_name, country, cpv_codes, limit=20):
    found=[]; seen=set()
    for cpv in cpv_codes:
        try:
            raw=get_text(base_url.rstrip('/')+'/search/search_category.aspx?ID='+urllib.parse.quote(str(cpv)))
        except Exception:
            continue
        rows=re.findall(r'<tr[^>]*>.*?</tr>',raw,re.I|re.S)
        for row in rows:
            mm=re.search(r'href=["\']([^"\']*search_view\.aspx\?ID=([A-Za-z0-9_-]+)[^"\']*)["\'][^>]*>(.*?)</a>',row,re.I|re.S)
            if not mm: continue
            ref=mm.group(2)
            if ref in seen: continue
            title=html.unescape(re.sub('<[^>]+>',' ',mm.group(3)))
            title=re.sub(r'\s+',' ',title).strip()
            plain=html.unescape(re.sub('<[^>]+>',' ',row))
            plain=re.sub(r'\s+',' ',plain).strip()
            low=plain.lower()
            if not title or 'award' in low: continue
            score,_=relevance(title,plain+' museum exhibition audiovisual interactive immersive interpretation','')
            if score<35: continue
            deadline=None
            dm=re.search(r'Deadline Date:\s*(\d{1,2}[-/]?[A-Za-z]{3,9}[-/]?\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})',plain,re.I)
            if dm:
                rawdate=dm.group(1).replace('-',' ').replace('/',' ')
                dt=parse_portal_date(rawdate)
                if dt: deadline=dt.strftime('%Y-%m-%d')
            if deadline:
                try:
                    if datetime.strptime(deadline,'%Y-%m-%d').date() < datetime.now(timezone.utc).date():
                        continue
                except Exception: pass
            elif not any(x in low for x in ['prior information','preliminary market','market engagement','speculative notice']):
                continue
            org=''
            om=re.search(r'Published By:\s*(.*?)(?:Deadline Date:|Notice Type:|$)',plain,re.I)
            if om: org=om.group(1).strip()
            stage='Pre-market' if any(x in low for x in ['prior information','preliminary market','market engagement','speculative notice']) else 'Live Tender'
            url=urllib.parse.urljoin(base_url.rstrip('/')+'/',mm.group(1))
            seen.add(ref)
            found.append({
                'id':source_key+'-'+ref.lower(),'title':title,
                'organization':org or source_name,'country':country,'city':'','stage':stage,
                'score':min(score,98),'confidence':93,'currency':'GBP' if country=='United Kingdom' else 'EUR',
                'deadline':deadline,'procurement_window':None if deadline else 'Pre-market',
                'summary':'Official procurement listing discovered in a museum / exhibition / AV category.',
                'fit_rationale':'Official procurement notice matched museum, exhibition, AV or interactive experience terms.',
                'pitch_angle':'Review the official notice and decide whether to bid directly or with a delivery partner.',
                'next_action':'Open the official procurement notice and review scope, documents, deadline and eligibility.',
                'sample':False,'verified':True,'source_key':source_key,'external_id':ref,
                'source_url':url,'source_label':source_name,
                'documents':[{'title':'Official procurement notice','url':url,'kind':'Contract notice'}],
                'updated_at':now(),
                'evidence':[{'date':'','kind':'Procurement','title':'Official procurement listing','detail':plain[:500],'source_url':url,'source_label':source_name,'strength':93}]
            })
            if len(found)>=limit: return found
    return found

def search_feed(query, name='', country='', mode='pitch', limit=40):
    encoded=urllib.parse.quote_plus(query)
    url=f'https://www.bing.com/news/search?q={encoded}&format=rss'
    root=parse_xml(get_text(url))
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
            'verified':False if mode=='pitch' else True,
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
        trusted_tender_sources={'ted','contracts_finder','evergabe','tenderned','sell2wales','public_contracts_scotland','find_a_tender','etenders_ie','etendersni'}
        if o.get('stage') in ['Live Tender','Pre-market'] and o.get('source_key') not in trusted_tender_sources:
            continue
        if o.get('source_key') in trusted_tender_sources:
            o['verified']=True
        elif o.get('source_key') in {'research_agent','search_pitch','rss'}:
            o['verified']=False
        else:
            o['verified']=bool(o.get('verified',False))
        verified.append(o)
    live=sorted(verified,key=lambda x:(x.get('score',0),x.get('updated_at','')),reverse=True)[:500]
    return live,created

def main():
    cfg=json.loads(CFG.read_text(encoding='utf8')); existing=json.loads(OPPS.read_text(encoding='utf8')); found=[]; errors=[]
    for name,fn in [('TED',lambda:ted(cfg.get('max_items_per_source',100))),('Contracts Finder',lambda:contracts_finder(cfg.get('max_items_per_source',100),21))]:
        try: found.extend(fn())
        except Exception as e: errors.append(f'{name}: {e}')
    try:
        found.extend(tenderned_search(60))
    except Exception as e:
        errors.append(f'TenderNed: {e}')
    for portal in cfg.get('official_portal_searches',[]):
        try:
            found.extend(portal_category_search(
                portal.get('base_url',''),portal.get('source_key','official_portal'),
                portal.get('name','Official procurement portal'),portal.get('country',''),
                portal.get('cpv_codes',cfg.get('cpv_codes',[])),20))
        except Exception as e:
            errors.append(f"Portal {portal.get('name','')}: {e}")
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
