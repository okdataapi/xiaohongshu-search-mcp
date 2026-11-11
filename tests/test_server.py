"""Starts server.py as an MCP client would (stdio) against a local mock of the okdata API."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mock_okdata import TEST_KEY, MockOkdata, error, ok  # noqa: E402

NOTE = "6650a1b2000000001e00abcd"
USER = "5f1234567890abcdef123456"


def note(i: int) -> Dict[str, Any]:
    return {"id": f"{i:024x}", "title": f"笔记{i}", "text": "很长的正文" * 100, "url": f"https://www.xiaohongshu.com/explore/{i:024x}",
            "type": "image", "author": {"id": USER, "name": "博主"}, "metrics": {"likes": i, "favorites": 2, "comments": 3, "shares": 4},
            "published_at": "2026-11-01T00:00:00Z", "images": ["https://img/1.jpg"], "hashtags": ["露营"]}


class ServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api = MockOkdata({
            "/v1/xiaohongshu/notes/search": lambda q: (200, ok("s", items=[note(1), note(2)], next_cursor="c2", amount="0.02")),
            "/v1/xiaohongshu/notes/get": lambda q: (200, ok("g", item=note(7), amount="0.02")) if q.get("id") or "xhslink" in q.get("url", "")
            else (404, error("not_found")),
            "/v1/xiaohongshu/notes/comments/list": lambda q: (200, ok("c", items=[{"text": "好用", "likes": 9, "author": {"name": "路人"},
                                                                                   "ip_location": "上海"}], amount="0.02")),
            "/v1/xiaohongshu/users/get": lambda q: (200, ok("u", item={"id": USER, "name": "博主", "followers": 1000}, amount="0.02")),
            "/v1/xiaohongshu/users/notes/list": lambda q: (200, ok("un", items=[note(3)], amount="0.02")),
            "/v1/xiaohongshu/trends/list": lambda q: (200, ok("t", items=[{"rank": 1, "name": "初雪", "heat": 10, "url": None}], amount="0.02")),
        })

    def tearDown(self) -> None:
        self.api.close()

    def session(self, messages: List[Dict[str, Any]], key: str = TEST_KEY) -> List[Dict[str, Any]]:
        env = {**os.environ, "OKDATA_BASE_URL": self.api.url, "OKDATA_API_KEY": key, "NO_PROXY": "*"}
        proc = subprocess.run([sys.executable, str(HERE.parent / "server.py")], input="\n".join(json.dumps(m) for m in messages) + "\n",
                              capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]

    def call_tool(self, name: str, arguments: Dict[str, Any], key: str = TEST_KEY) -> Dict[str, Any]:
        out = self.session([{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}], key)
        return out[0]["result"]

    def test_handshake_and_tool_list(self) -> None:
        out = self.session([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
            {"jsonrpc": "2.0", "id": 4, "method": "resources/list"},
        ])
        self.assertEqual([m["id"] for m in out], [1, 2, 3, 4])  # the notification got no answer
        self.assertEqual(out[0]["result"]["protocolVersion"], "2025-06-18")
        names = [t["name"] for t in out[1]["result"]["tools"]]
        self.assertEqual(names, ["search_notes", "get_note", "note_comments", "get_user", "user_notes", "hot_topics"])
        self.assertEqual(out[3]["error"]["code"], -32601)
        self.assertEqual(self.api.requests, [])  # listing tools costs nothing

    def test_unknown_protocol_version_gets_ours(self) -> None:
        out = self.session([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}}])
        self.assertEqual(out[0]["result"]["protocolVersion"], "2025-11-25")

    def test_search_returns_short_notes_and_cost(self) -> None:
        res = self.call_tool("search_notes", {"query": "露营 装备", "sort": "popular"})
        data = json.loads(res["content"][0]["text"])
        self.assertEqual(len(data["notes"]), 2)
        self.assertLessEqual(len(data["notes"][0]["text"]), 161)
        self.assertEqual((data["next_cursor"], data["cost_usd"]), ("c2", 0.02))
        req = self.api.requests[-1]
        self.assertEqual(req["query"], {"query": "露营 装备", "sort": "popular", "view": "compact"})
        self.assertEqual(req["headers"]["authorization"], f"Bearer {TEST_KEY}")
        self.assertIn("idempotency-key", req["headers"])

    def test_get_note_by_share_text(self) -> None:
        res = self.call_tool("get_note", {"note": "看看这篇 http://xhslink.com/a/AbCd 复制本条信息打开小红书"})
        data = json.loads(res["content"][0]["text"])
        self.assertEqual(data["note"]["hashtags"], ["露营"])
        self.assertEqual(self.api.requests[-1]["query"]["url"], "http://xhslink.com/a/AbCd")

    def test_comments_by_link_uses_the_id_without_extra_call(self) -> None:
        res = self.call_tool("note_comments", {"note": f"https://www.xiaohongshu.com/explore/{NOTE}?xsec_token=abc"})
        data = json.loads(res["content"][0]["text"])
        self.assertEqual(data["comments"][0]["text"], "好用")
        self.assertEqual([r["path"] for r in self.api.requests], ["/v1/xiaohongshu/notes/comments/list"])
        self.assertEqual(self.api.requests[0]["query"]["id"], NOTE)

    def test_comments_by_short_link_resolves_first(self) -> None:
        res = self.call_tool("note_comments", {"note": "http://xhslink.com/a/AbCd"})
        data = json.loads(res["content"][0]["text"])
        self.assertEqual(data["cost_usd"], 0.04)
        self.assertEqual([r["path"] for r in self.api.requests], ["/v1/xiaohongshu/notes/get", "/v1/xiaohongshu/notes/comments/list"])

    def test_user_tools_and_hot_topics(self) -> None:
        user = json.loads(self.call_tool("get_user", {"user": f"https://www.xiaohongshu.com/user/profile/{USER}"})["content"][0]["text"])
        self.assertEqual(user["user"]["followers"], 1000)
        notes = json.loads(self.call_tool("user_notes", {"user": USER})["content"][0]["text"])
        self.assertEqual(notes["user_id"], USER)
        topics = json.loads(self.call_tool("hot_topics", {})["content"][0]["text"])
        self.assertEqual(topics["topics"][0]["name"], "初雪")

    def test_errors_come_back_as_tool_errors(self) -> None:
        res = self.call_tool("get_note", {"note": NOTE[:-1] + "x"})  # not an id, not a link
        self.assertTrue(res["isError"])
        self.assertIn("invalid_params", res["content"][0]["text"])
        res = self.call_tool("search_notes", {"query": "x"}, key="")
        self.assertTrue(res["isError"])
        self.assertIn("src=gh-xiaohongshu-search-mcp", res["content"][0]["text"])
        self.assertEqual(self.api.requests, [])
        res = self.call_tool("search_notes", {"query": "x"}, key="okd_wrong")
        self.assertIn("unauthorized", res["content"][0]["text"])
        self.assertIn("未扣费", res["content"][0]["text"])

    def test_odd_input_and_odd_answers_never_stop_the_server(self) -> None:
        self.api.routes["/v1/xiaohongshu/users/get"] = lambda q: (200, ok("u", item={"name": "no id here"}))
        self.api.routes["/v1/xiaohongshu/trends/list"] = lambda q: (200, "not an envelope")
        out = self.session([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_note", "arguments": ["not", "a", "dict"]}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_note", "arguments": {"note": 12345}}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": "nonsense"},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "user_notes", "arguments": {"user": "http://xhslink.com/u/1"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "hot_topics", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 6, "method": "ping"},
        ])
        self.assertEqual([m["id"] for m in out], [1, 2, 3, 4, 5, 6])
        self.assertTrue(out[0]["result"]["isError"])
        self.assertIn("invalid_params", out[1]["result"]["content"][0]["text"])
        self.assertEqual(out[2]["error"]["code"], -32602)
        self.assertIn("bad_response", out[3]["result"]["content"][0]["text"])  # answer without an id
        self.assertIn("是否扣费未知", out[4]["result"]["content"][0]["text"])  # body that is not an envelope
        self.assertEqual(out[5]["result"], {})

    def test_bad_json_and_unknown_tool(self) -> None:
        env = {**os.environ, "OKDATA_BASE_URL": self.api.url, "NO_PROXY": "*"}
        proc = subprocess.run([sys.executable, str(HERE.parent / "server.py")], input="{not json\n" + json.dumps(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}}) + "\n", capture_output=True, text=True, env=env, timeout=30)
        lines = [json.loads(x) for x in proc.stdout.splitlines()]
        self.assertEqual(lines[0]["error"]["code"], -32700)
        self.assertEqual(lines[1]["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
