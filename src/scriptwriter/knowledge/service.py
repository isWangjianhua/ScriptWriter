from __future__ import annotations

from scriptwriter.knowledge.models import ProjectKnowledgeHit
from scriptwriter.rag.service import ingest_knowledge_document, search_knowledge_hits


def ingest_project_knowledge_document(
    *,
    user_id: str,
    project_id: str,
    content: str,
    doc_type: str,
    title: str | None = None,
    path_l1: str | None = None,
    path_l2: str | None = None,
    doc_id: str | None = None,
    source_type: str | None = None,
    version_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    is_active: bool = True,
):
    return ingest_knowledge_document(
        user_id=user_id,
        project_id=project_id,
        content=content,
        doc_type=doc_type,
        title=title,
        path_l1=path_l1,
        path_l2=path_l2,
        doc_id=doc_id,
        source_type=source_type,
        version_id=version_id,
        episode_id=episode_id,
        scene_id=scene_id,
        is_active=is_active,
    )


def search_project_knowledge_hits(
    *,
    user_id: str,
    project_id: str,
    query: str,
    limit: int = 3,
    doc_type: str | None = None,
    path_l1: str | None = None,
    path_l2: str | None = None,
    source_type: str | None = None,
    version_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    is_active: bool | None = None,
) -> list[ProjectKnowledgeHit]:
    hits = search_knowledge_hits(
        user_id=user_id,
        project_id=project_id,
        query=query,
        limit=limit,
        doc_type=doc_type,
        path_l1=path_l1,
        path_l2=path_l2,
        source_type=source_type,
        version_id=version_id,
        episode_id=episode_id,
        scene_id=scene_id,
        is_active=is_active,
    )

    return [
        ProjectKnowledgeHit(
            text=hit.text,
            doc_id=hit.doc_id,
            doc_type=hit.doc_type,
            title=hit.title,
            path_l1=hit.path_l1,
            path_l2=hit.path_l2,
            segment_type=hit.segment_type,
            chunk_order=hit.chunk_order,
            score=hit.score,
            source_backend=hit.source_backend,
            source_type=getattr(hit, "source_type", None),
            version_id=getattr(hit, "version_id", None),
            episode_id=getattr(hit, "episode_id", None),
            scene_id=getattr(hit, "scene_id", None),
            is_active=getattr(hit, "is_active", None),
        )
        for hit in hits
    ]
