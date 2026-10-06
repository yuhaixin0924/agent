import copy
import json
import unittest
from unittest.mock import patch

from radar_agent.agent import Agent
from radar_agent.demo import DemoClient, ITEMS, fixture_fetch
from radar_agent.http import NetworkError
from radar_agent.llm import ChatClient
from radar_agent.tools import HackerNewsTools, TOOL_SCHEMAS


def tool_call(name, arguments, call_id="call_1"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": arguments}}


class SequenceClient:
    def __init__(self, messages):
        self.responses = iter(messages)
        self.histories = []

    def complete(self, messages, tools, *, require_tool=False):
        self.histories.append(copy.deepcopy(messages))
        return {"message": next(self.responses), "usage": {}}


class ToolTests(unittest.TestCase):
    def test_html_and_fields(self):
        tools = HackerNewsTools(fixture_fetch)
        post = tools.get_post(1001)
        self.assertEqual(post["text"], "示例：通过工具调用循环搭建小型 Agent。")
        self.assertFalse(post["external_article_fetched"])
        self.assertEqual(post["url"], post["discussion_url"])

    def test_invalid_parameters_never_access_network(self):
        requests = []
        tools = HackerNewsTools(lambda url: requests.append(url))
        for name, arguments in [
            ("get_posts", {"feed": "../private", "limit": 1, "offset": 0}),
            ("get_posts", {"feed": "new", "limit": True, "offset": 0}),
            ("get_posts", {"feed": "new", "limit": 1000, "offset": 0}),
            ("get_post", {"post_id": "1001"}),
            ("get_post", {"post_id": 1001, "url": "https://example.com"}),
            ("get_comments", {"post_id": 1001}),
            ("run_shell", {"command": "anything"}),
            ("get_post", [1001]),
        ]:
            with self.subTest(name=name, arguments=arguments):
                self.assertFalse(tools.execute(name, arguments)["ok"])
        self.assertEqual(requests, [])

    def test_partial_failure_deleted_and_duplicate(self):
        def fetch(url):
            if "/item/" not in url:
                return [1001, 1001, 9999, 1002]
            if "9999.json" in url:
                raise NetworkError("timeout")
            if "1002.json" in url:
                return {"id": 1002, "deleted": True}
            return ITEMS[1001]
        result = HackerNewsTools(fetch).get_posts(limit=4)
        self.assertEqual([p["id"] for p in result["posts"]], [1001])
        self.assertEqual(result["errors"], [{"post_id": 9999, "error": "timeout"}])

    def test_caching_and_pagination(self):
        requests = []
        def fetch(url):
            requests.append(url)
            return fixture_fetch(url)
        tools = HackerNewsTools(fetch)
        first = tools.get_posts(limit=1)
        self.assertEqual(first["next_offset"], 1)
        self.assertEqual(tools.get_posts(limit=1, offset=1)["posts"][0]["id"], 1002)
        tools.get_post(1001)
        tools.get_posts(limit=1)
        self.assertEqual(len(requests), 3)

    def test_comments_skip_deleted_and_include_replies(self):
        data = copy.deepcopy(ITEMS)
        data[1001]["kids"] = [2001, 2002]
        data[2001]["kids"] = [2003]
        data[2002] = {"id": 2002, "type": "comment", "deleted": True}
        data[2003] = {"id": 2003, "type": "comment", "parent": 2001,
                      "text": "<p>A &amp; B</p>"}
        tools = HackerNewsTools(lambda url: data.get(int(url.rsplit("/", 1)[1].split(".")[0])))
        result = tools.get_comments(1001, limit=5)
        self.assertEqual([c["id"] for c in result["comments"]], [2001, 2003])
        self.assertEqual(result["comments"][1]["depth"], 1)
        self.assertEqual(result["comments"][1]["text"], "A & B")
        self.assertTrue(result["sample_only"])


class AgentTests(unittest.TestCase):
    def test_demo_runs_actual_dispatch_loop(self):
        events = []
        agent = Agent(DemoClient(), HackerNewsTools(fixture_fetch), emit=events.append)
        result = agent.run("演示")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["model_steps"], 3)
        self.assertEqual(result["tool_calls"], 2)
        self.assertEqual([e["tool"] for e in events if e["event"] == "tool_start"],
                         ["get_posts", "get_comments"])
        self.assertIn("离线演示", result["answer"])

    def test_error_is_returned_to_model_then_repaired(self):
        client = SequenceClient([
            {"role": "assistant", "content": None, "tool_calls": [
                tool_call("get_post", "{broken")
            ]},
            {"role": "assistant", "content": None, "tool_calls": [
                tool_call("get_post", '{"post_id":1001}', "call_2")
            ]},
            {"role": "assistant", "content": "有证据的回答"},
        ])
        result = Agent(client, HackerNewsTools(fixture_fetch)).run("任务")
        self.assertEqual(result["status"], "completed")
        returned_error = json.loads(client.histories[1][-1]["content"])
        self.assertFalse(returned_error["ok"])
        self.assertEqual(client.histories[2][-1]["tool_call_id"], "call_2")
        self.assertTrue(json.loads(client.histories[2][-1]["content"])["ok"])

    def test_call_budget_keeps_every_tool_reply(self):
        client = SequenceClient([
            {"role": "assistant", "content": None, "tool_calls": [
                tool_call("get_post", '{"post_id":1001}', "a"),
                tool_call("get_post", '{"post_id":1002}', "b"),
            ]},
            {"role": "assistant", "content": "根据已读帖子回答"},
        ])
        result = Agent(client, HackerNewsTools(fixture_fetch), max_tool_calls=1).run("任务")
        self.assertEqual(result["tool_calls"], 1)
        replies = [m for m in client.histories[1] if m["role"] == "tool"]
        self.assertEqual([m["tool_call_id"] for m in replies], ["a", "b"])
        self.assertFalse(json.loads(replies[1]["content"])["ok"])

    def test_round_budget_not_reported_as_success(self):
        result = Agent(DemoClient(), HackerNewsTools(fixture_fetch), max_steps=1).run("任务")
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual(result["model_steps"], 1)

    def test_answer_without_observation_is_flagged(self):
        client = SequenceClient([{"role": "assistant", "content": "未经取证的回答"}])
        result = Agent(client, HackerNewsTools(fixture_fetch)).run("任务")
        self.assertEqual(result["status"], "no_evidence")

    def test_duplicate_call_ids_rejected_before_execution(self):
        client = SequenceClient([{"role": "assistant", "tool_calls": [
            tool_call("get_post", '{"post_id":1001}'),
            tool_call("get_post", '{"post_id":1002}'),
        ]}])
        with self.assertRaisesRegex(ValueError, "重复"):
            Agent(client, HackerNewsTools(fixture_fetch)).run("任务")


