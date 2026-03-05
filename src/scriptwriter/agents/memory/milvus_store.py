from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

GLOBAL_COLLECTION_NAME = "global_script_vectors"
_milvus_client: Any | None = None
_data_type: Any | None = None
_init_error: Exception | None = None


def reset_milvus_for_tests() -> None:
    global _milvus_client, _data_type, _init_error
    _milvus_client = None
    _data_type = None
    _init_error = None


def _get_milvus_client() -> Any | None:
    global _milvus_client, _data_type, _init_error

    if _milvus_client is not None:
        return _milvus_client
    if _init_error is not None:
        return None

    try:
        from pymilvus import DataType, MilvusClient

        db_path = os.getenv("SCRIPTWRITER_MILVUS_DB_PATH", "./data/milvus_demo.db")
        _milvus_client = MilvusClient(db_path)
        _data_type = DataType
        return _milvus_client
    except Exception as exc:
        _init_error = exc
        logger.warning("Milvus unavailable, story bible search disabled: %s", exc)
        return None


def _escape_filter_value(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace('"', '\\"')


def _collection_field_names() -> set[str]:
    client = _get_milvus_client()
    if client is None:
        return set()

    try:
        info = client.describe_collection(GLOBAL_COLLECTION_NAME)
    except Exception:
        return set()

    fields = info.get("fields", []) if isinstance(info, dict) else []
    names = {
        str(field.get("name"))
        for field in fields
        if isinstance(field, dict) and isinstance(field.get("name"), str)
    }
    return names


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
        schema.add_field(field_name="doc_id", datatype=_data_type.VARCHAR, max_length=255)
        schema.add_field(field_name="doc_type", datatype=_data_type.VARCHAR, max_length=64)
        schema.add_field(field_name="path_l1", datatype=_data_type.VARCHAR, max_length=255)
        schema.add_field(field_name="path_l2", datatype=_data_type.VARCHAR, max_length=255)
        schema.add_field(field_name="segment_type", datatype=_data_type.VARCHAR, max_length=64)
        schema.add_field(field_name="chunk_order", datatype=_data_type.INT64)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="FLAT")
        index_params.add_index(field_name="user_id", index_type="Trie")
        index_params.add_index(field_name="project_id", index_type="Trie")
        index_params.add_index(field_name="doc_id", index_type="Trie")
        index_params.add_index(field_name="path_l1", index_type="Trie")
        index_params.add_index(field_name="path_l2", index_type="Trie")

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
    metadatas: list[dict[str, object]] | None = None,
) -> bool:
    if not texts or not vectors or len(texts) != len(vectors):
        return False

    if metadatas is not None and len(metadatas) != len(texts):
        return False

    if not _ensure_collection_exists(dimension=len(vectors[0])):
        return False

    client = _get_milvus_client()
    if client is None:
        return False

    data: list[dict[str, object]] = []
    for idx in range(len(texts)):
        item: dict[str, object] = {
            "vector": vectors[idx],
            "text": texts[idx],
            "user_id": user_id,
            "project_id": project_id,
            "source": "user_upload",
        }
        if metadatas is not None:
            item.update(metadatas[idx])
        data.append(item)

    try:
        client.insert(collection_name=GLOBAL_COLLECTION_NAME, data=data)
    except Exception as exc:
        logger.warning("Failed to insert vectors into Milvus: %s", exc)
        return False

    return True


