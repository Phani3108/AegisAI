"""Normalize chat completion bodies across backends (Ollama-shaped today)."""


def chat_message_content(body: dict) -> str:
    msg = body.get("message") or {}
    return (msg.get("content") or "").strip()
