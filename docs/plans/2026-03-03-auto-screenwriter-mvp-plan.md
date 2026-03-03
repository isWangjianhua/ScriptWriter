# Auto-Screenwriter MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the MVP of the Auto-Screenwriter Agent using LangGraph, FastAPI, and NDJSON streaming with a simple Text-based RAG tool.

**Architecture:** A FastAPI backend exposing a single `/api/chat` streaming endpoint. The backend orchestrates a LangGraph `StateGraph` with a `Writer` node and a `Critic` self-correction loop. We will implement NDJSON chunking for SSE-like streaming over standard HTTP. A simple `Chroma` local instance will be used for the RAG functionality.

**Tech Stack:** Python 3.10+, FastAPI, LangGraph, LangChain, ChromaDB, Uvicorn, Pytest.

---

### Task 1: Project Setup & Dependencies

**Files:**
- Create: `requirements.txt`
- Modify: (None)
- Test: (None)

**Step 1: Write requirements.txt**

```text
fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.3
langchain==0.1.12
langgraph==0.0.26
langchain-openai==0.0.8
chromadb==0.4.24
pytest==8.0.2
httpx==0.27.0
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore: add MVP dependencies to requirements.txt"
```

---

### Task 2: Define Core State Graph

**Files:**
- Create: `app/core/state.py`
- Create: `tests/app/core/test_state.py`

**Step 1: Write the failing test**

```python
# tests/app/core/test_state.py
from app.core.state import ScreenplayState

def test_screenplay_state_dict():
    state: ScreenplayState = {
        "messages": [],
        "project_id": "test_project",
        "current_draft": "",
        "critic_notes": [],
        "revision_count": 0,
        "artifacts": {}
    }
    assert state["project_id"] == "test_project"
    assert state["revision_count"] == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/app/core/test_state.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app'"

**Step 3: Write minimal implementation**

```python
# app/core/state.py
from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langchain_core.messages import BaseMessage

class ScreenplayState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    project_id: str
    
    # Text state
    current_draft: str
    
    # Critic state
    critic_notes: List[str]
    revision_count: int
    
    # Payload for Frontend UI
    artifacts: Dict[str, Any]
```
*(Remember to create empty `__init__.py` files in `app/` and `app/core/`)*

**Step 4: Run test to verify it passes**

Run: `pytest tests/app/core/test_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/core/state.py tests/app/core/test_state.py app/__init__.py app/core/__init__.py
git commit -m "feat: define ScreenplayState typing"
```

---

### Task 3: Build Simple Vector Store (RAG)

**Files:**
- Create: `app/memory/vector_store.py`
- Create: `app/agents/tools.py`
- Test: `tests/app/test_vector_store.py`

**Step 1: Write the failing test**

```python
# tests/app/test_vector_store.py
from app.agents.tools import search_story_bible

def test_search_story_bible():
    from app.memory.vector_store import add_texts_to_bible
    # Ingest text
    add_texts_to_bible("test_project_123", ["The protagonist's name is John Connor."])
    
    # Search text
    results = search_story_bible.invoke({"project_id": "test_project_123", "query": "What is the protagonist's name?"})
    assert "John Connor" in results
```

**Step 2: Write minimal implementation**

```python
# app/memory/vector_store.py
import chromadb
from langchain_openai import OpenAIEmbeddings

# Using persistent client in a local directory
chroma_client = chromadb.PersistentClient(path="./data/chroma")

def add_texts_to_bible(project_id: str, texts: list[str]):
    collection = chroma_client.get_or_create_collection(name=f"bible_{project_id}")
    collection.add(
        documents=texts,
        metadatas=[{"source": "user_upload"} for _ in texts],
        ids=[f"doc_{i}" for i in range(len(texts))]
    )
```

```python
# app/agents/tools.py
from langchain_core.tools import tool
from app.memory.vector_store import chroma_client

@tool
def search_story_bible(project_id: str, query: str) -> str:
    """Useful to search for rules, character names, or backgrounds from the user's uploaded story bible."""
    try:
        collection = chroma_client.get_collection(name=f"bible_{project_id}")
        results = collection.query(query_texts=[query], n_results=2)
        if not results['documents'] or not results['documents'][0]:
            return "No relevant information found."
        return "\n".join(results['documents'][0])
    except Exception:
        return "Knowledge base not initialized for this project."
```
*(Remember to create `app/memory/__init__.py` and `app/agents/__init__.py`)*

**Step 3: Run test to verify it passes**
Run: `pytest tests/app/test_vector_store.py -v`
Expected: PASS

**Step 4: Commit**
```bash
git add app/memory app/agents tests/app/test_vector_store.py
git commit -m "feat: add local ChromaDB RAG tool"
```

---

### Task 4: Construct Nodes and Graph

**Files:**
- Create: `app/agents/writer.py`
- Create: `app/agents/critic.py`
- Create: `app/workflow/graph.py`

*(Due to length, I'll describe the steps conceptually)*
1. Create `writer_node`: Calls LLM bound with `search_story_bible` tool. Updates `current_draft` and `artifacts`.
2. Create `critic_node`: Reviews `current_draft`. If bad, appends to `critic_notes` and increments `revision_count`.
3. Create `graph.py`: Wires `writer_node` -> `critic_node`. Adds a conditional edge from `critic_node`: if `revision_count < 3` and has errors -> `writer_node`, else -> `END`.
4. Add basic mock tests to ensure the nodes don't crash and the graph compiles.
5. Commit.

---

### Task 5: NDJSON Streaming API with LangGraph

**Files:**
- Create: `app/api/endpoints.py`
- Create: `app/main.py`
- Test: `tests/app/api/test_endpoints.py`

**Step 1: Write the API endpoint**

```python
# app/api/endpoints.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
from app.workflow.graph import compiled_graph
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post("/api/chat")
async def chat_stream(request: Request):
    data = await request.json()
    user_input = data.get("message")
    project_id = data.get("project_id", "default_project")
    
    async def event_generator():
        config = {"configurable": {"thread_id": project_id}}
        inputs = {"messages": [HumanMessage(content=user_input)], "project_id": project_id, "revision_count": 0}
        
        async for event in compiled_graph.astream_events(inputs, config, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield json.dumps({"type": "chat_chunk", "content": chunk}) + "\n"
            elif kind == "on_tool_start":
                yield json.dumps({"type": "tool_start", "name": event["name"]}) + "\n"
            elif kind == "on_node_end" and event["name"] == "writer_node":
                out = event["data"].get("output", {})
                if "artifacts" in out:
                    yield json.dumps({"type": "canvas_update", "data": out["artifacts"]}) + "\n"
                    
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
```

**Step 2: Add Main App Setup and Tests**
Setup FastApi initialization in `main.py` and run a basic HTTpx test.

**Step 3: Commit**
```bash
git add app/api app/main.py
git commit -m "feat: add NDJSON streaming chat endpoint"
```
