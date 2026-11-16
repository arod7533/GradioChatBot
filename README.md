# Astra Air · Local AI Travel Assistant

An **agentic airline support demo** built with Gradio and your locally installed
`qwen3.5:9b` model in [Ollama](https://ollama.com/). The assistant chooses
read-only tools to answer questions about a **fictional** airline's SQLite in-memory
flights, reservation, flight status, and baggage rules. Tool results appear as
collapsible steps in a polished dark-mode UI.

> **Demo data only.** Astra Air, its flight schedule, passenger, and reservation
> are fictional. No real inventory, live tracking, bookings, payments, or
> external inference services are involved.

## Demo video

[![Watch the chatbot demo](assets/demo-poster.png)](demo.mp4)

[Watch the 73-second MP4 recording](demo.mp4) — the recorded browser viewport
shows two multi-tool questions, the underlying tool results, and a declined
cancellation. The footage is sped up 1.4× to reduce model-wait time; it is
not a latency benchmark. The video is about 1 MB and is committed to Git.

## What it demonstrates

- **Tool-calling loop:** Qwen decides which of four allowlisted tools to call,
  can use a tool result to decide on another, and receives a maximum of two
  tool-selection rounds before answering. The UI shows each actual tool result.
- **Grounded example data:** searches use parameterized SQL against an
  in-memory SQLite database with writes disabled. Missing records return
  explicit errors.
- **Local inference:** Ollama runs on your machine, with thinking turned off.
  The model weights are never downloaded by browser visitors.
- **Usability:** streaming answers, example prompts, dark styling, explanatory
  sample-data panel, and helpful connection errors.

## Try it

1. Install [Ollama](https://ollama.com/) and start it (`ollama serve` or the
   desktop app). Run `ollama list`; if needed, install the model once with
   `ollama pull qwen3.5:9b` (~6.6 GB on the development machine).
2. With Python 3.11 or 3.12:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python app.py
   ```

Open http://127.0.0.1:7860. Only the local computer can access the Gradio UI.
Press **Ctrl+C** to stop it.

Try these sample questions (the fixtures are dated **December 5–6, 2026**):

1. `Find SFO to JFK flights on December 5, 2026.`
2. `Look up demo booking AX7K2Q and check the status of its flight.`
3. `What is the Economy baggage policy?`
4. `Find SFO to JFK flights on Dec 5 and tell me the Economy baggage policy.`

The last two combined questions demonstrate multi-tool reasoning. Model
responses are nondeterministic; inspect the collapsible tool steps for the
deterministic data behind each answer.

## Project layout

| File | Purpose |
| --- | --- |
| `app.py` | Gradio interface, dark theme, and visible tool activity |
| `ollama_chat.py` | Bounded agent loop and Ollama streaming protocol |
| `airline_data.py` | SQLite `:memory:` fixture database, four tools, and read-only dispatch |
| `tests/` | Mocked agent, tool, and UI adapter tests |

Messages are clipped to 4,000 characters and the last 12 history messages
are considered. Tool-display rows are excluded from the model's subsequent
conversation context. Calls to Ollama stay on `127.0.0.1`.

## Quality checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

GitHub Actions runs the tests and lint checks on Python 3.11 and 3.12 without
needing Ollama or the model. Live response quality and model latency are not
covered by these unit tests.

## Scope and limitations

This is a **local, single-user portfolio demo**, not an airline service.
SQLite records live only in process memory and do not represent real travel data. The
assistant may still make mistakes or ignore instructions; tool output is the
source of truth for fixture facts. Booking changes and payments are deliberately
out of scope and cannot be performed by any tool.
