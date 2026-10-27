#!/usr/bin/env python3
"""Read-only independent domain corroboration. P856 is independent evidence, not proof of site control."""
import argparse,csv,json,time,urllib.parse,urllib.request,ipaddress
from collections import Counter
from pathlib import Path

BAD=('airbnb.com','booking.com','tripadvisor.com','expedia.com','hotels.com','getyourguide.com','viator.com','facebook.com','instagram.com','wikipedia.org','wikidata.org','yelp.com','google.com','rome.info','romainweb.com','joinrome.com')
HEADERS={'User-Agent':'SortieOvertureVerification/1.0 (https://github.com/BuildBeast/digr-releases; open data research)','Accept':'application/json'}
def hostname(url):
    try:
        p=urllib.parse.urlsplit((url or '').strip());h=(p.hostname or '').lower().rstrip('.')
        if p.scheme not in ('https','http') or not h or not '.' in h or p.username or p.password: return ''
        try:ipaddress.ip_address(h);return ''
        except ValueError:pass
        return h
    except ValueError:return ''
def blocked(h):return any(h==b or h.endswith('.'+b) for b in BAD)
def same_domain(a,b):
    # Only exact hostname or www prefix equivalence. Never equate sibling subdomains.
    return a.removeprefix('www.')==b.removeprefix('www.')
def api(url,params):
    query=urllib.parse.urlencode(params);req=urllib.request.Request(url+'?'+query,headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
        except Exception:
            if attempt==2:raise
            time.sleep(2*(attempt+1))
def chunks(seq,n):
    for i in range(0,len(seq),n):yield seq[i:i+n]
def independent_official_sites(rows):
    pageids=sorted({r['place_id'].split(':',1)[1] for r in rows if r['place_id'].startswith('wikipedia:') and r['place_id'].split(':',1)[1].isdigit()})
    pg_q={}
    for block in chunks(pageids,50):
        payload=api('https://en.wikipedia.org/w/api.php',{'action':'query','prop':'pageprops','ppprop':'wikibase_item','pageids':'|'.join(block),'format':'json'})
        for pid,page in payload.get('query',{}).get('pages',{}).items():
            q=page.get('pageprops',{}).get('wikibase_item')
            if q:pg_q[str(pid)]=q
        time.sleep(.1)
    qids=sorted(set(pg_q.values()));site_by_q={}
    for block in chunks(qids,50):
        payload=api('https://www.wikidata.org/w/api.php',{'action':'wbgetentities','ids':'|'.join(block),'props':'claims','format':'json'})
        for q,entity in payload.get('entities',{}).items():
            sites=set()
            for claim in entity.get('claims',{}).get('P856',[]):
                value=claim.get('mainsnak',{}).get('datavalue',{}).get('value')
                if isinstance(value,str):
                    h=hostname(value)
                    if h:sites.add(h)
            site_by_q[q]=sites
        time.sleep(.1)
    return { 'wikipedia:'+pid:site_by_q.get(q,set()) for pid,q in pg_q.items() },len(pg_q),len(qids)
def verify(rows,official):
    out=[]
    for r in rows:
        h=hostname(r.get('website',''));corroboration=official.get(r.get('place_id'),set())
        reason=''
        if not h or r.get('status')=='UNRESOLVED':
            decision='UNRESOLVED';reason='No valid candidate'
        elif blocked(h):
            decision='REJECT_THIRD_PARTY';reason='Known aggregator or travel content domain'
        elif r.get('status')=='REVIEW_AMBIGUOUS':
            decision='REVIEW_AMBIGUOUS';reason='Multiple close candidate venues, independent domain match not sufficient'
        elif any(same_domain(h,s) for s in corroboration):
            decision='CORROBORATED_DOMAIN';reason='Exact host independently listed as official website on Wikidata P856; still requires operator and venue review'
        elif corroboration:
            decision='REVIEW_DOMAIN_CONFLICT';reason='Wikidata lists other official website domain(s)'
        else:
            decision='REVIEW_NO_INDEPENDENT_PROOF';reason='No independent official domain in Wikidata'
        out.append({**r,'verification':decision,'verification_reason':reason,'independent_official_hosts':';'.join(sorted(corroboration)),'approved_for_import':False})
    return out
def main():
    a=argparse.ArgumentParser()
    a.add_argument('--candidates',required=True);a.add_argument('--outdir',required=True)
    args=a.parse_args()
    with open(args.candidates,newline='',encoding='utf8') as f:rows=list(csv.DictReader(f))
    if not rows or len(rows)>3000:raise RuntimeError('Invalid candidate batch')
    official,pages,entities=independent_official_sites(rows)
    result=verify(rows,official);path=Path(args.outdir);path.mkdir(parents=True,exist_ok=True)
    with (path/'verified.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
    counts=dict(Counter(r['verification'] for r in result))
    summary={'sample':len(result),'candidate_count':sum(bool(r.get('website')) for r in result),
       'status_counts':counts,'wikipedia_wikidata_ids':pages,'wikidata_entities':entities,
       'confirmed_official_websites':0,'independent_domain_corroborations':counts.get('CORROBORATED_DOMAIN',0),
       'approved_for_import':0,'production_writes':0,'notes':'P856 domain corroboration is not sufficient proof of official operator or content licence; all remain unapproved'}
    (path/'verification-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('INDEPENDENT_VERIFICATION_SUMMARY='+json.dumps(summary),flush=True)
    if __import__('os').environ.get('GITHUB_STEP_SUMMARY'):
        with open(__import__('os').environ['GITHUB_STEP_SUMMARY'],'a') as f:
            f.write('### Independent official-domain corroboration\n\n'+json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
