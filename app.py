"""Local Gradio chat UI for a model already installed in Ollama."""

import gradio as gr

from ollama_chat import MODEL, chat


demo = gr.ChatInterface(
    fn=chat,
    title="Local AI Chat · Qwen 3.5",
    description=(
        f"A local chat demo powered by {MODEL} and Ollama. "
        "Thinking is off; replies stream from this computer, not the cloud."
    ),
    examples=[
        "Explain recursion with a simple analogy.",
        "Write a friendly welcome message for a new teammate.",
        "Give me three ideas for a weekend project.",
    ],
    save_history=True,
    analytics_enabled=False,
)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", inbrowser=True)
