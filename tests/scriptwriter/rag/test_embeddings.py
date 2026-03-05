from scriptwriter.rag.embeddings import get_embeddings, get_query_embedding


def test_embeddings_fallback_is_deterministic(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SCRIPTWRITER_EMBEDDING_PROVIDER", "mock")

    a1 = get_query_embedding("hero enters")
    a2 = get_query_embedding("hero enters")
    b = get_query_embedding("villain enters")

    assert len(a1) == len(a2) == len(b) == 1536
    assert a1 == a2
    assert a1 != b


def test_embeddings_batch_size_matches_inputs(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SCRIPTWRITER_EMBEDDING_PROVIDER", "mock")

    vectors = get_embeddings(["a", "b", "c"])
    assert len(vectors) == 3
    assert all(len(v) == 1536 for v in vectors)
