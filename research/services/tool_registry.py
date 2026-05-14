from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research.models import ResearchSession

from research.services import code_tools, db_tools

CANONICAL_TOOLS: list[dict] = [
    {
        "name": "list_files",
        "description": (
            "List files and directories in the repository up to a given depth. "
            "Start every exploration here to understand repo layout before reading files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path within the repository (default: repo root '.').",
                    "default": ".",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum directory depth to recurse into (default: 2).",
                    "default": 2,
                },
            },
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a file from the repository with line numbers. "
            "Maximum 200 lines per call — use line_start/line_end to paginate large files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Repository-relative path to the file.",
                },
                "line_start": {
                    "type": "integer",
                    "description": "First line to read, 1-indexed (default: 1).",
                    "default": 1,
                },
                "line_end": {
                    "type": "integer",
                    "description": "Last line to read, inclusive (default: 200).",
                    "default": 200,
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": (
            "Search the repository for a pattern using ripgrep. "
            "Returns up to 30 matching lines with file paths and line numbers. "
            "Prefer this over reading whole files when looking for a specific symbol or string."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search pattern (literal string or regex).",
                },
                "file_glob": {
                    "type": "string",
                    "description": "File glob to restrict search, e.g. '*.py' (default: all files).",
                    "default": "*",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_file_summary",
        "description": (
            "Return the first 40 lines of a file plus counts of 'def' and 'class' occurrences. "
            "Use to quickly gauge a file's purpose before committing to a full read."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Repository-relative path to the file.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "save_finding",
        "description": (
            "Persist a code location or fact discovered during this session. "
            "Call this whenever you identify something directly relevant to the question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Repository-relative path where the finding is located.",
                },
                "note": {
                    "type": "string",
                    "description": "Clear, self-contained description of what was found and why it matters.",
                },
                "line_start": {
                    "type": "integer",
                    "description": "First line of the relevant code span, 1-indexed (optional).",
                },
                "line_end": {
                    "type": "integer",
                    "description": "Last line of the relevant code span, inclusive (optional).",
                },
            },
            "required": ["file_path", "note"],
        },
    },
    {
        "name": "get_previous_findings",
        "description": (
            "Retrieve findings saved in earlier completed sessions for this repository. "
            "ALWAYS call this first — prior research may already answer the question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of findings to return (default: 10).",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_past_sessions",
        "description": (
            "List previously completed research sessions for this repository "
            "with their questions and summarised answers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of sessions to return (default: 5).",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
]

_TOOL_NAMES = {t["name"] for t in CANONICAL_TOOLS}


def dispatch(
    name: str,
    arguments: dict,
    session: ResearchSession,
    repo_path: Path,
) -> str:
    """Route a tool call by name. Returns a result string.

    The ``session`` and ``repo_path`` parameters are injected by the agent loop
    so that DB tools receive context without the LLM needing to supply it.
    All exceptions are caught and returned as readable error strings.

    Args:
        name: Tool name matching one of :data:`CANONICAL_TOOLS`.
        arguments: Parsed JSON arguments from the LLM tool call.
        session: Active research session (injected — not exposed to the LLM).
        repo_path: Absolute local path to the cloned repository.

    Returns:
        Tool output as a plain string, or an ``ERROR: …`` string on failure.
    """
    if name not in _TOOL_NAMES:
        return f"ERROR: unknown tool '{name}'. Available: {sorted(_TOOL_NAMES)}"

    try:
        if name == "list_files":
            return code_tools.list_files(
                repo_path,
                path=arguments.get("path", "."),
                max_depth=int(arguments.get("max_depth", 2)),
            )

        if name == "read_file":
            return code_tools.read_file(
                repo_path,
                path=arguments["path"],
                line_start=int(arguments.get("line_start", 1)),
                line_end=int(arguments.get("line_end", 200)),
            )

        if name == "search_code":
            return code_tools.search_code(
                repo_path,
                query=arguments["query"],
                file_glob=arguments.get("file_glob", "*"),
            )

        if name == "get_file_summary":
            return code_tools.get_file_summary(repo_path, path=arguments["path"])

        if name == "save_finding":
            return db_tools.save_finding(
                session,
                file_path=arguments["file_path"],
                note=arguments["note"],
                line_start=arguments.get("line_start"),
                line_end=arguments.get("line_end"),
            )

        if name == "get_previous_findings":
            return db_tools.get_previous_findings(
                session,
                repo_url=session.repository.url,
                limit=int(arguments.get("limit", 10)),
            )

        if name == "list_past_sessions":
            return db_tools.list_past_sessions(
                session,
                repo_url=session.repository.url,
                limit=int(arguments.get("limit", 5)),
            )

    except Exception as exc:  # noqa: BLE001
        return f"ERROR calling '{name}': {exc}"

    return f"ERROR: unhandled tool '{name}'"
