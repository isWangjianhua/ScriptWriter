from scriptwriter.config.extensions import ExtensionsConfig


def test_mcp_servers_default_to_empty(monkeypatch):
    monkeypatch.delenv("SCRIPTWRITER_MCP_SERVERS_JSON", raising=False)
    monkeypatch.delenv("SCRIPTWRITER_ENABLE_BRAVE_MCP", raising=False)
    assert ExtensionsConfig.get_enabled_mcp_servers() == {}


def test_mcp_servers_loaded_from_json_env(monkeypatch):
    monkeypatch.setenv(
        "SCRIPTWRITER_MCP_SERVERS_JSON",
        '{"alpha":{"type":"stdio","command":"echo","enabled":true},"beta":{"enabled":false}}',
    )
    servers = ExtensionsConfig.get_enabled_mcp_servers()
    assert "alpha" in servers
    assert "beta" not in servers
