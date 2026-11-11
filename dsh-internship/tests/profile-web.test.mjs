import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { mkdtemp, rm, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createProfileHandler, createResumeHandler, serveProfilePage } from '../src/profile-web.js'
import { runBridge, runProfileWeb, runResumeWeb } from '../src/index.js'

test('profile form saves through HTTP, guards origin, and detects stale versions', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'internship-form-'))
  const config = {dataDir: dir}
  const handler = createProfileHandler(request => runProfileWeb(request, config))
  const resume = createResumeHandler(request => runResumeWeb(request, config))
  const server = createServer((req, res) => {
    if (req.url === '/profile.html') return serveProfilePage(req, res)
    if (req.url === '/resume') return resume(req, res)
    return handler(req, res)
  })
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
    const origin = `http://127.0.0.1:${server.address().port}`
    const initial = await fetch(origin).then(r => r.json())
    assert.equal(initial.ok, true)
    const headers = {'content-type':'application/json', origin, 'x-internship-profile':'1'}
    const profile = {stage:'虚拟人物：本科大二',cities:['广州'],skills_known:['Python'],skills_learning:['Agent'],days_per_week:2,months:null,hard_constraints:[],growth_goal:'学习工程实践',additional_constraints:'必须靠近地铁；希望附近有公园'}
    const save = (version, value = profile, custom = headers) => fetch(origin, {method:'PUT',headers:custom,body:JSON.stringify({version,profile:value})})
    const forbidden = await save(initial.version, profile, {...headers,origin:'https://other.example'})
    assert.equal(forbidden.status, 403)
    assert.equal((await save(initial.version, profile, {'content-type':'application/json'})).status, 403)
    assert.equal((await save(initial.version, {...profile,days_per_week:8})).status, 422)
    const simultaneous = await Promise.all([save(initial.version), save(initial.version, {...profile,days_per_week:3})])
    assert.deepEqual(simultaneous.map(r => r.status).sort(), [200,409])
    const stored = JSON.parse(await readFile(join(dir,'profile.json'),'utf8'))
    assert.ok([2,3].includes(stored.days_per_week))
    const modelProfile = await runBridge('internship_profile',{},config)
    assert.equal(modelProfile.profile.stage, profile.stage)
    assert.equal(modelProfile.profile_form_url, '/dsh-internship/profile.html')
    assert.ok(modelProfile.missing_fields.includes('实习月数'))
    const before = await readFile(join(dir,'profile.json'),'utf8')
    const imported = await fetch(origin + '/resume',{method:'POST',headers,body:JSON.stringify({name:'虚拟简历.txt',data:Buffer.from('学历：本科大三\n已掌握技能：Python、SQL\n目标城市：上海').toString('base64')})}).then(r=>r.json())
    assert.equal(imported.ok,true)
    assert.equal(imported.suggestions.stage,'本科大三')
    assert.equal(await readFile(join(dir,'profile.json'),'utf8'),before)
    const html = await fetch(origin + '/profile.html').then(r=>r.text())
    assert.ok(html.includes('保存档案'))
    const version = modelProfile.version
    const draft = await fetch(origin,{method:'PUT',headers,body:JSON.stringify({profile:{...stored,cities:['广州 深圳 杭州']},version,prepare:true})}).then(r=>r.json())
    assert.equal(draft.confirmation_required,true)
    assert.equal(await readFile(join(dir,'profile.json'),'utf8'),before)
    const draftRead = await fetch(origin + '?draft=' + draft.draft_id).then(r=>r.json())
    assert.deepEqual(draftRead.profile.cities,['广州','深圳','杭州'])
    assert.equal((await fetch(origin,{method:'PUT',headers,body:JSON.stringify({draft_id:draft.draft_id,confirmation:'user_confirmed',profile:{}})})).status,400)
    const approved = await fetch(origin,{method:'PUT',headers,body:JSON.stringify({draft_id:draft.draft_id,confirmation:'user_confirmed'})}).then(r=>r.json())
    assert.equal(approved.saved,true)
    assert.deepEqual(approved.profile.cities,['广州','深圳','杭州'])
    assert.ok(approved.changes.some(change=>change.field==='cities'))
    const staleDraft = await runBridge('internship_profile_propose',{base_version:approved.version,changes:{stage:'虚拟大四'},reason:'并发修改检查'},config)
    const competing = await Promise.all([
      runBridge('internship_profile_apply',{draft_id:staleDraft.draft_id,confirmation:'user_confirmed'},config),
      runProfileWeb({action:'save',version:approved.version,profile:{...approved.profile,stage:'虚拟研究生'}},config)
    ])
    assert.equal(competing.filter(r=>r.ok && r.saved).length,1)
    assert.equal(competing.filter(r=>r.conflict).length,1)
  } finally {
    server.closeAllConnections()
    await new Promise(resolve => server.close(resolve))
    await rm(dir,{recursive:true,force:true})
  }
})
