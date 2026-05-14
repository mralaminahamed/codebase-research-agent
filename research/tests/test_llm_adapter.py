from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured

from research.services.llm_adapter import (
    AnthropicAdapter,
    LLMResponse,
    NormalisedToolCall,
    OpenAIAdapter,
    get_llm_adapter,
)

_ECHO_TOOL = {
    "name": "echo",
    "description": "Echo the input back.",
    "parameters": {"type": "object", "properties": {}},
}


def test_openai_format_tools_wraps_in_function_envelope() -> None:
    """OpenAIAdapter.format_tools wraps each tool in the OpenAI function envelope."""
    adapter = OpenAIAdapter(client=MagicMock(), model="gpt-4o")
    result = adapter.format_tools([_ECHO_TOOL])

    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "echo"
    assert "parameters" in result[0]["function"]


def test_anthropic_format_tools_renames_parameters_to_input_schema() -> None:
    """AnthropicAdapter.format_tools renames 'parameters' key to 'input_schema'."""
    adapter = AnthropicAdapter(client=MagicMock(), model="claude-sonnet-4-6")
    result = adapter.format_tools([_ECHO_TOOL])

    assert result[0]["name"] == "echo"
    assert "input_schema" in result[0]
    assert "parameters" not in result[0]


def test_openai_adapter_normalises_end_turn_response() -> None:
    """OpenAIAdapter.create_completion returns correct LLMResponse for a final answer."""
    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content="Final answer", tool_calls=None),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50),
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    adapter = OpenAIAdapter(client=mock_client, model="gpt-4o")
    response = adapter.create_completion(
        system_prompt="You are a helpful agent.",
        messages=[{"role": "user", "content": "Hello"}],
        tools=[],
    )

    assert isinstance(response, LLMResponse)
    assert response.stop_reason == "end_turn"
    assert response.text == "Final answer"
    assert response.tool_calls == []
    assert response.input_tokens == 100
    assert response.output_tokens == 50


def test_anthropic_adapter_normalises_end_turn_response() -> None:
    """AnthropicAdapter.create_completion returns correct LLMResponse for a final answer."""
    mock_response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text="Final answer")],
        usage=SimpleNamespace(input_tokens=80, output_tokens=40),
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    adapter = AnthropicAdapter(client=mock_client, model="claude-sonnet-4-6")
    response = adapter.create_completion(
        system_prompt="You are a helpful agent.",
        messages=[{"role": "user", "content": "Hello"}],
        tools=[],
    )

    assert isinstance(response, LLMResponse)
    assert response.stop_reason == "end_turn"
    assert response.text == "Final answer"
    assert response.tool_calls == []
    assert response.input_tokens == 80
    assert response.output_tokens == 40


def test_get_llm_adapter_raises_for_unknown_provider() -> None:
    """get_llm_adapter raises ImproperlyConfigured for an unrecognised provider."""
    with pytest.raises(ImproperlyConfigured, match="Unknown LLM_PROVIDER"):
        get_llm_adapter("invalid")
