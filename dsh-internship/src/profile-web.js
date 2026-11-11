import { profilePage } from './profile-page.js'

function send(res, status, value) {
  res.statusCode = status
  res.setHeader('content-type', 'application/json; charset=utf-8')
  res.setHeader('cache-control', 'no-store')
  res.setHeader('x-content-type-options', 'nosniff')
  res.end(JSON.stringify(value))
}

function sameOrigin(req) {
  try {
    const expected = new URL(`http://${req.headers.host}`)
    const origin = new URL(req.headers.origin)
    return ['http:', 'https:'].includes(origin.protocol) && origin.host === expected.host
  } catch { return false }
}

export function serveProfilePage(req, res) {
  if (!['GET', 'HEAD'].includes(req.method)) { res.statusCode = 405; res.end(); return }
  res.setHeader('content-type', 'text/html; charset=utf-8')
  res.setHeader('cache-control', 'no-store')
  res.setHeader('x-content-type-options', 'nosniff')
  res.setHeader('content-security-policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'")
  res.end(req.method === 'HEAD' ? undefined : profilePage)
}

export function createProfileHandler(runProfile) {
  // Keep saves in order so two browser tabs cannot silently overwrite each other.
  let saves = Promise.resolve()
  return async (req, res) => {
    try {
      if (!['GET', 'PUT'].includes(req.method)) { send(res, 405, {ok: false, error: '不支持的请求方式'}); return }
      if (req.headers['sec-fetch-site'] === 'cross-site' || (req.headers.origin && !sameOrigin(req))) {
        send(res, 403, {ok: false, error: '仅允许从当前 Harness 页面访问档案'}); return
      }
      if (req.method === 'GET') {
        const draft_id = new URL(req.url, 'http://local').searchParams.get('draft')
        const result = await runProfile(draft_id ? {action: 'draft_read', draft_id} : {action: 'read'})
        send(res, result.ok ? 200 : result.conflict ? 409 : 422, result)
        return
      }
      if (!sameOrigin(req) || req.headers['x-internship-profile'] !== '1') {
        send(res, 403, {ok: false, error: '请通过个人档案表单保存'}); return
      }
      if (req.headers['content-type']?.split(';')[0].trim() !== 'application/json') {
        send(res, 415, {ok: false, error: '需要 JSON 格式'}); return
      }
      let size = 0
      const chunks = []
      for await (const chunk of req) {
        size += chunk.length
        if (size > 40000) { send(res, 413, {ok: false, error: '档案内容过长'}); return }
        chunks.push(chunk)
      }
      let body
      try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')) }
      catch { send(res, 400, {ok: false, error: '无法解析档案内容'}); return }
      if (!body || typeof body !== 'object' || Array.isArray(body) ||
          Object.keys(body).some(key => !['profile', 'version', 'prepare', 'draft_id', 'confirmation', 'restore'].includes(key))) {
        send(res, 400, {ok: false, error: '档案请求格式不正确'}); return
      }
      let request
      if (body.draft_id) {
        if (Object.keys(body).some(key => !['draft_id', 'confirmation'].includes(key))) {send(res, 400, {ok:false,error:'确认时不能更改草稿内容'}); return}
        request = {action: 'apply', draft_id: body.draft_id, confirmation: body.confirmation}
      } else if (body.restore === true) {
        if (Object.keys(body).some(key => !['restore', 'version'].includes(key))) {send(res,400,{ok:false,error:'恢复请求无效'}); return}
        request = {action: 'restore', version: body.version}
      } else {
        request = {action: body.prepare === true ? 'prepare' : 'save', profile: body.profile, version: body.version}
      }
      const pending = saves.then(() => runProfile(request))
      saves = pending.catch(() => {})
      const result = await pending
      send(res, result.ok ? 200 : result.conflict ? 409 : 422, result)
    } catch {
      send(res, 503, {ok: false, error: '档案服务暂不可用，请检查 Python 和数据目录权限后重试。'})
    }
  }
}

export function createResumeHandler(runResume) {
  return async (req, res) => {
    try {
      if (req.method !== 'POST') {send(res, 405, {ok: false, error: '不支持的请求方式'}); return}
      if (!sameOrigin(req) || req.headers['sec-fetch-site'] === 'cross-site' || req.headers['x-internship-profile'] !== '1') {
        send(res, 403, {ok: false, error: '请通过个人档案页面导入简历'}); return
      }
      if (req.headers['content-type']?.split(';')[0].trim() !== 'application/json') {
        send(res, 415, {ok: false, error: '需要 JSON 格式'}); return
      }
      let size = 0
      const chunks = []
      for await (const chunk of req) {
        size += chunk.length
        if (size > 6_000_000) {send(res, 413, {ok: false, error: '请选择 4 MB 以内的简历'}); return}
        chunks.push(chunk)
      }
      let request
      try {request = JSON.parse(Buffer.concat(chunks).toString('utf8'))}
      catch {send(res, 400, {ok: false, error: '简历请求格式不正确'}); return}
      const result = await runResume(request)
      send(res, result.ok ? 200 : 422, result)
    } catch {send(res, 503, {ok: false, error: '简历提取失败，请检查 Python 环境或尝试其他文件格式。'})}
  }
}
