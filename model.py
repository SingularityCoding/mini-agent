"""The Model boundary: convert between the OpenAI-compatible wire format and small,

trusted internal types.

Deliberately minimal for a short course: a single non-streaming POST to
`/chat/completions`, no retries, and no provider-quirk handling. A production
Model boundary would also stream, retry on transient failures, and likely
distinguish several error subtypes (auth, rate limit, timeout, malformed
response, ...). Here, one exception type is enough -- the lesson is the
wire<->type conversion, not a resilience or error taxonomy.

The one rule that matters: a Harness caller must only ever see a `ModelResponse`
or a `ModelError` out of `request()` -- never a raw `httpx` exception, `KeyError`,
or `json.JSONDecodeError` leaking the wire format upward.
"""

from __future__ import annotations

import json
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
    """Any failure to get a usable ModelResponse: network, HTTP, or shape errors.

    A production Model boundary would likely split this into subtypes (auth,
    rate limit, timeout, malformed response, ...) so callers could react
    differently. That taxonomy is deliberately skipped here.
    """


async def request(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> ModelResponse:
    """POST a chat completion request and return a parsed ModelResponse.

    Raises ModelError for any network failure, non-2xx status, invalid JSON
    body, or response body missing required fields.
    """
    url = f"{settings.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    body: dict[str, Any] = {
        "model": settings.default_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        body["tools"] = tools

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            http_response = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ModelError(f"request to model failed: {exc!r}") from exc

    if http_response.status_code < 200 or http_response.status_code >= 300:
        raise ModelError(
            f"model request returned HTTP {http_response.status_code}: {http_response.text}"
        )

    try:
        payload = http_response.json()
    except json.JSONDecodeError as exc:
        raise ModelError(f"model response was not valid JSON: {exc}") from exc

    try:
        choices = payload["choices"]
        message = choices[0]["message"]
        finish_reason = choices[0].get("finish_reason")
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelError(f"model response missing expected 'choices[0].message': {exc}") from exc

    if not isinstance(message, dict):
        raise ModelError(f"model response 'message' was not an object: {message!r}")

    content = message.get("content")

    tool_calls: list[ToolCall] = []
    for raw_call in message.get("tool_calls") or []:
        try:
            call_id = raw_call["id"]
            function = raw_call["function"]
            name = function["name"]
            raw_arguments = function["arguments"]
        except (KeyError, TypeError) as exc:
            raise ModelError(f"model response tool call missing expected field: {exc}") from exc

        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ModelError(
                f"model response tool call {call_id!r} had invalid JSON arguments: {exc}"
            ) from exc

        tool_calls.append(ToolCall(id=call_id, name=name, arguments=arguments))

    return ModelResponse(
        content=content,
        tool_calls=tuple(tool_calls),
        finish_reason=finish_reason,
    )


def to_assistant_message(response: ModelResponse) -> dict[str, Any]:
    """Serialize a ModelResponse back into a wire-format assistant message.

    Used by the Agent Loop to feed a completed turn back into `messages` for
    the next request.
    """
    message: dict[str, Any] = {"role": "assistant", "content": response.content}
    if response.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in response.tool_calls
        ]
    return message


def to_tool_message(call_id: str, output: str) -> dict[str, Any]:
    """Serialize a tool's output into a wire-format tool result message."""
    return {"role": "tool", "tool_call_id": call_id, "content": output}
