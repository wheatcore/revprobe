"""Command line interface for RevProbe."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from .core import build_suite, evaluate_suite
from .llm import improve_question


def save_json(path: str, value: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def target_response(url: str, case: dict, timeout: float) -> dict:
    headers = {"Content-Type": "application/json"}
    token = os.getenv("REVPROBE_TARGET_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps({"query": case["question"], "case_id": case["id"]}).encode("utf-8")
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as reply:
        value = json.load(reply)
    if not isinstance(value, dict):
        raise ValueError("target must return a JSON object")
    return value


def markdown_report(report: dict, suite: dict) -> str:
    by_id = {case["id"]: case for case in suite["cases"]}
    summary = report["summary"]
    lines = ["# RevProbe report", "", f"Source: `{report['source']}`", "",
             f"Current SHA-256: `{report['new_sha256']}`", "",
             f"Pass: **{summary['pass']}** · Fail: **{summary['fail']}** · Inconclusive: **{summary['inconclusive']}**", ""]
    for result in report["results"]:
        case = by_id[result["id"]]
        lines.extend([f"## {result['status'].upper()} · {case['section']}", "",
                      f"- Question: {case['question']}",
                      f"- Old anchor: `{case['old_anchor']}`; new anchor: `{case['new_anchor']}`",
                      f"- Reason: `{result['reason']}`", ""])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="revprobe", description="Probe AI knowledge assistants after documents change")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="create probes from two document snapshots")
    generate.add_argument("--old", required=True)
    generate.add_argument("--new", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("--source", help="stable document name; defaults to new file name")
    generate.add_argument("--model", help="optional OpenAI-compatible model for questions")
    generate.add_argument("--api-base", default="http://localhost:11434/v1")
    run = commands.add_parser("run", help="evaluate recorded or live answers")
    run.add_argument("--suite", required=True)
    input_group = run.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--responses", help="JSON object keyed by case ID")
    input_group.add_argument("--url", help="HTTP endpoint accepting {query, case_id}")
    run.add_argument("--output", required=True, help="JSON report path")
    run.add_argument("--markdown", help="optional Markdown report path")
    run.add_argument("--timeout", type=float, default=15)
    run.add_argument("--allow-inconclusive", action="store_true", help="return success when no probe has failed but some are inconclusive")
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            old = Path(args.old).read_text(encoding="utf-8")
            new = Path(args.new).read_text(encoding="utf-8")
            suite = build_suite(old, new, args.source or Path(args.new).name)
            if args.model:
                for case in suite["cases"]:
                    case["question"] = improve_question(case, model=args.model, api_base=args.api_base)
            save_json(args.output, suite)
            print(f"Generated {len(suite['cases'])} probes in {args.output}")
            return 0 if suite["cases"] else 2

        suite = load_json(args.suite)
        if suite.get("schema_version") != 1 or not isinstance(suite.get("cases"), list):
            raise ValueError("unsupported suite schema")
        if args.responses:
            responses = load_json(args.responses)
        else:
            responses = {}
            for case in suite["cases"]:
                try:
                    responses[case["id"]] = target_response(args.url, case, args.timeout)
                except (OSError, ValueError) as exc:
                    print(f"Warning: target error for {case['id']}: {exc}", file=sys.stderr)
        report = evaluate_suite(suite, responses)
        save_json(args.output, report)
        if args.markdown:
            target = Path(args.markdown)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(markdown_report(report, suite), encoding="utf-8")
        print(json.dumps(report["summary"]))
        if not suite["cases"]:
            return 2
        if report["summary"]["fail"] or (not args.allow_inconclusive and report["summary"]["inconclusive"]):
            return 1
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"revprobe: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
