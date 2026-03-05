
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

import scriptwriter.agents.lead_agent.writer as writer_module
from scriptwriter.agents.lead_agent.writer import writer_node
from scriptwriter.tools.builtins.web_search import WebSearchHit


def test_writer_triggers_web_search_for_hot_topic(monkeypatch):
    monkeypatch.setattr(
        writer_module,
        "search_web_hits",
        lambda *args, **kwargs: [
            WebSearchHit(
                title="Trending Event",
                url="https://example.com/trend",
                snippet="A trending event happened today.",
                source="duckduckgo",
            )
        ],
    )
    monkeypatch.setattr(writer_module, "get_cached_mcp_tools", lambda: [])

    state = {
        "messages": [HumanMessage(content="写一个关于今天热点新闻的开场")],
        "user_id": "u1",
        "project_id": "p1",
        "thread_id": "thread_1",
        "thread_data": {},
        "revision_count": 0,
        "critic_notes": [],
        "plan": [],
        "current_draft": "",
        "artifacts": {},
    }

    # Mock LLM to avoid API calls
    class FakeLLM:
        def invoke(self, messages, **kwargs):
            return AIMessage(content="Today is sunny.")
        def bind_tools(self, *args, **kwargs):
            return self

    delta = writer_node(state, llm=FakeLLM())

    assert delta["artifacts"]["web_search_used"] is True
    assert "Trending Event" in delta["artifacts"]["web_context_debug"]


def test_writer_executes_tool_calling_loop(monkeypatch):
    captured: dict[str, object] = {}

    class SearchSchema(BaseModel):
        query: str

    class FakeSearchTool(BaseTool):
        name: str = "search_web"
        description: str = "search the web"
        args_schema: type[BaseModel] = SearchSchema

        def _run(self, query: str, run_manager=None, **kwargs):
            captured["payload"] = {"query": query}
            captured["config"] = kwargs.get("config") # In create_agent, it might be passed in kwargs
            # Actually, standard tools don't get config in _run unless specified.
            # But let's see.
            return "web result text"

    class FakeBibleTool(BaseTool):
        name: str = "search_story_bible"
        description: str = "search the bible"
        def _run(self, query: str):
            return "bible results"

    class FakeLLM:
        def __init__(self):
            self.calls = 0
        
        def bind_tools(self, tools, **kwargs):
            return self

        def invoke(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_web",
                            "args": {"query": "today ai trend"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(content="INT. ABANDONED FACTORY - DAY\nJohn looks around. He runs.")

    monkeypatch.setattr(writer_module, "get_cached_mcp_tools", lambda: [])
    monkeypatch.setattr(writer_module, "search_web", FakeSearchTool())
    monkeypatch.setattr(writer_module, "search_story_bible", FakeBibleTool())

    state = {
        "messages": [HumanMessage(content="Write a suspense scene")],
        "user_id": "u1",
        "project_id": "p1",
        "thread_id": "thread_1",
        "thread_data": {},
        "revision_count": 0,
        "critic_notes": [],
        "plan": [],
        "current_draft": "",
        "artifacts": {},
    }

    # In create_agent, we need a real-ish LLM or something that satisfies the interface
    llm = FakeLLM()
    delta = writer_node(state, llm=llm)

    assert "He runs." in delta["current_draft"]
    assert delta["artifacts"]["writer_tool_calls"]
    assert delta["artifacts"]["writer_tool_calls"][0]["tool"] == "search_web"
