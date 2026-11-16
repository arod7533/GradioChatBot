"""Ollama request and streaming logic, independent of the Gradio UI."""

import json
from collections.abc import Iterator
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3.5:9b"
SYSTEM_PROMPT = "You are a helpful assistant. Be clear and concise."
MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY_MESSAGES = 12


def build_messages(message: str, history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Keep recent text-only turns to limit the context sent to Ollama."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(
        {"role": item["role"], "content": item["content"][:MAX_MESSAGE_LENGTH]}
        for item in history[-MAX_HISTORY_MESSAGES:]
        if item.get("role") in ("user", "assistant")
        and isinstance(item.get("content"), str)
    )
    messages.append({"role": "user", "content": message[:MAX_MESSAGE_LENGTH]})
    return messages


def chat(message: str, history: list[dict[str, Any]]) -> Iterator[str]:
    """Yield cumulative text as Ollama streams newline-delimited JSON."""
    request = Request(
        OLLAMA_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": build_messages(message, history),
                "stream": True,
                "think": False,
                "options": {"num_ctx": 4096, "num_predict": 350},
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    reply = ""
    try:
        with urlopen(request, timeout=120) as response:
            for line in response:
                event = json.loads(line)
                if event.get("error"):
                    problem = "Ollama stopped generating. Please try again."
                    yield reply + "\n\n" + problem if reply else problem
                    return
                chunk = event.get("message", {}).get("content", "")
                if chunk:
                    reply += chunk
                    yield reply
                if event.get("done"):
                    break
        if not reply:
            yield "The model returned an empty response."
    except HTTPError as error:
        if error.code == 404:
            problem = f"Model `{MODEL}` is not installed. Check `ollama list`."
        else:
            problem = f"Ollama returned HTTP {error.code}. Please try again."
        yield reply + "\n\n" + problem if reply else problem
    except (URLError, TimeoutError):
        problem = "Can't connect to Ollama. Start the Ollama app or run `ollama serve`."
        yield reply + "\n\n" + problem if reply else problem
    except (ValueError, TypeError, KeyError):
        problem = "Ollama sent an unexpected response. Please try again."
        yield reply + "\n\n" + problem if reply else problem
