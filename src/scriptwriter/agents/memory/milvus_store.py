from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

GLOBAL_COLLECTION_NAME = "global_script_vectors"
_milvus_client: Any | None = None
_data_type: Any | None = None
_init_error: Exception | None = None


def _get_milvus_client() -> Any | None:
    global _milvus_client, _data_type, _init_error

    if _milvus_client is not None:
        return _milvus_client
    if _init_error is not None:
        return None

    try:
        from pymilvus import DataType, MilvusClient

        _milvus_client = MilvusClient("./data/milvus_demo.db")
        _data_type = DataType
        return _milvus_client
    except Exception as exc:
        _init_error = exc
        logger.warning("Milvus unavailable, story bible search disabled: %s", exc)
        return None


def _escape_filter_value(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace('"', '\\"')


def _ensure_collection_exists(dimension: int) -> bool:
    client = _get_milvus_client()
    if client is None or _data_type is None:
        return False

    if not client.has_collection(GLOBAL_COLLECTION_NAME):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=_data_type.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="vector", datatype=_data_type.FLOAT_VECTOR, dim=dimension)
        schema.add_field(field_name="user_id", datatype=_data_type.VARCHAR, max_length=255)
        schema.add_field(field_name="project_id", datatype=_data_type.VARCHAR, max_length=255)
        schema.add_field(field_name="text", datatype=_data_type.VARCHAR, max_length=65535)
        schema.add_field(field_name="source", datatype=_data_type.VARCHAR, max_length=255)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="FLAT")
        index_params.add_index(field_name="user_id", index_type="Trie")
        index_params.add_index(field_name="project_id", index_type="Trie")

        client.create_collection(
            collection_name=GLOBAL_COLLECTION_NAME,
            schema=schema,
            index_params=index_params,
        )
    return True


def add_texts_to_milvus(
    user_id: str,
    project_id: str,
    texts: list[str],
    vectors: list[list[float]],
) -> bool:
    if not texts or not vectors or len(texts) != len(vectors):
        return False

    if not _ensure_collection_exists(dimension=len(vectors[0])):
        return False

    client = _get_milvus_client()
    if client is None:
        return False

    data = [
        {
            "vector": vectors[i],
            "text": texts[i],
            "user_id": user_id,
            "project_id": project_id,
            "source": "user_upload",
        }
        for i in range(len(texts))
    ]
    client.insert(collection_name=GLOBAL_COLLECTION_NAME, data=data)
    return True


def search_milvus_bible(user_id: str, project_id: str, query_vector: list[float], limit: int = 2) -> list[str]:
    client = _get_milvus_client()
    if client is None or not client.has_collection(GLOBAL_COLLECTION_NAME):
        return []

    safe_user_id = _escape_filter_value(user_id)
    safe_project_id = _escape_filter_value(project_id)
    filter_expr = f'user_id == "{safe_user_id}" and project_id == "{safe_project_id}"'

    search_res = client.search(
        collection_name=GLOBAL_COLLECTION_NAME,
        data=[query_vector],
        limit=limit,
        filter=filter_expr,
        output_fields=["text", "source"],
    )

    results: list[str] = []
    for hits in search_res:
        for hit in hits:
            entity = hit.get("entity", {})
            text = entity.get("text")
            if isinstance(text, str):
                results.append(text)
    return results