class ClientTests(unittest.TestCase):
    @patch("radar_agent.llm.request_json")
    def test_chat_envelope_and_secret_not_in_payload(self, request):
        request.return_value = {"choices": [{"message": {"role": "assistant", "content": "结果"},
                                             "finish_reason": "stop"}], "usage": {"total_tokens": 9}}
        client = ChatClient("test-key", "https://example.com/v1/", "test-model")
        response = client.complete([{"role": "user", "content": "任务"}], TOOL_SCHEMAS, require_tool=True)
        url = request.call_args.args[0]
        kwargs = request.call_args.kwargs
        self.assertEqual(url, "https://example.com/v1/chat/completions")
        self.assertEqual(kwargs["payload"]["tool_choice"], "required")
        self.assertNotIn("test-key", json.dumps(kwargs["payload"]))
        self.assertNotIn("thinking", kwargs["payload"])
        self.assertEqual(response["usage"]["total_tokens"], 9)

    @patch("radar_agent.llm.request_json")
    def test_deepseek_disables_thinking_in_all_rounds(self, request):
        request.return_value = {"choices": [{"message": {"role": "assistant", "content": "结果"},
                                             "finish_reason": "stop"}]}
        client = ChatClient("test-key", "https://api.deepseek.com", "deepseek-flash")
        for require_tool in (True, False):
            with self.subTest(require_tool=require_tool):
                client.complete([], TOOL_SCHEMAS, require_tool=require_tool)
                payload = request.call_args.kwargs["payload"]
                self.assertEqual(payload["thinking"], {"type": "disabled"})
                self.assertEqual(payload["tool_choice"], "required" if require_tool else "auto")
                self.assertEqual(request.call_args.args[0], "https://api.deepseek.com/chat/completions")

    @patch("radar_agent.llm.request_json")
    def test_truncated_output_is_rejected(self, request):
        request.return_value = {"choices": [{"finish_reason": "length", "message": {
            "role": "assistant", "content": "半句"}}]}
        with self.assertRaisesRegex(ValueError, "截断"):
            ChatClient("key", "https://example.com", "model").complete([], TOOL_SCHEMAS)

    def test_remote_plain_http_and_credentials_in_url_rejected(self):
        for url in ("http://example.com", "https://key@example.com", "https://example.com?key=secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                ChatClient("key", url, "model")
        ChatClient("local", "http://localhost:1234/v1", "local-model")


if __name__ == "__main__":
    unittest.main()
