def get_mock_embedding(text: str) -> list[float]:
    """
    MVP embedding placeholder.
    Keep deterministic length to make retrieval pipeline testable without external model calls.
    """
    _ = text
    return [0.1] * 1536
