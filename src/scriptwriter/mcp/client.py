import logging
from typing import Any
from scriptwriter.config.extensions import ExtensionsConfig

logger = logging.getLogger(__name__)

def build_server_params(server_name: str, config: dict) -> dict[str, Any]:
    """Build server parameters for MultiServerMCPClient."""
    transport_type = config.get("type", "stdio")
    params: dict[str, Any] = {"transport": transport_type}

    if transport_type == "stdio":
        if not config.get("command"):
            raise ValueError(f"MCP server '{server_name}' with stdio transport requires 'command' field")
        params["command"] = config.get("command")
        params["args"] = config.get("args", [])
        if config.get("env"):
            params["env"] = config.get("env")
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")

    return params

def build_servers_config() -> dict[str, dict[str, Any]]:
    """Build servers configuration for MultiServerMCPClient mapping from names to params."""
    enabled_servers = ExtensionsConfig.get_enabled_mcp_servers()

    if not enabled_servers:
        logger.info("No enabled MCP servers found")
        return {}

    servers_config = {}
    for server_name, server_config in enabled_servers.items():
        try:
            servers_config[server_name] = build_server_params(server_name, server_config)
            logger.info(f"Configured MCP server: {server_name}")
        except Exception as e:
            logger.error(f"Failed to configure MCP server '{server_name}': {e}")

    return servers_config
