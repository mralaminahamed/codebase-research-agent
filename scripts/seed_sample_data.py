#!/usr/bin/env python
"""Seed the database with two completed research sessions for psf/requests.

Idempotent — skips any session whose (repository, question) pair already exists.

Usage (inside the web container):
    python scripts/seed_sample_data.py
"""
import os
import sys

# ── Bootstrap Django ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

# ── Imports that require Django to be set up first ────────────────────────────
from research.models import Finding, Repository, ResearchSession, ToolCall  # noqa: E402

# ── Seed data ─────────────────────────────────────────────────────────────────

REPO_URL = "https://github.com/psf/requests"

SESSIONS = [
    {
        "question": "How does requests handle SSL certificate verification?",
        "final_answer": (
            "SSL certificate verification in the `requests` library is handled primarily "
            "in `requests/adapters.py` via the `HTTPAdapter.send()` method. "
            "The `verify` parameter (default `True`) controls whether the SSL certificate "
            "is checked. When `verify=True`, the adapter resolves the CA bundle path "
            "using `extract_cookies_to_jar` and passes it to `urllib3` as `ca_certs`. "
            "The default CA bundle path is resolved at import time by "
            "`requests/certs.py:where()`, which returns the path to the `certifi` "
            "bundle if installed, otherwise falls back to the system bundle. "
            "Setting `verify=False` disables certificate checking entirely and triggers "
            "an `InsecureRequestWarning` via `urllib3.disable_warnings` — "
            "see `requests/adapters.py:236-280` and `requests/certs.py:1-25`."
        ),
        "iterations": 5,
        "input_tokens": 11800,
        "output_tokens": 820,
        "tool_calls": [
            {
                "sequence": 0,
                "tool_name": "get_previous_findings",
                "arguments": {"limit": 10},
                "result": "No prior findings on this repository.",
                "duration_ms": 18,
            },
            {
                "sequence": 1,
                "tool_name": "search_code",
                "arguments": {"query": "verify", "file_glob": "*.py"},
                "result": (
                    "requests/adapters.py\n"
                    "236:    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):\n"
                    "252:        if verify is True or verify:\n"
                    "260:            cert_loc = verify\n"
                    "\n"
                    "requests/sessions.py\n"
                    "114:        self.verify = True\n"
                    "490:            verify=merge_setting(request.verify, self.verify),"
                ),
                "duration_ms": 42,
            },
            {
                "sequence": 2,
                "tool_name": "read_file",
                "arguments": {"path": "requests/adapters.py", "line_start": 230, "line_end": 285},
                "result": (
                    "  230 | \n"
                    "  231 |     def send(self, request, stream=False, timeout=None,\n"
                    "  232 |              verify=True, cert=None, proxies=None):\n"
                    "  233 |         \"\"\"Sends PreparedRequest object. Returns Response object.\"\"\"\n"
                    "  234 |         try:\n"
                    "  235 |             conn = self.get_connection_with_tls_context(\n"
                    "  236 |                 request, verify=verify, proxies=proxies, cert=cert\n"
                    "  237 |             )\n"
                    "  238 |         except LocationValueError as e:\n"
                    "  239 |             raise InvalidURL(e, request=request)\n"
                    "  250 |         if not verify:\n"
                    "  251 |             from urllib3.exceptions import InsecureRequestWarning\n"
                    "  252 |             urllib3.disable_warnings(InsecureRequestWarning)\n"
                ),
                "duration_ms": 11,
            },
            {
                "sequence": 3,
                "tool_name": "read_file",
                "arguments": {"path": "requests/certs.py", "line_start": 1, "line_end": 30},
                "result": (
                    "    1 | \"\"\"\n"
                    "    2 | requests.certs\n"
                    "    3 | ~~~~~~~~~~~~~~\n"
                    "    4 | \n"
                    "    5 | This module returns the preferred default CA certificate bundle.\n"
                    "    6 | \"\"\"\n"
                    "    7 | \n"
                    "    8 | from certifi import where\n"
                    "    9 | \n"
                    "   10 | \n"
                    "   11 | def where():\n"
                    "   12 |     \"\"\"Return the preferred certificate bundle for this system.\"\"\"\n"
                    "   13 |     return certifi.where()\n"
                ),
                "duration_ms": 9,
            },
        ],
        "findings": [
            {
                "file_path": "requests/adapters.py",
                "line_start": 231,
                "line_end": 252,
                "note": (
                    "HTTPAdapter.send() is the entry point for SSL verification. "
                    "The 'verify' parameter is forwarded to urllib3 as 'ca_certs'. "
                    "Setting verify=False suppresses InsecureRequestWarning."
                ),
                "confidence": 0.97,
            },
            {
                "file_path": "requests/certs.py",
                "line_start": 1,
                "line_end": 25,
                "note": (
                    "requests/certs.py re-exports certifi.where() as the default CA bundle "
                    "resolver. This is the canonical place where the bundle path originates."
                ),
                "confidence": 0.95,
            },
        ],
    },
    {
        "question": "Where is authentication implemented in the requests library?",
        "final_answer": (
            "Authentication in `requests` is implemented in `requests/auth.py`. "
            "The module provides two concrete classes: "
            "`HTTPBasicAuth` (lines 15-33) encodes credentials as a base-64 Basic header, "
            "and `HTTPDigestAuth` (lines 36-144) implements the full RFC 7616 digest "
            "challenge-response flow, including nonce tracking and `qop=auth` support. "
            "Both classes implement the `AuthBase.__call__(r)` interface, which receives "
            "a `PreparedRequest` and returns it modified. "
            "Auth objects are attached to a `Session` via `session.auth` "
            "(see `requests/sessions.py:115`) and applied inside "
            "`PreparedRequest.prepare_auth()` at `requests/models.py:561`."
        ),
        "iterations": 5,
        "input_tokens": 10400,
        "output_tokens": 760,
        "tool_calls": [
            {
                "sequence": 0,
                "tool_name": "get_previous_findings",
                "arguments": {"limit": 10},
                "result": "No prior findings on this repository.",
                "duration_ms": 15,
            },
            {
                "sequence": 1,
                "tool_name": "search_code",
                "arguments": {"query": "class.*Auth", "file_glob": "*.py"},
                "result": (
                    "requests/auth.py\n"
                    "12:class AuthBase:\n"
                    "23:class HTTPBasicAuth(AuthBase):\n"
                    "52:class HTTPProxyAuth(HTTPBasicAuth):\n"
                    "58:class HTTPDigestAuth(AuthBase):\n"
                ),
                "duration_ms": 38,
            },
            {
                "sequence": 2,
                "tool_name": "read_file",
                "arguments": {"path": "requests/auth.py", "line_start": 1, "line_end": 80},
                "result": (
                    "    1 | \"\"\"\n"
                    "    2 | requests.auth\n"
                    "    3 | ~~~~~~~~~~~~~\n"
                    "    4 | \n"
                    "    5 | This module contains the authentication handlers for Requests.\n"
                    "    6 | \"\"\"\n"
                    "    7 | \n"
                    "   12 | class AuthBase:\n"
                    "   13 |     \"\"\"Base class that all auth implementations derive from\"\"\"\n"
                    "   14 | \n"
                    "   15 |     def __call__(self, r):\n"
                    "   16 |         raise NotImplementedError('Auth hooks must be callable.')\n"
                    "   23 | class HTTPBasicAuth(AuthBase):\n"
                    "   24 |     \"\"\"Attaches HTTP Basic Authentication to the given Request object.\"\"\"\n"
                    "   25 |     def __init__(self, username, password):\n"
                    "   26 |         self.username = username\n"
                    "   27 |         self.password = password\n"
                    "   28 |     def __call__(self, r):\n"
                    "   29 |         r.headers['Authorization'] = _basic_auth_str(self.username, self.password)\n"
                    "   30 |         return r\n"
                ),
                "duration_ms": 13,
            },
            {
                "sequence": 3,
                "tool_name": "search_code",
                "arguments": {"query": "prepare_auth", "file_glob": "*.py"},
                "result": (
                    "requests/models.py\n"
                    "561:    def prepare_auth(self, auth, url=''):\n"
                    "567:        auth(*args)\n"
                    "\n"
                    "requests/sessions.py\n"
                    "480:            auth=merge_setting(auth, self.auth),"
                ),
                "duration_ms": 29,
            },
        ],
        "findings": [
            {
                "file_path": "requests/auth.py",
                "line_start": 12,
                "line_end": 144,
                "note": (
                    "requests/auth.py contains all auth classes. AuthBase defines the __call__ "
                    "contract. HTTPBasicAuth sets Authorization header directly. "
                    "HTTPDigestAuth handles the full challenge-response nonce cycle."
                ),
                "confidence": 0.98,
            },
            {
                "file_path": "requests/models.py",
                "line_start": 561,
                "line_end": 570,
                "note": (
                    "PreparedRequest.prepare_auth() is where the auth callable is invoked "
                    "against the prepared request. The session merges session.auth with "
                    "per-request auth before this call."
                ),
                "confidence": 0.93,
            },
        ],
    },
]


