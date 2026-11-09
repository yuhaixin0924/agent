"""Deterministic discovery queue. Search snippets never become evidence."""
import json
import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from agent_snapshot.core import digest, encode, now
from agent_snapshot.web import WebTools, public_url

DOMAINS = ('career.gdut.edu.cn', 'nowcoder.com', 'v2ex.com', 'jobs.bytedance.com',
           'careers.tencent.com', 'talent.baidu.com', 'recruit.netease.com',
           'scdc.jnu.edu.cn', 'ncss.cn', 'smartedu.cn', 'shixiseng.com')
MIRRORS = {'global.v2ex.co': 'www.v2ex.com', 'tanronggui.xyz': 'www.v2ex.com'}
SOURCE_ORDER = {'www.nowcoder.com': 0, 'nowcoder.com': 0, 'scdc.jnu.edu.cn': 1,
                'ncss.cn': 1, 'smartedu.cn': 1, 'career.gdut.edu.cn': 2,
                'careers.tencent.com': 3, 'jobs.bytedance.com': 4}
QUERIES = (
    '广州 实习 Agent', '广州 Python 后端 实习',
    'site:career.gdut.edu.cn 广州 技术 实习',
    'site:nowcoder.com 广州 开发 实习', 'site:v2ex.com 广州 实习',
    'site:jobs.bytedance.com 广州 实习',
    'site:careers.tencent.com 广州 实习', 'site:recruit.netease.com 广州 实习',
    'site:shixiseng.com 广州 实习', 'site:shixiseng.com 广州 开发 实习',
    'site:nowcoder.com 广州 实习 招聘', 'site:nowcoder.com 广州 开发 实习',
    'site:shixiseng.com 广州 Python 实习', 'site:shixiseng.com 广州 后端 实习',
    'site:shixiseng.com 广州 算法 实习')


def canonical(url):
    p = urlsplit(public_url(url))
    host = (p.hostname or '').lower()
    if host in MIRRORS:
        p = p._replace(netloc=MIRRORS[host])
    # Preserve job identifiers and all unknown query parameters.
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'gclid', 'fbclid'}]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(sorted(query)), ''))


def allowed(url):
    host = urlsplit(url).hostname
    return any(host == d or host.endswith('.' + d) for d in DOMAINS)


EXPIRED_MARKERS = ('职位已下线', '已下线', '停止招聘', '已招满', '招聘已结束', '已结束',
                   '已过期', '职位已关闭', '该职位已失效')
RECHECK_DAYS = 7
# Site chrome that must never satisfy a keyword signal.
NOISE = ('刷真题', '看面经', '得内推', '题库', '模拟面试', '课程', '竞赛',
         '公众号', '营业执照', 'ICP备', '意见反馈', '关于我们', '免责声明')


def is_active(item):
    """'Active' means: clean signals AND a recheck inside the freshness window."""
    if item.get('screening') != 'signals_complete':
        return False
    stamp = item.get('rechecked_at')
    if not stamp:
        return False
    try:
        seen = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - seen).days <= RECHECK_DAYS


def deadline_line(text):
    """Last date on a 截止/投递时间 line, or None."""
    line = next((l for l in text.splitlines()
                 if any(k in l for k in ('截止', '投递时间', '报名时间')) and '20' in l), None)
    if not line:
        return None
    found = re.findall(r'(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})', line)
    dates = []
    for y, m, d in found:
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    return max(dates) if dates else None


def updated_date(text):
    line = next((l for l in text.splitlines()
                 if '更新' in l and re.search(r'20\d{2}', l)), None)
    if not line:
        return None
    m = re.search(r'(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})', line)
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


