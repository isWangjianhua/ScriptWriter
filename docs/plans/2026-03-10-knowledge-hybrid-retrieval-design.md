# Knowledge Hybrid Retrieval Redesign

## Goal
Upgrade the current project knowledge subsystem so that:
- metadata and chunk records are stored in PostgreSQL
- keyword retrieval is provided by OpenSearch/Elasticsearch
- vector retrieval continues to use Milvus
- query execution becomes `rewrite -> hybrid retrieve -> rerank`
- all three dependencies are strong requirements (no fallback mode)

## Product Constraints (Confirmed)
- `PostgreSQL`, `OpenSearch`, and `Milvus` are mandatory.
- If any dependency is unavailable, startup and runtime should fail explicitly.
- Query rewrite and rerank use LLM.
- Add `.env.example` to document required runtime configuration.

## Architecture

### Storage and Index Layers
- **PostgreSQL** becomes the source of truth for knowledge metadata:
  - document rows
  - chunk rows
  - filterable fields (`source_type`, `version_id`, `episode_id`, `scene_id`, `is_active`)
- **OpenSearch** stores chunk-level keyword index for BM25-style retrieval.
- **Milvus** stores chunk-level vector embeddings and filter metadata.

### Retrieval Pipeline
1. **Rewrite**: LLM rewrites user query into retrieval-focused query text.
2. **Hybrid retrieve**:
   - keyword retrieval from OpenSearch (top-N)
   - vector retrieval from Milvus (top-N)
   - merge and deduplicate by `chunk_id`
   - fuse scores (RRF)
3. **Rerank**: LLM reranks fused candidates and outputs final top-K.

### Service Contract Strategy
- Keep public knowledge service method signatures stable where possible:
  - `ingest_knowledge_document(...)`
  - `search_knowledge_hits(...)`
  - `search_project_knowledge_hits(...)`
- Internally replace the SQLite-centric implementation with a repository + pipeline model.

## Data Model Design

### PostgreSQL tables
- `knowledge_documents`
  - `doc_id` (PK), `user_id`, `project_id`, `doc_type`, `title`, `path_l1`, `path_l2`, `source_path`, `created_at`, `updated_at`
- `knowledge_chunks`
  - `chunk_id` (PK), `doc_id` (FK), `chunk_order`, `segment_type`, `text`
  - `source_type`, `version_id`, `episode_id`, `scene_id`, `is_active`

### OpenSearch index
- index name: `knowledge_chunks_v1` (configurable)
- doc id: `chunk_id`
- fields:
  - text fields: `text`, `title`, `path_l1`, `path_l2`
  - filter fields: `user_id`, `project_id`, `doc_id`, `doc_type`, `source_type`, `version_id`, `episode_id`, `scene_id`, `is_active`

### Milvus records
- keep one global collection with strict filters
- required per-record metadata:
  - `chunk_id`, `doc_id`, `user_id`, `project_id`, `doc_type`
  - `path_l1`, `path_l2`, `chunk_order`, `segment_type`
  - `source_type`, `version_id`, `episode_id`, `scene_id`, `is_active`, `title`

## Ingest Flow
1. Validate payload and chunk content.
2. Persist source text to configured RAG source directory.
3. Upsert document and chunk metadata in PostgreSQL.
4. Upsert keyword docs in OpenSearch.
5. Insert vectors in Milvus.
6. If step 4 or 5 fails, raise explicit error and execute compensating rollback for prior external writes where possible.

## Search Flow
1. LLM query rewrite.
2. OpenSearch keyword search with project/user filters.
3. Milvus vector search with project/user filters.
4. RRF score fusion and deduplication.
5. LLM rerank over fused candidates.
6. Return `KnowledgeHit` list with source metadata and backend markers.

## Error Handling and Availability
- Startup performs strict health checks for PostgreSQL, OpenSearch, Milvus.
- Any dependency failure blocks app startup.
- Runtime dependency errors propagate as service exceptions (no fallback to SQLite path or single-backend retrieval).

## Configuration and Environment

### Required environment variables
- `SCRIPTWRITER_KNOWLEDGE_PG_DSN`
- `SCRIPTWRITER_OPENSEARCH_URL`
- `SCRIPTWRITER_OPENSEARCH_INDEX`
- `SCRIPTWRITER_MILVUS_DB_PATH` or Milvus connection setting used by deployment
- `OPENAI_API_KEY`
- `SCRIPTWRITER_QUERY_REWRITE_MODEL`
- `SCRIPTWRITER_RERANK_MODEL`

### Tunables
- `SCRIPTWRITER_RETRIEVAL_TOPN_VECTOR`
- `SCRIPTWRITER_RETRIEVAL_TOPN_KEYWORD`
- `SCRIPTWRITER_RETRIEVAL_TOPK_FINAL`

### Documentation artifact
- Add `.env.example` with all required variables and reasonable defaults/comments.

## Testing Strategy
- Unit tests for:
  - rewrite behavior and fallback errors
  - OpenSearch query builder
  - RRF fusion and dedupe
  - rerank output handling
- Integration-style tests with monkeypatched clients for:
  - ingest success path across PG + OpenSearch + Milvus
  - ingest failure and compensation behavior
  - search pipeline ordering (`rewrite -> hybrid -> rerank`)
  - strong dependency failure behavior
- API tests for:
  - `/api/projects/{project_id}/knowledge/upload` failure propagation
  - built-in tool search behavior with rewritten/reranked outputs

## Out of Scope
- introducing async workers for indexing
- introducing eventual consistency queues
- distributed transaction coordination across all stores

