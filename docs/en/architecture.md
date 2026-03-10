# Architecture Overview

## Runtime Topology

ScriptWriter currently runs as a single FastAPI process centered on project workflow management.

- API: project CRUD, workflow chat, confirmation, version listing, knowledge ingest
- Workflow: `bible -> outline -> draft`, advanced synchronously per request
- Project state: in-memory repository for projects, versions, and confirmation records
- Knowledge: PostgreSQL metadata, OpenSearch keyword index, plus Milvus vector search
- Tools: built-in knowledge and web search tools

```mermaid
flowchart TB
    Client[Client]

    subgraph API[FastAPI API]
      App["api/app.py"]
      Router["api/routers/projects.py"]
    end

    subgraph Workflow[Project Workflow]
      Service["projects/service.py"]
      Planner["agent/service.py"]
      Prompts["agent/prompts.py"]
      Store["projects/store.py"]
      Memory["projects/memory.py"]
      Model["projects/workflow.py"]
    end

    subgraph Knowledge[Knowledge Layer]
      KService["knowledge/service.py"]
      Meta["knowledge/metadata_store_pg.py"]
      Keyword["knowledge/keyword_store.py"]
      Milvus["knowledge/milvus_store.py"]
      Emb["knowledge/embeddings.py"]
    end

    subgraph Tools[Tools]
      Builtins["tools/builtins/*"]
    end

    Client --> App --> Router
    Router --> Service
    Service --> Planner
    Service --> Prompts
    Service --> Store
    Service --> Memory
    Service --> Model
    Router --> KService
    KService --> Meta
    KService --> Keyword
    KService --> Milvus
    KService --> Emb
    Service --> Builtins
```

## Project Workflow

The API is project-centric rather than thread-centric.

1. A client creates a project explicitly with `POST /api/projects`, or implicitly by calling `POST /api/projects/{project_id}/chat` with a `title`.
2. `ProjectService.handle_chat(...)` converts the current project state into a workflow state.
3. `plan_agent_action(...)` runs a LangGraph routing graph; routing rules currently use keyword heuristics such as approve, continue, and rewrite.
4. The service generates the next artifact version:
   - bible via `build_bible_prompt(...)`
   - outline via `build_outline_prompt(...)`
   - draft via `build_draft_prompt(...)`
   - rewrite via `build_rewrite_prompt(...)`
5. The updated project and artifact versions are returned as JSON.

```mermaid
flowchart TD
    A["POST /api/projects/<project_id>/chat"] --> B{"Project exists?"}
    B -- No --> C{"title provided?"}
    C -- No --> X["400 title required"]
    C -- Yes --> D["Create project + start workflow"]
    B -- Yes --> E["Load project"]
    D --> F["plan_agent_action(...)"]
    E --> F
    F --> G{"Action"}
    G -->|generate bible| H["save bible version"]
    G -->|confirm artifact| I["advance workflow"]
    G -->|generate outline| J["save outline version"]
    G -->|continue draft| K["save draft version"]
    G -->|rewrite draft| L["save rewritten draft version"]
    H --> M["Return project JSON"]
    I --> M
    J --> M
    K --> M
    L --> M
```

## Knowledge Flow

Knowledge ingest is separate from the in-memory project store.

1. `POST /api/projects/{project_id}/knowledge/upload` checks that the project exists.
2. `ingest_knowledge_document(...)` validates `doc_type`, segments text, and chunks it.
3. Source text is persisted under `${SCRIPTWRITER_RAG_DATA_DIR:-data/rag}/sources/`.
4. Document metadata is stored in PostgreSQL and chunk keyword index is upserted to OpenSearch.
5. Embeddings are generated and inserted into Milvus.

```mermaid
flowchart TD
    A["POST /api/projects/<project_id>/knowledge/upload"] --> B["Validate project exists"]
    B --> C["Validate content + doc_type"]
    C --> D["segment_content(...)"]
    D --> E["chunk_segments(...)"]
    E --> F["persist source text"]
    F --> G["upsert PostgreSQL metadata"]
    G --> H["upsert OpenSearch keyword index"]
    H --> I["embed chunks"]
    I --> J["insert vectors into Milvus"]
    J --> K["Return doc_id + chunk_count + source_path"]
```

## Module Map

### API

- `src/scriptwriter/api/app.py`: FastAPI app composition
- `src/scriptwriter/api/routers/projects.py`: all public routes

### Workflow

- `src/scriptwriter/projects/service.py`: project orchestration
- `src/scriptwriter/projects/workflow.py`: workflow states and transitions
- `src/scriptwriter/projects/store.py`: in-memory project/version store
- `src/scriptwriter/projects/models.py`: API and domain models
- `src/scriptwriter/agent/service.py`: LangGraph-based action routing graph
- `src/scriptwriter/agent/prompts.py`: artifact prompt builders

### Memory

- `src/scriptwriter/projects/memory.py`: in-memory character, world, fact, and timeline snapshot utilities

### Knowledge

- `src/scriptwriter/knowledge/service.py`: ingest and retrieval orchestration
- `src/scriptwriter/knowledge/metadata_store_pg.py`: PostgreSQL metadata and source management
- `src/scriptwriter/knowledge/keyword_store.py`: OpenSearch keyword index adapter
- `src/scriptwriter/knowledge/milvus_store.py`: vector storage and filtered search
- `src/scriptwriter/knowledge/embeddings.py`: OpenAI or hash-based embeddings

### Tools

- `src/scriptwriter/tools/builtins/`: knowledge search and web search tools

## Data Boundaries

- Project records and artifact versions: process memory only
- Knowledge metadata and sources: `${SCRIPTWRITER_RAG_DATA_DIR:-data/rag}`
- Milvus local database: `${SCRIPTWRITER_MILVUS_DB_PATH:-./data/milvus_demo.db}`

## Compatibility Notes

- Public APIs are project-scoped.
- There is no run persistence or recovery API in the current implementation.
- Restarting the service clears project workflow state but does not remove persisted knowledge files.
