import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from bridge import Backend
from candidates import Candidates, QUERIES, canonical, allowed, screen

URL = 'https://www.nowcoder.com/jobs/123'
PAGE = {'url': URL, 'title': 'Python实习生', 'text': 'Python开发实习生\n工作地点：广州\n学历：本科及以上\n参与接口开发和测试工作，具体实习周期面议。',
        'fetched_at': '2026-11-09T00:00:00+00:00', 'links': [], 'truncated': False}

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = Backend(self.tmp.name)
        self.queue = Candidates(self.backend)

    def tearDown(self):
        self.backend.close()
        self.tmp.cleanup()

    def test_url_dedup_retains_job_ids_and_rejects_spoof_domains(self):
        self.assertEqual(canonical(URL+'?utm_source=x&id=2#hello'), URL+'?id=2')
        self.assertNotEqual(canonical(URL+'?id=2'), canonical(URL+'?id=3'))
        self.assertFalse(allowed('https://nowcoder.com.evil.example/jobs/123'))
        result = self.queue.add(QUERIES[0], [URL, URL+'?utm_source=x', 'https://127.0.0.1/'])
        self.assertEqual(len(result['added']), 1)
        self.assertEqual(len(result['duplicates']), 1)
        self.assertEqual(len(result['search']['rejected']), 1)
        self.assertEqual(self.backend.store.jobs(), [])

    def test_missing_conditions_and_company_address_are_not_rejected(self):
        r = screen({**PAGE, 'text': '广州公司地址\nPython开发实习生\n学历未注明'})
        self.assertEqual(r['screening'], 'needs_review')
        self.assertNotIn('city', r['evidence'])
        self.assertNotIn('degree', r['evidence'])
        self.assertNotIn('degree', screen({**PAGE, 'text': '网友评论：本科上岸，目前写Python'})['evidence'])

    def test_fetch_snapshot_failure_and_report_survive_reopen(self):
        ids = self.queue.add(QUERIES[0], [URL, URL+'?id=2'])['added']
        web = Mock()
        web.read.side_effect = [PAGE, ValueError('需要登录')]
        first = self.queue.check(ids[0], web)
        self.assertEqual(first['screening'], 'signals_complete')
        snap = self.backend.read_snapshot(first['page_id'], 0)
        self.assertTrue(all(q in snap['text'] for q in first['evidence'].values()))
        self.assertEqual(self.queue.check(ids[1], web)['screening'], 'read_failed')
        self.queue.check(ids[0], web)
        self.assertEqual(web.read.call_count, 2)
        self.backend.close()
        self.backend = Backend(self.tmp.name)
        self.queue = Candidates(self.backend)
        result = self.queue.report()
        self.assertEqual(result['counts']['read_failed'], 1)
        self.assertEqual(result['counts']['signals_complete'], 1)
        self.assertTrue((Path(self.tmp.name)/'candidates.json').exists())
        self.assertEqual(self.backend.store.jobs(), [])

    def test_identical_content_not_double_counted(self):
        ids = self.queue.add(QUERIES[0], [URL, URL+'?id=2'])['added']
        web = Mock()
        web.read.side_effect = [PAGE, {**PAGE, 'url': URL+'?id=2'}]
        for cid in ids:
            self.queue.check(cid, web)
        self.assertEqual(self.queue.report()['counts']['signals_complete'], 1)
        self.assertEqual(self.queue.report()['counts']['duplicate'], 1)

    def test_expired_or_delisted_page_never_counts_as_complete(self):
        closed = {**PAGE, 'text': 'AI Agent 实习\n广州\n本科及以上\n职位已下线\n投递时间：2026年1月1日-2026年3月1日'}
        self.assertEqual(screen(closed)['screening'], 'expired')
        past = {**PAGE, 'text': 'AI Agent 实习\n广州\n本科及以上\n截止日期：2025年12月31日'}
        self.assertEqual(screen(past)['screening'], 'expired')
        live = {**PAGE, 'text': 'AI Agent 实习\n广州\n本科及以上\n截止日期：2099年12月31日'}
        self.assertEqual(screen(live)['screening'], 'signals_complete')
        stale = {**PAGE, 'text': 'AI Agent 实习\n广州\n本科及以上\n2020-01-01 更新'}
        self.assertEqual(screen(stale)['screening'], 'needs_review')

    def test_recheck_flips_closed_page_and_marks_active(self):
        ids = self.queue.add(QUERIES[0], [URL, URL + '?id=2'])['added']
        web = Mock()
        second = {**PAGE, 'url': URL + '?id=2', 'text': PAGE['text'] + ' 补充说明'}
        web.read.side_effect = [PAGE, second]
        for cid in ids:
            self.queue.check(cid, web)
        closed = {**PAGE, 'url': URL + '?id=2', 'text': 'AI Agent 实习\n广州\n本科及以上\n职位已下线'}
        web.read.side_effect = [PAGE, closed]
        summary = self.queue.recheck(limit=2, web=web)
        self.assertEqual(summary['checked'], 2)
        self.assertEqual(summary['active'], 1)
        rows = {r['id']: r for r in self.queue.rows()}
        self.assertEqual(rows[ids[1]]['screening'], 'expired')
        self.assertIsNotNone(rows[ids[0]]['rechecked_at'])

    def test_report_writes_html_dashboard_and_view_regenerates(self):
        ids = self.queue.add(QUERIES[0], [URL])['added']
        web = Mock()
        web.read.return_value = PAGE
        self.queue.check(ids[0], web)
        result = self.queue.report()
        self.assertTrue(result['html'].endswith('candidates.html'))
        html = (Path(self.tmp.name) / 'candidates.html').read_text(encoding='utf-8')
        self.assertIn('广州实习候选看板', html)
        self.assertIn('信号齐全', html)
        view = self.queue.view()
        self.assertTrue(view['ok'])
        self.assertEqual(view['counts']['signals_complete'], 1)

    def test_zero_results_and_search_errors_are_distinct(self):
        self.queue.add(QUERIES[0], [])
        self.queue.add(QUERIES[1], [], 'NetworkError')
        report = self.queue.report()
        self.assertEqual([r['error'] for r in report['searches']], ['', 'NetworkError'])
        with self.assertRaises(ValueError):
            self.queue.add('invented query', [])

if __name__ == '__main__':
    unittest.main()