def screen(page):
    """Conservative lead signals, not eligibility or vacancy certification."""
    text = page['text']
    # A page that says it is over outranks every keyword match.
    expired = next((m for m in EXPIRED_MARKERS if m in text), None)
    deadline = deadline_line(text)
    if deadline and deadline < date.today():
        expired = expired or f'截止日期 {deadline.isoformat()} 已过'
    if expired:
        return {'screening': 'expired', 'evidence': {'listing': expired},
                'reasons': [f'页面已失效：{expired}', '关键词命中也无效，不再作为候选'],
                'listing_status': 'closed'}
    patterns = {
        'internship': r'[^\n。；]{0,60}实习[^\n。；]{0,60}',
        'technical': r'[^\n。；]{0,50}(?:Python|Java|后端|前端|软件开发|算法|机器学习|Agent|测试开发|数据工程)[^\n。；]{0,50}',
    }
    evidence = {k: m.group(0) for k, p in patterns.items() if (m := re.search(p, text, re.I))}
    # Technical must come from a real content line, not the site's nav/footer.
    technical = next((line.strip() for line in text.splitlines()
                      if not any(n in line for n in NOISE)
                      and re.search(patterns['technical'], line, re.I)), None)
    if technical:
        evidence['technical'] = technical[:120]
    else:
        evidence.pop('technical', None)
    # City and degree are often inline ("广东省广州市…", "本科及以上"), not "label: value".
    for key, test in (
            ('city', lambda s: '广州' in s and not any(x in s for x in ('地址', '公司', '办公'))),
            ('degree', lambda s: any(d in s for d in ('本科', '硕士', '博士', '大专'))
             and any(k in s for k in ('以上', '在读', '学历', '/天', '周')))):
        line = next((line.strip() for line in text.splitlines()
                     if 0 < len(line.strip()) <= 80 and test(line)), None)
        if line:
            evidence[key] = line
    keys = ('internship', 'city', 'degree', 'technical')
    reasons = [f'{k}：命中原文' for k in evidence]
    missing = [k for k in keys if k not in evidence]
    reasons += [f'{k}：缺少明确证据，待核对' for k in missing]
    stale = None
    updated = updated_date(text)
    if updated:
        age = (date.today() - updated).days
        if age > 45:
            stale = f'页面更新于 {updated.isoformat()}，已 {age} 天未更新，可能已过期或招满'
            reasons.insert(0, stale)
    # A school list or multi-job posting is not counted as a single qualified job.
    reasons.append('待核对是否单岗详情、发布日期、截止日期及仍在招状态')
    return {'screening': 'signals_complete' if not missing and not stale else 'needs_review',
            'evidence': evidence, 'reasons': reasons, 'listing_status': 'unknown'}


