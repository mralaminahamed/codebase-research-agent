import pytest

from research.models import Finding, Repository, ResearchSession
from research.services.db_tools import get_previous_findings, save_finding


@pytest.mark.django_db
def test_save_finding_creates_row_and_returns_id() -> None:
    """save_finding persists a Finding row; result string contains the new row id."""
    repo = Repository.from_url("https://github.com/django/django")
    session = ResearchSession.objects.create(repository=repo, question="Where is auth?")

    result = save_finding(session, file_path="auth/models.py", note="User model here")

    assert Finding.objects.filter(session=session).count() == 1
    finding = Finding.objects.get(session=session)
    assert str(finding.id) in result


@pytest.mark.django_db
def test_get_previous_findings_excludes_current_session() -> None:
    """get_previous_findings returns findings from other COMPLETE sessions, not current."""
    repo = Repository.from_url("https://github.com/pallets/flask")

    prior = ResearchSession.objects.create(
        repository=repo,
        question="What is the app factory pattern?",
        status=ResearchSession.Status.COMPLETE,
        final_answer="Flask uses create_app().",
    )
    Finding.objects.create(
        session=prior,
        file_path="src/flask/app.py",
        note="create_app factory defined here",
    )

    current = ResearchSession.objects.create(
        repository=repo, question="How does routing work?"
    )

    result = get_previous_findings(current, repo_url=repo.url)

    assert "create_app factory defined here" in result
    assert "No prior findings" not in result


@pytest.mark.django_db
def test_get_previous_findings_returns_sentinel_when_none_exist() -> None:
    """get_previous_findings returns the no-results string when no prior sessions exist."""
    repo = Repository.from_url("https://github.com/psf/requests")
    session = ResearchSession.objects.create(
        repository=repo, question="How are retries handled?"
    )

    result = get_previous_findings(session, repo_url=repo.url)

    assert result == "No prior findings on this repository."
