"""OpenRouter HTTP client and structured response parsing for Part 9."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_AI_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_TOKENS = 1200


class AIServiceError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _extract_text_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIServiceError("AI returned an empty response. Please try again.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise AIServiceError("AI returned an invalid response format. Please try again.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise AIServiceError("AI returned an invalid response format. Please try again.")

    content = message.get("content")
    if isinstance(content, str):
        text = content.strip()
        if not text:
            raise AIServiceError("AI returned an empty response. Please try again.")
        return text

    if isinstance(content, list):
        fragments: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                fragments.append(item["text"])
        text = "".join(fragments).strip()
        if not text:
            raise AIServiceError("AI returned an empty response. Please try again.")
        return text

    raise AIServiceError("AI returned an invalid response format. Please try again.")


def _strip_code_fence(value: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("```") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return trimmed


def _parse_float_env(name: str, default_value: float) -> float:
    raw_value = os.getenv(name, str(default_value)).strip()
    try:
        parsed = float(raw_value)
    except ValueError:
        return default_value
    if parsed <= 0:
        return default_value
    return parsed


def _parse_int_env(name: str, default_value: int) -> int:
    raw_value = os.getenv(name, str(default_value)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return default_value
    if parsed <= 0:
        return default_value
    return parsed


def parse_structured_output(provider_payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Parse provider payload into (reply, operations)."""
    raw_content = _extract_text_content(provider_payload)
    content = _strip_code_fence(raw_content)

    try:
        parsed = json.loads(content)
    except ValueError as error:
        raise AIServiceError("AI returned invalid JSON output. Please try again.") from error

    if not isinstance(parsed, dict):
        raise AIServiceError("AI returned invalid JSON output. Please try again.")

    if "board" in parsed:
        raise AIServiceError("AI returned an unsupported response shape. Please try again.")

    reply = parsed.get("reply")
    operations = parsed.get("operations", [])

    if not isinstance(reply, str) or not reply.strip():
        raise AIServiceError('AI response is missing a valid "reply".')

    if not isinstance(operations, list):
        raise AIServiceError('AI response has an invalid "operations" field.')

    normalized_operations: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise AIServiceError(f"Operation at index {index} must be an object.")
        normalized_operations.append(operation)

    return reply.strip(), normalized_operations


def request_openrouter(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Call OpenRouter chat completion endpoint and return provider JSON."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise AIServiceError("AI service is not configured.", status_code=500)

    model = os.getenv("AI_MODEL", DEFAULT_AI_MODEL).strip() or DEFAULT_AI_MODEL
    timeout_seconds = _parse_float_env("AI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    max_tokens = _parse_int_env("AI_MAX_TOKENS", DEFAULT_MAX_TOKENS)

    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }

    try:
        response = httpx.post(
            OPENROUTER_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "pm-mvp",
            },
            json=request_payload,
            timeout=timeout_seconds,
        )
    except httpx.TimeoutException as error:
        raise AIServiceError("AI request timed out. Please try again.", status_code=502) from error
    except httpx.HTTPError as error:
        raise AIServiceError("AI service is temporarily unavailable. Please try again.", status_code=502) from error

    if response.status_code >= 400:
        raise AIServiceError("AI provider request failed. Please try again.", status_code=502)

    try:
        return response.json()
    except ValueError as error:
        raise AIServiceError("AI provider returned invalid JSON. Please try again.", status_code=502) from error