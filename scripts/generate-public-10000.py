#!/usr/bin/env python3
"""Public-data-only reproducible geotag sample; 500 each in four chosen cities."""
import argparse,csv,json,time,urllib.request,urllib.parse
from pathlib import Path

CITIES={
"rome":(41.8992,12.4823,"IT"),"paris":(48.8566,2.3522,"FR"),
"london":(51.5074,-0.1278,"GB"),"berlin":(52.5200,13.4050,"DE"),
"madrid":(40.4168,-3.7038,"ES"),"barcelona":(41.3874,2.1686,"ES"),
"lisbon":(38.7223,-9.1393,"PT"),"amsterdam":(52.3676,4.9041,"NL"),
"vienna":(48.2082,16.3738,"AT"),"prague":(50.0755,14.4378,"CZ"),
"istanbul":(41.0082,28.9784,"TR"),"athens":(37.9838,23.7275,"GR"),
"tokyo":(35.6762,139.6503,"JP"),"seoul":(37.5665,126.9780,"KR"),
"singapore":(1.3521,103.8198,"SG"),"sydney":(-33.8688,151.2093,"AU"),
"new-york":(40.7128,-74.0060,"US"),"chicago":(41.8781,-87.6298,"US"),
"toronto":(43.6532,-79.3832,"CA"),"mexico-city":(19.4326,-99.1332,"MX")}
HEADERS={"User-Agent":"SortiePublicOvertureBenchmark/1.0 (https://github.com/BuildBeast/digr-releases; independent geotag coverage test)","Accept":"application/json"}
OFFSETS=[(0,0),(.03,.03),(-.03,-.03),(.03,-.03),(-.03,.03),
 (.055,0),(-.055,0),(0,.055),(0,-.055),
 (.065,.035),(-.065,-.035),(-.065,.035),(.065,-.035)]
def fetch(city,lat,lon):
    seen={}
    for a,b in OFFSETS:
        params=urllib.parse.urlencode({"action":"query","list":"geosearch",
          "gscoord":f"{lat+a}|{lon+b}","gsradius":10000,"gslimit":500,
          "format":"json","formatversion":2})
        url="https://en.wikipedia.org/w/api.php?"+params
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=30) as resp:
                    result=json.load(resp)
                if "error" in result:raise RuntimeError(str(result["error"]))
                break
            except Exception as e:
                if attempt==2:raise RuntimeError(f"Wikipedia request failed for {city}: {e}") from e
                time.sleep(2*(attempt+1))
        for item in result.get("query",{}).get("geosearch",[]):
            if all(k in item for k in ("pageid","title","lat","lon")):
                if -90<float(item["lat"])<90 and -180<float(item["lon"])<180:
                    seen[item["pageid"]]=item
        if len(seen)>=525:break
        time.sleep(.5)
    if len(seen)<500:
        raise RuntimeError(f"Insufficient public geotags for {city}: {len(seen)} of required 500")
    return sorted(seen.values(),key=lambda x:x["pageid"])[:500]
def main():
    a=argparse.ArgumentParser();a.add_argument("--cities",nargs=4,required=True)
    a.add_argument("--out",required=True);args=a.parse_args()
    if len(set(args.cities))!=4 or any(c not in CITIES for c in args.cities):raise ValueError("Require four unique supported city names")
    rows=[]
    for city in args.cities:
        lat,lon,country=CITIES[city];items=fetch(city,lat,lon)
        for i in items:
            rows.append({"place_id":f"wikipedia:{i['pageid']}","name":i["title"],
             "latitude":i["lat"],"longitude":i["lon"],"city_slug":city,
             "country_code":country,"category":"wikipedia_geotagged_page"})
        print(f"{city}: {len(items)} independent public geotags",flush=True)
    if len(rows)!=2000 or len(set(r["place_id"] for r in rows))!=2000:
        raise RuntimeError("Expected 2000 unique public places per shard")
    with Path(args.out).open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f"Public places, four cities: {len(rows)}",flush=True)
if __name__=="__main__":main()
