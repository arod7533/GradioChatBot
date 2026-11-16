"""Fast unit tests: no Gradio server, Ollama process, or model required."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ollama_chat import MAX_HISTORY_MESSAGES, MAX_MESSAGE_LENGTH, build_messages, chat


def stream(*events):
    return io.BytesIO(b"".join(json.dumps(event).encode() + b"\n" for event in events))


class BuildMessagesTests(unittest.TestCase):
    def test_keeps_only_recent_text_messages_and_new_prompt(self):
        history = [{"role": "user", "content": "old"}] * (MAX_HISTORY_MESSAGES + 1)
        history += [
            {"role": "assistant", "content": "A" * (MAX_MESSAGE_LENGTH + 20)},
            {"role": "tool", "content": "ignored"},
            {"role": "assistant", "content": {"path": "ignored.png"}},
        ]
        messages = build_messages("B" * (MAX_MESSAGE_LENGTH + 20), history)
        self.assertEqual(messages[0]["role"], "system")
        self.assertLessEqual(len(messages), MAX_HISTORY_MESSAGES + 2)
        self.assertEqual(messages[-2], {"role": "assistant", "content": "A" * 4000})
        self.assertEqual(messages[-1], {"role": "user", "content": "B" * 4000})
        self.assertNotIn("tool", [item["role"] for item in messages])


class ChatTests(unittest.TestCase):
    @patch("ollama_chat.urlopen")
    def test_streams_cumulative_response_and_sends_chat_settings(self, urlopen):
        urlopen.return_value = stream(
            {"message": {"content": "Hello"}},
            {"message": {"content": " there"}},
            {"done": True},
        )
        self.assertEqual(list(chat("Hi", [])), ["Hello", "Hello there"])
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(payload["model"], "qwen3.5:9b")
        self.assertIs(payload["think"], False)
        self.assertIs(payload["stream"], True)
        self.assertEqual(payload["messages"][-1], {"role": "user", "content": "Hi"})
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 120)

    @patch("ollama_chat.urlopen", return_value=stream({"done": True}))
    def test_empty_reply(self, _urlopen):
        self.assertEqual(
            list(chat("Hi", [])), ["The model returned an empty response."]
        )

    @patch("ollama_chat.urlopen", return_value=stream({"error": "internal detail"}))
    def test_stream_error_does_not_expose_internal_detail(self, _urlopen):
        self.assertEqual(
            list(chat("Hi", [])), ["Ollama stopped generating. Please try again."]
        )

    @patch(
        "ollama_chat.urlopen",
        return_value=stream(
            {"message": {"content": "Partial"}},
            {"error": "private detail"},
        ),
    )
    def test_stream_error_preserves_partial_reply(self, _urlopen):
        self.assertEqual(
            list(chat("Hi", []))[-1],
            "Partial\n\nOllama stopped generating. Please try again.",
        )

    @patch("ollama_chat.urlopen", return_value=io.BytesIO(b"invalid json\n"))
    def test_malformed_response(self, _urlopen):
        self.assertIn("unexpected response", list(chat("Hi", []))[-1])

    @patch("ollama_chat.urlopen", side_effect=URLError("connection refused"))
    def test_ollama_unavailable(self, _urlopen):
        self.assertIn("Start the Ollama app", list(chat("Hi", []))[-1])

    @patch("ollama_chat.urlopen")
    def test_missing_model(self, urlopen):
        urlopen.side_effect = HTTPError("http://localhost", 404, "not found", {}, None)
        self.assertIn("not installed", list(chat("Hi", []))[-1])


if __name__ == "__main__":
    unittest.main()
