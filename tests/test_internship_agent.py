import json
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import plistlib
import io
from unittest.mock import patch

from internship_agent.core import Store, normalize, match, sync, collect
from internship_agent import mail
from internship_agent.evaluate import metrics
from internship_agent.research import research


CFG = {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "465", "SMTP_USER": "me@example.com",
       "SMTP_PASSWORD": "fake-test-password", "SMTP_FROM": "me@example.com",
       "SMTP_SECURITY": "ssl", "DAILY_TO": "me@example.com"}
JOB = {"title": "Agent 实习", "company": "示例", "url": "https://example.com/job/1",
       "description": "Python Agent 工具开发，每周至少3天。", "min_days": 3, "min_months": 3,
       "city": "上海", "degree": "本科在读"}


class TestInternship(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root)
        self.store.ingest([JOB], "test")
        self.job = self.store.jobs()[0]
        self.pdf = self.root / "cv.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nTEST ONLY")
        self.cfg = patch("internship_agent.mail.config", return_value=dict(CFG))
        self.cfg.start()

    def tearDown(self):
        self.cfg.stop()
        self.store.db.close()
        self.temp.cleanup()

    def draft(self):
        return mail.create(self.store, "application", "hr@example.com", "申请", "真实正文",
                           attachment=self.pdf, job={"id": self.job["id"]})

    def test_dedup_and_changed_content(self):
        result = self.store.ingest([JOB], "test")
        self.assertEqual(result, {"read": 1, "new": 0, "updated": 0})
        self.assertEqual(self.store.ingest([{**JOB, "description": "更新正文"}], "test")["updated"], 1)
        self.assertEqual(len(self.store.jobs()), 1)

    def test_invalid_batch_is_atomic(self):
        with self.assertRaises(ValueError):
            self.store.ingest([{**JOB, "url": "https://example.com/2"}, {"title": "bad"}], "test")
        self.assertEqual(len(self.store.jobs()), 1)

    def test_missing_conditions_not_passed(self):
        result = match(self.job, {"keywords": ["Agent"]})
        self.assertEqual(result["status"], "review")
        self.assertTrue(result["unknown"])

    def test_hard_constraints_and_deadline(self):
        result = match(self.job, {"days_per_week": 2, "months": 6})
        self.assertEqual(result["status"], "excluded")
        self.assertEqual(match({**self.job, "deadline": "2000-01-01"}, {})["status"], "excluded")

    def test_source_failure_not_empty_success(self):
        result = sync(self.store, [{"name": "missing", "type": "json", "path": str(self.root / "missing.json")}])
        self.assertFalse(result[0]["ok"])
        self.assertEqual(len(self.store.jobs()), 1)

    def test_greenhouse_filters_internship_titles(self):
        payload = {"jobs": [{"title": "Software Engineer Intern", "absolute_url": JOB["url"],
                              "content": "&lt;p&gt;Python internship&lt;/p&gt;", "location": {"name": "上海"}},
                             {"title": "Senior Engineer"}]}
        with patch("internship_agent.core.request_json", return_value=payload):
            rows = collect({"type": "greenhouse", "board": "example"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(normalize(rows[0], "test")["description"], "Python internship")

    def test_rss_and_atom(self):
        samples = [b'<rss><channel><item><title>Internship</title><link>https://example.com/job</link><description>Python</description></item></channel></rss>',
                   b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Intern</title><link href="https://example.com/job"/><summary>Python</summary></entry></feed>']
        for raw in samples:
            with patch("internship_agent.core.build_opener") as opener:
                opener.return_value.open.return_value = io.BytesIO(raw)
                rows = collect({"type": "rss", "url": "https://example.com/feed"})
            self.assertEqual(rows[0]["description"], "Python")
            self.assertEqual(rows[0]["url"], "https://example.com/job")

    def test_cli_draft_review_and_noninteractive_send(self):
        target = self.root / "cli"
        def run(*args):
            return subprocess.run([sys.executable, "-m", "internship_agent", "--data-dir", str(target), *args],
                                  input="", capture_output=True, text=True, env={**os.environ, **CFG})
        self.assertEqual(run("init").returncode, 0)
        config_path = target / "profile.json"
        blank = json.loads(config_path.read_text())
        self.assertEqual(blank["background"], "")
        blank["background"] = "用户自行填写的档案"
        config_path.write_text(json.dumps(blank))
        self.assertEqual(run("init").returncode, 0)
        self.assertEqual(json.loads(config_path.read_text())["background"], "用户自行填写的档案")
        jobfile = target / "jobs.json"
        jobfile.write_text(json.dumps([JOB]))
        self.assertEqual(run("import", str(jobfile)).returncode, 0)
        self.assertEqual(run("report").returncode, 0)
        result = run("draft", self.job["id"], "--to", "hr@example.com", "--resume", str(self.pdf))
        self.assertEqual(result.returncode, 0, result.stderr)
        other = Store(target)
        mid = other.db.execute("SELECT id FROM mail").fetchone()[0]
        self.assertEqual(run("review", mid).returncode, 0)
        blocked = run("send", mid)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("交互终端", blocked.stderr)
        self.assertEqual(mail.get(other, mid)[0]["state"], "draft")
        self.assertEqual(run("schedule-template", "--send").returncode, 0)
        data = plistlib.loads((target / "local.internship-radar.daily.plist").read_bytes())
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 8, "Minute": 30})
        self.assertEqual(data["ProgramArguments"][-2:], ["daily", "--send"])
        self.assertEqual(run("schedule-template").returncode, 1)
        other.db.close()

    def test_reject_header_injection(self):
        with self.assertRaises(ValueError):
            mail.create(self.store, "digest", "a@example.com\nBcc: b@example.com", "s", "b")
        with self.assertRaises(ValueError):
            mail.create(self.store, "digest", "a@example.com", "s\nBcc: b@example.com", "b")

    def test_attachment_is_snapshot(self):
        mid = self.draft()
        before = mail.get(self.store, mid)[0]["attachment"]
        self.pdf.write_bytes(b"%PDF-1.4\nCHANGED")
        self.assertEqual(mail.get(self.store, mid)[0]["attachment"], before)
        self.assertEqual((mail.export(self.store, mid) / "resume.pdf").read_bytes(), before)

    def test_no_approval_no_send(self):
        mid = self.draft()
        sent = []
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, transport=lambda *a: sent.append(a))
        self.assertEqual(sent, [])
        self.assertEqual(mail.get(self.store, mid)[0]["state"], "draft")

    def test_edit_invalidates_approval_and_duplicate_send(self):
        mid = self.draft()
        old = mail.fingerprint(mail.get(self.store, mid)[1])
        mail.revise(self.store, mid, {"body": "新的正文"})
        sent = []
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, approval=old, transport=lambda *a: sent.append(a))
        token = mail.fingerprint(mail.get(self.store, mid)[1])
        mail.send(self.store, mid, approval=token, transport=lambda *a: sent.append(a))
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, approval=token, transport=lambda *a: sent.append(a))
        self.assertEqual(len(sent), 1)

    def test_daily_path_cannot_send_application(self):
        mid = self.draft()
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, daily=True, transport=lambda *a: self.fail("sent"))

    def test_uncertain_send_is_not_retried(self):
        mid = self.draft()
        token = mail.fingerprint(mail.get(self.store, mid)[1])
        def failure(*args):
            raise TimeoutError("server may have accepted")
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, approval=token, transport=failure)
        self.assertEqual(mail.get(self.store, mid)[0]["state"], "uncertain")
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, approval=token, transport=lambda *a: self.fail("retried"))
        mail.reconcile(self.store, mid, "not-sent")
        self.assertEqual(mail.get(self.store, mid)[0]["state"], "cancelled")

    def test_daily_delivery_records_only_after_success(self):
        mid = mail.create(self.store, "digest", CFG["DAILY_TO"], "日报", "正文", versions={"j": "v"})
        self.assertEqual(list(self.store.db.execute("SELECT * FROM delivered")), [])
        mail.send(self.store, mid, daily=True, transport=lambda *a: None)
        self.assertEqual(len(list(self.store.db.execute("SELECT * FROM delivered"))), 1)
        duplicate = mail.create(self.store, "digest", CFG["DAILY_TO"], "日报", "正文", versions={"j": "v"})
        with self.assertRaises(ValueError):
            mail.send(self.store, duplicate, daily=True, transport=lambda *a: self.fail("duplicate"))

    def test_uncertain_digest_blocks_new_send(self):
        mid = mail.create(self.store, "digest", CFG["DAILY_TO"], "日报", "正文", versions={"j": "v"})
        def failure(*args):
            raise TimeoutError()
        with self.assertRaises(ValueError):
            mail.send(self.store, mid, daily=True, transport=failure)
        second = mail.create(self.store, "digest", CFG["DAILY_TO"], "日报", "正文", versions={"j": "v2"})
        with self.assertRaises(ValueError):
            mail.send(self.store, second, daily=True, transport=lambda *a: self.fail("duplicate"))

    def test_metrics_no_unlabelled_or_duplicate_predictions(self):
        self.assertEqual(metrics(["a"], {"a": 2})["precision_at_5"], 0.2)
        self.assertEqual(metrics(["a"], {"a": 2})["ndcg_at_10"], 1)
        with self.assertRaises(ValueError):
            metrics(["missing"], {"a": 1})
        with self.assertRaises(ValueError):
            metrics(["a", "a"], {"a": 1})

    def test_fixed_assessment_repairs_quotes_without_search_or_send(self):
        from internship_agent.research import DIMENSIONS
        job = self.job
        class Client:
            count = 0
            def complete(self, messages, tools, **kwargs):
                assert {t["function"]["name"] for t in tools} == {"submit_assessments"}
                self.count += 1
                if self.count == 2:
                    feedback = [m for m in messages if m["role"] == "tool"]
                    assert len(feedback) == 1
                    assert "work" in feedback[0]["content"]
                    assert any(m["role"] == "assistant" for m in messages)
                dims = {k: {"fact": "", "quote": "", "interpretation": "需询问招聘方"} for k in DIMENSIONS}
                dims["work"] = {"fact": "Python工具开发", "quote": "伪造引用" if self.count == 1 else "Python Agent 工具开发", "interpretation": "可探索工具开发"}
                args = {"cards": [{"id": job["id"], "dimensions": dims, "questions": ["能否寒假实习？"], "next_step": "先确认到岗时间"}]}
                return {"message": {"role": "assistant", "tool_calls": [{"id": str(self.count), "type": "function",
                    "function": {"name": "submit_assessments", "arguments": json.dumps(args)}}]}}
        result = research(self.store, {"keywords": ["完全不同的技术"], "days_per_week": 1}, Client())
        self.assertEqual(result["steps"], 2)
        self.assertFalse(result["trace"][0]["ok"])
        self.assertEqual(result["cards"][0]["dimensions"]["work"]["quote"], "Python Agent 工具开发")
        self.assertTrue(result["cards"][0]["hard_conflicts"])
        self.assertEqual(result["cards"][0]["source_url"], job["url"])
        from internship_agent.research import render_cards
        rendered = render_cards(result["cards"], ["remote", "period"])
        self.assertLess(rendered.index("远程与地点限制"), rendered.index("实际工作"))
        self.assertIn("未知", rendered)
        self.assertIn("模型分析（待核对）", rendered)
        diagnostic = self.store.db.execute("SELECT data FROM events WHERE kind='assessment_validation_error'").fetchone()
        self.assertIn("work", json.loads(diagnostic[0])["error"])

    def test_soft_constraints_do_not_exclude(self):
        result = match(self.job, {"cities": ["杭州"], "days_per_week": 1, "hard_constraints": [], "keywords": ["Java"]})
        self.assertEqual(result["status"], "review")
        self.assertEqual(result["rejected"], [])

    def test_unsubstantiated_benefit_and_missing_card_rejected(self):
        from internship_agent.research import validate, DIMENSIONS
        dims = {k: {"fact": "", "quote": "", "interpretation": "待核对"} for k in DIMENSIONS}
        card = {"id": self.job["id"], "dimensions": dims, "questions": [], "next_step": "核对"}
        validate([card], [self.job])
        dims["benefits"]["fact"] = "五险一金双休"
        with self.assertRaises(ValueError):
            validate([card], [self.job])
        with self.assertRaises(ValueError):
            validate([], [self.job])

    def test_assessment_budget_and_unknown_job(self):
        with self.assertRaises(ValueError):
            research(self.store, {}, None, max_steps=0)
        with self.assertRaises(ValueError):
            research(self.store, {}, None, job_id="not-found")


if __name__ == "__main__":
    unittest.main()
