import pytest

from scriptwriter.knowledge import dependencies


def test_check_knowledge_dependencies_raises_when_opensearch_unavailable(monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_SKIP_DEPENDENCY_CHECK", "0")
    monkeypatch.setenv("SCRIPTWRITER_KNOWLEDGE_PG_DSN", "postgresql://x")
    monkeypatch.setenv("SCRIPTWRITER_OPENSEARCH_URL", "http://localhost:9200")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    monkeypatch.setattr(dependencies, "_check_postgres", lambda: None)
    monkeypatch.setattr(dependencies, "_check_milvus", lambda: None)
    monkeypatch.setattr(
        dependencies,
        "_check_opensearch",
        lambda: (_ for _ in ()).throw(RuntimeError("os down")),
    )

    with pytest.raises(RuntimeError, match="os down"):
        dependencies.check_knowledge_dependencies()
