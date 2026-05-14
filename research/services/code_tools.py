import shutil
import subprocess
from pathlib import Path

IGNORE_PATTERNS: set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
}

MAX_RESULT_CHARS = 8_000
_MAX_LINES_PER_READ = 200
_MAX_SEARCH_OUTPUT_LINES = 30


def _safe_resolve(repo_path: Path, relative: str) -> Path:
    """Resolve a relative path against repo_path and confirm it stays inside.

    Args:
        repo_path: Absolute path to the repository root.
        relative: Relative path string to resolve.

    Returns:
        Resolved absolute :class:`~pathlib.Path`.

    Raises:
        ValueError: If the resolved path escapes ``repo_path`` (path traversal).
    """
    resolved = (repo_path / relative).resolve()
    try:
        resolved.relative_to(repo_path.resolve())
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {relative!r} resolves outside repository root"
        )
    return resolved


def list_files(repo_path: Path, path: str = ".", max_depth: int = 2) -> str:
    """Return a directory listing up to max_depth, ignoring IGNORE_PATTERNS.

    Args:
        repo_path: Absolute path to the repository root.
        path: Relative starting path within the repo (default: repo root).
        max_depth: Maximum directory depth to recurse into.

    Returns:
        Newline-separated indented directory listing as a string.
    """
    base = _safe_resolve(repo_path, path)
    lines: list[str] = []

    def _walk(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            return
        for entry in entries:
            if entry.name in IGNORE_PATTERNS:
                continue
            indent = "  " * depth
            if entry.is_dir():
                lines.append(f"{indent}{entry.name}/")
                _walk(entry, depth + 1)
            else:
                lines.append(f"{indent}{entry.name}")

    _walk(base, 0)
    result = "\n".join(lines) if lines else "(empty)"
    return result[:MAX_RESULT_CHARS]


def read_file(
    repo_path: Path,
    path: str,
    line_start: int = 1,
    line_end: int = 200,
) -> str:
    """Return lines line_start..line_end (1-indexed, inclusive) with line numbers.

    Caps at 200 lines per call; returns an error string if the caller requests
    more than that in a single call.

    Args:
        repo_path: Absolute path to the repository root.
        path: Relative file path within the repo.
        line_start: First line to return (1-based).
        line_end: Last line to return (1-based, inclusive).

    Returns:
        Line-numbered file content or an error string.
    """
    requested = line_end - line_start + 1
    if requested > _MAX_LINES_PER_READ:
        return (
            f"ERROR: requested {requested} lines; "
            f"maximum is {_MAX_LINES_PER_READ} per call. "
            "Narrow the range or make multiple calls."
        )
    target = _safe_resolve(repo_path, path)
    content = target.read_text(errors="replace").splitlines()
    selected = content[line_start - 1 : line_end]
    numbered = [
        f"{line_start + i:5d} | {line}" for i, line in enumerate(selected)
    ]
    return "\n".join(numbered)


def search_code(repo_path: Path, query: str, file_glob: str = "*") -> str:
    """Search for query using ripgrep. Returns up to 30 matching lines.

    Args:
        repo_path: Absolute path to the repository root.
        query: Search pattern (literal string or regex) passed to ``rg``.
        file_glob: File glob filter, e.g. ``"*.py"`` (default: all files).

    Returns:
        Matching lines formatted by ripgrep, or an error/empty-result string.
    """
    rg_bin = shutil.which("rg")
    if rg_bin is None:
        return "ERROR: ripgrep (rg) not found in PATH"

    result = subprocess.run(
        [
            rg_bin,
            "--max-count=5",
            "-n",
            "--heading",
            "-g", "!.git",
            "-g", file_glob,
            query,
            str(repo_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 2:
        return f"ERROR: ripgrep failed: {result.stderr.strip()}"

    stdout = result.stdout.strip()
    if not stdout:
        return "No matches found."

    lines = stdout.splitlines()[:_MAX_SEARCH_OUTPUT_LINES]
    output = "\n".join(lines)
    if len(output) > MAX_RESULT_CHARS:
        output = output[:MAX_RESULT_CHARS] + "\n... (truncated)"
    return output


def get_file_summary(repo_path: Path, path: str) -> str:
    """Return first 40 lines plus counts of 'def ' and 'class ' occurrences.

    Args:
        repo_path: Absolute path to the repository root.
        path: Relative file path within the repo.

    Returns:
        String containing the file header and a summary line.
    """
    target = _safe_resolve(repo_path, path)
    content = target.read_text(errors="replace")
    lines = content.splitlines()
    header = "\n".join(lines[:40])
    def_count = content.count("def ")
    class_count = content.count("class ")
    return f"{header}\n\n--- {def_count} def(s), {class_count} class(es) ---"
