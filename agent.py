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

    TODO, roughly in this order:
    - Validate max_steps is a positive int (raise ValueError otherwise).
    - messages = [{"role": "user", "content": task}].
    - for step in range(max_steps):
        - call request(settings, messages, tools=registry.specs()); a
          ModelError should become RunResult(status="failed", output=None,
          error=str(exc), messages=messages) -- don't let it escape run_agent.
        - append to_assistant_message(response) to messages.
        - if response.tool_calls is empty: the model is done -- return
          RunResult(status="completed", output=response.content or "",
          error=None, messages=messages).
        - otherwise, for each call: dispatch(registry, call), then append
          to_tool_message(call.id, result.error if result.error is not None
          else result.output) to messages.
        - if this was the last allowed step, return RunResult(status="max_steps",
          output=None, error=None, messages=messages).
    - Call on_event(...) with a short trace line before/after the interesting
      steps above (which model call, which tool call, what it returned) -- there
      is no TUI here, on_event is the only observability you get.
    """
    raise NotImplementedError
