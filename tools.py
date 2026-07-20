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
        """Register `tool`, rejecting duplicate names rather than replacing one."""
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Return the named tool, or `None` when it is not registered."""
        return self._tools.get(name)

    def specs(self) -> list[dict[str, Any]]:
        """Wire-format tool specs to pass as `model.request(..., tools=...)`.

        Only the name, description, and JSON Schema parameters are sent to the
        model -- never the Python handler. The model can only ever propose a
        call by name and arguments; it has no access to the code that runs.

        Each entry uses the OpenAI-compatible function-tool shape:
        `{"type": "function", "function": {"name": ..., "description": ...,
        "parameters": ...}}`.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]


@dataclass(frozen=True)
class ToolResult:
    output: str
    error: str | None = None


async def dispatch(
    registry: ToolRegistry, call: ToolCall, *, timeout_seconds: float = 30.0
) -> ToolResult:
    """Validate and execute a single tool call -- the only place a handler runs.

    Distinguishes four outcomes so a Harness can react to each differently:

    - `unknown_tool`: the name is not registered; no handler runs.
    - `invalid_arguments`: a required argument is missing; no handler runs.
    - `handler_error` / `tool_timeout`: execution failed or exceeded its bound.
    - success: the handler's return value is normalized to a string.

    Handler exceptions are caught at this boundary, but `CancelledError` is
    deliberately allowed through so cancelling the whole agent remains
    possible.
    """
    # Resolve the proposed name before touching a handler.
    tool = registry.get(call.name)
    if tool is None:
        return ToolResult(output="", error=f"unknown_tool: {call.name}")

    # Lightweight required-field check only -- not a full JSON Schema validator
    # (type checking, enums, nested objects, etc. are out of scope here).
    required = tool.parameters.get("required", [])
    missing = [name for name in required if name not in call.arguments]
    if missing:
        return ToolResult(output="", error=f"invalid_arguments: missing {missing}")

    # Adapt synchronous handlers to the async boundary, then apply the same
    # timeout and error normalization to both sync and async implementations.
    try:
        if inspect.iscoroutinefunction(tool.handler):
            coro = tool.handler(**call.arguments)
        else:
            # Sync handlers (e.g. blocking file or subprocess calls) must not run
            # directly on the event loop -- to_thread hands them to a worker
            # thread so a slow handler doesn't stall every other in-flight task.
            coro = asyncio.to_thread(tool.handler, **call.arguments)
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        return ToolResult(output="", error=f"tool_timeout: exceeded {timeout_seconds}s")
    except Exception as exc:  # noqa: BLE001 - intentional catch-all execution boundary
        return ToolResult(output="", error=f"handler_error: {type(exc).__name__}: {exc}")

    return ToolResult(output=result if isinstance(result, str) else str(result))


def _resolve_confined(path: str) -> Path | str:
    """Resolve `path` and refuse anything outside the current working directory.

    Minimal safety net, not real sandboxing: it only stops a path from
    escaping cwd via `..` or an absolute path, and it is only enforced for
    calls that go through these builtin handlers.
    """
    resolved = Path(path).resolve()
    root = Path.cwd().resolve()
    if resolved != root and root not in resolved.parents:
        return f"refused: {path} is outside the project directory"
    return resolved


def read_file(path: str) -> str:
    """Return a confined file's text, or an `error:` string for expected failures."""
    resolved = _resolve_confined(path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.exists():
        return f"error: {path} does not exist"
    if not resolved.is_file():
        return f"error: {path} is not a file"
    try:
        return resolved.read_text()
    except OSError as exc:
        return f"error: could not read {path}: {exc}"


def list_files(path: str = ".") -> str:
    """List a confined directory non-recursively, sorted with `/` on directories."""
    resolved = _resolve_confined(path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.exists():
        return f"error: {path} does not exist"
    if not resolved.is_dir():
        return f"error: {path} is not a directory"
    entries = sorted(resolved.iterdir(), key=lambda entry: entry.name)
    return "\n".join(entry.name + ("/" if entry.is_dir() else "") for entry in entries)


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Create a new file or replace exactly one matching string in an existing file.

    An empty `old_str` means creation and is accepted only when the target does
    not exist. Edits require exactly one match so the tool never guesses which
    occurrence the model intended.
    """
    resolved = _resolve_confined(path)
    if isinstance(resolved, str):
        return resolved

    if old_str == "":
        if resolved.exists():
            return f"error: {path} already exists; old_str must match existing content to edit it"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(new_str)
        return f"created {path}"

    if not resolved.exists() or not resolved.is_file():
        return f"error: {path} does not exist"

    content = resolved.read_text()
    occurrences = content.count(old_str)
    if occurrences == 0:
        return f"error: old_str not found in {path}"
    if occurrences > 1:
        return f"error: old_str is ambiguous in {path} ({occurrences} occurrences)"

    resolved.write_text(content.replace(old_str, new_str, 1))
    return f"edited {path}"


# The three builtin handlers are paired with the JSON Schemas shown to the
# model. Their Python callables themselves never cross the Model boundary.
BUILTIN_TOOLS: list[Tool] = [
    Tool(
        name="read_file",
        description="Read and return the text contents of a file under the project directory.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to the file to read."}},
            "required": ["path"],
        },
        handler=read_file,
    ),
    Tool(
        name="list_files",
        description="List the immediate (non-recursive) contents of a directory under the "
        "project directory. Directory entries are suffixed with '/'.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to list. Defaults to the current directory.",
                }
            },
            "required": [],
        },
        handler=list_files,
    ),
    Tool(
        name="edit_file",
        description="Edit a file by replacing a unique occurrence of old_str with new_str. "
        "If old_str is empty and the file does not exist, creates it with new_str as its "
        "full content.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to edit or create."},
                "old_str": {
                    "type": "string",
                    "description": "Exact text to replace; must occur exactly once. Empty to "
                    "create a new file.",
                },
                "new_str": {"type": "string", "description": "Replacement text."},
            },
            "required": ["path", "old_str", "new_str"],
        },
        handler=edit_file,
    ),
]
