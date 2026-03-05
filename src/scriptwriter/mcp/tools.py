from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from langchain_core.tools import BaseTool

from scriptwriter.mcp.client import build_servers_config

logger = logging.getLogger(__name__)

_MCP_CACHE_LOCK = threading.Lock()
_MCP_CACHE_SIGNATURE: str | None = None
_MCP_CACHE_TOOLS: list[BaseTool] | None = None


def _env_signature() -> str:
    raw = "|".join(
        [
            os.getenv("SCRIPTWRITER_MCP_SERVERS_JSON", ""),
            os.getenv("SCRIPTWRITER_ENABLE_BRAVE_MCP", ""),
            os.getenv("BRAVE_API_KEY", ""),
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_mcp_tools() -> list[BaseTool]:
    """Get all tools from enabled MCP servers."""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed.")
        return []

    servers_config = build_servers_config()
    if not servers_config:
        logger.info("No enabled MCP servers configured")
        return []

    try:
        logger.info(
            "Initializing MultiServerMCPClient with %d server(s)",
            len(servers_config),
        )
        client = MultiServerMCPClient(servers_config)
        tools = await client.get_tools()
        logger.info("Successfully loaded %d tool(s) from MCP servers", len(tools))
        return tools
    except Exception as exc:
        logger.error("Failed to load MCP tools: %s", exc, exc_info=True)
        return []


def _load_tools_sync() -> list[BaseTool]:
    try:
        asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, get_mcp_tools())
            return future.result()
    except RuntimeError:
        return asyncio.run(get_mcp_tools())


def get_cached_mcp_tools(force_reload: bool = False) -> list[BaseTool]:
    global _MCP_CACHE_SIGNATURE, _MCP_CACHE_TOOLS

    signature = _env_signature()
    with _MCP_CACHE_LOCK:
        if (
            not force_reload
            and _MCP_CACHE_TOOLS is not None
            and _MCP_CACHE_SIGNATURE == signature
        ):
            return _MCP_CACHE_TOOLS

    tools = _load_tools_sync()
    with _MCP_CACHE_LOCK:
        _MCP_CACHE_TOOLS = tools
        _MCP_CACHE_SIGNATURE = signature
        return _MCP_CACHE_TOOLS


def reset_mcp_tools_cache() -> None:
    global _MCP_CACHE_SIGNATURE, _MCP_CACHE_TOOLS
    with _MCP_CACHE_LOCK:
        _MCP_CACHE_SIGNATURE = None
        _MCP_CACHE_TOOLS = None
