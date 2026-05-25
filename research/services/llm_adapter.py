from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalisedToolCall:
    """A tool call extracted from the LLM response, provider-independent.

    Attributes:
        id: Provider-assigned identifier used to correlate tool results.
        name: Tool function name to dispatch.
        arguments: Parsed JSON arguments as a Python dict.
    """

    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """Normalised LLM response returned by :meth:`LLMAdapter.create_completion`.

    Attributes:
        stop_reason: ``"end_turn"`` when the model produced a final answer,
            ``"tool_calls"`` when it requested one or more tool invocations.
        text: Model's final answer text; set only when ``stop_reason == "end_turn"``.
        tool_calls: Extracted tool calls; non-empty when ``stop_reason == "tool_calls"``.
        input_tokens: Prompt tokens consumed by this call.
        output_tokens: Completion tokens produced by this call.
        _raw: Original provider response object, passed to
            :meth:`LLMAdapter.append_assistant_message`.
    """

    stop_reason: str
    text: str | None
    tool_calls: list[NormalisedToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    _raw: Any = field(default=None, repr=False)


class LLMAdapter(ABC):
    """Provider-agnostic interface for LLM tool-use loops.

    Concrete subclasses translate between the canonical tool format and
    provider-specific wire formats, and normalise responses into
    :class:`LLMResponse` so ``agent.py`` stays provider-agnostic.
    """

    @abstractmethod
    def format_tools(self, canonical_tools: list[dict]) -> list[dict]:
        """Transform canonical tool specs to provider-specific format.

        Args:
            canonical_tools: Tool specs in canonical internal format.

        Returns:
            Provider-formatted tool list ready to pass to the API.
        """

    @abstractmethod
    def create_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Make one LLM call and return a normalised :class:`LLMResponse`.

        Args:
            system_prompt: System instruction string.
            messages: Conversation history (user/assistant turns).
            tools: Provider-formatted tool list from :meth:`format_tools`.
            max_tokens: Maximum tokens to generate.

        Returns:
            Normalised response with stop reason, text, and tool calls.
        """

    @abstractmethod
    def append_assistant_message(
        self,
        messages: list[dict],
        response: LLMResponse,
    ) -> None:
        """Append the assistant turn to messages in-place.

        Args:
            messages: Conversation history list to mutate.
            response: The :class:`LLMResponse` returned by :meth:`create_completion`.
        """

    @abstractmethod
    def append_tool_results(
        self,
        messages: list[dict],
        tool_calls: list[NormalisedToolCall],
        results: list[str],
    ) -> None:
        """Append tool result messages to messages in-place.

        Args:
            messages: Conversation history list to mutate.
            tool_calls: The tool calls that produced these results.
            results: Result strings, aligned 1-to-1 with ``tool_calls``.
        """


class OpenAIAdapter(LLMAdapter):
    """LLM adapter for the OpenAI chat completions API.

    Args:
        client: An ``openai.OpenAI`` instance (injected to avoid top-level import).
        model: Model identifier, e.g. ``"gpt-4o"``.
    """

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self.model = model

    def format_tools(self, canonical_tools: list[dict]) -> list[dict]:
        """Wrap each tool in the OpenAI ``{"type": "function", "function": {...}}`` envelope.

        Args:
            canonical_tools: Tool specs in canonical internal format.

        Returns:
            OpenAI-formatted tool list.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in canonical_tools
        ]

    def create_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Call the OpenAI chat completions endpoint and normalise the response.

        The system prompt is prepended as the first message in the list.

        Args:
            system_prompt: System instruction string.
            messages: Conversation history (user/assistant turns).
            tools: OpenAI-formatted tools from :meth:`format_tools`.
            max_tokens: Maximum tokens to generate.

        Returns:
            Normalised :class:`LLMResponse`.
        """
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = self._client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        msg = response.choices[0].message
        finish = response.choices[0].finish_reason
        stop_reason = "tool_calls" if finish == "tool_calls" else "end_turn"
        text = msg.content if stop_reason == "end_turn" else None
        tool_calls = [
            NormalisedToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
            )
            for tc in (msg.tool_calls or [])
        ]
        return LLMResponse(
            stop_reason=stop_reason,
            text=text,
            tool_calls=tool_calls,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            _raw=response,
        )

    def append_assistant_message(
        self,
        messages: list[dict],
        response: LLMResponse,
    ) -> None:
        """Append the raw OpenAI message object to the conversation history.

        Args:
            messages: Conversation history list to mutate.
            response: The :class:`LLMResponse` whose ``_raw`` holds the API response.
        """
        messages.append(response._raw.choices[0].message)

    def append_tool_results(
        self,
        messages: list[dict],
        tool_calls: list[NormalisedToolCall],
        results: list[str],
    ) -> None:
        """Append one ``role: tool`` message per tool call.

        OpenAI requires each result as a separate message keyed by ``tool_call_id``.

        Args:
            messages: Conversation history list to mutate.
            tool_calls: The tool calls that produced these results.
            results: Result strings, aligned 1-to-1 with ``tool_calls``.
        """
        for tc, result in zip(tool_calls, results):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )


class AnthropicAdapter(LLMAdapter):
    """LLM adapter for the Anthropic messages API.

    Args:
        client: An ``anthropic.Anthropic`` instance (injected to avoid top-level import).
        model: Model identifier, e.g. ``"claude-sonnet-4-6"``.
    """

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self.model = model

    def format_tools(self, canonical_tools: list[dict]) -> list[dict]:
        """Rename ``parameters`` to ``input_schema`` per the Anthropic tool spec.

        Args:
            canonical_tools: Tool specs in canonical internal format.

        Returns:
            Anthropic-formatted tool list.
        """
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            }
            for tool in canonical_tools
        ]

    def create_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Call the Anthropic messages endpoint and normalise the response.

        The system prompt is passed as the ``system`` kwarg, not as a message.

        Args:
            system_prompt: System instruction string.
            messages: Conversation history (user/assistant turns).
            tools: Anthropic-formatted tools from :meth:`format_tools`.
            max_tokens: Maximum tokens to generate.

        Returns:
            Normalised :class:`LLMResponse`.
        """
        response = self._client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        stop_reason = (
            "end_turn" if response.stop_reason == "end_turn" else "tool_calls"
        )
        text = (
            next(
                (b.text for b in response.content if b.type == "text"),
                None,
            )
            if stop_reason == "end_turn"
            else None
        )
        tool_calls = [
            NormalisedToolCall(
                id=b.id,
                name=b.name,
                arguments=b.input,
            )
            for b in response.content
            if b.type == "tool_use"
        ]
        return LLMResponse(
            stop_reason=stop_reason,
            text=text,
            tool_calls=tool_calls,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            _raw=response,
        )

    def append_assistant_message(
        self,
        messages: list[dict],
        response: LLMResponse,
    ) -> None:
        """Append the assistant content block list to the conversation history.

        Args:
            messages: Conversation history list to mutate.
            response: The :class:`LLMResponse` whose ``_raw`` holds the API response.
        """
        messages.append(
            {
                "role": "assistant",
                "content": response._raw.content,
            }
        )

    def append_tool_results(
        self,
        messages: list[dict],
        tool_calls: list[NormalisedToolCall],
        results: list[str],
    ) -> None:
        """Append all tool results in a single ``role: user`` message.

        Anthropic requires all results from one round to be batched into one
        user message; separate messages cause a validation error.

        Args:
            messages: Conversation history list to mutate.
            tool_calls: The tool calls that produced these results.
            results: Result strings, aligned 1-to-1 with ``tool_calls``.
        """
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": result,
                    }
                    for tc, result in zip(tool_calls, results)
                ],
            }
        )


