from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints

from scriptwriter.knowledge.service import ingest_project_knowledge_document
from scriptwriter.memory.service import MemoryService
from scriptwriter.projects.service import ProjectService
from scriptwriter.storage.in_memory_project_store import InMemoryProjectStore

router = APIRouter(prefix="/api/projects")
_service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())


class CreateProjectRequest(BaseModel):
    project_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None


class ConfirmRequest(BaseModel):
    comment: str | None = None


class KnowledgeUploadRequest(BaseModel):
    user_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    doc_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    title: str | None = None
    path_l1: str | None = None
    path_l2: str | None = None
    source_type: str | None = None
    version_id: str | None = None
    episode_id: str | None = None
    scene_id: str | None = None
    is_active: bool = True


@router.post("")
async def create_project(payload: CreateProjectRequest):
    project = _service.create_project(project_id=payload.project_id, title=payload.title)
    return project.model_dump()


@router.get("/{project_id}")
async def get_project(project_id: str):
    project = _service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project.model_dump()


@router.post("/{project_id}/chat")
async def project_chat(project_id: str, payload: ChatRequest):
    try:
        project = _service.handle_chat(project_id=project_id, title=payload.title, user_input=payload.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return project.model_dump()


@router.post("/{project_id}/confirm")
async def confirm_project_artifact(project_id: str, payload: ConfirmRequest):
    try:
        project = _service.confirm_current_artifact(project_id, comment=payload.comment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return project.model_dump()


@router.post("/{project_id}/knowledge/upload")
async def upload_project_knowledge(project_id: str, payload: KnowledgeUploadRequest):
    if _service.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    result = ingest_project_knowledge_document(
        user_id=payload.user_id,
        project_id=project_id,
        content=payload.content,
        doc_type=payload.doc_type,
        title=payload.title,
        path_l1=payload.path_l1,
        path_l2=payload.path_l2,
        source_type=payload.source_type,
        version_id=payload.version_id,
        episode_id=payload.episode_id,
        scene_id=payload.scene_id,
        is_active=payload.is_active,
    )
    return {
        "doc_id": result.doc_id,
        "chunk_count": result.chunk_count,
        "source_path": result.source_path,
    }


@router.get("/{project_id}/versions")
async def list_project_versions(project_id: str):
    try:
        versions = _service.list_versions(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc
    return versions
