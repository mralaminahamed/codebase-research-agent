from __future__ import annotations

import time

from django.conf import settings
from django.utils import timezone

from research.models import ResearchSession, ToolCall
from research.services.llm_adapter import get_llm_adapter
from research.services.repo_service import clone_or_update
from research.services.tool_registry import CANONICAL_TOOLS, dispatch

_SYSTEM_PROMPT = """\
You are a codebase research agent. You are analysing the repository
at {repo_url} to answer this question:

  {question}

The repository has been cloned locally. You have access to seven tools:
four for exploring the codebase and three for reading and writing your
session database.

RULES YOU MUST FOLLOW:

1. Your FIRST tool call must always be get_previous_findings(repo_url).
   If prior sessions found relevant locations, build on them.
   Do not re-explore what is already known.

2. Use list_files to orient, search_code to locate, read_file to confirm.
   Do not read the same file twice — read once, record with save_finding.

3. Call save_finding whenever you identify a specific file, function,
   or line range relevant to the question. Do not wait until the end.

4. Your final answer must cite specific file paths and, where possible,
   line numbers. A correct but uncited answer is incomplete.

5. Stop when you have enough information. You have at most
   {MAX_AGENT_ITERATIONS} tool calls. Use them wisely."""


def run(session: ResearchSession) -> ResearchSession:
    """Execute the tool-use agent loop for the given session.

    Clones the repository, loads prior findings, then iterates tool calls
    until the model produces a final answer or a stopping condition is met.
    All tool calls are persisted. The session is updated in-place and saved.

    Args:
        session: A ``PENDING`` :class:`~research.models.ResearchSession` to run.

    Returns:
        The updated session with ``status`` set to ``COMPLETE`` or ``FAILED``.
    """
    # 1. Clone / update the repository.
    repo_path, commit_sha = clone_or_update(session.repository.url)
    session.repository.commit_sha = commit_sha
    session.repository.last_indexed_at = timezone.now()
    session.repository.save(update_fields=["commit_sha", "last_indexed_at"])

    # 2. Initialise adapter, tools, and session state.
    adapter = get_llm_adapter()
    formatted_tools = adapter.format_tools(CANONICAL_TOOLS)
    messages: list[dict] = []
    session.status = ResearchSession.Status.RUNNING
    session.save(update_fields=["status"])

    # 3. Build system prompt with session-specific values.
    system_prompt = _SYSTEM_PROMPT.format(
        repo_url=session.repository.url,
        question=session.question,
        MAX_AGENT_ITERATIONS=settings.MAX_AGENT_ITERATIONS,
    )

    # 4. Seed conversation with the user's question.
    messages.append({"role": "user", "content": session.question})

    # 5. Agent loop.
    for iteration in range(settings.MAX_AGENT_ITERATIONS):

        # a. Token budget guard.
        if session.input_tokens >= settings.MAX_INPUT_TOKENS:
            session.status = ResearchSession.Status.FAILED
            session.error = "Token budget exceeded"
            break

        # b. LLM call.
        try:
            response = adapter.create_completion(
                system_prompt,
                messages,
                formatted_tools,
                max_tokens=1024,
            )
        except Exception as exc:  # noqa: BLE001
            session.status = ResearchSession.Status.FAILED
            session.error = f"LLM API error: {exc}"
            break

        # c. Accumulate usage.
        session.input_tokens += response.input_tokens
        session.output_tokens += response.output_tokens
        session.iterations += 1

        # d. Natural end.
        if response.stop_reason == "end_turn":
            session.final_answer = response.text or ""
            session.status = ResearchSession.Status.COMPLETE
            break

        # e. Append assistant turn for context continuity.
        adapter.append_assistant_message(messages, response)

        # f. Dispatch each tool call and persist the record.
        results: list[str] = []
        for seq_offset, tc in enumerate(response.tool_calls):
            t0 = time.monotonic()
            result = dispatch(tc.name, tc.arguments, session, repo_path)
            ToolCall.objects.create(
                session=session,
                sequence=iteration * 10 + seq_offset,
                tool_name=tc.name,
                arguments=tc.arguments,
                result=result[:8000],
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
            results.append(result)

        # g. Feed results back to the model.
        adapter.append_tool_results(messages, response.tool_calls, results)

    else:
        # Loop exhausted — iteration cap reached.
        if session.status == ResearchSession.Status.RUNNING:
            session.status = ResearchSession.Status.FAILED
            session.error = "Iteration cap reached"

    # 7. Finalise and persist.
    session.completed_at = timezone.now()
    session.save()
    return session
