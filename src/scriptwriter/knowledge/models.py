from __future__ import annotations

from pydantic import BaseModel


class ProjectKnowledgeHit(BaseModel):
    text: str
    doc_id: str | None = None
    doc_type: str | None = None
    title: str | None = None
    path_l1: str | None = None
    path_l2: str | None = None
    segment_type: str | None = None
    chunk_order: int | None = None
    score: float | None = None
    source_backend: str = "milvus"
    source_type: str | None = None
    version_id: str | None = None
    episode_id: str | None = None
    scene_id: str | None = None
    is_active: bool | None = None
