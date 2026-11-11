"""One JSON request per process. No model call, credential loading or email tool."""
import argparse
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import sqlite3
import time
import uuid

# Explicit path also works under python -I; never import the parent agent.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_snapshot.core import Store, digest, encode, match, now
from agent_snapshot.discovery import Discovery, EvidenceError
from agent_snapshot.web import WebTools
from candidates import Candidates

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = json.loads((ROOT / 'schemas.json').read_text(encoding='utf-8'))
NOTICE = '来源内容与模型分析均待核对；引用通过不等于语义正确，网页可访问不等于仍在招。'


def validate(value, schema, path='args'):
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int}
    if kind in types and type(value) is not types[kind]:
        raise ValueError(f'{path} 类型错误')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path} 不在允许值内')
    if kind == 'object':
        props = schema.get('properties', {})
        if set(schema.get('required', [])) - set(value) or (schema.get('additionalProperties') is False and set(value) - set(props)):
            raise ValueError(f'{path} 缺少字段或包含未知字段')
        for key, item in value.items():
            if key in props:
                validate(item, props[key], path + '.' + key)
    elif kind == 'array':
        if len(value) > schema.get('maxItems', 40):
            raise ValueError(f'{path} 数组过长')
        for i, item in enumerate(value):
            validate(item, schema['items'], f'{path}[{i}]')
    elif kind == 'string':
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 8000):
            raise ValueError(f'{path} 文本长度不合适')
    elif kind == 'integer':
        if not schema.get('minimum', 0) <= value <= schema.get('maximum', 1_000_000):
            raise ValueError(f'{path} 数字超出范围')


def profile(root):
    path = root / 'profile.json'
    if not path.exists():
        return {}
    if path.stat().st_size > 32000:
        raise ValueError('profile.json 过大')
    value = json.loads(path.read_text(encoding='utf-8'))
    validate_profile(value)
    return value


def validate_profile(value):
    fields = {k: {'type': 'string', 'maxLength': 4000} for k in ('stage','background','growth_goal','additional_constraints')}
    fields.update({k: {'type': 'array', 'items': {'type': 'string', 'maxLength': 500}, 'maxItems': 40}
                   for k in ('skills_known','skills_learning','cities','keywords','priorities','hard_constraints','accepted_degree_labels')})
    fields.update(days_per_week={'type':'integer','maximum':7}, months={'type':'integer','maximum':120})
    # Null availability is explicitly unknown.
    if not isinstance(value, dict):
        raise ValueError('档案必须是对象')
    clean = {k:v for k,v in value.items() if not (k in ('days_per_week','months') and v is None)}
    validate(clean, {'type':'object','properties':fields,'additionalProperties':False}, 'profile')
    if set(value.get('hard_constraints', [])) - {'days_per_week','months','city'}:
        raise ValueError('当前硬约束只支持 days_per_week / months / city；其他条件保留文字说明')


