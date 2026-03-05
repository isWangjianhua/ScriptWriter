from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx
from langchain_core.tools import tool


@dataclass(frozen=True)
class WebSearchHit:
    title: str
    url: str
    snippet: str
    source: str


def _get_langchain_ddg_results_tool():
    try:
        from langchain_community.tools import DuckDuckGoSearchResults

        return DuckDuckGoSearchResults
    except Exception:
        return None


def _parse_langchain_result(raw: object, *, source: str) -> list[WebSearchHit]:
    hits: list[WebSearchHit] = []

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("snippet") or "").strip()
            url = str(item.get("link") or item.get("url") or "").strip()
            snippet = str(item.get("snippet") or item.get("body") or title).strip()
            if title and url:
                hits.append(WebSearchHit(title=title, url=url, snippet=snippet, source=source))
        return hits

    if isinstance(raw, str):
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        for line in lines:
            url_match = re.search(r"https?://\S+", line)
            if not url_match:
                continue
            url = url_match.group(0).rstrip(",.;")
            snippet = line.replace(url_match.group(0), "").strip(" -,:;") or line
            title = snippet.split(" - ", 1)[0].strip() or "Web result"
            hits.append(WebSearchHit(title=title, url=url, snippet=snippet, source=source))

    return hits


def _search_langchain_duckduckgo(
    query: str,
    *,
    max_results: int,
) -> list[WebSearchHit]:
    tool_cls = _get_langchain_ddg_results_tool()
    if tool_cls is None:
        return []

    tool = tool_cls(num_results=max_results)
    raw = tool.invoke(query)
    hits = _parse_langchain_result(raw, source="langchain-ddg")
    return hits[:max_results]


def _search_brave(query: str, *, max_results: int, timeout_sec: float) -> list[WebSearchHit]:
    api_key = os.getenv("BRAVE_API_KEY", "").strip()
    if not api_key:
        return []

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": max_results}

    with httpx.Client(timeout=timeout_sec) as client:
        response = client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

    web_payload = payload.get("web", {}) if isinstance(payload, dict) else {}
    items = web_payload.get("results", []) if isinstance(web_payload, dict) else []

    hits: list[WebSearchHit] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("description") or "").strip()
        if not title or not url:
            continue
        hits.append(WebSearchHit(title=title, url=url, snippet=snippet, source="brave"))

    return hits[:max_results]


def _iter_ddg_topics(raw_topics: list[object]) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    for item in raw_topics:
        if not isinstance(item, dict):
            continue
        if "Topics" in item and isinstance(item["Topics"], list):
            flattened.extend(_iter_ddg_topics(item["Topics"]))
            continue
        flattened.append(item)
    return flattened


def _search_duckduckgo(query: str, *, max_results: int, timeout_sec: float) -> list[WebSearchHit]:
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }

    with httpx.Client(timeout=timeout_sec) as client:
        response = client.get("https://api.duckduckgo.com/", params=params)
        response.raise_for_status()
        payload = response.json()

    related = payload.get("RelatedTopics", []) if isinstance(payload, dict) else []
    topics = _iter_ddg_topics(related if isinstance(related, list) else [])

    hits: list[WebSearchHit] = []
    for item in topics:
        text = str(item.get("Text") or "").strip()
        url = str(item.get("FirstURL") or "").strip()
        if not text or not url:
            continue
        title = text.split(" - ", 1)[0].strip()
        hits.append(WebSearchHit(title=title or text, url=url, snippet=text, source="duckduckgo"))

    return hits[:max_results]


def search_web_hits(
    query: str,
    *,
    max_results: int = 5,
    timeout_sec: float = 8.0,
) -> list[WebSearchHit]:
    q = query.strip()
    if not q:
        return []

    k = min(max(max_results, 1), 10)

    # Priority 1: LangChain-native internet search tool
    try:
        lc_hits = _search_langchain_duckduckgo(q, max_results=k)
        if lc_hits:
            return lc_hits
    except Exception:
        pass

    # Priority 2: Brave Search API
    try:
        brave_hits = _search_brave(q, max_results=k, timeout_sec=timeout_sec)
        if brave_hits:
            return brave_hits
    except Exception:
        pass

    # Priority 3: direct DDG fallback
    try:
        return _search_duckduckgo(q, max_results=k, timeout_sec=timeout_sec)
    except Exception:
        return []


def _format_hits(hits: list[WebSearchHit]) -> str:
    if not hits:
        return "No relevant web search results found."

    lines: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        lines.append(f"{idx}. {hit.title}\n{hit.snippet}\n{hit.url}\n[source: {hit.source}]")
    return "\n\n".join(lines)


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the internet for latest/hot topics, news, and public information."""
    hits = search_web_hits(query, max_results=max_results)
    return _format_hits(hits)
