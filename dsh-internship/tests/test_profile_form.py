import base64
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from bridge import Backend, normalize_profile, profile, profile_web
from agent_snapshot.core import match
from resume import import_resume


class ProfileFormTests(unittest.TestCase):
    def test_space_lists_preserve_phrases_and_ask_ambiguities(self):
        value, questions = normalize_profile({'cities':['广州 深圳 杭州'], 'skills_known':['Git Python HTML', 'Machine Learning'],
            'skills_learning':['Agent 开发', '新工具 多模态应用'], 'priorities':['学习机会;住宿'],
            'additional_constraints':'希望附近有公园 健身房'})
        self.assertEqual(value['cities'], ['广州','深圳','杭州'])
        self.assertEqual(value['skills_known'], ['Git','Python','HTML','Machine Learning'])
        self.assertEqual(value['skills_learning'], ['Agent 开发','新工具 多模态应用'])
        self.assertEqual(value['priorities'], ['学习机会','住宿'])
        self.assertEqual(value['additional_constraints'], '希望附近有公园 健身房')
        self.assertEqual([q['original'] for q in questions], ['新工具 多模态应用'])

    def test_model_drafts_confirmation_roundtrip_noop_and_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = Backend(directory)
            try:
                original = {'stage':'本科大二','skills_learning':['Agent 开发'], 'cities':['广州'],
                            'days_per_week':5, 'hard_constraints':['days_per_week']}
                profile_web(backend.root, {'action':'save','profile':original,'version':profile_web(backend.root,{'action':'read'})['version']})
                current = backend.execute('internship_profile', {})
                prepared = backend.execute('internship_profile_propose', {'base_version':current['version'],
                    'changes':{'cities':['广州 深圳'], 'additional_constraints':'希望靠近公园'},'reason':'用户要求增加城市和偏好'})
                self.assertEqual(profile(backend.root), original)
                self.assertEqual({c['field'] for c in prepared['changes']}, {'cities','additional_constraints'})
                self.assertEqual(prepared['profile']['skills_learning'], ['Agent 开发'])
                with self.assertRaises(ValueError):
                    backend.execute('internship_profile_apply', {'draft_id':prepared['draft_id'],'confirmation':'not_confirmed'})
                applied = backend.execute('internship_profile_apply', {'draft_id':prepared['draft_id'],'confirmation':'user_confirmed'})
                self.assertTrue(applied['saved'])
                self.assertEqual(profile(backend.root)['cities'], ['广州','深圳'])
                self.assertEqual(applied['profile'], profile(backend.root))
                with self.assertRaises(ValueError):
                    backend.execute('internship_profile_apply', {'draft_id':prepared['draft_id'],'confirmation':'user_confirmed'})
                noop = backend.execute('internship_profile_propose', {'base_version':applied['version'],
                    'changes':{'days_per_week':5},'reason':'澄清最多可出勤5天，不改数值'})
                self.assertEqual(noop['changes'], [])
                unchanged = backend.execute('internship_profile_apply', {'draft_id':noop['draft_id'],'confirmation':'user_confirmed'})
                self.assertFalse(unchanged['saved'])
                restore = backend.execute('internship_profile_propose', {'base_version':unchanged['version'],
                    'restore_previous':'yes','reason':'用户要撤销上一轮修改'})
                restored = backend.execute('internship_profile_apply', {'draft_id':restore['draft_id'],'confirmation':'user_confirmed'})
                self.assertEqual(restored['profile'], original)
            finally:
                backend.close()

    def test_stale_draft_and_form_normalization_never_write_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = profile_web(root, {'action':'read'})
            draft = profile_web(root, {'action':'save','profile':{'cities':['广州 深圳']},'version':first['version']})
            self.assertTrue(draft['confirmation_required'])
            self.assertEqual(profile(root), {})
            other = profile_web(root, {'action':'save','profile':{'stage':'大三'},'version':first['version']})
            stale = profile_web(root, {'action':'apply','draft_id':draft['draft_id'],'confirmation':'user_confirmed'})
            self.assertTrue(stale['conflict'])
            self.assertEqual(profile(root), other['profile'])
            invalid = {'action':'prepare','version':other['version'],'profile':{'hard_constraints':['city'],'cities':[]}}
            with self.assertRaises(ValueError):
                profile_web(root, invalid)

    def test_five_days_is_availability_ceiling_not_exact_equality(self):
        p = {'days_per_week':5,'hard_constraints':['days_per_week']}
        for days in (3,4,5,6,7):
            job = {'id':'test','city':'','min_days':days,'min_months':None,'degree':'','deadline':'', 'title':'开发实习','description':'测试'}
            result = match(job,p)
            self.assertEqual(result['status'] == 'excluded', days > 5)

    def test_save_backup_conflict_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = profile_web(root, {'action': 'read'})
            value = {'stage': '本科大二', 'skills_known': ['Python'], 'days_per_week': None,
                     'accepted_degree_labels': ['本科'], 'hard_constraints': [],
                     'additional_constraints': '必须靠近地铁；希望附近有公园、健身房'}
            result = profile_web(root, {'action': 'save', 'profile': value, 'version': first['version']})
            self.assertEqual(profile(root), value)
            self.assertTrue(result['saved'])
            conflict = profile_web(root, {'action': 'save', 'profile': {}, 'version': first['version']})
            self.assertTrue(conflict['conflict'])
            for invalid in [{'days_per_week': 8}, {'hard_constraints': ['city'], 'cities': []}, {'invented': True}]:
                with self.assertRaises(ValueError):
                    profile_web(root, {'action': 'save', 'profile': invalid, 'version': result['version']})
                self.assertEqual(profile(root), value)
            profile_web(root, {'action': 'save', 'profile': {**value, 'days_per_week': 2}, 'version': result['version']})
            self.assertEqual(json.loads((root / 'profile.json.bak').read_text(encoding='utf-8')), value)
            self.assertFalse(list(root.glob('.profile-*.tmp')))

    def test_resume_txt_suggestions_do_not_invent_constraints(self):
        text = '学历：本科大二\n已掌握技能：Python、Git\n正在学习：Agent 开发\n意向城市：广州\n每周可出勤：2天\n可连续实习：3个月\n电话：12345678901'
        result = import_resume({'name': '虚拟简历.txt', 'data': base64.b64encode(text.encode()).decode()})
        self.assertEqual(result['suggestions']['skills_known'], ['Python', 'Git'])
        self.assertEqual(result['suggestions']['skills_learning'], ['Agent 开发'])
        self.assertEqual(result['suggestions']['days_per_week'], 2)
        self.assertNotIn('hard_constraints', result['suggestions'])
        self.assertNotIn('phone', result['suggestions'])
        unlabeled = import_resume({'name': 'resume.txt', 'data': base64.b64encode('在广州读书，目前正在学习 Python 开发。'.encode()).decode()})
        self.assertEqual(unlabeled['suggestions'], {})

    def test_resume_docx_and_invalid_documents(self):
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>学历：本科大二学生（虚拟）</w:t></w:r></w:p></w:body></w:document>')
        result = import_resume({'name': 'resume.docx', 'data': base64.b64encode(buffer.getvalue()).decode()})
        self.assertEqual(result['suggestions']['stage'], '本科大二学生（虚拟）')
        for request in [{'name': 'x.png', 'data': base64.b64encode(b'fake image').decode()},
                        {'name': 'x.txt', 'data': 'not-base64'},
                        {'name': 'x.docx', 'data': base64.b64encode(b'bad zip').decode()}]:
            with self.assertRaises(ValueError):
                import_resume(request)

    def test_text_pdf_if_optional_dependency_installed(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.runtime' / 'python'))
        try:
            from pypdf import PdfWriter
            from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        except ImportError:
            self.skipTest('optional pypdf is not installed')
        writer = PdfWriter()
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 50 700 Td (Synthetic resume: undergraduate student.) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = BytesIO()
        writer.write(output)
        result = import_resume({'name': 'synthetic.pdf', 'data': base64.b64encode(output.getvalue()).decode()})
        self.assertIn('undergraduate student', result['text'])
        self.assertEqual(result['suggestions'], {})


if __name__ == '__main__':
    unittest.main()
