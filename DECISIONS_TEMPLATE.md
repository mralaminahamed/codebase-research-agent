# Design Decisions and Trade-Offs

> **Note to Al Amin:** Fill every `<<…>>` with concrete specifics from your actual build before submitting. The reviewer explicitly scores for specificity. Do not leave generic statements. Run `wc -w DECISIONS.md` before submitting — target 500–800 words.

---

## 1. Architecture Overview

The system is a Django 5.0 + Django REST Framework backend exposing a single AI agent for codebase research. A `POST /api/sessions/` request carrying a GitHub URL and a natural-language question kicks off a synchronous tool-use loop. The agent has access to seven tools in two families: four code-exploration tools that operate on a shallow clone of the repository, and three database tools that read and write the PostgreSQL session log.

The LLM provider is controlled by a single environment variable, `LLM_PROVIDER=openai|anthropic`. A thin `LLMAdapter` abstraction layer — an abstract base class with `OpenAIAdapter` and `AnthropicAdapter` implementations — normalises the two SDKs. `agent.py` never imports `openai` or `anthropic` directly; it only calls four abstract methods: `format_tools`, `create_completion`, `append_assistant_message`, and `append_tool_results`. Switching providers is a one-line change in `.env`.

The orchestration loop is hand-written (~<<N>> lines in `services/agent.py`), not built on LangChain, LangGraph, or CrewAI. Trade-off: less out-of-the-box tooling, more transparency about what happens on each iteration — which is the right choice for a project whose agent design is being evaluated directly.

Code search uses `ripgrep` shelled via `subprocess`, not a vector database. For repositories of the size tested (<<approximate file count>>), BM25-style grep is faster to set up, faster to run, and produces equally relevant results for the questions asked. Vector retrieval is the clear next step at scale and is documented as such.

---

## 2. Database Schema Rationale

Four tables: `Repository`, `ResearchSession`, `ToolCall`, `Finding`.

The most important schema decision is keeping `ToolCall` and `Finding` as separate tables. They are easy to conflate — both record things the agent did during a session — but they serve fundamentally different purposes.

`ToolCall` is a **complete audit log**: every LLM-initiated invocation, in sequence, with raw arguments and raw output. It answers "what did the agent do?" and enables forensic review of any session.

`Finding` is the **distilled signal**: locations the agent explicitly chose to remember by calling the `save_finding` tool. It answers "what did the agent conclude?" and is what the `get_previous_findings` tool reads when a new session starts on a previously-researched repo.

If merged into one table, you either pollute the audit log with semantic tags (losing replay clarity) or lose the audit log by keeping only "interesting" calls (losing debuggability). Separate tables give you both at the cost of one extra JOIN, which is negligible.

At scale I would add: a partial index on `ResearchSession.status='COMPLETE'` (the `get_previous_findings` query only reads completed sessions), a `Chunk` table with `pgvector` embeddings for semantic search, and move `commit_sha` to `ResearchSession` (currently on `Repository`) to enable per-session reproducibility.

---

## 3. Key Design Decisions and Trade-Offs

**Dual LLM provider support.** Supporting both OpenAI and Anthropic via a provider adapter is the most deliberate design choice in the codebase. Real production AI systems almost always need provider fallback. The adapter adds ~<<N>> lines of code and makes the rest of the system provider-agnostic. Trade-off: slightly more code upfront; benefit: any future provider (Gemini, Groq, Bedrock) is a new concrete class, not a rewrite of the loop.

**`get_previous_findings`-first discipline.** The system prompt instructs the agent to call `get_previous_findings(repo_url)` as its very first tool call. Without this instruction, the agent tends to explore from scratch every time. With it, sessions on the same repo compound: the second researcher builds on the first's conclusions. This turns the database from a passive log into an active memory layer, which is the most important product behaviour in the system.

**Synchronous request handling.** `POST /api/sessions/` blocks until the agent finishes (typically <<N>>–<<N>> seconds against a small repo with the <<provider>> provider). Trade-off: simple code, no worker queue, no polling. Cost: a slow session occupies a Django worker. Celery + poll is the obvious next step and is documented in the README.

**Iteration cap of 12, token budget of 40,000 input tokens.** <<One or two sentences on how you arrived at these numbers empirically during testing.>>

---

## 4. What I'd Do Differently with More Time

- **Async execution via Celery.** The single highest-impact change for a real product. Return session id immediately; client polls.
- **Vector retrieval.** Add `Chunk` + `pgvector`, embed at index time, expose a `semantic_search` tool for large repos.
- **`commit_sha` per session.** True reproducibility: capture the commit each session observed, not just the repo's current HEAD.
- **Streaming via SSE.** Surface live agent reasoning to the API client — useful both for UX and debugging.
- **Additional providers in the adapter.** Gemini, Groq, and Bedrock each require only a new concrete `LLMAdapter` subclass. The interface is already defined.

---

## 5. AI Coding Tools — Honest Account

I used **Claude Code (CLI)** throughout this project. Specific accounting:

- **Claude Code generated and I accepted with minor edits:** project scaffold (Phase 0), the four code-exploration tools (`code_tools.py`), serializers and ViewSet wiring (Phase 7), the seed script.
- **Claude Code drafted and I substantially rewrote:** `llm_adapter.py` — the generated `AnthropicAdapter.append_tool_results` initially used the wrong message format (separate messages per result rather than one batched `user` message); I caught this in review and rewrote it. Also rewrote the initial system prompt — the generated version did not reliably produce the `get_previous_findings`-first behaviour until I strengthened the instruction.
- **I wrote by hand:** The four-table schema design and the decision to separate `ToolCall` from `Finding`. The `get_previous_findings`-first instruction in the system prompt. The `LLMAdapter` ABC interface. This `DECISIONS.md`.
- **Where Claude Code led me astray:** <<A concrete example from your build. E.g., a silently swallowed exception, an incorrect message format, a missing index in a migration.>>

Discipline I held: one phase per Claude Code session, reviewed every diff, ran `pytest` before committing, committed per phase. The repository's commit history reflects this progression.

---

## 6. Known Limitations

- Public HTTPS GitHub URLs only. No private repos, no GitLab or Bitbucket.
- `read_file` caps at 200 lines per call. For large files the agent must page, consuming iterations.
- `commit_sha` is captured on `Repository`, not `ResearchSession`. A re-clone between two sessions on the same repo shifts the commit underlying earlier findings.
- The agent cannot execute code — only read it.
- Synchronous request handling: one slow session blocks a Django worker.
- No authentication, no rate limiting — explicitly out of scope per the brief.

---

**Word count:** <<run `wc -w DECISIONS.md` before submitting; target 500–800>>
