import pytest

from research.services.repo_service import (
    RepoCloneError,
    repo_local_path,
    validate_repo_url,
)


def test_validate_repo_url_accepts_valid_github_url() -> None:
    """validate_repo_url does not raise for a valid public GitHub HTTPS URL."""
    validate_repo_url("https://github.com/python/cpython")


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://evil.com/repo",
        "https://github.com/../../../etc/passwd",
        "http://github.com/python/cpython",
        "https://github.com/python",
        "git@github.com:python/cpython.git",
    ],
)
def test_validate_repo_url_rejects_invalid_urls(bad_url: str) -> None:
    """validate_repo_url raises RepoCloneError for non-GitHub or path-traversal URLs."""
    with pytest.raises(RepoCloneError):
        validate_repo_url(bad_url)


def test_repo_local_path_is_deterministic() -> None:
    """Same URL always maps to the same Path; different URLs map to different Paths."""
    url_a = "https://github.com/django/django"
    url_b = "https://github.com/pallets/flask"

    assert repo_local_path(url_a) == repo_local_path(url_a)
    assert repo_local_path(url_a) != repo_local_path(url_b)
