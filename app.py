"""Astra Air: a fictional, locally running airline assistant demo."""

import json
from collections.abc import Iterator

import gradio as gr

from ollama_chat import chat

TOOL_LABELS = {
    "search_flights": "Flight search",
    "get_flight_status": "Flight status",
    "lookup_booking": "Booking lookup",
    "get_baggage_policy": "Baggage policy",
}


def respond(message: str, history: list[dict]) -> Iterator[list[gr.ChatMessage]]:
    """Present tool executions as collapsible records, followed by the answer."""
    output: list[gr.ChatMessage] = []
    answer_index = None
    for kind, data in chat(message, history):
        if kind == "tool":
            output.append(
                gr.ChatMessage(
                    role="assistant",
                    content=f"```json\n{json.dumps(data['result'], indent=2)}\n```",
                    metadata={
                        "title": f"✓ {TOOL_LABELS.get(data['name'], 'Tool call')}",
                        "status": "done",
                    },
                )
            )
            answer_index = None
        else:
            answer = gr.ChatMessage(role="assistant", content=data)
            if answer_index is None:
                answer_index = len(output)
                output.append(answer)
            else:
                output[answer_index] = answer
        yield output.copy()


THEME = gr.themes.Soft(primary_hue="cyan", secondary_hue="blue", neutral_hue="slate")
CSS = """
body, .gradio-container { background: #090f1d !important; }
.gradio-container { max-width: 1440px !important; padding: 24px 38px !important; }
#hero { padding: 20px 4px 24px; }
#hero .eyebrow { color: #42d8d0; font-size: 12px; font-weight: 700; letter-spacing: .2em; }
#hero h1 { color: #f5f8ff; font-size: 40px; line-height: 1.15; margin: 12px 0 8px; }
#hero p { color: #9dabcb; font-size: 15px; margin: 0; }
#hero .brand { color: #6be3dd; }
#hero .badge { display: inline-block; margin-left: 14px; border: 1px solid #317a81;
  border-radius: 999px; padding: 5px 10px; color: #89e4df; letter-spacing: .05em;
  font-size: 11px; vertical-align: middle; }
#side-panel { padding: 22px; border: 1px solid #27344d; border-radius: 18px;
  background: #111c30; color: #d4dff4; }
#side-panel h3 { color: #f5f8ff; font-size: 16px; margin: 0 0 14px; }
#side-panel p, #side-panel li { color: #9fb1ce; font-size: 13px; line-height: 1.6; }
#side-panel strong { color: #e1f2f8; }
#side-panel .tag { display: inline-block; padding: 6px 10px; margin: 3px 3px 3px 0;
  border: 1px solid #335069; border-radius: 8px; color: #a9e6e4; font-size: 12px; }
#side-panel .divider { height: 1px; background: #29374e; margin: 20px 0; }
#side-panel .note { font-size: 12px; color: #8396b5; }
#chat-panel { border: 1px solid #27344d; border-radius: 18px; overflow: hidden; }
"""

with gr.Blocks(
    title="Astra Air | Local AI Travel Assistant", analytics_enabled=False
) as demo:
    gr.HTML(
        """
        <header id="hero">
          <div class="eyebrow">ASTRA AIR <span class="badge">● LOCAL AGENT DEMO</span></div>
          <h1>Travel questions, <span class="brand">answered.</span></h1>
          <p>Explore flights, look up a reservation, and check travel policies with a
             tool-using AI assistant.</p>
        </header>
        """
    )
    with gr.Row(equal_height=False):
        with gr.Column(scale=4, min_width=550, elem_id="chat-panel"):
            gr.ChatInterface(
                fn=respond,
                chatbot=gr.Chatbot(
                    label="Astra Air assistant",
                    layout="bubble",
                    height=555,
                    placeholder=(
                        "<div style='text-align:center; padding:70px 20px'>"
                        "<div style='font-size:30px'>✈</div>"
                        "<h3>Where can we take you?</h3>"
                        "<p>Ask about flights, a sample booking, or baggage rules.</p></div>"
                    ),
                ),
                textbox=gr.Textbox(
                    placeholder="Ask Astra Air anything...",
                    show_label=False,
                    submit_btn=True,
                    stop_btn=True,
                ),
                examples=[
                    "Find SFO to JFK flights on December 5, 2026.",
                    "What is the status of AST 218?",
                    "Look up my demo booking AX7K2Q.",
                    "What is the Economy baggage policy?",
                ],
                example_labels=[
                    "Find a flight",
                    "Track a flight",
                    "View a booking",
                    "Baggage rules",
                ],
                fill_height=False,
                analytics_enabled=False,
                api_visibility="private",
            )
        with gr.Column(scale=1, min_width=260):
            gr.HTML(
                """
                <aside id="side-panel">
                  <h3>Explore the demo</h3>
                  <p>Try a multi-step question:</p>
                  <p><strong>“Find SFO to JFK flights on Dec 5 and tell me
                     the Economy baggage policy.”</strong></p>
                  <div class="divider"></div>
                  <h3>Sample data</h3>
                  <span class="tag">SFO → JFK · Dec 5</span>
                  <span class="tag">LAX → SEA · Dec 5</span>
                  <span class="tag">Booking · AX7K2Q</span>
                  <div class="divider"></div>
                  <h3>Under the hood</h3>
                  <p>Qwen 3.5 selects read-only tools to search an in-memory timetable,
                     inspect a booking, or check baggage rules. Open a tool step in
                     the chat to see the actual database result.</p>
                  <p class="note">Fictional airline and sample data. No real flights,
                     bookings, payments, or live tracking.</p>
                </aside>
                """
            )

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=True,
        theme=THEME,
        css=CSS,
        js="() => { document.documentElement.classList.add('dark'); document.body.classList.add('dark'); }",
        footer_links=[],
    )
