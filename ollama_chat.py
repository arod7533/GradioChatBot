"""Bounded Ollama agent loop with visible, allowlisted tool calls."""

import json
from collections.abc import Iterator
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from airline_data import TOOLS, run_tool

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3.5:9b"
MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_LENGTH = 4000
MAX_TOOL_ROUNDS = 2
SYSTEM_PROMPT = (
    "You are Astra Air's friendly virtual assistant. This is a FICTIONAL demo airline "
    "with sample data, not real flights or reservations. For any specific flight, booking, "
    "or baggage question, use the supplied tools; never invent prices, times, status, or "
    "reservation details. Use multiple tools if the question needs them. Explain results "
    "briefly and label all flight and booking data as demo data. Do not offer to make, "
    "change, or cancel bookings: these tools are read-only. Ask for a date if none is given; "
    "do not assume today's date."
)


def build_messages(message: str, history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Send only the recent conversational text, not Gradio tool-display rows."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(
        {"role": item["role"], "content": item["content"][:MAX_MESSAGE_LENGTH]}
        for item in history[-MAX_HISTORY_MESSAGES:]
        if item.get("role") in ("user", "assistant")
        and not item.get("metadata")
        and isinstance(item.get("content"), str)
    )
    messages.append({"role": "user", "content": message[:MAX_MESSAGE_LENGTH]})
    return messages


def chat(message: str, history: list[dict[str, Any]]) -> Iterator[tuple[str, Any]]:
    """Yield ('tool', details) and ('answer', cumulative text) as Ollama responds."""
    messages: list[dict[str, Any]] = build_messages(message, history)
    answer = ""
    try:
        for round_number in range(MAX_TOOL_ROUNDS + 1):
            payload: dict[str, Any] = {
                "model": MODEL,
                "messages": messages,
                "stream": True,
                "think": False,
                "options": {"num_ctx": 4096, "num_predict": 300, "temperature": 0},
            }
            if round_number < MAX_TOOL_ROUNDS:
                payload["tools"] = TOOLS
            request = Request(
                OLLAMA_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            calls: list[dict[str, Any]] = []
            answer = ""
            with urlopen(request, timeout=120) as response:
                for line in response:
                    event = json.loads(line)
                    if event.get("error"):
                        raise ValueError("Ollama stream error")
                    chunk = event.get("message", {})
                    calls.extend(chunk.get("tool_calls", []))
                    if chunk.get("content"):
                        answer += chunk["content"]
                        yield "answer", answer
                    if event.get("done"):
                        break
            if not calls:
                if not answer:
                    yield "answer", "The model returned an empty response."
                return

            messages.append(
                {"role": "assistant", "content": answer, "tool_calls": calls}
            )
            for call in calls:
                function = call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", {})
                result = run_tool(name, arguments)
                messages.append(
                    {"role": "tool", "tool_name": name, "content": json.dumps(result)}
                )
                yield "tool", {"name": name, "arguments": arguments, "result": result}
    except HTTPError as error:
        if error.code == 404:
            problem = f"Model `{MODEL}` is not installed. Check `ollama list`."
        else:
            problem = f"Ollama returned HTTP {error.code}. Please try again."
        yield "answer", answer + "\n\n" + problem if answer else problem
    except (URLError, TimeoutError):
        problem = "Can't connect to Ollama. Start the Ollama app or run `ollama serve`."
        yield "answer", answer + "\n\n" + problem if answer else problem
    except (ValueError, TypeError, KeyError):
        problem = "Ollama sent an unexpected response. Please try again."
        yield "answer", answer + "\n\n" + problem if answer else problem
