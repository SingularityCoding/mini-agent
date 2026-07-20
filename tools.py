"""The Tool boundary: register tools, expose their schema to the model, and
execute them with a single dispatch point that distinguishes failure modes.

Deliberately minimal for a short course: no approval/confirmation system, no
trusted-value injection (every argument comes straight from the model), and no
per-call timeout override from the model. A production Tool boundary would
likely add all three. Here the lesson is narrower: a tool's *schema* (what the
model sees) is a different thing from its *handler* (what actually runs), and
a dispatcher must cleanly tell apart "no such tool", "bad arguments", and "the
handler blew up" -- three failure modes that a Harness needs to react to
differently, and that get muddled together if you let exceptions propagate
unstructured.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from model import ToolCall


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]


class ToolRegistry:
    """Holds the tools available this run and exposes their wire-format schema."""

    def __init__(self, tools: list[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """TODO: raise ValueError if tool.name is already registered."""
        raise NotImplementedError

    def get(self, name: str) -> Tool | None:
        raise NotImplementedError

    def specs(self) -> list[dict[str, Any]]:
        """Wire-format tool specs to pass as `model.request(..., tools=...)`.

        Only the name, description, and JSON Schema parameters are sent to the
        model -- never the Python handler. The model can only ever propose a
        call by name and arguments; it has no access to the code that runs.

        TODO: [{"type": "function", "function": {"name": ..., "description": ...,
        "parameters": ...}}, ...] for every registered tool.
        """
        raise NotImplementedError


@dataclass(frozen=True)
class ToolResult:
    output: str
    error: str | None = None


async def dispatch(
    registry: ToolRegistry, call: ToolCall, *, timeout_seconds: float = 30.0
) -> ToolResult:
    """Validate and execute a single tool call -- the only place a handler runs.

    Must distinguish three failure modes so a caller can react to each
    differently:

    TODO:
    - unknown tool: registry.get(call.name) is None -> ToolResult(output="",
      error=f"unknown_tool: {call.name}"). The handler must NOT be called.
    - invalid arguments: a lightweight required-field check (every name in
      tool.parameters.get("required", []) must be a key in call.arguments; a
      full JSON Schema validator is out of scope) -> ToolResult(output="",
      error=f"invalid_arguments: missing {missing_names}"). The handler must
      NOT be called.
    - handler exception / timeout: the handler raised, or ran past
      timeout_seconds -> ToolResult(output="", error="handler_error: ...") or
      ToolResult(output="", error="tool_timeout: ..."). asyncio.CancelledError
      must always re-raise, never be caught as an error result.
    - success -> ToolResult(output=<the handler's return value, as a str>).

    Also: adapt sync handlers to this async boundary. If
    inspect.iscoroutinefunction(tool.handler), await it directly; otherwise run
    it via asyncio.to_thread(tool.handler, **call.arguments) so a blocking
    file/subprocess call doesn't stall the event loop.
    """
    raise NotImplementedError


def _resolve_confined(path: str) -> Path | str:
    """Resolve `path` and refuse anything outside the current working directory.

    Minimal safety net, not real sandboxing.

    TODO: Path(path).resolve(), then check it's Path.cwd().resolve() itself or
    somewhere under it; return an f"refused: {path} is outside the project
    directory" string (not raise) when it's not.
    """
    raise NotImplementedError


def read_file(path: str) -> str:
    """TODO: use _resolve_confined, then return the file's text contents (or an
    "error: ..." string if it doesn't exist / isn't a file -- that's a normal,
    expected outcome the model should see, not a crash)."""
    raise NotImplementedError


def list_files(path: str = ".") -> str:
    """TODO: use _resolve_confined, then return a newline-joined listing of the
    immediate (non-recursive) contents of the directory, directories suffixed
    with "/", sorted by name."""
    raise NotImplementedError


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """TODO: use _resolve_confined. If old_str == "" and the file doesn't exist,
    create it (and parent dirs) with new_str as its full content. Otherwise
    require old_str to appear in the file *exactly once* (return an "error: ..."
    string on zero or multiple matches -- don't guess which one), replace it
    with new_str, and write the file back."""
    raise NotImplementedError


# TODO: three Tool instances (read_file, list_files, edit_file) with a JSON
# Schema `parameters` for each, wired to the handlers above. See tools.py in
# the `reference` branch for the exact schema shape once you've tried this
# yourself.
BUILTIN_TOOLS: list[Tool] = []
