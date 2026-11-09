"""One JSON request per process. No model call, credential loading or email tool."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

# Explicit path also works under python -I; never import the parent agent.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_snapshot.core import Store, digest, encode, match, now
from agent_snapshot.discovery import Discovery, EvidenceError
from agent_snapshot.web import WebTools
from candidates import Candidates

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = json.loads((ROOT / 'schemas.json').read_text())
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
    fields = {k: {'type': 'string', 'maxLength': 4000} for k in ('stage','background','growth_goal')}
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
                'limits':'规则仅核对明确的最低出勤/时长，并按正文中的城市线索做硬约束（需人工核对）；复杂表述、远程、年级、待遇由模型结合原文分析。score只是关键词命中数。'}

    def execute(self, tool, args):
        if tool not in SCHEMAS:
            raise ValueError('未知工具')
        validate(args, SCHEMAS[tool])
        if tool.startswith('internship_candidates_'):
            candidates = Candidates(self)
            action = tool.removeprefix('internship_candidates_')
            if action == 'plan':
                return candidates.plan()
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
                    'instruction':'用户在本插件数据目录手动编辑 profile.json 后生效。未知条件先问；不得自行认定为硬约束。'}
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
    opt=parser.parse_args()
    try:
        with closing(Backend(opt.data_dir)) as backend:
            if opt.init_profile:
                with (backend.root/'profile.json').open('x',encoding='utf-8') as f:
                    json.dump({'stage':'','skills_known':[],'skills_learning':[], 'cities':[], 'days_per_week':None,
                               'months':None,'hard_constraints':[],'priorities':[]}, f,ensure_ascii=False,indent=2)
                result={'ok':True,'created':'profile.json'}
            else:
                raw=sys.stdin.buffer.read(200001)
                if len(raw)>200000:
                    raise ValueError('请求过大')
                request=json.loads(raw)
                if not isinstance(request,dict) or set(request)!={'tool','args'}:
                    raise ValueError('请求必须包含 tool 和 args')
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
