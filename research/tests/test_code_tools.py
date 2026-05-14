import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research.services.code_tools import (
    _safe_resolve,
    get_file_summary,
    list_files,
    read_file,
    search_code,
)

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def test_list_files_returns_expected_entries() -> None:
    """list_files includes repo contents and excludes .git directory."""
    result = list_files(SAMPLE_REPO)

    assert "main.py" in result
    assert "README.md" in result
    assert "subpkg" in result
    assert ".git" not in result


def test_read_file_returns_numbered_lines() -> None:
    """read_file returns lines 1–5 with five-char right-justified line numbers."""
    result = read_file(SAMPLE_REPO, "main.py", line_start=1, line_end=5)
    lines = result.splitlines()

    assert len(lines) == 5
    assert lines[0].startswith("    1 | ")
    assert lines[4].startswith("    5 | ")


def test_search_code_finds_def_keyword() -> None:
    """search_code returns ripgrep output containing matched lines for 'def '."""
    fake_output = (
        "main.py\n"
        "4:def greet(name: str) -> str:\n"
        "16:def add(a: int, b: int) -> int:\n"
        "\n"
        "subpkg/utils.py\n"
        "4:def helper() -> str:\n"
    )
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = fake_output
    mock_proc.stderr = ""

    with patch("research.services.code_tools.shutil.which", return_value="/usr/bin/rg"), \
         patch("research.services.code_tools.subprocess.run", return_value=mock_proc) as mock_run:
        result = search_code(SAMPLE_REPO, "def ")

    assert "def greet" in result
    assert "def add" in result
    called_args = mock_run.call_args[0][0]
    assert "def " in called_args
    assert str(SAMPLE_REPO) in called_args


def test_get_file_summary_counts_defs_and_classes() -> None:
    """get_file_summary reports 3 defs and 1 class for main.py."""
    result = get_file_summary(SAMPLE_REPO, "main.py")

    assert "3 def(s)" in result
    assert "1 class(es)" in result


def test_safe_resolve_blocks_path_traversal() -> None:
    """_safe_resolve raises ValueError when path escapes repository root."""
    with pytest.raises(ValueError, match="traversal"):
        _safe_resolve(SAMPLE_REPO, "../../etc/passwd")
