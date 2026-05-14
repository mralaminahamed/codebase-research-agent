import hashlib
import re
from pathlib import Path

import git
from django.conf import settings


class RepoCloneError(Exception):
    """Raised when a repository cannot be cloned or updated."""


GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$",
    re.IGNORECASE,
)


def validate_repo_url(url: str) -> None:
    """Raise RepoCloneError if url is not a valid public GitHub HTTPS URL.

    Args:
        url: The URL to validate.

    Raises:
        RepoCloneError: If the URL does not match the expected GitHub HTTPS format.
    """
    if not GITHUB_URL_RE.match(url):
        raise RepoCloneError(
            f"Invalid GitHub URL: {url!r}. "
            "Must match https://github.com/<owner>/<repo>[.git]"
        )


def repo_local_path(url: str) -> Path:
    """Return the deterministic local clone path for a URL.

    Uses the first 16 hex characters of sha256(url) as the directory name
    under ``settings.MEDIA_ROOT/repos/``. Pure function — makes no
    filesystem calls.

    Args:
        url: Canonical GitHub repository URL.

    Returns:
        Absolute :class:`~pathlib.Path` for the local clone directory.
    """
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return Path(settings.MEDIA_ROOT) / "repos" / digest


def clone_or_update(url: str) -> tuple[Path, str]:
    """Clone a GitHub repo shallowly (depth=1) or fetch+reset if already cloned.

    On first call the repository is cloned with ``--depth=1``. On subsequent
    calls the existing clone is brought up to date via ``fetch`` +
    ``reset --hard origin/HEAD``.

    Args:
        url: Public GitHub HTTPS URL of the repository.

    Returns:
        A ``(local_path, commit_sha)`` tuple where ``commit_sha`` is the
        full hex SHA of HEAD after the operation completes.

    Raises:
        RepoCloneError: If the URL is invalid or any git operation fails.
    """
    validate_repo_url(url)
    path = repo_local_path(url)

    try:
        if path.exists():
            repo = git.Repo(path)
            origin = repo.remotes.origin
            origin.fetch(depth=1)
            repo.git.reset("--hard", "origin/HEAD")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(url, path, multi_options=["--depth=1"])
    except git.GitCommandError as exc:
        raise RepoCloneError(f"Git operation failed for {url!r}: {exc}") from exc

    return path, repo.head.commit.hexsha
