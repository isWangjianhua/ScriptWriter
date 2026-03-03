# Auto-Screenwriter Architecture (MVP focus)

## System Goals
Transition from a simple "single-prompt scriptwriter" to a multi-agent orchestrated application powered by LangGraph, enabling robust production-grade capabilities for generating long-form serialized scripts.

## Core Pillars
1. **Hybrid Memory Architecture (L0-L3)** to prevent "amnesia" and logical contradictions natively.
2. **Multi-Agent Flow (Planner -> Writer/Dispatcher -> Critic -> Reflector)** to delegate responsibilities clearly.
3. **NDJSON HTTP Streaming (Fetch API)** to enable a modern "Typing Chat (Left) + Updating Canvas (Right)" interface natively suited for React apps.

## MVP Implementation Strategy

The MVP will specifically target the following functional subset to prove the End-to-End value without getting bogged down in Database configurations.

### 1. Functional Scope 
* A simple script generation flow: Idea -> Setup (Characters/Setting) -> Outline (1 episode) -> Script Body (1 episode).
* The **Critic Node** acts as a self-correction mechanism to iterate a draft *before* yielding it to the user.
* **Basic External RAG (New Addition per user request)**: The Writer agent will be equipped with a basic local knowledge retrieval tool (using `ChromaDB` or similar lightweight vector store) to ingest and query simple reference documents (e.g. a provided novel).

### 2. Backend Stack (The Engine)
* `FastAPI` as the web delivery server.
* `LangGraph` and `LangChain` to construct the `StateGraph` and its nodes.
* `SqliteSaver` for L0 Checkpointer memory (to resume conversations).
* Memory Store: Provide a simple endpoint to ingest a `.txt` file into an ephemeral ChromaDB instance, linked to the tool for the `Writer`.

### 3. API & Communication Spec (The NDJSON Route)
Expose a single main conversational endpoint `/api/chat` using `StreamingResponse`. The payload chunks will be Line-Delimited JSON matching Vercel AI SDK expectations to easily plug a hypothetical React frontend into it:
```json
{"type": "chat_chunk", "content": "Let me..."}
{"type": "tool_start", "name": "rag_search"}
{"type": "canvas_update", "component": "outline", "data": {...}}
```

## Later Phases
* **Beta**: Introduce World Tracker Ledger (L3), inter-episode Overlap Method fetching, and Human-in-the-loop interruption breaks.
* **V1.0**: Full Postgres (`pgvector`) multitenant database migration, and Long-chapter Planner for N-episode cascading generation.
