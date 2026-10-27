#!/usr/bin/env python3
"""Sortie: read-only Overture website discovery; never imports to Supabase."""
import argparse, csv, json, math, re, subprocess, os, unicodedata, ipaddress
from collections import defaultdict, Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

BLOCK = ('facebook.com','instagram.com','tripadvisor.com','wikipedia.org','wikidata.org','google.com','booking.com','yelp.com','tiktok.com')
def valid_url(url):
    if not isinstance(url,str): return None
    try:
        u=urlsplit(url.strip()); h=(u.hostname or '').lower().rstrip('.')
        if u.scheme not in ('https','http') or u.username or u.password or not h.count('.') or u.port not in (None,80,443): return None
        if h.endswith(('.local','.internal','.invalid','.test')): return None
        try: ipaddress.ip_address(h); return None
        except ValueError: pass
        if any(h==b or h.endswith('.'+b) for b in BLOCK): return None
        return url.strip()
    except ValueError: return None

def norm(x):
    x=unicodedata.normalize('NFKD',str(x or '')).casefold()
    return ' '.join(re.findall(r'\w+',''.join(c for c in x if not unicodedata.combining(c))))
def score(a,b):
    a,b=norm(a),norm(b)
    if not a or not b:return 0.0
    if a==b:return 1.0
    x,y=set(a.split()),set(b.split())
    return max(0.9*SequenceMatcher(None,a,b).ratio(),len(x&y)/len(x|y))
def metres(lat,lon,otherlat,otherlon):
    a,b,c,d=map(math.radians,(lat,lon,otherlat,otherlon))
    h=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 12742000*math.asin(min(1,math.sqrt(h)))
def websites(p):
    v=p.get('websites') or []
    if isinstance(v,(str,dict)): v=[v]
    if not isinstance(v,list):return []
    out=[]
    for item in v:
        u=valid_url(item.get('url') if isinstance(item,dict) else item)
        if u and u not in out:out.append(u)
    return out
def names(p):
    n=p.get('names') or {}
    if isinstance(n,str):return [n]
    if not isinstance(n,dict):return []
    vals=[n.get('primary')]
    c=n.get('common')
    if isinstance(c,dict):vals.extend(c.values())
    return [s for s in vals if isinstance(s,str) and s.strip()]
def features(path):
    with open(path,encoding='utf8') as f:
        head=f.read(200).lstrip();f.seek(0)
        if 'FeatureCollection' in head:yield from json.load(f).get('features',[])
        else:
            for line in f:
                if line.strip():yield json.loads(line.lstrip('\x1e'))
def load(path):
    with open(path,newline='',encoding='utf8') as f:rows=list(csv.DictReader(f))
    if not 1<=len(rows)<=1000 or len(set(p['place_id'] for p in rows))!=len(rows):raise ValueError('Invalid or duplicate input')
    for p in rows:
        p['latitude']=float(p['latitude']);p['longitude']=float(p['longitude'])
        if not (-90<=p['latitude']<=90 and -180<=p['longitude']<=180):raise ValueError('Invalid point')
    return rows
def bbox(rows):
    w=min(p['longitude'] for p in rows)-.003;e=max(p['longitude'] for p in rows)+.003
    s=min(p['latitude'] for p in rows)-.003;n=max(p['latitude'] for p in rows)+.003
    if e-w>.2 or n-s>.2:raise ValueError('Area too big, partition first')
    return ','.join(f'{v:.6f}' for v in (w,s,e,n))
def match(rows,path):
    grid=defaultdict(list);total=0;sites=0
    for f in features(path):
        total+=1
        p=f.get('properties') or {};u=websites(p);n=names(p)
        loc=(f.get('geometry') or {}).get('coordinates') or []
        if not u or not n or len(loc)<2:continue
        lon,lat=loc[:2]
        if not isinstance(lat,(float,int)) or not isinstance(lon,(float,int)) or not (-90<=lat<=90 and -180<=lon<=180):continue
        sites+=1
        grid[(math.floor(lat*100),math.floor(lon*100))].append((lat,lon,n,u,p.get('id') or f.get('id') or ''))
    results=[]
    for place in rows:
        lat,lon=place['latitude'],place['longitude'];cy=math.floor(lat*100);cx=math.floor(lon*100)
        candidates=[]
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                for plat,plon,n,u,oid in grid.get((cy+dy,cx+dx),[]):
                    dist=metres(lat,lon,plat,plon)
                    if dist>120:continue
                    sim,name=max((score(place['name'],item),item) for item in n)
                    if sim>=.65:candidates.append((sim,dist,name,u,oid))
        candidates.sort(key=lambda c:(-c[0],c[1]))
        r={'place_id':place['place_id'],'sortie_name':place['name'],'category':place.get('category',''),
           'status':'UNRESOLVED','website':'','overture_name':'','overture_id':'','distance_m':'','name_similarity':'',
           'candidate_count':len(candidates),'approved_for_import':False}
        if candidates:
            sim,dist,name,urls,oid=candidates[0]
            ambiguous=len(candidates)>1 and candidates[1][0]>=sim-.08
            status='REVIEW_AMBIGUOUS' if ambiguous else ('HIGH_CONFIDENCE_CANDIDATE' if sim>=.92 and dist<=65 and len(urls)==1 else 'REVIEW_MATCH')
            r.update(status=status,website=urls[0],overture_name=name,overture_id=oid,
                     distance_m=round(dist,1),name_similarity=round(sim,3))
        results.append(r)
    return results,{'features_scanned':total,'features_with_site_and_name':sites}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sortie',required=True);p.add_argument('--source-data',required=True);p.add_argument('--outdir',default='overture-results')
    p.add_argument('--skip-download',action='store_true');p.add_argument('--dry-run',action='store_true')
    args=p.parse_args();rows=load(args.sortie);bounds=bbox(rows);data=Path(args.source_data)
    if args.dry_run:print('Overture bbox:',bounds);return
    if not args.skip_download:
        subprocess.run(['overturemaps','download','--bbox='+bounds,'-f','geojsonseq','--type=place','--no-stac','--release=2026-10-21.0','-o',str(data)],check=True,timeout=350)
    if not data.is_file() or not data.stat().st_size:raise RuntimeError('No Overture records; cannot calculate recovery')
    results,meta=match(rows,data);out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    with (out/'candidates.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    found=sum(bool(x['website']) for x in results);counts=dict(Counter(x['status'] for x in results))
    summary={'sample':len(results),'website_candidates':found,'candidate_recovery_pct':round(found/len(results)*100,1),
             'statuses':counts,'overture':meta,'production_writes':0,'approved_for_import':0,'paid_api_calls':0,
             'warning':'Candidates are NOT verified official websites; do not import without separate source/identity verification'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    md=['# Sortie × Overture: real website discovery','','Places: '+str(len(results)),'Website candidates: '+str(found),
        'Candidate recovery: '+str(summary['candidate_recovery_pct'])+'%','','No websites imported or verified.','',
        '| Match status | Count |','|---|---:|']+[f'| {k} | {v} |' for k,v in counts.items()]
    md+=['','| Sortie place | Matched name | Website | Status |','|---|---|---|---|']
    for r in results:
        if r['website']:md.append('| '+ ' | '.join(str(r[k]).replace('|','/') for k in ('sortie_name','overture_name','website','status'))+' |')
    body='\n'.join(md)+'\n';(out/'summary.md').write_text(body)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(body)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
