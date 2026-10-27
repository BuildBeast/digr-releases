#!/usr/bin/env python3
"""Independent public Wikipedia geosearch sample: 250 geotagged pages in each city."""
import csv, json, time, urllib.request, urllib.parse
from pathlib import Path

CITIES={
    "rome":(41.8992,12.4823,"IT"),
    "paris":(48.8566,2.3522,"FR"),
    "london":(51.5074,-0.1278,"GB"),
    "berlin":(52.5200,13.4050,"DE"),
}
OUTPUT=Path("public-wikipedia-1000.csv")
HEADERS={"User-Agent":"OverturePublicCoverageTest/1.0 (https://github.com/BuildBeast/digr-releases; public place coverage benchmark)","Accept":"application/json"}
def get(city,lat,lon):
    all_pages={}
    # Nearby searches use public article locations, not any Sortie records.
    offsets=[(0,0),(.028,.028),(-.028,-.028),(.028,-.028),(-.028,.028)]
    for offlat,offlon in offsets:
        query=urllib.parse.urlencode({
            "action":"query","list":"geosearch","gscoord":f"{lat+offlat}|{lon+offlon}",
            "gsradius":10000,"gslimit":500,"format":"json","formatversion":2
        })
        req=urllib.request.Request("https://en.wikipedia.org/w/api.php?"+query,headers=HEADERS)
        try:
            with urllib.request.urlopen(req,timeout=18) as response:data=json.load(response)
        except Exception as e:
            print(f"Public Wikipedia request failed {city}: {type(e).__name__}: {e}",flush=True)
            raise
        for p in data.get("query",{}).get("geosearch",[]):
            if not (-90<float(p["lat"])<90 and -180<float(p["lon"])<180):continue
            all_pages[p["pageid"]]=p
        if len(all_pages)>=280:break
        time.sleep(.6)
    result=sorted(all_pages.values(),key=lambda p:int(p['pageid']))
    if len(result)<250:raise RuntimeError(f"{city}: only {len(result)} independent geo-articles; needs 250")
    return result[:250]
def main():
    rows=[]
    for city,(lat,lon,country) in CITIES.items():
        items=get(city,lat,lon)
        for p in items:
            rows.append({"place_id":f"wikipedia:{p['pageid']}","name":p["title"],
                         "latitude":p["lat"],"longitude":p["lon"],
                         "city_slug":city,"country_code":country,"category":"wikipedia_geotagged_page"})
        print(f"{city}: {len(items)} Wikipedia geotagged public places",flush=True)
    assert len(rows)==1000 and len({r["place_id"] for r in rows})==1000
    with OUTPUT.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f"Frozen public source sample: {len(rows)} records across 4 cities",flush=True)
if __name__=="__main__":main()
