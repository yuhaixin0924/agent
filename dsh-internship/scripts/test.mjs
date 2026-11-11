import { spawnSync } from 'node:child_process'
const python = process.platform === 'win32' ? 'python' : 'python3'
for (const [command, args] of [[python,['-X','utf8','-m','unittest','discover','-s','tests','-v']],
  [process.execPath,['--test','tests/plugin.test.mjs','tests/profile-web.test.mjs']]]) {
  const result = spawnSync(command,args,{stdio:'inherit'})
  if (result.error) {console.error(result.error.message); process.exit(1)}
  if (result.status !== 0) process.exit(result.status || 1)
}
