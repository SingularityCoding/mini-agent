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
    body, or response body missing required fields.

    TODO:
    - Build the request body: {"model": settings.default_model, "messages": messages,
      "stream": False}, plus "tools": tools when tools is non-empty.
    - POST to f"{settings.base_url.rstrip('/')}/chat/completions" with an
      httpx.AsyncClient, an "Authorization: Bearer {settings.api_key.get_secret_value()}"
      header, and settings.request_timeout_seconds as the timeout.
    - Convert network/timeout failures, non-2xx status codes, and a body that
      isn't valid JSON into ModelError -- don't let the raw httpx/json exception
      escape this function.
    - Parse choices[0].message.content (may be null), choices[0].message.tool_calls
      (may be absent -- each entry has an id, function.name, and function.arguments,
      which is a JSON-encoded *string* you need to json.loads into a dict), and
      choices[0].finish_reason. Any missing/malformed field should become a
      ModelError naming what was wrong, not a KeyError.
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
