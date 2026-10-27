#!/usr/bin/env python3
"""Direct anonymous Overture GeoParquet read, no STAC and no keys."""
import csv, json, sys
from pathlib import Path
import duckdb

inputs=list(csv.DictReader(open(sys.argv[1],newline='',encoding='utf8')))
out=Path(sys.argv[2])
west=min(float(r['longitude']) for r in inputs)-.003
east=max(float(r['longitude']) for r in inputs)+.003
south=min(float(r['latitude']) for r in inputs)-.003
north=max(float(r['latitude']) for r in inputs)+.003
c=duckdb.connect()
c.execute('INSTALL httpfs; LOAD httpfs;')
c.execute("SET s3_region = 'us-west-2'")
sql="""
SELECT id, names, websites,
       (bbox.xmin + bbox.xmax)/2 AS lon,
       (bbox.ymin + bbox.ymax)/2 AS lat
FROM read_parquet(
  's3://overturemaps-us-west-2/release/2026-10-21.0/theme=places/type=place/*',
  filename=true, hive_partitioning=1
)
WHERE bbox.xmin <= ? AND bbox.xmax >= ?
  AND bbox.ymin <= ? AND bbox.ymax >= ?
  AND websites IS NOT NULL
LIMIT 50000
"""
result=c.execute(sql,[east,west,north,south]).fetchall()
print(f'Overture geographic candidates with websites: {len(result)}',flush=True)
with out.open('w',encoding='utf8') as f:
    for id,names,websites,lon,lat in result:
        data={'type':'Feature','properties':{'id':id,'names':names,'websites':websites},
              'geometry':{'type':'Point','coordinates':[float(lon),float(lat)]}}
        f.write(json.dumps(data,default=str)+'\n')
