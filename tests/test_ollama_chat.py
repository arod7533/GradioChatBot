"""Agent tests with mocked Ollama responses: no model or server needed."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ollama_chat import MAX_MESSAGE_LENGTH, build_messages, chat


def stream(*events):
    return io.BytesIO(b"".join(json.dumps(event).encode() + b"\n" for event in events))


def tool_call(name, arguments):
    return {"function": {"name": name, "arguments": arguments}}


class BuildMessagesTests(unittest.TestCase):
    def test_filters_tool_ui_messages_and_caps_history(self):
        history = [{"role": "user", "content": "old"}] * 20
        history += [
            {
                "role": "assistant",
                "content": "tool result",
                "metadata": {"title": "Tool"},
            },
            {"role": "assistant", "content": "A" * (MAX_MESSAGE_LENGTH + 20)},
            {"role": "tool", "content": "ignored"},
        ]
        messages = build_messages("B" * (MAX_MESSAGE_LENGTH + 20), history)
        self.assertEqual(messages[0]["role"], "system")
        self.assertLessEqual(len(messages), 14)
        self.assertEqual(messages[-2], {"role": "assistant", "content": "A" * 4000})
        self.assertEqual(messages[-1], {"role": "user", "content": "B" * 4000})
        self.assertNotIn("tool result", [item["content"] for item in messages])


class AgentTests(unittest.TestCase):
    @patch("ollama_chat.urlopen")
    def test_calls_tool_then_uses_result_to_answer(self, urlopen):
        call = tool_call(
            "search_flights",
            {"origin": "SFO", "destination": "JFK", "date": "2026-12-05"},
        )
        urlopen.side_effect = [
            stream({"message": {"tool_calls": [call]}}, {"done": True}),
            stream({"message": {"content": "Two demo flights"}}, {"done": True}),
        ]
        events = list(chat("Find SFO to JFK", []))
        self.assertEqual([kind for kind, _ in events], ["tool", "answer"])
        self.assertEqual(events[0][1]["result"]["count"], 2)
        self.assertEqual(events[1][1], "Two demo flights")
        first = json.loads(urlopen.call_args_list[0].args[0].data)
        second = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(first["model"], "qwen3.5:9b")
        self.assertFalse(first["think"])
        self.assertTrue(first["stream"])
        self.assertEqual(len(first["tools"]), 4)
        self.assertEqual(second["messages"][-1]["role"], "tool")
        self.assertEqual(json.loads(second["messages"][-1]["content"])["count"], 2)

    @patch("ollama_chat.urlopen")
    def test_multiple_tools_and_bounded_followup(self, urlopen):
        urlopen.side_effect = [
            stream(
                {
                    "message": {
                        "tool_calls": [
                            tool_call("lookup_booking", {"reference": "AX7K2Q"}),
                            tool_call(
                                "get_flight_status", {"flight_number": "AST 218"}
                            ),
                        ]
                    }
                },
                {"done": True},
            ),
            stream(
                {"message": {"content": "Your demo flight is scheduled."}},
                {"done": True},
            ),
        ]
        events = list(chat("Check my booking and flight", []))
        self.assertEqual([kind for kind, _ in events], ["tool", "tool", "answer"])
        self.assertEqual(events[0][1]["result"]["seat"], "14A")
        self.assertEqual(events[1][1]["result"]["status"], "Scheduled")
        followup = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(
            [item["role"] for item in followup["messages"][-3:]],
            ["assistant", "tool", "tool"],
        )

    @patch("ollama_chat.urlopen")
    def test_sequential_tool_decisions_have_a_hard_limit(self, urlopen):
        urlopen.side_effect = [
            stream(
                {
                    "message": {
                        "tool_calls": [
                            tool_call("lookup_booking", {"reference": "AX7K2Q"})
                        ]
                    }
                },
                {"done": True},
            ),
            stream(
                {
                    "message": {
                        "tool_calls": [
                            tool_call("get_flight_status", {"flight_number": "AST 218"})
                        ]
                    }
                },
                {"done": True},
            ),
            stream(
                {"message": {"content": "Demo flight is scheduled."}}, {"done": True}
            ),
        ]
        events = list(chat("Check booking AX7K2Q and its flight status.", []))
        self.assertEqual([kind for kind, _ in events], ["tool", "tool", "answer"])
        self.assertNotIn("tools", json.loads(urlopen.call_args_list[2].args[0].data))
        self.assertEqual(urlopen.call_count, 3)

    @patch("ollama_chat.urlopen")
    def test_streams_direct_answer(self, urlopen):
        urlopen.return_value = stream(
            {"message": {"content": "Hello"}},
            {"message": {"content": " there"}},
            {"done": True},
        )
        self.assertEqual(
            list(chat("Hi", [])), [("answer", "Hello"), ("answer", "Hello there")]
        )

    @patch("ollama_chat.urlopen", return_value=stream({"done": True}))
    def test_empty_reply(self, _urlopen):
        self.assertEqual(
            list(chat("Hi", []))[-1],
            ("answer", "The model returned an empty response."),
        )

    @patch("ollama_chat.urlopen", return_value=stream({"error": "internal detail"}))
    def test_stream_error_does_not_expose_internal_detail(self, _urlopen):
        self.assertIn("unexpected response", list(chat("Hi", []))[-1][1])

    @patch("ollama_chat.urlopen", return_value=io.BytesIO(b"invalid json\n"))
    def test_malformed_response(self, _urlopen):
        self.assertIn("unexpected response", list(chat("Hi", []))[-1][1])

    @patch("ollama_chat.urlopen", side_effect=URLError("connection refused"))
    def test_ollama_unavailable(self, _urlopen):
        self.assertIn("Start the Ollama app", list(chat("Hi", []))[-1][1])

    @patch("ollama_chat.urlopen")
    def test_missing_model(self, urlopen):
        urlopen.side_effect = HTTPError("http://localhost", 404, "not found", {}, None)
        self.assertIn("not installed", list(chat("Hi", []))[-1][1])


if __name__ == "__main__":
    unittest.main()
