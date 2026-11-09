"""网络适配：GET 可重试，模型 POST 不自动重试。"""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NetworkError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 模型请求携带凭据，禁止跟随重定向到其他地址。
        return None


def request_json(url, *, payload=None, api_key=None, timeout=20, max_bytes=2_000_000):
    headers = {"Accept": "application/json", "User-Agent": "LearningRadar/0.1"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    attempts = 2 if payload is None else 1
    for attempt in range(attempts):
        try:
            request = Request(url, data=data, headers=headers)
            with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
                raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise NetworkError(f"响应超过 {max_bytes} 字节限制，停止读取。")
            return json.loads(raw.decode("utf-8"))
        except HTTPError as error:
            status = error.code
            error.close()
            if payload is None and status in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1)
                continue
            hint = {
                401: "请检查 API Key。",
                403: "请检查访问权限。",
                404: "请检查接口地址和模型名。",
                429: "服务限流或额度不足，请稍后重试。",
            }.get(status, "请检查服务状态。")
            # 不打印请求头、完整 URL 或服务端正文，避免输出凭据。
            raise NetworkError(f"HTTP {status}：{hint}") from None
        except (URLError, TimeoutError, OSError):
            if attempt + 1 < attempts:
                time.sleep(1)
                continue
            raise NetworkError("网络连接失败或超时，请检查网络和接口地址。") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise NetworkError("服务器没有返回有效的 UTF-8 JSON。") from None
