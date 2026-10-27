import unittest, importlib.util, tempfile, json
from pathlib import Path
path=Path(__file__).with_name('overture-discovery-pilot.py')
spec=importlib.util.spec_from_file_location('pilot',path)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class MatchTests(unittest.TestCase):
    def setUp(self):self.row={'place_id':'wikidata:Q1','name':'Museo Roma','latitude':41.9,'longitude':12.48,'category':'museums'}
    def data(self,features):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        f=Path(t.name)/'source.geojsonseq'
        f.write_text(''.join(json.dumps(x)+'\n' for x in features));return f
    def venue(self,name,lat=41.90001,lon=12.48001,website='https://museo.example.org',id='a'):
        return {'type':'Feature','properties':{'id':id,'names':{'primary':name},'websites':[website]},'geometry':{'coordinates':[lon,lat],'type':'Point'}}
    def test_match_is_not_import(self):
        rows,_=p.match([self.row],self.data([self.venue('Museo Roma')]))
        self.assertEqual(rows[0]['status'],'HIGH_CONFIDENCE_CANDIDATE')
        self.assertFalse(rows[0]['approved_for_import'])
    def test_different_name(self):
        rows,_=p.match([self.row],self.data([self.venue('Restaurant Noname')]))
        self.assertEqual(rows[0]['status'],'UNRESOLVED')
    def test_distant(self):
        rows,_=p.match([self.row],self.data([self.venue('Museo Roma',lat=41.95)]))
        self.assertEqual(rows[0]['status'],'UNRESOLVED')
    def test_ambiguity(self):
        rows,_=p.match([self.row],self.data([self.venue('Museo Roma'),self.venue('Museo Roma',id='b')]))
        self.assertEqual(rows[0]['status'],'REVIEW_AMBIGUOUS')
    def test_block_private_and_aggregators(self):
        for u in ['http://127.0.0.1/','https://evil.facebook.com/x','http://localhost/a','file:///etc/passwd','https://museo.internal/']:
            self.assertIsNone(p.valid_url(u))
    def test_bbox_limit(self):
        self.assertEqual(len(p.bbox([self.row]).split(',')),4)
        with self.assertRaises(ValueError):p.bbox([self.row,{**self.row,'longitude':13.3}])
    def test_empty_no_false_success(self):
        rows,_=p.match([self.row],self.data([]))
        self.assertEqual(rows[0]['status'],'UNRESOLVED')
if __name__=='__main__':unittest.main()
