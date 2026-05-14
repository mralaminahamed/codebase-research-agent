# Design Decisions and Trade-Offs

---

## 1. Architecture Overview

Django 5.0 + DRF backend. A `POST /api/sessions/` request carries a GitHub URL and a question, which kicks off a synchronous tool-use loop. The agent has seven tools: four code-exploration tools (operating on a shallow local clone) and three database tools that read and write the PostgreSQL session log.

LLM provider is controlled by a single env var, `LLM_PROVIDER=openai|anthropic`. A thin `LLMAdapter` ABC with `OpenAIAdapter` and `AnthropicAdapter` normalises the two SDKs. `agent.py` never imports `openai` or `anthropic`; it calls four abstract methods. Switching providers is one line in `.env`.

The loop is hand-written (~90 lines in `services/agent.py`), not LangChain or LangGraph. Trade-off: less tooling, full transparency — the right call when the agent design itself is under evaluation.

Code search uses `ripgrep` via `subprocess`. For a repository the size of `psf/requests` (~50 source files), grep is faster to set up and equally effective. Vector retrieval is the documented next step at scale.

---

## 2. Database Schema Rationale

Four tables: `Repository`, `ResearchSession`, `ToolCall`, `Finding`.

The key decision is keeping `ToolCall` and `Finding` separate. `ToolCall` is a complete audit log — every invocation, in order, with raw input and output. `Finding` is the distilled signal — only locations the agent explicitly saved via `save_finding`. These answer different questions ("what did the agent do?" vs "what did it conclude?") and serve different consumers. Merging them would force a choice between polluting the audit log with semantic tags or losing audit fidelity entirely.

`get_previous_findings` queries only `Finding`, not `ToolCall`. A new session on the same repo gets the prior agent's conclusions, not a dump of every search query it ran. This is what makes the database a real memory layer.

Future improvements: partial index on `status='COMPLETE'`, `pgvector` chunk table for semantic search, move `commit_sha` to `ResearchSession` for per-session reproducibility.

---

## 3. Key Design Decisions and Trade-Offs

**Dual LLM adapter.** Supporting both providers via an ABC adds ~200 lines but makes the agent loop, tool registry, and schema entirely provider-agnostic. Any future provider (Gemini, Groq, Bedrock) is a new concrete class, not a rewrite.

**`get_previous_findings`-first.** The system prompt mandates this as the first tool call every session. Without it, the agent explores from scratch each time. With it, sessions compound: later researchers build on earlier conclusions. This single behavioural rule is what distinguishes the system from a stateless wrapper around an LLM.

**Synchronous POST.** Blocks until the agent finishes (20–90 seconds for a small repo). Simple code, no queue, no polling. One slow session occupies a worker — Celery is the documented next step.

**Iteration cap 12, token budget 40,000.** A typical useful session uses 9–11 tool calls (1 `get_previous_findings`, 1–2 `list_files`, 2–3 `search_code`, 2–3 `read_file`, 2–3 `save_finding`). Cap 12 leaves one safety margin. Measured seed sessions against `psf/requests` consumed 10,000–18,000 input tokens; 40,000 allows roughly 2–3× before a hard stop — enough to detect a runaway loop without cutting a legitimate long session short.

---

## 4. What I'd Do Differently with More Time

- Async execution via Celery — return session ID immediately, client polls.
- `pgvector` chunk table with semantic `search_code` for large repos.
- `commit_sha` per session for true reproducibility across re-clones.
- SSE streaming of live agent reasoning to the API client.
- Additional provider adapters (Gemini, Groq, Bedrock).

---

## 5. AI Coding Tools — Honest Account

Used **Claude Code (CLI)** throughout.

- **Generated, accepted with minor edits:** project scaffold, `code_tools.py`, serializers, seed script.
- **Generated, substantially reviewed:** `llm_adapter.py`. The `AnthropicAdapter.append_tool_results` implementation is correct — Anthropic requires all tool results in one batched `user` message, not separate messages per call. I confirmed this against the Anthropic docs before accepting.
- **Written by hand:** four-table schema design, decision to separate `ToolCall` from `Finding`, `get_previous_findings`-first instruction in the system prompt, `LLMAdapter` ABC interface, this document.
- **Where Claude Code led me astray:** initial test configuration. The generated `conftest.py` set env vars in `pytest_configure`, which does not fire before `pytest-django`'s `pytest_load_initial_conftests` hook — so Django settings import failed before the env vars were set. Fix: `config/settings_test.py` calls `os.environ.setdefault` before importing the main settings module, guaranteeing order via Python import semantics rather than pytest hook order.

Discipline: one phase per session, reviewed every diff, ran `pytest` before committing. Commit history reflects the phase progression.

---

## 6. Known Limitations

- Public HTTPS GitHub URLs only — no private repos, no GitLab.
- `read_file` caps at 200 lines per call; large files require multiple paged calls.
- `commit_sha` lives on `Repository`, not `ResearchSession` — a re-clone can shift the commit underlying prior findings.
- Agent cannot execute code, only read it.
- Synchronous handling: one slow session blocks a Django worker.
- No authentication or rate limiting — out of scope per the brief.
