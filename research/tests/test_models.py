import pytest
from django.db import IntegrityError

from research.models import Repository, ResearchSession, ToolCall


@pytest.mark.django_db
def test_repository_from_url_idempotent() -> None:
    """from_url creates a row; calling again with the same URL returns same row."""
    url = "https://github.com/django/django"
    repo1 = Repository.from_url(url)
    repo2 = Repository.from_url(url)

    assert repo1.pk == repo2.pk
    assert Repository.objects.filter(url=url).count() == 1
    assert repo1.name == "django/django"


@pytest.mark.django_db
def test_research_session_default_status() -> None:
    """ResearchSession.status defaults to PENDING on creation."""
    repo = Repository.from_url("https://github.com/pallets/flask")
    session = ResearchSession.objects.create(
        repository=repo, question="What is the request lifecycle?"
    )

    assert session.status == ResearchSession.Status.PENDING


@pytest.mark.django_db
def test_tool_call_unique_sequence_constraint() -> None:
    """Creating two ToolCalls with same (session, sequence) raises IntegrityError."""
    repo = Repository.from_url("https://github.com/psf/requests")
    session = ResearchSession.objects.create(
        repository=repo, question="How are retries handled?"
    )
    ToolCall.objects.create(
        session=session, sequence=0, tool_name="list_files", result="[]"
    )

    with pytest.raises(IntegrityError):
        ToolCall.objects.create(
            session=session, sequence=0, tool_name="read_file", result="..."
        )