def seed() -> None:
    """Seed the database with sample research sessions. Idempotent."""
    repo = Repository.from_url(REPO_URL)
    print(f"Repository: {repo.name} (id={repo.pk})")

    for session_data in SESSIONS:
        question = session_data["question"]

        if ResearchSession.objects.filter(repository=repo, question=question).exists():
            print(f"  SKIP (already exists): {question[:60]}…")
            continue

        session = ResearchSession.objects.create(
            repository=repo,
            question=question,
            status=ResearchSession.Status.COMPLETE,
            iterations=session_data["iterations"],
            input_tokens=session_data["input_tokens"],
            output_tokens=session_data["output_tokens"],
            final_answer=session_data["final_answer"],
        )

        for tc_data in session_data["tool_calls"]:
            ToolCall.objects.create(
                session=session,
                sequence=tc_data["sequence"],
                tool_name=tc_data["tool_name"],
                arguments=tc_data["arguments"],
                result=tc_data["result"],
                duration_ms=tc_data["duration_ms"],
            )

        for finding_data in session_data["findings"]:
            Finding.objects.create(
                session=session,
                file_path=finding_data["file_path"],
                line_start=finding_data["line_start"],
                line_end=finding_data["line_end"],
                note=finding_data["note"],
                confidence=finding_data["confidence"],
            )

        print(f"  CREATED: {question[:60]}… (session={session.pk})")

    print("Seed complete.")


if __name__ == "__main__":
    seed()
