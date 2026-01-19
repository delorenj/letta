"""Translate between OpenAI and Anthropic API formats."""

from typing import Any


# Model mapping: OpenAI-style names to Anthropic model IDs
MODEL_MAP = {
    # Direct Anthropic models
    "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229": "claude-3-opus-20240229",
    "claude-3-sonnet-20240229": "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307": "claude-3-haiku-20240307",
    # Aliases for convenience
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3.5-haiku": "claude-3-5-haiku-20241022",
    "claude-opus-4": "claude-opus-4-20250514",
    # Latest aliases
    "claude-sonnet": "claude-sonnet-4-20250514",
    "claude-opus": "claude-opus-4-20250514",
}


def translate_model(openai_model: str) -> str:
    """Translate OpenAI model name to Anthropic model ID."""
    return MODEL_MAP.get(openai_model, openai_model)


def openai_to_anthropic_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """
    Convert OpenAI messages format to Anthropic format.

    Returns (system_prompt, messages) tuple.
    Anthropic requires system prompt separate from messages.
    """
    system_prompt = None
    anthropic_messages = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            # Anthropic takes system as separate parameter
            if system_prompt:
                system_prompt += "\n\n" + content
            else:
                system_prompt = content
        elif role == "user":
            anthropic_messages.append({"role": "user", "content": content})
        elif role == "assistant":
            anthropic_messages.append({"role": "assistant", "content": content})
        elif role == "tool":
            # Tool results in Anthropic format
            anthropic_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", ""),
                    "content": content,
                }],
            })

    return system_prompt, anthropic_messages


def openai_to_anthropic_tools(tools: list[dict] | None) -> list[dict] | None:
    """Convert OpenAI tools format to Anthropic format."""
    if not tools:
        return None

    anthropic_tools = []
    for tool in tools:
        if tool.get("type") != "function":
            continue

        func = tool.get("function", {})
        anthropic_tools.append({
            "name": func.get("name", ""),
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {}),
        })

    return anthropic_tools if anthropic_tools else None


def openai_to_anthropic_request(openai_request: dict) -> dict:
    """Convert full OpenAI chat completion request to Anthropic format."""
    messages = openai_request.get("messages", [])
    system_prompt, anthropic_messages = openai_to_anthropic_messages(messages)

    anthropic_request = {
        "model": translate_model(openai_request.get("model", "")),
        "messages": anthropic_messages,
        "max_tokens": openai_request.get("max_tokens", 4096),
    }

    # Add system prompt if present
    if system_prompt:
        anthropic_request["system"] = system_prompt

    # Temperature (Anthropic uses 0-1 range like OpenAI)
    if "temperature" in openai_request:
        anthropic_request["temperature"] = openai_request["temperature"]

    # Top P
    if "top_p" in openai_request:
        anthropic_request["top_p"] = openai_request["top_p"]

    # Stop sequences
    if "stop" in openai_request:
        stop = openai_request["stop"]
        if isinstance(stop, str):
            anthropic_request["stop_sequences"] = [stop]
        elif isinstance(stop, list):
            anthropic_request["stop_sequences"] = stop

    # Tools
    tools = openai_to_anthropic_tools(openai_request.get("tools"))
    if tools:
        anthropic_request["tools"] = tools

    # Stream
    if openai_request.get("stream"):
        anthropic_request["stream"] = True

    return anthropic_request


def anthropic_to_openai_response(anthropic_response: dict, model: str) -> dict:
    """Convert Anthropic response to OpenAI format."""
    content_blocks = anthropic_response.get("content", [])

    # Extract text content and tool calls
    text_content = ""
    tool_calls = []

    for i, block in enumerate(content_blocks):
        if block.get("type") == "text":
            text_content += block.get("text", "")
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id", f"call_{i}"),
                "type": "function",
                "function": {
                    "name": block.get("name", ""),
                    "arguments": _serialize_json(block.get("input", {})),
                },
            })

    # Build OpenAI-style message
    message: dict[str, Any] = {
        "role": "assistant",
        "content": text_content if text_content else None,
    }

    if tool_calls:
        message["tool_calls"] = tool_calls

    # Map finish reason
    stop_reason = anthropic_response.get("stop_reason", "end_turn")
    finish_reason_map = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop",
        "tool_use": "tool_calls",
    }
    finish_reason = finish_reason_map.get(stop_reason, "stop")

    # Build usage
    usage = anthropic_response.get("usage", {})
    openai_usage = {
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
    }

    return {
        "id": anthropic_response.get("id", "chatcmpl-anthropic"),
        "object": "chat.completion",
        "created": int(__import__("time").time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": finish_reason,
        }],
        "usage": openai_usage,
    }


def anthropic_stream_to_openai_stream(event_type: str, data: dict, model: str) -> dict | None:
    """Convert Anthropic streaming event to OpenAI SSE format."""
    if event_type == "message_start":
        return {
            "id": data.get("message", {}).get("id", "chatcmpl-anthropic"),
            "object": "chat.completion.chunk",
            "created": int(__import__("time").time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None,
            }],
        }

    elif event_type == "content_block_delta":
        delta = data.get("delta", {})
        if delta.get("type") == "text_delta":
            return {
                "id": "chatcmpl-anthropic",
                "object": "chat.completion.chunk",
                "created": int(__import__("time").time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": delta.get("text", "")},
                    "finish_reason": None,
                }],
            }
        elif delta.get("type") == "input_json_delta":
            # Tool call argument streaming
            return {
                "id": "chatcmpl-anthropic",
                "object": "chat.completion.chunk",
                "created": int(__import__("time").time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "tool_calls": [{
                            "index": data.get("index", 0),
                            "function": {"arguments": delta.get("partial_json", "")},
                        }]
                    },
                    "finish_reason": None,
                }],
            }

    elif event_type == "content_block_start":
        block = data.get("content_block", {})
        if block.get("type") == "tool_use":
            return {
                "id": "chatcmpl-anthropic",
                "object": "chat.completion.chunk",
                "created": int(__import__("time").time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "tool_calls": [{
                            "index": data.get("index", 0),
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {"name": block.get("name", ""), "arguments": ""},
                        }]
                    },
                    "finish_reason": None,
                }],
            }

    elif event_type == "message_delta":
        delta = data.get("delta", {})
        stop_reason = delta.get("stop_reason")
        if stop_reason:
            finish_reason_map = {
                "end_turn": "stop",
                "max_tokens": "length",
                "stop_sequence": "stop",
                "tool_use": "tool_calls",
            }
            return {
                "id": "chatcmpl-anthropic",
                "object": "chat.completion.chunk",
                "created": int(__import__("time").time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": finish_reason_map.get(stop_reason, "stop"),
                }],
            }

    elif event_type == "message_stop":
        return {
            "id": "chatcmpl-anthropic",
            "object": "chat.completion.chunk",
            "created": int(__import__("time").time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
        }

    return None


def _serialize_json(obj: Any) -> str:
    """Serialize object to JSON string."""
    import json
    return json.dumps(obj)