def get_llm_adapter(provider: str | None = None) -> LLMAdapter:
    """Return the configured :class:`LLMAdapter` for the active provider.

    Reads ``settings.LLM_PROVIDER`` when ``provider`` is not supplied.
    Imports the provider SDK lazily so ``agent.py`` never needs to import
    ``openai`` or ``anthropic`` directly.

    Args:
        provider: Override string (``"openai"`` or ``"anthropic"``).
            Defaults to ``settings.LLM_PROVIDER``.

    Returns:
        A ready-to-use :class:`LLMAdapter` instance.

    Raises:
        django.core.exceptions.ImproperlyConfigured: If the provider is
            unknown or the required API key is blank.
    """
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured

    p = provider or settings.LLM_PROVIDER

    if p == "openai":
        if not settings.OPENAI_API_KEY:
            raise ImproperlyConfigured(
                "OPENAI_API_KEY must be set when LLM_PROVIDER=openai"
            )
        import openai

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return OpenAIAdapter(client=client, model=settings.OPENAI_MODEL)

    if p == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ImproperlyConfigured(
                "ANTHROPIC_API_KEY must be set when LLM_PROVIDER=anthropic"
            )
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return AnthropicAdapter(client=client, model=settings.ANTHROPIC_MODEL)

    if p == "ollama":
        import openai

        client = openai.OpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL.rstrip('/')}/v1",
            api_key="ollama",
        )
        return OpenAIAdapter(client=client, model=settings.OLLAMA_MODEL)

    raise ImproperlyConfigured(
        f"Unknown LLM_PROVIDER {p!r}. Valid values: 'openai', 'anthropic', 'ollama'."
    )
