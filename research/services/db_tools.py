from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research.models import ResearchSession

from research.models import Finding


def save_finding(
    session: ResearchSession,
    file_path: str,
    note: str,
    line_start: int | None = None,
    line_end: int | None = None,
) -> str:
    """Create a Finding row and return a confirmation string.

    Args:
        session: Active research session that owns this finding.
        file_path: Repository-relative path where the finding was located.
        note: Human-readable description of the finding.
        line_start: Optional first line of the relevant code span (1-based).
        line_end: Optional last line of the relevant code span (inclusive).

    Returns:
        Confirmation string containing the new row's primary key.
    """
    finding = Finding.objects.create(
        session=session,
        file_path=file_path,
        note=note,
        line_start=line_start,
        line_end=line_end,
    )
    location = f" (lines {line_start}–{line_end})" if line_start else ""
    return f"Finding saved (id={finding.id}, file={file_path}{location})"


def get_previous_findings(
    session: ResearchSession,
    repo_url: str,
    limit: int = 10,
) -> str:
    """Return findings from prior COMPLETE sessions on repo_url.

    Excludes the current session. Ordered most-recent first.

    Args:
        session: The active session (excluded from results).
        repo_url: URL of the repository to look up findings for.
        limit: Maximum number of findings to return.

    Returns:
        Human-readable formatted findings, or a no-results sentinel string
        if no prior complete sessions exist for the repository.
    """
    from research.models import ResearchSession as RS

    findings = (
        Finding.objects.filter(
            session__repository__url=repo_url,
            session__status=RS.Status.COMPLETE,
        )
        .exclude(session=session)
        .select_related("session")
        .order_by("-created_at")[:limit]
    )

    if not findings:
        return "No prior findings on this repository."

    lines: list[str] = [f"{len(findings)} prior finding(s) on this repository:\n"]
    for f in findings:
        loc = f" (lines {f.line_start}–{f.line_end})" if f.line_start else ""
        lines.append(f"[{f.session_id}] {f.file_path}{loc}")
        lines.append(f.note)
        lines.append("")
    return "\n".join(lines).rstrip()


def list_past_sessions(
    session: ResearchSession,
    repo_url: str,
    limit: int = 5,
) -> str:
    """Return recent completed sessions for repo_url, excluding the current one.

    Formatted as ``Q: <question> / A: <answer truncated to 200 chars>``.

    Args:
        session: The active session (excluded from results).
        repo_url: URL of the repository to query.
        limit: Maximum number of sessions to return.

    Returns:
        Human-readable session summary string.
    """
    from research.models import ResearchSession as RS

    sessions = (
        RS.objects.filter(
            repository__url=repo_url,
            status=RS.Status.COMPLETE,
        )
        .exclude(pk=session.pk)
        .order_by("-started_at")[:limit]
    )

    if not sessions:
        return "No prior sessions on this repository."

    lines: list[str] = [f"{len(sessions)} prior session(s) on this repository:\n"]
    for s in sessions:
        answer = (s.final_answer or "")[:200]
        if len(s.final_answer or "") > 200:
            answer += "..."
        lines.append(f"Q: {s.question}")
        lines.append(f"A: {answer}")
        lines.append("")
    return "\n".join(lines).rstrip()
