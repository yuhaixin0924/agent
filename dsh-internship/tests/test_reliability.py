import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from bridge import Backend
from candidates import Candidates, QUERIES, is_active, screen
from agent_snapshot.core import encode

URL='https://www.nowcoder.com/jobs/123'
PAGE={'url':URL,'title':'Python开发实习生','text':'Python开发实习生\n工作地点：上海\n学历：本科及以上\n岗位职责：参与后端接口开发。\n投递简历请见申请入口。',
      'fetched_at':'2026-11-09T00:00:00+00:00','links':[],'truncated':False}

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.backend=Backend(self.tmp.name)
        self.q=Candidates(self.backend)
        self.web=Mock(); self.web.read.return_value=PAGE
        self.cid=self.q.add(QUERIES[0],[URL])['added'][0]
    def tearDown(self):
        self.backend.close(); self.tmp.cleanup()
    def item(self):
        return next(r for r in self.q.rows() if r['id']==self.cid)
    def test_failure_does_not_renew_success_or_return_to_active_on_report(self):
        first=self.q.check(self.cid,self.web)
        self.assertTrue(is_active(first))
        success=first['last_check_success_at']
        self.web.read.side_effect=TimeoutError()
        summary=self.q.recheck(web=self.web)
        self.assertEqual(summary['active'],0)
        self.assertEqual(self.item()['last_check_success_at'],success)
        for _ in range(2):
            r=self.q.report()
            self.assertEqual(r['counts']['active'],0)
            self.assertEqual(r['candidates'][0]['listing_status'],'unknown')
        self.web.read.side_effect=None
        self.q.recheck(web=self.web)
        self.assertTrue(is_active(self.item()))
    def test_http_missing_survives_cached_rescreen_and_can_recover(self):
        self.q.check(self.cid,self.web)
        self.web.read.side_effect=ValueError('网页 HTTP 404')
        self.q.recheck(web=self.web)
        self.assertEqual(self.q.report()['candidates'][0]['listing_status'],'closed')
        self.assertEqual(self.item()['closure_reason'],'http_missing')
        self.web.read.side_effect=None
        self.q.recheck(web=self.web)
        self.assertEqual(self.q.report()['candidates'][0]['listing_status'],'suspected_open')
    def test_expired_freshness_future_and_legacy_timestamps(self):
        item=self.q.check(self.cid,self.web)
        for stamp in [(datetime.now(timezone.utc)-timedelta(days=7,seconds=1)).isoformat(),
                      (datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
                      '2026-11-09T00:00:00', 'broken']:
            self.assertFalse(is_active({**item,'last_check_success_at':stamp}))
        legacy={**item,'rechecked_at':datetime.now(timezone.utc).isoformat()}
        del legacy['last_check_outcome']
        self.assertFalse(is_active(legacy))
    def test_redirect_outside_allowlist_is_unknown(self):
        self.q.check(self.cid,self.web)
        self.web.read.return_value={**PAGE,'url':'https://unlisted.example/123'}
        self.q.recheck(web=self.web)
        self.assertFalse(is_active(self.item()))
        self.assertEqual(self.item()['listing_status'],'unknown')
    def test_initial_failure_can_be_rechecked(self):
        self.web.read.side_effect=TimeoutError()
        self.q.check(self.cid,self.web)
        self.web.read.side_effect=None
        self.assertEqual(self.q.recheck(web=self.web)['checked'],1)
        self.assertTrue(is_active(self.item()))
    def test_guide_home_and_unknown_not_promoted_by_keywords(self):
        for page in [{**PAGE,'title':'Python实习面试攻略'},
                     {**PAGE,'title':'招聘首页','url':'https://www.nowcoder.com/'},
                     {**PAGE,'title':'招聘总公告'},
                     {**PAGE,'title':'校园通知','url':'https://www.nowcoder.com/discuss/123'}]:
            self.assertEqual(screen(page)['screening'],'needs_review')
        self.assertEqual(screen(PAGE)['page_kind'],'job_detail')
    def test_negated_expiry_does_not_close_job(self):
        for text in ('岗位尚未停止招聘','若职位已下线请联系我们','其他职位已结束'):
            self.assertNotEqual(screen({**PAGE,'text':PAGE['text']+'\n'+text})['screening'],'expired')
        self.assertEqual(screen({**PAGE,'text':PAGE['text']+'\n职位已关闭'})['screening'],'expired')
    def test_profile_plan_persists_and_accepts_registered_supplement(self):
        path=Path(self.tmp.name)/'profile.json'
        path.write_text(json.dumps({'cities':['上海'],'keywords':['后端'],'background':'隐私经历不进入查询'}))
        result=self.q.plan(extra_queries=['上海 后端 暑期 实习'])
        self.assertTrue(all('上海' in q and '广州' not in q for q in result['queries']))
        self.assertNotIn('隐私',json.dumps(result,ensure_ascii=False))
        self.backend.close(); self.backend=Backend(self.tmp.name); self.q=Candidates(self.backend)
        self.q.add('上海 后端 暑期 实习',[])
        with self.assertRaises(ValueError): self.q.add('尚未登记 实习',[])
        with self.assertRaises(ValueError): self.q.plan(extra_queries=['实习 联系foo@example.com'])
        self.assertEqual(len(self.q.plan(mode='baseline')['queries']),len(set(QUERIES)))
    def test_missing_profile_never_defaults_to_guangzhou(self):
        result=self.q.plan()
        self.assertEqual(result['missing_profile_fields'],['cities','keywords'])
        self.assertFalse(any('广州' in q for q in result['queries']))
    def test_legacy_cache_rescreen_does_not_count_as_live_fetch(self):
        item=self.q.check(self.cid,self.web)
        for k in ['last_check_success_at','last_check_outcome','page_kind']: item.pop(k,None)
        with self.backend.store.db:
            self.backend.store.db.execute('UPDATE plugin_candidates SET data=? WHERE id=?',(encode(item),self.cid))
        report=self.q.report()
        self.assertEqual(report['counts']['active'],0)
        self.assertEqual(report['candidates'][0]['page_kind'],'job_detail')
    def test_recheck_content_dedup(self):
        self.q.check(self.cid,self.web)
        other=self.q.add(QUERIES[0],[URL+'?v=2'])['added'][0]
        self.web.read.return_value={**PAGE,'url':URL+'?v=2','text':PAGE['text']+'初始不同正文'}
        self.q.check(other,self.web)
        self.web.read.side_effect=[PAGE,{**PAGE,'url':URL+'?v=2'}]
        self.q.recheck(limit=2,web=self.web)
        self.assertEqual(self.q.report()['counts']['active'],1)

if __name__=='__main__': unittest.main()
