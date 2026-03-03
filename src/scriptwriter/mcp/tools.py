import logging
from langchain_core.tools import BaseTool
from scriptwriter.mcp.client import build_servers_config

logger = logging.getLogger(__name__)

async def get_mcp_tools() -> list[BaseTool]:
    """Get all tools from enabled MCP servers using DeerFlow architecture."""
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
        logger.info(f"Initializing MultiServerMCPClient with {len(servers_config)} server(s)")
        
        # Instantiate the client
        client = MultiServerMCPClient(servers_config)
        
        # Connect to the underlying servers and extract their capabilities as LangChain tools
        tools = await client.get_tools()
        logger.info(f"Successfully loaded {len(tools)} tool(s) from MCP servers")

        return tools

    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
        return []
