"""Quick manual check for tools.py -- run after you've implemented dispatch()
and the three builtin tools.

Given to you as-is; this is a convenience script, not the lesson.

    uv run scripts/check_tools.py

Exercises dispatch()'s three outcomes directly, with no model involved: an
unknown tool name, a call missing a required argument, and a real successful
call.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model import ToolCall  # noqa: E402
from tools import BUILTIN_TOOLS, ToolRegistry, dispatch  # noqa: E402


async def main() -> None:
    registry = ToolRegistry(BUILTIN_TOOLS)

    print("--- unknown tool ---")
    result = await dispatch(registry, ToolCall(id="1", name="nope", arguments={}))
    print(result)
    assert result.error is not None and result.error.startswith("unknown_tool"), (
        f"expected an unknown_tool error, got {result!r}"
    )
    print("looks right\n")

    print("--- missing required argument ---")
    result = await dispatch(registry, ToolCall(id="2", name="read_file", arguments={}))
    print(result)
    assert result.error is not None and result.error.startswith("invalid_arguments"), (
        f"expected an invalid_arguments error, got {result!r}"
    )
    print("looks right\n")

    print("--- real call: read this project's own main.py ---")
    result = await dispatch(
        registry, ToolCall(id="3", name="read_file", arguments={"path": "main.py"})
    )
    print(result)
    assert result.error is None, f"expected a successful read, got {result!r}"
    assert "def main" in result.output, "expected to see main.py's own source in the output"
    print("looks right\n")


if __name__ == "__main__":
    asyncio.run(main())
