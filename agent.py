"""The Agent Loop: tie the Model boundary and Tool boundary together into a
bounded control loop.

Deliberately minimal for a short course -- and deliberately missing several
things a real Harness has, each cut for a specific reason:

- No streaming. There is no async generator handing partial tokens back to a
  caller, so there is nothing to cancel mid-flight -- that specific hard
  problem (tearing down an in-progress stream cleanly) does not exist here.
  `model.request()` is already a single non-streaming await.
- No cancellation handling. With no long-lived stream and no background
  tasks, there is no in-flight work a user could interrupt; the loop either
  is between steps (safe to stop by just not calling again) or it isn't
  running at all.
- No Hooks or other interception points. A real Harness lets external code
  observe or alter behavior at defined points (before a tool runs, before a
  step starts, ...). Here `on_event` is a single plain callback for a visible
  trace -- it can print, it cannot change what happens next.
- No typed Event bus. Trace lines are just strings passed to `on_event`
  (default: `print`), not a queue of structured Event objects a UI subscribes
  to. There is no UI here to subscribe.

What is left is the actual lesson: call the model, see if it asked for tools,
run the tools through the one dispatch point, feed the results back, repeat --
bounded by `max_steps` so a misbehaving model can't loop forever.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from model import ModelError, request, to_assistant_message, to_tool_message
from settings import Settings
from tools import ToolRegistry, dispatch


@dataclass(frozen=True)
class RunResult:
    status: str
    output: str | None
    error: str | None
    messages: list[dict[str, Any]]


async def run_agent(
    settings: Settings,
    task: str,
    registry: ToolRegistry,
    *,
    max_steps: int = 10,
    on_event: Callable[[str], None] = print,
) -> RunResult:
    """Run the bounded Agent Loop for `task` and return a `RunResult`.

    Three ways this can end, and only three: the model stops asking for
    tools (`"completed"`), the loop hits `max_steps` without that happening
    (`"max_steps"`), or a model request itself fails (`"failed"`).

    # Step 0: if max_steps is not a positive int, raise ValueError -- fail
    #   fast on a caller mistake rather than silently looping zero times.

    # Step 1: messages = [{"role": "user", "content": task}] -- this list is
    #   what you append to and pass to every request() call; it's also what
    #   ends up in the returned RunResult.messages.

    # Step 2: for step in range(max_steps):
    #
    #   2a. on_event(f"step {step}: requesting model"), then:
    #       try: response = await request(settings, messages, tools=registry.specs())
    #       except ModelError as exc: return RunResult(status="failed", output=None,
    #       error=str(exc), messages=messages) -- do not let ModelError escape
    #       run_agent itself.
    #
    #   2b. messages.append(to_assistant_message(response)) -- the model's turn
    #       (including any tool_calls it asked for) is now part of the transcript,
    #       same as it would be sent back on the next request.
    #
    #   2c. if not response.tool_calls: the model is done talking -- on_event(...),
    #       return RunResult(status="completed", output=response.content or "",
    #       error=None, messages=messages).
    #
    #   2d. otherwise, for call in response.tool_calls:
    #       on_event(f"  calling {call.name}({call.arguments})")
    #       result = await dispatch(registry, call)
    #       on_event(f"  -> {result}")
    #       messages.append(to_tool_message(
    #           call.id, result.error if result.error is not None else result.output
    #       ))
    #       -- every tool_call the model asked for needs a matching tool
    #       message appended, success or error, or the next request will be
    #       malformed (a dangling tool_call with no result).
    #
    #   2e. if step is the last one in range(max_steps) and you got here (the
    #       model still wanted more tool calls), return RunResult(status="max_steps",
    #       output=None, error=None, messages=messages).
    """
    raise NotImplementedError
