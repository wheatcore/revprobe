# RevProbe

**Turn document changes into regression tests for AI knowledge assistants.**

When a policy or help article changes from “30 days” to “14 days”, a RAG assistant can keep citing the old version. RevProbe compares two document snapshots, builds targeted questions around changed facts, calls your assistant (or reads recorded answers), and emits a CI-friendly report with source hashes and reasons for each result.

The core runs entirely offline with Python's standard library. An OpenAI-compatible model is optional for writing more natural probe questions. The model cannot alter the old/new evidence anchors.

> **Status:** v0.1 prototype. This is a focused implementation of change-derived freshness probes, not a claim that RAG evaluation or temporal provenance is new. Review generated questions before using them as release gates.

## Quick start

Python 3.11+:

```bash
python -m pip install -e .
revprobe generate \
  --old examples/policy-old.md \
  --new examples/policy-new.md \
  --source support-policy \
  --output examples/probes.json
revprobe run \
  --suite examples/probes.json \
  --responses examples/answers-fresh.json \
  --output report.json \
  --markdown report.md
```

The included fresh fixture produces `{"pass": 2, "fail": 0, "inconclusive": 0}`. Try `examples/answers-stale.json` to see a failing run. Exit codes: `0` all probes pass, `1` at least one failed or is inconclusive, `2` invalid input or no checkable changes. Pass `--allow-inconclusive` to let unresolved probes return `0` if none failed.

## Connect a live assistant

```bash
revprobe run --suite examples/probes.json \
  --url http://localhost:8000/answer \
  --output report.json --markdown report.md
```

For each probe, RevProbe sends `POST` JSON:

```json
{"query": "According to support-policy, what is the current rule in the 'Refund window' section?", "case_id": "038422a0215f"}
```

Your endpoint returns:

```json
{"answer": "Customers can request a refund within 14 days.", "source_sha256": "27b6c8e66db6efc739c09466c92a10c5dbbe6803d0c81095f33f46f473a4645e"}
```

`source_sha256` is optional, but supplying the SHA-256 of the document revision actually cited lets RevProbe catch stale evidence even when answer wording appears current. `REVPROBE_TARGET_TOKEN` adds a bearer token to endpoint requests. Keep endpoint URLs and secrets out of committed test fixtures.

## Optional AI question generation

```bash
export REVPROBE_API_KEY=your_key  # omit for an unauthenticated local server
revprobe generate --old examples/policy-old.md --new examples/policy-new.md \
  --source support-policy --output probes.json \
  --model your-model --api-base http://localhost:11434/v1
```

The model sees only the changed paragraphs. It returns one JSON question per change. RevProbe rejects empty questions and questions that reveal either answer anchor. It always derives answer anchors and source hashes locally. An OpenAI-compatible `/chat/completions` endpoint is required; no hosted service is baked in.

## How it works

```text
old/new Markdown or text
    → section-aware paragraph diff
    → changed token pair (prefer numbers)
    → reviewable question + old/new anchors + revision hashes
    → recorded answers or HTTP Q&A endpoint
    → pass / fail / inconclusive JSON and Markdown reports
```

- **Pass:** the new anchor appears and the old one does not.
- **Fail:** the old anchor appears alone, or the endpoint reports a source hash other than the current revision.
- **Inconclusive:** no answer, malformed answer, both anchors, or neither anchor. RevProbe never calls a vague answer “fresh” by default.

The report is evidence-oriented: it records the question, anchors, answer, cited revision when supplied, and a machine-readable reason. The suite and report schemas are versioned.

## Scope and limits

RevProbe currently works best for changed values and short rules inside stable Markdown headings. It pairs changed paragraphs inside the same heading and skips changes without a distinct old/new token pair. It does not infer semantic equivalence from paraphrases, prove that an answer is true, parse PDFs, or verify that your Q&A endpoint actually cited the claimed revision. Numeric anchors are whole-token matched, but a number used elsewhere in an answer can still make the verdict inconclusive or misleading; review the case and answer before acting on a release gate. AI-generated questions can also be imperfect.

For production use, record a trustworthy document revision in your retrieval metadata and return it from the Q&A endpoint. Add human-reviewed probes for complex policy changes. Never send confidential documents to a third-party model without permission.

## Development

```bash
python -m unittest discover -s tests -v
```

The [implementation plan](docs/plans/2026-10-19-revprobe.md) describes the design. [Contributing](CONTRIBUTING.md) explains how to add tests and adapters.

## Related work

RAG reliability and citation testing are established areas. [RAGProbe](https://github.com/AntonGlenbovitch/ragprobe) evaluates RAG datasets and model configurations; [ragcitecheck](https://github.com/ppon1086/ragcitecheck) studies citation stability. RevProbe focuses on deriving small, reviewable regression probes directly from a document revision and checking whether an assistant has moved away from the superseded fact. These projects are complementary, and no exhaustive originality claim is made.

## Resume description

> Built RevProbe, an open-source Python CLI that converts policy-document revisions into targeted regression probes for RAG assistants; implemented section-aware diffing, optional LLM question generation, source-hash validation, HTTP/offline adapters, explainable verdicts, and CI tests.

## License

MIT. See [LICENSE](LICENSE).
