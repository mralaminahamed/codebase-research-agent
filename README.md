# Codebase Research Agent

> An AI agent that answers technical questions about public GitHub repositories by exploring the code itself, using tool-calling. Every research session is persisted to PostgreSQL. The agent reads prior findings before re-exploring the same repository.

Built as a take-home assessment for **CodeFusion AI** — Senior Backend Developer.

**Author:** Al Amin Ahamed · [github.com/mralaminahamed](https://github.com/mralaminahamed) · [alaminahamed.com](https://alaminahamed.com)

---

## Stack

Python 3.11 · Django 5.0 · Django REST Framework · PostgreSQL 16 · OpenAI / Anthropic (env-switchable)

---

## Quick Start

**Prerequisites:** Docker + Docker Compose; an OpenAI or Anthropic API key.

```bash
# 1. Clone
git clone https://github.com/mralaminahamed/codebase-research-agent.git
cd codebase-research-agent

# 2. Configure
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the matching API key (see Configuration below)

# 3. Start services
docker compose up --build -d

# 4. Run migrations
docker compose exec web python manage.py migrate

# 5. Load sample data (optional — creates two pre-seeded sessions)
docker compose exec web python scripts/seed_sample_data.py

# 6. Create an admin superuser
docker compose exec web python manage.py createsuperuser

# 7. Run the demo
bash scripts/run_demo.sh
```

Application: `http://localhost:8000/`
Django Admin: `http://localhost:8000/admin/`

---

## Configuration

All settings are via environment variables in `.env`. Copy `.env.example` and populate:

| Variable | Default | Required | Description |
|---|---|---|---|
| `SECRET_KEY` | — | ✓ | Django secret key |
| `DEBUG` | `True` | | Django debug mode |
| `DATABASE_URL` | `postgres://postgres:postgres@db:5432/research` | ✓ | Postgres connection string |
| **`LLM_PROVIDER`** | `openai` | ✓ | `openai` or `anthropic` — switches the active LLM |
| `OPENAI_API_KEY` | — | If `LLM_PROVIDER=openai` | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | | OpenAI model to use |
| `ANTHROPIC_API_KEY` | — | If `LLM_PROVIDER=anthropic` | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | | Anthropic model to use |
| `MAX_AGENT_ITERATIONS` | `12` | | Maximum tool-call iterations per session |
| `MAX_INPUT_TOKENS` | `40000` | | Cumulative input-token budget per session |
| `MEDIA_ROOT` | `/app/media` | | Where repository clones are stored |

To switch providers, change `LLM_PROVIDER` and populate the corresponding API key. The inactive provider's key can remain blank.

---

## API

Three endpoints under `/api/`.

### `POST /api/sessions/` — Start a research session

```bash
curl -s -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/tiangolo/fastapi",
    "question": "How does FastAPI handle dependency injection internally?"
  }' | jq .
```

This call is **synchronous** — it blocks until the agent completes (typically 20–90 seconds for a small repo). Returns the full session including tool calls and findings.

**Response shape:**

```json
{
  "id": "8a4b1c2d-...",
  "repository": {
    "id": 1,
    "url": "https://github.com/tiangolo/fastapi",
    "name": "tiangolo/fastapi",
    "commit_sha": "a1b2c3..."
  },
  "question": "How does FastAPI handle dependency injection internally?",
  "final_answer": "FastAPI implements dependency injection in fastapi/dependencies/utils.py...",
  "status": "COMPLETE",
  "iterations": 6,
  "input_tokens": 18200,
  "output_tokens": 1100,
  "tool_calls": [
    {
      "sequence": 0,
      "tool_name": "get_previous_findings",
      "arguments": {"repo_url": "https://github.com/tiangolo/fastapi"},
      "result_preview": "No prior findings on this repository.",
      "duration_ms": 12
    }
  ],
  "findings": [
    {
      "id": 1,
      "file_path": "fastapi/dependencies/utils.py",
      "line_start": 415,
      "line_end": 480,
      "note": "solve_dependencies recursively resolves the dependency graph..."
    }
  ]
}
```

### `GET /api/sessions/<uuid>/` — Retrieve a session

```bash
curl -s http://localhost:8000/api/sessions/8a4b1c2d-.../ | jq .
```

### `GET /api/repositories/<id>/sessions/` — List past sessions for a repo

```bash
curl -s 'http://localhost:8000/api/repositories/1/sessions/?page=1' | jq .
```

Paginated, page size 20.

---

## How the Agent Works

On every new session, the agent:

1. Clones (or fetches) the target repository locally (shallow, `--depth=1`).
2. **First tool call is always `get_previous_findings(repo_url)`** — if prior sessions found relevant code locations, the agent builds on them instead of re-exploring from scratch. This makes the database a real memory layer, not a passive log.
3. Uses `list_files`, `search_code`, and `read_file` to locate relevant code.
4. Calls `save_finding(file_path, note, line_start, line_end)` for each location worth remembering.
5. Stops when it has enough information, or when the iteration cap (default 12) or token budget (default 40,000 input tokens) is reached.
6. Returns a final answer that cites specific files and line numbers.

Every tool invocation is persisted as a `ToolCall` row. Every `save_finding` call creates a `Finding` row. Both are visible in the Django admin.

---

## Project Structure

```
codebase-research-agent/
├── config/              # Django project (settings, urls, wsgi)
├── research/
│   ├── models.py        # Repository, ResearchSession, ToolCall, Finding
│   ├── admin.py
│   ├── serializers.py
│   ├── views.py         # Three DRF endpoints
│   ├── urls.py
│   └── services/
│       ├── llm_adapter.py    # LLMAdapter ABC + OpenAIAdapter + AnthropicAdapter + factory
│       ├── repo_service.py   # Clone, validate, path safety
│       ├── code_tools.py     # list_files, read_file, search_code, get_file_summary
│       ├── db_tools.py       # save_finding, get_previous_findings, list_past_sessions
│       ├── tool_registry.py  # Canonical tool specs + dispatcher
│       └── agent.py          # Provider-agnostic tool-use loop
├── scripts/
│   ├── seed_sample_data.py
│   └── run_demo.sh
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── README.md
├── DECISIONS.md
└── ARCHITECTURE.md
```

---

## Running Tests

```bash
docker compose exec web pytest -v
```

The test suite covers:

- Model invariants (`Repository.from_url` idempotency, `ToolCall` sequence uniqueness)
- Code tool path-safety (path traversal rejected)
- `get_previous_findings` correctly excludes the current session
- `OpenAIAdapter` and `AnthropicAdapter` format tools and normalise responses correctly
- End-to-end agent integration test against a mocked adapter (provider-agnostic)

No real API calls are made during tests.

---

## Switching LLM Provider

To run with Anthropic instead of OpenAI:

```bash
# In .env:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

docker compose restart web
```

That's the only change required. The agent loop, tool registry, and database schema are entirely provider-agnostic.

---

## Design Documents

- **`DECISIONS.md`** — Architecture overview, schema rationale, trade-offs, AI tool usage (500–800 words per the brief).
- **`ARCHITECTURE.md`** — Detailed component breakdown, sequence diagrams, adapter pattern design, future-work register.

---

## Limitations

- Public HTTPS GitHub URLs only.
- Synchronous request handling — one slow session blocks a worker.
- No authentication, no rate limiting (out of scope per brief).
- `read_file` caps at 200 lines per call.
- No vector retrieval (ripgrep is sufficient at this scope).

---

## License

MIT.
