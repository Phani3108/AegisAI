from __future__ import annotations

from typing import Any

from aegisai.ollama.client import OllamaClient

VISION_PROMPT_IMAGE = (
    "Describe this image factually and in detail. Include visible text, UI elements, "
    "objects, people (without identifying real individuals), and overall context."
)


def frame_prompt(frame_index: int, frame_total: int) -> str:
    return (
        f"This is frame {frame_index} of {frame_total} sampled from a video. "
        "Describe what you see factually: actions, setting, on-screen text, objects, "
        "and any changes compared to a typical adjacent frame if apparent."
    )


async def vision_single_shot(
    ollama: OllamaClient,
    model: str,
    image_b64: str,
    content: str,
) -> tuple[str, dict]:
    body = await ollama.chat(
        model,
        [{"role": "user", "content": content, "images": [image_b64]}],
    )
    return OllamaClient.message_content(body), body


async def llm_answer_from_evidence(
    ollama: OllamaClient,
    llm_model: str,
    *,
    evidence_title: str,
    evidence_text: str,
    user_question: str,
    output_schema: dict[str, Any] | None = None,
) -> tuple[str, dict]:
    prompt = (
        f"Use only the following {evidence_title} to answer the user. "
        "If something is not supported by this evidence, say you cannot tell from the media.\n\n"
        f"{evidence_title}:\n{evidence_text}\n\nUser question:\n{user_question}"
    )
    if output_schema:
        prompt += (
            "\n\nRespond with a single JSON object only (no markdown fences) "
            "that best satisfies the user's question."
        )
        body = await ollama.chat(
            llm_model,
            [{"role": "user", "content": prompt}],
            response_format="json",
        )
    else:
        body = await ollama.chat(llm_model, [{"role": "user", "content": prompt}])
    return OllamaClient.message_content(body), body


def merge_token_hints(*bodies: dict) -> tuple[int | None, int | None]:
    ps: list[int] = []
    es: list[int] = []
    for b in bodies:
        p = b.get("prompt_eval_count")
        e = b.get("eval_count")
        if isinstance(p, int):
            ps.append(p)
        if isinstance(e, int):
            es.append(e)
    return (sum(ps) if ps else None, sum(es) if es else None)
