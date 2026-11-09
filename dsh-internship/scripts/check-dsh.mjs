// Run with Electron's Node mode so app.asar dependencies resolve.
import {pathToFileURL} from 'node:url'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {apply} from '../src/index.js'
const resources=process.env.DSH_APP_RESOURCES || '/Applications/DeepSeek Harness.app/Contents/Resources'
const sdk=await import(pathToFileURL(join(resources,'app.asar/dsh/node_modules/@deepseek-ai/dsh-tools/lib/index.js')))
const dir=await mkdtemp(join(tmpdir(),'internship-sdk-'))
try {
  const tools=[]
  apply({tools:{register:tool=>{
    sdk.assertObjectJsonSchema(tool.parameters)
    sdk.assertSupportedJsonSchema(tool.output.schema)
    tools.push(tool)
  }}},{dataDir:dir})
  const tool=tools.find(t=>t.name==='internship_status')
  const result=await tool.execute({}, {signal:new AbortController().signal})
  sdk.validateJsonSchemaValue(result,tool.output.schema)
  if (!result.ok) throw new Error('Python bridge failed')
  console.log(JSON.stringify({sdkSchemaAccepted:tools.length,pythonBridge:result.ok,
    note:'SDK schema + subprocess check; not a live DSH conversation'},null,2))
} finally {await rm(dir,{recursive:true,force:true})}
