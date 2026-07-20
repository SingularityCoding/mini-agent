"""The Model boundary: convert between the OpenAI-compatible wire format and small,
trusted internal types.

Deliberately minimal for a short course: a single non-streaming POST to
`/chat/completions`, no retries, and no provider-quirk handling. A production
Model boundary would also stream, retry on transient failures, and likely
distinguish several error subtypes (auth, rate limit, timeout, malformed
response, ...). Here, one exception type is enough -- the lesson is the
wire<->type conversion, not a resilience or error taxonomy.

The one rule that matters: a caller must only ever see a `ModelResponse` or a
`ModelError` out of `request()` -- never a raw `httpx` exception, `KeyError`,
or `json.JSONDecodeError` leaking the wire format upward.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from settings import Settings


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelResponse:
    content: str | None
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str | None


class ModelError(Exception):
    """Any failure to get a usable ModelResponse: network, HTTP, or shape errors."""


async def request(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> ModelResponse:
    """POST a chat completion request and return a parsed ModelResponse.

    Raises ModelError for any network failure, non-2xx status, invalid JSON
    body, or response body missing required fields -- nothing else should
    ever escape this function.

    A response body looks like this (only the parts you need are shown):

        {
          "choices": [
            {
              "message": {
                "content": null,
                "tool_calls": [
                  {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                      "name": "read_file",
                      "arguments": "{\\"path\\": \\"main.py\\"}"
                    }
                  }
                ]
              },
              "finish_reason": "tool_calls"
            }
          ]
        }

    Note that `function.arguments` is a JSON-encoded *string*, not an object --
    you need `json.loads` it into a dict yourself. A plain text reply looks the
    same but with `"tool_calls"` absent (or `null`) and `content` a string.

    # Step 1: build the request body dict --
    #   {"model": settings.default_model, "messages": messages, "stream": False}
    #   plus a "tools": tools key, but only when tools is non-empty. Don't send
    #   "tools": None or "tools": [] -- omit the key entirely in that case.

    # Step 2: POST it with an httpx.AsyncClient --
    #   url: f"{settings.base_url.rstrip('/')}/chat/completions"
    #   headers: {"Authorization": f"Bearer {settings.api_key.get_secret_value()}"}
    #   timeout: settings.request_timeout_seconds
    #   Wrap the request in try/except: httpx.HTTPError (covers timeouts and
    #   connection failures) -> raise ModelError(...) from exc. Also check
    #   response.status_code -- anything outside 200-299 -> raise ModelError
    #   naming the status code and response text.

    # Step 3: parse the body -- response.json(), wrapped in try/except for
    #   json.JSONDecodeError -> ModelError.

    # Step 4: pull the fields out of the parsed dict, all defensively (use
    #   .get, not []; a missing "choices" list or "message" key should become
    #   a ModelError naming what was missing, not a KeyError/IndexError):
    #   - content = message.get("content")
    #   - finish_reason = choices[0].get("finish_reason")
    #   - tool_calls: for each entry in message.get("tool_calls") or [], build
    #     a ToolCall(id=entry["id"], name=entry["function"]["name"],
    #     arguments=json.loads(entry["function"]["arguments"])) -- a
    #     json.JSONDecodeError here should also become a ModelError, not crash.
    #   Return ModelResponse(content=content, tool_calls=tuple(...), finish_reason=finish_reason).
    """
    raise NotImplementedError


def to_assistant_message(response: ModelResponse) -> dict[str, Any]:
    """Serialize a ModelResponse back into a wire-format assistant message.

    Used by the Agent Loop to feed a completed turn back into `messages` for
    the next request.

    TODO: {"role": "assistant", "content": response.content}, plus a "tool_calls"
    key (only when response.tool_calls is non-empty) shaped like the wire format:
    [{"id": call.id, "type": "function", "function": {"name": call.name,
    "arguments": json.dumps(call.arguments)}}, ...].
    """
    raise NotImplementedError


def to_tool_message(call_id: str, output: str) -> dict[str, Any]:
    """Serialize a tool's output into a wire-format tool result message.

    TODO: {"role": "tool", "tool_call_id": call_id, "content": output}.
    """
    raise NotImplementedError
