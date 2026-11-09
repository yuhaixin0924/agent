import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from bridge import Backend, validate_profile
from agent_snapshot.discovery import EvidenceError

TEXT='测试公司\nAgent 开发实习生\n每周至少3天。至少实习3个月。参与工具调用模块开发。'
PAGE={'url':'https://careers.example.com/intern','title':'Agent 开发实习生','text':TEXT,
      'links':[],'truncated':False,'fetched_at':'2026-11-09T00:00:00+00:00'}

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.backend=Backend(self.root)
    def tearDown(self):
        self.backend.close(); self.tmp.cleanup()
    def args(self,pid):
        return dict(primary_page_id=pid,title='Agent 开发实习生',company='测试公司',
          evidence=[dict(dimension='attendance',fact='每周至少3天',quote='每周至少3天',page_id=pid)],
          analysis='需核对时间',unknowns=['年级及远程未知'],next_step='向招聘方确认',reason='保留原文')
    def test_roundtrip_persistence_and_soft_hard_constraints(self):
        with patch('bridge.WebTools.read',return_value=PAGE):
            p=self.backend.execute('internship_read_page',{'url':PAGE['url']})
        result=self.backend.execute('internship_record',self.args(p['page_id']))
        self.backend.close(); self.backend=Backend(self.root)
        jid=result['job_id']
        (self.root/'profile.json').write_text(json.dumps({'days_per_week':2}))
        self.assertNotEqual(self.backend.get(jid)['match']['status'],'excluded')
        (self.root/'profile.json').write_text(json.dumps({'days_per_week':2,'hard_constraints':['days_per_week']}))
        self.assertEqual(self.backend.get(jid)['match']['status'],'excluded')
        self.assertEqual(self.backend.get(jid)['card']['evidence'][0]['quote'],'每周至少3天')
        self.backend.execute('internship_record',self.args(p['page_id']))
        self.assertEqual(len(self.backend.store.jobs()),1)
    def test_fabricated_quote_atomic_failure(self):
        p=self.backend.snapshot(PAGE); args=self.args(p['page_id'])
        args['evidence'][0]['quote']='每周至少4天'
        with self.assertRaises(EvidenceError) as error:
            self.backend.execute('internship_record',args)
        self.assertEqual(error.exception.errors[0]['index'],1)
        self.assertEqual(self.backend.store.jobs(),[])
    def test_unread_text_not_valid_until_page_read(self):
        p=self.backend.snapshot({**PAGE,'text':'测试公司 Agent 开发实习生\n'+'甲'*11000+'\n每周至少3天'})
        with self.assertRaises(EvidenceError):
            self.backend.execute('internship_record',self.args(p['page_id']))
        self.backend.execute('internship_read_snapshot',{'page_id':p['page_id'],'offset':10000})
        self.assertTrue(self.backend.execute('internship_record',self.args(p['page_id']))['saved'])
    def test_schema_and_network_boundaries(self):
        for tool,args in [('internship_status',{'path':'.env'}),('internship_list',{'offset':True}),
                          ('internship_read_snapshot',{'page_id':'missing','offset':0}),
                          ('internship_read_page',{'url':'https://127.0.0.1/'})]:
            with self.assertRaises(ValueError): self.backend.execute(tool,args)
        with self.assertRaises(ValueError): validate_profile({'hard_constraints':['remote']})
    def test_immutable_snapshots(self):
        old=self.backend.snapshot(PAGE)
        new=self.backend.snapshot({**PAGE,'text':TEXT+'更新'})
        self.assertNotEqual(old['page_id'],new['page_id'])
        self.assertEqual(self.backend.read_snapshot(old['page_id'],0)['text'],TEXT)
    def test_missing_profile_is_unknown(self):
        self.assertFalse(self.backend.execute('internship_profile',{})['configured'])
        self.assertFalse((self.root/'profile.json').exists())
    def test_optional_wording_not_hard_excluded(self):
        p=self.backend.snapshot({**PAGE,'text':TEXT.replace('每周至少3天','最好每周至少3天')})
        # Even if the model omits "最好" from its quote, the full source context wins.
        args=self.args(p['page_id'])
        jid=self.backend.record(args)['job_id']
        (self.root/'profile.json').write_text(json.dumps({'days_per_week':1,'hard_constraints':['days_per_week']}))
        self.assertNotEqual(self.backend.get(jid)['match']['status'],'excluded')

if __name__=='__main__': unittest.main()