def _build_filter_expr(
    user_id: str,
    project_id: str,
    filters: dict[str, object],
    field_names: set[str],
) -> str:
    safe_user_id = _escape_filter_value(user_id)
    safe_project_id = _escape_filter_value(project_id)
    conditions = [f'user_id == "{safe_user_id}"', f'project_id == "{safe_project_id}"']

    def add_equals(field: str, raw_value: object) -> None:
        if field not in field_names:
            return
        if isinstance(raw_value, str) and raw_value.strip():
            conditions.append(f'{field} == "{_escape_filter_value(raw_value.strip())}"')

    add_equals("doc_type", filters.get("doc_type"))
    add_equals("path_l1", filters.get("path_l1"))
    add_equals("path_l2", filters.get("path_l2"))
    add_equals("segment_type", filters.get("segment_type"))

    doc_ids = filters.get("doc_ids")
    if "doc_id" in field_names and isinstance(doc_ids, list):
        safe_ids = [
            f'"{_escape_filter_value(doc_id)}"'
            for doc_id in doc_ids
            if isinstance(doc_id, str) and doc_id.strip()
        ]
        if safe_ids:
            conditions.append(f"doc_id in [{', '.join(safe_ids)}]")

    return " and ".join(conditions)


def search_milvus_bible_records(
    user_id: str,
    project_id: str,
    query_vector: list[float],
    limit: int = 2,
    filters: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    client = _get_milvus_client()
    if client is None or not client.has_collection(GLOBAL_COLLECTION_NAME):
        return []

    field_names = _collection_field_names()
    filter_expr = _build_filter_expr(user_id, project_id, filters or {}, field_names)

    try:
        search_res = client.search(
            collection_name=GLOBAL_COLLECTION_NAME,
            data=[query_vector],
            limit=limit,
            filter=filter_expr,
            output_fields=[
                "text",
                "source",
                "doc_id",
                "doc_type",
                "path_l1",
                "path_l2",
                "segment_type",
                "chunk_order",
                "title",
            ],
        )
    except Exception as exc:
        logger.warning("Milvus search failed: %s", exc)
        return []

    records: list[dict[str, object]] = []
    for hits in search_res:
        for hit in hits:
            entity = hit.get("entity", {}) if isinstance(hit, dict) else {}
            if not isinstance(entity, dict):
                continue
            text = entity.get("text")
            if not isinstance(text, str):
                continue

            score_value: float | None = None
            raw_distance = hit.get("distance") if isinstance(hit, dict) else None
            if isinstance(raw_distance, (float, int)):
                score_value = float(raw_distance)

            records.append(
                {
                    "text": text,
                    "doc_id": entity.get("doc_id"),
                    "doc_type": entity.get("doc_type"),
                    "path_l1": entity.get("path_l1"),
                    "path_l2": entity.get("path_l2"),
                    "segment_type": entity.get("segment_type"),
                    "chunk_order": entity.get("chunk_order"),
                    "title": entity.get("title"),
                    "score": score_value,
                    "source_backend": "milvus",
                }
            )
    return records


def search_milvus_bible(
    user_id: str,
    project_id: str,
    query_vector: list[float],
    limit: int = 2,
    filters: dict[str, object] | None = None,
) -> list[str]:
    records = search_milvus_bible_records(
        user_id=user_id,
        project_id=project_id,
        query_vector=query_vector,
        limit=limit,
        filters=filters,
    )
    return [str(record["text"]) for record in records if isinstance(record.get("text"), str)]


def delete_milvus_documents(*, user_id: str, project_id: str, doc_ids: list[str]) -> int:
    if not doc_ids:
        return 0

    client = _get_milvus_client()
    if client is None or not client.has_collection(GLOBAL_COLLECTION_NAME):
        return 0

    field_names = _collection_field_names()
    filter_expr = _build_filter_expr(
        user_id=user_id,
        project_id=project_id,
        filters={"doc_ids": doc_ids},
        field_names=field_names,
    )

    try:
        result = client.delete(collection_name=GLOBAL_COLLECTION_NAME, filter=filter_expr)
    except Exception as exc:
        logger.warning("Milvus delete failed: %s", exc)
        return 0

    if isinstance(result, int):
        return result
    if isinstance(result, dict):
        deleted = result.get("delete_count") or result.get("deleted_count") or result.get("count")
        if isinstance(deleted, int):
            return deleted
    return len(doc_ids)
