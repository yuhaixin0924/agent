export const profilePage = String.raw`<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>我的实习档案</title>
<style>
:root{font-family:Inter,"Microsoft YaHei",system-ui,sans-serif;color:#172c3d;background:#f3f6f9;font-synthesis:none}
*{box-sizing:border-box}body{margin:0}main{max-width:1100px;margin:auto;padding:32px 28px 90px}
header{margin-bottom:24px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:2px;color:#527084}h1{font-size:30px;letter-spacing:-1px;margin:10px 0}p{line-height:1.8;color:#607182;margin:6px 0;font-size:14px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 268px;gap:22px;align-items:start}.card{background:white;border:1px solid #dce5ed;border-radius:16px;padding:24px;margin-bottom:18px}
h2{font-size:17px;margin:0 0 6px;display:flex;align-items:center;gap:10px}.number{display:inline-grid;place-items:center;width:27px;height:27px;border-radius:8px;background:#e9f3f3;color:#216263;font-size:12px}.hint{font-size:12px;color:#738292;margin-bottom:18px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.field{display:flex;flex-direction:column;gap:7px}.wide{grid-column:1/-1}label{font-size:13px;font-weight:600}input[type=text],input[type=number],textarea{width:100%;border:1px solid #cdd9e3;border-radius:9px;padding:11px 12px;font:inherit;font-size:14px;color:#172c3d;background:#fff}textarea{resize:vertical;min-height:82px;line-height:1.6}input:focus,textarea:focus{outline:2px solid #99cccc;outline-offset:1px}small{font-size:12px;line-height:1.6;color:#738292}
.check{display:flex;align-items:flex-start;gap:8px;margin:10px 0;font-weight:400;line-height:1.6}.check input{margin-top:4px;accent-color:#216263}.aside{position:sticky;top:24px}.aside .card{padding:20px}.badge{display:inline-block;padding:5px 9px;background:#e9f3f3;color:#216263;border-radius:6px;font-size:12px;margin-bottom:14px}.summary{font-size:14px;line-height:1.9;white-space:pre-line}.aside h2{font-size:15px;margin-bottom:14px}.note{padding-top:14px;margin-top:14px;border-top:1px solid #e7edf2;font-size:12px;line-height:1.8;color:#607182}.import{border:1px dashed #94b7bd;background:#f7fbfb}.import-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.import-row input{max-width:100%;font-size:13px}.missing{padding:12px;background:#fff8e9;border-radius:8px;font-size:12px;line-height:1.8;color:#775d2e;margin-top:14px}
details{margin-top:18px}summary{cursor:pointer;font-size:13px;color:#527084}pre{white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto;font-size:12px;background:#f4f7fa;padding:14px;border-radius:8px}details .grid{margin-top:18px}
.actions{position:fixed;bottom:0;left:0;right:0;background:#fffffff5;border-top:1px solid #dce5ed;padding:14px 28px;display:flex;gap:12px;align-items:center;justify-content:center;z-index:2}button{font:inherit;font-size:14px;cursor:pointer;border-radius:9px;padding:10px 18px;border:1px solid #cdd9e3;background:white;color:#314b60}button.primary{background:#216263;border-color:#216263;color:white}button:disabled{opacity:.5;cursor:default}#status{font-size:13px;max-width:500px;line-height:1.5;color:#527084}#status[data-error=true]{color:#ab3030}
dialog{width:min(720px,92vw);max-height:86vh;overflow:auto;border:1px solid #cdd9e3;border-radius:16px;padding:24px;color:#172c3d}dialog::backdrop{background:#142c3f88}.review-actions{display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-end;margin-top:20px}.diff-row{border-bottom:1px solid #e7edf2;padding:12px 0}.diff-row strong{font-size:14px}.diff-row pre{margin:6px 0}.question{background:#fff8e9;color:#775d2e;padding:12px;border-radius:8px;margin:10px 0;font-size:13px;line-height:1.7}.review-help{font-size:12px}
@media(max-width:780px){main{padding:22px 16px 160px}.layout{grid-template-columns:1fr}.aside{position:static}.grid{grid-template-columns:1fr}.actions{padding:12px 16px;flex-wrap:wrap;justify-content:flex-start}#status{width:100%;order:3}.card{padding:18px}h1{font-size:26px}}
</style></head>
<body><main>
<header><div class="eyebrow">INTERNSHIP · 个人档案</div><h1>先了解你，再看实习机会。</h1><p>按你的实际情况填写；尚未确定的内容可以留空，之后随时调整。</p></header>
<div class="layout"><form id="profile-form">
<fieldset id="fields" disabled style="border:0;padding:0;margin:0;min-width:0">
<section class="card import"><h2>有简历？可以先导入草稿</h2><p class="hint">支持文字版 PDF、DOCX、TXT、MD，最大 4 MB；扫描图片暂不支持。</p><div class="import-row"><label for="resume-file">选择简历</label><input id="resume-file" type="file" accept=".pdf,.docx,.txt,.md"><button type="button" id="import-resume">提取并填入空白项</button></div><p class="hint" style="margin:12px 0 0">在本机提取，不调用模型，不保留简历原件。只提取明确的中文字段，可能遗漏；不会覆盖已填内容，也不会自动保存。</p><p id="import-status" role="status" aria-live="polite"></p><details id="resume-details" hidden><summary>核对提取到的简历文字</summary><pre id="resume-text"></pre></details></section>
<section class="card"><h2><span class="number">01</span>你目前的情况</h2><p class="hint">不用提供姓名、电话或学号。</p><div class="grid">
<div class="field wide"><label for="stage">学历与年级</label><input id="stage" name="stage" type="text" maxlength="4000" placeholder="例如：本科大二，计算机相关专业"></div>
<div class="field wide"><label for="background">学习或项目经历（选填）</label><textarea id="background" name="background" maxlength="4000" placeholder="例如：做过课程项目，尚无正式实习经历"></textarea></div>
</div></section>
<section class="card"><h2><span class="number">02</span>技能与成长方向</h2><p class="hint">支持逗号、顿号、分号、换行；常见独立条目也支持空格。保存前会展示整理结果，有歧义的短语请核对。</p><div class="grid">
<div class="field"><label for="skills_known">已经掌握的技能</label><textarea id="skills_known" name="skills_known" placeholder="例如：Python、Git、SQL"></textarea></div>
<div class="field"><label for="skills_learning">正在学习的技能</label><textarea id="skills_learning" name="skills_learning" placeholder="例如：Agent 开发、后端框架"></textarea></div>
<div class="field wide"><label for="growth_goal">希望在实习中学到什么（选填）</label><textarea id="growth_goal" name="growth_goal" maxlength="4000" placeholder="例如：参与真实项目，了解从开发到上线的流程"></textarea></div>
</div></section>
<section class="card"><h2><span class="number">03</span>想找怎样的实习</h2><p class="hint">城市、方向和偏好会帮助制定搜索计划。</p><div class="grid">
<div class="field"><label for="cities">目标城市</label><input id="cities" name="cities" type="text" placeholder="例如：广州、深圳"></div>
<div class="field"><label for="keywords">目标岗位或方向</label><input id="keywords" name="keywords" type="text" placeholder="例如：后端开发、Agent"></div>
<div class="field wide"><label for="priorities">最看重的条件</label><textarea id="priorities" name="priorities" placeholder="例如：学习机会、远程、住宿、薪酬"></textarea><small>这里记录你的偏好；住宿、薪酬等目前需要结合岗位原文分析，不会自动作为硬性过滤条件。</small></div>
</div></section>
<section class="card"><h2><span class="number">04</span>时间与不可妥协的条件</h2><p class="hint">没有确定的时间先留空，留空表示未知。</p><div class="grid">
<div class="field"><label for="days_per_week">每周可出勤上限（天）</label><input id="days_per_week" name="days_per_week" type="number" min="0" max="7" step="1" placeholder="待定"><small>填 5 表示每周最多可提供 5 天，可满足至少 3、4 或 5 天的要求；不是必须正好 5 天。</small></div>
<div class="field"><label for="months">可连续实习（月）</label><input id="months" name="months" type="number" min="0" max="120" step="1" placeholder="待定"></div>
<div class="wide"><label>以下条件不能妥协（选填）</label><label class="check"><input type="checkbox" name="hard" value="city">只能在所填城市实习</label><label class="check"><input type="checkbox" name="hard" value="days_per_week">不能超过所填的每周出勤天数</label><label class="check"><input type="checkbox" name="hard" value="months">无法满足比所填月数更长的最低实习要求</label><small>只有明确不能调整时才勾选。未勾选的条件仍可用于分析，但不自动排除岗位。</small></div>
</div><div class="field" style="margin-top:20px"><label for="additional_constraints">其他重要条件或不可接受的情况（选填）</label><textarea id="additional_constraints" name="additional_constraints" maxlength="4000" placeholder="请注明“必须”还是“希望”。例如：必须靠近地铁、不能接受夜班；希望附近有公园或健身房，方便下班后运动。"></textarea><small>这些补充会提供给后续分析作参考。周边设施、通勤距离等需要额外证据，信息不足时应标为待确认；目前不会据此自动排除岗位。</small></div><details><summary>更多设置：可接受的学历标签</summary><div class="field" style="margin-top:14px"><label for="accepted_degree_labels">用于匹配岗位学历要求（选填）</label><input id="accepted_degree_labels" name="accepted_degree_labels" type="text" placeholder="例如：本科、本科及以上"><small>不确定时留空，不要把希望达到的学历当成现有学历。</small></div></details></section>
</fieldset></form>
<aside class="aside"><section class="card"><span class="badge">本机保存 · 随时修改</span><h2>你的求职画像</h2><div id="summary" class="summary">正在读取档案…</div><div id="missing" class="missing"></div><div class="note">当前 Harness 中的实习对话共用这份档案。演示切换人物时，请先在这里修改并保存。</div><div class="note">填写和保存不调用模型。之后进行岗位分析时，相关信息会交给 Harness 所配置的模型服务。</div><details><summary>查看当前表单数据（未保存的修改也会显示）</summary><pre id="preview"></pre></details></section></aside>
</div></main>
<div class="actions"><button class="primary" id="save" type="submit" form="profile-form" disabled>保存档案</button><button id="reload" type="button">重新载入</button><button id="undo" type="button" disabled>恢复上一版</button><span id="status" role="status" aria-live="polite">正在读取…</span></div>
<dialog id="review"><h2>核对这次档案修改</h2><p>以下是准备写入的实际内容，目前尚未保存。请检查条目拆分、已掌握/正在学习及不可妥协条件。</p><div id="review-changes"></div><div id="review-questions"></div><p class="review-help">出勤天数是个人可提供的上限，并非岗位必须正好要求该天数。解释含义不会自动改变数值。</p><p id="review-status" role="status" aria-live="polite"></p><div class="review-actions"><button id="edit-draft" type="button">返回修改</button><button id="confirm-draft" type="button" class="primary">确认并保存这些修改</button></div></dialog>
<script>
const form = document.getElementById('profile-form');
const fields = document.getElementById('fields');
const saveButton = document.getElementById('save');
const reloadButton = document.getElementById('reload');
const status = document.getElementById('status');
const undoButton = document.getElementById('undo');
const review = document.getElementById('review');
const confirmDraft = document.getElementById('confirm-draft');
let pendingDraft = null, undoAvailable = false;
const texts = ['stage','background','growth_goal','additional_constraints'];
const lists = ['skills_known','skills_learning','cities','keywords','priorities','accepted_degree_labels'];
let version = null, original = {}, dirty = false, busy = false;
function message(text, error = false) { status.textContent = text; status.dataset.error = String(error); }
function split(text) { return [...new Set(text.split(/[,，、;；\n\r]+/).map(s => s.trim()).filter(Boolean))]; }
function populate(value) {
  for (const key of texts) form.elements[key].value = value[key] || '';
  for (const key of lists) form.elements[key].value = (value[key] || []).join('、');
  for (const key of ['days_per_week','months']) form.elements[key].value = value[key] ?? '';
  for (const input of form.querySelectorAll('input[name=hard]')) input.checked = (value.hard_constraints || []).includes(input.value);
}
async function requestProfile(body) {
  const response = await fetch('/dsh-internship/profile', {method:'PUT',headers:{'Content-Type':'application/json','X-Internship-Profile':'1'},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok || !result.ok) throw new Error(result.error || '档案操作失败');
  return result;
}
function showReview(draft) {
  pendingDraft = draft;
  document.getElementById('review-status').textContent = '';
  const changes = document.getElementById('review-changes'); changes.replaceChildren();
  for (const change of draft.changes) {
    const row = document.createElement('div'); row.className = 'diff-row';
    const label = document.createElement('strong'); label.textContent = change.label;
    const display = value => value === null || value === '' || (Array.isArray(value) && !value.length) ? '未填写' : Array.isArray(value) ? value.join('、') : String(value);
    const before = document.createElement('pre'); before.textContent = '原值：' + display(change.before);
    const after = document.createElement('pre'); after.textContent = '改为：' + (change.removed ? '清空（未知）' : display(change.after));
    row.append(label, before, after); changes.append(row);
  }
  if (!draft.changes.length) changes.textContent = '没有字段变化，无需重复写入。';
  const questions = document.getElementById('review-questions'); questions.replaceChildren();
  for (const item of draft.questions || []) {const p = document.createElement('p'); p.className = 'question'; p.textContent = item.label + '：“' + item.original + '”。' + item.question; questions.append(p);}
  confirmDraft.textContent = draft.changes.length ? '确认并保存这些修改' : '确认无变化';
  if (!review.open) review.showModal();
}
function collect() {
  const value = {...original};
  for (const key of texts) value[key] = form.elements[key].value.trim();
  for (const key of lists) value[key] = split(form.elements[key].value);
  for (const key of ['days_per_week','months']) value[key] = form.elements[key].value === '' ? null : Number(form.elements[key].value);
  value.hard_constraints = Array.from(form.querySelectorAll('input[name=hard]:checked'), e => e.value);
  return value;
}
function preview() {
  const value = collect();
  document.getElementById('summary').textContent = [value.stage || '学历与年级待补充', '城市：' + (value.cities.join('、') || '待定'), '方向：' + (value.keywords.join('、') || '待定'), '每周最多出勤：' + (value.days_per_week === null ? '待定' : value.days_per_week + ' 天'), '实习时长：' + (value.months === null ? '待定' : value.months + ' 个月'), '优先考虑：' + (value.priorities.join('、') || '待定')].join('\n');
  document.getElementById('preview').textContent = JSON.stringify(value, null, 2);
  if (value.additional_constraints) document.getElementById('summary').textContent += '\n其他重要条件：' + value.additional_constraints;
  const labels = {stage:'学历与年级',skills_known:'已掌握的技能',cities:'目标城市',keywords:'岗位方向',days_per_week:'每周出勤',months:'实习月数',priorities:'求职偏好'};
  const missing = Object.keys(labels).filter(key => value[key] === null || value[key] === '' || (Array.isArray(value[key]) && !value[key].length));
  document.getElementById('missing').textContent = missing.length ? '还想了解你：' + missing.map(key => labels[key]).join('、') + '。可以现在补充，也可以保留待定。' : '主要信息已填写。请核对技能、时间和不可妥协的条件，再保存。';
}
function setDirty(value) {
  dirty = value;
  window.parent.postMessage({source: 'dsh-internship-profile', dirty}, window.location.origin);
}
async function load() {
  if (dirty && !confirm('重新载入会放弃尚未保存的修改，继续吗？')) return;
  busy = true; fields.disabled = true; saveButton.disabled = true; reloadButton.disabled = true; undoButton.disabled = true;
  message('正在读取…');
  try {
    const response = await fetch('/dsh-internship/profile', {cache:'no-store'});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || '读取失败');
    original = result.profile; version = result.version;
    undoAvailable = result.undo_available; populate(original);
    setDirty(false); preview(); message('已读取当前档案。填写后点击“保存档案”。');
    fields.disabled = false; saveButton.disabled = false;
  } catch (error) { message(error.message + '；未修改本地文件。', true); }
  finally { busy = false; reloadButton.disabled = false; undoButton.disabled = !undoAvailable; }
}
form.addEventListener('input', event => {if (event.target.id === 'resume-file') return; setDirty(true); preview(); message('有修改尚未保存');});
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !form.reportValidity() || version === null) return;
  const profile = collect();
  const hard = profile.hard_constraints;
  if ((hard.includes('city') && !profile.cities.length) || (hard.includes('days_per_week') && !profile.days_per_week) || (hard.includes('months') && !profile.months)) {message('请先填写有效的城市、出勤天数或实习月数，再勾选对应的不可妥协条件。', true); return;}
  busy = true; fields.disabled = true; saveButton.disabled = true; reloadButton.disabled = true; message('正在保存…');
  try {
    const submitted = Object.fromEntries(Object.entries(profile).filter(([key,value]) => key in original || !(value === '' || value === null || (Array.isArray(value) && !value.length))));
    const result = await requestProfile({profile:submitted,version,prepare:true});
    showReview(result); message('请核对修改预览，确认后才会保存。');
  } catch (error) {message(error.message, true);}
  finally {busy = false; fields.disabled = false; saveButton.disabled = false; reloadButton.disabled = false;}
});
reloadButton.addEventListener('click', load);
function backToEdit() {
  if (pendingDraft) {populate(pendingDraft.profile); setDirty(true); preview();}
  pendingDraft = null; review.close(); message('草稿未保存，可以继续编辑后再保存。');
}
document.getElementById('edit-draft').addEventListener('click', backToEdit);
review.addEventListener('cancel', event => {if (busy) {event.preventDefault();return;} event.preventDefault(); backToEdit();});
confirmDraft.addEventListener('click', async () => {
  if (!pendingDraft || busy) return;
  busy = true; confirmDraft.disabled = true; document.getElementById('edit-draft').disabled = true;
  try {
    const result = await requestProfile({draft_id:pendingDraft.draft_id,confirmation:'user_confirmed'});
    version = result.version; original = result.profile; undoAvailable = result.undo_available || undoAvailable;
    populate(original); setDirty(false); preview(); pendingDraft = null; review.close();
    message(result.saved ? '已保存并重新读取本机 profile.json，共更新 ' + result.changes.length + ' 项。' : '档案内容没有变化，无需重复保存。');
    history.replaceState(null,'',location.pathname);
  } catch (error) {document.getElementById('review-status').textContent = error.message + ' 未保存；可返回后重新载入。';}
  finally {busy = false; confirmDraft.disabled = false; document.getElementById('edit-draft').disabled = false; undoButton.disabled = !undoAvailable;}
});
undoButton.addEventListener('click', async () => {
  if (busy || (dirty && !confirm('恢复预览会替代当前未保存的修改，继续吗？'))) return;
  busy = true; undoButton.disabled = true;
  try {showReview(await requestProfile({restore:true,version}));}
  catch (error) {message(error.message,true);}
  finally {busy = false; undoButton.disabled = !undoAvailable;}
});
document.getElementById('import-resume').addEventListener('click', async () => {
  if (busy) return;
  const file = document.getElementById('resume-file').files[0];
  const importStatus = document.getElementById('import-status');
  if (!file) {importStatus.textContent = '请先选择简历文件。'; return;}
  if (file.size > 4 * 1024 * 1024) {importStatus.textContent = '请选择 4 MB 以内的简历文件。'; return;}
  busy = true; fields.disabled = true; saveButton.disabled = true; reloadButton.disabled = true;
  importStatus.textContent = '正在本机提取文字…';
  try {
    const data = await new Promise((resolve, reject) => {const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject(new Error('文件读取失败')); reader.readAsDataURL(file);});
    const response = await fetch('/dsh-internship/resume', {method:'POST',headers:{'Content-Type':'application/json','X-Internship-Profile':'1'},body:JSON.stringify({name:file.name,data})});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || '简历读取失败');
    let filled = 0;
    for (const [key, value] of Object.entries(result.suggestions)) {
      const input = form.elements[key];
      if (input && input.value.trim() === '') {input.value = Array.isArray(value) ? value.join('、') : value; filled++;}
    }
    document.getElementById('resume-text').textContent = result.text;
    document.getElementById('resume-details').hidden = false;
    preview();
    if (filled) {setDirty(true); message('简历已填入草稿，尚未保存。请核对并补充待定项。');}
    importStatus.textContent = filled ? '已填入 ' + filled + ' 个空白项。请核对提取文字，并在下方补充缺失信息。' : '已提取文字，但没有可直接填入的明确字段，或对应条目已有内容。请参考下方文字手动补充。';
  } catch (error) {importStatus.textContent = error.message;}
  finally {busy = false; fields.disabled = false; saveButton.disabled = false; reloadButton.disabled = false;}
});
window.addEventListener('beforeunload', event => {if (dirty) {event.preventDefault(); event.returnValue = '';}});
async function start() {
  await load();
  const draft = new URLSearchParams(location.search).get('draft');
  if (!draft || version === null) return;
  try {
    const response = await fetch('/dsh-internship/profile?draft=' + encodeURIComponent(draft),{cache:'no-store'});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || '无法读取草稿');
    showReview(result);
  } catch (error) {message(error.message,true);}
}
start();
</script></body></html>`
