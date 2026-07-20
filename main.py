"""CLI entry point. Given to students as-is -- argument parsing isn't the lesson.

Usage:
    uv run main.py "read main.py and tell me what it does"
    uv run main.py "list the files in this project" --max-steps 5
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agent import run_agent
from settings import load_settings
from tools import BUILTIN_TOOLS, ToolRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="mini-agent: a from-scratch coding agent")
    parser.add_argument("task", help="the task to hand to the agent")
    parser.add_argument("--max-steps", type=int, default=10)
    args = parser.parse_args()

    settings = load_settings()
    registry = ToolRegistry(BUILTIN_TOOLS)

    result = asyncio.run(
        run_agent(settings, args.task, registry, max_steps=args.max_steps)
    )

    print("=== RESULT ===")
    print(f"status: {result.status}")
    if result.status == "completed":
        print(result.output)
    elif result.status == "failed":
        print(f"error: {result.error}")
        sys.exit(1)
    else:
        print(f"ran out of steps ({args.max_steps}) without finishing")
        sys.exit(1)


if __name__ == "__main__":
    main()
