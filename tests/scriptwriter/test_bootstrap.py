import importlib
from pathlib import Path

import pytest


def test_app_module_importable(monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_SKIP_DEPENDENCY_CHECK", "1")
    module = importlib.import_module("scriptwriter.main")
    assert hasattr(module, "app")


def test_app_startup_fails_when_knowledge_dependencies_unavailable(monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_SKIP_DEPENDENCY_CHECK", "0")

    with pytest.raises(RuntimeError, match="pg down"):
        module = importlib.import_module("scriptwriter.knowledge.dependencies")
        monkeypatch.setattr(module, "check_knowledge_dependencies", lambda: (_ for _ in ()).throw(RuntimeError("pg down")))
        importlib.reload(importlib.import_module("scriptwriter.api.app"))


def test_env_example_contains_required_knowledge_settings():
    text = Path(".env.example").read_text(encoding="utf-8")
    required = [
        "SCRIPTWRITER_KNOWLEDGE_PG_DSN=",
        "SCRIPTWRITER_OPENSEARCH_URL=",
        "SCRIPTWRITER_OPENSEARCH_INDEX=",
        "SCRIPTWRITER_QUERY_REWRITE_MODEL=",
        "SCRIPTWRITER_RERANK_MODEL=",
        "SCRIPTWRITER_MEMORY_PG_DSN=",
        "SCRIPTWRITER_MEMORY_REDIS_URL=",
    ]
    for key in required:
        assert key in text
