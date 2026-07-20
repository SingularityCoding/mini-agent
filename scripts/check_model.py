"""Quick manual check for model.py -- run after you've implemented request().

Given to you as-is; this is a convenience script, not the lesson.

    uv run scripts/check_model.py

Exercises two paths: a plain text reply (no tools), and a reply where the
model actually calls a tool -- that second one is the one it's easy to pass
by accident without really implementing, since chapter 1's headline example
never sends a `tools=` argument.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model import request  # noqa: E402
from settings import load_settings  # noqa: E402

GET_WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}


async def main() -> None:
    settings = load_settings()

    print("--- plain text, no tools ---")
    response = await request(settings, [{"role": "user", "content": "reply with exactly: pong"}])
    print(response)
    assert response.content is not None, "expected non-null content for a plain text reply"
    assert not response.tool_calls, "did not expect tool_calls without a tools= argument"
    print("looks right\n")

    print("--- with a tool available ---")
    response = await request(
        settings,
        [{"role": "user", "content": "what's the weather in Tokyo? use the tool, don't guess."}],
        tools=[GET_WEATHER_TOOL],
    )
    print(response)
    assert response.tool_calls, "expected the model to call get_weather"
    call = response.tool_calls[0]
    assert call.name == "get_weather", f"expected get_weather, got {call.name!r}"
    assert isinstance(call.arguments, dict) and "city" in call.arguments, (
        f"expected arguments to be a parsed dict with a 'city' key, got {call.arguments!r}"
    )
    print("looks right -- tool_calls parsed into a ToolCall with a dict arguments\n")


if __name__ == "__main__":
    asyncio.run(main())
