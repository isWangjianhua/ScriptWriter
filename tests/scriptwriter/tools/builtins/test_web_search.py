import scriptwriter.tools.builtins.web_search as web_search_module
from scriptwriter.tools.builtins.web_search import WebSearchHit, search_web


def test_search_web_formats_results(monkeypatch):
    monkeypatch.setattr(
        web_search_module,
        "search_web_hits",
        lambda *args, **kwargs: [
            WebSearchHit(
                title="Hot Topic",
                url="https://example.com/hot",
                snippet="Latest development summary",
                source="brave",
            )
        ],
    )

    output = search_web.invoke({"query": "latest hot topic", "max_results": 3})

    assert "Hot Topic" in output
    assert "https://example.com/hot" in output
    assert "[source: brave]" in output


def test_search_web_empty_fallback(monkeypatch):
    monkeypatch.setattr(web_search_module, "search_web_hits", lambda *args, **kwargs: [])

    output = search_web.invoke({"query": "x", "max_results": 1})
    assert output == "No relevant web search results found."


def test_search_web_hits_prefers_langchain_tool(monkeypatch):
    class _Tool:
        def __init__(self, num_results: int):
            self.num_results = num_results

        def invoke(self, query: str):
            _ = query
            return [
                {
                    "title": "LangChain Result",
                    "link": "https://example.com/langchain",
                    "snippet": "from langchain tool",
                }
            ]

    monkeypatch.setattr(web_search_module, "_get_langchain_ddg_results_tool", lambda: _Tool)
    monkeypatch.setattr(
        web_search_module,
        "_search_brave",
        lambda *args, **kwargs: [
            WebSearchHit("Brave Result", "https://example.com/brave", "from brave", "brave")
        ],
    )

    hits = web_search_module.search_web_hits("latest ai", max_results=3)

    assert hits
    assert hits[0].source == "langchain-ddg"
    assert hits[0].title == "LangChain Result"
