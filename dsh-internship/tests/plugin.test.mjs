import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtemp, rm, writeFile} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {apply, runBridge} from '../src/index.js'

test('raw DSH registration and real Python subprocess', async () => {
  const dir = await mkdtemp(join(tmpdir(),'internship-plugin-'))
  try {
    const tools=[]
    apply({tools:{register:t=>tools.push(t)}},{dataDir:dir})
    assert.equal(tools.length,13)
    assert.ok(tools.every(t => typeof t.description === 'string'))
    const signal=new AbortController().signal
    for (const name of ['internship_status','internship_profile']) {
      const tool=tools.find(t=>t.name===name)
      const value=await tool.execute({}, {signal})
      assert.equal(value.ok,true)
      assert.equal(tool.output.render({},value)[0].type,'text')
    }
    const plan=await runBridge('internship_candidates_plan',{extra_queries:['上海 后端 暑期 实习']},{dataDir:dir},signal)
    assert.equal(plan.ok,true)
    assert.ok(plan.queries.includes('上海 后端 暑期 实习'))
    const added=await runBridge('internship_candidates_add',{query:'上海 后端 暑期 实习',urls:[],error:''},{dataDir:dir},signal)
    assert.equal(added.ok,true)
    assert.equal(added.search.search_execution_verified,false)
    const invalid=await runBridge('internship_list',{offset:true},{dataDir:dir},signal)
    assert.equal(invalid.ok,false)
    const missing=await runBridge('internship_get',{job_id:'不存在'},{dataDir:dir},signal)
    assert.equal(missing.ok,false)
  } finally {await rm(dir,{recursive:true,force:true})}
})
test('pre-cancelled calls do not start subprocess',async()=> {
  const control=new AbortController(); control.abort()
  await assert.rejects(runBridge('internship_status',{}, {},control.signal),/取消/)
})
test('missing Python executable gives actionable error',async()=> {
  await assert.rejects(runBridge('internship_status',{}, {python:'/nonexistent/python'}),/Python/)
})
test('in-flight cancellation kills subprocess',async()=> {
  const dir=await mkdtemp(join(tmpdir(),'internship-cancel-'))
  try {
    const python=join(dir,'slow-python')
    await writeFile(python,'#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n',{mode:0o700})
    const controller=new AbortController()
    const pending=runBridge('internship_status',{}, {python,dataDir:dir},controller.signal)
    const timer=setTimeout(()=>controller.abort(),100)
    try {await assert.rejects(pending,/取消/)} finally {clearTimeout(timer)}
  } finally {await rm(dir,{recursive:true,force:true})}
})