def atomic_text(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.profile-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


PROFILE_LABELS = dict(stage='学历与年级', background='学习或项目经历', growth_goal='成长目标',
    additional_constraints='其他重要条件', skills_known='已掌握的技能', skills_learning='正在学习的技能',
    cities='目标城市', keywords='岗位方向', priorities='优先条件', hard_constraints='不可妥协条件',
    accepted_degree_labels='可接受学历', days_per_week='每周可出勤天数', months='可实习月数')
PROFILE_MEANINGS = {'days_per_week': '个人每周最多可出勤天数；5 表示可以满足最低要求为 3、4、5 天的岗位，并非必须正好 5 天。只有设为硬约束且岗位最低要求超过此数时，才因出勤不足排除；要求未知则待确认。',
    'months': '个人可提供的连续实习月数，与岗位最低要求比较，不是必须正好该月数。',
    'additional_constraints': '保留必须/希望的区别；公园、健身房、交通距离等缺少可靠证据时标待确认。'}


def normalize_profile(value, fields=None):
    validate_profile(value)
    value = dict(value)
    questions = []
    cities = set('北京 上海 广州 深圳 杭州 成都 南京 武汉 西安 苏州 天津 重庆 长沙 合肥 郑州 宁波 厦门 福州 济南 青岛 珠海 东莞 佛山 无锡 大连 沈阳 昆明 南宁 海口 香港 澳门 台北'.split())
    terms = {'cities': cities | {x + '市' for x in cities},
        'skills_known': set('git python html css javascript typescript java c c++ c# go rust sql mysql redis linux react vue node.js docker kubernetes pytorch pandas numpy'.split()),
        'skills_learning': set('git python html css javascript typescript java c c++ go sql react vue agent 后端开发 前端开发 应用开发 机器学习 深度学习'.split()),
        'keywords': set('agent 后端开发 前端开发 全栈开发 应用开发 机器学习 深度学习 数据分析 产品 运营'.split()),
        'priorities': set('学习机会 住宿 薪酬 福利 远程 转正 通勤 成长 培养'.split())}
    # Preserve phrases containing meaningful spaces; never turn learning into mastery.
    phrases = {'agent 开发', 'agent development', 'machine learning', 'deep learning',
               'visual studio code', 'node js', 'react native', 'c sharp'}
    for field in ('cities', 'skills_known', 'skills_learning', 'keywords', 'priorities', 'accepted_degree_labels'):
        if field not in value or (fields is not None and field not in fields):
            continue
        items = []
        for raw in value[field]:
            for part in re.split(r'[,，、;；\n\r]+', raw):
                part = re.sub(r'\s+', ' ', part).strip()
                if not part:
                    continue
                tokens = part.split()
                if len(tokens) > 1 and part.casefold() not in phrases:
                    known = terms.get(field, set())
                    if all(token.casefold() in known for token in tokens):
                        items.extend(tokens)
                        continue
                    questions.append({'field': field, 'label': PROFILE_LABELS[field], 'original': part,
                        'question': '这里的空格表示多个条目，还是一个完整短语？当前保留整段，请核对；要拆开可用逗号或换行，或在对话中说明。'})
                items.append(part)
        value[field] = list(dict.fromkeys(items))
    validate_profile(value)
    return value, questions


def checked_profile(value):
    validate_profile(value)
    for key, field in [('city', 'cities'), ('days_per_week', 'days_per_week'), ('months', 'months')]:
        if key in value.get('hard_constraints', []) and not value.get(field):
            raise ValueError('设为不可妥协前，请先填写有效的城市、出勤天数或实习月数。')
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if len(text.encode('utf-8')) > 32000:
        raise ValueError('档案内容过长，请精简后保存。')
    return text


def profile_changes(before, after):
    return [{'field': key, 'label': PROFILE_LABELS[key], 'before': before.get(key), 'after': after.get(key),
             'removed': key not in after} for key in PROFILE_LABELS if (key in before) != (key in after) or before.get(key) != after.get(key)]


@contextmanager
def profile_lock(root):
    # One database lock shared by browser saves and all model-tool subprocesses.
    with closing(sqlite3.connect(root / 'profile-edits.sqlite3', timeout=10)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, created REAL NOT NULL, data TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        try:
            db.execute('DELETE FROM drafts WHERE created < ?', (time.time() - 86400,))
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


def save_profile(root, current, value):
    text = checked_profile(value)
    changes = profile_changes(current, value)
    if not changes:
        return {'profile': current, 'version': digest(current), 'saved': False, 'changes': [],
                'message': '档案内容未变化，无需重复写入。', 'field_meanings': PROFILE_MEANINGS}
    path = root / 'profile.json'
    if path.exists():
        atomic_text(root / 'profile.json.bak', path.read_text(encoding='utf-8'))
    atomic_text(path, text)
    actual = profile(root)
    return {'profile': actual, 'version': digest(actual), 'saved': True, 'changes': profile_changes(current, actual),
            'field_meanings': PROFILE_MEANINGS, 'undo_available': (root / 'profile.json.bak').exists(),
            'message': '已写入并重新读取本机 profile.json；请向用户展示实际变更。'}


def prepare_profile(root, db, current, value, reason, normalize_fields=None):
    value, questions = normalize_profile(value, normalize_fields)
    checked_profile(value)
    draft_id = uuid.uuid4().hex
    draft = {'draft_id': draft_id, 'base_version': digest(current), 'profile': value,
             'changes': profile_changes(current, value), 'questions': questions, 'reason': reason,
             'review_url': '/dsh-internship/profile.html?draft=' + draft_id, 'field_meanings': PROFILE_MEANINGS}
    db.execute('INSERT INTO drafts VALUES (?,?,?)', (draft_id, time.time(), encode(draft)))
    return {**draft, 'saved': False, 'confirmation_required': True,
            'instruction': '正式档案未改变。请展示 changes 与 questions，说明解释不等于字段变化；用户确认这份草稿后才能调用 internship_profile_apply。用户补充或纠正时重新生成草稿。草稿 24 小时过期。'}


def profile_web(root, request):
    """Browser and model tools share validation, locking, drafts and persistence."""
    if not isinstance(request, dict):
        raise ValueError('档案请求无效')
    with profile_lock(root) as db:
        current = profile(root)
        version = digest(current)
        action = request.get('action')
        if action == 'read':
            return {'profile': current, 'version': version, 'field_meanings': PROFILE_MEANINGS,
                    'undo_available': (root / 'profile.json.bak').exists()}
        if action in ('draft_read', 'apply'):
            draft_id = request.get('draft_id', '')
            if not isinstance(draft_id, str) or not re.fullmatch('[a-f0-9]{32}', draft_id):
                raise ValueError('草稿编号无效')
            row = db.execute('SELECT data FROM drafts WHERE id=?', (draft_id,)).fetchone()
            if not row:
                raise ValueError('草稿不存在、已过期或已使用，请重新生成。')
            draft = json.loads(row[0])
            if draft['base_version'] != version:
                return {'ok': False, 'conflict': True, 'error': '档案已被其他页面或工具修改，请重新读取并生成草稿。'}
            if action == 'draft_read':
                return {**draft, 'confirmation_required': True}
            if request.get('confirmation') != 'user_confirmed':
                raise ValueError('需要用户确认具体草稿后才能保存')
            result = save_profile(root, current, draft['profile'])
            db.execute('DELETE FROM drafts WHERE id=?', (draft_id,))
            return result
        if request.get('version') != version:
            return {'ok': False, 'conflict': True, 'error': '档案已被其他页面或程序修改，请重新载入后再保存。'}
        if action == 'restore':
            path = root / 'profile.json.bak'
            if not path.exists():
                raise ValueError('没有可恢复的上一版档案')
            previous = json.loads(path.read_text(encoding='utf-8'))
            return prepare_profile(root, db, current, previous, '恢复上一版档案', ())
        if action == 'patch':
            changes = request.get('changes', {})
            clear = request.get('clear_fields', [])
            if not isinstance(changes, dict) or not isinstance(clear, list) or set(clear) - set(PROFILE_LABELS):
                raise ValueError('只允许修改档案白名单字段')
            if set(changes) & set(clear):
                raise ValueError('同一字段不能同时修改和清空')
            validate_profile(changes)
            value = {**current, **changes}
            for key in clear:
                value.pop(key, None)
            return prepare_profile(root, db, current, value, request.get('reason', ''), set(changes))
        if action not in ('save', 'prepare'):
            raise ValueError('档案请求无效')
        value = request.get('profile')
        if action == 'prepare':
            return prepare_profile(root, db, current, value, request.get('reason', '表单修改'))
        value, questions = normalize_profile(value)
        # Older callers must not silently commit a changed interpretation.
        if value != request['profile'] or questions:
            return prepare_profile(root, db, current, value, '条目整理，请先核对')
        return save_profile(root, current, value)


class Backend:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        # Do not point this standalone adapter at the original agent's state directory.
        if self.root == (ROOT.parent / 'internship_data').resolve() or (self.root / 'mail.env').exists():
            raise ValueError('请使用独立插件数据目录，不能使用原 Agent 数据目录')
        self.store = Store(self.root)
        self.store.db.executescript('''
        CREATE TABLE IF NOT EXISTS plugin_pages (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plugin_seen (page_id TEXT NOT NULL, text TEXT NOT NULL,
          PRIMARY KEY(page_id,text));
        CREATE TABLE IF NOT EXISTS plugin_cards (job_id TEXT PRIMARY KEY, data TEXT NOT NULL);
        ''')

    def close(self):
        self.store.db.close()

    def current_profile(self):
        return profile(self.root)

    def snapshot(self, page):
        """Internal only: no model-facing tool accepts supplied page text."""
        page = {**page, 'kind': 'public_web'}
        pid = 'p_' + digest(page)[:24]
        with self.store.db:
            self.store.db.execute('INSERT OR IGNORE INTO plugin_pages VALUES (?,?)', (pid, encode(page)))
        return self.read_snapshot(pid, 0)

    def read_snapshot(self, pid, offset):
        row = self.store.db.execute('SELECT data FROM plugin_pages WHERE id=?', (pid,)).fetchone()
        if not row:
            raise ValueError('快照不存在，请先 internship_read_page')
        page = json.loads(row[0])
        if offset < 0 or offset >= len(page['text']):
            raise ValueError('offset 超出正文范围')
        text = page['text'][offset:offset+10000]
        with self.store.db:
            self.store.db.execute('INSERT OR IGNORE INTO plugin_seen VALUES (?,?)', (pid,text))
        return {**{k:v for k,v in page.items() if k != 'text'}, 'page_id':pid, 'text':text,
                'next_offset':offset+len(text) if offset+len(text)<len(page['text']) else None,
                'total_chars':len(page['text']), 'warning':NOTICE}

    def record(self, args):
        agent = Discovery(self.store, None)
        ids = {args['primary_page_id'], *(e['page_id'] for e in args['evidence'])}
        for pid in ids:
            row = self.store.db.execute('SELECT data FROM plugin_pages WHERE id=?', (pid,)).fetchone()
            if row:
                agent.pages[pid] = json.loads(row[0])
                agent.seen_text[pid] = [r[0] for r in self.store.db.execute('SELECT text FROM plugin_seen WHERE page_id=?', (pid,))]
        result = agent.record(args)
        card = next(iter(agent.records.values()))
        with self.store.db:
            self.store.db.execute('INSERT OR REPLACE INTO plugin_cards VALUES (?,?)', (result['job_id'],encode(card)))
        return {**result, 'warning':NOTICE}

    def get(self, jid):
        job = next((j for j in self.store.jobs() if j['id']==jid), None)
        if not job:
            raise ValueError('岗位不存在')
        row = self.store.db.execute('SELECT data FROM plugin_cards WHERE job_id=?', (jid,)).fetchone()
        card = json.loads(row[0]) if row else None
        # Only unambiguous minimum wording in primary-page quotes enters hard filtering.
        # More complex/negated/negotiable requirements remain for the model and user.
        supported = []
        if card:
            for e in card['evidence']:
                if e['source_url'] != card['source_url']:
                    continue
                quote=e['quote']
                context = '\n'.join(line for line in job['description'].splitlines() if quote in line) or job['description']
                if re.search(r'不(?!少于)|非|优先|最好|建议|可协商|或|\d\s*到\s*\d|[-~～]|\d至\d', context):
                    continue
                for dimension, field, pattern, maximum in (
                    ('attendance','min_days',r'每周(?:可|能)?(?:到岗|工作|实习|出勤)?\s*(?:至少|最少|不少于)?\s*([1-7])\s*天',7),
                    ('period','min_months',r'(?:至少|最少|不少于)\s*(?:实习)?\s*(\d{1,2})\s*个月',120)):
                    values=re.findall(pattern,quote)
                    if e['dimension']==dimension and len(values)==1 and int(values[0])<=maximum:
                        supported.append({'field':field,'value':int(values[0]),'quote':quote})
        for field in ('min_days','min_months'):
            values={x['value'] for x in supported if x['field']==field}
            if len(values)==1:
                job[field]=values.pop()
        p=profile(self.root)
        job=dict(job)
        if not job.get('city') and p.get('cities'):
            for line in job['description'].splitlines()[:40]:
                text=line.strip()
                if 0 < len(text) <= 24 and any(c and c in text for c in p['cities']):
                    job['city']=text
                    break
        m=match(job,p)
        if job.get('city') and p.get('cities') and not any(c.casefold() in job['city'].casefold() for c in p['cities']):
            if 'city' in p.get('hard_constraints', []):
                m['rejected'].append('城市不符：岗位地点为 ' + job['city'])
                m['unknown']=[u for u in m['unknown'] if not u.startswith('地点')]
                m['status']='excluded'
        return {'job':job, 'card':card, 'profile':p, 'profile_version':digest(p),
                'match':m, 'parsed_requirements':supported,
                'listing_status':'unknown', 'warning':NOTICE,
                'review_guide': {
                    'sections': ['实际工作与经历联系', '时间地点和到岗冲突', '必需/优先技术与准备方向', '未知项与要问招聘方的问题', '下一步行动'],
                    'instruction': '每项分别写原文事实（带引用）、结合档案的分析、未知项。当前档案可能已不同于保存证据卡时；重新核对，不把旧analysis直接当当前结论。days_per_week 是可出勤上限，5 可以满足至少3、4或5天的出勤条件，不能解释成必须正好5天；按实际最低要求比较。技术关键词未命中不能单独淘汰。对 additional_constraints 补充条件区分必须和希望；周边公园、健身房、交通和距离等缺乏可靠证据时标待确认，不得猜测，也不进入规则硬过滤。'
                },
                'limits':'规则仅核对明确的最低出勤/时长，并按正文中的城市线索做硬约束（需人工核对）；复杂表述、远程、年级、待遇由模型结合原文分析。score只是关键词命中数。'}

    def execute(self, tool, args):
        if tool not in SCHEMAS:
            raise ValueError('未知工具')
        validate(args, SCHEMAS[tool])
        if tool.startswith('internship_candidates_'):
            candidates = Candidates(self)
            action = tool.removeprefix('internship_candidates_')
            if action == 'plan':
                return candidates.plan(**args)
            if action == 'add':
                return candidates.add(**args)
            if action == 'check':
                return candidates.check(args['candidate_id'], WebTools())
            if action == 'report':
                return candidates.report()
            if action == 'view':
                return candidates.view()
            if action == 'recheck':
                return candidates.recheck(args.get('limit', 10))
        if tool=='internship_status':
            return {'jobs':len(self.store.jobs()), 'pages':self.store.db.execute('SELECT COUNT(*) FROM plugin_pages').fetchone()[0],
                    'profile_configured':(self.root/'profile.json').exists(), 'listing_status':'unknown', 'warning':NOTICE}
        if tool=='internship_profile':
            p=profile(self.root)
            return {'profile':p,'version':digest(p),'configured':bool(p),
                    'profile_form_url': '/dsh-internship/profile.html',
                    'field_meanings': PROFILE_MEANINGS,
                    'update_tools': ['internship_profile_propose', 'internship_profile_apply'],
                    'missing_fields': [label for field, label in [('stage', '学历与年级'), ('skills_known', '已掌握的技能'),
                        ('cities', '目标城市'), ('keywords', '岗位方向'), ('days_per_week', '每周出勤天数'),
                        ('months', '实习月数'), ('priorities', '求职偏好')] if not p.get(field)],
                    'instruction':'用户提出建档时请展示[填写个人档案](/dsh-internship/profile.html)。用户希望你补充或修改时，调用 internship_profile_propose 提交最小字段变更并展示差异与疑问；用户确认该草稿后用 internship_profile_apply 保存，再展示重新读取的实际结果。不要用 Shell 编辑文件，不要声称只有表单可写。additional_constraints 区分必须和希望，周边设施没有证据时记待确认。每周 5 天是可出勤上限，不是必须正好 5 天；解释纠正不一定需要改数值。'}
        if tool=='internship_profile_propose':
            if args.get('restore_previous', 'no') == 'yes':
                if args.get('changes') or args.get('clear_fields'):
                    raise ValueError('恢复上一版不能同时修改其他字段')
                return profile_web(self.root, {'action': 'restore', 'version': args['base_version']})
            return profile_web(self.root, {'action': 'patch', 'version': args['base_version'],
                'changes': args.get('changes', {}), 'clear_fields': args.get('clear_fields', []), 'reason': args['reason']})
        if tool=='internship_profile_apply':
            return profile_web(self.root, {'action': 'apply', 'draft_id': args['draft_id'], 'confirmation': args['confirmation']})
        if tool=='internship_read_page':
            return self.snapshot(WebTools().read(args['url']))
        if tool=='internship_read_snapshot':
            return self.read_snapshot(args['page_id'],args['offset'])
        if tool=='internship_record':
            return self.record(args)
        if tool=='internship_get':
            return self.get(args['job_id'])
        if tool=='internship_list':
            jobs=self.store.jobs(); start=args['offset']; items=[]
            for j in jobs[start:start+20]:
                detail=self.get(j['id'])
                items.append({k:j[k] for k in ('id','title','company','url','last_seen')} | {'match':detail['match']})
            return {'jobs':items, 'total':len(jobs), 'next_offset':start+20 if start+20<len(jobs) else None, 'warning':NOTICE}


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--init-profile', action='store_true', help='Create an empty manual profile; never overwrite')
    parser.add_argument('--profile-web', action='store_true', help='Local profile form API, not a model tool')
    parser.add_argument('--resume-web', action='store_true', help='Local resume import, no automatic profile save')
    opt=parser.parse_args()
    try:
        with closing(Backend(opt.data_dir)) as backend:
            if opt.init_profile:
                with (backend.root/'profile.json').open('x',encoding='utf-8') as f:
                    json.dump({'stage':'','skills_known':[],'skills_learning':[], 'cities':[], 'days_per_week':None,
                               'months':None,'hard_constraints':[],'priorities':[]}, f,ensure_ascii=False,indent=2)
                result={'ok':True,'created':'profile.json'}
            else:
                limit = 6_000_000 if opt.resume_web else 200000
                raw=sys.stdin.buffer.read(limit + 1)
                if len(raw)>limit:
                    raise ValueError('请求过大')
                request=json.loads(raw)
                if opt.resume_web:
                    from resume import import_resume
                    result = {'ok': True, **import_resume(request)}
                elif opt.profile_web:
                    result = {'ok': True, **profile_web(backend.root, request)}
                elif not isinstance(request,dict) or set(request)!={'tool','args'}:
                    raise ValueError('请求必须包含 tool 和 args')
                else:
                    result={'ok':True, **backend.execute(request['tool'],request['args'])}
    except EvidenceError as error:
        result={'ok':False,'error':str(error),'evidence_errors':error.errors}
    except ValueError as error:
        result={'ok':False,'error':str(error)}
    except Exception as error:
        result={'ok':False,'error':type(error).__name__,'instruction':'检查 Python >=3.10、数据目录权限或网络；不输出敏感配置。'}
    print(encode(result))


if __name__=='__main__':
    main()
