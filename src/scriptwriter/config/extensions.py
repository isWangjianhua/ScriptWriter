import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ExtensionsConfig:
    @staticmethod
    def _load_servers_from_env() -> dict[str, dict[str, Any]]:
        raw = os.getenv("SCRIPTWRITER_MCP_SERVERS_JSON", "").strip()
        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in SCRIPTWRITER_MCP_SERVERS_JSON; MCP servers disabled")
            return {}

        if not isinstance(parsed, dict):
            logger.warning("SCRIPTWRITER_MCP_SERVERS_JSON must be a JSON object; MCP servers disabled")
            return {}

        return {
            name: cfg
            for name, cfg in parsed.items()
            if isinstance(name, str) and isinstance(cfg, dict)
        }

    @staticmethod
    def _load_legacy_brave_config() -> dict[str, dict[str, Any]]:
        if os.getenv("SCRIPTWRITER_ENABLE_BRAVE_MCP") != "1":
            return {}

        return {
            "brave-search": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")},
            }
        }

    @classmethod
    def get_enabled_mcp_servers(cls) -> dict[str, dict[str, Any]]:
        """
        Load MCP server definitions from env config and return only enabled entries.
        """
        servers = cls._load_servers_from_env()
        if not servers:
            servers = cls._load_legacy_brave_config()

        enabled_servers: dict[str, dict[str, Any]] = {}
        for name, cfg in servers.items():
            if cfg.get("enabled", True):
                enabled_servers[name] = cfg
        return enabled_servers
