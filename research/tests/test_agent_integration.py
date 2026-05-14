from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research.models import Repository, ResearchSession, ToolCall
from research.services.agent import run
from research.services.llm_adapter import LLMResponse, NormalisedToolCall

_REPO_URL = "https://github.com/test/repo"


def _make_mock_adapter() -> MagicMock:
    """Return a mock LLMAdapter scripted for a one-tool-call then end-turn sequence."""
    tool_call_response = LLMResponse(
        stop_reason="tool_calls",
        text=None,
        tool_calls=[
            NormalisedToolCall(
                id="tc_1",
                name="get_previous_findings",
                arguments={"repo_url": _REPO_URL},
            )
        ],
        input_tokens=100,
        output_tokens=20,
    )
    end_turn_response = LLMResponse(
        stop_reason="end_turn",
        text="FastAPI uses DI in dependencies/utils.py",
        tool_calls=[],
        input_tokens=150,
        output_tokens=50,
    )

    adapter = MagicMock()
    adapter.format_tools.return_value = []
    adapter.create_completion.side_effect = [tool_call_response, end_turn_response]
    return adapter


@pytest.mark.django_db
def test_agent_completes_with_tool_call_then_end_turn() -> None:
    """Agent persists one ToolCall, reaches COMPLETE, and sets final_answer."""
    repo = Repository.from_url(_REPO_URL)
    session = ResearchSession.objects.create(
        repository=repo,
        question="How is dependency injection implemented?",
    )

    mock_adapter = _make_mock_adapter()

    with (
        patch("research.services.agent.get_llm_adapter", return_value=mock_adapter),
        patch(
            "research.services.agent.clone_or_update",
            return_value=(Path("/fake/repo"), "a" * 40),
        ),
        patch(
            "research.services.agent.dispatch",
            return_value="No prior findings.",
        ),
    ):
        result = run(session)

    assert result.status == ResearchSession.Status.COMPLETE
    assert result.final_answer == "FastAPI uses DI in dependencies/utils.py"
    assert result.iterations == 2
    assert result.input_tokens > 0

    assert ToolCall.objects.filter(session=result).count() == 1
    tc = ToolCall.objects.get(session=result)
    assert tc.tool_name == "get_previous_findings"
    assert tc.sequence == 0
