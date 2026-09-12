"""Run real model analysis on a finalized transcript JSON file."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .agent import MeetingAgent
from .loop import AgentLoop


async def run(args) -> dict:
    data = json.loads(args.transcript.read_text(encoding="utf-8-sig"))
    utterances = data["transcript"] if isinstance(data, dict) else data
    agent = MeetingAgent.from_env()

    async def emit(event: dict) -> None:
        print(json.dumps(event, ensure_ascii=False), file=sys.stderr)

    loop = AgentLoop(agent, emit, auto_search=args.search)
    if args.search and not agent.supports_web_search:
        print("Exa key is not configured; running analysis and Q&A only.", file=sys.stderr)
    try:
        await loop.start()
        loop.append_final(utterances)
        if loop.auto_search:
            await loop.analyze_now()
        await loop.stop()
        if args.question:
            await loop.ask("cli-question", args.question)
        return loop.export()
    finally:
        await loop.aclose()
        await agent.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--question")
    parser.add_argument("--search", action="store_true", help="Allow automatic web search")
    parser.add_argument("--output", type=Path, help="Write export JSON outside the repository")
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if not result["analysis_is_current"] or result["analysis_error"]:
        parser.exit(1, "Final analysis failed; retained transcript and previous analysis.\n")
    if args.question and not result["messages"]:
        parser.exit(1, "Question answering failed; meeting export retained.\n")


if __name__ == "__main__":
    main()