def _esc(value):
    return (str(value if value is not None else '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


HTML_HEAD = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>广州实习候选看板</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c1f23;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;
--ok:#059669;--warn:#d97706;--bad:#dc2626;--chip:#eef2ff}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#e5e7eb;--muted:#9ca3af;
--line:#2a2f38;--accent:#60a5fa;--ok:#34d399;--warn:#fbbf24;--bad:#f87171;--chip:#1e293b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px}
.chip b{font-size:15px;margin-left:4px}
.chip.ok b{color:var(--ok)}.chip.warn b{color:var(--warn)}.chip.bad b{color:var(--bad)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:18px}
.panel h2{font-size:14px;margin:0 0 12px;color:var(--muted);font-weight:600;letter-spacing:.02em}
.bar{display:flex;height:12px;border-radius:999px;overflow:hidden;background:var(--chip);margin:6px 0 10px}
.bar span{display:block;height:100%}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600}
.tools{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
button{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer}
button.on{border-color:var(--accent);color:var(--accent)}
input{flex:1;min-width:180px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:8px}
.card header{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.card h3{font-size:14px;margin:0;line-height:1.45;overflow-wrap:anywhere}
.badge{font-size:11px;padding:2px 8px;border-radius:999px;white-space:nowrap;border:1px solid var(--line);color:var(--muted)}
.badge.complete{color:var(--ok);border-color:var(--ok)}
.badge.review{color:var(--warn);border-color:var(--warn)}
.badge.failed{color:var(--bad);border-color:var(--bad)}
.badge.unread{color:var(--muted)}
.src{font-size:12px;color:var(--muted)}
.ev{font-size:12px;background:var(--chip);border-radius:8px;padding:6px 8px;color:var(--ink)}
.why{font-size:12px;color:var(--muted);margin:0;padding-left:16px}
.why li{margin:2px 0}
a{color:var(--accent);text-decoration:none;font-size:12px;overflow-wrap:anywhere}
.empty{color:var(--muted);font-size:13px}
footer{color:var(--muted);font-size:12px;margin-top:26px}
</style></head><body><div class="wrap">
"""

HTML_TAIL = """</div>
<script>
const buttons = document.querySelectorAll('[data-filter]');
const cards = [...document.querySelectorAll('.card')];
const box = document.getElementById('q');
let active = 'all';
function apply(){
  const q = (box.value || '').trim().toLowerCase();
  cards.forEach(c => {
    const okType = active === 'all' || c.dataset.screening === active;
    const okText = !q || c.textContent.toLowerCase().includes(q);
    c.style.display = okType && okText ? '' : 'none';
  });
}
buttons.forEach(b => b.addEventListener('click', () => {
  active = b.dataset.filter;
  buttons.forEach(x => x.classList.toggle('on', x === b));
  apply();
}));
box.addEventListener('input', apply);
apply();
</script></body></html>"""

COLORS = {'signals_complete': '#059669', 'needs_review': '#d97706',
          'read_failed': '#dc2626', 'expired': '#6b7280', 'unread': '#94a3b8', 'duplicate': '#6366f1'}
LABELS = {'signals_complete': '信号齐全', 'needs_review': '待核对',
          'read_failed': '读取失败', 'expired': '已结束/下线', 'unread': '未读', 'duplicate': '重复'}
BADGE = {'signals_complete': 'complete', 'needs_review': 'review',
         'read_failed': 'failed', 'expired': 'unread', 'unread': 'unread', 'duplicate': 'unread'}


ORDER = {'signals_complete': 0, 'needs_review': 1, 'read_failed': 2, 'expired': 3, 'unread': 4, 'duplicate': 5}


def render_html(rows, searches, counts, generated):
    rows = sorted(rows, key=lambda r: (ORDER.get(r['screening'], 9), r.get('source') or ''))
    total = len(rows) or 1
    read = len(rows) - counts.get('unread', 0)
    parts = [HTML_HEAD]
    parts.append(f'<h1>广州实习候选看板</h1>')
    parts.append(f'<div class="sub">生成于 {_esc(generated)} · 数据只在本机 · 关键词命中不等于在招，投递前需人工核对</div>')
    parts.append('<div class="chips">')
    parts.append(f'<div class="chip">唯一 URL <b>{len(rows)}</b></div>')
    parts.append(f'<div class="chip">已读 <b>{read}</b></div>')
    parts.append(f'<div class="chip ok">在招（复检通过） <b>{counts.get("active", 0)}</b></div>')
    parts.append(f'<div class="chip ok">关键词齐全 <b>{counts.get("signals_complete", 0)}</b></div>')
    parts.append(f'<div class="chip">已复检 <b>{counts.get("rechecked", 0)}</b></div>')
    parts.append(f'<div class="chip warn">待核对 <b>{counts.get("needs_review", 0)}</b></div>')
    parts.append(f'<div class="chip bad">读取失败 <b>{counts.get("read_failed", 0)}</b></div>')
    parts.append(f'<div class="chip">已结束/下线 <b>{counts.get("expired", 0)}</b></div>')
    parts.append(f'<div class="chip">未读 <b>{counts.get("unread", 0)}</b></div>')
    parts.append('</div>')

    # funnel
    parts.append('<div class="panel"><h2>漏斗</h2><div class="bar">')
    for key in ('signals_complete', 'needs_review', 'read_failed', 'unread', 'duplicate'):
        n = counts.get(key, 0)
        if n:
            parts.append(f'<span title="{LABELS[key]} {n}" style="width:{n / total * 100:.4f}%;background:{COLORS[key]}"></span>')
    parts.append('</div><div class="legend">')
    for key in ('signals_complete', 'needs_review', 'read_failed', 'expired', 'unread'):
        parts.append(f'<span><i class="dot" style="background:{COLORS[key]}"></i>{LABELS[key]} {counts.get(key, 0)}</span>')
    parts.append('</div></div>')

    # sources
    by_source = {}
    for r in rows:
        by_source[r.get('source') or '未知'] = by_source.get(r.get('source') or '未知', 0) + 1
    parts.append('<div class="panel"><h2>来源分布</h2><table><tr><th>来源</th><th>候选数</th><th>已读</th><th>信号齐全</th></tr>')
    for src, n in sorted(by_source.items(), key=lambda x: -x[1]):
        done = sum(1 for r in rows if (r.get('source') or '未知') == src and r['screening'] != 'unread')
        good = sum(1 for r in rows if (r.get('source') or '未知') == src and r['screening'] == 'signals_complete')
        parts.append(f'<tr><td>{_esc(src)}</td><td>{n}</td><td>{done}</td><td>{good}</td></tr>')
    parts.append('</table></div>')

    # searches
    parts.append('<div class="panel"><h2>查询记录</h2><table><tr><th>查询</th><th>返回</th><th>新增</th><th>错误</th></tr>')
    for s in searches:
        parts.append(f'<tr><td>{_esc(s.get("query"))}</td><td>{s.get("returned", 0)}</td><td>{s.get("added", 0)}</td><td>{_esc(s.get("error") or "无")}</td></tr>')
    parts.append('</table></div>')

    # filters
    parts.append('<div class="tools">')
    parts.append('<button data-filter="all" class="on">全部</button>')
    parts.append(f'<button data-filter="active">在招 {counts.get("active", 0)}</button>')
    for key in ('signals_complete', 'needs_review', 'read_failed', 'expired', 'unread'):
        parts.append(f'<button data-filter="{key}">{LABELS[key]} {counts.get(key, 0)}</button>')
    parts.append('<input id="q" placeholder="搜索岗位、公司、来源、理由…">')
    parts.append('</div><div class="cards">')

    for r in rows:
        screening = r['screening']
        title = r.get('title') or ''
        generic = ('职位详情-国家大学生就业服务平台', '广东工业大学学生就业指导中心', '暨南大学就业信息服务平台')
        if not title or title in generic or title.startswith('职位详情'):
            title = ((r.get('evidence') or {}).get('technical')
                     or (r.get('evidence') or {}).get('internship')
                     or f"{r.get('source')} · " + ('未读候选' if screening == 'unread' else '无标题'))
        reasons = r.get('reasons') or []
        evidence = r.get('evidence') or {}
        active = is_active(r)
        parts.append(f'<article class="card" data-screening="{"active" if active else screening}">')
        parts.append(f'<header><h3>{_esc(title)}</h3><span class="badge {"complete" if active else BADGE.get(screening, "unread")}">{"在招" if active else LABELS.get(screening, screening)}</span></header>')
        stamp = str(r.get("fetched_at"))[:16].replace("T", " ") if r.get("fetched_at") else "未读"
        again = str(r.get("rechecked_at"))[:16].replace("T", " ") if r.get("rechecked_at") else "—"
        parts.append(f'<div class="src">{_esc(r.get("source"))} · 发现 {_esc(str(r.get("discovered_at"))[:16].replace("T", " "))} · 抓取 {_esc(stamp)} · 复检 {_esc(again)}</div>')
        if r.get("recheck_error"):
            parts.append(f'<div class="ev">复检失败：{_esc(r["recheck_error"])}</div>')
        for key in ('city', 'degree', 'internship', 'technical'):
            if key in evidence:
                parts.append(f'<div class="ev"><b>{_esc({"city": "地点", "degree": "学历", "internship": "实习", "technical": "技术"}[key])}</b>：{_esc(evidence[key])}</div>')
        parts.append('<ul class="why">' + ''.join(f'<li>{_esc(x)}</li>' for x in reasons[:4]) + '</ul>')
        parts.append(f'<a href="{_esc(r.get("url"))}" target="_blank" rel="noreferrer">{_esc(r.get("url"))}</a>')
        parts.append('</article>')
    parts.append('</div>')
    parts.append(f'<footer>累计队列，不是新增日报。验收线：≥5 条经核对的独立在招岗位，并跨日重复验证。当前 {counts.get("signals_complete", 0)} 条信号齐全，未达线。</footer>')
    parts.append(HTML_TAIL)
    return ''.join(parts)


class Candidates:
    def __init__(self, backend):
        self.backend = backend
        self.db = backend.store.db
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS plugin_candidates (
          id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plugin_candidate_searches (
          id INTEGER PRIMARY KEY, data TEXT NOT NULL);
        ''')

    def plan(self):
        return {'queries': list(QUERIES), 'allowed_domains': list(DOMAINS),
                'read_budget': 10, 'model_calls': 0,
                'instruction': '逐条用 DSH 搜索工具执行查询；每条查询即使失败或零结果也调用 internship_candidates_add。仅提交URL，不提交摘要。读取按来源配额：nowcoder 4、jnu/ncss 2、gdut 3、tencent 2、bytedance 1；优先标题含 Agent/AI/算法/后端/开发 的候选。最后 report。'}

    def rows(self):
        return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM plugin_candidates ORDER BY rowid')]

    def add(self, query, urls, error=''):
        if query not in QUERIES:
            raise ValueError('请使用 candidates_plan 中的固定查询')
        added, duplicates, rejected = [], [], []
        stamp = now()
        with self.db:
            for raw in urls:
                try:
                    url = canonical(raw)
                    if not allowed(url):
                        raise ValueError('不在来源白名单')
                except ValueError as exc:
                    rejected.append({'url': raw, 'reason': str(exc)})
                    continue
                row = self.db.execute('SELECT data FROM plugin_candidates WHERE url=?', (url,)).fetchone()
                if row:
                    data = json.loads(row[0])
                    data['queries'] = list(dict.fromkeys([*data['queries'], query]))
                    data['last_discovered_at'] = stamp
                    self.db.execute('UPDATE plugin_candidates SET data=? WHERE url=?', (encode(data), url))
                    duplicates.append(data['id'])
                    continue
                item = {'id': 'c_' + digest(url)[:24], 'url': url, 'source': urlsplit(url).hostname,
                        'queries': [query], 'discovered_at': stamp, 'last_discovered_at': stamp,
                        'fetched_at': None, 'state': 'new', 'screening': 'unread',
                        'reasons': ['搜索URL线索，未读取正文']}
                self.db.execute('INSERT INTO plugin_candidates VALUES (?,?,?)', (item['id'], url, encode(item)))
                added.append(item['id'])
            event = {'query': query, 'searched_at': stamp, 'returned': len(urls), 'added': len(added),
                     'duplicates': len(duplicates), 'rejected': rejected, 'error': error}
            self.db.execute('INSERT INTO plugin_candidate_searches(data) VALUES (?)', (encode(event),))
        return {'added': added, 'duplicates': duplicates, 'search': event}

    def check(self, candidate_id, web):
        row = self.db.execute('SELECT data FROM plugin_candidates WHERE id=?', (candidate_id,)).fetchone()
        if not row:
            raise ValueError('候选不存在')
        item = json.loads(row[0])
        if item['screening'] != 'unread':
            return item  # No implicit retries or repeated reads.
        item['attempted_at'] = now()
        try:
            page = web.read(item['url'])
            if not allowed(canonical(page['url'])):
                raise ValueError('最终页面不在来源白名单，不作为候选证据')
            snapshot = self.backend.snapshot(page)
            item.update(screen(page), page_id=snapshot['page_id'], fetched_at=page['fetched_at'],
                        title=page.get('title', ''), final_url=canonical(page['url']))
            item['content_hash'] = digest(page['text'])
            duplicate = next((r for r in self.rows() if r['id'] != item['id'] and
                              (r.get('final_url') == item['final_url'] or
                               r.get('content_hash') == item['content_hash'])), None)
            if duplicate:
                item.update(screening='duplicate', duplicate_of=duplicate['id'])
                item['reasons'].append('最终URL或全文完全相同')
        except Exception as exc:
            item.update(screening='read_failed', reasons=[str(exc) if isinstance(exc, ValueError) else type(exc).__name__])
        with self.db:
            self.db.execute('UPDATE plugin_candidates SET data=? WHERE id=?', (encode(item), candidate_id))
        return item

    def recheck(self, limit=10, web=None):
        """Refetch already-read pages, refresh snapshots, and re-screen them."""
        web = web or WebTools()
        weight = {'signals_complete': 0, 'needs_review': 1, 'expired': 2}
        targets = [r for r in self.rows()
                   if r.get('page_id') and r['screening'] in weight]
        targets.sort(key=lambda r: weight.get(r['screening'], 9))
        targets = targets[:max(1, min(int(limit), 30))]
        summary = {'checked': 0, 'expired': 0, 'active': 0, 'errors': []}
        for item in targets:
            url = canonical(item.get('final_url') or item['url'])
            item['rechecked_at'] = now()
            try:
                if not allowed(url):
                    raise ValueError('不在来源白名单')
                page = web.read(url)
                snapshot = self.backend.snapshot(page)
                fresh = screen(page)
                item.update(fresh)
                item['reasons'] = fresh['reasons']
                item['listing_status'] = fresh['listing_status']
                item['page_id'] = snapshot['page_id']
                item['fetched_at'] = page['fetched_at']
                item['content_hash'] = digest(page['text'])
                item.pop('recheck_error', None)
            except Exception as exc:
                detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                item['recheck_error'] = detail
                if 'HTTP 404' in detail or 'HTTP 410' in detail:
                    item.update(screening='expired', evidence={'listing': '页面已不存在'},
                                reasons=['复检：页面已不存在（404/410）'], listing_status='closed')
            summary['checked'] += 1
            summary['expired'] += item['screening'] == 'expired'
            summary['active'] += is_active(item)
            if item.get('recheck_error'):
                summary['errors'].append({'id': item['id'], 'error': item['recheck_error'][:200]})
            with self.db:
                self.db.execute('UPDATE plugin_candidates SET data=? WHERE id=?', (encode(item), item['id']))
        summary['active_total'] = sum(is_active(r) for r in self.rows())
        return summary

    def rescreen(self):
        """Re-run the screen over stored snapshots (no network, no model)."""
        changed = 0
        for item in self.rows():
            pid = item.get('page_id')
            if not pid or item['screening'] in ('unread', 'read_failed', 'duplicate'):
                continue
            row = self.db.execute('SELECT data FROM plugin_pages WHERE id=?', (pid,)).fetchone()
            if not row:
                continue
            fresh = screen(json.loads(row[0]))
            if fresh['screening'] != item['screening']:
                item.update(fresh)
                item['reasons'] = fresh['reasons']
                item['listing_status'] = fresh['listing_status']
                with self.db:
                    self.db.execute('UPDATE plugin_candidates SET data=? WHERE id=?', (encode(item), item['id']))
                changed += 1
        return changed

    def data(self):
        self.rescreen()
        rows = self.rows()
        rows = sorted(rows, key=lambda r: (0 if r['screening'] == 'unread' else 1,
                                           SOURCE_ORDER.get(r.get('source') or '', 5), r['url']))
        searches = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM plugin_candidate_searches ORDER BY id')]
        counts = {key: sum(r['screening'] == key for r in rows) for key in
                  ('unread', 'signals_complete', 'needs_review', 'read_failed', 'expired', 'duplicate')}
        counts['active'] = sum(is_active(r) for r in rows)
        counts['rechecked'] = sum(1 for r in rows if r.get('rechecked_at'))
        return rows, searches, counts

    def view(self, rows=None, searches=None, counts=None):
        generated = now()
        self.rescreen()
        rows = self.rows() if rows is None else rows
        searches = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM plugin_candidate_searches ORDER BY id')] if searches is None else searches
        counts = {key: sum(r['screening'] == key for r in rows) for key in
                  ('unread', 'signals_complete', 'needs_review', 'read_failed', 'expired', 'duplicate')} if counts is None else counts
        counts['active'] = sum(is_active(r) for r in rows)
        counts['rechecked'] = sum(1 for r in rows if r.get('rechecked_at'))
        path = self.backend.root / 'candidates.html'
        tmp = path.with_suffix('.html.tmp')
        tmp.write_text(render_html(rows, searches, counts, generated), encoding='utf-8')
        tmp.replace(path)
        return {'ok': True, 'path': str(path), 'generated_at': generated,
                'unique_urls': len(rows), 'counts': counts}

    def report(self):
        rows, searches, counts = self.data()
        result = {'generated_at': now(), 'model_calls': 0, 'unique_urls': len(rows), 'counts': counts,
                  'searches': searches, 'candidates': rows,
                  'html': str(self.view(rows, searches, counts)['path']),
                  'acceptance': '未验收：关键词命中不等于有效岗位；至少5条经核对的独立在招岗位，并跨日重复验证后才能声称稳定。'}
        text = ['候选供给基线（累计队列，不是新增日报）', f'唯一URL：{len(rows)}；模型调用：0',
                encode(counts), result['acceptance'], '']
        text.extend(['搜索记录：'] + [f"{s['query']} | 返回{s['returned']} | 新增{s['added']} | 错误：{s['error'] or '无'}" for s in searches] + [''])
        for r in rows:
            text.extend([f"[{r['id']}] {r.get('title') or r['url']} — {r['screening']}",
                         r['url'], '来源：' + r['source'], '抓取时间：' + str(r['fetched_at']),
                         '；'.join(r['reasons']), ''])
        for name, content in [('candidates.json', encode(result)), ('candidates.txt', '\n'.join(text))]:
            path = self.backend.root / name
            tmp = path.with_suffix(path.suffix + '.tmp')
            tmp.write_text(content, encoding='utf-8')
            tmp.replace(path)
        return result
