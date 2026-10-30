"""实习助手的 Chat Completions 模型适配；无需安装 SDK。"""

import os
from pathlib import Path
from urllib.parse import urlsplit

from .http import request_json

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    """支持简单 KEY=value 格式；已有环境变量优先，不做变量展开。"""
    path = ROOT / ".env"
    if not path.exists():
        return
    allowed = {"LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name in allowed:
            os.environ.setdefault(name, value)


class ChatClient:
    def __init__(self, api_key, base_url, model):
        parsed = urlsplit(base_url)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (not parsed.hostname or not (parsed.scheme == "https" or local_http)
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("LLM_BASE_URL 请使用 HTTPS；本机服务可用 HTTP，且不要包含凭据或查询参数。")
        self.api_key, self.model = api_key, model
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.is_deepseek = parsed.hostname == "api.deepseek.com"

    @classmethod
    def from_env(cls):
        load_env()
        values = [os.environ.get(name, "").strip()
                  for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")]
        if not all(values):
            raise ValueError("请在 .env 配置 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL。")
        return cls(*values)

    def complete(self, messages, tools, *, require_tool=False):
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "tool_choice": "required" if require_tool else "auto"}
        if self.is_deepseek:
            # DeepSeek 默认开启思考；思考模式不接受 tool_choice=required。
            # 这一版固定使用非思考模式，保持首轮取证和后续调用协议一致。
            payload["thinking"] = {"type": "disabled"}
        response = request_json(self.url, payload=payload, api_key=self.api_key, timeout=60)
        try:
            choice = response["choices"][0]
            if choice.get("finish_reason") in {"length", "content_filter"}:
                raise ValueError("模型输出被截断或过滤，本轮不能作为完整结果。")
            message = choice["message"]
            if not isinstance(message, dict) or message.get("role") != "assistant":
                raise ValueError("模型没有返回合法的 assistant 消息。")
            # 只回传对话字段，不回传 provider 的额外元数据。
            clean = {key: message[key] for key in
                     ("role", "content", "tool_calls", "reasoning_content") if key in message}
            return {"message": clean, "usage": response.get("usage", {})}
        except (KeyError, IndexError, TypeError):
            raise ValueError("模型接口响应不符合 Chat Completions 格式；请检查提供商兼容性。") from None
