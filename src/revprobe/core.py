"""Pure document diffing and probe evaluation logic."""

from __future__ import annotations

from difflib import SequenceMatcher
from hashlib import sha256
import re
from typing import Any


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def paragraphs(text: str) -> list[dict[str, str]]:
    """Return content paragraphs with the closest Markdown heading."""
    result: list[dict[str, str]] = []
    heading = "Document"
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            result.append({"heading": heading, "text": " ".join(buffer).strip()})
            buffer.clear()

    for line in text.splitlines() + [""]:
        stripped = line.strip()
        if stripped.startswith("#") and re.match(r"^#{1,6}\s+", stripped):
            flush()
            heading = re.sub(r"^#{1,6}\s+", "", stripped)
        elif not stripped:
            flush()
        else:
            buffer.append(stripped)
    return result


def changed_pairs(old: str, new: str) -> list[tuple[dict[str, str], dict[str, str]]]:
    before, after = paragraphs(old), paragraphs(new)
    # Match by heading first, so a changed paragraph retains its section identity.
    old_by_heading: dict[str, list[dict[str, str]]] = {}
    new_by_heading: dict[str, list[dict[str, str]]] = {}
    for item in before:
        old_by_heading.setdefault(item["heading"], []).append(item)
    for item in after:
        new_by_heading.setdefault(item["heading"], []).append(item)

    pairs = []
    for heading, new_items in new_by_heading.items():
        old_items = old_by_heading.get(heading, [])
        matcher = SequenceMatcher(None, [x["text"] for x in old_items], [x["text"] for x in new_items], autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "replace":
                continue
            old_block, new_block = old_items[i1:i2], new_items[j1:j2]
            for old_item, new_item in zip(old_block, new_block):
                pairs.append((old_item, new_item))
    return pairs


TOKEN = re.compile(r"\d+(?:[.,]\d+)?%?|[A-Za-z][A-Za-z0-9_-]*|[\u4e00-\u9fff]+")


def anchors(old: str, new: str) -> tuple[str, str] | None:
    old_tokens, new_tokens = TOKEN.findall(old), TOKEN.findall(new)
    matcher = SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)
    candidates: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "replace":
            continue
        for a, b in zip(old_tokens[i1:i2], new_tokens[j1:j2]):
            if a.casefold() != b.casefold() and a.casefold() not in new.casefold() and b.casefold() not in old.casefold():
                candidates.append((a, b))
    if not candidates:
        return None
    # Numeric changes are more reliably checkable without an LLM.
    return next((pair for pair in candidates if re.search(r"\d", pair[0]) and re.search(r"\d", pair[1])), candidates[0])


def build_suite(old: str, new: str, source: str) -> dict[str, Any]:
    cases = []
    for old_item, new_item in changed_pairs(old, new):
        pair = anchors(old_item["text"], new_item["text"])
        if not pair:
            continue
        old_anchor, new_anchor = pair
        heading = new_item["heading"]
        case_id = digest("\n".join((source, heading, old_item["text"], new_item["text"])))[:12]
        cases.append({
            "id": case_id,
            "section": heading,
            "question": f"According to {source}, what is the current rule in the '{heading}' section?",
            "old_anchor": old_anchor,
            "new_anchor": new_anchor,
            "old_text": old_item["text"],
            "new_text": new_item["text"],
        })
    return {"schema_version": 1, "source": source, "old_sha256": digest(old), "new_sha256": digest(new), "cases": cases}


def evaluate_case(case: dict[str, Any], response: dict[str, Any] | None, expected_sha: str) -> dict[str, Any]:
    if response is None:
        return {"id": case["id"], "status": "inconclusive", "reason": "missing_response"}
    answer = response.get("answer")
    if not isinstance(answer, str):
        return {"id": case["id"], "status": "inconclusive", "reason": "invalid_answer"}
    cited_sha = response.get("source_sha256")
    if cited_sha is not None and cited_sha != expected_sha:
        return {"id": case["id"], "status": "fail", "reason": "stale_source_revision", "answer": answer, "source_sha256": cited_sha}
    def hit(anchor: str) -> bool:
        escaped = re.escape(anchor)
        if anchor.isalnum():
            return bool(re.search(rf"(?<!\w){escaped}(?!\w)", answer, re.IGNORECASE))
        return anchor.casefold() in answer.casefold()

    old_hit = hit(case["old_anchor"])
    new_hit = hit(case["new_anchor"])
    if old_hit and not new_hit:
        status, reason = "fail", "old_anchor_in_answer"
    elif new_hit and not old_hit:
        status, reason = "pass", "new_anchor_in_answer"
    elif old_hit and new_hit:
        status, reason = "inconclusive", "both_anchors_in_answer"
    else:
        status, reason = "inconclusive", "no_anchor_in_answer"
    return {"id": case["id"], "status": status, "reason": reason, "answer": answer, "source_sha256": cited_sha}


def evaluate_suite(suite: dict[str, Any], responses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_case(case, responses.get(case["id"]), suite["new_sha256"]) for case in suite["cases"]]
    return {
        "schema_version": 1,
        "source": suite["source"],
        "new_sha256": suite["new_sha256"],
        "summary": {status: sum(r["status"] == status for r in results) for status in ("pass", "fail", "inconclusive")},
        "results": results,
    }
