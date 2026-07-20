"""CLI entry point. Given to students as-is -- argument parsing isn't the lesson.

Usage:
    uv run main.py "read main.py and tell me what it does"
"""

from __future__ import annotations

import argparse
import sys

from settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="mini-agent: a from-scratch coding agent")
    parser.add_argument("task", help="the task to hand to the agent")
    parser.add_argument("--max-steps", type=int, default=10)
    args = parser.parse_args()

    settings = load_settings()

    # Batch 4 will replace this with a call into agent.run_agent(...).
    print(f"[mini-agent] would run task {args.task!r} against {settings.default_model!r}")
    print("[mini-agent] agent loop not implemented yet")
    sys.exit(1)


if __name__ == "__main__":
    main()
