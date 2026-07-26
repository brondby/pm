"""Unit tests for OpenRouter client and structured output parsing."""

from __future__ import annotations

import json

import httpx
import pytest

from backend.ai.openrouter_ai import AIServiceError, parse_structured_output, request_openrouter


class _MockResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _provider_payload(content):
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ]
    }


def test_parse_structured_output_accepts_valid_json():
    reply, operations = parse_structured_output(
        _provider_payload(
            json.dumps(
                {
                    "reply": "Renamed column.",
                    "operations": [{"type": "rename_column", "column_title": "Backlog", "new_title": "Ideas"}],
                }
            )
        )
    )

    assert reply == "Renamed column."
    assert operations == [{"type": "rename_column", "column_title": "Backlog", "new_title": "Ideas"}]


def test_parse_structured_output_strips_json_code_fence():
    reply, operations = parse_structured_output(
        _provider_payload(
            """```json
{"reply":"No changes needed.","operations":[]}
```"""
        )
    )

    assert reply == "No changes needed."
    assert operations == []


def test_parse_structured_output_rejects_non_json_prose():
    with pytest.raises(AIServiceError) as error:
        parse_structured_output(_provider_payload("Here is your result: not json"))

    assert "invalid json output" in error.value.detail.lower()


def test_parse_structured_output_rejects_board_replacement_payload():
    with pytest.raises(AIServiceError) as error:
        parse_structured_output(
            _provider_payload(
                json.dumps(
                    {
                        "reply": "Applied update.",
                        "operations": [],
                        "board": {"columns": [], "cards": {}},
                    }
                )
            )
        )

    assert "unsupported response shape" in error.value.detail.lower()


def test_parse_structured_output_rejects_malformed_operation_entry():
    with pytest.raises(AIServiceError) as error:
        parse_structured_output(_provider_payload(json.dumps({"reply": "test", "operations": ["bad"]})))

    assert "operation at index 0 must be an object" in error.value.detail.lower()


def test_request_openrouter_includes_max_tokens_and_defaults(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("AI_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("AI_MAX_TOKENS", raising=False)

    captured: dict = {}

    def _mock_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _MockResponse(200, _provider_payload('{"reply":"ok","operations":[]}'))

    monkeypatch.setattr("backend.ai.openrouter_ai.httpx.post", _mock_post)

    payload = request_openrouter("sys", "user")
    assert isinstance(payload, dict)
    assert captured["json"]["model"] == "openai/gpt-oss-120b"
    assert captured["json"]["max_tokens"] == 1200
    assert captured["json"]["temperature"] == 0
    assert captured["timeout"] == 20.0


def test_request_openrouter_uses_configured_model_timeout_and_max_tokens(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "9.5")
    monkeypatch.setenv("AI_MAX_TOKENS", "800")

    captured: dict = {}

    def _mock_post(url, headers, json, timeout):
        captured["json"] = json
        captured["timeout"] = timeout
        return _MockResponse(200, _provider_payload('{"reply":"ok","operations":[]}'))

    monkeypatch.setattr("backend.ai.openrouter_ai.httpx.post", _mock_post)

    request_openrouter("sys", "user")
    assert captured["json"]["max_tokens"] == 800
    assert captured["timeout"] == 9.5


def test_request_openrouter_handles_timeout(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("backend.ai.openrouter_ai.httpx.post", _raise_timeout)

    with pytest.raises(AIServiceError) as error:
        request_openrouter("sys", "user")

    assert error.value.status_code == 502
    assert "timed out" in error.value.detail.lower()


def test_request_openrouter_handles_http_error(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    monkeypatch.setattr(
        "backend.ai.openrouter_ai.httpx.post",
        lambda *args, **kwargs: _MockResponse(500, {"error": "provider failure"}),
    )

    with pytest.raises(AIServiceError) as error:
        request_openrouter("sys", "user")

    assert error.value.status_code == 502
    assert "provider request failed" in error.value.detail.lower()


def test_request_openrouter_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(AIServiceError) as error:
        request_openrouter("sys", "user")

    assert error.value.status_code == 500
    assert "not configured" in error.value.detail.lower()