"""Optional OpenAI-compatible question generation."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


def improve_question(case: dict, *, model: str, api_base: str, api_key: str | None = None) -> str:
    """Ask a model for a discriminative question; leave evidence anchors untouched."""
    endpoint = api_base.rstrip("/") + "/chat/completions"
    prompt = (
        "Create one concise question that distinguishes the OLD rule from the NEW rule. "
        "Do not include either answer in the question. Return only JSON: {\"question\": \"...\"}.\n"
        f"Section: {case['section']}\nOLD: {case['old_text'][:4000]}\nNEW: {case['new_text'][:4000]}"
    )
    payload = {"model": model, "temperature": 0, "messages": [
        {"role": "system", "content": "You write narrow regression questions for document changes."},
        {"role": "user", "content": prompt},
    ]}
    headers = {"Content-Type": "application/json"}
    token = api_key or os.getenv("REVPROBE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=30) as reply:
        data = json.load(reply)
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    question = parsed.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        raise ValueError("model returned an invalid question")
    if case["old_anchor"].casefold() in question.casefold() or case["new_anchor"].casefold() in question.casefold():
        raise ValueError("model question contains an answer anchor")
    return question.strip()
