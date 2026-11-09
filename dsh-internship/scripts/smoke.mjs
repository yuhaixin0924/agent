// No API key, network or user data: verifies native tool contract + Python bridge.
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {apply} from '../src/index.js'
const dir=await mkdtemp(join(tmpdir(),'internship-smoke-'))
try {
  const tools=[]
  apply({tools:{register:t=>tools.push(t)}},{dataDir:dir})
  const result=await tools.find(t=>t.name==='internship_status').execute({}, {signal:new AbortController().signal})
  if (!result.ok || tools.length!==7) throw new Error('smoke failed')
  console.log(JSON.stringify({registered:tools.map(t=>t.name),result},null,2))
} finally {await rm(dir,{recursive:true,force:true})}
